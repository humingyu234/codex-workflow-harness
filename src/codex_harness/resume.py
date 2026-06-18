from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .tasks import HARNESS_DIR, TASKS_DIR
from .verification import read_verify_freshness


@dataclass(frozen=True)
class ResumeBriefRequest:
    root: Path
    task_id: str | None = None


@dataclass(frozen=True)
class ResumeBriefResult:
    task_id: str
    task_dir: Path
    brief_path: Path
    metadata_path: Path
    status: str
    next_step: str


def create_resume_brief(request: ResumeBriefRequest) -> ResumeBriefResult:
    root = request.root.resolve()
    task_dir = _resolve_task_dir(root, request.task_id)
    contract = _read_json(task_dir / "contract.json")
    task_id = str(contract["task_id"])
    verify = _read_json_if_exists(task_dir / "verify.json")
    review = _read_json_if_exists(task_dir / "review.json")
    proof = _read_json_if_exists(task_dir / "proof-pack.json")
    freshness = read_verify_freshness(root, task_id)
    current_source_state = _as_dict(freshness.get("current_source_state"))
    status, next_step = _task_status(
        verify=verify,
        review=review,
        proof=proof,
        freshness=freshness,
        current_source_state=current_source_state,
    )
    artifacts = _artifact_map(task_dir)
    resume = {
        "schema_version": 1,
        "created_at": _now(),
        "task_id": task_id,
        "status": status,
        "next_step": next_step,
        "goal": contract.get("goal", ""),
        "mode": contract.get("mode", ""),
        "changed_files": current_source_state.get("changed_files", []),
        "verify": _verify_summary(verify, freshness),
        "review": _review_summary(review, current_source_state),
        "proof": _proof_summary(proof, current_source_state),
        "artifacts": artifacts,
        "files_to_inspect": _files_to_inspect(artifacts),
    }

    metadata_path = task_dir / "resume-brief.json"
    brief_path = task_dir / "resume-brief.md"
    _write_json(metadata_path, resume)
    brief_path.write_text(_render_resume_brief(resume, contract), encoding="utf-8")

    return ResumeBriefResult(
        task_id=task_id,
        task_dir=task_dir,
        brief_path=brief_path,
        metadata_path=metadata_path,
        status=status,
        next_step=next_step,
    )


def _task_status(
    *,
    verify: dict[str, object] | None,
    review: dict[str, object] | None,
    proof: dict[str, object] | None,
    freshness: dict[str, object],
    current_source_state: dict[str, object],
) -> tuple[str, str]:
    if verify is None:
        return "needs_verify", "Run `codex-harness task verify` after implementation changes are ready."
    if freshness.get("is_stale") is True:
        return "needs_reverify", "Source changed after verify; rerun `codex-harness task verify`."
    if verify.get("verdict") != "pass":
        return "needs_repair", "Fix verification issues, then rerun `codex-harness task verify`."
    if review is None:
        return "needs_review", "Run `codex-harness task review-brief`, get a fresh review, then record it."
    if _review_is_stale(review, current_source_state):
        return "needs_review_refresh", "Source changed after review; regenerate review-brief and record a fresh review."
    if review.get("verdict") in ("repair", "block"):
        return "needs_repair", "Fix P0/P1 review findings, then verify and review again."
    if review.get("verdict") != "pass":
        return "needs_review", "Record a valid pass/repair/block review result."
    if proof is None:
        return "ready_for_proof_pack", "Run `codex-harness task proof-pack` if this task is ready for delivery."
    if _proof_is_stale(proof, current_source_state):
        return "ready_for_proof_pack", "Proof pack is stale; regenerate it with `codex-harness task proof-pack`."
    return "ready_for_delivery", "Use proof-pack.md for delivery or handoff."


def _verify_summary(verify: dict[str, object] | None, freshness: dict[str, object]) -> dict[str, object]:
    if verify is None:
        return {
            "exists": False,
            "verdict": None,
            "freshness": freshness.get("reason"),
        }
    return {
        "exists": True,
        "verdict": verify.get("verdict"),
        "freshness": freshness.get("reason"),
        "is_stale": freshness.get("is_stale"),
        "issues": verify.get("issues", []),
    }


