# Codex Harness Roadmap

This roadmap fixes the product direction before more implementation work.

## Positioning

`codex-harness` is a project-level quality and delivery harness for Codex,
Claude Code, and similar coding agents.

It is not an agent runtime.

```text
Codex / Claude Code:
  plan, explore, implement, debug, use loops, use subagents, and continue work

codex-harness:
  record contracts, verify evidence, detect stale artifacts, prepare review,
  build proof packs, and support session handoff
```

The goal is to maximize the coding agent's execution ability while keeping
project boundaries, evidence, review, and delivery trustworthy.

## Design Principles

- Keep `AGENTS.md` short and practical.
- Put detailed rationale and templates in `docs/`.
- Let Codex and Claude Code own the execution loop.
- Use CLI checks for evidence and gates that should not depend on model memory.
- Prefer git state, command exit codes, saved logs, and structured artifacts over summaries.
- Keep small tasks fast and large tasks checkpointed.
- Do not add runtime complexity until the evidence path is dependable.

## Implementation Phases

### Phase 2: Verification Evidence

Make `required_checks` evidence stronger.

Done when each check records command, cwd, start/end time, duration, exit code,
timeout state, and stdout/stderr log paths.

### Phase 3: Source State + Stale Detection

Bind verify, review, and proof artifacts to the source state they observed.

Done when source state includes at least git HEAD, diff hash, untracked hash,
contract hash, and changed files; stale verify/review artifacts cannot be used
as fresh evidence.

### Phase 4: Review Brief + Review Record

Generate clean reviewer input and record structured reviewer output.

Done when `review-brief` can package contract, plan, verify evidence, source
state, diff, and non-goals; `review-record` validates reviewer verdicts and
their reviewed source state.

### Phase 5: Proof Pack

Generate human-readable and machine-readable delivery evidence.

Done when proof pack generation requires fresh passing verify evidence and a
fresh review result without blocking P0/P1 findings.

### Phase 6: Resume Brief

Generate a task handoff for a new Codex/Claude session.

Done when a new session can read the resume brief and know the task goal,
current state, latest evidence, next step, and files to inspect.

### Phase 7: Project Profile + Recipes

Make the harness reusable across projects and task types.

Done when the repo has a project profile template and task recipes for bugfix,
feature, refactor, take-home, and open-source PR workflows.

### Phase 8: Lightweight Workflow Status

Track task status without building a heavy runtime.

Done when the harness can report the current task state and automatically mark
fact-based transitions such as passing verify, stale evidence, and blocking
review findings.

## Deferred

These may be useful later, but they are not part of the near-term path:

```text
LangGraph orchestration
custom multi-agent runtime
auto-repair loop
large dashboard
complex memory database
background worker scheduler
automatic worktree isolation
subagent runtime orchestration
```

They are deferred because Codex and Claude Code already provide strong planning,
looping, hooks, subagents, resume, and automation primitives. This project
should complement those capabilities instead of rebuilding them.
