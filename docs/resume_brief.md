# Resume Brief

A resume brief is the task handoff for a fresh Codex or Claude Code session.

It should answer:

```text
What is the task?
What is the current status?
What evidence exists?
What changed files matter?
What should the next session inspect first?
What is the next concrete step?
```

Generate it with:

```bash
codex-harness task resume-brief
```

Unlike `proof-pack`, this command is not a delivery gate. It should work even
when verification or review is missing, because unfinished tasks still need
clean handoff.
