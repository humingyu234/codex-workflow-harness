from __future__ import annotations

from codex_harness.cli import build_parser, main


def test_help_parser_mentions_project_name() -> None:
    parser = build_parser()

    help_text = parser.format_help()

    assert "codex-harness" in help_text
    assert "doctor" in help_text


def test_doctor_command_reports_ok(capsys) -> None:
    exit_code = main(["doctor"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "codex-harness: ok" in captured.out

