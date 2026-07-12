"""SK-005: every gate decision leaves a verbatim, append-only, trail-first audit record."""

import json

import pytest

from supskill_state import commands
from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_gate, render_show
from supskill_state.errors import StateError
from supskill_state.store import (
    gates_path,
    load_state,
    require_aware_utc_iso,
    state_path,
)


def _gate_lines(tmp_path):
    return [
        json.loads(line)
        for line in gates_path(tmp_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_gate_appends_record_and_updates_state(tmp_path):
    init_sprint("s1", root=tmp_path)
    record_gate("G1", "approved", "yes - looks right, go ahead", root=tmp_path)

    lines = _gate_lines(tmp_path)
    assert len(lines) == 1
    record = lines[0]
    assert record["gate"] == "G1"
    assert record["decision"] == "approved"
    assert record["response"] == "yes - looks right, go ahead"
    require_aware_utc_iso(record["at"], "gates.jsonl at")

    assert load_state(state_path(tmp_path)).gates["G1_sprint_doc"] == "approved"


def test_second_decision_on_same_gate_appends_history_and_last_wins(tmp_path):
    init_sprint("s1", root=tmp_path)
    record_gate("G1", "rejected", "no - the scope section is wrong", root=tmp_path)
    record_gate("G1", "approved", "fixed, approved", root=tmp_path)

    lines = _gate_lines(tmp_path)
    assert [(r["gate"], r["decision"]) for r in lines] == [("G1", "rejected"), ("G1", "approved")]
    assert load_state(state_path(tmp_path)).gates["G1_sprint_doc"] == "approved"


def test_write_order_trail_lands_before_state(tmp_path, monkeypatch):
    # fail the SECOND write (state.json): the trail must already be on disk
    init_sprint("s1", root=tmp_path)
    before = state_path(tmp_path).read_bytes()

    def crash(state, path):
        raise RuntimeError("killed between the two writes")

    monkeypatch.setattr(commands.store, "dump_state", crash)
    with pytest.raises(RuntimeError):
        record_gate("G2", "approved", "plan approved", root=tmp_path)

    assert [r["gate"] for r in _gate_lines(tmp_path)] == ["G2"]  # trail ahead of state
    assert state_path(tmp_path).read_bytes() == before  # state untouched


def test_empty_response_is_accepted_recorded_and_visible_in_show(tmp_path):
    # F-4: a fabricated approval must leave a readable (empty) quote, not be rejected
    init_sprint("s1", root=tmp_path)
    record_gate("G1", "approved", "", root=tmp_path)
    assert _gate_lines(tmp_path)[0]["response"] == ""
    assert 'response: ""' in render_show(tmp_path)


def test_unknown_gate_id_and_decision_refused_with_nothing_written(tmp_path):
    init_sprint("s1", root=tmp_path)
    before_state = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match="unknown gate"):
        record_gate("G4", "approved", "x", root=tmp_path)
    with pytest.raises(StateError, match="unknown decision"):
        record_gate("G1", "maybe", "x", root=tmp_path)
    assert _gate_lines(tmp_path) == []
    assert state_path(tmp_path).read_bytes() == before_state


def test_gate_requires_an_initialized_sprint_before_writing_the_trail(tmp_path):
    with pytest.raises(StateError, match="init"):
        record_gate("G1", "approved", "x", root=tmp_path)
    assert not gates_path(tmp_path).exists()


def test_cli_gate(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s1"]) == 0
    assert main(["gate", "--id", "G1", "--decision", "approved", "--response", "approved, go"]) == 0
    assert load_state(state_path(tmp_path)).gates["G1_sprint_doc"] == "approved"
