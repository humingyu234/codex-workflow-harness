from __future__ import annotations

from pathlib import Path

from codex_harness.cli import main


def test_project_init_creates_profile_and_recipes(tmp_path: Path) -> None:
    assert main(["project", "init", "--root", str(tmp_path), "--name", "Demo Project"]) == 0

    harness_dir = tmp_path / ".codex-harness"
    profile = harness_dir / "project-profile.md"
    recipes = harness_dir / "recipes"

    assert profile.exists()
    assert "Demo Project" in profile.read_text(encoding="utf-8")
    assert (recipes / "bugfix.md").exists()
    assert (recipes / "feature.md").exists()
    assert (recipes / "refactor.md").exists()
    assert (recipes / "take-home.md").exists()
    assert (recipes / "open-source-pr.md").exists()
    assert "Recommended mode" in (recipes / "bugfix.md").read_text(encoding="utf-8")


def test_project_init_does_not_overwrite_existing_files_without_force(tmp_path: Path) -> None:
    harness_dir = tmp_path / ".codex-harness"
    recipes = harness_dir / "recipes"
    recipes.mkdir(parents=True)
    profile = harness_dir / "project-profile.md"
    recipe = recipes / "bugfix.md"
    profile.write_text("custom profile\n", encoding="utf-8")
    recipe.write_text("custom recipe\n", encoding="utf-8")

    assert main(["project", "init", "--root", str(tmp_path), "--name", "Ignored Name"]) == 0

    assert profile.read_text(encoding="utf-8") == "custom profile\n"
    assert recipe.read_text(encoding="utf-8") == "custom recipe\n"
    assert (recipes / "feature.md").exists()


def test_project_init_force_overwrites_existing_files(tmp_path: Path) -> None:
    harness_dir = tmp_path / ".codex-harness"
    harness_dir.mkdir()
    profile = harness_dir / "project-profile.md"
    profile.write_text("custom profile\n", encoding="utf-8")

    assert main(["project", "init", "--root", str(tmp_path), "--name", "Forced Project", "--force"]) == 0

    content = profile.read_text(encoding="utf-8")
    assert "Forced Project" in content
    assert "custom profile" not in content
