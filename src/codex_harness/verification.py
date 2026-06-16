from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .tasks import HARNESS_DIR, TASKS_DIR


@dataclass(frozen=True)
class TaskVerifyRequest:
    root: Path
    task_id: str | None = None
    run_checks: bool = True
    check_timeout: int = 300


@dataclass(frozen=True)
class TaskVerifyResult:
    verdict: str
    task_id: str
    task_dir: Path
    report_path: Path
    summary_path: Path


def verify_task(request: TaskVerifyRequest) -> TaskVerifyResult:
    root = request.root.resolve()
    task_dir = _resolve_task_dir(root, request.task_id)
    contract = _read_json(task_dir / "contract.json")
    baseline = _read_json(task_dir / "baseline.json")
    task_id = str(contract["task_id"])

    check_results = _run_required_checks(
        root=root,
        task_dir=task_dir,
        commands=_as_string_list(contract.get("required_checks", [])),
        run_checks=request.run_checks,
        timeout=request.check_timeout,
    )
    current_status = _run_git(root, "status", "--porcelain")
    source_state = _collect_source_state(root, task_dir, contract)
    changed_files = _changed_files_since_baseline(
        baseline_status=_git_stdout(baseline, "status_porcelain"),
        current_status=current_status["stdout"],
    )
    changed_files = [path for path in changed_files if not path.startswith(f"{HARNESS_DIR}/")]

    issues = _evaluate_issues(
        contract=contract,
        baseline=baseline,
        current_status=current_status,
        changed_files=changed_files,
        check_results=check_results,
    )
    verdict = "pass" if not issues else "fail"
    created_at = datetime.now(UTC).isoformat(timespec="seconds")
    report = {
        "schema_version": 1,
        "created_at": created_at,
        "task_id": task_id,
        "verdict": verdict,
        "changed_files": changed_files,
        "issues": issues,
        "checks": check_results,
        "source_state": source_state,
        "freshness": {
            "is_stale": False,
            "reason": "generated_for_current_source_state",
        },
        "git": {
            "current_status": current_status,
        },
    }

    report_path = task_dir / "verify.json"
    summary_path = task_dir / "verify.md"
    _write_json(report_path, report)
    summary_path.write_text(_render_verify_markdown(report), encoding="utf-8")

    return TaskVerifyResult(
        verdict=verdict,
        task_id=task_id,
        task_dir=task_dir,
        report_path=report_path,
        summary_path=summary_path,
    )


def read_verify_freshness(root: Path, task_id: str | None = None) -> dict[str, object]:
    root = root.resolve()
    task_dir = _resolve_task_dir(root, task_id)
    contract = _read_json(task_dir / "contract.json")
    report_path = task_dir / "verify.json"
    if not report_path.exists():
        return {
            "is_stale": True,
            "reason": "verify_missing",
            "current_source_state": _collect_source_state(root, task_dir, contract),
            "recorded_source_state": None,
        }

    report = _read_json(report_path)
    recorded_source_state = report.get("source_state")
    current_source_state = _collect_source_state(root, task_dir, contract)
    is_stale = recorded_source_state != current_source_state
    return {
        "is_stale": is_stale,
        "reason": "source_state_changed" if is_stale else "fresh",
        "current_source_state": current_source_state,
        "recorded_source_state": recorded_source_state,
    }


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


def _run_required_checks(
    root: Path,
    task_dir: Path,
    commands: list[str],
    run_checks: bool,
    timeout: int,
) -> list[dict[str, object]]:
    evidence_dir = task_dir / "evidence" / "checks"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    if not run_checks:
        return [
            {
                "command": command,
                "cwd": str(root),
                "skipped": True,
                "exit_code": None,
                "started_at": None,
                "finished_at": None,
                "duration_ms": None,
                "timed_out": False,
                "stdout_path": None,
                "stderr_path": None,
            }
            for command in commands
        ]

    return [
        _run_check(
            root=root,
            command=command,
            timeout=timeout,
            evidence_dir=evidence_dir,
            index=index,
        )
        for index, command in enumerate(commands, start=1)
    ]


