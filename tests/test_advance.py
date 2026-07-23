"""SK-003: the enforcement mechanism. Gate-skipping fails loudly; refusal changes nothing."""

import pytest

from supskill_state.cli import main
from supskill_state.commands import (
    advance_stage,
    init_sprint,
    record_artifact,
    record_gate,
)
from supskill_state.errors import StateError
from supskill_state.model import Stage, Task, TaskStatus
from supskill_state.store import dump_state, load_state, state_path


def _write_doc(tmp_path, name):
    (tmp_path / name).write_text("# artifact\n")
    return name


def _refused(tmp_path, to, match):
    """Assert advance refuses with a reason naming the precondition and state byte-identical."""
    before = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match=match) as excinfo:
        advance_stage(to, root=tmp_path)
    assert state_path(tmp_path).read_bytes() == before
    return str(excinfo.value)


def _set_tasks(tmp_path, *statuses):
    state = load_state(state_path(tmp_path))
    state.tasks = [
        Task(id=f"T{i}", seam="unit", provable="offline", status=status)
        for i, status in enumerate(statuses, start=1)
    ]
    dump_state(state, state_path(tmp_path))


# --- the design's own named test, verbatim (design section 6) ---


def test_advance_to_execute_with_g2_null_refuses(tmp_path):
    # can you advance to EXECUTE with G2 == null? No.
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_gate("G1", "approved", "approved", root=tmp_path)
    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)
    advance_stage("PLAN", root=tmp_path)

    message = _refused(tmp_path, "EXECUTE", "G2_plan")
    assert "null" in message  # the reason names the failed precondition and its value


# --- one-step-forward only ---


def test_skipping_a_stage_is_impossible_regardless_of_gate_state(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    # even with every gate approved and artifacts present, you cannot skip ahead:
    # since SK-100 collapsed SCOPE and REFINE, SCOPE's one legal step is PLAN, and
    # EXECUTE and REVIEW remain unreachable in a single hop.
    record_gate("G1", "approved", "x", root=tmp_path)
    record_gate("G2", "approved", "x", root=tmp_path)
    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)
    record_artifact("dev_plan", _write_doc(tmp_path, "plan.md"), root=tmp_path)
    _refused(tmp_path, "EXECUTE", "one-step-forward")
    _refused(tmp_path, "REVIEW", "one-step-forward")


def test_backwards_and_self_transitions_are_not_expressible(tmp_path):
    init_sprint("s1", entry="EXECUTE", root=tmp_path)
    _refused(tmp_path, "SCOPE", "one-step-forward")
    _refused(tmp_path, "EXECUTE", "one-step-forward")


def test_review_is_final_nothing_to_advance_to(tmp_path):
    init_sprint("s1", entry="EXECUTE", root=tmp_path)
    _set_tasks(tmp_path, TaskStatus.DONE)  # an empty tasks[] no longer passes vacuously
    advance_stage("REVIEW", root=tmp_path)
    _refused(tmp_path, "SCOPE", "final stage")


def test_unknown_target_stage_refused(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    _refused(tmp_path, "SHIP", "unknown stage")


# --- the three preconditions, each way ---


def test_advance_to_plan_requires_a_recorded_existing_sprint_doc(tmp_path):
    # SK-100 collapsed SCOPE and REFINE: the recorded-doc precondition that used to
    # guard SCOPE -> REFINE now guards SCOPE -> PLAN, alongside G1. With G1 approved,
    # the doc is the only remaining blocker, so its absence is named on its own.
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_gate("G1", "approved", "approved", root=tmp_path)
    _refused(tmp_path, "PLAN", "sprint_doc is not recorded")

    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)
    (tmp_path / "doc.md").unlink()
    _refused(tmp_path, "PLAN", "missing file")

    _write_doc(tmp_path, "doc.md")
    assert advance_stage("PLAN", root=tmp_path).stage is Stage.PLAN


def test_advance_to_plan_requires_g1_on_top_of_the_doc(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)

    _refused(tmp_path, "PLAN", "G1_sprint_doc")  # the doc is recorded; the gate alone refuses

    record_gate("G1", "approved", "approved", root=tmp_path)
    (tmp_path / "doc.md").unlink()  # a doc that vanished after the gate is re-caught at -> PLAN
    _refused(tmp_path, "PLAN", "missing file")

    _write_doc(tmp_path, "doc.md")
    assert advance_stage("PLAN", root=tmp_path).stage is Stage.PLAN


def test_a_rejected_gate_is_not_approved(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)
    record_gate("G1", "rejected", "no - redo the scope section", root=tmp_path)
    message = _refused(tmp_path, "PLAN", "G1_sprint_doc")
    assert "rejected" in message


