"""SK-001: atomic writes survive a mid-write kill; timestamps are aware-UTC everywhere."""

import json
import subprocess

import pytest

from supskill_state import store
from supskill_state.cli import main
from supskill_state.errors import StateError
from supskill_state.model import Stage
from supskill_state.store import (
    append_jsonl,
    dump_state,
    load_state,
    now_utc_iso,
    require_aware_utc_iso,
    resolve_root,
    state_path,
)


def test_load_missing_file_refuses_with_a_clear_message(tmp_path):
    with pytest.raises(StateError, match="init"):
        load_state(state_path(tmp_path))


def test_dump_then_load_round_trips(tmp_path, make_state):
    path = state_path(tmp_path)
    state = make_state(stage=Stage.PLAN)
    dump_state(state, path)
    assert load_state(path) == state


def test_partial_temp_file_from_a_killed_write_is_ignored_on_load(tmp_path, make_state):
    # simulate a process killed mid-write: a truncated temp file beside a valid state.json
    path = state_path(tmp_path)
    state = make_state()
    dump_state(state, path)
    (path.parent / "state.json.tmp-killed").write_text('{"schema": 1, "backlog": "docs/')
    assert load_state(path) == state


def test_interrupted_write_leaves_previous_state_intact(tmp_path, make_state, monkeypatch):
    path = state_path(tmp_path)
    dump_state(make_state(), path)
    before = path.read_bytes()

    def crash(src, dst):
        raise RuntimeError("killed mid-write")

    monkeypatch.setattr(store.os, "replace", crash)
    with pytest.raises(RuntimeError):
        dump_state(make_state(stage=Stage.PLAN), path)
    assert path.read_bytes() == before
    # and the crashed write's temp file was cleaned up
    assert [p.name for p in path.parent.iterdir()] == ["state.json"]


def test_append_jsonl_appends_and_never_truncates(tmp_path):
    path = tmp_path / "gates.jsonl"
    append_jsonl(path, {"n": 1})
    append_jsonl(path, {"n": 2})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["n"] for line in lines] == [1, 2]


def test_now_utc_iso_is_aware_utc():
    require_aware_utc_iso(now_utc_iso(), "test")


@pytest.mark.parametrize(
    "bad",
    [
        "2026-07-12T18:00:00",        # naive
        "2026-07-12T18:00:00+02:00",  # aware but not UTC
        "12/07/2026 18:00",           # not ISO-8601
        "",
    ],
)
def test_non_aware_utc_timestamps_are_rejected(bad):
    with pytest.raises(StateError):
        require_aware_utc_iso(bad, "test")


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def test_resolve_root_returns_an_explicit_root_unchanged(tmp_path):
    assert resolve_root(tmp_path) == tmp_path


def test_resolve_root_uses_cwd_when_state_is_present(tmp_path, monkeypatch, make_state):
    dump_state(make_state(), state_path(tmp_path))  # tmp_path/.supskill/state.json now exists
    monkeypatch.chdir(tmp_path)
    assert resolve_root() == tmp_path


def test_resolve_root_falls_back_to_cwd_outside_a_repo(tmp_path, monkeypatch):
    # no .supskill/, not a git repo: unchanged no-upward-search behavior
    monkeypatch.chdir(tmp_path)
    assert resolve_root() == tmp_path


@pytest.fixture
def repo_with_worktree(tmp_path, make_state):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "initial")
    # state lives at the MAIN root only
    dump_state(make_state(), state_path(repo))
    # a linked worktree, exactly like the EXECUTE stage's `supskill-state worktree`
    worktree = repo / ".worktrees" / "s1"
    _git(repo, "worktree", "add", "-q", "-b", "s1", str(worktree))
    return repo, worktree


def test_resolve_root_redirects_from_a_linked_worktree_to_the_main_root(
    repo_with_worktree, monkeypatch
):
    repo, worktree = repo_with_worktree
    monkeypatch.chdir(worktree)
    assert resolve_root().resolve() == repo.resolve()


def test_resolve_root_in_the_main_worktree_stays_at_cwd(repo_with_worktree, monkeypatch):
    repo, _worktree = repo_with_worktree
    monkeypatch.chdir(repo)
    assert resolve_root().resolve() == repo.resolve()


def test_a_cli_command_run_from_the_worktree_cwd_finds_the_main_root_state(
    repo_with_worktree, monkeypatch, capsys
):
    # the exact s5 failure: `supskill-state` from the worktree cwd was refused
    repo, worktree = repo_with_worktree
    monkeypatch.chdir(worktree)
    assert main(["show", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["sprint"]["id"] == "S10"
