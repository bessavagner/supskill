"""SK-105: the guard that catches a dispatched agent's `git add -A` sweeping
foreign harness state (`.omc/`) into a task's committed range."""

import subprocess
from pathlib import Path

import pytest

from supskill_state.cli import main
from supskill_state.commit_scope import (
    FOREIGN_PREFIXES,
    foreign_paths,
    refusal,
)
from supskill_state.errors import StateError

BEFORE = "133da28f8f2b7c1a9e5d4c3b2a1908070605f4e3"
AFTER = "aa81d4d0e1f2a3b4c5d6e7f8091a2b3c4d5e6f70"


def test_a_clean_range_has_no_foreign_paths():
    assert foreign_paths(["src/app.py", "tests/test_app.py", "README.md"]) == []


def test_omc_state_is_foreign():
    assert foreign_paths(["src/app.py", ".omc/state.json"]) == [".omc/state.json"]


def test_every_denylisted_prefix_is_caught():
    for prefix in FOREIGN_PREFIXES:
        assert foreign_paths([f"{prefix}x/y.txt"]) == [f"{prefix}x/y.txt"]


def test_a_leading_dot_slash_is_normalized():
    assert foreign_paths(["./.omc/x"]) == [".omc/x"]


def test_a_lookalike_outside_the_dir_is_not_foreign():
    # dir-anchored: `.omcfg/` and a file merely NAMED like the dir are not foreign
    assert foreign_paths([".omcfg/x", "src/.omc_notes.md"]) == []


def test_duplicates_are_collapsed():
    assert foreign_paths([".omc/a", ".omc/a"]) == [".omc/a"]


def test_the_refusal_lists_paths_and_names_the_range_and_the_reset():
    text = refusal([".omc/state.json"], BEFORE, AFTER)
    assert ".omc/state.json" in text
    assert BEFORE in text and AFTER in text
    assert "reset --soft" in text


def test_the_refusal_on_no_paths_raises():
    with pytest.raises(StateError, match="nothing to refuse"):
        refusal([], BEFORE, AFTER)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _head(root: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


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


def test_cli_passes_a_clean_range(git_repo, capsys):
    before = _head(git_repo)
    (git_repo / "src").mkdir()
    (git_repo / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    _git(git_repo, "add", "src/app.py")
    _git(git_repo, "commit", "-q", "-m", "feat: app")
    after = _head(git_repo)
    code = main(["commit-scope-guard", "--before", before, "--after", after, "--dir", str(git_repo)])
    assert code == 0
    assert "no foreign state" in capsys.readouterr().out


def test_cli_refuses_a_commit_that_swept_in_omc_state(git_repo, capsys):
    before = _head(git_repo)
    (git_repo / ".omc").mkdir()
    (git_repo / ".omc" / "state.json").write_text("{}\n", encoding="utf-8")
    (git_repo / "src.py").write_text("y = 2\n", encoding="utf-8")
    _git(git_repo, "add", "-A")  # the exact footgun: stages the whole tree
    _git(git_repo, "commit", "-q", "-m", "feat: work (and swept .omc/)")
    after = _head(git_repo)
    code = main(["commit-scope-guard", "--before", before, "--after", after, "--dir", str(git_repo)])
    assert code == 1
    assert ".omc/state.json" in capsys.readouterr().err


def test_cli_reports_a_git_failure_on_bogus_shas(git_repo, capsys):
    code = main(["commit-scope-guard", "--before", "deadbeef", "--after", "cafef00d", "--dir", str(git_repo)])
    assert code == 1
    assert "failed" in capsys.readouterr().err


def test_the_guard_needs_no_state_file(git_repo, monkeypatch, capsys):
    # a query, not a verb: it must work before init and after a wipe
    monkeypatch.chdir(git_repo)
    before = _head(git_repo)
    assert main(["commit-scope-guard", "--before", before, "--after", before]) == 0


def test_the_execute_dispatch_discipline_names_the_commit_scope_guard():
    skill = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    start = text.index("### The dispatch discipline")
    section = text[start : text.index("\n### ", start + 1)]
    assert "commit-scope-guard" in section
    assert ".omc/" in section  # names the harness state it exists to catch


def test_a_conductor_commit_that_would_stage_supskill_state_is_refused():
    from supskill_state.commit_scope import guard_conductor_commit

    foreign = guard_conductor_commit(
        ["docs/sprints/backlog-01/backlog.md", ".supskill/state.json"]
    )
    assert foreign == [".supskill/state.json"]


def test_a_conductor_commit_of_only_the_recorded_artifacts_is_allowed():
    from supskill_state.commit_scope import guard_conductor_commit

    assert guard_conductor_commit(
        ["docs/sprints/backlog-01/sprint-s9.md", "docs/superpowers/plans/2026-08-04-sprint-s9.md"]
    ) == []


def test_the_conductor_guard_uses_the_same_denylist_as_the_task_guard():
    from supskill_state.commit_scope import guard_conductor_commit

    for prefix in FOREIGN_PREFIXES:
        assert guard_conductor_commit([f"{prefix}x"]) == [f"{prefix}x"]
