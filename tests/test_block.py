"""SK-006: a blocker is a decision, not an acknowledgment - enumerated options required."""

import json

import pytest

from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_blocker
from supskill_state.errors import StateError
from supskill_state.model import Task, TaskStatus
from supskill_state.store import (
    dump_state,
    load_state,
    require_aware_utc_iso,
    runs_dir,
    state_path,
)

# D5's verbatim S9a blocker - the fixture the spec names
S9A = {
    "task": "T3",
    "kind": "needs-live-capture",
    "found": "entity parser returns 0 posts on all 23 profile reads",
    "options": [
        "(a) operator drives a live capture now",
        "(b) defer to next sprint, proceed with the other 4 tasks",
        "(c) re-scope: the drift hypothesis may be wrong",
    ],
    "recommend": "(a) - the drift detector's heuristic may be firing misleadingly",
}


def _init_with_task(tmp_path, task_id="T3"):
    init_sprint("s9a", root=tmp_path)
    state = load_state(state_path(tmp_path))
    state.tasks = [Task(id=task_id, seam="e2e", provable="operator", status=TaskStatus.PENDING)]
    dump_state(state, state_path(tmp_path))


def _blocker_lines(tmp_path):
    path = runs_dir(tmp_path) / "s9a" / "blockers.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_one_command_three_effects_asserted_together(tmp_path):
    _init_with_task(tmp_path)
    record_blocker(S9A["task"], S9A["kind"], S9A["found"], S9A["options"], S9A["recommend"], root=tmp_path)

    # effect 1: append-only audit record in runs/<sprint-id>/blockers.jsonl
    lines = _blocker_lines(tmp_path)
    assert len(lines) == 1
    require_aware_utc_iso(lines[0].pop("at"), "blockers.jsonl at")
    assert lines[0] == S9A  # D5's fixture round-trips verbatim

    state = load_state(state_path(tmp_path))
    # effect 2: mirrored into state.json.blockers
    assert len(state.blockers) == 1
    blocker = state.blockers[0]
    assert (blocker.task, blocker.kind, blocker.found, blocker.options, blocker.recommend) == (
        S9A["task"], S9A["kind"], S9A["found"], S9A["options"], S9A["recommend"],
    )
    # effect 3: the task is now BLOCKED
    assert state.tasks[0].status is TaskStatus.BLOCKED


@pytest.mark.parametrize(
    "override,match",
    [
        ({"task": ""}, "non-empty"),
        ({"kind": ""}, "non-empty"),
        ({"found": ""}, "non-empty"),
        ({"recommend": ""}, "non-empty"),
        ({"options": ["(a) only one option"]}, "at least two"),
        ({"options": []}, "at least two"),
        ({"options": ["no label here", "(b) fine"]}, "label"),
        ({"options": ["(a) first", "(a) duplicate label"]}, "duplicate"),
        ({"recommend": "(z) - references nothing"}, "reference one of the options"),
        ({"recommend": "do option a"}, "reference one of the options"),
    ],
)
def test_invalid_records_are_rejected_with_nothing_written_anywhere(tmp_path, override, match):
    _init_with_task(tmp_path)
    before = state_path(tmp_path).read_bytes()
    record = {**S9A, **override}
    with pytest.raises(StateError, match=match):
        record_blocker(
            record["task"], record["kind"], record["found"], record["options"],
            record["recommend"], root=tmp_path,
        )
    assert _blocker_lines(tmp_path) == []
    assert state_path(tmp_path).read_bytes() == before


def test_unknown_task_refused(tmp_path):
    _init_with_task(tmp_path, task_id="T1")
    with pytest.raises(StateError, match="no task 'T3'"):
        record_blocker(S9A["task"], S9A["kind"], S9A["found"], S9A["options"], S9A["recommend"], root=tmp_path)
    assert _blocker_lines(tmp_path) == []


def test_scope_boundary_block_records_one_blocker_and_parks_nothing(tmp_path):
    # computing the downstream cone to PARK is E5's drain logic, not block's
    _init_with_task(tmp_path)
    state = load_state(state_path(tmp_path))
    state.tasks.append(Task(id="T4", seam="unit", provable="offline", status=TaskStatus.PENDING))
    dump_state(state, state_path(tmp_path))

    record_blocker(S9A["task"], S9A["kind"], S9A["found"], S9A["options"], S9A["recommend"], root=tmp_path)

    state = load_state(state_path(tmp_path))
    downstream = next(task for task in state.tasks if task.id == "T4")
    assert downstream.status is TaskStatus.PENDING  # untouched


def test_cli_block_with_repeated_option_flags(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_with_task(tmp_path)
    assert (
        main(
            [
                "block", "--task", "T3", "--kind", "needs-live-capture",
                "--found", "entity parser returns 0 posts on all 23 profile reads",
                "--option", "(a) operator drives a live capture now",
                "--option", "(b) defer to next sprint, proceed with the other 4 tasks",
                "--recommend", "(a) - the drift detector's heuristic may be firing misleadingly",
            ]
        )
        == 0
    )
    assert load_state(state_path(tmp_path)).tasks[0].status is TaskStatus.BLOCKED
