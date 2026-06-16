from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .tasks import TaskStartRequest, start_task
from .verification import TaskVerifyRequest, verify_task


TASK_MODES = ("direct", "checked", "controlled", "council")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-harness",
        description="Codex-first delivery harness for task boundaries, verification, and proof packs.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("doctor", help="Check that the harness CLI is installed correctly.")

    task_parser = subparsers.add_parser("task", help="Manage task contracts and delivery artifacts.")
    task_subparsers = task_parser.add_subparsers(dest="task_command")
    task_start = task_subparsers.add_parser("start", help="Start a task and write its contract files.")
    task_start.add_argument("goal", help="Short task goal or raw request.")
    task_start.add_argument(
        "--mode",
        choices=TASK_MODES,
        default="controlled",
        help="Task mode. Defaults to controlled.",
    )
    task_start.add_argument(
        "--root",
        default=".",
        help="Target project root. Defaults to the current directory.",
    )
    task_start.add_argument(
        "--allowed",
        action="append",
        default=[],
        help="File or directory the task may modify. Repeat as needed.",
    )
    task_start.add_argument(
        "--denied",
        action="append",
        default=[],
        help="File or directory the task must not modify. Repeat as needed.",
    )
    task_start.add_argument(
        "--check",
        action="append",
        default=[],
        help="Required verification command. Repeat as needed.",
    )
    task_start.add_argument(
        "--acceptance",
        action="append",
        default=[],
        help="Acceptance criterion. Repeat as needed.",
    )
    task_start.add_argument(
        "--non-goal",
        action="append",
        default=[],
        help="Explicit non-goal. Repeat as needed.",
    )
    task_verify = task_subparsers.add_parser("verify", help="Verify a task contract against git and checks.")
    task_verify.add_argument("task_id", nargs="?", help="Task id. Defaults to the latest task.")
    task_verify.add_argument(
        "--root",
        default=".",
        help="Target project root. Defaults to the current directory.",
    )
    task_verify.add_argument(
        "--no-checks",
        action="store_true",
        help="Do not run required checks; only verify git and scope.",
    )
    task_verify.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout per required check in seconds.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        print("codex-harness: ok")
        return 0

    if args.command == "task" and args.task_command == "start":
        result = start_task(
            TaskStartRequest(
                goal=args.goal,
                mode=args.mode,
                root=Path(args.root),
                allowed_files=tuple(args.allowed),
                denied_files=tuple(args.denied),
                required_checks=tuple(args.check),
                acceptance_criteria=tuple(args.acceptance),
                non_goals=tuple(args.non_goal),
            )
        )
        print(f"Task started: {result.task_id}")
        print(f"Task dir: {result.task_dir}")
        print(f"Contract: {result.contract_path}")
        print(f"Baseline: {result.baseline_path}")
        print("Next: fill plan.md, implement one phase, then run verification.")
        return 0

    if args.command == "task" and args.task_command == "verify":
        try:
            result = verify_task(
                TaskVerifyRequest(
                    root=Path(args.root),
                    task_id=args.task_id,
                    run_checks=not args.no_checks,
                    check_timeout=args.timeout,
                )
            )
        except FileNotFoundError as exc:
            parser.error(str(exc))
        print(f"Verification: {result.verdict}")
        print(f"Task: {result.task_id}")
        print(f"Report: {result.report_path}")
        print(f"Summary: {result.summary_path}")
        return 0 if result.verdict == "pass" else 1

    parser.print_help()
    return 0
