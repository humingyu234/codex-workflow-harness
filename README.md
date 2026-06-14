# Codex Harness

Codex Harness is a lightweight delivery harness for AI-native software work.
It does not replace Codex or Claude Code. It gives them a repeatable delivery
frame: task boundaries, checks, review handoff, and proof artifacts.

## Phase 0 Scope

This repository currently contains only the project skeleton:

- Python package layout
- CLI entrypoint
- Test harness
- Minimal project documentation

The first usable workflow will be added in later phases:

```text
init -> task start -> verify -> review-brief -> review-result -> proof-pack
```

## Development

```bash
python -m pytest -q
python -m codex_harness --help
```

Or, after editable install:

```bash
pip install -e .
codex-harness --help
```

