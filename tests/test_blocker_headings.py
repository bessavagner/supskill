"""SK-102: a blocker silently cancels its story's unrun plan headings.

When one story spans several plan task headings, blocking it mid-way parks the
rest with no record an operator would see. The blocker's trail record now names
every plan heading that serves the blocked story, so the cancellation is visible
at Gate 3 instead of inferred.
"""

import json

from supskill_state.commands import init_sprint, record_artifact, record_blocker, render_show
from supskill_state.model import Task, TaskStatus
from supskill_state.plan_coverage import headings_for_story
from supskill_state.store import dump_state, load_state, runs_dir, state_path

PLAN = """# Plan

### Task 1: the state spine (SK-051)

Prose.

### Task 2: the guard (SK-052)

### Task 3: the guard's CLI verb (SK-052)

### Task 4: backlog bookkeeping (process)
"""

OPTIONS = ["(a) do X", "(b) do Y"]
RECOMMEND = "(a) - cheaper"


def test_headings_for_story_finds_every_heading_that_names_it():
    assert headings_for_story(PLAN, "SK-052") == [
        "### Task 2: the guard (SK-052)",
        "### Task 3: the guard's CLI verb (SK-052)",
    ]


def test_headings_for_story_is_empty_for_an_unnamed_story():
    assert headings_for_story(PLAN, "SK-999") == []


def test_headings_for_story_honours_the_configured_prefix():
    plan = "### Task 1: a thing (PLS-040)\n"
    assert headings_for_story(plan, "PLS-040", story_prefix="PLS") == ["### Task 1: a thing (PLS-040)"]


def test_headings_for_story_ignores_a_fenced_example():
    """plan_task_headings is already fence-aware; this pins that we inherit it."""
    plan = "```\n### Task 9: quoted example (SK-052)\n```\n### Task 2: real (SK-052)\n"
    assert headings_for_story(plan, "SK-052") == ["### Task 2: real (SK-052)"]


def _init_with_plan(tmp_path, plan_text=PLAN):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    (tmp_path / "plan.md").write_text(plan_text, encoding="utf-8")
    record_artifact("dev_plan", "plan.md", root=tmp_path)
    state = load_state(state_path(tmp_path))
    state.tasks = [Task(id="SK-052", seam="unit", provable="offline", status=TaskStatus.PENDING)]
    dump_state(state, state_path(tmp_path))


def _blocker_records(tmp_path):
    path = runs_dir(tmp_path) / "s1" / "blockers.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_the_blocker_trail_names_the_stories_plan_headings(tmp_path):
    _init_with_plan(tmp_path)
    record_blocker("SK-052", "contradiction", "observed", list(OPTIONS), RECOMMEND, root=tmp_path)
    assert _blocker_records(tmp_path)[0]["plan_headings"] == [
        "### Task 2: the guard (SK-052)",
        "### Task 3: the guard's CLI verb (SK-052)",
    ]


def test_no_recorded_dev_plan_records_an_empty_list_and_never_refuses(tmp_path):
    """A blocker is the more important record: a missing plan must not block writing it."""
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    state = load_state(state_path(tmp_path))
    state.tasks = [Task(id="SK-052", seam="unit", provable="offline", status=TaskStatus.PENDING)]
    dump_state(state, state_path(tmp_path))
    record_blocker("SK-052", "contradiction", "observed", list(OPTIONS), RECOMMEND, root=tmp_path)
    assert _blocker_records(tmp_path)[0]["plan_headings"] == []


def test_a_recorded_dev_plan_that_vanished_records_an_empty_list(tmp_path):
    _init_with_plan(tmp_path)
    (tmp_path / "plan.md").unlink()
    record_blocker("SK-052", "contradiction", "observed", list(OPTIONS), RECOMMEND, root=tmp_path)
    assert _blocker_records(tmp_path)[0]["plan_headings"] == []


def test_state_json_gains_no_plan_headings_field(tmp_path):
    """The headings live in the trail only - the schema does not move."""
    _init_with_plan(tmp_path)
    record_blocker("SK-052", "contradiction", "observed", list(OPTIONS), RECOMMEND, root=tmp_path)
    on_disk = json.loads(state_path(tmp_path).read_text(encoding="utf-8"))
    assert "plan_headings" not in on_disk["blockers"][0]


def test_show_names_the_cancelled_headings_under_the_open_blocker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_with_plan(tmp_path)
    record_blocker("SK-052", "contradiction", "observed", list(OPTIONS), RECOMMEND, root=tmp_path)
    out = render_show(root=tmp_path)
    assert "plan headings this blocker halted:" in out
    assert "### Task 3: the guard's CLI verb (SK-052)" in out
