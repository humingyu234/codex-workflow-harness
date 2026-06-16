from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .tasks import HARNESS_DIR, TASKS_DIR
from .verification import read_verify_freshness


REVIEW_VERDICTS = ("pass", "repair", "block")


@dataclass(frozen=True)
class ReviewBriefRequest:
    root: Path
    task_id: str | None = None


@dataclass(frozen=True)
class ReviewBriefResult:
    task_id: str
    task_dir: Path
    brief_path: Path
    metadata_path: Path
    diff_path: Path
    readiness: str


@dataclass(frozen=True)
class ReviewRecordRequest:
    root: Path
    verdict: str
    task_id: str | None = None
    reviewer: str = "external-reviewer"
    findings: tuple[str, ...] = ()
    residual_risks: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewRecordResult:
    task_id: str
    task_dir: Path
    record_path: Path
    summary_path: Path
    verdict: str


class StaleReviewBriefError(RuntimeError):
    pass


def create_review_brief(request: ReviewBriefRequest) -> ReviewBriefResult:
    root = request.root.resolve()
    task_dir = _resolve_task_dir(root, request.task_id)
    contract = _read_json(task_dir / "contract.json")
    task_id = str(contract["task_id"])
    verify = _read_json_if_exists(task_dir / "verify.json")
    freshness = read_verify_freshness(root, task_id)
    source_state = _as_dict(freshness.get("current_source_state"))
    readiness = _review_readiness(verify, freshness)
    diff = _git_diff(root)

    diff_path = task_dir / "review-diff.patch"
    brief_path = task_dir / "review-brief.md"
    metadata_path = task_dir / "review-brief.json"
    diff_path.write_text(diff, encoding="utf-8")

    metadata = {
        "schema_version": 1,
        "created_at": _now(),
        "task_id": task_id,
        "readiness": readiness,
        "source_state": source_state,
        "verify_freshness": freshness,
        "artifacts": {
            "contract": "contract.json",
            "verify": "verify.json" if verify is not None else None,
            "diff": "review-diff.patch",
            "brief": "review-brief.md",
        },
    }
    _write_json(metadata_path, metadata)
    brief_path.write_text(
        _render_review_brief(
            contract=contract,
            verify=verify,
            freshness=freshness,
            source_state=source_state,
            readiness=readiness,
            diff=diff,
            spec=_read_text_if_exists(task_dir / "spec.md"),
            plan=_read_text_if_exists(task_dir / "plan.md"),
        ),
        encoding="utf-8",
    )

    return ReviewBriefResult(
        task_id=task_id,
        task_dir=task_dir,
        brief_path=brief_path,
        metadata_path=metadata_path,
        diff_path=diff_path,
        readiness=readiness,
    )


def record_review(request: ReviewRecordRequest) -> ReviewRecordResult:
    root = request.root.resolve()
    task_dir = _resolve_task_dir(root, request.task_id)
    contract = _read_json(task_dir / "contract.json")
    task_id = str(contract["task_id"])
    verdict = request.verdict.strip().lower()
    if verdict not in REVIEW_VERDICTS:
        raise ValueError(f"review verdict must be one of: {', '.join(REVIEW_VERDICTS)}")
    if verdict in ("repair", "block") and not request.findings:
        raise ValueError("repair/block review records require at least one finding")

    brief_metadata = _read_json(task_dir / "review-brief.json")
    reviewed_source_state = _as_dict(brief_metadata.get("source_state"))
    current_source_state = _as_dict(read_verify_freshness(root, task_id).get("current_source_state"))
    if reviewed_source_state != current_source_state:
        raise StaleReviewBriefError("review brief is stale; regenerate review-brief before recording review")

    created_at = _now()
    record = {
        "schema_version": 1,
        "created_at": created_at,
        "task_id": task_id,
        "reviewer": request.reviewer,
        "verdict": verdict,
        "findings": list(request.findings),
        "residual_risks": list(request.residual_risks),
        "reviewed_source_state": reviewed_source_state,
        "review_brief": "review-brief.json",
    }
    record_path = task_dir / "review.json"
    summary_path = task_dir / "review.md"
    _write_json(record_path, record)
    summary_path.write_text(_render_review_record(record), encoding="utf-8")

    return ReviewRecordResult(
        task_id=task_id,
        task_dir=task_dir,
        record_path=record_path,
        summary_path=summary_path,
        verdict=verdict,
    )


