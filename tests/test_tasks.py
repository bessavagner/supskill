"""SK-033: tasks[] is loaded from the sprint doc's proof lines - the verb, never a second parser.

E5 cannot block, park, or map a single SDD status until this exists: init writes
tasks=[] (commands.py:77) and record_blocker refuses a task it cannot find
(commands.py:250).
"""

from pathlib import Path

import pytest

from supskill_state.cli import main
from supskill_state.commands import init_sprint, load_tasks
from supskill_state.errors import StateError
from supskill_state.model import TaskStatus
from supskill_state.store import load_state, state_path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPRINT_04 = "docs/plans/sprints/backlog-01/sprint-04-plan-gate2.md"

DOC = """## Stories

### SK-001 — first · 3 · M
- **proof:** seam=unit · impact=local · provable=offline

### SK-002 — second · 2 · M
- **proof:** seam=app-level · impact=journey · provable=operator
"""


def _sprint(tmp_path, text=DOC, name="doc.md"):
    init_sprint("s4", backlog="backlog.md", root=tmp_path)
    (tmp_path / name).write_text(text, encoding="utf-8")
    return name


def test_tasks_are_story_shaped_and_in_document_order(tmp_path):
    doc = _sprint(tmp_path)
    state = load_tasks(doc, root=tmp_path)
    assert [(t.id, t.seam, t.provable, t.status) for t in state.tasks] == [
        ("SK-001", "unit", "offline", TaskStatus.PENDING),
        ("SK-002", "app-level", "operator", TaskStatus.PENDING),
    ]
    # and it is persisted, not just returned
    assert [t.id for t in load_state(state_path(tmp_path)).tasks] == ["SK-001", "SK-002"]


def test_dogfood_this_sprints_own_doc_classifies_its_four_stories(tmp_path):
    # the state lives in tmp_path; the doc lives in THIS repo. An absolute doc path is
    # resolved as-is by the verb, because Path("/a") / "/b" == Path("/b").
    init_sprint("s4", backlog="backlog.md", root=tmp_path)
    state = load_tasks(str(REPO_ROOT / SPRINT_04), root=tmp_path)
    assert [(t.id, t.seam, t.provable) for t in state.tasks] == [
        ("SK-030", "app-level", "operator"),
        ("SK-031", "app-level", "operator"),
        ("SK-032", "app-level", "operator"),
        ("SK-033", "unit", "offline"),
    ]


def test_a_doc_with_no_proof_lines_refuses(tmp_path):
    doc = _sprint(tmp_path, text="# a doc with prose and no stories\n")
    with pytest.raises(StateError, match="no proof lines"):
        load_tasks(doc, root=tmp_path)
    assert load_state(state_path(tmp_path)).tasks == []


def test_a_missing_doc_refuses_before_touching_state(tmp_path):
    _sprint(tmp_path)
    before = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match="no such doc"):
        load_tasks("ghost.md", root=tmp_path)
    assert state_path(tmp_path).read_bytes() == before


def test_a_grammar_violation_refuses_with_the_parsers_own_message(tmp_path):
    doc = _sprint(tmp_path, text=DOC.replace("seam=unit", "seam=vibes"))
    with pytest.raises(StateError, match="unknown seam token 'vibes'"):
        load_tasks(doc, root=tmp_path)


def test_reloading_while_every_task_is_still_pending_is_idempotent(tmp_path):
    doc = _sprint(tmp_path)
    load_tasks(doc, root=tmp_path)
    state = load_tasks(doc, root=tmp_path)
    assert [t.id for t in state.tasks] == ["SK-001", "SK-002"]  # no duplicates, no growth


def test_reloading_over_progress_refuses_rather_than_resetting_it(tmp_path):
    doc = _sprint(tmp_path)
    load_tasks(doc, root=tmp_path)
    state = load_state(state_path(tmp_path))
    state.tasks[0].status = TaskStatus.DONE
    from supskill_state.store import dump_state

    dump_state(state, state_path(tmp_path))

    with pytest.raises(StateError, match="--archive") as excinfo:
        load_tasks(doc, root=tmp_path)
    assert "SK-001" in str(excinfo.value)  # the task whose progress would be lost is named
    assert load_state(state_path(tmp_path)).tasks[0].status is TaskStatus.DONE  # untouched


def test_cli_tasks_reports_what_it_loaded(tmp_path, monkeypatch, capsys):
    doc = _sprint(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["tasks", "--from", doc]) == 0
    assert "loaded 2 tasks: SK-001, SK-002" in capsys.readouterr().out
    assert main(["tasks", "--from", "ghost.md"]) == 1
    assert "no such doc" in capsys.readouterr().err
