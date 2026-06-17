# Task Modes

This file only answers one question:

```text
How much process does this task need?
```

The full workflow lives in `docs/workflow.md`.

| Mode | Use When | Minimum Discipline |
| --- | --- | --- |
| `direct` | explanation, source reading, tiny docs, obvious one-line fixes | Work directly; run a focused check if files changed. |
| `checked` | bounded bugfix or small feature with clear tests | Make a short plan, implement, run targeted checks, summarize evidence. |
| `controlled` | core logic, public API behavior, multi-file delivery, reviewer/proof needed | Start a task contract, implement one phase, verify, review, then package proof. |
| `council` | unclear architecture, high uncertainty, competing designs, long multi-phase work | Do spec and red-team planning first, then deliver through `controlled` phases. |

## Escalation Rule

Move up one mode when the task touches:

- trust/evidence/review/proof logic
- files with broad project impact
- external delivery or take-home work
- unclear requirements
- changes that are hard to verify by inspection
