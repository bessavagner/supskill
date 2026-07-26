"""SK-103: a blocker whose task succeeded is settled, and must stop reading as live.

playset s1 resolved both its blockers and `show` still said "open blockers: 2",
so Gate 3 presented two settled decisions as live ones. Resolution is derived
from the task's own status - there is no second verb that could disagree with it.
"""

import json

from supskill_state.blockers import RESOLVING_STATUSES, partition, resolving_status
from supskill_state.commands import (
    init_sprint,
    record_blocker,
    record_task_status,
    render_show,
    render_show_json,
)
from supskill_state.model import Blocker, Task, TaskStatus
from supskill_state.store import dump_state, load_state, state_path

OPTIONS = ["(a) do X", "(b) do Y"]
RECOMMEND = "(a) - because X is cheaper"


def _blocker(task="SK-052"):
    return Blocker(task=task, kind="contradiction", found="observed", options=list(OPTIONS), recommend=RECOMMEND)


def _task(task_id="SK-052", status=TaskStatus.BLOCKED):
    return Task(id=task_id, seam="unit", provable="offline", status=status)


def test_a_blocked_task_leaves_its_blocker_open():
    open_, resolved = partition([_blocker()], [_task()])
    assert [b.task for b in open_] == ["SK-052"]
    assert resolved == []


def test_a_done_task_resolves_its_blocker():
    open_, resolved = partition([_blocker()], [_task(status=TaskStatus.DONE)])
    assert open_ == []
    assert [b.task for b in resolved] == ["SK-052"]


def test_done_with_concerns_also_resolves():
    open_, resolved = partition([_blocker()], [_task(status=TaskStatus.DONE_WITH_CONCERNS)])
    assert [b.task for b in resolved] == ["SK-052"]


def test_parked_does_not_resolve_a_blocker():
    """PARKED is terminal, but it means the task never ran - not that it was settled."""
    open_, resolved = partition([_blocker()], [_task(status=TaskStatus.PARKED)])
    assert [b.task for b in open_] == ["SK-052"]
    assert resolved == []
    assert TaskStatus.PARKED not in RESOLVING_STATUSES


def test_a_blocker_whose_task_vanished_stays_open():
    """Never silently resolve on missing evidence: an unknown task cannot settle anything."""
    open_, resolved = partition([_blocker(task="SK-999")], [_task()])
    assert [b.task for b in open_] == ["SK-999"]
    assert resolved == []


def test_input_order_is_preserved_within_each_side():
    blockers = [_blocker("SK-1"), _blocker("SK-2"), _blocker("SK-3")]
    tasks = [_task("SK-1", TaskStatus.DONE), _task("SK-2"), _task("SK-3", TaskStatus.DONE)]
    open_, resolved = partition(blockers, tasks)
    assert [b.task for b in open_] == ["SK-2"]
    assert [b.task for b in resolved] == ["SK-1", "SK-3"]


def test_resolving_status_names_the_status_that_settled_it():
    assert resolving_status(_blocker(), [_task(status=TaskStatus.DONE)]) is TaskStatus.DONE
    assert resolving_status(_blocker(), [_task()]) is None


def _init_blocked_sprint(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    state = load_state(state_path(tmp_path))
    state.tasks = [_task(status=TaskStatus.PENDING)]
    dump_state(state, state_path(tmp_path))
    record_blocker("SK-052", "contradiction", "observed", list(OPTIONS), RECOMMEND, root=tmp_path)


def test_show_splits_open_from_resolved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_blocked_sprint(tmp_path)
    assert "open blockers:" in render_show(root=tmp_path)
    assert "resolved blockers:" not in render_show(root=tmp_path)

    record_task_status("SK-052", "DONE", note="operator corrected AGENTS.md out of band", root=tmp_path)
    out = render_show(root=tmp_path)
    assert "open blockers: none" in out
    assert "resolved blockers:" in out
    assert "resolved by: SK-052 -> DONE" in out
    assert "operator corrected AGENTS.md out of band" in out


def test_show_json_carries_the_split_under_derived(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_blocked_sprint(tmp_path)
    record_task_status("SK-052", "DONE", note="settled", root=tmp_path)
    payload = json.loads(render_show_json(root=tmp_path))
    assert [b["task"] for b in payload["derived"]["blockers"]["resolved"]] == ["SK-052"]
    assert payload["derived"]["blockers"]["open"] == []


def test_show_json_never_writes_derived_back_into_state(tmp_path, monkeypatch):
    """`derived` is a read-time view. state.json must not grow a key from rendering it."""
    monkeypatch.chdir(tmp_path)
    _init_blocked_sprint(tmp_path)
    render_show_json(root=tmp_path)
    on_disk = json.loads(state_path(tmp_path).read_text(encoding="utf-8"))
    assert "derived" not in on_disk


# --- final review of feat/e9-gate3-inputs: Important 3 (resolved blockers carried no
# resolution evidence in show --json, the path SKILL.md:510 actually reads) ---


def test_show_json_carries_the_resolution_evidence_for_a_settled_blocker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_blocked_sprint(tmp_path)
    record_task_status("SK-052", "DONE", note="operator corrected AGENTS.md out of band", root=tmp_path)
    payload = json.loads(render_show_json(root=tmp_path))
    resolved = payload["derived"]["blockers"]["resolved"][0]
    assert resolved["resolved_by"] == "DONE"
    assert resolved["note"] == "operator corrected AGENTS.md out of band"


def test_show_json_null_resolution_for_an_open_blocker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_blocked_sprint(tmp_path)
    payload = json.loads(render_show_json(root=tmp_path))
    open_blocker = payload["derived"]["blockers"]["open"][0]
    assert open_blocker["resolved_by"] is None
    assert open_blocker["note"] is None


def test_show_json_resolved_by_agrees_with_the_status_that_partitioned_it(tmp_path, monkeypatch):
    """Minor 5, applied to the JSON view too: `resolved_by` must come from the same
    `resolving_status` call `partition` used, not a second independent trail read that
    could disagree with it."""
    monkeypatch.chdir(tmp_path)
    _init_blocked_sprint(tmp_path)
    record_task_status("SK-052", "DONE_WITH_CONCERNS", note="shipped with a caveat", root=tmp_path)
    payload = json.loads(render_show_json(root=tmp_path))
    resolved = payload["derived"]["blockers"]["resolved"][0]
    assert resolved["resolved_by"] == "DONE_WITH_CONCERNS"


def test_a_non_resolving_note_on_an_open_blockers_task_does_not_leak_in(tmp_path, monkeypatch):
    """A blocker's task can carry a PARKED note in tasks.jsonl without being resolved -
    that note must not surface as though it settled the blocker (it stays open)."""
    monkeypatch.chdir(tmp_path)
    _init_blocked_sprint(tmp_path)
    record_task_status("SK-052", "PARKED", note="parked pending the operator", root=tmp_path)
    payload = json.loads(render_show_json(root=tmp_path))
    assert payload["derived"]["blockers"]["resolved"] == []
    open_blocker = payload["derived"]["blockers"]["open"][0]
    assert open_blocker["resolved_by"] is None
    assert open_blocker["note"] is None
