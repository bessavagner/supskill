"""SK-132: a blocker's answer gets a verb.

block records options[] and recommend; nothing recorded which option was chosen.
This does - and deliberately does NOT decide resolution, which stays SK-103's
derivation from task status.
"""

import json

import pytest

from supskill_state.commands import init_sprint, record_blocker, record_decision
from supskill_state.errors import StateError
from supskill_state.model import Task, TaskStatus
from supskill_state.store import dump_state, load_state, require_aware_utc_iso, runs_dir, state_path


def _seed_one_task(root, task_id):
    """Populate state.tasks so record_blocker has a task to attach to.

    Same mechanism as tests/test_block.py's _init_with_task, minus the
    init_sprint call the fixture already makes.
    """
    state = load_state(state_path(root))
    state.tasks = [Task(id=task_id, seam="e2e", provable="operator", status=TaskStatus.PENDING)]
    dump_state(state, state_path(root))


def _blocker_rows(tmp_path, sprint_dir="s10"):
    path = runs_dir(tmp_path) / sprint_dir / "blockers.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.fixture
def blocked(tmp_path, monkeypatch):
    """A sprint with one recorded blocker on SK-001, offering (a) and (b)."""
    monkeypatch.chdir(tmp_path)
    init_sprint("s10", backlog="backlog.md", root=tmp_path)
    # Populate tasks[] the way the suite's other blocker tests do - copy the exact
    # helper tests/test_block.py uses rather than inventing a second path.
    _seed_one_task(tmp_path, "SK-001")
    record_blocker(
        "SK-001",
        kind="plan-mandated",
        found="the plan mandates a transport that does not run",
        options=["(a) fix against the plan", "(b) keep the plan and carry the finding"],
        recommend="(a) - because the transport is unrunnable as specified",
        root=tmp_path,
    )
    return tmp_path


def test_records_the_chosen_option_and_the_operator_response_verbatim(blocked):
    record_decision("SK-001", "(a)", "go with (a), the transport is the actual defect", root=blocked)

    decisions = [r for r in _blocker_rows(blocked) if r.get("row") == "decision"]
    assert len(decisions) == 1
    assert decisions[0]["task"] == "SK-001"
    assert decisions[0]["option"] == "a"
    assert decisions[0]["response"] == "go with (a), the transport is the actual defect"
    assert decisions[0]["batched"] is False
    require_aware_utc_iso(decisions[0]["at"], "decision.at")


def test_refuses_an_option_label_the_blocker_never_offered(blocked):
    with pytest.raises(StateError, match="never offered"):
        record_decision("SK-001", "(c)", "go with c", root=blocked)

    assert [r for r in _blocker_rows(blocked) if r.get("row") == "decision"] == []


def test_refuses_an_empty_response(blocked):
    with pytest.raises(StateError, match="--response"):
        record_decision("SK-001", "(a)", "   ", root=blocked)

    assert [r for r in _blocker_rows(blocked) if r.get("row") == "decision"] == []


def test_refuses_a_task_with_no_recorded_blocker(blocked):
    with pytest.raises(StateError, match="no blocker"):
        record_decision("SK-999", "(a)", "go with a", root=blocked)


def test_refuses_deciding_the_same_blocker_twice(blocked):
    record_decision("SK-001", "(a)", "go with a", root=blocked)

    with pytest.raises(StateError, match="already decided"):
        record_decision("SK-001", "(b)", "changed my mind", root=blocked)


def test_does_not_resolve_the_blocker_by_itself(blocked):
    """SK-103 keeps owning resolution: a decided blocker whose task is still
    BLOCKED is answered, not settled."""
    from supskill_state.blockers import partition
    from supskill_state.store import load_state, state_path

    record_decision("SK-001", "(a)", "go with a", root=blocked)

    state = load_state(state_path(blocked))
    open_, resolved = partition(state.blockers, state.tasks)
    assert len(open_) == 1
    assert resolved == []


def test_state_json_gains_no_key(blocked):
    from supskill_state.store import state_path

    before = state_path(blocked).read_bytes()
    record_decision("SK-001", "(a)", "go with a", root=blocked)
    assert state_path(blocked).read_bytes() == before


def test_a_blocker_whose_free_text_kind_is_decision_does_not_masquerade_as_one(blocked):
    """The discriminator must not collide with Blocker.kind's free text.

    --kind has no allow-list (Blocker.kind: str), so a blocker legally recorded with
    kind="decision" writes a row whose "kind" field is the string "decision". If the
    decision row used "kind" as its own discriminator, record_decision's dedupe scan
    would mistake that blocker row for a decision row and then KeyError on
    record['option'] - a blocker row has "options" (plural), not "option". The
    discriminator is "row", a key record_blocker never writes, so the two shapes
    cannot collide.
    """
    _seed_one_task(blocked, "SK-002")
    record_blocker(
        "SK-002",
        kind="decision",  # legal free text; --kind has no allow-list
        found="a blocker that names itself decision",
        options=["(a) x", "(b) y"],
        recommend="(a) - because",
        root=blocked,
    )

    record_decision("SK-002", "(a)", "go with a", root=blocked)  # must not raise KeyError

    decisions = [r for r in _blocker_rows(blocked) if r.get("row") == "decision"]
    assert [d["task"] for d in decisions] == ["SK-002"]
