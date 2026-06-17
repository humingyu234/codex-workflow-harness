from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .tasks import HARNESS_DIR, TASKS_DIR
from .verification import read_verify_freshness


@dataclass(frozen=True)
class ProofPackRequest:
    root: Path
    task_id: str | None = None


@dataclass(frozen=True)
class ProofPackResult:
    task_id: str
    task_dir: Path
    proof_path: Path
    metadata_path: Path


class ProofPackBlockedError(RuntimeError):
    pass


def create_proof_pack(request: ProofPackRequest) -> ProofPackResult:
    root = request.root.resolve()
    task_dir = _resolve_task_dir(root, request.task_id)
    contract = _read_json(task_dir / "contract.json")
    task_id = str(contract["task_id"])
    verify = _read_json_if_exists(task_dir / "verify.json")
    review = _read_json_if_exists(task_dir / "review.json")
    freshness = read_verify_freshness(root, task_id)
    issues = _proof_blockers(verify=verify, review=review, freshness=freshness)
    if issues:
        raise ProofPackBlockedError(_render_blocker_message(issues))

    assert verify is not None
    assert review is not None
    source_state = _as_dict(freshness.get("current_source_state"))
    created_at = _now()
    proof = {
        "schema_version": 1,
        "created_at": created_at,
        "task_id": task_id,
        "verdict": "pass",
        "goal": contract.get("goal", ""),
        "mode": contract.get("mode", ""),
        "changed_files": source_state.get("changed_files", []),
        "source_state": source_state,
        "verification": _verification_summary(verify),
        "review": _review_summary(review),
        "artifacts": {
            "contract": "contract.json",
            "verify": "verify.json",
            "review_brief": "review-brief.md",
            "review_record": "review.json",
            "proof_pack": "proof-pack.md",
        },
    }

    metadata_path = task_dir / "proof-pack.json"
    proof_path = task_dir / "proof-pack.md"
    _write_json(metadata_path, proof)
    proof_path.write_text(
        _render_proof_pack(
            contract=contract,
            proof=proof,
            verify=verify,
            review=review,
        ),
        encoding="utf-8",
    )

    return ProofPackResult(
        task_id=task_id,
        task_dir=task_dir,
        proof_path=proof_path,
        metadata_path=metadata_path,
    )


def _proof_blockers(
    *,
    verify: dict[str, object] | None,
    review: dict[str, object] | None,
    freshness: dict[str, object],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    current_source_state = _as_dict(freshness.get("current_source_state"))

    if verify is None:
        issues.append({"category": "verify_missing", "message": "verify.json is required before proof pack"})
    elif freshness.get("is_stale") is True:
        issues.append({"category": "verify_stale", "message": "verification evidence is stale"})
    elif verify.get("verdict") != "pass":
        issues.append({"category": "verify_failed", "message": "verification verdict must be pass"})

    if review is None:
        issues.append({"category": "review_missing", "message": "review.json is required before proof pack"})
    else:
        if review.get("verdict") != "pass":
            issues.append({"category": "review_not_pass", "message": "review verdict must be pass"})
        reviewed_source_state = _as_dict(review.get("reviewed_source_state"))
        if reviewed_source_state != current_source_state:
            issues.append({"category": "review_stale", "message": "review result does not match current source state"})
        blocking_findings = _blocking_findings(review.get("findings"))
        if blocking_findings:
            issues.append(
                {
                    "category": "blocking_findings",
                    "message": "review findings include blocking P0/P1 items: " + "; ".join(blocking_findings),
                }
            )

    return issues


def _verification_summary(verify: dict[str, object]) -> dict[str, object]:
    return {
        "verdict": verify.get("verdict"),
        "checks": [
            {
                "command": check.get("command"),
                "exit_code": check.get("exit_code"),
                "timed_out": check.get("timed_out"),
                "stdout_path": check.get("stdout_path"),
                "stderr_path": check.get("stderr_path"),
            }
            for check in _as_dict_list(verify.get("checks"))
        ],
        "issues": verify.get("issues", []),
    }


def _review_summary(review: dict[str, object]) -> dict[str, object]:
    return {
        "reviewer": review.get("reviewer"),
        "verdict": review.get("verdict"),
        "findings": review.get("findings", []),
        "residual_risks": review.get("residual_risks", []),
    }


def _render_proof_pack(
    *,
    contract: dict[str, object],
    proof: dict[str, object],
    verify: dict[str, object],
    review: dict[str, object],
) -> str:
    source_state = _as_dict(proof.get("source_state"))
    return "\n".join(
        [
            "# Proof Pack",
            "",
            "## Task",
            "",
            f"Task ID: `{proof['task_id']}`",
            f"Mode: `{proof.get('mode', '')}`",
            "",
            str(proof.get("goal", "")),
            "",
            "## Scope",
            "",
            "Allowed files:",
            "",
            _render_list(contract.get("allowed_files")),
            "",
            "Denied files:",
            "",
            _render_list(contract.get("denied_files")),
            "",
            "## Implementation Summary",
            "",
            "Implementation details are represented by the current git diff and review artifacts.",
            "",
            "## Changed Files",
            "",
            _render_list(source_state.get("changed_files")),
            "",
            "## Verification",
            "",
            f"Verdict: `{verify.get('verdict')}`",
            "",
            _render_checks(verify.get("checks")),
            "",
            "## Review Findings",
            "",
            f"Reviewer: `{review.get('reviewer', '')}`",
            f"Verdict: `{review.get('verdict', '')}`",
            "",
            _render_list(review.get("findings")),
            "",
            "## Known Limitations",
            "",
            _render_list(review.get("residual_risks")),
            "",
            "## How To Run",
            "",
            _render_commands(contract.get("required_checks")),
            "",
            "## Evidence Paths",
            "",
            _render_list(
                [
                    "contract.json",
                    "verify.json",
                    "verify.md",
                    "review-brief.md",
                    "review-brief.json",
                    "review-diff.patch",
                    "review.json",
                    "review.md",
                    "proof-pack.json",
                ]
            ),
            "",
        ]
    )


def _render_checks(checks: object) -> str:
    rows = _as_dict_list(checks)
    if not rows:
        return "- No required checks recorded."
    lines = ["| Check | Exit Code | Evidence |", "| --- | --- | --- |"]
    for check in rows:
        evidence = ", ".join(
            path
            for path in (check.get("stdout_path"), check.get("stderr_path"))
            if isinstance(path, str) and path
        )
        lines.append(f"| `{check.get('command', '')}` | `{check.get('exit_code')}` | `{evidence}` |")
    return "\n".join(lines)


def _render_commands(commands: object) -> str:
    if not isinstance(commands, list) or not commands:
        return "```bash\n# No required checks recorded.\n```"
    body = "\n".join(str(command) for command in commands)
    return f"```bash\n{body}\n```"


def _render_blocker_message(issues: list[dict[str, str]]) -> str:
    return "proof pack blocked: " + "; ".join(f"{issue['category']}: {issue['message']}" for issue in issues)


def _blocking_findings(findings: object) -> list[str]:
    if not isinstance(findings, list):
        return []
    return [
        finding
        for finding in findings
        if isinstance(finding, str) and (_has_severity(finding, "P0") or _has_severity(finding, "P1"))
    ]


def _has_severity(value: str, severity: str) -> bool:
    return re.search(rf"\b{re.escape(severity)}\b", value.upper()) is not None


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


def _as_dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


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