def _review_readiness(verify: dict[str, object] | None, freshness: dict[str, object]) -> str:
    if verify is None:
        return "verify_missing"
    if freshness.get("is_stale") is True:
        return "verify_stale"
    if verify.get("verdict") != "pass":
        return "verify_failed"
    return "ready"


def _render_review_brief(
    *,
    contract: dict[str, object],
    verify: dict[str, object] | None,
    freshness: dict[str, object],
    source_state: dict[str, object],
    readiness: str,
    diff: str,
    spec: str,
    plan: str,
) -> str:
    verify_verdict = verify.get("verdict") if verify else "missing"
    return "\n".join(
        [
            "# Review Brief",
            "",
            "You are an independent reviewer. Do not rely on implementation chat context.",
            "Review whether the diff satisfies the task contract. Prioritize correctness, scope, tests, safety, and maintainability.",
            "",
            f"Task ID: `{contract['task_id']}`",
            f"Review readiness: `{readiness}`",
            f"Verify verdict: `{verify_verdict}`",
            f"Verify freshness: `{freshness.get('reason', 'unknown')}`",
            "",
            "## Goal",
            "",
            str(contract.get("goal", "")),
            "",
            "## Allowed Files",
            "",
            _render_list(contract.get("allowed_files")),
            "",
            "## Denied Files",
            "",
            _render_list(contract.get("denied_files")),
            "",
            "## Acceptance Criteria",
            "",
            _render_list(contract.get("acceptance_criteria")),
            "",
            "## Non-Goals",
            "",
            _render_list(contract.get("non_goals")),
            "",
            "## Source State",
            "",
            f"- head: `{_source_state_head(source_state)}`",
            f"- diff_hash: `{source_state.get('diff_hash', '')}`",
            f"- untracked_hash: `{source_state.get('untracked_hash', '')}`",
            f"- contract_hash: `{source_state.get('contract_hash', '')}`",
            "",
            "## Changed Files",
            "",
            _render_list(source_state.get("changed_files")),
            "",
            "## Spec",
            "",
            _fence(spec),
            "",
            "## Plan",
            "",
            _fence(plan),
            "",
            "## Diff",
            "",
            _fence(diff, language="diff"),
            "",
            "## Expected Review Output",
            "",
            "Verdict: pass | repair | block",
            "",
            "Findings:",
            "- Severity: P0 | P1 | P2",
            "  Category:",
            "  File/Location:",
            "  Evidence:",
            "  Why it matters:",
            "  Suggested fix:",
            "",
            "Residual risk:",
            "- ",
            "",
        ]
    )


def _render_review_record(record: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Review Record",
            "",
            f"Task ID: `{record['task_id']}`",
            f"Reviewer: `{record['reviewer']}`",
            f"Verdict: `{record['verdict']}`",
            "",
            "## Findings",
            "",
            _render_list(record.get("findings")),
            "",
            "## Residual Risks",
            "",
            _render_list(record.get("residual_risks")),
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


def _git_diff(root: Path) -> str:
    result = subprocess.run(
        ("git", "diff", "--binary", "--", "."),
        cwd=root,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    return result.stdout


def _source_state_head(source_state: dict[str, object]) -> str:
    head = source_state.get("head")
    if isinstance(head, dict):
        return str(head.get("stdout", "")).strip()
    return ""


def _render_list(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "- Not specified."
    return "\n".join(f"- {value}" for value in values)


def _fence(value: str, language: str = "text") -> str:
    return f"```{language}\n{value.rstrip()}\n```"


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return _read_json(path)


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
