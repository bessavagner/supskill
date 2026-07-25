# Gate 3's Inputs Implementation Plan (SK-102, SK-103, SK-104, SK-109)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the four inputs Gate 3 assembles its question from trustworthy — settled blockers stop reading as live, a blocker names the plan headings it cancelled, a stale review package is refused rather than reviewed, and an estimated cost row is marked as an estimate.

**Architecture:** Three of the four rows are the epic's through-line — *a guard validates the shape of a thing and never its preconditions, and an agent's judgment quietly patched the hole*. Each fix follows the shape this repo already established: a pure, offline-testable function in its own small module; a thin `cli.py` verb or a `commands.py` call site; one conductor sentence in `SKILL.md`; a dedicated test file. No task adds a schema field — every new fact lands in an append-only trail under `runs/<id>/`, which is where Gate 3 already reads.

**Tech Stack:** Python 3.11+, stdlib only. `pytest` (offline, no network, no LLM calls). `ruff check` at 100 columns. `uv` for the venv.

## Global Constraints

- **No new `state.json` schema fields.** `SCHEMA_VERSION` stays `1` and `state_to_dict` / `state_from_dict` are untouched by Tasks 1–4. Derived facts are computed at read time; recorded facts go to `runs/<id>/*.jsonl`.
- **Trail FIRST, state SECOND.** Any verb that writes both writes the append-only trail before `state.json`, per `commands.py`'s module docstring.
- **No AI attribution** in commit messages (global user rule). No `Co-Authored-By`, no "Generated with".
- **No mypy** — it is not installed. Lint is `uv run ruff check .` (100 cols); tests are `uv run pytest` and must stay offline.
- **Guard modules follow one shape:** pure check + `refusal()` string + thin `cli.py` verb + dedicated test + one `SKILL.md` sentence. `plan_guard.py`, `replan_guard.py` and `artifact_tracking.py` are the templates.
- **No dead pure modules.** SK-055/SK-056 were filed as defects precisely because `review.py`'s `aggregate()` had no production caller. Every function this plan adds is wired to a real call site in the same task that creates it.
- **supskill runs no git command that changes the operator's repo.** Read-only git (`rev-parse`, `ls-files`, `merge-base`) is fine; `git add`, `git commit`, branch creation are not.
- **Baseline:** at the tip of `feat/e9-gate3-inputs` (commit `bd16e34`), `uv run pytest` → **485 passed**. Every task ends with the full suite green.
- **Branch:** all work lands on `feat/e9-gate3-inputs`, merged to `main` with `--no-ff` at the end.

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `scripts/supskill_state/blockers.py` | create | Pure: partition blockers into open/resolved from their tasks' statuses (SK-103). |
| `scripts/supskill_state/review_package.py` | create | Pure: is the recorded review package stale against current HEAD, plus its `refusal()` (SK-104). |
| `scripts/supskill_state/plan_coverage.py` | modify | Gains `headings_for_story` — the story→plan-heading lookup SK-102 records. |
| `scripts/supskill_state/commands.py` | modify | `render_show`/`render_show_json` consume `blockers.py`; `record_blocker` records plan headings; `record_cost` gains `estimated`; new `record_package`. |
| `scripts/supskill_state/cli.py` | modify | New `package` and `review-guard` verbs; `cost --estimated` flag. |
| `skills/supskill/SKILL.md` | modify | One conductor sentence per check (Task 5). |
| `skills/supskill/references/review-notes.md` | modify | The `--estimated` rule for mailbox-teammate reviewers (Task 5). |
| `tests/test_blockers_resolved.py` | create | SK-103. |
| `tests/test_blocker_headings.py` | create | SK-102. |
| `tests/test_review_guard.py` | create | SK-104. |
| `tests/test_cost.py` | modify | SK-109. |
| `tests/test_skill_frontmatter.py` | modify | Body cap 515 → 540, with the decision recorded in the docstring (Task 5). |
| `docs/plans/sprints/backlog-01/backlog.md` | modify | Mark the four rows done (Task 6). |

---

### Task 1: A blocker whose task succeeded stops reading as open (SK-103)

**Why:** After both playset s1 blockers were resolved, `show --json` still reported "open blockers: 2" and Gate 3 presented two settled decisions as live ones. The operator had to reconstruct resolution from the tasks trail.

**Design decision locked here:** resolution is **derived**, not recorded. A blocker is resolved iff its task reached a *successful* terminal status. There is no `unblock` verb: `task --id X --status DONE --note "..."` already records how it was settled, in `runs/<id>/tasks.jsonl`, and a second way to move a blocker could disagree with the task's own status.

**Divergence from the row as filed — record this in the mark-done commit, do not edit the row.** SK-103 says "a terminal non-blocked status". `TaskStatus.PARKED` is terminal and not `BLOCKED`, but a parked task is one that *never ran* because it was downstream of a blocker — that is not resolution. So the resolving set is `{DONE, DONE_WITH_CONCERNS}`, and `PARKED` leaves a blocker open, which is what Gate 3 needs to see.

**Files:**
- Create: `scripts/supskill_state/blockers.py`
- Modify: `scripts/supskill_state/commands.py` (`render_show`, `render_show_json`, plus a `_last_task_notes` helper)
- Test: `tests/test_blockers_resolved.py`

**Interfaces:**
- Consumes: `model.Blocker`, `model.Task`, `model.TaskStatus`.
- Produces:
  - `blockers.RESOLVING_STATUSES: frozenset[TaskStatus]`
  - `blockers.partition(blockers: list[Blocker], tasks: list[Task]) -> tuple[list[Blocker], list[Blocker]]` returning `(open_, resolved)`, each in the input's order.
  - `blockers.resolving_status(blocker: Blocker, tasks: list[Task]) -> TaskStatus | None` — the status that resolved it, or `None` if it is still open. Task 2 does not use this; Task 5's prose refers to it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_blockers_resolved.py`:

