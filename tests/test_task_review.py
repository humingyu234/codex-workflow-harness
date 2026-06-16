from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from codex_harness.cli import main


def test_task_review_brief_packages_contract_verify_and_diff(tmp_path: Path) -> None:
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
            "--acceptance",
            "app output is updated",
            "--non-goal",
            "no dashboard",
        ]
    ) == 0
    (tmp_path / "src" / "app.py").write_text("print('changed')\n", encoding="utf-8")
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path)]) == 0

    assert main(["task", "review-brief", task_id, "--root", str(tmp_path)]) == 0

    task_dir = tmp_path / ".codex-harness" / "tasks" / task_id
    metadata = _read_json(task_dir / "review-brief.json")
    brief = (task_dir / "review-brief.md").read_text(encoding="utf-8")
    diff = (task_dir / "review-diff.patch").read_text(encoding="utf-8")

    assert metadata["readiness"] == "ready"
    assert metadata["verify_freshness"]["is_stale"] is False
    assert metadata["source_state"]["changed_files"] == ["src/app.py"]
    assert "You are an independent reviewer" in brief
    assert "Update app" in brief
    assert "app output is updated" in brief
    assert "no dashboard" in brief
    assert "print('changed')" in brief
    assert "print('changed')" in diff


def test_task_review_record_writes_structured_result_for_current_brief(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    _git_commit_all(tmp_path)

    assert main(["task", "start", "Review app", "--root", str(tmp_path), "--allowed", "src/"]) == 0
    (tmp_path / "src" / "app.py").write_text("print('changed')\n", encoding="utf-8")
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0
    assert main(["task", "review-brief", task_id, "--root", str(tmp_path)]) == 0

    assert (
        main(
            [
                "task",
                "review-record",
                task_id,
                "--root",
                str(tmp_path),
                "--verdict",
                "pass",
                "--reviewer",
                "fresh-codex",
                "--residual-risk",
                "manual reviewer did not run performance tests",
            ]
        )
        == 0
    )

    task_dir = tmp_path / ".codex-harness" / "tasks" / task_id
    brief = _read_json(task_dir / "review-brief.json")
    record = _read_json(task_dir / "review.json")
    summary = (task_dir / "review.md").read_text(encoding="utf-8")

    assert record["verdict"] == "pass"
    assert record["reviewer"] == "fresh-codex"
    assert record["reviewed_source_state"] == brief["source_state"]
    assert "manual reviewer did not run performance tests" in summary


def test_task_review_record_requires_findings_for_repair_or_block(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "Needs review", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0
    assert main(["task", "review-brief", task_id, "--root", str(tmp_path)]) == 0

    with pytest.raises(SystemExit):
        main(["task", "review-record", task_id, "--root", str(tmp_path), "--verdict", "repair"])


def test_task_review_record_rejects_stale_review_brief(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    _git_commit_all(tmp_path)

    assert main(["task", "start", "Review stale app", "--root", str(tmp_path), "--allowed", "src/"]) == 0
    (tmp_path / "src" / "app.py").write_text("print('changed')\n", encoding="utf-8")
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0
    assert main(["task", "review-brief", task_id, "--root", str(tmp_path)]) == 0

    (tmp_path / "src" / "app.py").write_text("print('changed again')\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        main(["task", "review-record", task_id, "--root", str(tmp_path), "--verdict", "pass"])


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


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
