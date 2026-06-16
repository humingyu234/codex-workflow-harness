# Task Modes

Use the lightest mode that still gives enough trust.

## `direct`

Use for:

- explanations
- small docs edits
- obvious one-line fixes
- source reading

Process:

```text
read relevant source -> make the change or answer -> run focused check if needed
```

## `checked`

Use for:

- small bugfixes
- bounded features
- low-risk multi-file edits

Process:

```text
short plan -> implement -> run targeted checks -> summarize evidence
```

## `controlled`

Use for:

- core logic
- public API behavior
- deliverable work
- tests, review, and proof requirements

Process:

```text
task contract -> implement phase -> verify -> review -> proof pack
```

## `council`

Use for:

- unclear architecture
- high uncertainty
- competing implementation strategies
- long-running project work

Process:

```text
spec -> plan -> red-team review -> phase tasks -> controlled delivery
```

