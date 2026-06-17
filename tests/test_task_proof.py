from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from codex_harness.cli import main


def test_task_proof_pack_requires_fresh_passing_verify_and_review(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    _git_commit_all(tmp_path)

    assert main(
        [
            "task",
            "start",
            "Ship app update",
            "--root",
            str(tmp_path),
            "--allowed",
            "src/",
            "--check",
            "python3 -c 'print(\"ok\")'",
            "--acceptance",
            "app behavior is updated",
        ]
    ) == 0
    (tmp_path / "src" / "app.py").write_text("print('changed')\n", encoding="utf-8")
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path)]) == 0
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
            ]
        )
        == 0
    )

    assert main(["task", "proof-pack", task_id, "--root", str(tmp_path)]) == 0

    task_dir = tmp_path / ".codex-harness" / "tasks" / task_id
    proof = _read_json(task_dir / "proof-pack.json")
    summary = (task_dir / "proof-pack.md").read_text(encoding="utf-8")

    assert proof["verdict"] == "pass"
    assert proof["task_id"] == task_id
    assert proof["changed_files"] == ["src/app.py"]
    assert proof["verification"]["checks"][0]["exit_code"] == 0
    assert proof["review"]["reviewer"] == "fresh-codex"
    assert "Ship app update" in summary
    assert "src/app.py" in summary
    assert "review.json" in summary


def test_task_proof_pack_blocks_missing_verify(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "No verify", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)

    with pytest.raises(SystemExit):
        main(["task", "proof-pack", task_id, "--root", str(tmp_path)])


def test_task_proof_pack_blocks_failed_verify(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert (
        main(
            [
                "task",
                "start",
                "Failed verify",
                "--root",
                str(tmp_path),
                "--check",
                "python3 -c 'import sys; sys.exit(5)'",
            ]
        )
        == 0
    )
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path)]) == 1
    assert main(["task", "review-brief", task_id, "--root", str(tmp_path)]) == 0
    assert main(["task", "review-record", task_id, "--root", str(tmp_path), "--verdict", "pass"]) == 0

    with pytest.raises(SystemExit):
        main(["task", "proof-pack", task_id, "--root", str(tmp_path)])


def test_task_proof_pack_blocks_missing_review(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "No review", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0

    with pytest.raises(SystemExit):
        main(["task", "proof-pack", task_id, "--root", str(tmp_path)])


def test_task_proof_pack_blocks_non_passing_review(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "Repair needed", "--root", str(tmp_path)]) == 0
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
                "repair",
                "--finding",
                "P1: missing boundary test",
            ]
        )
        == 1
    )

    with pytest.raises(SystemExit):
        main(["task", "proof-pack", task_id, "--root", str(tmp_path)])


def test_task_proof_pack_blocks_stale_review(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    _git_commit_all(tmp_path)

    assert main(["task", "start", "Stale proof", "--root", str(tmp_path), "--allowed", "src/"]) == 0
    (tmp_path / "src" / "app.py").write_text("print('changed')\n", encoding="utf-8")
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0
    assert main(["task", "review-brief", task_id, "--root", str(tmp_path)]) == 0
    assert main(["task", "review-record", task_id, "--root", str(tmp_path), "--verdict", "pass"]) == 0

    (tmp_path / "src" / "app.py").write_text("print('changed again')\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        main(["task", "proof-pack", task_id, "--root", str(tmp_path)])


def test_task_proof_pack_blocks_p0_or_p1_findings_even_when_verdict_passes(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "Suspicious pass", "--root", str(tmp_path)]) == 0
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
                "--finding",
                "P1: accepted with blocking concern",
            ]
        )
        == 0
    )

    with pytest.raises(SystemExit):
        main(["task", "proof-pack", task_id, "--root", str(tmp_path)])


def test_task_proof_pack_allows_p2_findings(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "P2 allowed", "--root", str(tmp_path)]) == 0
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
                "--finding",
                "P2: optional wording cleanup",
            ]
        )
        == 0
    )

    assert main(["task", "proof-pack", task_id, "--root", str(tmp_path)]) == 0


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
