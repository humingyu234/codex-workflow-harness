from __future__ import annotations

import pytest

from codex_harness.cli import build_parser, main


def test_help_parser_mentions_project_name() -> None:
    parser = build_parser()

    help_text = parser.format_help()

    assert "codex-harness" in help_text
    assert "doctor" in help_text
    assert "task" in help_text


def test_task_help_mentions_proof_pack(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["task", "--help"])

    captured = capsys.readouterr()
    assert exc.value.code == 0
    assert "proof-pack" in captured.out
    assert "resume-brief" in captured.out


def test_doctor_command_reports_ok(capsys) -> None:
    exit_code = main(["doctor"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "codex-harness: ok" in captured.out
