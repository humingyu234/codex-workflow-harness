# Project Profile

A project profile is the short, project-specific memory that Codex or Claude
Code should read before a serious task.

Generate it with:

```bash
codex-harness project init
```

This writes:

```text
.codex-harness/project-profile.md
.codex-harness/recipes/
```

The profile should record:

```text
stack
important paths
standard checks
protected paths
delivery standard
project notes
```

It is not a memory database. It is a small project card that keeps each new
session from rediscovering basic project facts.
