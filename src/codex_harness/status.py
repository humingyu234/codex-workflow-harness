from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .tasks import HARNESS_DIR, TASKS_DIR
from .verification import read_verify_freshness


@dataclass(frozen=True)
class TaskStatusRequest:
    root: Path
    task_id: str | None = None


@dataclass(frozen=True)
class TaskStatusResult:
    task_id: str
    task_dir: Path
    status: str
    next_step: str
    contract: dict[str, object]
    verify: dict[str, object] | None
    review: dict[str, object] | None
    proof: dict[str, object] | None
    freshness: dict[str, object]
    current_source_state: dict[str, object]
    artifacts: dict[str, str | None]
    review_is_stale: bool | None
    proof_is_stale: bool | None


def read_task_status(request: TaskStatusRequest) -> TaskStatusResult:
    root = request.root.resolve()
    task_dir = _resolve_task_dir(root, request.task_id)
    contract = _read_json(task_dir / "contract.json")
    task_id = str(contract["task_id"])
    verify = _read_json_if_exists(task_dir / "verify.json")
    review = _read_json_if_exists(task_dir / "review.json")
    proof = _read_json_if_exists(task_dir / "proof-pack.json")
    freshness = read_verify_freshness(root, task_id)
    current_source_state = _as_dict(freshness.get("current_source_state"))
    review_is_stale = _review_is_stale(review, current_source_state) if review is not None else None
    proof_is_stale = _proof_is_stale(proof, current_source_state) if proof is not None else None
    status, next_step = _task_status(
        verify=verify,
        review=review,
        proof=proof,
        freshness=freshness,
        review_is_stale=review_is_stale,
        proof_is_stale=proof_is_stale,
    )

    return TaskStatusResult(
        task_id=task_id,
        task_dir=task_dir,
        status=status,
        next_step=next_step,
        contract=contract,
        verify=verify,
        review=review,
        proof=proof,
        freshness=freshness,
        current_source_state=current_source_state,
        artifacts=_artifact_map(task_dir),
        review_is_stale=review_is_stale,
        proof_is_stale=proof_is_stale,
    )


def render_task_status(result: TaskStatusResult) -> str:
    changed_files = result.current_source_state.get("changed_files", [])
    verify_verdict = result.verify.get("verdict") if result.verify else None
    review_verdict = result.review.get("verdict") if result.review else None
    proof_verdict = result.proof.get("verdict") if result.proof else None
    return "\n".join(
        [
            f"Task: {result.task_id}",
            f"Status: {result.status}",
            f"Next: {result.next_step}",
            f"Verify: {_artifact_state(result.verify, verify_verdict, result.freshness.get('is_stale'))}",
            f"Review: {_artifact_state(result.review, review_verdict, result.review_is_stale)}",
            f"Proof: {_artifact_state(result.proof, proof_verdict, result.proof_is_stale)}",
            "Changed files:",
            _render_list(changed_files),
        ]
    )


def _task_status(
    *,
    verify: dict[str, object] | None,
    review: dict[str, object] | None,
    proof: dict[str, object] | None,
    freshness: dict[str, object],
    review_is_stale: bool | None,
    proof_is_stale: bool | None,
) -> tuple[str, str]:
    if verify is None:
        return "needs_verify", "Run `codex-harness task verify` after implementation changes are ready."
    if freshness.get("is_stale") is True:
        return "needs_reverify", "Source changed after verify; rerun `codex-harness task verify`."
    if verify.get("verdict") != "pass":
        return "needs_repair", "Fix verification issues, then rerun `codex-harness task verify`."
    if review is None:
        return "needs_review", "Run `codex-harness task review-brief`, get a fresh review, then record it."
    if review_is_stale is True:
        return "needs_review_refresh", "Source changed after review; regenerate review-brief and record a fresh review."
    if review.get("verdict") in ("repair", "block"):
        return "needs_repair", "Fix P0/P1 review findings, then verify and review again."
    if review.get("verdict") != "pass":
        return "needs_review", "Record a valid pass/repair/block review result."
    if proof is None:
        return "ready_for_proof_pack", "Run `codex-harness task proof-pack` if this task is ready for delivery."
    if proof_is_stale is True:
        return "ready_for_proof_pack", "Proof pack is stale; regenerate it with `codex-harness task proof-pack`."
    return "ready_for_delivery", "Use proof-pack.md for delivery or handoff."


def _review_is_stale(review: dict[str, object], current_source_state: dict[str, object]) -> bool:
    return _as_dict(review.get("reviewed_source_state")) != current_source_state


def _proof_is_stale(proof: dict[str, object], current_source_state: dict[str, object]) -> bool:
    return _as_dict(proof.get("source_state")) != current_source_state


def _artifact_state(artifact: dict[str, object] | None, verdict: object, is_stale: object) -> str:
    if artifact is None:
        return "missing"
    stale = "stale" if is_stale is True else "fresh"
    return f"{verdict} ({stale})"


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
