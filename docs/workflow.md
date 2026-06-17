# Codex-First Workflow

This is the main user-facing workflow for `codex-harness`.

The harness does not replace Codex or Claude Code. It gives them a trusted
delivery frame: task boundaries, executable checks, stale evidence detection,
review handoff, and proof artifacts.

## Document Map

| File | Purpose |
| --- | --- |
| `AGENTS.md` | Short operating contract for coding agents in this repo. |
| `docs/roadmap.md` | Product direction, implementation phases, and deferred ideas. |
| `docs/workflow.md` | This file: the canonical workflow for using the harness. |
| `docs/task_modes.md` | Quick routing guide for `direct`, `checked`, `controlled`, and `council`. |
| `docs/review_process.md` | Independent reviewer input, severity rules, and review recording. |
| `docs/proof_pack.md` | What final delivery evidence should contain. |
| `docs/templates/` | Reusable artifact skeletons for spec, plan, phase, review, and proof pack. |
| `docs/zh/workflow_explained.md` | Chinese explanation of the same design for learning and review. |

## Rule Of Thumb

```text
Small tasks need speed.
Large tasks need checkpoints.
External delivery needs proof.
```

Use `docs/task_modes.md` only to choose the mode. Use this file for the actual
end-to-end flow.

## Controlled Delivery Flow

Use this path for multi-file, risky, reviewable, or externally delivered work.

### 1. Clarify

Turn the raw request into a short spec and acceptance criteria. For uncertain
work, ask Codex or Claude to explore first, then write the spec.

### 2. Plan

Split the work into small phases. Each phase should have:

```text
objective
allowed files
denied files
required checks
done criteria
non-goals
```

### 3. Start The Task

Record the task contract and git baseline.

```bash
codex-harness task start "<goal>" \
  --mode controlled \
  --allowed src/ \
  --check "python -m pytest -q"
```

### 4. Build One Phase

Let Codex or Claude Code implement the phase freely. Do not use the harness to
micromanage the implementation loop.

### 5. Verify

Run the harness verification after meaningful changes.

```bash
codex-harness task verify
```

Verification records source state, changed files, command exit codes, timings,
and stdout/stderr logs.

### 6. Review

Generate a fresh-context review packet.

```bash
codex-harness task review-brief
```

Give the generated brief to an independent reviewer. Record the result:

```bash
codex-harness task review-record --verdict pass --reviewer fresh-codex
```

If review returns P0/P1 findings, repair only those findings, then verify and
review again.

### 7. Proof Pack

For delivery work, generate a proof pack once the command exists. The proof pack
should require fresh passing verification and a fresh passing review.

## Non-Goals

These belong in `docs/roadmap.md`, but the short version is:

- No custom multi-agent runtime.
- No hidden automatic rewrite loop.
- No complex memory database in the first version.
- No replacement for normal tests, CI, or code review.