def _review_summary(review: dict[str, object] | None, current_source_state: dict[str, object]) -> dict[str, object]:
    if review is None:
        return {
            "exists": False,
            "verdict": None,
            "is_stale": None,
            "findings": [],
        }
    return {
        "exists": True,
        "reviewer": review.get("reviewer"),
        "verdict": review.get("verdict"),
        "is_stale": _review_is_stale(review, current_source_state),
        "findings": review.get("findings", []),
        "residual_risks": review.get("residual_risks", []),
    }


def _proof_summary(proof: dict[str, object] | None, current_source_state: dict[str, object]) -> dict[str, object]:
    if proof is None:
        return {
            "exists": False,
            "verdict": None,
            "is_stale": None,
        }
    return {
        "exists": True,
        "verdict": proof.get("verdict"),
        "is_stale": _proof_is_stale(proof, current_source_state),
    }


def _review_is_stale(review: dict[str, object], current_source_state: dict[str, object]) -> bool:
    return _as_dict(review.get("reviewed_source_state")) != current_source_state


def _proof_is_stale(proof: dict[str, object], current_source_state: dict[str, object]) -> bool:
    return _as_dict(proof.get("source_state")) != current_source_state


def _artifact_map(task_dir: Path) -> dict[str, str | None]:
    names = {
        "contract": "contract.md",
        "spec": "spec.md",
        "plan": "plan.md",
        "verify": "verify.md",
        "review_brief": "review-brief.md",
        "review": "review.md",
        "proof_pack": "proof-pack.md",
        "resume_brief": "resume-brief.md",
    }
    return {key: value if (task_dir / value).exists() else None for key, value in names.items()}


def _files_to_inspect(artifacts: dict[str, str | None]) -> list[str]:
    preferred = ("contract", "spec", "plan", "verify", "review", "proof_pack")
    return [artifact for key in preferred if (artifact := artifacts.get(key))]


def _render_resume_brief(resume: dict[str, object], contract: dict[str, object]) -> str:
    verify = _as_dict(resume.get("verify"))
    review = _as_dict(resume.get("review"))
    proof = _as_dict(resume.get("proof"))
    return "\n".join(
        [
            "# Resume Brief",
            "",
            "Use this brief to continue the task in a fresh Codex or Claude Code session.",
            "",
            f"Task ID: `{resume['task_id']}`",
            f"Status: `{resume['status']}`",
            "",
            "## Goal",
            "",
            str(resume.get("goal", "")),
            "",
            "## Next Step",
            "",
            str(resume.get("next_step", "")),
            "",
            "## Current Evidence",
            "",
            f"- verify: `{verify.get('verdict')}` freshness: `{verify.get('freshness')}` stale: `{verify.get('is_stale')}`",
            f"- review: `{review.get('verdict')}` stale: `{review.get('is_stale')}`",
            f"- proof: `{proof.get('verdict')}` stale: `{proof.get('is_stale')}`",
            "",
            "## Changed Files",
            "",
            _render_list(resume.get("changed_files")),
            "",
            "## Files To Inspect First",
            "",
            _render_list(resume.get("files_to_inspect")),
            "",
            "## Required Checks",
            "",
            _render_list(contract.get("required_checks")),
            "",
            "## Review Findings",
            "",
            _render_list(review.get("findings")),
            "",
            "## Residual Risks",
            "",
            _render_list(review.get("residual_risks")),
            "",
            "## Non-Goals",
            "",
            _render_list(contract.get("non_goals")),
            "",
        ]
    )


def _resolve_task_dir(root: Path, task_id: str | None) -> Path:
    tasks_root = root / HARNESS_DIR / TASKS_DIR
    if task_id:
        task_dir = tasks_root / task_id
        if not task_dir.exists():
            raise FileNotFoundError(f"task not found: {task_id}")
        return task_dir

    task_dirs = [path for path in tasks_root.iterdir() if path.is_dir()]
    if not task_dirs:
        raise FileNotFoundError("no tasks found")
    return max(task_dirs, key=lambda path: path.stat().st_mtime)


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _render_list(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "- None."
    return "\n".join(f"- {value}" for value in values)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return _read_json(path)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
