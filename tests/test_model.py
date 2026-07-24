"""SK-001: schema v1 round-trips D2's example; wrong vocabulary refuses loudly."""

import dataclasses
import json
from pathlib import Path

import pytest

from supskill_state.errors import StateError
from supskill_state.model import (
    TERMINAL_STATUSES,
    Stage,
    State,
    TaskStatus,
    dumps_state,
    loads_state,
    state_from_dict,
    state_to_dict,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "state_d2_example.json"


def fixture_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_d2_example_round_trips_field_by_field():
    state = loads_state(fixture_text())
    reloaded = loads_state(dumps_state(state))
    for field in dataclasses.fields(State):
        assert getattr(reloaded, field.name) == getattr(state, field.name), field.name


def test_dump_reproduces_the_fixture_json_exactly():
    state = loads_state(fixture_text())
    assert json.loads(dumps_state(state)) == json.loads(fixture_text())


def test_unknown_schema_version_refuses_loudly():
    raw = json.loads(fixture_text())
    raw["schema"] = 2
    with pytest.raises(StateError, match="unsupported schema version 2"):
        loads_state(json.dumps(raw))


def test_missing_schema_field_refuses():
    raw = json.loads(fixture_text())
    del raw["schema"]
    with pytest.raises(StateError, match="schema"):
        loads_state(json.dumps(raw))


def test_invalid_json_refuses_without_traceback_vocabulary():
    with pytest.raises(StateError, match="not valid JSON"):
        loads_state('{"schema": 1,')


def test_needs_context_is_rejected_as_a_status():
    raw = json.loads(fixture_text())
    raw["tasks"][0]["status"] = "NEEDS_CONTEXT"
    with pytest.raises(StateError, match="controller-loop signal"):
        loads_state(json.dumps(raw))


def test_unknown_status_is_rejected():
    raw = json.loads(fixture_text())
    raw["tasks"][0]["status"] = "IN_PROGRESS"
    with pytest.raises(StateError, match="unknown task status"):
        loads_state(json.dumps(raw))


def test_status_vocabulary_is_exact():
    assert {s.value for s in TaskStatus} == {
        "PENDING",
        "DONE",
        "DONE_WITH_CONCERNS",
        "BLOCKED",
        "PARKED",
    }


def test_terminal_set_is_exported_and_exact():
    assert TERMINAL_STATUSES == frozenset(
        {TaskStatus.DONE, TaskStatus.DONE_WITH_CONCERNS, TaskStatus.BLOCKED, TaskStatus.PARKED}
    )
    assert TaskStatus.PENDING not in TERMINAL_STATUSES


def test_stage_vocabulary_is_exact():
    assert [s.value for s in Stage] == ["SCOPE", "PLAN", "EXECUTE", "REVIEW"]


def test_a_legacy_refine_stage_loads_as_scope():
    # SK-100 collapsed SCOPE and REFINE. A state.json frozen at the old REFINE
    # stage across the upgrade resumes as SCOPE instead of failing to parse.
    raw = json.loads(fixture_text())
    raw["stage"] = "REFINE"
    assert loads_state(json.dumps(raw)).stage is Stage.SCOPE


@pytest.mark.parametrize("bad_entry", ["REFINE", "REVIEW", "execute", "START"])
def test_entry_outside_scope_plan_execute_is_rejected(bad_entry):
    raw = json.loads(fixture_text())
    raw["sprint"]["entry"] = bad_entry
    with pytest.raises(StateError):
        loads_state(json.dumps(raw))


def test_gate_value_outside_vocabulary_is_rejected():
    raw = json.loads(fixture_text())
    raw["gates"]["G1_sprint_doc"] = "maybe"
    with pytest.raises(StateError, match="gates.G1_sprint_doc"):
        loads_state(json.dumps(raw))


def test_gates_keys_must_be_exactly_the_three():
    raw = json.loads(fixture_text())
    raw["gates"]["G4_extra"] = None
    with pytest.raises(StateError, match="exactly"):
        loads_state(json.dumps(raw))
    raw = json.loads(fixture_text())
    del raw["gates"]["G2_plan"]
    with pytest.raises(StateError, match="exactly"):
        loads_state(json.dumps(raw))


def test_artifacts_keys_must_be_exactly_sprint_doc_and_dev_plan():
    raw = json.loads(fixture_text())
    raw["artifacts"]["extra"] = "x"
    with pytest.raises(StateError, match="exactly"):
        loads_state(json.dumps(raw))


def test_make_state_fixture_is_valid(make_state):
    state = make_state()
    assert loads_state(dumps_state(state)) == state


# --- SK-116: the continuation a sprint's state could not express ---

def test_sprint_continues_defaults_to_none(make_state):
    assert make_state().sprint.continues is None


def test_a_state_file_written_before_this_field_still_parses(make_state):
    # the field is read tolerantly on purpose: a dogfood run is live against a
    # state.json that has no `continues` key, and the schema version is unchanged
    raw = state_to_dict(make_state())
    del raw["sprint"]["continues"]
    assert state_from_dict(raw).sprint.continues is None


def test_continues_round_trips_through_json(make_state):
    state = make_state()
    state.sprint.continues = "s5"
    assert state_from_dict(json.loads(dumps_state(state))).sprint.continues == "s5"


def test_state_to_dict_always_writes_the_key(make_state):
    assert "continues" in state_to_dict(make_state())["sprint"]


def test_a_non_string_continues_is_refused(make_state):
    raw = state_to_dict(make_state())
    raw["sprint"]["continues"] = 5
    with pytest.raises(StateError, match="continues"):
        state_from_dict(raw)
