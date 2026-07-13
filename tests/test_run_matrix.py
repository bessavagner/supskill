"""SK-013: the init-or-resume-or-refuse matrix, one test per CLI-reachable cell.

The conductor's prose (SKILL.md) implements the matrix; this suite pins the
CLI behavior each cell relies on, against a real .supskill/ in a temp dir.
The dangerous cell is the third: init over existing state must refuse and
name --archive - the conductor inherits the refusal, never the flag.
"""

import json

import pytest

from supskill_state.cli import main
from supskill_state.scratch import normalize_sprint_id
from supskill_state.store import state_path


def test_cell_no_state_init_then_dispatch_lands_on_default_entry(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s2", "--backlog", "backlog.md"]) == 0
    capsys.readouterr()
    assert main(["show", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["stage"] == "SCOPE"


def test_cell_no_state_show_refuses_naming_the_missing_state_file(tmp_path, monkeypatch, capsys):
    # SKILL.md step 1 branches to init on this exact phrase - the conductor's cell-1 trigger
    monkeypatch.chdir(tmp_path)
    assert main(["show", "--json"]) == 1
    assert "no state file" in capsys.readouterr().err


@pytest.mark.parametrize("entry", ["PLAN", "EXECUTE"])
def test_cell_no_state_entry_flag_lands_dispatch_on_the_entry_stage(tmp_path, monkeypatch, capsys, entry):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s2", "--entry", entry]) == 0
    capsys.readouterr()
    assert main(["show", "--json"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["stage"] == entry
    assert state["sprint"]["entry"] == entry


def test_cell_resume_is_read_only(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s2", "--backlog", "backlog.md"]) == 0
    before = state_path(tmp_path).read_bytes()
    assert main(["show", "--json"]) == 0
    assert main(["show"]) == 0
    assert state_path(tmp_path).read_bytes() == before  # resume mutates nothing


def test_same_sprint_in_any_case_normalizes_to_one_id():
    # the conductor compares the requested id with sprint.id via this rule:
    # S2 and s2 are the same sprint and must resume, not collide
    assert normalize_sprint_id("S2") == normalize_sprint_id("s2") == "s2"


def test_cell_mismatch_init_refuses_and_names_archive_without_using_it(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s2", "--backlog", "backlog.md"]) == 0
    before = state_path(tmp_path).read_bytes()
    capsys.readouterr()
    assert main(["init", "s99", "--backlog", "backlog.md"]) == 1
    err = capsys.readouterr().err
    assert "refused" in err and "--archive" in err
    assert state_path(tmp_path).read_bytes() == before  # nothing archived, nothing clobbered