def _run_check(root: Path, command: str, timeout: int, evidence_dir: Path, index: int) -> dict[str, object]:
    stdout_path = evidence_dir / f"check-{index:03d}.stdout.log"
    stderr_path = evidence_dir / f"check-{index:03d}.stderr.log"
    started_at = _now()
    started_perf = time.perf_counter()

    try:
        argv = shlex.split(command)
    except ValueError as exc:
        finished_at = _now()
        _write_text(stdout_path, "")
        _write_text(stderr_path, f"Could not parse command: {exc}\n")
        return {
            "command": command,
            "cwd": str(root),
            "skipped": False,
            "exit_code": 127,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": _duration_ms(started_perf),
            "timed_out": False,
            "stdout_path": _relative_to_task(evidence_dir, stdout_path),
            "stderr_path": _relative_to_task(evidence_dir, stderr_path),
        }

    if not argv:
        finished_at = _now()
        _write_text(stdout_path, "")
        _write_text(stderr_path, "Empty check command.\n")
        return {
            "command": command,
            "cwd": str(root),
            "skipped": False,
            "exit_code": 127,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": _duration_ms(started_perf),
            "timed_out": False,
            "stdout_path": _relative_to_task(evidence_dir, stdout_path),
            "stderr_path": _relative_to_task(evidence_dir, stderr_path),
        }

    result, timed_out = _run_check_command(root, tuple(argv), timeout=timeout)
    finished_at = _now()
    _write_text(stdout_path, result.stdout)
    _write_text(stderr_path, result.stderr)
    return {
        "command": command,
        "cwd": str(root),
        "skipped": False,
        "exit_code": result.returncode,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": _duration_ms(started_perf),
        "timed_out": timed_out,
        "stdout_path": _relative_to_task(evidence_dir, stdout_path),
        "stderr_path": _relative_to_task(evidence_dir, stderr_path),
    }


def _run_check_command(
    root: Path,
    command: tuple[str, ...],
    timeout: int,
) -> tuple[subprocess.CompletedProcess[str], bool]:
    try:
        result = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return result, False
    except FileNotFoundError as exc:
        return (
            subprocess.CompletedProcess(
                args=command,
                returncode=127,
                stdout="",
                stderr=str(exc),
            ),
            False,
        )
    except subprocess.TimeoutExpired as exc:
        return (
            subprocess.CompletedProcess(
                args=command,
                returncode=124,
                stdout=_decode_timeout_output(exc.stdout),
                stderr=_decode_timeout_output(exc.stderr) + f"\nTimed out after {timeout} seconds.\n",
            ),
            True,
        )


def _evaluate_issues(
    contract: dict[str, object],
    baseline: dict[str, object],
    current_status: dict[str, object],
    changed_files: list[str],
    check_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []

    if not _baseline_git_available(baseline):
        issues.append(
            {
                "severity": "P0",
                "category": "git_baseline_missing",
                "message": "Task baseline was not captured inside a git worktree.",
            }
        )

    if current_status["exit_code"] != 0:
        issues.append(
            {
                "severity": "P0",
                "category": "git_status_failed",
                "message": "Could not read current git status.",
                "stderr": current_status["stderr"],
            }
        )

    denied = _as_string_list(contract.get("denied_files", []))
    denied_changes = [path for path in changed_files if _matches_any(path, denied)]
    if denied_changes:
        issues.append(
            {
                "severity": "P0",
                "category": "denied_files_changed",
                "message": "Changed files include denied paths.",
                "files": denied_changes,
            }
        )

    allowed = _as_string_list(contract.get("allowed_files", []))
    if allowed:
        outside_allowed = [path for path in changed_files if not _matches_any(path, allowed)]
        if outside_allowed:
            issues.append(
                {
                    "severity": "P1",
                    "category": "outside_allowed_files",
                    "message": "Changed files include paths outside the allowed scope.",
                    "files": outside_allowed,
                }
            )

    failed_checks = [check for check in check_results if check["exit_code"] not in (0, None)]
    if failed_checks:
        issues.append(
            {
                "severity": "P0",
                "category": "required_checks_failed",
                "message": "One or more required checks failed.",
                "checks": [check["command"] for check in failed_checks],
            }
        )

    return issues


def _collect_source_state(root: Path, task_dir: Path, contract: dict[str, object]) -> dict[str, object]:
    diff = _run_git(root, "diff", "--binary", "--", ".")
    untracked_files = _untracked_files(root)
    return {
        "schema_version": 1,
        "head": _run_git(root, "rev-parse", "HEAD"),
        "diff_hash": _hash_text(diff["stdout"]),
        "untracked_hash": _hash_untracked_files(root, untracked_files),
        "contract_hash": _hash_file(task_dir / "contract.json"),
        "changed_files": _git_changed_files(root),
        "untracked_files": untracked_files,
    }


def _git_changed_files(root: Path) -> list[str]:
    status = _run_git(root, "status", "--porcelain")
    return sorted(
        path
        for path in _parse_porcelain_paths(status["stdout"])
        if not path.startswith(f"{HARNESS_DIR}/")
    )


def _untracked_files(root: Path) -> list[str]:
    status = _run_git(root, "ls-files", "--others", "--exclude-standard")
    return sorted(
        path.strip()
        for path in status["stdout"].splitlines()
        if path.strip() and not path.startswith(f"{HARNESS_DIR}/")
    )


def _changed_files_since_baseline(baseline_status: str, current_status: str) -> list[str]:
    baseline_files = set(_parse_porcelain_paths(baseline_status))
    current_files = set(_parse_porcelain_paths(current_status))
    return sorted(current_files - baseline_files)


def _parse_porcelain_paths(output: str) -> list[str]:
    paths: list[str] = []
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.strip())
    return paths


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(_matches_path(path, pattern) for pattern in patterns)


