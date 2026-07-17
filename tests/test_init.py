"""SK-002: init creates the sprint layout, honors entry points, never clobbers."""

import pytest

from supskill_state.cli import main
from supskill_state.commands import init_sprint
from supskill_state.errors import StateError
from supskill_state.model import Stage
from supskill_state.store import gates_path, load_state, runs_dir, state_path, supskill_dir


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
