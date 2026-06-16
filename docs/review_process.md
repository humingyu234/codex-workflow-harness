# Review Process

The reviewer should be independent from the implementation context.

## Inputs

- task contract
- acceptance criteria
- verification output
- git diff or review patch
- known risks and non-goals

## Reviewer Instructions

```text
You are an independent reviewer.
Do not rewrite the implementation.
Review whether the diff satisfies the task contract.
Prioritize correctness, safety, scope, tests, and maintainability.
Report findings as P0/P1/P2.
```

## Severity

| Severity | Meaning |
| --- | --- |
| `P0` | Must fix before delivery. Correctness, data loss, security, or failing acceptance criteria. |
| `P1` | Should fix before delivery. Reliability, missing boundary tests, confusing design, or maintainability risk. |
| `P2` | Follow-up improvement. Not blocking current delivery. |

## Output Shape

```text
Verdict: pass | repair | block

Findings:
- Severity:
  Category:
  File/Location:
  Evidence:
  Why it matters:
  Suggested fix:

Residual risk:
```

