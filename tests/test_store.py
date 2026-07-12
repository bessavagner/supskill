"""SK-001: atomic writes survive a mid-write kill; timestamps are aware-UTC everywhere."""

import json

import pytest

from supskill_state import store
from supskill_state.errors import StateError
from supskill_state.model import Stage
from supskill_state.store import (
    append_jsonl,
    dump_state,
    load_state,
    now_utc_iso,
    require_aware_utc_iso,
    state_path,
)


def test_load_missing_file_refuses_with_a_clear_message(tmp_path):
    with pytest.raises(StateError, match="init"):
        load_state(state_path(tmp_path))


def test_dump_then_load_round_trips(tmp_path, make_state):
    path = state_path(tmp_path)
    state = make_state(stage=Stage.REFINE)
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
        dump_state(make_state(stage=Stage.REFINE), path)
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
