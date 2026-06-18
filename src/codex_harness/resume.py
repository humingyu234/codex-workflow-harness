from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .status import TaskStatusRequest, TaskStatusResult, read_task_status


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
    status_result = read_task_status(TaskStatusRequest(root=request.root, task_id=request.task_id))
    task_dir = status_result.task_dir
    contract = status_result.contract
    task_id = status_result.task_id
    artifacts = status_result.artifacts
    resume = {
        "schema_version": 1,
        "created_at": _now(),
        "task_id": task_id,
        "status": status_result.status,
        "next_step": status_result.next_step,
        "goal": contract.get("goal", ""),
        "mode": contract.get("mode", ""),
        "changed_files": status_result.current_source_state.get("changed_files", []),
        "verify": _verify_summary(status_result),
        "review": _review_summary(status_result),
        "proof": _proof_summary(status_result),
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
        status=status_result.status,
        next_step=status_result.next_step,
    )


def _verify_summary(status_result: TaskStatusResult) -> dict[str, object]:
    verify = status_result.verify
    freshness = status_result.freshness
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


def _review_summary(status_result: TaskStatusResult) -> dict[str, object]:
    review = status_result.review
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
        "is_stale": status_result.review_is_stale,
        "findings": review.get("findings", []),
        "residual_risks": review.get("residual_risks", []),
    }


def _proof_summary(status_result: TaskStatusResult) -> dict[str, object]:
    proof = status_result.proof
    if proof is None:
        return {
            "exists": False,
            "verdict": None,
            "is_stale": None,
        }
    return {
        "exists": True,
        "verdict": proof.get("verdict"),
        "is_stale": status_result.proof_is_stale,
    }


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


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _render_list(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "- None."
    return "\n".join(f"- {value}" for value in values)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
