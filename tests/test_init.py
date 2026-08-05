"""SK-002: init creates the sprint layout, honors entry points, never clobbers."""

import pytest

from supskill_state.cli import main
from supskill_state.commands import init_sprint
from supskill_state.errors import StateError
from supskill_state.model import Blocker, Stage, Task, TaskStatus
from supskill_state.store import (
    dump_state,
    gates_path,
    load_state,
    runs_dir,
    state_path,
    supskill_dir,
)


def test_init_creates_state_gates_and_runs_dir(tmp_path):
    state = init_sprint(
        "S1", slug="state-spine", branch="feat/e1-state-spine", backlog="backlog.md", root=tmp_path
    )
    assert state_path(tmp_path).exists()
    assert gates_path(tmp_path).exists()
    assert gates_path(tmp_path).read_text() == ""
    assert (runs_dir(tmp_path) / "s1").is_dir()
    on_disk = load_state(state_path(tmp_path))
    assert on_disk == state
    assert on_disk.sprint.id == "S1"
    assert on_disk.sprint.scratch == ".superpowers/sdd/s1/"
    assert on_disk.stage is Stage.SCOPE
    assert on_disk.sprint.entry is Stage.SCOPE
    assert all(value is None for value in on_disk.gates.values())
    assert all(value is None for value in on_disk.artifacts.values())
    assert on_disk.tasks == [] and on_disk.blockers == []


@pytest.mark.parametrize("entry,stage", [("PLAN", Stage.PLAN), ("EXECUTE", Stage.EXECUTE)])
def test_init_entry_sets_stage_with_all_gates_null(tmp_path, entry, stage):
    state = init_sprint("s9b", entry=entry, root=tmp_path)
    assert state.stage is stage
    assert state.sprint.entry is stage
    assert all(value is None for value in state.gates.values())


@pytest.mark.parametrize("bad_entry", ["REFINE", "REVIEW", "anything"])
def test_init_rejects_non_entry_stages(tmp_path, bad_entry):
    with pytest.raises(StateError):
        init_sprint("s1", entry=bad_entry, root=tmp_path)
    assert not supskill_dir(tmp_path).exists()


def test_init_rejects_bad_sprint_id_before_touching_disk(tmp_path):
    with pytest.raises(StateError, match="refusing"):
        init_sprint("s 1", root=tmp_path)
    assert not supskill_dir(tmp_path).exists()


def test_init_refuses_to_clobber_existing_state(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    before = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match="--archive"):
        init_sprint("s2", backlog="backlog.md", root=tmp_path)
    assert state_path(tmp_path).read_bytes() == before


