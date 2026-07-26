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
from supskill_state.review_package import (
    dispatch_root_for,
    git_head,
    is_stale,
    last_record,
    missing_refusal,
    refusal,
)
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


def test_refusal_recovery_command_carries_dispatch_root():
    """Carried finding: the recovery text must not reproduce the bug SK-104 just fixed -
    an operator who copies a `package` call with no --dispatch-root re-records a package
    the guard can never match in the worktree workflow."""
    text = refusal(RECORD, "0123456")
    assert "--dispatch-root" in text


def test_refusal_recovery_command_uses_the_recorded_dispatch_root_when_present():
    record = {**RECORD, "dispatch_root": ".worktrees/s1"}
    text = refusal(record, "0123456")
    assert "--dispatch-root .worktrees/s1" in text


def test_missing_refusal_recovery_command_carries_dispatch_root():
    text = missing_refusal("s1")
    assert "--dispatch-root" in text


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


def _write_diff(root, rel_path="scratch/review-final.diff"):
    """Write a real file at `rel_path`, so a guard call is not confounded by the
    Critical-1 file-existence check when the test means to exercise something else."""
    diff = root / rel_path
    diff.parent.mkdir(parents=True, exist_ok=True)
    diff.write_text("diff\n", encoding="utf-8")
    return diff


