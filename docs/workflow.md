# Codex-First Delivery Workflow

This harness exists to make AI-assisted engineering repeatable and reviewable.
It does not replace Codex or Claude Code.

## Large Task Flow

```text
1. Intake
   Capture the raw request, target project, constraints, and deadline.

2. Spec
   Turn the request into a short specification with acceptance criteria.

3. Plan
   Split the work into phases with clear file boundaries and checks.

4. Task Start
   Record task goal, allowed files, denied files, required checks, and git baseline.

   ```bash
   codex-harness task start "<goal>" \
     --mode controlled \
     --allowed src/ \
     --check "python -m pytest -q"
   ```

5. Phase Build
   Let Codex or Claude Code implement one phase only.

6. Verify
   Check git diff, scope boundaries, denied files, and required checks.

   ```bash
   codex-harness task verify
   ```

   This writes `verify.json` and `verify.md` into the task directory.

7. Review
   Give a fresh reviewer the task contract, diff, and verification output.

8. Repair
   Fix only P0/P1 reviewer findings, then verify again.

9. Proof Pack
   Generate a human-readable delivery packet.
```

## Rule Of Thumb

```text
Small tasks need speed.
Large tasks need checkpoints.
External delivery needs proof.
```

## Non-Goals

- No custom multi-agent runtime.
- No hidden automatic rewrite loop.
- No complex memory database in the first version.
- No replacement for normal tests, CI, or code review.
