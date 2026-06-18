from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_core_harness_docs_exist() -> None:
    expected = [
        "AGENTS.md",
        "docs/workflow.md",
        "docs/task_modes.md",
        "docs/review_process.md",
        "docs/proof_pack.md",
        "docs/resume_brief.md",
        "docs/project_profile.md",
        "docs/recipes.md",
        "docs/zh/workflow_explained.md",
    ]

    for relative in expected:
        assert (ROOT / relative).exists(), relative


def test_templates_exist() -> None:
    expected = [
        "spec.md",
        "plan.md",
        "phase.md",
        "review.md",
        "proof_pack.md",
        "project_profile.md",
    ]

    for name in expected:
        assert (ROOT / "docs" / "templates" / name).exists(), name


def test_recipes_exist() -> None:
    expected = [
        "bugfix.md",
        "feature.md",
        "refactor.md",
        "take-home.md",
        "open-source-pr.md",
    ]

    for name in expected:
        assert (ROOT / "docs" / "recipes" / name).exists(), name


def test_workflow_names_codex_and_proof_boundary() -> None:
    workflow = (ROOT / "docs" / "workflow.md").read_text(encoding="utf-8")

    assert "Codex" in workflow
    assert "Proof Pack" in workflow
    assert "No custom multi-agent runtime" in workflow
