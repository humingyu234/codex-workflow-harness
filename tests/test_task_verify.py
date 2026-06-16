from __future__ import annotations

import json
import subprocess
from pathlib import Path

from codex_harness.cli import main


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