def test_guard_passes_when_head_has_not_moved(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    _write_diff(tmp_path)
    head = git_head(str(tmp_path))
    record_package("a1b2c3d", head, "scratch/review-final.diff", root=tmp_path)
    assert main(["review-guard"]) == 0
    assert "matches HEAD" in capsys.readouterr().out


def test_guard_refuses_when_head_moved_past_the_package(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    _write_diff(tmp_path)
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


# --- review findings fix round 1: Important 2 (false-pass surfaces were untested) ---


def _write_package_jsonl(tmp_path, sprint_id, lines):
    """Write raw lines to runs/<id>/package.jsonl, bypassing record_package.

    Lets a test construct a malformed or partial record that record_package's own
    validation would refuse to write - exactly the kind of record a torn write or a
    hand-edited trail can leave behind.
    """
    path = runs_dir(tmp_path) / sprint_id / "package.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_last_record_skips_a_torn_or_malformed_tail_line(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    good = json.dumps({"base": "a1b2c3d", "head": "f9e8d7c", "path": "x.diff"})
    _write_package_jsonl(tmp_path, "s1", [good, '{"base": "a1b2c3d", "head": "011'])  # torn tail
    assert last_record(tmp_path, "s1") == json.loads(good)


def test_last_record_skips_a_non_dict_record(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    good = json.dumps({"base": "a1b2c3d", "head": "f9e8d7c", "path": "x.diff"})
    _write_package_jsonl(tmp_path, "s1", [good, json.dumps(["not", "a", "dict"])])
    assert last_record(tmp_path, "s1") == json.loads(good)


def test_guard_refuses_when_the_recorded_head_key_is_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    _write_package_jsonl(
        tmp_path, "s1", [json.dumps({"base": "a1b2c3d", "path": "x.diff"})]  # no "head" at all
    )
    assert main(["review-guard"]) == 1
    assert "review-package" in capsys.readouterr().err


def test_guard_refuses_when_the_recorded_head_is_whitespace_only(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    _write_package_jsonl(
        tmp_path, "s1", [json.dumps({"base": "a1b2c3d", "head": "   ", "path": "x.diff"})]
    )
    assert main(["review-guard"]) == 1
    assert "review-package" in capsys.readouterr().err


# --- review findings fix round 1: Important 1 (guard rev-parsed the wrong repo) ---


def test_dispatch_root_for_falls_back_to_the_state_root_when_absent(tmp_path):
    assert dispatch_root_for(tmp_path, {}) == tmp_path


def test_dispatch_root_for_falls_back_to_the_state_root_when_blank(tmp_path):
    assert dispatch_root_for(tmp_path, {"dispatch_root": "   "}) == tmp_path


def test_dispatch_root_for_resolves_a_relative_path_against_the_state_root(tmp_path):
    assert dispatch_root_for(tmp_path, {"dispatch_root": ".worktrees/s1"}) == tmp_path / ".worktrees" / "s1"


def test_dispatch_root_for_leaves_an_absolute_path_unchanged(tmp_path):
    worktree = tmp_path / "elsewhere"
    assert dispatch_root_for(tmp_path, {"dispatch_root": str(worktree)}) == worktree


def test_record_package_stores_the_dispatch_root_when_given(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_package("a1b2c3d", "f9e8d7c", "scratch/review-final.diff",
                    dispatch_root=".worktrees/s1", root=tmp_path)
    assert last_record(tmp_path, "s1")["dispatch_root"] == ".worktrees/s1"


def test_record_package_stores_a_null_dispatch_root_when_omitted(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_package("a1b2c3d", "f9e8d7c", "scratch/review-final.diff", root=tmp_path)
    assert last_record(tmp_path, "s1")["dispatch_root"] is None


def test_the_package_verb_records_the_dispatch_root_through_the_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    assert main(["package", "--base", "a1b2c3d", "--head", "f9e8d7c",
                 "--path", "scratch/review-final.diff", "--dispatch-root", ".worktrees/s1"]) == 0
    assert last_record(tmp_path, "s1")["dispatch_root"] == ".worktrees/s1"


def test_guard_rev_parses_the_recorded_dispatch_root_not_the_state_root(tmp_path, monkeypatch, capsys):
    """SK-104 fix: EXECUTE isolates into a worktree (SK-111) - .supskill/ stays at the
    main root, but the package is cut on the sprint branch in the worktree. The guard
    must rev-parse HEAD there, not at the state root, or it can never pass in that
    workflow."""
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    worktree = tmp_path / ".worktrees" / "s1"
    _git(tmp_path, "worktree", "add", "-b", "s1-branch", str(worktree))
    (worktree / "a.txt").write_text("two\n", encoding="utf-8")
    _git(worktree, "commit", "-aqm", "two")
    worktree_head = git_head(str(worktree))
    assert git_head(str(tmp_path)) != worktree_head  # the state root's own HEAD never moved
    _write_diff(worktree)
    record_package("a1b2c3d", worktree_head, "scratch/review-final.diff",
                    dispatch_root=str(worktree), root=tmp_path)
    assert main(["review-guard"]) == 0
    assert "matches HEAD" in capsys.readouterr().out


# --- final review of feat/e9-gate3-inputs: Critical 1 (reused sprint id false-passes) ---


def test_guard_refuses_when_a_reused_sprint_id_outlives_its_package(tmp_path, monkeypatch, capsys):
    """`_archive_existing` moves state.json and gates.jsonl into runs/<id>/archive-N/ on
    `init --archive`, but leaves runs/<id>/package.jsonl where it is. Reusing a sprint id
    is exactly what SKILL.md:130 tells the operator to do (`init <sprint-id> --archive`),
    and it must not let a previous run's package.jsonl pass as though it belonged to a run
    that recorded nothing - the false pass this guard's entire purpose is preventing.

    Reproduces the review's own finding: `review-guard` matched HEAD on a package whose
    diff was gone, on a run that had recorded nothing at all.
    """
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    diff = tmp_path / "scratch" / "review-final.diff"
    diff.parent.mkdir(parents=True)
    diff.write_text("diff\n", encoding="utf-8")
    record_package("a1b2c3d", git_head(str(tmp_path)), "scratch/review-final.diff", root=tmp_path)
    assert main(["review-guard"]) == 0  # sanity: the first run's own package is genuinely current

    diff.unlink()  # the first run's diff does not survive into the second (scratch is ephemeral)
    init_sprint("s1", backlog="backlog.md", root=tmp_path, archive=True)  # a new run; records nothing
    assert (runs_dir(tmp_path) / "s1" / "package.jsonl").exists()  # the old record survived the archive
    assert last_record(tmp_path, "s1") is not None  # and review-guard can still see it

    assert main(["review-guard"]) == 1
    assert "scratch/review-final.diff" in capsys.readouterr().err


def test_guard_resolves_a_relative_dispatch_root_against_the_state_root(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    worktree = tmp_path / ".worktrees" / "s1"
    _git(tmp_path, "worktree", "add", "-b", "s1-branch", str(worktree))
    (worktree / "a.txt").write_text("two\n", encoding="utf-8")
    _git(worktree, "commit", "-aqm", "two")
    worktree_head = git_head(str(worktree))
    _write_diff(worktree)
    record_package("a1b2c3d", worktree_head, "scratch/review-final.diff",
                    dispatch_root=".worktrees/s1", root=tmp_path)
    assert main(["review-guard"]) == 0
    assert "matches HEAD" in capsys.readouterr().out