```python
"""SK-103: a blocker whose task succeeded is settled, and must stop reading as live.

playset s1 resolved both its blockers and `show` still said "open blockers: 2",
so Gate 3 presented two settled decisions as live ones. Resolution is derived
from the task's own status - there is no second verb that could disagree with it.
"""

import json

import pytest

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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_blockers_resolved.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'supskill_state.blockers'`

- [ ] **Step 3: Write the module**

Create `scripts/supskill_state/blockers.py`:

```python
"""SK-103: which recorded blockers are still live, derived from their tasks.

`block` mirrors a blocker into state.blockers and flips its task to BLOCKED, and
nothing ever took it back out. On playset s1 both blockers were resolved, both
tasks moved on, and `show` still reported "open blockers: 2" - so Gate 3, the one
irreversible decision in the product, presented two settled questions as live
ones and the operator reconstructed resolution from the tasks trail by hand.

Resolution is DERIVED here, never recorded. `task --id X --status DONE --note`
already writes how a blocker was settled to runs/<id>/tasks.jsonl; a second verb
that could move a blocker independently could also disagree with its task, and
then Gate 3 would have two answers and no rule for picking one.

The resolving set is DONE and DONE_WITH_CONCERNS - successful terminal statuses.
PARKED is terminal too, and deliberately excluded: a parked task is one that never
ran because it sat downstream of a blocker, which is the opposite of settled. The
backlog row says "terminal non-blocked status"; this is narrower on purpose, and
the divergence is recorded rather than the row rewritten.

The ceiling: this says a blocker's task moved on, not that the operator made a
good call. A task marked DONE with an empty note resolves its blocker here.
"""

from __future__ import annotations

from .model import Blocker, Task, TaskStatus

# Successful terminal statuses only. PARKED is terminal but means "never ran".
RESOLVING_STATUSES: frozenset[TaskStatus] = frozenset(
    (TaskStatus.DONE, TaskStatus.DONE_WITH_CONCERNS)
)


def resolving_status(blocker: Blocker, tasks: list[Task]) -> TaskStatus | None:
    """The status that settled this blocker, or None while it is still open.

    A blocker whose task is not in `tasks` at all stays open: missing evidence is
    never read as resolution.
    """
    task = next((t for t in tasks if t.id == blocker.task), None)
    if task is None or task.status not in RESOLVING_STATUSES:
        return None
    return task.status


def partition(blockers: list[Blocker], tasks: list[Task]) -> tuple[list[Blocker], list[Blocker]]:
    """`(open, resolved)`, each preserving the order the blockers were recorded in."""
    open_: list[Blocker] = []
    resolved: list[Blocker] = []
    for blocker in blockers:
        (resolved if resolving_status(blocker, tasks) else open_).append(blocker)
    return open_, resolved
```

- [ ] **Step 4: Run the pure-function tests**

Run: `uv run pytest tests/test_blockers_resolved.py -q -k "not show"`
Expected: PASS (7 tests). The four `show`/`show_json` tests still fail.

- [ ] **Step 5: Wire it into `render_show`**

In `scripts/supskill_state/commands.py`, add `blockers` to the package imports at the top:

```python
from . import blockers as blockers_view, config, store
```

Add this helper immediately after `_last_gate_responses` (around line 260):

```python
def _last_task_notes(root: Path | None, sprint_id: str) -> dict[str, tuple[str, str | None]]:
    """Each task's last recorded (status, note) from runs/<id>/tasks.jsonl.

    Same shape as _last_gate_responses: a read-only convenience for `show`, and a
    crash-torn tail is skipped rather than allowed to take the command down.
    """
    path = store.runs_dir(root) / normalize_sprint_id(sprint_id) / "tasks.jsonl"
    notes: dict[str, tuple[str, str | None]] = {}
    if not path.exists():
        return notes
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        task = record.get("task")
        if isinstance(task, str):
            notes[task] = (record.get("status", ""), record.get("note"))
    return notes
```

Now replace the blocker-rendering block at the end of `render_show` (currently `if state.blockers: ... else: lines.append("open blockers: none")`) with:

```python
    open_blockers, resolved_blockers = blockers_view.partition(state.blockers, state.tasks)
    notes = _last_task_notes(root, state.sprint.id) if resolved_blockers else {}

    if open_blockers:
        lines.append("open blockers:")
        for blocker in open_blockers:
            lines.append(f"  {blocker.task} [{blocker.kind}] {blocker.found}")
            for option in blocker.options:
                lines.append(f"      {option}")
            lines.append(f"    recommend: {blocker.recommend}")
    else:
        lines.append("open blockers: none")

    if resolved_blockers:
        lines.append("resolved blockers:")
        for blocker in resolved_blockers:
            lines.append(f"  {blocker.task} [{blocker.kind}] {blocker.found}")
            status, note = notes.get(blocker.task, ("", None))
            lines.append(f"    resolved by: {blocker.task} -> {status}")
            if note:
                lines.append(f'    note: "{note}"')
    return "\n".join(lines) + "\n"
```

- [ ] **Step 6: Wire it into `render_show_json`**

Replace the body of `render_show_json` in `scripts/supskill_state/commands.py`:

```python
def render_show_json(root: Path | None = None) -> str:
    """The resume read-contract: the full state as JSON, plus a `derived` view.

    The conductor's dispatch consumes this instead of parsing state.json
    itself - the schema stays the CLI's concern, never skill prose's.

    `derived` is computed at read time and never written back: state.json has no
    such key and gains none (SK-103). Everything under it is a function of the
    state above it, so a reader that ignores `derived` still sees the whole truth.
    """
    root = store.resolve_root(root)
    state = store.load_state(store.state_path(root))
    payload = state_to_dict(state)
    open_blockers, resolved_blockers = blockers_view.partition(state.blockers, state.tasks)
    payload["derived"] = {
        "blockers": {
            "open": [_blocker_to_dict(b) for b in open_blockers],
            "resolved": [_blocker_to_dict(b) for b in resolved_blockers],
        }
    }
    return json.dumps(payload, indent=2) + "\n"


def _blocker_to_dict(blocker: Blocker) -> dict:
    return {
        "task": blocker.task,
        "kind": blocker.kind,
        "found": blocker.found,
        "options": list(blocker.options),
        "recommend": blocker.recommend,
    }
```

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all of `tests/test_blockers_resolved.py` passes, and the pre-existing 485 still pass.

