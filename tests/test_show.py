"""SK-002: show answers "what stage, what did the gates say, what's blocked" at a glance."""

from supskill_state.cli import main
from supskill_state.commands import init_sprint, render_show
from supskill_state.model import Blocker, Task, TaskStatus
from supskill_state.store import append_jsonl, dump_state, gates_path, load_state, state_path


def _state_with_activity(tmp_path):
    init_sprint("s1", slug="state-spine", root=tmp_path)
    state = load_state(state_path(tmp_path))
    state.gates["G1_sprint_doc"] = "approved"
    state.tasks = [
        Task(id="T1", seam="unit", provable="offline", status=TaskStatus.DONE),
        Task(id="T2", seam="unit", provable="offline", status=TaskStatus.PENDING),
        Task(id="T3", seam="e2e", provable="operator", status=TaskStatus.BLOCKED),
    ]
    state.blockers = [
        Blocker(
            task="T3",
            kind="needs-live-capture",
            found="entity parser returns 0 posts on all 23 profile reads",
            options=["(a) operator drives a live capture now", "(b) defer to next sprint"],
            recommend="(a) - the heuristic may be firing misleadingly",
        )
    ]
    dump_state(state, state_path(tmp_path))
    append_jsonl(
        gates_path(tmp_path),
        {"gate": "G1", "decision": "approved", "response": "yes, approved", "at": "2026-07-12T18:00:00+00:00"},
    )


def test_show_reads_stage_gates_task_counts_and_blockers_in_one_glance(tmp_path):
    _state_with_activity(tmp_path)
    output = render_show(tmp_path)
    assert "stage SCOPE" in output
    assert "G1" in output and "approved" in output and '"yes, approved"' in output
    assert "G2" in output and "G3" in output
    assert "3 total" in output
    assert "1 DONE" in output and "1 PENDING" in output and "1 BLOCKED" in output
    assert "T3" in output and "needs-live-capture" in output
    assert "(a) operator drives a live capture now" in output
    assert "recommend" in output


def test_show_makes_an_empty_gate_response_visible(tmp_path):
    init_sprint("s1", root=tmp_path)
    append_jsonl(
        gates_path(tmp_path),
        {"gate": "G2", "decision": "approved", "response": "", "at": "2026-07-12T18:00:00+00:00"},
    )
    assert 'response: ""' in render_show(tmp_path)


def test_show_without_state_is_a_clear_message_not_a_stack_trace(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["show"]) == 1
    captured = capsys.readouterr()
    assert "refused" in captured.err and "init" in captured.err
    assert "Traceback" not in captured.err


def test_cli_show_happy_path(tmp_path, monkeypatch, capsys):
    _state_with_activity(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["show"]) == 0
    assert "stage SCOPE" in capsys.readouterr().out


def test_show_tolerates_a_crash_torn_trailing_gate_line(tmp_path):
    init_sprint("s1", root=tmp_path)
    append_jsonl(
        gates_path(tmp_path),
        {"gate": "G1", "decision": "approved", "response": "yes", "at": "2026-07-12T18:00:00+00:00"},
    )
    with open(gates_path(tmp_path), "a", encoding="utf-8") as handle:  # simulate a torn append
        handle.write('{"gate": "G2", "decision": "appr')
    output = render_show(tmp_path)
    assert '"yes"' in output  # the readable prefix still renders
