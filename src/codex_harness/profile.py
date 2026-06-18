from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .tasks import HARNESS_DIR


RECIPE_NAMES = ("bugfix", "feature", "refactor", "take-home", "open-source-pr")


@dataclass(frozen=True)
class ProjectInitRequest:
    root: Path
    name: str | None = None
    force: bool = False


@dataclass(frozen=True)
class ProjectInitResult:
    root: Path
    profile_path: Path
    recipe_paths: tuple[Path, ...]
    skipped_paths: tuple[Path, ...]


def init_project_profile(request: ProjectInitRequest) -> ProjectInitResult:
    root = request.root.resolve()
    harness_dir = root / HARNESS_DIR
    recipes_dir = harness_dir / "recipes"
    harness_dir.mkdir(parents=True, exist_ok=True)
    recipes_dir.mkdir(parents=True, exist_ok=True)

    project_name = request.name or root.name
    skipped: list[Path] = []
    written_recipes: list[Path] = []

    profile_path = harness_dir / "project-profile.md"
    if _write_if_needed(profile_path, _render_project_profile(project_name), force=request.force):
        pass
    else:
        skipped.append(profile_path)

    for recipe_name in RECIPE_NAMES:
        recipe_path = recipes_dir / f"{recipe_name}.md"
        if _write_if_needed(recipe_path, _render_recipe(recipe_name), force=request.force):
            written_recipes.append(recipe_path)
        else:
            skipped.append(recipe_path)

    return ProjectInitResult(
        root=root,
        profile_path=profile_path,
        recipe_paths=tuple(written_recipes),
        skipped_paths=tuple(skipped),
    )


def _write_if_needed(path: Path, content: str, *, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _render_project_profile(project_name: str) -> str:
    return "\n".join(
        [
            "# Project Profile",
            "",
            f"Project: {project_name}",
            "",
            "Use this file to teach Codex or Claude Code the project-specific rules before a task starts.",
            "",
            "## Stack",
            "",
            "- Language/runtime:",
            "- Package manager:",
            "- Framework:",
            "",
            "## Important Paths",
            "",
            "- Source:",
            "- Tests:",
            "- Docs:",
            "- Config:",
            "",
            "## Standard Checks",
            "",
            "```bash",
            "# Replace with this project's real checks.",
            "# Examples: pytest -q, go test ./..., npm test, mvn test",
            "```",
            "",
            "## Protected Paths",
            "",
            "- .env",
            "- secrets/",
            "",
            "## Delivery Standard",
            "",
            "- Prefer small phases for risky work.",
            "- Use real tests, git diff, review, and proof artifacts as evidence.",
            "- Do not treat model summaries as proof.",
            "",
            "## Project Notes",
            "",
            "- ",
            "",
        ]
    )


def _render_recipe(name: str) -> str:
    recipes = {
        "bugfix": _bugfix_recipe,
        "feature": _feature_recipe,
        "refactor": _refactor_recipe,
        "take-home": _take_home_recipe,
        "open-source-pr": _open_source_pr_recipe,
    }
    return recipes[name]()


def _bugfix_recipe() -> str:
    return _recipe(
        title="Bugfix Recipe",
        mode="checked or controlled",
        use_when="A behavior is wrong and the intended behavior is known.",
        phases=[
            "Reproduce the bug or identify the failing path.",
            "Add or identify a regression check.",
            "Make the smallest fix.",
            "Run targeted checks and record evidence.",
        ],
        proof="Show the failing behavior is fixed without changing unrelated behavior.",
    )


def _feature_recipe() -> str:
    return _recipe(
        title="Feature Recipe",
        mode="controlled",
        use_when="A new behavior or user-facing capability is added.",
        phases=[
            "Write acceptance criteria.",
            "Split the feature into one narrow phase.",
            "Implement the phase.",
            "Verify with tests and review scope.",
        ],
        proof="Show acceptance criteria, changed files, checks, and reviewer result.",
    )


def _refactor_recipe() -> str:
    return _recipe(
        title="Refactor Recipe",
        mode="controlled",
        use_when="The structure changes but intended behavior should stay the same.",
        phases=[
            "Lock existing behavior with checks first.",
            "Change one module boundary at a time.",
            "Avoid mixing new features into the refactor.",
            "Run regression checks and review the diff.",
        ],
        proof="Show behavior checks still pass and explain which public behavior stayed unchanged.",
    )


def _take_home_recipe() -> str:
    return _recipe(
        title="Take-Home Recipe",
        mode="controlled or council",
        use_when="The output will be evaluated by an interviewer or external reviewer.",
        phases=[
            "Clarify problem, constraints, and scoring criteria.",
            "Create a short plan with visible tradeoffs.",
            "Build in small deliverable slices.",
            "Verify, review, proof-pack, and polish README/run instructions.",
        ],
        proof="Make the project easy to run, easy to inspect, and honest about limitations.",
    )


def _open_source_pr_recipe() -> str:
    return _recipe(
        title="Open-Source PR Recipe",
        mode="controlled",
        use_when="The change will be sent to another repository's maintainers.",
        phases=[
            "Keep the scope small and maintainer-friendly.",
            "Match existing code and test style.",
            "Add focused tests for the changed behavior.",
            "Prepare a reviewable diff and concise PR explanation.",
        ],
        proof="Show the specific issue fixed, tests run, and why the change is low-risk.",
    )


def _recipe(title: str, mode: str, use_when: str, phases: list[str], proof: str) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            f"Recommended mode: `{mode}`",
            "",
            "## Use When",
            "",
            use_when,
            "",
            "## Flow",
            "",
            *[f"{index}. {phase}" for index, phase in enumerate(phases, start=1)],
            "",
            "## Evidence To Keep",
            "",
            "- Task contract",
            "- Git diff/source state",
            "- Required check logs",
            "- Review result",
            "- Proof pack when externally delivered",
            "",
            "## Done When",
            "",
            proof,
            "",
        ]
    )
