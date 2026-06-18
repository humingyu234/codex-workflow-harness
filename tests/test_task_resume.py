from __future__ import annotations

import json
import subprocess
from pathlib import Path

from codex_harness.cli import main


def test_task_resume_brief_reports_needs_verify_before_verify_runs(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "Resume no verify", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)

    assert main(["task", "resume-brief", task_id, "--root", str(tmp_path)]) == 0

    task_dir = tmp_path / ".codex-harness" / "tasks" / task_id
    resume = _read_json(task_dir / "resume-brief.json")
    brief = (task_dir / "resume-brief.md").read_text(encoding="utf-8")

    assert resume["status"] == "needs_verify"
    assert "task verify" in resume["next_step"]
    assert "Resume no verify" in brief
    assert "contract.md" in resume["files_to_inspect"]


def test_task_resume_brief_reports_needs_review_after_passing_verify(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "Resume needs review", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0

    assert main(["task", "resume-brief", task_id, "--root", str(tmp_path)]) == 0

    resume = _read_json(tmp_path / ".codex-harness" / "tasks" / task_id / "resume-brief.json")
    assert resume["status"] == "needs_review"
    assert "review-brief" in resume["next_step"]
    assert resume["verify"]["verdict"] == "pass"
    assert resume["verify"]["is_stale"] is False


def test_task_resume_brief_reports_ready_for_proof_pack_after_passing_review(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "Resume ready proof", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0
    assert main(["task", "review-brief", task_id, "--root", str(tmp_path)]) == 0
    assert main(["task", "review-record", task_id, "--root", str(tmp_path), "--verdict", "pass"]) == 0

    assert main(["task", "resume-brief", task_id, "--root", str(tmp_path)]) == 0

    resume = _read_json(tmp_path / ".codex-harness" / "tasks" / task_id / "resume-brief.json")
    assert resume["status"] == "ready_for_proof_pack"
    assert "proof-pack" in resume["next_step"]
    assert resume["review"]["verdict"] == "pass"


def test_task_resume_brief_reports_ready_for_delivery_after_proof_pack(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "Resume delivered", "--root", str(tmp_path)]) == 0
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0
    assert main(["task", "review-brief", task_id, "--root", str(tmp_path)]) == 0
    assert main(["task", "review-record", task_id, "--root", str(tmp_path), "--verdict", "pass"]) == 0
    assert main(["task", "proof-pack", task_id, "--root", str(tmp_path)]) == 0

    assert main(["task", "resume-brief", task_id, "--root", str(tmp_path)]) == 0

    resume = _read_json(tmp_path / ".codex-harness" / "tasks" / task_id / "resume-brief.json")
    assert resume["status"] == "ready_for_delivery"
    assert "proof-pack.md" in resume["next_step"]
    assert "proof-pack.md" in resume["files_to_inspect"]


def test_task_resume_brief_reports_needs_reverify_when_source_changes(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    _git_commit_all(tmp_path)

    assert main(["task", "start", "Resume stale", "--root", str(tmp_path), "--allowed", "src/"]) == 0
    (tmp_path / "src" / "app.py").write_text("print('changed')\n", encoding="utf-8")
    task_id = _only_task_id(tmp_path)
    assert main(["task", "verify", task_id, "--root", str(tmp_path), "--no-checks"]) == 0

    (tmp_path / "src" / "app.py").write_text("print('changed again')\n", encoding="utf-8")

    assert main(["task", "resume-brief", task_id, "--root", str(tmp_path)]) == 0

    resume = _read_json(tmp_path / ".codex-harness" / "tasks" / task_id / "resume-brief.json")
    assert resume["status"] == "needs_reverify"
    assert resume["verify"]["is_stale"] is True
    assert "src/app.py" in resume["changed_files"]


def test_task_resume_brief_reports_needs_repair_for_repair_review(tmp_path: Path) -> None:
    _git_init(tmp_path)
    assert main(["task", "start", "Resume repair", "--root", str(tmp_path)]) == 0
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
                "P1: missing edge test",
            ]
        )
        == 1
    )

    assert main(["task", "resume-brief", task_id, "--root", str(tmp_path)]) == 0

    resume = _read_json(tmp_path / ".codex-harness" / "tasks" / task_id / "resume-brief.json")
    assert resume["status"] == "needs_repair"
    assert "P1: missing edge test" in resume["review"]["findings"]


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