`tests/test_show.py::test_show_reads_stage_gates_task_counts_and_blockers_in_one_glance`
was checked against this change and needs **no edit**: its blocker sits on task `T3`
whose status is `BLOCKED`, so it stays open, renders under the unchanged
`open blockers:` heading, and every one of its assertions still holds. If any other
show test does break, the split is the intended behavior — fix the assertion, not the
module.

- [ ] **Step 8: Commit**

```bash
git add scripts/supskill_state/blockers.py scripts/supskill_state/commands.py tests/test_blockers_resolved.py
git commit -m "feat(SK-103): a blocker whose task succeeded reads as resolved"
```

---

### Task 2: A blocker names the plan headings it cancelled (SK-102)

**Why:** When one story spans several plan task headings, blocking it mid-way parks the remaining headings without a record an operator would see. Discovered structurally — playset's plans happened not to hit it.

**Design decision locked here — and its ceiling, which must go in the docstring.** `state.json` tracks *stories*, not plan headings; nothing in the spine knows which of a story's headings already ran. So this records **every plan heading that names the blocked story**, not a computed "remaining" subset. That makes the cancellation observable — Gate 3 can say *this blocker halted SK-052, which the plan spends headings 3 through 5 on* — without inventing heading-level tracking the spine does not have. Do not fake the narrower claim.

**Files:**
- Modify: `scripts/supskill_state/plan_coverage.py` (add `headings_for_story`)
- Modify: `scripts/supskill_state/commands.py` (`record_blocker` writes `plan_headings` to the trail; `render_show` reads it back)
- Test: `tests/test_blocker_headings.py`

**Interfaces:**
- Consumes: `plan_coverage.plan_task_headings` (existing — fence-aware), `_story_id_pattern` (existing, module-private).
- Produces: `plan_coverage.headings_for_story(plan_text: str, story: str, story_prefix: str = "SK") -> list[str]` — every `### Task N ...` heading naming `story`, in document order.

- [ ] **Step 1: Write the failing test**

Create `tests/test_blocker_headings.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_blocker_headings.py -q`
Expected: FAIL — `ImportError: cannot import name 'headings_for_story'`

- [ ] **Step 3: Add `headings_for_story` to `plan_coverage.py`**

Append to `scripts/supskill_state/plan_coverage.py`:

```python
def headings_for_story(plan_text: str, story: str, story_prefix: str = "SK") -> list[str]:
    """Every '### Task N ...' heading that names `story`, in document order (SK-102).

    Fence-awareness is inherited from plan_task_headings: a quoted example inside a
    code fence is not a real task and does not appear here either.

    This answers "which plan headings serve this story", NOT "which of them already
    ran" - the spine tracks stories, not headings, and nothing in it knows where a
    drain stopped. A caller that needs the narrower claim does not get it from here.
    """
    pattern = _story_id_pattern(story_prefix)
    return [
        heading
        for heading in plan_task_headings(plan_text)
        if story in pattern.findall(heading)
    ]
```

- [ ] **Step 4: Run the pure-function tests**

Run: `uv run pytest tests/test_blocker_headings.py -q -k "headings_for_story"`
Expected: PASS (4 tests).

- [ ] **Step 5: Record the headings in `record_blocker`'s trail**

In `scripts/supskill_state/commands.py`, import the new function alongside the existing one:

```python
from .plan_coverage import headings_for_story, validate_plan_coverage
```

Add this helper directly above `record_blocker`:

```python
def _blocked_story_headings(state: State, task_id: str, root: Path) -> list[str]:
    """The recorded dev plan's headings that serve `task_id` (SK-102).

    Best-effort by design: no recorded dev_plan, a recorded path that has since
    vanished, or a plan that cannot be decoded all return []. A blocker is the more
    important record of the two - refusing to write one because the plan moved would
    trade the escalation for the annotation.

    These are the story's headings, not its UNRUN headings: state tracks stories, so
    nothing here knows where the drain stopped. Gate 3 reads this as "the blocker
    halted a story the plan spends these headings on".
    """
    plan = state.artifacts.get("dev_plan")
    if not plan:
        return []
    plan_path = root / plan
    try:
        text = plan_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return headings_for_story(text, task_id, story_prefix=config.load_story_id_prefix(root))
```

In `record_blocker`, after the `task is None` refusal and before building the `Blocker`, add:

```python
    plan_headings = _blocked_story_headings(state, task_id, root)
```

and add the key to the `store.append_jsonl` record — the trail only, never the `Blocker` dataclass:

```python
            "recommend": blocker.recommend,
            "plan_headings": plan_headings,  # SK-102: trail only; the schema does not move
            "at": store.now_utc_iso(),
```

- [ ] **Step 6: Surface them in `render_show`**

In `commands.py`, add a helper next to `_last_task_notes`:

```python
def _blocker_plan_headings(root: Path | None, sprint_id: str) -> dict[str, list[str]]:
    """Each task's last-recorded cancelled plan headings from runs/<id>/blockers.jsonl."""
    path = store.runs_dir(root) / normalize_sprint_id(sprint_id) / "blockers.jsonl"
    found: dict[str, list[str]] = {}
    if not path.exists():
        return found
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        task = record.get("task")
        headings = record.get("plan_headings")
        if isinstance(task, str) and isinstance(headings, list):
            found[task] = [h for h in headings if isinstance(h, str)]
    return found
```

In `render_show`, compute it once next to `notes`:

