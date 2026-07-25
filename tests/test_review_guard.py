"""SK-104: REVIEW refuses a review package that HEAD has moved past.

playset s1: out-of-band commits landed after EXECUTE's halt, the recorded
review-final.diff no longer matched the branch, and only the conductor's judgment
caught it. PAR reviewing a diff that is not the branch returns a CLEAN review of
the wrong thing - the most expensive way this product can fail quietly.
"""

import json
import subprocess

import pytest

from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_package
from supskill_state.errors import StateError
from supskill_state.review_package import git_head, is_stale, last_record, refusal
from supskill_state.store import require_aware_utc_iso, runs_dir

RECORD = {"base": "a1b2c3d", "head": "f9e8d7c", "path": ".superpowers/sdd/s1/review-final.diff"}


def test_the_same_head_is_not_stale():
    assert is_stale("f9e8d7c", "f9e8d7c") is False


def test_a_moved_head_is_stale():
    assert is_stale("f9e8d7c", "0123456") is True


def test_surrounding_whitespace_never_makes_a_package_look_stale():
    assert is_stale(" f9e8d7c\n", "f9e8d7c") is False


def test_an_empty_recorded_head_is_stale():
    """Never read missing evidence as freshness."""
    assert is_stale("", "f9e8d7c") is True


def test_refusal_names_both_shas_and_the_command_to_run():
    text = refusal(RECORD, "0123456")
    assert "f9e8d7c" in text and "0123456" in text and "a1b2c3d" in text
    assert "review-package" in text
    assert ".superpowers/sdd/s1/review-final.diff" in text


def test_refusal_on_a_fresh_package_is_itself_refused():
    with pytest.raises(StateError):
        refusal(RECORD, "f9e8d7c")


def test_record_package_writes_an_append_only_trail(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_package("a1b2c3d", "f9e8d7c", "scratch/review-final.diff", root=tmp_path)
    record_package("a1b2c3d", "0123456", "scratch/review-final.diff", root=tmp_path)
    lines = (runs_dir(tmp_path) / "s1" / "package.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    require_aware_utc_iso(json.loads(lines[0])["at"], "package.at")


def test_last_record_returns_the_most_recent(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_package("a1b2c3d", "f9e8d7c", "scratch/review-final.diff", root=tmp_path)
    record_package("a1b2c3d", "0123456", "scratch/review-final.diff", root=tmp_path)
    assert last_record(tmp_path, "s1")["head"] == "0123456"


def test_last_record_is_none_when_nothing_was_ever_recorded(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    assert last_record(tmp_path, "s1") is None


def test_record_package_refuses_empty_shas(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    with pytest.raises(StateError):
        record_package("", "f9e8d7c", "scratch/review-final.diff", root=tmp_path)
    with pytest.raises(StateError):
        record_package("a1b2c3d", "  ", "scratch/review-final.diff", root=tmp_path)


def _git(tmp_path, *args):
    subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)


def _repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-qm", "one")


def test_git_head_reads_the_current_sha(tmp_path):
    _repo(tmp_path)
    assert len(git_head(str(tmp_path))) == 40


def test_git_head_raises_rather_than_guessing_outside_a_repo(tmp_path):
    with pytest.raises(StateError):
        git_head(str(tmp_path))


def test_guard_passes_when_head_has_not_moved(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    head = git_head(str(tmp_path))
    record_package("a1b2c3d", head, "scratch/review-final.diff", root=tmp_path)
    assert main(["review-guard"]) == 0
    assert "matches HEAD" in capsys.readouterr().out


def test_guard_refuses_when_head_moved_past_the_package(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_package("a1b2c3d", git_head(str(tmp_path)), "scratch/review-final.diff", root=tmp_path)
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")
    _git(tmp_path, "commit", "-aqm", "two")
    assert main(["review-guard"]) == 1
    assert "review-package" in capsys.readouterr().err


def test_guard_refuses_when_no_package_was_ever_recorded(tmp_path, monkeypatch, capsys):
    """EXECUTE not recording its package is exactly the state that hid the s1 defect."""
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    assert main(["review-guard"]) == 1
    assert "no review package" in capsys.readouterr().err


def test_the_package_verb_records_through_the_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    assert main(["package", "--base", "a1b2c3d", "--head", "f9e8d7c",
                 "--path", "scratch/review-final.diff"]) == 0
    assert "recorded review package" in capsys.readouterr().out
    assert last_record(tmp_path, "s1")["base"] == "a1b2c3d"
