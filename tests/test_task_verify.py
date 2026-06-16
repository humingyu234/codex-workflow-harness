from __future__ import annotations

import json
import subprocess
from pathlib import Path

from codex_harness.cli import main
from codex_harness.verification import read_verify_freshness


def test_task_verify_passes_for_allowed_change_and_passing_check(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    _git_commit_all(tmp_path)

    assert main(
        [
            "task",
            "start",
            "Update app",
            "--root",
            str(tmp_path),
            "--allowed",
            "src/",
            "--check",
            "python3 -c 'print(\"ok\")'",
        ]
    ) == 0

    (tmp_path / "src" / "app.py").write_text("print('changed')\n", encoding="utf-8")
    task_id = _only_task_id(tmp_path)

    assert main(["task", "verify", task_id, "--root", str(tmp_path)]) == 0

    report = _read_report(tmp_path, task_id)
    assert report["verdict"] == "pass"
    assert report["changed_files"] == ["src/app.py"]
    assert report["issues"] == []
    check = report["checks"][0]
    assert check["command"] == "python3 -c 'print(\"ok\")'"
    assert check["cwd"] == str(tmp_path)
    assert check["exit_code"] == 0
    assert check["timed_out"] is False
    assert isinstance(check["duration_ms"], int)
    assert isinstance(check["started_at"], str)
    assert isinstance(check["finished_at"], str)
    assert check["stdout_path"] == "evidence/checks/check-001.stdout.log"
    assert check["stderr_path"] == "evidence/checks/check-001.stderr.log"
    assert (tmp_path / ".codex-harness" / "tasks" / task_id / check["stdout_path"]).read_text(
        encoding="utf-8"
    ) == "ok\n"
    assert report["freshness"] == {
        "is_stale": False,
        "reason": "generated_for_current_source_state",
    }
    source_state = report["source_state"]
    assert source_state["schema_version"] == 1
    assert str(source_state["diff_hash"]).startswith("sha256:")
    assert str(source_state["untracked_hash"]).startswith("sha256:")
    assert str(source_state["contract_hash"]).startswith("sha256:")
    assert source_state["changed_files"] == ["src/app.py"]


def test_task_verify_fails_when_denied_file_changed(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "token.txt").write_text("old\n", encoding="utf-8")
    _git_commit_all(tmp_path)

    assert main(
        [
            "task",
            "start",
            "Do safe work",
            "--root",
            str(tmp_path),
            "--denied",
            "secrets/",
        ]
    ) == 0

    (tmp_path / "secrets" / "token.txt").write_text("new\n", encoding="utf-8")
    task_id = _only_task_id(tmp_path)

    assert main(["task", "verify", task_id, "--root", str(tmp_path)]) == 1

    report = _read_report(tmp_path, task_id)
    assert report["verdict"] == "fail"
    assert report["issues"][0]["category"] == "denied_files_changed"
    assert report["issues"][0]["files"] == ["secrets/token.txt"]


def test_task_verify_fails_when_required_check_fails(tmp_path: Path) -> None:
    _git_init(tmp_path)

    assert main(
        [
            "task",
            "start",
            "Run failing check",
            "--root",
            str(tmp_path),
            "--check",
            "python3 -c 'import sys; sys.exit(3)'",
        ]
    ) == 0

    task_id = _only_task_id(tmp_path)

    assert main(["task", "verify", task_id, "--root", str(tmp_path)]) == 1

    report = _read_report(tmp_path, task_id)
    assert report["verdict"] == "fail"
    assert report["issues"][0]["category"] == "required_checks_failed"
    check = report["checks"][0]
    assert check["exit_code"] == 3
    assert check["stdout_path"] == "evidence/checks/check-001.stdout.log"
    assert check["stderr_path"] == "evidence/checks/check-001.stderr.log"


def test_task_verify_records_parse_errors_as_evidence_logs(tmp_path: Path) -> None:
    _git_init(tmp_path)

    assert main(
        [
            "task",
            "start",
            "Run unparseable check",
            "--root",
            str(tmp_path),
            "--check",
            "python3 -c '",
        ]
    ) == 0

    task_id = _only_task_id(tmp_path)

    assert main(["task", "verify", task_id, "--root", str(tmp_path)]) == 1

    report = _read_report(tmp_path, task_id)
    check = report["checks"][0]
    assert check["exit_code"] == 127
    stderr = (tmp_path / ".codex-harness" / "tasks" / task_id / check["stderr_path"]).read_text(
        encoding="utf-8"
    )
    assert "Could not parse command" in stderr


def test_read_verify_freshness_detects_changed_source_after_verify(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    _git_commit_all(tmp_path)

    assert main(
        [
            "task",
            "start",
            "Update app",
            "--root",
            str(tmp_path),
            "--allowed",
            "src/",
        ]
    ) == 0

    (tmp_path / "src" / "app.py").write_text("print('changed')\n", encoding="utf-8")
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0

    fresh = read_verify_freshness(tmp_path, task_id)
    assert fresh["is_stale"] is False

    (tmp_path / "src" / "app.py").write_text("print('changed again')\n", encoding="utf-8")

    stale = read_verify_freshness(tmp_path, task_id)
    assert stale["is_stale"] is True
    assert stale["reason"] == "source_state_changed"


def test_read_verify_freshness_detects_untracked_content_change_after_verify(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git_commit_all(tmp_path)
    (tmp_path / "notes.txt").write_text("v1\n", encoding="utf-8")

    assert main(["task", "start", "Track untracked notes", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0

    fresh = read_verify_freshness(tmp_path, task_id)
    assert fresh["is_stale"] is False

    (tmp_path / "notes.txt").write_text("v2\n", encoding="utf-8")

    stale = read_verify_freshness(tmp_path, task_id)
    assert stale["is_stale"] is True
    assert stale["reason"] == "source_state_changed"


def test_read_verify_freshness_detects_missing_verify_report(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "No verify yet", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)

    freshness = read_verify_freshness(tmp_path, task_id)

    assert freshness["is_stale"] is True
    assert freshness["reason"] == "verify_missing"
    assert freshness["recorded_source_state"] is None


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Codex Harness Tests"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "tests@example.local"], cwd=root, check=True)


def _git_commit_all(root: Path) -> None:
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=root, check=True, capture_output=True)


def _only_task_id(root: Path) -> str:
    task_dirs = list((root / ".codex-harness" / "tasks").iterdir())
    assert len(task_dirs) == 1
    return task_dirs[0].name


def _read_report(root: Path, task_id: str) -> dict[str, object]:
    report_path = root / ".codex-harness" / "tasks" / task_id / "verify.json"
    return json.loads(report_path.read_text(encoding="utf-8"))
