# Proof Pack

A proof pack is the final human-readable delivery artifact for a task.

It should let a reviewer understand what happened without reading the whole
chat history.

## Required Sections

```text
Task
Scope
Implementation Summary
Changed Files
Verification
Review Findings
Known Limitations
How To Run
Evidence Paths
```

## Evidence Standard

Use observed evidence:

- git diff
- check command and exit code
- review findings
- generated artifacts

Do not treat an agent-written summary as proof by itself.

