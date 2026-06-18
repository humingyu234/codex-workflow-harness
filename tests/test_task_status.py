from __future__ import annotations

import subprocess
from pathlib import Path

from codex_harness.cli import main


def test_task_status_reports_needs_verify_before_verify_runs(tmp_path: Path, capsys) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "Status no verify", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)

    assert main(["task", "status", task_id, "--root", str(tmp_path)]) == 0

    captured = capsys.readouterr()
    assert "Status: needs_verify" in captured.out
    assert "task verify" in captured.out
    assert "Verify: missing" in captured.out


def test_task_status_reports_needs_review_after_passing_verify(tmp_path: Path, capsys) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "Status needs review", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0

    assert main(["task", "status", task_id, "--root", str(tmp_path)]) == 0

    captured = capsys.readouterr()
    assert "Status: needs_review" in captured.out
    assert "Verify: pass (fresh)" in captured.out
    assert "Review: missing" in captured.out


def test_task_status_reports_ready_for_proof_pack_after_passing_review(tmp_path: Path, capsys) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "Status ready proof", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0
    assert main(["task", "review-brief", task_id, "--root", str(tmp_path)]) == 0
    assert main(["task", "review-record", task_id, "--root", str(tmp_path), "--verdict", "pass"]) == 0

    assert main(["task", "status", task_id, "--root", str(tmp_path)]) == 0

    captured = capsys.readouterr()
    assert "Status: ready_for_proof_pack" in captured.out
    assert "Review: pass (fresh)" in captured.out
    assert "Proof: missing" in captured.out


def test_task_status_reports_ready_for_delivery_after_proof_pack(tmp_path: Path, capsys) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "Status delivered", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0
    assert main(["task", "review-brief", task_id, "--root", str(tmp_path)]) == 0
    assert main(["task", "review-record", task_id, "--root", str(tmp_path), "--verdict", "pass"]) == 0
    assert main(["task", "proof-pack", task_id, "--root", str(tmp_path)]) == 0

    assert main(["task", "status", task_id, "--root", str(tmp_path)]) == 0

    captured = capsys.readouterr()
    assert "Status: ready_for_delivery" in captured.out
    assert "Proof: pass (fresh)" in captured.out


def test_task_status_reports_needs_reverify_when_source_changes(tmp_path: Path, capsys) -> None:
    _git_init(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    _git_commit_all(tmp_path)

    assert main(["task", "start", "Status stale", "--root", str(tmp_path), "--allowed", "src/"]) == 0
    (tmp_path / "src" / "app.py").write_text("print('changed')\n", encoding="utf-8")
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0

    (tmp_path / "src" / "app.py").write_text("print('changed again')\n", encoding="utf-8")

    assert main(["task", "status", task_id, "--root", str(tmp_path)]) == 0

    captured = capsys.readouterr()
    assert "Status: needs_reverify" in captured.out
    assert "Verify: pass (stale)" in captured.out
    assert "- src/app.py" in captured.out


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