```python
    notes = _last_task_notes(root, state.sprint.id) if resolved_blockers else {}
    headings = _blocker_plan_headings(root, state.sprint.id) if open_blockers else {}
```

and inside the open-blocker loop, after the `recommend:` line:

```python
            lines.append(f"    recommend: {blocker.recommend}")
            halted = headings.get(blocker.task, [])
            if halted:
                lines.append("    plan headings this blocker halted:")
                for heading in halted:
                    lines.append(f"      {heading}")
```

The heading list is omitted entirely when empty rather than printed as an empty
label: a blocker recorded before this field existed, or one recorded with no dev
plan on file, must not render as "halted: (nothing)" — that reads as a positive
finding when it is an absence of data.

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add scripts/supskill_state/plan_coverage.py scripts/supskill_state/commands.py tests/test_blocker_headings.py
git commit -m "feat(SK-102): a blocker names the plan headings it halted"
```

---

### Task 3: A stale review package is refused, not reviewed (SK-104)

**Why:** On playset s1, out-of-band commits landed after EXECUTE's halt and the recorded `review-final.diff` no longer matched the branch. The conductor caught it by judgment and regenerated. PAR reviewing a diff that is not the branch is the worst failure this product has, because it produces a *clean* review of the wrong thing.

**Design decision locked here:** **refuse, never regenerate.** This is the `artifact-guard` posture — supskill reports, the operator acts, and the way past a refusal is to change the thing it names. The refusal prints the exact `review-package` command to run.

**Why a recording verb is required, not just a guard:** EXECUTE's halt prose ends the run — REVIEW is a separate `/supskill run` invocation. So the package's HEAD cannot live in the conductor's memory across the boundary (invariant 5: resume from `state.json` alone). It goes to `runs/<id>/package.jsonl`, an append-only trail, keeping the schema fixed.

**Files:**
- Create: `scripts/supskill_state/review_package.py`
- Modify: `scripts/supskill_state/commands.py` (add `record_package`)
- Modify: `scripts/supskill_state/cli.py` (add `package` and `review-guard` verbs)
- Test: `tests/test_review_guard.py`

**Interfaces:**
- Consumes: `store.append_jsonl`, `store.runs_dir`, `scratch.normalize_sprint_id`, `errors.StateError`.
- Produces:
  - `review_package.is_stale(recorded_head: str, current_head: str) -> bool`
  - `review_package.last_record(root: Path, sprint_id: str) -> dict | None`
  - `review_package.git_head(root: str) -> str` (raises `StateError` when git cannot answer)
  - `review_package.refusal(record: dict, current_head: str) -> str`
  - `commands.record_package(base: str, head: str, path: str, *, root: Path | None = None) -> None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_review_guard.py`:

```python
"""SK-104: REVIEW refuses a review package that HEAD has moved past.

playset s1: out-of-band commits landed after EXECUTE's halt, the recorded
review-final.diff no longer matched the branch, and only the conductor's judgment
caught it. PAR reviewing a diff that is not the branch returns a CLEAN review of
the wrong thing - the most expensive way this product can fail quietly.
"""

import json
import subprocess

import pytest

from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_package
from supskill_state.errors import StateError
from supskill_state.review_package import git_head, is_stale, last_record, refusal
from supskill_state.store import require_aware_utc_iso, runs_dir

RECORD = {"base": "a1b2c3d", "head": "f9e8d7c", "path": ".superpowers/sdd/s1/review-final.diff"}


def test_the_same_head_is_not_stale():
    assert is_stale("f9e8d7c", "f9e8d7c") is False


def test_a_moved_head_is_stale():
    assert is_stale("f9e8d7c", "0123456") is True


def test_surrounding_whitespace_never_makes_a_package_look_stale():
    assert is_stale(" f9e8d7c\n", "f9e8d7c") is False


def test_an_empty_recorded_head_is_stale():
    """Never read missing evidence as freshness."""
    assert is_stale("", "f9e8d7c") is True


def test_refusal_names_both_shas_and_the_command_to_run():
    text = refusal(RECORD, "0123456")
    assert "f9e8d7c" in text and "0123456" in text and "a1b2c3d" in text
    assert "review-package" in text
    assert ".superpowers/sdd/s1/review-final.diff" in text


def test_refusal_on_a_fresh_package_is_itself_refused():
    with pytest.raises(StateError):
        refusal(RECORD, "f9e8d7c")