def test_init_archive_preserves_old_state_and_gates(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    gates_path(tmp_path).write_text('{"gate": "G1"}\n')  # stand-in for a recorded decision
    old_state = state_path(tmp_path).read_bytes()

    state = init_sprint("s2", archive=True, backlog="backlog.md", root=tmp_path)

    archive = runs_dir(tmp_path) / "s1" / "archive-1"
    assert (archive / "state.json").read_bytes() == old_state
    assert (archive / "gates.jsonl").read_text() == '{"gate": "G1"}\n'
    assert state.sprint.id == "s2"
    assert gates_path(tmp_path).read_text() == ""  # fresh, empty trail for the new run


def test_init_archive_twice_numbers_archives(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    init_sprint("s1", archive=True, backlog="backlog.md", root=tmp_path)
    init_sprint("s1", archive=True, backlog="backlog.md", root=tmp_path)
    assert (runs_dir(tmp_path) / "s1" / "archive-1" / "state.json").exists()
    assert (runs_dir(tmp_path) / "s1" / "archive-2" / "state.json").exists()


def test_init_archives_unreadable_old_state_under_unknown(tmp_path):
    supskill_dir(tmp_path).mkdir(parents=True)
    state_path(tmp_path).write_text("{corrupted")
    init_sprint("s1", archive=True, backlog="backlog.md", root=tmp_path)
    assert (runs_dir(tmp_path) / "unknown" / "archive-1" / "state.json").read_text() == "{corrupted"


def test_cli_init_happy_path(tmp_path, monkeypatch, capsys):
    from supskill_state.cli import main

    monkeypatch.chdir(tmp_path)
    assert main(["init", "s1", "--entry", "EXECUTE"]) == 0
    assert "s1" in capsys.readouterr().out
    assert load_state(state_path(tmp_path)).stage is Stage.EXECUTE


def test_cli_init_refusal_exits_nonzero_with_reason(tmp_path, monkeypatch, capsys):
    from supskill_state.cli import main

    monkeypatch.chdir(tmp_path)
    assert main(["init", "s1", "--backlog", "backlog.md"]) == 0
    assert main(["init", "s2", "--backlog", "backlog.md"]) == 1
    assert "refused" in capsys.readouterr().err


def test_init_scope_entry_without_backlog_refuses_before_touching_disk(tmp_path):
    # a SCOPE sprint with backlog null has nothing to scope and no verb to fix it (S3 DoR finding 2)
    with pytest.raises(StateError, match="--backlog"):
        init_sprint("s1", root=tmp_path)  # SCOPE is the default entry
    with pytest.raises(StateError, match="--backlog"):
        init_sprint("s1", entry="SCOPE", root=tmp_path)
    assert not supskill_dir(tmp_path).exists()


@pytest.mark.parametrize("entry", ["PLAN", "EXECUTE"])
def test_init_non_scope_entry_still_allows_a_null_backlog(tmp_path, entry):
    assert init_sprint("s9b", entry=entry, root=tmp_path).backlog is None


def test_cli_init_scope_without_backlog_refuses(tmp_path, monkeypatch, capsys):
    from supskill_state.cli import main

    monkeypatch.chdir(tmp_path)
    assert main(["init", "s1"]) == 1
    assert "--backlog" in capsys.readouterr().err
    assert not supskill_dir(tmp_path).exists()


def test_cli_config_sets_the_story_id_prefix_and_reports_the_previous_value(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["config", "--story-id-prefix", "BLK"]) == 0
    assert "set story id prefix: BLK (was: SK)" in capsys.readouterr().out
    assert main(["config", "--story-id-prefix", "PROJ"]) == 0
    assert "set story id prefix: PROJ (was: BLK)" in capsys.readouterr().out


def test_cli_config_rejects_an_invalid_prefix(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["config", "--story-id-prefix", "blk"]) == 1
    assert "story-id-prefix" in capsys.readouterr().err


# --- SK-115: archiving a sprint that never recorded its Gate 3 decision ---

def _at_review_with_g3(tmp_path, decision):
    """A sprint resting at REVIEW, with G3 either recorded or still open."""
    init_sprint("s5", backlog="backlog.md", root=tmp_path)
    state = load_state(state_path(tmp_path))
    state.stage = Stage.REVIEW
    state.gates["G3_review"] = decision
    from supskill_state.store import dump_state

    dump_state(state, state_path(tmp_path))


def test_archive_refuses_over_a_review_sprint_with_no_gate_three_decision(tmp_path):
    _at_review_with_g3(tmp_path, None)
    before = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match="no Gate 3 decision") as excinfo:
        init_sprint("s6", entry="EXECUTE", archive=True, root=tmp_path)
    message = str(excinfo.value)
    assert "s5" in message
    assert "gate --id G3" in message  # names the verb that records the answer
    assert state_path(tmp_path).read_bytes() == before  # nothing archived, nothing created
    assert not (runs_dir(tmp_path) / "s5" / "archive-1").exists()


@pytest.mark.parametrize("decision", ["approved", "rejected", "replan"])
def test_archive_proceeds_once_any_gate_three_decision_is_recorded(tmp_path, decision):
    _at_review_with_g3(tmp_path, decision)
    state = init_sprint("s6", entry="EXECUTE", archive=True, root=tmp_path)
    assert state.sprint.id == "s6"
    assert (runs_dir(tmp_path) / "s5" / "archive-1" / "state.json").exists()


@pytest.mark.parametrize("stage", [Stage.SCOPE, Stage.PLAN, Stage.EXECUTE])
def test_archive_is_untouched_for_a_sprint_that_never_reached_review(tmp_path, stage):
    # the row is about REVIEW specifically: an earlier stage has no G3 to record
    init_sprint("s5", backlog="backlog.md", root=tmp_path)
    state = load_state(state_path(tmp_path))
    state.stage = stage
    from supskill_state.store import dump_state

    dump_state(state, state_path(tmp_path))
    assert init_sprint("s6", entry="EXECUTE", archive=True, root=tmp_path).sprint.id == "s6"


def test_an_unreadable_old_state_is_still_archived_never_refused(tmp_path):
    # SK-115 must not turn "never destroy prior state" into "never archive it"
    supskill_dir(tmp_path).mkdir(parents=True)
    state_path(tmp_path).write_text("{corrupted")
    init_sprint("s6", entry="EXECUTE", archive=True, root=tmp_path)
    assert (runs_dir(tmp_path) / "unknown" / "archive-1" / "state.json").read_text() == "{corrupted"


def test_a_non_utf8_old_state_is_still_archived_never_refused(tmp_path):
    # a state.json that isn't even valid UTF-8: read_text raises UnicodeDecodeError,
    # not OSError - the "unreadable old state" rule must cover this too
    supskill_dir(tmp_path).mkdir(parents=True)
    garbage = b"\xff\xfe\x00\x01garbage not utf8"
    state_path(tmp_path).write_bytes(garbage)
    init_sprint("s6", entry="EXECUTE", archive=True, root=tmp_path)
    assert (runs_dir(tmp_path) / "unknown" / "archive-1" / "state.json").read_bytes() == garbage


# --- SK-116: recording the continuation ---

def test_an_execute_entry_over_an_archived_sprint_inherits_its_id(tmp_path):
    # requiring the conductor to remember --continues would reproduce the defect:
    # a fact recorded only when an agent thinks to record it
    init_sprint("s5", backlog="backlog.md", root=tmp_path)
    state = init_sprint("s6", entry="EXECUTE", archive=True, root=tmp_path)
    assert state.sprint.continues == "s5"


def test_an_explicit_continues_wins_over_the_inherited_id(tmp_path):
    init_sprint("s5", backlog="backlog.md", root=tmp_path)
    state = init_sprint("s6", entry="EXECUTE", archive=True, continues="s3", root=tmp_path)
    assert state.sprint.continues == "s3"


def test_a_first_sprint_continues_nothing(tmp_path):
    assert init_sprint("s1", entry="EXECUTE", root=tmp_path).sprint.continues is None


def test_a_scope_entry_never_inherits_a_continuation(tmp_path):
    # a SCOPE sprint scopes its own doc from the backlog; it continues nothing
    init_sprint("s5", backlog="backlog.md", root=tmp_path)
    state = init_sprint("s6", backlog="backlog.md", archive=True, root=tmp_path)
    assert state.sprint.continues is None


def test_continues_with_a_scope_entry_is_refused_before_touching_disk(tmp_path):
    with pytest.raises(StateError, match="continues nothing"):
        init_sprint("s6", backlog="backlog.md", continues="s5", root=tmp_path)
    assert not supskill_dir(tmp_path).exists()


def test_an_empty_continues_is_refused(tmp_path):
    with pytest.raises(StateError, match="--continues"):
        init_sprint("s6", entry="EXECUTE", continues="   ", root=tmp_path)


def test_cli_init_accepts_continues(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s6", "--entry", "EXECUTE", "--continues", "s5"]) == 0
    assert load_state(state_path(tmp_path)).sprint.continues == "s5"


# --- SK-143: archiving a sprint whose work is still live ---


def _live_sprint(tmp_path, *, stage, tasks, blockers=()):
    """A sprint parked mid-flight, the way an operator's `.supskill/` actually looks."""
    init_sprint("s5", backlog="backlog.md", root=tmp_path)
    state = load_state(state_path(tmp_path))
    state.stage = stage
    state.tasks = [Task(id=i, seam="unit", provable="offline", status=s) for i, s in tasks]
    state.blockers = [
        Blocker(task=t, kind="ambiguity", found="mid-drain", options=["(a)", "(b)"], recommend="(a)")
        for t in blockers
    ]
    dump_state(state, state_path(tmp_path))


def test_archive_refuses_over_a_sprint_with_a_non_terminal_task(tmp_path):
    # SK-143: E10 made every stage but REVIEW-with-null-G3 silently archivable
    _live_sprint(tmp_path, stage=Stage.EXECUTE, tasks=[("SK-001", TaskStatus.PENDING)])
    before = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match="still live") as excinfo:
        init_sprint("s6", backlog="backlog.md", archive=True, root=tmp_path)
    message = str(excinfo.value)
    assert "s5" in message
    assert "SK-001" in message  # names the work it would have retired
    assert state_path(tmp_path).read_bytes() == before
    assert not (runs_dir(tmp_path) / "s5" / "archive-1").exists()


def test_archive_refuses_over_a_sprint_with_an_open_blocker(tmp_path):
    # turmarium B5's exact shape: BLOCKED is terminal, so the task check alone misses it
    _live_sprint(
        tmp_path,
        stage=Stage.EXECUTE,
        tasks=[("SK-001", TaskStatus.DONE), ("SK-002", TaskStatus.BLOCKED)],
        blockers=["SK-002"],
    )
    with pytest.raises(StateError, match="still live") as excinfo:
        init_sprint("s6", backlog="backlog.md", archive=True, root=tmp_path)
    assert "SK-002" in str(excinfo.value)
    assert not (runs_dir(tmp_path) / "s5" / "archive-1").exists()


def test_archive_proceeds_when_every_task_is_terminal_and_no_blocker_is_open(tmp_path):
    _live_sprint(
        tmp_path,
        stage=Stage.EXECUTE,
        tasks=[("SK-001", TaskStatus.DONE), ("SK-002", TaskStatus.DONE_WITH_CONCERNS)],
        blockers=["SK-002"],  # resolved: its task reached a successful terminal status
    )
    state = init_sprint("s6", backlog="backlog.md", archive=True, root=tmp_path)
    assert state.sprint.id == "s6"
    assert (runs_dir(tmp_path) / "s5" / "archive-1" / "state.json").exists()


def test_a_recorded_gate_three_closes_a_sprint_that_still_holds_an_open_blocker(tmp_path):
    """The ordering that keeps SK-143 from stranding a sprint permanently.

    BLOCKED is terminal, so `advance --to REVIEW` lets a sprint reach REVIEW carrying an
    open blocker - and that blocker can never resolve afterwards, because resolution is
    derived from its task's status and the task is already terminal. If an open blocker
    outranked a recorded G3, that sprint could never be archived by any command, which
    is a worse failure than the one SK-143 fixes. Gate 3 is the operator ruling on the
    whole sprint, blockers included.
    """
    _live_sprint(
        tmp_path,
        stage=Stage.REVIEW,
        tasks=[("SK-001", TaskStatus.BLOCKED)],
        blockers=["SK-001"],
    )
    state = load_state(state_path(tmp_path))
    state.gates["G3_review"] = "approved"
    dump_state(state, state_path(tmp_path))

    assert init_sprint("s6", backlog="backlog.md", archive=True, root=tmp_path).sprint.id == "s6"


def test_a_parked_task_does_not_keep_a_sprint_live(tmp_path):
    # PARKED is terminal: it names work that never ran, not work still running
    _live_sprint(tmp_path, stage=Stage.EXECUTE, tasks=[("SK-001", TaskStatus.PARKED)])
    assert init_sprint("s6", backlog="backlog.md", archive=True, root=tmp_path).sprint.id == "s6"


# --- SK-144: the backlog crosses the archive ---


def test_a_scope_entry_inherits_the_backlog_of_the_sprint_it_archives(tmp_path):
    # a bare `/supskill run <new-id>` types no flags; the trail already holds the path
    init_sprint("s5", backlog="docs/backlog.md", root=tmp_path)
    state = init_sprint("s6", archive=True, root=tmp_path)
    assert state.backlog == "docs/backlog.md"
    assert state.sprint.id == "s6"
    assert load_state(state_path(tmp_path)).backlog == "docs/backlog.md"


def test_an_explicit_backlog_wins_over_the_inherited_one(tmp_path):
    init_sprint("s5", backlog="docs/backlog.md", root=tmp_path)
    state = init_sprint("s6", archive=True, backlog="docs/backlog-02.md", root=tmp_path)
    assert state.backlog == "docs/backlog-02.md"


def test_a_scope_entry_over_a_sprint_with_no_backlog_still_refuses(tmp_path):
    # inheritance carries a recorded path; it never invents one
    init_sprint("s5", entry="EXECUTE", root=tmp_path)
    before = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match="--backlog"):
        init_sprint("s6", archive=True, root=tmp_path)
    assert state_path(tmp_path).read_bytes() == before
    assert not (runs_dir(tmp_path) / "s5" / "archive-1").exists()


def test_a_scope_entry_over_an_unreadable_state_still_refuses(tmp_path):
    supskill_dir(tmp_path).mkdir(parents=True)
    state_path(tmp_path).write_text("{corrupted")
    with pytest.raises(StateError, match="--backlog"):
        init_sprint("s6", archive=True, root=tmp_path)
    assert state_path(tmp_path).read_text() == "{corrupted"  # archived by nothing, destroyed by nothing


def test_a_first_sprint_inherits_no_backlog(tmp_path):
    with pytest.raises(StateError, match="--backlog"):
        init_sprint("s1", root=tmp_path)
    assert not supskill_dir(tmp_path).exists()


def test_cli_a_bare_archive_init_carries_the_backlog_forward(tmp_path, monkeypatch, capsys):
    # the ledgerus failure end to end: the operator typed `run s10` and nothing else
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s5", "--backlog", "docs/backlog.md"]) == 0
    assert main(["init", "s6", "--archive"]) == 0
    assert load_state(state_path(tmp_path)).backlog == "docs/backlog.md"
