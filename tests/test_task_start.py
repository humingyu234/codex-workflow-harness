from __future__ import annotations

import json
from pathlib import Path

from codex_harness.cli import main


def test_task_start_writes_contract_and_artifacts(tmp_path: Path, capsys) -> None:
    exit_code = main(
        [
            "task",
            "start",
            "Add worker doctor",
            "--root",
            str(tmp_path),
            "--mode",
            "controlled",
            "--allowed",
            "src/",
            "--denied",
            "secrets/",
            "--check",
            "python -m pytest -q",
            "--acceptance",
            "doctor reports worker readiness",
            "--non-goal",
            "no dashboard",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Task started:" in captured.out

    task_root = tmp_path / ".codex-harness" / "tasks"
    task_dirs = list(task_root.iterdir())
    assert len(task_dirs) == 1

    task_dir = task_dirs[0]
    contract = json.loads((task_dir / "contract.json").read_text(encoding="utf-8"))
    baseline = json.loads((task_dir / "baseline.json").read_text(encoding="utf-8"))

    assert contract["task_id"] == task_dir.name
    assert contract["goal"] == "Add worker doctor"
    assert contract["mode"] == "controlled"
    assert contract["allowed_files"] == ["src/"]
    assert contract["denied_files"] == ["secrets/"]
    assert contract["required_checks"] == ["python -m pytest -q"]
    assert contract["acceptance_criteria"] == ["doctor reports worker readiness"]
    assert contract["non_goals"] == ["no dashboard"]
    assert baseline["schema_version"] == 1

    assert (task_dir / "contract.md").exists()
    assert (task_dir / "spec.md").exists()
    assert (task_dir / "plan.md").exists()
    assert (task_dir / "phases" / "phase-001.md").exists()
    assert (task_dir / "log.md").exists()


def test_task_start_does_not_overwrite_existing_task(tmp_path: Path) -> None:
    args = [
        "task",
        "start",
        "Same goal",
        "--root",
        str(tmp_path),
    ]

    assert main(args) == 0
    assert main(args) == 0

    task_dirs = sorted((tmp_path / ".codex-harness" / "tasks").iterdir())
    assert len(task_dirs) == 2
    assert task_dirs[0].name != task_dirs[1].name

    for task_dir in task_dirs:
        contract = json.loads((task_dir / "contract.json").read_text(encoding="utf-8"))
        assert contract["task_id"] == task_dir.name
