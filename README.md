# Codex Workflow Harness

A lightweight workflow, evidence, review, and proof harness for Codex-first
software development.

Codex and Claude Code are strong at planning, coding, debugging, and iterating.
This project does not replace that loop. It adds the missing project discipline
around it:

```text
task boundary -> real verification -> fresh review -> proof pack -> resume handoff
```

Use it when AI-assisted work needs to be reviewable, repeatable, and safe to
handoff instead of just "the agent said it is done."

## Why This Exists

AI coding agents can move fast, but fast work still needs trustworthy delivery:

- What was the task supposed to change?
- Which files were allowed or denied?
- Did the required checks actually run?
- Does the review match the current source state?
- Is the final proof pack based on fresh evidence?
- Can a new session continue without relying on chat history?

`codex-harness` answers those questions with small CLI artifacts stored in the
project under `.codex-harness/`.

## What It Does

| Need | Harness Support |
| --- | --- |
| Keep task scope explicit | `task start` writes a contract and git baseline. |
| Verify with real evidence | `task verify` records checks, logs, changed files, and source state. |
| Avoid stale reviews | Review records are bound to the source state they reviewed. |
| Prepare clean reviewer context | `task review-brief` creates a fresh-context packet. |
| Prove delivery | `task proof-pack` requires fresh passing verify and review. |
| Resume cleanly | `task resume-brief` writes a handoff for a new session. |
| See current state | `task status` reports the next required action. |

## Quickstart

Install locally while developing:

```bash
pip install -e .
```

Initialize harness assets in a project:

```bash
codex-harness project init --name "My Project"
```

Start a controlled task:

```bash
codex-harness task start "Add worker doctor" \
  --mode controlled \
  --allowed src/ \
  --denied secrets/ \
  --check "python -m pytest -q" \
  --acceptance "doctor reports worker readiness"
```

Let Codex or Claude Code implement freely. Then verify and review:

```bash
codex-harness task verify
codex-harness task review-brief
codex-harness task review-record --verdict pass --reviewer fresh-codex
codex-harness task proof-pack
codex-harness task status
```

For handoff to a fresh session:

```bash
codex-harness task resume-brief
```

## Example Flow

```text
1. User asks for a risky multi-file change.
2. Codex creates or follows a plan and implements the change.
3. codex-harness checks the agreed scope and required commands.
4. A fresh reviewer gets review-brief.md, not the full implementation chat.
5. proof-pack.md is generated only if verification and review are fresh.
6. resume-brief.md tells the next session exactly where to continue.
```

## When To Use It

Use the harness for:

- multi-file changes
- take-home projects
- open-source PRs
- core logic
- externally delivered work
- changes where review/proof matters

Skip it for:

- quick explanations
- tiny docs edits
- throwaway experiments

The goal is not bureaucracy. The goal is to keep Codex fast while making the
delivery trustworthy.

## Main Commands

```bash
codex-harness doctor
codex-harness project init --name "My Project"
codex-harness task start "Goal" --mode controlled --check "python -m pytest -q"
codex-harness task verify
codex-harness task review-brief
codex-harness task review-record --verdict pass --reviewer fresh-codex
codex-harness task proof-pack
codex-harness task resume-brief
codex-harness task status
```

## Generated Artifacts

Each task is stored under:

```text
.codex-harness/tasks/<task-id>/
```

Important files:

| File | Purpose |
| --- | --- |
| `contract.json` / `contract.md` | Task goal, allowed files, denied files, checks, acceptance criteria. |
| `baseline.json` | Git state captured before implementation. |
| `verify.json` / `verify.md` | Verification result, changed files, check logs, source state. |
| `review-brief.md` | Fresh-context packet for an independent reviewer. |
| `review.json` / `review.md` | Structured review verdict and findings. |
| `proof-pack.md` | Final delivery evidence for humans. |
| `resume-brief.md` | Handoff packet for a new Codex or Claude Code session. |

## Project Docs

- [AGENTS.md](AGENTS.md) - short operating contract for coding agents.
- [docs/workflow.md](docs/workflow.md) - canonical workflow.
- [docs/task_modes.md](docs/task_modes.md) - direct / checked / controlled / council routing.
- [docs/review_process.md](docs/review_process.md) - review brief and review record rules.
- [docs/proof_pack.md](docs/proof_pack.md) - proof pack expectations.
- [docs/zh/workflow_explained.md](docs/zh/workflow_explained.md) - Chinese walkthrough.

## Development

```bash
python -m pytest -q
python -m codex_harness --help
```

Or after editable install:

```bash
pip install -e .
codex-harness --help
```

Current test status:

```text
43 passed
```
