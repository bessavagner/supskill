"""SK-043: the verb that can finish a task.

Before this, DONE / DONE_WITH_CONCERNS / PARKED were unreachable strings in an
enum (model.py:45-51): `tasks` writes PENDING (commands.py:322-325), `block`
writes BLOCKED (commands.py:269), and nothing wrote a status at all - so
advance --to REVIEW's all-terminal check (transitions.py:39-46) was unsatisfiable
for any task that SUCCEEDED. The last test here is the walk that was impossible.
"""

import json

import pytest

from supskill_state.cli import main
from supskill_state.commands import advance_stage, init_sprint, record_task_status
from supskill_state.errors import StateError
from supskill_state.model import Stage, Task, TaskStatus
from supskill_state.store import (
    dump_state,
    load_state,
    require_aware_utc_iso,
    runs_dir,
    state_path,
)


def _init_with_tasks(tmp_path, *ids):
    # "S5" with a capital S on purpose: the trail path must normalize it, like blockers.jsonl
    init_sprint("S5", entry="EXECUTE", root=tmp_path)
    state = load_state(state_path(tmp_path))
    state.tasks = [
        Task(id=task_id, seam="unit", provable="offline", status=TaskStatus.PENDING)
        for task_id in ids
    ]
    dump_state(state, state_path(tmp_path))


def _trail(tmp_path):
    path = runs_dir(tmp_path) / "s5" / "tasks.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _status(tmp_path, task_id):
    return next(t.status for t in load_state(state_path(tmp_path)).tasks if t.id == task_id)


def test_done_lands_in_state_and_in_the_trail_beside_blockers_jsonl(tmp_path):
    _init_with_tasks(tmp_path, "SK-040")
    record_task_status("SK-040", "DONE", root=tmp_path)

    assert _status(tmp_path, "SK-040") is TaskStatus.DONE
    lines = _trail(tmp_path)
    assert len(lines) == 1
    require_aware_utc_iso(lines[0].pop("at"), "tasks.jsonl at")
    assert lines[0] == {"task": "SK-040", "status": "DONE", "note": None}


def test_a_note_on_done_carries_the_minor_findings_rollup(tmp_path):
    _init_with_tasks(tmp_path, "SK-040")
    record_task_status("SK-040", "DONE", note="Minor: magic number in the drain loop", root=tmp_path)
    assert _trail(tmp_path)[0]["note"] == "Minor: magic number in the drain loop"


def test_done_with_concerns_requires_a_note(tmp_path):
    _init_with_tasks(tmp_path, "SK-041")
    before = state_path(tmp_path).read_bytes()
    for note in (None, "   "):
        with pytest.raises(StateError, match="requires --note"):
            record_task_status("SK-041", "DONE_WITH_CONCERNS", note=note, root=tmp_path)
    assert _trail(tmp_path) == []
    assert state_path(tmp_path).read_bytes() == before

    record_task_status("SK-041", "DONE_WITH_CONCERNS", note="the halt loop is untested", root=tmp_path)
    assert _status(tmp_path, "SK-041") is TaskStatus.DONE_WITH_CONCERNS
    assert _trail(tmp_path)[0]["note"] == "the halt loop is untested"


def test_parked_is_recordable_and_its_note_names_the_blocker(tmp_path):
    _init_with_tasks(tmp_path, "SK-042")
    record_task_status("SK-042", "PARKED", note="parked by SK-041's blocker: no live capture", root=tmp_path)
    assert _status(tmp_path, "SK-042") is TaskStatus.PARKED
    assert _trail(tmp_path)[0]["status"] == "PARKED"


@pytest.mark.parametrize(
    "status,match",
    [
        ("NEEDS_CONTEXT", "controller-loop signal"),
        ("BLOCKED", "is `block`'s transition"),
        ("PENDING", "moved TO"),
        ("SHIPPED", "unknown task status"),
    ],
)
def test_the_statuses_this_verb_refuses_write_nothing_anywhere(tmp_path, status, match):
    _init_with_tasks(tmp_path, "SK-040")
    before = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match=match):
        record_task_status("SK-040", status, root=tmp_path)
    assert _trail(tmp_path) == []
    assert state_path(tmp_path).read_bytes() == before


def test_an_unknown_id_is_a_typo_or_a_hallucination_never_a_new_task(tmp_path):
    _init_with_tasks(tmp_path, "SK-040")
    with pytest.raises(StateError, match="no task 'SK-099'"):
        record_task_status("SK-099", "DONE", root=tmp_path)
    assert _trail(tmp_path) == []
    assert [t.id for t in load_state(state_path(tmp_path)).tasks] == ["SK-040"]


def test_re_recording_appends_and_the_last_status_wins(tmp_path):
    _init_with_tasks(tmp_path, "SK-040")
    record_task_status("SK-040", "DONE", root=tmp_path)
    record_task_status("SK-040", "DONE_WITH_CONCERNS", note="reviewer reopened it", root=tmp_path)
    assert [line["status"] for line in _trail(tmp_path)] == ["DONE", "DONE_WITH_CONCERNS"]
    assert _status(tmp_path, "SK-040") is TaskStatus.DONE_WITH_CONCERNS


def test_cli_records_and_refuses_with_the_right_exit_codes(tmp_path, monkeypatch, capsys):
    _init_with_tasks(tmp_path, "SK-040")
    monkeypatch.chdir(tmp_path)
    assert main(["task", "--id", "SK-040", "--status", "DONE"]) == 0
    assert "recorded SK-040: DONE" in capsys.readouterr().out

    assert main(["task", "--id", "SK-040", "--status", "NEEDS_CONTEXT"]) == 1
    assert "controller-loop signal" in capsys.readouterr().err

    assert main(["task", "--id", "SK-040", "--status", "DONE_WITH_CONCERNS"]) == 1
    assert "requires --note" in capsys.readouterr().err


def test_the_walk_that_is_impossible_on_main_today(tmp_path):
    # PENDING -> terminal -> advance --to REVIEW. No sprint could take this walk before:
    # nothing could make a task that SUCCEEDED terminal (transitions.py:39-46).
    _init_with_tasks(tmp_path, "SK-040", "SK-041", "SK-042")
    record_task_status("SK-040", "DONE", root=tmp_path)
    record_task_status("SK-041", "DONE_WITH_CONCERNS", note="not proven - operator seam", root=tmp_path)

    with pytest.raises(StateError, match="terminal"):
        advance_stage("REVIEW", root=tmp_path)  # SK-042 is still PENDING

    record_task_status("SK-042", "PARKED", note="parked by SK-041's blocker", root=tmp_path)
    assert advance_stage("REVIEW", root=tmp_path).stage is Stage.REVIEW
