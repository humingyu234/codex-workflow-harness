# Codex Harness Operating Contract

This repository builds a Codex-first quality and delivery harness. Keep this
file short; put detailed rationale in `docs/roadmap.md`.

## Default Posture

```text
Codex or Claude Code plans, explores, codes, debugs, and loops.
codex-harness records boundaries, verifies evidence, prepares review, builds proof, and supports handoff.
```

Do not turn this project into an autonomous multi-agent runtime. The harness
should maximize existing coding agents, not replace or constrain their core
execution loop.

## Task Modes

| Mode | Use When | Process |
| --- | --- | --- |
| `direct` | explanation, tiny edits, low-risk docs | Work directly and run a focused check if files changed. |
| `checked` | bounded bugfix or small feature | Let Codex implement, then run targeted checks. |
| `controlled` | multi-file, core logic, external delivery | Create a task contract, verify evidence, review, and proof pack. |
| `council` | unclear architecture or high uncertainty | Do spec and red-team planning before controlled delivery. |

## Main Path

```text
spec -> plan -> phase build -> verify evidence -> stale check -> review -> proof pack -> resume brief
```

For large tasks, do one phase at a time. Do not bundle unrelated cleanup,
rewrites, and new features into the same phase.

## Evidence Rules

- Prefer git state, check exit codes, saved logs, and structured artifacts over agent summaries.
- Treat model-written summaries as narrative, not observed evidence.
- Old verify/review artifacts must not be reused after relevant source changes.
- Reviewer findings must be concrete: severity, file/path, evidence, and risk.
- Proof packs must be honest about limitations and linked evidence.

## Frozen By Default

Do not add these in the first version:

```text
multi-agent runtime
LangGraph orchestration
auto-repair loop
complex memory system
dashboard
background worker scheduler
```
