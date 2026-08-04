"""SK-117: the guard that names recorded artifacts git does not track.

The sprint doc and the dev plan authorize a sprint; three times across two
projects they were left untracked while the code they authorize was committed,
and every time a human reader caught it rather than a mechanism.
"""

import subprocess
from pathlib import Path

import pytest

from supskill_state.artifact_tracking import git_tracked, refusal, untracked
from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_artifact
from supskill_state.errors import StateError


def test_everything_tracked_leaves_nothing_to_report():
    assert untracked(["docs/sprint-s6.md"], {"docs/sprint-s6.md"}) == []


def test_an_untracked_path_is_named():
    assert untracked(["docs/sprint-s6.md", "docs/plan.md"], {"docs/plan.md"}) == [
        "docs/sprint-s6.md"
    ]


def test_a_leading_dot_slash_is_normalized_before_comparing():
    assert untracked(["./docs/sprint-s6.md"], {"docs/sprint-s6.md"}) == []


def test_a_redundant_separator_is_normalized_before_comparing():
    # `git ls-files` prints "docs/sprint-s6.md" for this pathspec too; the raw
    # recorded string must not be compared against that output verbatim
    assert untracked(["docs//sprint-s6.md"], {"docs/sprint-s6.md"}) == []


def test_an_internally_resolving_dotdot_is_normalized_before_comparing():
    assert untracked(["docs/../docs/sprint-s6.md"], {"docs/sprint-s6.md"}) == []


def test_duplicates_are_collapsed():
    assert untracked(["docs/a.md", "docs/a.md"], set()) == ["docs/a.md"]


def test_blank_entries_are_ignored():
    assert untracked(["", "   "], set()) == []


def test_no_recorded_paths_asks_git_nothing(tmp_path):
    # an empty question needs no subprocess and no repo
    assert git_tracked(str(tmp_path), []) == set()


def test_the_refusal_lists_the_paths_and_refuses_to_stage_them():
    text = refusal(["docs/sprints/sprint-s6.md"])
    assert "docs/sprints/sprint-s6.md" in text
    assert "never fixed here" in text
    assert "G3 is still open" in text


def test_no_guard_text_still_claims_supskill_never_runs_a_repo_changing_git_command():
    """C2: true before E10, false at this seam after it.

    `artifact-guard.untracked` is remediable now: SKILL.md's Gate 3 has the conductor
    stage and commit exactly these paths. A refusal relayed verbatim that says supskill
    runs no such command tells the operator to do the thing the conductor just did.
    """
    scripts = Path(__file__).resolve().parent.parent / "scripts" / "supskill_state"
    for module in sorted(scripts.glob("*.py")):
        text = module.read_text(encoding="utf-8")
        assert "runs no git command" not in text, f"{module.name} still makes the pre-E10 claim"


def test_the_refusal_names_the_remediable_stop_and_its_recording_verb():
    text = refusal(["docs/sprints/sprint-s6.md"])
    assert "artifact-guard.untracked" in text
    assert "remediable" in text
    assert "action --stop artifact-guard.untracked" in text


def test_the_conventions_bullet_carves_out_remediable_stops():
    """C2: "never work around a refusal" with no exception never reaches the remediation."""
    skill = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    start = text.index("never work around a refusal")
    bullet = text[start : text.index("\n- ", start)]
    assert "remediable" in bullet
    assert "references/stop-classes.md" in bullet


def test_the_refusal_on_no_paths_raises():
    with pytest.raises(StateError, match="nothing to refuse"):
        refusal([])


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def sprint_repo(tmp_path):
    """A git repo with a supskill sprint whose sprint doc exists on disk."""
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "initial")
    (repo / "docs" / "sprint-s6.md").write_text("# sprint s6\n", encoding="utf-8")
    init_sprint("s6", backlog="docs/backlog.md", root=repo)
    record_artifact("sprint_doc", "docs/sprint-s6.md", root=repo)
    return repo


def test_cli_refuses_an_untracked_sprint_doc(sprint_repo, capsys):
    assert main(["artifact-guard", "--dir", str(sprint_repo)]) == 1
    err = capsys.readouterr().err
    assert "docs/sprint-s6.md" in err
    assert "never fixed here" in err


def test_cli_passes_once_the_doc_is_committed(sprint_repo, capsys):
    _git(sprint_repo, "add", "docs/sprint-s6.md")
    _git(sprint_repo, "commit", "-q", "-m", "docs: the sprint doc")
    assert main(["artifact-guard", "--dir", str(sprint_repo)]) == 0
    assert "tracked by git" in capsys.readouterr().out


def test_cli_passes_for_an_artifact_recorded_by_an_absolute_path(sprint_repo, capsys):
    # record_artifact only checks the path exists; nothing constrains its shape, so an
    # absolute path landing inside the repo is reachable in production. `git ls-files`
    # accepts it and prints the file's canonical relative form - the comparison must
    # land in that same frame, not false-refuse a file that is genuinely tracked.
    _git(sprint_repo, "add", "docs/sprint-s6.md")
    _git(sprint_repo, "commit", "-q", "-m", "docs: the sprint doc")
    record_artifact("sprint_doc", str(sprint_repo / "docs" / "sprint-s6.md"), root=sprint_repo)
    assert main(["artifact-guard", "--dir", str(sprint_repo)]) == 0
    assert "tracked by git" in capsys.readouterr().out


def test_cli_passes_when_no_artifact_is_recorded_yet(sprint_repo, capsys):
    init_sprint("s7", entry="EXECUTE", archive=True, root=sprint_repo)
    assert main(["artifact-guard", "--dir", str(sprint_repo)]) == 0
    assert "no artifacts recorded" in capsys.readouterr().out


def test_cli_defaults_to_cwd(sprint_repo, monkeypatch, capsys):
    monkeypatch.chdir(sprint_repo)
    assert main(["artifact-guard"]) == 1
    assert "docs/sprint-s6.md" in capsys.readouterr().err


def test_cli_refuses_when_there_is_no_state_to_read(tmp_path, monkeypatch, capsys):
    # unlike plan-guard, this reads state: it is a Gate 3 check, and Gate 3 implies state
    monkeypatch.chdir(tmp_path)
    assert main(["artifact-guard"]) == 1
    assert "no state file" in capsys.readouterr().err


def test_gate_three_prose_names_the_artifact_guard():
    skill = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    start = text.index("## Gate 3")
    section = text[start : text.index("\n## ", start + 1)]
    assert "artifact-guard" in section
    assert "commit" in section  # the operator's move, named
