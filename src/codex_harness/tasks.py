from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


HARNESS_DIR = ".codex-harness"
TASKS_DIR = "tasks"


@dataclass(frozen=True)
class TaskStartRequest:
    goal: str
    mode: str
    root: Path
    allowed_files: tuple[str, ...] = ()
    denied_files: tuple[str, ...] = ()
    required_checks: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    non_goals: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskStartResult:
    task_id: str
    task_dir: Path
    contract_path: Path
    baseline_path: Path


def start_task(request: TaskStartRequest) -> TaskStartResult:
    root = request.root.resolve()
    task_id = _make_task_id(request.goal)
    task_dir = _next_task_dir(root / HARNESS_DIR / TASKS_DIR, task_id)
    task_id = task_dir.name
    task_dir.mkdir(parents=True, exist_ok=False)
    (task_dir / "phases").mkdir()

    created_at = datetime.now(UTC).isoformat(timespec="seconds")
    baseline = _collect_git_baseline(root, created_at)
    contract = _build_contract(request, task_id, created_at, root)

    _write_json(task_dir / "contract.json", contract)
    _write_json(task_dir / "baseline.json", baseline)
    _write_text(task_dir / "contract.md", _render_contract_markdown(contract))
    _write_text(task_dir / "spec.md", _render_spec(request))
    _write_text(task_dir / "plan.md", _render_plan(request))
    _write_text(task_dir / "phases" / "phase-001.md", _render_phase(request))
    _write_text(task_dir / "log.md", _render_log(task_id, created_at))

    return TaskStartResult(
        task_id=task_id,
        task_dir=task_dir,
        contract_path=task_dir / "contract.json",
        baseline_path=task_dir / "baseline.json",
    )


def _make_task_id(goal: str) -> str:
    date_prefix = datetime.now(UTC).strftime("%Y%m%d")
    slug = re.sub(r"[^a-z0-9]+", "-", goal.lower()).strip("-")
    slug = slug[:48].strip("-") or "task"
    return f"{date_prefix}-{slug}"


def _next_task_dir(parent: Path, task_id: str) -> Path:
    candidate = parent / task_id
    if not candidate.exists():
        return candidate

    counter = 2
    while True:
        candidate = parent / f"{task_id}-{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def _collect_git_baseline(root: Path, created_at: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "created_at": created_at,
        "git": {
            "available": _git_available(root),
            "branch": _run_git(root, "rev-parse", "--abbrev-ref", "HEAD"),
            "head": _run_git(root, "rev-parse", "HEAD"),
            "status_porcelain": _run_git(root, "status", "--porcelain"),
        },
    }


def _git_available(root: Path) -> bool:
    result = _run_command(root, ("git", "rev-parse", "--is-inside-work-tree"))
    return result.returncode == 0 and result.stdout.strip() == "true"


def _run_git(root: Path, *args: str) -> dict[str, object]:
    result = _run_command(root, ("git", *args))
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _run_command(root: Path, command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(
            args=command,
            returncode=127,
            stdout="",
            stderr=str(exc),
        )


def _build_contract(
    request: TaskStartRequest,
    task_id: str,
    created_at: str,
    root: Path,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "task_id": task_id,
        "created_at": created_at,
        "goal": request.goal,
        "mode": request.mode,
        "root": str(root),
        "allowed_files": list(request.allowed_files),
        "denied_files": list(request.denied_files),
        "required_checks": list(request.required_checks),
        "acceptance_criteria": list(request.acceptance_criteria),
        "non_goals": list(request.non_goals),
        "artifacts": {
            "contract": "contract.json",
            "baseline": "baseline.json",
            "spec": "spec.md",
            "plan": "plan.md",
            "phase_1": "phases/phase-001.md",
            "log": "log.md",
        },
    }


def _render_contract_markdown(contract: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Task Contract",
            "",
            f"Task ID: `{contract['task_id']}`",
            f"Mode: `{contract['mode']}`",
            "",
            "## Goal",
            "",
            str(contract["goal"]),
            "",
            "## Allowed Files",
            "",
            _render_list(contract["allowed_files"]),
            "",
            "## Denied Files",
            "",
            _render_list(contract["denied_files"]),
            "",
            "## Required Checks",
            "",
            _render_list(contract["required_checks"]),
            "",
            "## Acceptance Criteria",
            "",
            _render_list(contract["acceptance_criteria"]),
            "",
            "## Non-Goals",
            "",
            _render_list(contract["non_goals"]),
            "",
        ]
    )


def _render_spec(request: TaskStartRequest) -> str:
    return "\n".join(
        [
            "# Task Spec",
            "",
            "## Raw Request",
            "",
            request.goal,
            "",
            "## Goal",
            "",
            request.goal,
            "",
            "## Acceptance Criteria",
            "",
            _render_list(request.acceptance_criteria),
            "",
            "## Constraints",
            "",
            _render_list(request.denied_files, prefix="Do not touch "),
            "",
            "## Non-Goals",
            "",
            _render_list(request.non_goals),
            "",
            "## Open Questions",
            "",
            "- None recorded yet.",
            "",
        ]
    )


def _render_plan(request: TaskStartRequest) -> str:
    return "\n".join(
        [
            "# Task Plan",
            "",
            "## Goal",
            "",
            request.goal,
            "",
            "## Phases",
            "",
            "### Phase 1",
            "",
            "Scope: define the smallest useful implementation slice.",
            "",
            "Allowed files:",
            "",
            _render_list(request.allowed_files),
            "",
            "Checks:",
            "",
            _render_list(request.required_checks),
            "",
            "Acceptance:",
            "",
            _render_list(request.acceptance_criteria),
            "",
            "## Risks And Mitigations",
            "",
            "- Add risks before implementation if this task is more than a small change.",
            "",
            "## Non-Goals",
            "",
            _render_list(request.non_goals),
            "",
        ]
    )


def _render_phase(request: TaskStartRequest) -> str:
    return "\n".join(
        [
            "# Phase Handoff",
            "",
            "## Phase",
            "",
            "Phase 1",
            "",
            "## Objective",
            "",
            request.goal,
            "",
            "## Allowed Files",
            "",
            _render_list(request.allowed_files),
            "",
            "## Denied Files",
            "",
            _render_list(request.denied_files),
            "",
            "## Required Checks",
            "",
            _render_list(request.required_checks),
            "",
            "## Done When",
            "",
            _render_list(request.acceptance_criteria),
            "",
            "## Non-Goals",
            "",
            _render_list(request.non_goals),
            "",
        ]
    )


def _render_log(task_id: str, created_at: str) -> str:
    return "\n".join(
        [
            "# Task Log",
            "",
            f"- {created_at}: started `{task_id}`.",
            "",
        ]
    )


def _render_list(values: object, prefix: str = "") -> str:
    if not isinstance(values, (list, tuple)) or not values:
        return "- Not specified."
    return "\n".join(f"- {prefix}{value}" for value in values)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
