# Codex Harness

Codex Harness is a lightweight delivery harness for AI-native software work.
It does not replace Codex or Claude Code. It gives them a repeatable delivery
frame: task boundaries, checks, review handoff, and proof artifacts.

## Phase 0 Scope

This repository currently contains the project skeleton plus the first workflow
documents:

- Python package layout
- CLI entrypoint
- Test harness
- Minimal project documentation
- Codex-first delivery workflow
- Reusable task templates

The first usable workflow is being built in small phases:

```text
init -> task start -> verify -> review-brief -> review-result -> proof-pack
```

Current CLI commands:

```bash
codex-harness doctor
codex-harness project init --name "My Project"
codex-harness task start "Add worker doctor" \
  --mode controlled \
  --allowed src/ \
  --denied secrets/ \
  --check "python -m pytest -q" \
  --acceptance "doctor reports worker readiness"
codex-harness task verify
codex-harness task review-brief
codex-harness task review-record --verdict pass --reviewer fresh-codex
codex-harness task proof-pack
codex-harness task resume-brief
codex-harness task status
```

`task start` creates a task directory under `.codex-harness/tasks/` with a
contract, git baseline, spec, plan, first phase handoff, and task log.

`project init` writes `.codex-harness/project-profile.md` and starter recipes
for bugfix, feature, refactor, take-home, and open-source PR workflows.

`task verify` compares the current git status with the task baseline, checks
allowed/denied file boundaries, runs required checks, and writes `verify.json`
plus `verify.md` into the task directory.

`task review-brief` writes a fresh-context reviewer packet with the task
contract, verification state, source state, and git diff.

`task review-record` records the independent reviewer verdict and binds it to
the source state captured by the review brief.

`task proof-pack` generates final delivery artifacts only when verification is
fresh and passing and the review record is fresh and passing without blocking
P0/P1 findings.

`task resume-brief` generates a fresh-session handoff with current status,
latest evidence, changed files, files to inspect first, and the recommended
next step.

`task status` prints the current fact-based workflow state, such as
`needs_verify`, `needs_review`, `needs_reverify`, `ready_for_proof_pack`, or
`ready_for_delivery`.

## Development

```bash
python -m pytest -q
python -m codex_harness --help
```

Or, after editable install:

```bash
pip install -e .
codex-harness --help
```

## Core Workflow

Use Codex or Claude Code for implementation. Use this harness for delivery
discipline:

```text
spec -> plan -> phase build -> verify -> review -> proof pack
```

Small tasks should stay lightweight. Large or risky tasks should use task
contracts, checks, review handoff, and proof artifacts.

Start with:

- [AGENTS.md](AGENTS.md)
- [docs/workflow.md](docs/workflow.md)
- [docs/task_modes.md](docs/task_modes.md)
- [docs/zh/workflow_explained.md](docs/zh/workflow_explained.md)