def test_advance_to_execute_requires_g2_and_dev_plan(tmp_path):
    init_sprint("s1", entry="PLAN", root=tmp_path)
    _set_tasks(tmp_path, TaskStatus.PENDING)
    record_gate("G2", "approved", "plan approved", root=tmp_path)
    message = _refused(tmp_path, "EXECUTE", "dev_plan is not recorded")
    record_artifact("dev_plan", _write_doc(tmp_path, "plan.md"), root=tmp_path)
    assert advance_stage("EXECUTE", root=tmp_path).stage is Stage.EXECUTE
    assert "G2_plan" not in message  # the gate was fine; only the artifact was named


def test_artifact_that_vanished_from_disk_refuses(tmp_path):
    init_sprint("s1", entry="PLAN", root=tmp_path)
    record_gate("G2", "approved", "x", root=tmp_path)
    record_artifact("dev_plan", _write_doc(tmp_path, "plan.md"), root=tmp_path)
    (tmp_path / "plan.md").unlink()
    _refused(tmp_path, "EXECUTE", "missing file")


def test_advance_to_review_requires_every_task_terminal(tmp_path):
    init_sprint("s1", entry="EXECUTE", root=tmp_path)
    _set_tasks(tmp_path, TaskStatus.DONE, TaskStatus.PENDING)
    message = _refused(tmp_path, "REVIEW", "terminal")
    assert "T2" in message  # the open task is named

    _set_tasks(
        tmp_path,
        TaskStatus.DONE,
        TaskStatus.DONE_WITH_CONCERNS,
        TaskStatus.BLOCKED,
        TaskStatus.PARKED,
    )
    assert advance_stage("REVIEW", root=tmp_path).stage is Stage.REVIEW


# --- entry-aware, asserted both ways (D7 x D2) ---


def test_entry_execute_reaches_review_with_all_gates_null(tmp_path):
    # a sprint that STARTS at EXECUTE never crosses the G2 check - legal by design
    init_sprint("s9b", entry="EXECUTE", root=tmp_path)
    _set_tasks(tmp_path, TaskStatus.DONE, TaskStatus.DONE)
    state = advance_stage("REVIEW", root=tmp_path)
    assert state.stage is Stage.REVIEW
    assert all(value is None for value in state.gates.values())


def test_entry_scope_can_never_reach_execute_without_both_gates(tmp_path):
    # whatever sequence of calls is attempted
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)
    record_artifact("dev_plan", _write_doc(tmp_path, "plan.md"), root=tmp_path)
    _set_tasks(tmp_path, TaskStatus.PENDING)

    _refused(tmp_path, "EXECUTE", "one-step-forward")  # from SCOPE
    _refused(tmp_path, "PLAN", "G1_sprint_doc")  # G1 not approved

    record_gate("G1", "approved", "x", root=tmp_path)
    advance_stage("PLAN", root=tmp_path)
    _refused(tmp_path, "EXECUTE", "G2_plan")  # G1 alone is not enough

    record_gate("G2", "approved", "x", root=tmp_path)
    assert advance_stage("EXECUTE", root=tmp_path).stage is Stage.EXECUTE  # both gates crossed


# --- CLI surface ---


def test_cli_refusal_is_nonzero_and_names_the_precondition(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s1", "--entry", "PLAN"]) == 0
    assert main(["advance", "--to", "EXECUTE"]) == 1
    err = capsys.readouterr().err
    assert "refused" in err and "G2_plan" in err


# --- an empty tasks[] made the strongest precondition pass vacuously (S4 DoR finding 2) ---


def test_advance_to_execute_refuses_an_empty_task_list(tmp_path):
    # a sprint with no tasks has nothing to execute (S4 DoR finding 2)
    init_sprint("s1", entry="PLAN", root=tmp_path)
    record_gate("G2", "approved", "plan approved", root=tmp_path)
    record_artifact("dev_plan", _write_doc(tmp_path, "plan.md"), root=tmp_path)
    message = _refused(tmp_path, "EXECUTE", r"tasks\[\] is empty")
    assert "tasks --from" in message  # the refusal names the way forward

    _set_tasks(tmp_path, TaskStatus.PENDING)
    assert advance_stage("EXECUTE", root=tmp_path).stage is Stage.EXECUTE


def test_advance_to_review_refuses_an_empty_task_list_including_an_entry_execute_sprint(tmp_path):
    # the vacuous pass this closes: nothing is non-terminal in an empty list, and an
    # entry=EXECUTE sprint never crosses the -> EXECUTE guard, so REVIEW is its only one
    init_sprint("s9b", entry="EXECUTE", root=tmp_path)
    _refused(tmp_path, "REVIEW", r"tasks\[\] is empty")

    _set_tasks(tmp_path, TaskStatus.DONE)
    assert advance_stage("REVIEW", root=tmp_path).stage is Stage.REVIEW