def _matches_path(path: str, pattern: str) -> bool:
    normalized = pattern.strip().replace("\\", "/")
    if not normalized:
        return False
    if normalized.endswith("/"):
        return path.startswith(normalized)
    return path == normalized or path.startswith(f"{normalized}/")


def _baseline_git_available(baseline: dict[str, object]) -> bool:
    git = baseline.get("git", {})
    return isinstance(git, dict) and git.get("available") is True


def _git_stdout(baseline: dict[str, object], key: str) -> str:
    git = baseline.get("git", {})
    if not isinstance(git, dict):
        return ""
    value = git.get(key, {})
    if not isinstance(value, dict):
        return ""
    stdout = value.get("stdout", "")
    return stdout if isinstance(stdout, str) else ""


def _run_git(root: Path, *args: str) -> dict[str, object]:
    result = _run_command(root, ("git", *args), timeout=10)
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _run_command(root: Path, command: tuple[str, ...], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(
            args=command,
            returncode=127,
            stdout="",
            stderr=str(exc),
        )


def _render_verify_markdown(report: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Verification Report",
            "",
            f"Task ID: `{report['task_id']}`",
            f"Verdict: `{report['verdict']}`",
            "",
            "## Changed Files",
            "",
            _render_list(report["changed_files"]),
            "",
            "## Issues",
            "",
            _render_issue_list(report["issues"]),
            "",
            "## Checks",
            "",
            _render_check_list(report["checks"]),
            "",
        ]
    )


def _render_issue_list(issues: object) -> str:
    if not isinstance(issues, list) or not issues:
        return "- None."
    lines: list[str] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        lines.append(f"- {issue.get('severity', 'P?')} {issue.get('category', 'unknown')}: {issue.get('message', '')}")
    return "\n".join(lines) if lines else "- None."


def _render_check_list(checks: object) -> str:
    if not isinstance(checks, list) or not checks:
        return "- Not specified."
    lines: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        skipped = " skipped" if check.get("skipped") else ""
        duration = check.get("duration_ms")
        duration_note = f", {duration}ms" if isinstance(duration, int) else ""
        logs = _render_check_logs(check)
        lines.append(f"- `{check.get('command', '')}` -> {check.get('exit_code')}{skipped}{duration_note}{logs}")
    return "\n".join(lines) if lines else "- Not specified."


def _render_check_logs(check: dict[str, object]) -> str:
    stdout_path = check.get("stdout_path")
    stderr_path = check.get("stderr_path")
    parts: list[str] = []
    if isinstance(stdout_path, str):
        parts.append(f"stdout: `{stdout_path}`")
    if isinstance(stderr_path, str):
        parts.append(f"stderr: `{stderr_path}`")
    return f" ({', '.join(parts)})" if parts else ""


def _render_list(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "- None."
    return "\n".join(f"- {value}" for value in values)


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _duration_ms(started_perf: float) -> int:
    return max(0, round((time.perf_counter() - started_perf) * 1000))


def _relative_to_task(evidence_dir: Path, path: Path) -> str:
    task_dir = evidence_dir.parents[1]
    return path.relative_to(task_dir).as_posix()


def _decode_timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def _hash_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _hash_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _hash_untracked_files(root: Path, paths: list[str]) -> str:
    digest = hashlib.sha256()
    for relative_path in paths:
        path = root / relative_path
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        if path.is_file():
            digest.update(path.read_bytes())
        else:
            digest.update(b"<non-file>")
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"
