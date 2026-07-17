"""SK-092: EXECUTE auto-isolates into a worktree instead of blocking on branch.

The one test file in this codebase that needs a real, disposable git repo
rather than markdown/string parsing (design doc, "Testing plan") - worktree
creation is genuinely a git operation, not a state-file shape.
"""

import subprocess
from pathlib import Path

import pytest

from supskill_state.errors import StateError
from supskill_state.worktree import ensure_gitignored, ensure_worktree


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def test_fresh_creation_creates_worktree_and_gitignores_it(git_repo):
    path, created = ensure_worktree(git_repo, "s15", [])
    assert created is True
    assert path == git_repo / ".worktrees" / "s15"
    assert path.is_dir()
    assert (path / "README.md").exists()
    assert ".worktrees/" in (git_repo / ".gitignore").read_text(encoding="utf-8")


def test_artifacts_are_copied_into_the_worktree(git_repo):
    (git_repo / "sprint.md").write_text("sprint doc\n", encoding="utf-8")
    (git_repo / "docs").mkdir()
    (git_repo / "docs" / "plan.md").write_text("plan\n", encoding="utf-8")
    path, _ = ensure_worktree(git_repo, "s15", ["sprint.md", "docs/plan.md"])
    assert (path / "sprint.md").read_text(encoding="utf-8") == "sprint doc\n"
    assert (path / "docs" / "plan.md").read_text(encoding="utf-8") == "plan\n"


def test_reuse_does_not_duplicate_creation(git_repo):
    path1, created1 = ensure_worktree(git_repo, "s15", [])
    path2, created2 = ensure_worktree(git_repo, "s15", [])
    assert created1 is True
    assert created2 is False
    assert path1 == path2


def test_reuse_re_copies_artifacts_even_when_unchanged(git_repo):
    (git_repo / "sprint.md").write_text("v1\n", encoding="utf-8")
    ensure_worktree(git_repo, "s15", ["sprint.md"])
    (git_repo / "sprint.md").write_text("v2\n", encoding="utf-8")
    path2, created2 = ensure_worktree(git_repo, "s15", ["sprint.md"])
    assert created2 is False
    assert (path2 / "sprint.md").read_text(encoding="utf-8") == "v2\n"


def test_existing_branch_with_no_worktree_attaches_instead_of_erroring(git_repo):
    _git(git_repo, "branch", "s15")
    path, created = ensure_worktree(git_repo, "s15", [])
    assert created is True
    assert path.is_dir()
    result = subprocess.run(
        ["git", "-C", str(path), "branch", "--show-current"],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == "s15"


def test_stale_worktree_registration_raises_state_error(git_repo):
    path, _ = ensure_worktree(git_repo, "s15", [])
    import shutil
    shutil.rmtree(path)
    with pytest.raises(StateError, match="gone"):
        ensure_worktree(git_repo, "s15", [])


def test_gitignore_already_containing_worktrees_is_not_duplicated(git_repo):
    (git_repo / ".gitignore").write_text(".worktrees/\nnode_modules/\n", encoding="utf-8")
    ensure_worktree(git_repo, "s15", [])
    text = (git_repo / ".gitignore").read_text(encoding="utf-8")
    assert text.count(".worktrees/") == 1


def test_ensure_gitignored_appends_without_a_trailing_newline_in_the_source(git_repo):
    (git_repo / ".gitignore").write_text("node_modules", encoding="utf-8")
    ensure_gitignored(git_repo)
    text = (git_repo / ".gitignore").read_text(encoding="utf-8")
    assert text == "node_modules\n.worktrees/\n"


def test_missing_artifact_raises_state_error(git_repo):
    with pytest.raises(StateError, match="artifact not found"):
        ensure_worktree(git_repo, "s15", ["nope.md"])


def test_empty_branch_raises_state_error(git_repo):
    with pytest.raises(StateError, match="--branch"):
        ensure_worktree(git_repo, "", [])


def test_cli_worktree_prints_created_then_reused(git_repo, monkeypatch, capsys):
    from supskill_state.cli import main

    monkeypatch.chdir(git_repo)
    assert main(["worktree", "--branch", "s15"]) == 0
    assert "worktree ready at" in capsys.readouterr().out
    assert main(["worktree", "--branch", "s15"]) == 0
    assert "reused" in capsys.readouterr().out


def test_cli_worktree_passes_artifacts_through(git_repo, monkeypatch, capsys):
    from supskill_state.cli import main

    (git_repo / "sprint.md").write_text("doc\n", encoding="utf-8")
    monkeypatch.chdir(git_repo)
    assert main(["worktree", "--branch", "s15", "--artifact", "sprint.md"]) == 0
    assert (git_repo / ".worktrees" / "s15" / "sprint.md").read_text(encoding="utf-8") == "doc\n"


def test_cli_worktree_refusal_exits_nonzero(git_repo, monkeypatch, capsys):
    from supskill_state.cli import main

    monkeypatch.chdir(git_repo)
    assert main(["worktree", "--branch", "s15", "--artifact", "missing.md"]) == 1
    assert "refused" in capsys.readouterr().err