def test_record_package_writes_an_append_only_trail(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_package("a1b2c3d", "f9e8d7c", "scratch/review-final.diff", root=tmp_path)
    record_package("a1b2c3d", "0123456", "scratch/review-final.diff", root=tmp_path)
    lines = (runs_dir(tmp_path) / "s1" / "package.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    require_aware_utc_iso(json.loads(lines[0])["at"], "package.at")


def test_last_record_returns_the_most_recent(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_package("a1b2c3d", "f9e8d7c", "scratch/review-final.diff", root=tmp_path)
    record_package("a1b2c3d", "0123456", "scratch/review-final.diff", root=tmp_path)
    assert last_record(tmp_path, "s1")["head"] == "0123456"


def test_last_record_is_none_when_nothing_was_ever_recorded(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    assert last_record(tmp_path, "s1") is None


def test_record_package_refuses_empty_shas(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    with pytest.raises(StateError):
        record_package("", "f9e8d7c", "scratch/review-final.diff", root=tmp_path)
    with pytest.raises(StateError):
        record_package("a1b2c3d", "  ", "scratch/review-final.diff", root=tmp_path)


def _git(tmp_path, *args):
    subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)


def _repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-qm", "one")


def test_git_head_reads_the_current_sha(tmp_path):
    _repo(tmp_path)
    assert len(git_head(str(tmp_path))) == 40


def test_git_head_raises_rather_than_guessing_outside_a_repo(tmp_path):
    with pytest.raises(StateError):
        git_head(str(tmp_path))


def test_guard_passes_when_head_has_not_moved(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    head = git_head(str(tmp_path))
    record_package("a1b2c3d", head, "scratch/review-final.diff", root=tmp_path)
    assert main(["review-guard"]) == 0
    assert "matches HEAD" in capsys.readouterr().out


def test_guard_refuses_when_head_moved_past_the_package(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_package("a1b2c3d", git_head(str(tmp_path)), "scratch/review-final.diff", root=tmp_path)
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")
    _git(tmp_path, "commit", "-aqm", "two")
    assert main(["review-guard"]) == 1
    assert "review-package" in capsys.readouterr().err


def test_guard_refuses_when_no_package_was_ever_recorded(tmp_path, monkeypatch, capsys):
    """EXECUTE not recording its package is exactly the state that hid the s1 defect."""
    monkeypatch.chdir(tmp_path)
    _repo(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    assert main(["review-guard"]) == 1
    assert "no review package" in capsys.readouterr().err


def test_the_package_verb_records_through_the_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    assert main(["package", "--base", "a1b2c3d", "--head", "f9e8d7c",
                 "--path", "scratch/review-final.diff"]) == 0
    assert "recorded review package" in capsys.readouterr().out
    assert last_record(tmp_path, "s1")["base"] == "a1b2c3d"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_review_guard.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'supskill_state.review_package'`

- [ ] **Step 3: Write the module**

Create `scripts/supskill_state/review_package.py`:

```python
"""SK-104: is the recorded review package still this branch? (the guard)

EXECUTE's last act is to leave `<scratch>/review-final.diff` on disk for REVIEW to
read, and then the run STOPS - REVIEW is the next `/supskill run` invocation. On
playset s1, out-of-band commits landed in that gap, the diff no longer matched the
branch, and nothing checked: only the conductor's judgment caught it and
regenerated. PAR handed a diff that is not the branch returns a clean review of the
wrong code, which is the most expensive way this product can fail, because it fails
quietly and at the one gate that is irreversible.

Refuse, never regenerate. This is `artifact_tracking`'s posture: the guard reports
and the operator acts, and the way past a refusal in this package is to change the
thing it names. The refusal prints the exact `review-package` command.

Because EXECUTE and REVIEW are separate invocations, the package's HEAD cannot live
in the conductor's memory across the boundary (invariant 5). It is recorded to
`runs/<id>/package.jsonl` - an append-only trail, so the schema does not move.

The ceiling: this compares SHAs. A package regenerated at the right HEAD but written
from the wrong base, or a diff hand-edited after the fact, walks past it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .errors import StateError
from .scratch import normalize_sprint_id


def is_stale(recorded_head: str, current_head: str) -> bool:
    """Has HEAD moved since the package was cut?

    An empty or whitespace-only recorded head is stale: missing evidence is never
    read as freshness. Surrounding whitespace is stripped from both sides first, so
    a SHA captured with a trailing newline does not false-refuse.
    """
    recorded = (recorded_head or "").strip()
    if not recorded:
        return True
    return recorded != (current_head or "").strip()


def git_head(root: str) -> str:
    """`git rev-parse HEAD` in `root`. Raises rather than guessing (read-only)."""
    result = subprocess.run(
        ["git", "-C", root, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        raise StateError(f"git rev-parse HEAD failed in {root}: {detail}")
    return result.stdout.strip()


def package_path(root: Path, sprint_id: str) -> Path:
    return Path(root) / ".supskill" / "runs" / normalize_sprint_id(sprint_id) / "package.jsonl"


def last_record(root: Path, sprint_id: str) -> dict | None:
    """The most recently recorded package, or None if EXECUTE never recorded one.

    A crash-torn or malformed tail line is skipped, the same rule `show` applies to
    gates.jsonl: a torn trail must not take the guard down.
    """
    path = package_path(root, sprint_id)
    if not path.exists():
        return None
    found: dict | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            found = record
    return found


def missing_refusal(sprint_id: str) -> str:
    """What the conductor reports when EXECUTE recorded no package at all."""
    return (
        f"no review package was recorded for sprint {sprint_id}, so there is nothing to "
        "prove PAR would review this branch.\n"
        "EXECUTE's halt is what records it, right after it writes the diff:\n"
        "  supskill-state package --base <merge-base> --head <HEAD> "
        "--path <scratch>/review-final.diff\n"
        "An unrecorded package is exactly the state that hid this defect on playset s1: "
        "the diff on disk looked fine and nothing could say which commits it covered.\n"
        "Nothing was dispatched and no gate was called."
    )


def refusal(record: dict, current_head: str) -> str:
    """What the conductor reports, verbatim, when the recorded package is stale."""
    recorded_head = str(record.get("head", ""))
    if not is_stale(recorded_head, current_head):
        raise StateError(
            "refusal() called on a package that matches HEAD; there is nothing to refuse"
        )
    base = str(record.get("base", "?"))
    path = str(record.get("path", "<scratch>/review-final.diff"))
    return (
        "the recorded review package is stale: HEAD has moved since EXECUTE cut it.\n"
        f"  package base:  {base}\n"
        f"  package head:  {recorded_head or '(none recorded)'}\n"
        f"  HEAD now:      {current_head}\n"
        f"  package file:  {path}\n"
        "PAR would review a diff that is not this branch, and a review of the wrong code "
        "comes back clean - which is why this refuses instead of proceeding.\n"
        "Regenerate the package from the dispatch root, re-record it, then re-run this "
        "stage:\n"
        f"  review-package $(git merge-base <default-branch> HEAD) HEAD {path}\n"
        f"  supskill-state package --base $(git merge-base <default-branch> HEAD) "
        f"--head {current_head} --path {path}\n"
        "Nothing was dispatched and no gate was called: G3 is still open.\n"
        "This compares SHAs; a package cut at the right HEAD from the wrong base walks "
        "past it."
    )
```

- [ ] **Step 4: Add `record_package` to `commands.py`**

Add to `scripts/supskill_state/commands.py`, immediately after `record_cost`:

```python
def record_package(
    base: str,
    head: str,
    path: str,
    *,
    root: Path | None = None,
) -> None:
    """Record the review package EXECUTE just cut (SK-104).

    Pure telemetry, the same shape as record_cost: state.json is read only to place
    the trail file by sprint.id, and nothing is written back to it. What this buys is
    the one fact REVIEW cannot otherwise have - EXECUTE and REVIEW are separate
    `/supskill run` invocations, so the SHA the package covers has to survive on disk
    or not at all (invariant 5).
    """
    root = store.resolve_root(root)
    for flag, value in (("--base", base), ("--head", head), ("--path", path)):
        if not (value or "").strip():
            raise StateError(f"a review package record requires a non-empty {flag}")
    state = store.load_state(store.state_path(root))
    package_file = store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / "package.jsonl"
    store.append_jsonl(
        package_file,
        {
            "base": base.strip(),
            "head": head.strip(),
            "path": path.strip(),
            "at": store.now_utc_iso(),
        },
    )
```

- [ ] **Step 5: Wire both verbs into `cli.py`**

Add `review_package` to the package import block at the top of `scripts/supskill_state/cli.py` (keep the list alphabetical):

```python
from . import (
    artifact_tracking,
    commands,
    commit_scope,
    config,
    plan_guard,
    preflight,
    replan_guard,
    review_package,
    store,
    worktree,
)
```

Register both in `build_parser`, after `_add_artifact_guard(subparsers)`:

```python
    _add_package(subparsers)
    _add_review_guard(subparsers)
```

Add the two verb blocks next to the other guards:

```python
def _add_package(subparsers) -> None:
    sub = subparsers.add_parser(
        "package",
        help="record the review package EXECUTE just cut, so REVIEW can prove it is current",
    )
    sub.add_argument("--base", required=True, help="the package's base SHA (the merge-base)")
    sub.add_argument("--head", required=True, help="HEAD at the moment the package was cut")
    sub.add_argument("--path", required=True, help="where the diff was written, e.g. <scratch>/review-final.diff")
    sub.set_defaults(func=_cmd_package)


def _cmd_package(args) -> int:
    commands.record_package(args.base, args.head, args.path)
    print(f"recorded review package: {args.base.strip()}..{args.head.strip()} -> {args.path.strip()}")
    return 0


def _add_review_guard(subparsers) -> None:
    sub = subparsers.add_parser(
        "review-guard",
        help="is the recorded review package still this branch? exit 1 means refuse",
    )
    sub.add_argument(
        "--dir",
        default=None,
        dest="root",
        help="the repo root whose .supskill/ holds this sprint's state; default cwd",
    )
    sub.set_defaults(func=_cmd_review_guard)


def _cmd_review_guard(args) -> int:
    root = store.resolve_root(Path(args.root) if args.root else None)
    state = store.load_state(store.state_path(root))
    record = review_package.last_record(root, state.sprint.id)
    if record is None:
        print(review_package.missing_refusal(state.sprint.id), file=sys.stderr)
        return 1
    current = review_package.git_head(str(root))
    if review_package.is_stale(str(record.get("head", "")), current):
        print(review_package.refusal(record, current), file=sys.stderr)
        return 1
    print(f"review-guard: the recorded package matches HEAD ({current})")
    return 0
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/test_review_guard.py -q`
Expected: PASS (16 tests).

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add scripts/supskill_state/review_package.py scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_review_guard.py
git commit -m "feat(SK-104): refuse a review package HEAD has moved past"
```

---

### Task 4: An estimated cost row says it is an estimate (SK-109)

**Why:** PAR reviewers run as mailbox teammates whose transcripts the conductor cannot retrieve, so it recorded each at an estimated 70k. The ledger now silently mixes measured and estimated rows with no marker. playset s3's REVIEW rows came back measured — but `0.3.0` changed no accounting code, so that was operational luck, not a fix.

**Design decision locked here:** of the row's two options — "dispatch reviewers as trackable tasks, or mark estimated cost rows as estimates" — this takes the second. It is the 2-point half, it makes the existing ledger honest immediately, and it does not disturb PAR's dispatch discipline (no cross-visibility between reviewers), which is load-bearing for D9.

**Files:**
- Modify: `scripts/supskill_state/commands.py` (`record_cost` gains `estimated`)
- Modify: `scripts/supskill_state/cli.py` (`cost --estimated`)
- Test: `tests/test_cost.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `commands.record_cost(..., estimated: bool = False)` — writes `"estimated": <bool>` on **every** row, measured ones included, so an old row without the key is distinguishable from a new measured one.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cost.py`. **Add no helpers and no imports** — the file already
has `main` imported and a `_costs(tmp_path, sprint_dir="s10")` reader, and its
sprint id throughout is `s10`. Use both as they are:

```python
def test_a_cost_row_is_measured_unless_it_says_otherwise(tmp_path):
    """SK-109: the key is always present, so a row that predates it stays distinguishable."""
    init_sprint("s10", backlog="backlog.md", root=tmp_path)
    record_cost("REVIEW", 63016, label="reviewer-a", root=tmp_path)
    assert _costs(tmp_path)[0]["estimated"] is False


def test_an_estimated_row_is_marked(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)
    record_cost("REVIEW", 70000, label="reviewer-b", estimated=True, root=tmp_path)
    assert _costs(tmp_path)[0]["estimated"] is True


def test_the_cli_marks_an_estimate_and_says_so(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    init_sprint("s10", backlog="backlog.md", root=tmp_path)
    assert main(["cost", "--stage", "REVIEW", "--label", "reviewer-b",
                 "--tokens", "70000", "--estimated"]) == 0
    assert "estimated" in capsys.readouterr().out
    assert _costs(tmp_path)[0]["estimated"] is True


def test_the_cli_defaults_to_measured(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_sprint("s10", backlog="backlog.md", root=tmp_path)
    assert main(["cost", "--stage", "PLAN", "--tokens", "1234"]) == 0
    assert _costs(tmp_path)[0]["estimated"] is False
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_cost.py -q`
Expected: FAIL — `TypeError: record_cost() got an unexpected keyword argument 'estimated'`

- [ ] **Step 3: Add the parameter**

In `scripts/supskill_state/commands.py`, change `record_cost`'s signature and record:

```python
def record_cost(
    stage: str,
    tokens: int,
    *,
    label: str | None = None,
    tool_uses: int | None = None,
    duration_ms: int | None = None,
    estimated: bool = False,
    root: Path | None = None,
) -> None:
```

Extend its docstring with:

```
    SK-109: `estimated` marks a row whose token count the conductor could not
    retrieve. PAR's reviewers run as mailbox teammates and their transcripts are
    not readable from the controller, so those rows were guessed at 70k and filed
    beside measured ones with nothing to tell them apart. The key is written on
    EVERY row, measured included - a row that predates this field has no key at
    all, and that difference is the point.
```

and add the key to the appended record:

```python
            "duration_ms": duration_ms,
            "estimated": estimated,
            "at": store.now_utc_iso(),
```

- [ ] **Step 4: Add the flag in `cli.py`**

In `_add_cost`, after the `--duration-ms` argument:

```python
    sub.add_argument(
        "--estimated",
        action="store_true",
        help="this token count was estimated, not read from a dispatch's reported usage "
             "(e.g. a mailbox teammate whose transcript the conductor cannot retrieve)",
    )
```

and in `_cmd_cost`:

```python
def _cmd_cost(args) -> int:
    commands.record_cost(
        args.stage,
        args.tokens,
        label=args.label,
        tool_uses=args.tool_uses,
        duration_ms=args.duration_ms,
        estimated=args.estimated,
    )
    where = f"{args.stage}/{args.label}" if args.label else args.stage
    marker = " (estimated)" if args.estimated else ""
    print(f"recorded cost: {where} tokens={args.tokens}{marker}")
    return 0
```

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_cost.py
git commit -m "feat(SK-109): mark a cost row whose tokens were estimated"
```

---

### Task 5: The conductor's prose for all four checks

**Why:** Every mechanism above is reachable only if `SKILL.md` tells the conductor to run it. The last sprint made this its own commit (`81f175a`), and this follows that shape.

**The cap.** `tests/test_skill_frontmatter.py` pins the body at ≤515 lines and the body is at **513** — two lines of headroom against four checks. Raise the cap to **540** and record the reason in the docstring, exactly as the 500→515 raise did. This is an anti-bloat guard, not a loader limit.

**Files:**
- Modify: `skills/supskill/SKILL.md`
- Modify: `skills/supskill/references/review-notes.md`
- Modify: `tests/test_skill_frontmatter.py`

**Interfaces:**
- Consumes: the verbs from Tasks 1–4 (`review-guard`, `package`, `cost --estimated`) and the `show` output shape from Tasks 1–2.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Raise the cap and record why**

In `tests/test_skill_frontmatter.py`, update the module docstring line:

```
non-empty <=1024, combined description + when_to_use <=1536, body <=540 lines.
```

Extend the docstring paragraph that explains the budget:

```
The body budget is an anti-bloat guard, not a loader limit: 500 was Claude Code's
own "keep SKILL.md under 500 lines" authoring tip (contexts/02), and the body sat
at exactly 500 when SK-112's task-review file-handoff paragraph landed. The cap
was raised to 515 as a decision rather than squeezing the paragraph out. Raised
again to 540 for the Gate-3 group (SK-102/103/104/109): four checks, each needing
a conductor sentence, against two lines of headroom. Raise it as a decision, and
say here why - never by deleting prose that earns its place.
```

Rename the test and its assertion:

```python
def test_body_stays_under_540_lines():
    _, body = read_frontmatter_and_body()
    assert len(body) <= 540
```

- [ ] **Step 2: Run it to confirm it passes at the current length**

Run: `uv run pytest tests/test_skill_frontmatter.py -q`
Expected: PASS.

- [ ] **Step 3: Add EXECUTE's package recording (SK-104's other half)**

In `skills/supskill/SKILL.md`, in the `BASE` is recorded, never derived bullet, directly after the `review-package $(git -C <dispatch-root> merge-base <default-branch> HEAD) HEAD <scratch>/review-final.diff` line and its two continuation lines, add:

```markdown
  Then record what that package covers, so REVIEW can prove it is still the branch:
  `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state package --base <the merge-base you just used> --head $(git -C <dispatch-root> rev-parse HEAD) --path <scratch>/review-final.diff`
  EXECUTE and REVIEW are different runs; a SHA you do not write down does not survive
  the gap (SK-104).
```

- [ ] **Step 4: Add REVIEW's staleness check**

In the **The REVIEW stage** section, insert before the sentence beginning `PAR: two adversarial reviewers`:

```markdown
Before you dispatch either reviewer, run `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state review-guard`: exit 1 means HEAD has moved past the package EXECUTE recorded, or that EXECUTE never recorded one. Relay the refusal verbatim and stop — do not regenerate the diff yourself. PAR handed a diff that is not this branch comes back *clean*, which is why this refuses rather than repairs (SK-104).
```

- [ ] **Step 5: Add the estimated-cost rule**

In the same `PAR: two adversarial reviewers …` paragraph, replace:

```
cost each as it completes, `cost --stage REVIEW --label reviewer-a|reviewer-b`.
```

with:

```
cost each as it completes, `cost --stage REVIEW --label reviewer-a|reviewer-b` — and add `--estimated` whenever you could not read that dispatch's reported usage, which is every reviewer dispatched as a mailbox teammate. A guessed number filed beside a measured one is the ledger lying quietly (SK-109).
```

Then in `skills/supskill/references/review-notes.md`, replace the two-line cost sentence in **Dispatch**:

```markdown
Cost each dispatch as it completes: `cost --stage REVIEW --label reviewer-a` /
`cost --stage REVIEW --label reviewer-b`. A reviewer dispatched as a mailbox
teammate reports no retrievable usage, so its token count is your estimate and
the row must carry `--estimated`. Recording an estimate as if it were measured is
what made this row: s2's reviewers were both filed at a round 70k with nothing in
`costs.jsonl` saying so.
```

- [ ] **Step 6: Add Gate 3's reading of resolved blockers and halted headings**

In the **Gate 3 — one decision, not two** section, replace the sentence beginning `The question batches every open blocker` with:

```markdown
The question batches every **open** blocker, every parked task, every `DONE_WITH_CONCERNS` note, and every `runs/<id>/review.jsonl` finding at `confidence=high` or `confidence=actionable` — nothing silently dropped. Take open from `show --json`'s `derived.blockers.open`: a blocker whose task reached `DONE` or `DONE_WITH_CONCERNS` is settled and belongs in `derived.blockers.resolved`, which you report as context and never re-ask (SK-103). Where a blocker names the plan headings it halted, name them too — a story the plan spends three headings on, blocked at the first, cancelled two the operator never saw (SK-102).
```

- [ ] **Step 7: Verify the frontmatter test and the whole suite**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all green. If the body now exceeds 540, move the longest addition into a reference file rather than raising the cap a second time in one sprint.

- [ ] **Step 8: Verify the plugin still validates**

Run: `uv run pytest tests/test_plugin_manifest.py tests/test_skill_frontmatter.py tests/test_prompt_templates.py -q`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add skills/supskill/SKILL.md skills/supskill/references/review-notes.md tests/test_skill_frontmatter.py
git commit -m "docs(skill): name the four Gate-3 input checks in the conductor's prose"
```

---

### Task 6: Mark the rows done

**Why:** Repo convention — backlog bookkeeping is its own commit, separate from the code that closes the row, and a divergence between the row as filed and what shipped is recorded in the mark-done commit rather than by editing the row.

**Files:**
- Modify: `docs/plans/sprints/backlog-01/backlog.md`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces: nothing.

- [ ] **Step 1: Flip the four status cells**

In `docs/plans/sprints/backlog-01/backlog.md`, change the trailing `| ☐ |` to `| ☑ |` on the rows for **SK-102**, **SK-103**, **SK-104** and **SK-109**. Change nothing else on those rows — the row records the finding as filed, not as fixed.

- [ ] **Step 2: Add the delivery note**

After the existing `**Delivered 2026-07-24 (SK-114..117).**` paragraph, add:

```markdown
**Delivered 2026-07-25 (SK-102, SK-103, SK-104, SK-109).** The Gate-3 input group:
the highest-stakes screen in the product was assembled from four partly-untrustworthy
inputs, and each is now either derived, recorded, or refused. Three divergences from
the rows as filed, recorded here rather than by editing them. SK-103 asked for "a
terminal non-blocked status" to resolve a blocker; `PARKED` is terminal and does
**not** resolve one — a parked task never ran, which is the opposite of settled, so
the resolving set is `DONE` and `DONE_WITH_CONCERNS`. SK-103 also asked to "give
`block` an inverse"; it shipped as a derivation with no new verb, because
`task --status DONE --note` already records how a blocker was settled and a second
mover could disagree with it. SK-102 asked for "the parked headings"; what is
recorded is every plan heading serving the blocked story, because the spine tracks
stories and nothing in it knows where a drain stopped — the narrower claim would
have been fabricated. SK-109 took the second of its two options (mark estimates)
rather than the first (make reviewer dispatches trackable), which remains open as a
possibility and is not filed as a row.
```

- [ ] **Step 3: Verify the doc tests still pass**

Run: `uv run pytest tests/test_validation_docs.py tests/test_fixture_backlog.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/plans/sprints/backlog-01/backlog.md
git commit -m "docs(backlog): mark SK-102, SK-103, SK-104, SK-109 done"
```

- [ ] **Step 5: Final verification before the merge decision**

Run: `uv run pytest -q && uv run ruff check .`
Expected: **all green**, test count up from 485 by roughly 40.

Then use `superpowers:finishing-a-development-branch` — it presents merge/PR/keep/discard rather than guessing. The repo's own convention for this epic is a `--no-ff` merge to `main`.

---

## Self-Review

**Spec coverage.** SK-102 → Task 2. SK-103 → Task 1. SK-104 → Task 3 (record) + Task 5 Step 3 (EXECUTE emits it) + Task 5 Step 4 (REVIEW checks it). SK-109 → Task 4 + Task 5 Step 5. The handoff's sequencing note — "sequence 103 → 102 (shared terminal-status semantics) before 104 and 109" — is honored by the task order. The SKILL.md line-cap constraint is Task 5 Step 1. No row is left without a task.

**Placeholder scan.** Every code step carries real, complete code. No "TBD", no "add error handling", no "similar to Task N", no step that says what to do without showing how.

**Type consistency.** `partition` returns `(open, resolved)` in Task 1 and is destructured as `open_blockers, resolved_blockers` in both call sites. `headings_for_story(plan_text, story, story_prefix="SK")` matches its caller `_blocked_story_headings`. `review_package.last_record(root, sprint_id)` returns `dict | None` and `_cmd_review_guard` checks `is None` before calling `refusal(record, current)`, whose own guard clause raises on a fresh package. `record_cost`'s new `estimated` is keyword-only, matching its existing keyword-only block. `record_package(base, head, path, *, root)` matches both the CLI call site and the tests.

**One gap worth naming, not fixing here.** Task 3's guard proves the package's *head*; its *base* is recorded but never checked, so a package cut at the right HEAD from the wrong base passes. That ceiling is stated in the module docstring and in the refusal text rather than papered over, and it is strictly better than today, where neither is checked.
