# E10 — The operator decides, the conductor acts: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move every mechanical command supskill hands back to the operator into the conductor, while keeping the decision human, recorded, and auditable from disk.

**Architecture:** A new `stop_classes` module records, for every CLI verb, whether its refusals are *remediable* (the conductor may act), *evidential* (still refuse — acting destroys the signal), or *no_stop*. A test asserts the table covers every subparser, so the classification cannot drift back into prose. Two new trails follow: `actions.jsonl` records what the conductor did on the operator's behalf, and a `decision` record captures which option an operator chose for a blocker. Both `gate` and `decide` gain `--batched` to mark bulk acceptance.

**Tech Stack:** Python 3.11+, stdlib only (`argparse`, `dataclasses`, `json`, `subprocess`, `re`), pytest, ruff.

## Global Constraints

- Design source: `docs/superpowers/specs/2026-08-04-operator-interaction-model-design.md`. Backlog rows: `docs/plans/sprints/backlog-01/backlog.md`, E10, SK-130..SK-136.
- Ruff line length is **120**.
- Every new verb is **conductor-only**: no dispatched agent runs `supskill-state` (invariant 3).
- Every refusal must **write nothing** — validate fully before touching disk, the shape `record_blocker` already uses.
- Trails are **append-only JSONL** via `store.append_jsonl`; timestamps via `store.now_utc_iso()`.
- Per-run trails live at `store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / <name>.jsonl`, the pattern `record_cost` uses.
- `record_gate` **may** gain a keyword argument (Task 4 adds `batched`), but its **acceptance of an empty `--response` must not change** (`commands.py:402`, `empty is accepted and recorded by design (F-4)`). The constraint is on that one behaviour, not on the function.
- **Do not** add merge, push, branch-create or branch-delete anywhere.
- `state.json` schema stays at **1**. Everything added here is a trail or a read-time derivation.
- Run `uv run pytest && uv run ruff check .` before every commit.

## Divergences from the rows as filed

Recorded here rather than by editing the backlog rows, per this project's convention.

1. **SK-130 has three classes, not two.** The spec names *remediable* and *evidential*. The anti-drift test can only be total if every verb is classified, and several verbs (`show`, `config`, `root`) never stop at all. A third value `no_stop` makes coverage checkable instead of leaving unclassifiable verbs as silent exceptions.

2. **SK-132 records the decision, not the resolution.** The spec says `show` should "derive resolution from the decision rather than inferring it from task status." Implementing that literally would reintroduce exactly what `blockers.py`'s module docstring warns against: *"a second verb that could move a blocker independently could also disagree with its task, and then Gate 3 would have two answers and no rule for picking one."* So `decide` records **which option was chosen**, and SK-103's derivation still decides **whether the blocker is resolved**. `derived.blockers.*` gains a `decision` field beside the existing `resolved_by`. One source per question: the trail says what was chosen, the task status says whether it settled.

---

### Task 1: The stop classification table (SK-130)

**Files:**
- Create: `scripts/supskill_state/stop_classes.py`
- Create: `tests/test_stop_classes.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `StopClass` (str enum-like constants `REMEDIABLE`, `EVIDENTIAL`, `NO_STOP`); `STOPS: tuple[Stop, ...]`; `Stop` dataclass with fields `id: str`, `verb: str`, `condition: str`, `stop_class: str`, `action: str | None`; `classify(stop_id: str) -> Stop`; `verbs_covered() -> set[str]`. Task 2 and Task 6 import `classify`.

- [ ] **Step 1: Write the failing test**

```python
"""SK-130: every stop the CLI can produce carries exactly one recorded class."""

import pytest

from supskill_state import stop_classes
from supskill_state.cli import build_parser
from supskill_state.errors import StateError


def _cli_verbs() -> set[str]:
    parser = build_parser()
    actions = [a for a in parser._actions if hasattr(a, "choices") and a.choices]
    return set(actions[0].choices)


def test_every_cli_verb_is_classified():
    missing = _cli_verbs() - stop_classes.verbs_covered()
    assert missing == set(), f"unclassified verbs: {sorted(missing)}"


def test_no_stop_names_a_verb_the_cli_does_not_have():
    extra = stop_classes.verbs_covered() - _cli_verbs()
    assert extra == set(), f"table names verbs the CLI lacks: {sorted(extra)}"


def test_stop_ids_are_unique():
    ids = [stop.id for stop in stop_classes.STOPS]
    assert len(ids) == len(set(ids))


def test_every_remediable_stop_names_its_action():
    for stop in stop_classes.STOPS:
        if stop.stop_class == stop_classes.REMEDIABLE:
            assert stop.action, f"{stop.id} is remediable but names no action"


def test_no_evidential_stop_names_an_action():
    for stop in stop_classes.STOPS:
        if stop.stop_class == stop_classes.EVIDENTIAL:
            assert stop.action is None, f"{stop.id} is evidential but names an action"


def test_archive_is_classified_both_ways_on_whether_a_decision_exists():
    archive = [s for s in stop_classes.STOPS if s.verb == "init" and "archive" in s.id]
    classes = {s.stop_class for s in archive}
    assert classes == {stop_classes.REMEDIABLE, stop_classes.EVIDENTIAL}


def test_the_seven_evidential_stops_are_present():
    evidential_verbs = {
        s.verb for s in stop_classes.STOPS if s.stop_class == stop_classes.EVIDENTIAL
    }
    assert {
        "review-guard",
        "plan-guard",
        "commit-scope-guard",
        "replan-guard",
        "preflight",
        "tasks",
        "init",
    } <= evidential_verbs


def test_classify_refuses_an_unknown_stop_id():
    with pytest.raises(StateError):
        stop_classes.classify("no-such-stop")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_stop_classes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'supskill_state.stop_classes'`

- [ ] **Step 3: Write the classification table**

`build_parser() -> argparse.ArgumentParser` already exists at `scripts/supskill_state/cli.py:24` and `main()` calls it, so the test above can inspect the parser without running it. No extraction is needed.

```python
"""SK-130: which stops the conductor may remediate, and which must stay refusals.

Every seam where supskill stops carries exactly one class. `remediable` means the
stop names a known, safe, specific action and the conductor takes it. `evidential`
means acting on the stop would destroy the signal it exists to raise - a
regenerated review package comes back clean, which is precisely what SK-104 was
built to prevent. `no_stop` is a verb that cannot refuse in a way an operator has
to act on.

The table is total over the CLI's verbs, and tests/test_stop_classes.py enforces
that. Without the test this decays into per-run prose judgment, which is SK-108's
failure mode: open across four runs and three contradictory readings.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import StateError

REMEDIABLE = "remediable"
EVIDENTIAL = "evidential"
NO_STOP = "no_stop"


@dataclass(frozen=True)
class Stop:
    id: str
    verb: str
    condition: str
    stop_class: str
    action: str | None = None


STOPS: tuple[Stop, ...] = (
    Stop(
        id="init.archive.decided",
        verb="init",
        condition="a different sprint is on disk and its G3 decision IS recorded",
        stop_class=REMEDIABLE,
        action="run init <id> --archive, carrying every operator flag forward verbatim",
    ),
    Stop(
        id="init.archive.undecided",
        verb="init",
        condition="the sprint on disk rests at REVIEW with no G3 decision (SK-115)",
        stop_class=EVIDENTIAL,
    ),
    Stop(
        id="artifact-guard.untracked",
        verb="artifact-guard",
        condition="a recorded artifact is untracked by git",
        stop_class=REMEDIABLE,
        action="stage and commit exactly the recorded artifact paths",
    ),
    Stop(
        id="review-guard.stale",
        verb="review-guard",
        condition="HEAD moved past the recorded package, or none was recorded",
        stop_class=EVIDENTIAL,
    ),
    Stop(
        id="plan-guard.commits",
        verb="plan-guard",
        condition="the plan agent produced commits",
        stop_class=EVIDENTIAL,
    ),
    Stop(
        id="commit-scope-guard.foreign",
        verb="commit-scope-guard",
        condition="a commit range swept foreign harness state in",
        stop_class=EVIDENTIAL,
    ),
    Stop(
        id="replan-guard.north-star",
        verb="replan-guard",
        condition="the shape reads as a north-star reset (invariant 7)",
        stop_class=EVIDENTIAL,
    ),
    Stop(
        id="preflight.unresolvable",
        verb="preflight",
        condition="a skill a later stage dispatches will not resolve",
        stop_class=EVIDENTIAL,
    ),
    Stop(
        id="tasks.coverage",
        verb="tasks",
        condition="the dev plan does not cover the sprint doc's stories",
        stop_class=EVIDENTIAL,
    ),
    Stop(id="show.none", verb="show", condition="reads only", stop_class=NO_STOP),
    Stop(id="config.none", verb="config", condition="reads or sets config", stop_class=NO_STOP),
    Stop(id="root.none", verb="root", condition="prints the resolved root", stop_class=NO_STOP),
    Stop(id="artifact.none", verb="artifact", condition="records a path", stop_class=NO_STOP),
    Stop(id="gate.none", verb="gate", condition="records a decision", stop_class=NO_STOP),
    Stop(id="block.none", verb="block", condition="records a blocker", stop_class=NO_STOP),
    Stop(id="task.none", verb="task", condition="records a status", stop_class=NO_STOP),
    Stop(id="advance.none", verb="advance", condition="validates a transition", stop_class=NO_STOP),
    Stop(id="package.none", verb="package", condition="records a package", stop_class=NO_STOP),
    Stop(id="worktree.none", verb="worktree", condition="creates the dispatch root", stop_class=NO_STOP),
    Stop(id="cost.none", verb="cost", condition="records telemetry", stop_class=NO_STOP),
    Stop(id="review.none", verb="review", condition="records a finding", stop_class=NO_STOP),
)


def classify(stop_id: str) -> Stop:
    for stop in STOPS:
        if stop.id == stop_id:
            return stop
    raise StateError(f"unknown stop id {stop_id!r}; expected one of {sorted(s.id for s in STOPS)}")


def verbs_covered() -> set[str]:
    return {stop.verb for stop in STOPS}
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_stop_classes.py -v`
Expected: PASS. If `test_no_stop_names_a_verb_the_cli_does_not_have` fails, the CLI has verbs this table omits — add a `Stop` for each; do **not** relax the test.

- [ ] **Step 5: Run the full suite and lint**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/supskill_state/stop_classes.py tests/test_stop_classes.py
git commit -m "feat(SK-130): classify every CLI stop as remediable, evidential or no_stop

The table is total over the CLI's verbs and a test enforces it. --archive
appears twice, split on whether a G3 decision exists to preserve: remediable
when one does, evidential when it does not (SK-115).

review-guard, plan-guard, commit-scope-guard, replan-guard, preflight and the
tasks coverage refusal stay evidential. Acting on them destroys the signal
they exist to raise."
```

---

### Task 2: `actions.jsonl` and the `action` verb (SK-131)

**Files:**
- Modify: `scripts/supskill_state/commands.py`
- Modify: `scripts/supskill_state/cli.py`
- Create: `tests/test_actions.py`

**Interfaces:**
- Consumes: `stop_classes.classify` from Task 1.
- Produces: `commands.record_action(stop_id: str, command: str, *, result: str = "ok", sha: str | None = None, root: Path | None = None) -> None`, appending to `runs/<id>/actions.jsonl`. Task 5 calls it after a conductor commit.

- [ ] **Step 1: Write the failing test**

```python
"""SK-131: what the conductor did on the operator's behalf, durable on disk.

Decision 2 of the design makes these actions silent. Invariant 5 says the
conductor is disposable with .supskill/ as its only memory, so a report in a
conversation /clear destroys is not a record.
"""

import json

import pytest

from supskill_state.commands import init_sprint, record_action
from supskill_state.errors import StateError
from supskill_state.store import require_aware_utc_iso, runs_dir, state_path


def _actions(tmp_path, sprint_dir="s10"):
    path = runs_dir(tmp_path) / sprint_dir / "actions.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_records_the_stop_its_reason_and_the_exact_command(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    record_action(
        "artifact-guard.untracked",
        "git add docs/a.md docs/b.md && git commit -m 'docs: track sprint artifacts'",
        sha="0173092",
        root=tmp_path,
    )

    rows = _actions(tmp_path)
    assert len(rows) == 1
    assert rows[0]["stop"] == "artifact-guard.untracked"
    assert rows[0]["command"].startswith("git add ")
    assert rows[0]["sha"] == "0173092"
    assert rows[0]["result"] == "ok"
    assert rows[0]["reason"]  # carried from the table's condition, never invented
    require_aware_utc_iso(rows[0]["at"], "actions.at")


def test_state_json_is_untouched(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)
    before = state_path(tmp_path).read_bytes()

    record_action("artifact-guard.untracked", "git add docs/a.md", root=tmp_path)

    assert state_path(tmp_path).read_bytes() == before


def test_refuses_an_evidential_stop_and_writes_nothing(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    with pytest.raises(StateError, match="evidential"):
        record_action("review-guard.stale", "git diff > pkg.diff", root=tmp_path)

    assert _actions(tmp_path) == []


def test_refuses_an_unknown_stop_id_and_writes_nothing(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    with pytest.raises(StateError):
        record_action("no-such-stop", "true", root=tmp_path)

    assert _actions(tmp_path) == []


def test_refuses_an_empty_command(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    with pytest.raises(StateError, match="--command"):
        record_action("artifact-guard.untracked", "", root=tmp_path)

    assert _actions(tmp_path) == []


def test_appends_rather_than_replaces(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    record_action("artifact-guard.untracked", "git add a", root=tmp_path)
    record_action("init.archive.decided", "supskill-state init s11 --archive", root=tmp_path)

    assert [r["stop"] for r in _actions(tmp_path)] == [
        "artifact-guard.untracked",
        "init.archive.decided",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actions.py -v`
Expected: FAIL with `ImportError: cannot import name 'record_action'`

- [ ] **Step 3: Implement `record_action` in `commands.py`**

Add the import at the top of `commands.py` beside the other module imports:

```python
from . import stop_classes
```

Then add the function next to `record_cost`:

```python
def record_action(
    stop_id: str,
    command: str,
    *,
    result: str = "ok",
    sha: str | None = None,
    root: Path | None = None,
) -> None:
    """Record one action the conductor took on the operator's behalf (SK-131).

    Only a `remediable` stop may produce one: an evidential stop is a refusal, and
    a refusal that writes an action record would be claiming it fixed the thing it
    was built to surface.

    `reason` is copied from the classification table's own `condition`, never
    supplied by the caller - the record says why the stop fired, not why the
    conductor felt like acting.

    Pure telemetry in the same sense as record_cost: state.json never changes.
    """
    root = store.resolve_root(root)
    stop = stop_classes.classify(stop_id)  # refuses an unknown id, writing nothing
    if stop.stop_class != stop_classes.REMEDIABLE:
        raise StateError(
            f"{stop_id} is {stop.stop_class}, not remediable - it is a refusal to relay, "
            "not an action to take"
        )
    if not command.strip():
        raise StateError("an action record requires a non-empty --command")

    state = store.load_state(store.state_path(root))
    actions_file = store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / "actions.jsonl"
    store.append_jsonl(
        actions_file,
        {
            "stop": stop.id,
            "reason": stop.condition,
            "command": command,
            "sha": sha,
            "result": result,
            "at": store.now_utc_iso(),
        },
    )
```

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/test_actions.py -v`
Expected: PASS

- [ ] **Step 5: Add the CLI verb**

In `cli.py`, register it alongside the others by adding `_add_action(subparsers)` to the list after `_add_cost(subparsers)`, then:

```python
def _add_action(subparsers) -> None:
    sub = subparsers.add_parser(
        "action", help="record one action the conductor took on the operator's behalf"
    )
    sub.add_argument("--stop", required=True, dest="stop_id", help="the stop id from stop_classes.STOPS")
    sub.add_argument("--command", required=True, help="the exact command that was run")
    sub.add_argument("--sha", help="the resulting commit SHA, when the action produced one")
    sub.add_argument("--result", default="ok", help="ok | failed")
    sub.set_defaults(func=_cmd_action)


def _cmd_action(args) -> int:
    commands.record_action(args.stop_id, args.command, result=args.result, sha=args.sha)
    print(f"recorded action: {args.stop_id} result={args.result}")
    return 0
```

- [ ] **Step 6: Add the CLI coverage test**

Append to `tests/test_actions.py`:

```python
def test_cli_records_an_action(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    from supskill_state.cli import main

    exit_code = main(["action", "--stop", "artifact-guard.untracked", "--command", "git add a", "--sha", "abc1234"])

    assert exit_code == 0
    assert "recorded action" in capsys.readouterr().out
    assert _actions(tmp_path)[0]["sha"] == "abc1234"


def test_cli_refuses_an_evidential_stop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    from supskill_state.cli import main

    assert main(["action", "--stop", "review-guard.stale", "--command", "true"]) == 1
```

`main()` catches `StateError` and returns 1 (`cli.py:503-509`, printing `supskill-state: refused: <msg>` to stderr), so asserting `== 1` is correct.

- [ ] **Step 7: Run everything and commit**

Run: `uv run pytest -q && uv run ruff check .`

```bash
git add scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_actions.py
git commit -m "feat(SK-131): record what the conductor did on the operator's behalf

runs/<id>/actions.jsonl, one append-only row per conductor-executed action.
Only a remediable stop can produce one; an evidential stop refuses, because a
refusal that writes an action record claims it fixed what it was built to
surface.

reason is copied from the classification table's condition, never supplied by
the caller. Invariant 5: a report in a conversation /clear destroys is not a
record."
```

---

### Task 3: `decide` — the blocker's inverse (SK-132)

**Files:**
- Modify: `scripts/supskill_state/commands.py`
- Modify: `scripts/supskill_state/cli.py`
- Create: `tests/test_decide.py`

**Interfaces:**
- Consumes: `_OPTION_LABEL` (`commands.py:411`), `Blocker` (`model.py`).
- Produces: `commands.record_decision(task_id: str, option: str, response: str, *, batched: bool = False, root: Path | None = None) -> None`, appending a `{"kind": "decision", ...}` row to `runs/<id>/blockers.jsonl`. Task 4 adds `batched`. Task 4 also surfaces it in `show`.

**Design note — read before implementing.** This records **which option was chosen**, not **whether the blocker is resolved**. SK-103's derivation (`blockers.py`) still owns resolution, because a second independent mover could disagree with the task's status and leave Gate 3 with two answers and no rule. One source per question.

- [ ] **Step 1: Write the failing test**

```python
"""SK-132: a blocker's answer gets a verb.

block records options[] and recommend; nothing recorded which option was chosen.
This does - and deliberately does NOT decide resolution, which stays SK-103's
derivation from task status.
"""

import json

import pytest

from supskill_state.commands import init_sprint, load_tasks, record_blocker, record_decision
from supskill_state.errors import StateError
from supskill_state.store import require_aware_utc_iso, runs_dir


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

    decisions = [r for r in _blocker_rows(blocked) if r.get("kind") == "decision"]
    assert len(decisions) == 1
    assert decisions[0]["task"] == "SK-001"
    assert decisions[0]["option"] == "a"
    assert decisions[0]["response"] == "go with (a), the transport is the actual defect"
    assert decisions[0]["batched"] is False
    require_aware_utc_iso(decisions[0]["at"], "decision.at")


def test_refuses_an_option_label_the_blocker_never_offered(blocked):
    with pytest.raises(StateError, match="never offered"):
        record_decision("SK-001", "(c)", "go with c", root=blocked)

    assert [r for r in _blocker_rows(blocked) if r.get("kind") == "decision"] == []


def test_refuses_an_empty_response(blocked):
    with pytest.raises(StateError, match="--response"):
        record_decision("SK-001", "(a)", "   ", root=blocked)

    assert [r for r in _blocker_rows(blocked) if r.get("kind") == "decision"] == []


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
```

- [ ] **Step 2: Write the `_seed_one_task` helper the fixture needs**

Open `tests/test_block.py` and find how it populates `state.tasks` before calling `record_blocker` (that verb refuses a task not in `state.json`). Copy that mechanism verbatim into a module-level helper in `tests/test_decide.py`:

```python
def _seed_one_task(root, task_id):
    """Populate state.tasks so record_blocker has a task to attach to.

    Copy the body from tests/test_block.py's own setup - do not invent a second
    way to seed tasks.
    """
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_decide.py -v`
Expected: FAIL with `ImportError: cannot import name 'record_decision'`

- [ ] **Step 4: Implement `record_decision`**

```python
def record_decision(
    task_id: str,
    option: str,
    response: str,
    *,
    batched: bool = False,
    root: Path | None = None,
) -> None:
    """Record which option an operator chose for a blocker (SK-132).

    This records the ANSWER, not the RESOLUTION. Whether the blocker is settled
    stays `blockers.resolving_status`'s derivation from task status (SK-103): a
    second independent mover could disagree with the task, and Gate 3 would then
    have two answers and no rule for picking one.

    `option` is matched against the blocker's own recorded options[] labels, so a
    label the operator was never offered cannot be recorded as their choice.
    """
    root = store.resolve_root(root)
    if not response.strip():
        raise StateError("a decision requires a non-empty --response - an empty answer is not a decision (D4)")

    state = store.load_state(store.state_path(root))
    blocker = next((b for b in state.blockers if b.task == task_id), None)
    if blocker is None:
        raise StateError(f"no blocker recorded for task {task_id!r}")

    match = _OPTION_LABEL.match(option)
    if match is None:
        raise StateError(f"--option must be a label like '(a)': {option!r}")
    label = match.group(1)
    offered = [_OPTION_LABEL.match(o).group(1) for o in blocker.options if _OPTION_LABEL.match(o)]
    if label not in offered:
        raise StateError(
            f"option ({label}) was never offered for {task_id}; this blocker offers {offered}"
        )

    sprint_dir = normalize_sprint_id(state.sprint.id)
    blockers_file = store.runs_dir(root) / sprint_dir / "blockers.jsonl"
    for record in _jsonl_records(blockers_file):
        if record.get("kind") == "decision" and record.get("task") == task_id:
            raise StateError(
                f"{task_id} was already decided as ({record['option']}); "
                "the trail is append-only and a decision is not re-taken"
            )

    store.append_jsonl(
        blockers_file,
        {
            "kind": "decision",
            "task": task_id,
            "option": label,
            "response": response,
            "batched": batched,
            "at": store.now_utc_iso(),
        },
    )
```

`_jsonl_records(path)` already exists in `commands.py` just below `_blocker_view`, and it **is** a generator (bare `return` on a missing file, `yield` per line). It is iterated once here, so no `list(...)` wrap is needed — but wrap it if you iterate twice.

- [ ] **Step 5: Run the test**

Run: `uv run pytest tests/test_decide.py -v`
Expected: PASS

- [ ] **Step 6: Confirm existing blocker tests still pass**

Run: `uv run pytest tests/test_block.py tests/test_blockers_resolved.py tests/test_blocker_headings.py tests/test_show.py -v`
Expected: PASS. The new rows carry `kind: "decision"`; existing readers must skip them. If any existing reader chokes on a row without `options`, add the `kind` filter there and note it in the commit.

- [ ] **Step 7: Add the CLI verb**

Register `_add_decide(subparsers)` after `_add_block(subparsers)`:

```python
def _add_decide(subparsers) -> None:
    sub = subparsers.add_parser(
        "decide", help="record which option the operator chose for a recorded blocker"
    )
    sub.add_argument("--task", required=True, dest="task_id", help="the blocked story id")
    sub.add_argument("--option", required=True, help="the chosen option's label, e.g. '(a)'")
    sub.add_argument("--response", required=True, help="the operator's answer, verbatim")
    sub.set_defaults(func=_cmd_decide)


def _cmd_decide(args) -> int:
    commands.record_decision(args.task_id, args.option, args.response)
    print(f"recorded decision: {args.task_id} chose {args.option}")
    return 0
```

- [ ] **Step 8: Run everything and commit**

Run: `uv run pytest -q && uv run ruff check .`

```bash
git add scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_decide.py
git commit -m "feat(SK-132): give a blocker's answer a verb

decide records which option the operator chose, matched against the blocker's
own recorded options[] so a label they were never offered cannot become their
choice.

It records the ANSWER, not the RESOLUTION. SK-103's derivation from task status
still decides whether a blocker is settled - a second independent mover could
disagree with the task and leave Gate 3 with two answers and no rule. Divergence
from SK-132 as filed, recorded in the plan."
```

---

### Task 4: `--batched` on `gate` and `decide` (SK-133)

**Files:**
- Modify: `scripts/supskill_state/commands.py`
- Modify: `scripts/supskill_state/cli.py`
- Modify: `tests/test_gate.py`, `tests/test_decide.py`

**Interfaces:**
- Consumes: `record_gate`, `record_decision` from Task 3.
- Produces: `record_gate(..., batched: bool = False)`; `gates.jsonl` rows gain `"batched"`; `derived.blockers.*` entries gain `"decision"` and `"batched"`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gate.py`:

```python
def test_a_gate_row_records_whether_it_was_batch_accepted(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    record_gate("G1", "approved", "all three, your recs", batched=True, root=tmp_path)

    row = _gate_lines(tmp_path)[-1]
    assert row["batched"] is True


def test_an_individually_answered_gate_is_marked_not_batched(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    record_gate("G1", "approved", "approve", root=tmp_path)

    assert _gate_lines(tmp_path)[-1]["batched"] is False
```

`tests/test_gate.py` already has `_gate_lines(tmp_path)` for reading `gates.jsonl` — use that name.

Append to `tests/test_decide.py`:

```python
def test_a_batched_decision_says_so(blocked):
    record_decision("SK-001", "(a)", "go with your recommendations on all three", batched=True, root=blocked)

    decisions = [r for r in _blocker_rows(blocked) if r.get("kind") == "decision"]
    assert decisions[0]["batched"] is True


def test_show_json_surfaces_the_decision_beside_resolved_by(blocked):
    import json as _json

    from supskill_state.commands import render_show_json

    record_decision("SK-001", "(a)", "go with a", root=blocked)

    payload = _json.loads(render_show_json(root=blocked))
    entry = payload["derived"]["blockers"]["open"][0]
    assert entry["decision"] == "a"
    assert entry["batched"] is False
    assert entry["resolved_by"] is None  # answered, not settled
```

The renderer is `commands.render_show_json(root=...)` (`cli.py:100`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_gate.py tests/test_decide.py -v`
Expected: FAIL — `record_gate() got an unexpected keyword argument 'batched'`, and `KeyError: 'decision'`.

- [ ] **Step 3: Add `batched` to `record_gate`**

Change the signature and the record. Do **not** touch the empty-response behaviour:

```python
def record_gate(
    gate_id: str,
    decision: str,
    response: str,
    *,
    batched: bool = False,
    root: Path | None = None,
) -> State:
```

and in the record dict, beside `"response"`:

```python
        "batched": batched,  # SK-133: a bulk acceptance must not read as a considered one
```

- [ ] **Step 4: Surface the decision in `_blocker_view`**

Add a `decisions` lookup beside the existing `notes` lookup in the `derived` builder, then extend `_blocker_view`'s returned dict:

```python
def _blocker_decisions(root: Path, sprint_id: str) -> dict[str, dict]:
    """task id -> its decision row, for blockers answered through `decide` (SK-132)."""
    path = store.runs_dir(root) / normalize_sprint_id(sprint_id) / "blockers.jsonl"
    found: dict[str, dict] = {}
    for record in _jsonl_records(path):
        if record.get("kind") == "decision":
            found[record["task"]] = record
    return found
```

In `_blocker_view`, accept `decisions: dict[str, dict]` as a parameter and return:

```python
    decision = decisions.get(blocker.task)
    return {
        **blocker_to_dict(blocker),
        "plan_headings": headings.get(blocker.task, []),
        "resolved_by": status.value if status else None,
        "note": note,
        "decision": decision["option"] if decision else None,
        "batched": decision["batched"] if decision else False,
    }
```

Update both `_blocker_view(...)` call sites in the `derived` builder to pass the new dict.

- [ ] **Step 5: Add `--batched` to both CLI verbs**

To `_add_gate` and `_add_decide`:

```python
    sub.add_argument(
        "--batched",
        action="store_true",
        help="this answer accepted several recommendations at once, rather than being reasoned "
             "individually (SK-133)",
    )
```

And pass it through in `_cmd_gate` / `_cmd_decide`: `batched=args.batched`.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/test_gate.py tests/test_decide.py tests/test_show.py -v`
Expected: PASS

- [ ] **Step 7: Run everything and commit**

Run: `uv run pytest -q && uv run ruff check .`

```bash
git add scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_gate.py tests/test_decide.py
git commit -m "feat(SK-133): mark a gate or decision that was batch-accepted

Exactly SK-109's shape and reason: a ledger that cannot distinguish two
provenances is lying quietly. show renders it, so a batch-accepted G3 and an
individually-reasoned one are tellable apart.

record_gate's acceptance of an empty response is untouched (F-4)."
```

---

### Task 5: `commit-scope-guard` covers the conductor's own commits (SK-134)

**Files:**
- Modify: `scripts/supskill_state/commit_scope.py`
- Modify: `scripts/supskill_state/cli.py`
- Modify: `tests/test_commit_scope.py`

**Interfaces:**
- Consumes: `commit_scope.foreign_paths`, `stop_classes` from Task 1.
- Produces: `commit_scope.guard_conductor_commit(paths: list[str]) -> list[str]` — the foreign paths among a *staged set*, before the commit exists.

**Why this differs from the existing guard.** Today the guard inspects a committed `BASE..HEAD` range. A conductor commit has to be checked *before* it lands, so this checks the paths about to be staged. Same denylist, same refusal, different input.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_commit_scope.py`:

```python
def test_a_conductor_commit_that_would_stage_supskill_state_is_refused():
    foreign = commit_scope.guard_conductor_commit(
        ["docs/sprints/backlog-01/backlog.md", ".supskill/state.json"]
    )
    assert foreign == [".supskill/state.json"]


def test_a_conductor_commit_of_only_the_recorded_artifacts_is_allowed():
    assert commit_scope.guard_conductor_commit(
        ["docs/sprints/backlog-01/sprint-s9.md", "docs/superpowers/plans/2026-08-04-sprint-s9.md"]
    ) == []


def test_the_conductor_guard_uses_the_same_denylist_as_the_task_guard():
    for prefix in commit_scope.FOREIGN_PREFIXES:
        assert commit_scope.guard_conductor_commit([f"{prefix}x"]) == [f"{prefix}x"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_commit_scope.py -v`
Expected: FAIL with `AttributeError: module 'supskill_state.commit_scope' has no attribute 'guard_conductor_commit'`

- [ ] **Step 3: Implement it**

```python
def guard_conductor_commit(paths: Iterable[str]) -> list[str]:
    """The foreign paths among a set the CONDUCTOR is about to stage (SK-134).

    `foreign_paths` inspects a committed range, which is right for a task's
    implementer: the commits already exist and REVIEW will see them. A conductor
    commit is checked before it lands, so the input is the staged set instead.
    The denylist is shared - the actor that gains the most reach under E10 must
    not be the one the guard exempts.
    """
    return foreign_paths(paths)
```

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/test_commit_scope.py -v`
Expected: PASS

- [ ] **Step 5: Run everything and commit**

Run: `uv run pytest -q && uv run ruff check .`

```bash
git add scripts/supskill_state/commit_scope.py tests/test_commit_scope.py
git commit -m "feat(SK-134): guard the conductor's own commits with the task denylist

foreign_paths inspects a committed range, which suits an implementer whose
commits already exist. A conductor commit is checked before it lands, so the
input is the staged set. Same denylist either way - the actor that gains the
most reach under E10 must not be the one the guard exempts."
```

---

### Task 6: A run that cannot ask cannot act (SK-136)

**Files:**
- Modify: `scripts/supskill_state/preflight.py`
- Modify: `scripts/supskill_state/cli.py`
- Create: `tests/test_interactive_precondition.py`

**Interfaces:**
- Consumes: `stop_classes` from Task 1.
- Produces: `preflight.interactive_refusal(answered: bool) -> str | None` — the refusal text when a run has not demonstrated it can reach an operator, `None` otherwise.

**Why this shape.** `record_gate` must keep accepting an empty response (`commands.py:402`, F-4), so the rule cannot be enforced inside `gate`. It is enforced one level up: the conductor proves an operator answered something before it takes any silent action. This is a precondition backed by conductor discipline, not a mechanism that makes the failure impossible — F-4's ceiling, restated one level out. That limitation is recorded in the row and in the docstring; do not write a test that claims otherwise.

- [ ] **Step 1: Write the failing test**

```python
"""SK-136: a run that cannot reach an operator does not act on their behalf.

D4: AskUserQuestion auto-resolves EMPTY in ~37ms headless. Before E10 that cost a
missing record. Under E10 it would cost an executed action nobody chose.
"""

from supskill_state import preflight


def test_a_run_that_has_not_reached_an_operator_is_refused():
    refusal = preflight.interactive_refusal(answered=False)

    assert refusal is not None
    assert "empty" in refusal.lower()
    assert "did not act" in refusal.lower() or "nothing was" in refusal.lower()


def test_a_run_that_reached_an_operator_may_proceed():
    assert preflight.interactive_refusal(answered=True) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_interactive_precondition.py -v`
Expected: FAIL with `AttributeError: module 'supskill_state.preflight' has no attribute 'interactive_refusal'`

- [ ] **Step 3: Implement it**

```python
def interactive_refusal(answered: bool) -> str | None:
    """The refusal when a run has not shown it can reach an operator (SK-136).

    `answered` is the conductor's own observation: did a real, non-empty answer
    come back from the operator this run? AskUserQuestion auto-resolves with an
    EMPTY answer in ~37ms in headless/no-TTY runs (D4), so an empty answer is
    never consent - and under E10 an action would follow it.

    The ceiling, stated plainly: this checks what the conductor reports, not what
    a human did. F-4 applies here exactly as it applies to the gates - loud and
    auditable, not impossible.
    """
    if answered:
        return None
    return (
        "this run has not received a non-empty answer from an operator, so it will not act on "
        "one's behalf: AskUserQuestion auto-resolves with an empty answer in headless runs, and an "
        "empty answer is not consent. Nothing was recorded and nothing was executed.\n"
        "Re-run this stage in an interactive session."
    )
```

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/test_interactive_precondition.py -v`
Expected: PASS

- [ ] **Step 5: Run everything and commit**

Run: `uv run pytest -q && uv run ruff check .`

```bash
git add scripts/supskill_state/preflight.py tests/test_interactive_precondition.py
git commit -m "feat(SK-136): a run that cannot ask does not act

record_gate must keep accepting an empty response so a fabricated approval
leaves a readable trace (F-4), so this cannot live inside gate. It lives one
level up: the conductor proves it reached an operator before taking any silent
action.

Recorded as a precondition, not a mechanism - F-4's ceiling one level out."
```

---

### Task 7: Rewrite the prose that tells the operator to type (SK-135)

**Files:**
- Create: `skills/supskill/references/stop-classes.md`
- Modify: `skills/supskill/SKILL.md`
- Modify: `tests/test_execute_prose.py` or create `tests/test_stop_prose.py`

**Interfaces:**
- Consumes: `stop_classes.STOPS` from Task 1; the verbs from Tasks 2–6.
- Produces: nothing importable. This is the conductor-facing half.

- [ ] **Step 1: Write the failing prose test**

Create `tests/test_stop_prose.py`:

```python
"""SK-135: the conductor's prose matches the classification table it describes."""

import pathlib

from supskill_state import stop_classes

SKILL = pathlib.Path("skills/supskill/SKILL.md")
REFERENCE = pathlib.Path("skills/supskill/references/stop-classes.md")


def test_the_reference_names_every_stop():
    text = REFERENCE.read_text(encoding="utf-8")
    for stop in stop_classes.STOPS:
        if stop.stop_class != stop_classes.NO_STOP:
            assert stop.id in text, f"{stop.id} is missing from stop-classes.md"


def test_skill_no_longer_forbids_archive_outright():
    text = SKILL.read_text(encoding="utf-8")
    assert "**Never pass `--archive`.**" not in text


def test_skill_links_the_stop_classes_reference():
    assert "references/stop-classes.md" in SKILL.read_text(encoding="utf-8")


def test_skill_still_refuses_a_north_star_supersede():
    text = SKILL.read_text(encoding="utf-8")
    assert "north-star-reset" in text
    assert "operator's alone" in text or "operator-authored" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_stop_prose.py -v`
Expected: FAIL — the reference file does not exist.

- [ ] **Step 3: Write `references/stop-classes.md`**

One table with a row per non-`no_stop` stop: its id, the condition, its class, and — for remediable ones — the exact action the conductor takes and the `action --stop <id>` call that records it. Copy the ids and conditions verbatim from `stop_classes.STOPS`; the test above enforces that they match.

Open the file with the same framing the other references use: state that it is conductor-facing, that nothing in it is sent to a subagent, and that `stop_classes.py` is the authority the prose describes rather than the other way round.

- [ ] **Step 4: Update `SKILL.md`**

Four edits, each replacing "tell the operator to type it" with "do it and record it":

1. **Conventions** — replace `**Never pass `--archive`.**` and its paragraph with: pass `--archive` only to close a sprint whose G3 decision is recorded (`init.archive.decided`); a sprint at REVIEW with no G3 is `init.archive.undecided` and still refuses. Link `references/stop-classes.md`.
2. **Run checklist step 3** — the id-mismatch branch runs the archive itself when the on-disk sprint's G3 is recorded, then `action --stop init.archive.decided --command "<the exact init line>"`, then continues at step 4. When G3 is absent, relay the refusal verbatim and stop, unchanged.
3. **Gate 3's `artifact-guard` paragraph** — on exit 1, run `guard_conductor_commit` over the untracked recorded artifact paths; if clean, stage and commit exactly those paths, then `action --stop artifact-guard.untracked --command "<the exact git line>" --sha <sha>`. If the guard reports foreign paths, relay and stop.
4. **Gate 3's Shape-1 row** — after the writeback, commit exactly the backlog path written, then record the action.

Add one line to the run checklist's preflight step: before the first action of a run, confirm a non-empty operator answer has been received this run (SK-136); if not, relay `preflight.interactive_refusal`'s text and stop.

- [ ] **Step 5: Run the prose tests and the whole suite**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all pass. `tests/test_execute_prose.py` and `tests/test_review_prose.py` pin existing SKILL.md phrases — if either breaks, the phrase it pins was load-bearing; update the test deliberately and say so in the commit.

- [ ] **Step 6: Commit**

```bash
git add skills/supskill/SKILL.md skills/supskill/references/stop-classes.md tests/test_stop_prose.py
git commit -m "docs(SK-135): the conductor acts on remediable stops, and records it

Never pass --archive becomes: pass it only to close a sprint whose G3 decision
is recorded. The id-mismatch branch, artifact-guard and the Shape-1 writeback
all execute and record instead of handing back a command to type.

The seven evidential stops are unchanged and still relayed verbatim. A test
pins the prose against stop_classes.STOPS so the two cannot drift."
```

---

### Task 8: Release 0.7.0 (process)

**Files:**
- Modify: `pyproject.toml`, `.claude-plugin/plugin.json`, `uv.lock`

- [ ] **Step 1: Follow the runbook exactly**

Run: `cat docs/runbook.md` and follow "Cut a release", replacing `0.6.0` with `0.7.0`. **Do not skip `uv lock`** — the runbook names that as the failure that cost a repair commit after 0.3.0.

- [ ] **Step 2: Note the schema answer in the commit body**

The release body must say whether an in-progress sprint can resume across the upgrade. For E10 the answer is **yes**: `state.json` schema stays at 1 and every addition is a trail or a read-time derivation. Verify it against a real 0.6.0-written state file rather than asserting it — `/home/bessa/Documents/projetos/ledgerus/.supskill/state.json` is one:

```bash
uv run python -c "
from supskill_state.store import load_state, state_path
s = load_state(state_path('/home/bessa/Documents/projetos/ledgerus'))
print(s.sprint.id, s.stage, s.sprint.continues)
"
```

Expected: it loads without error and prints the sprint id, stage, and `None` for `continues`. If that repo is gone, use any `.supskill/` written by 0.6.0; if none exists, say so in the release body rather than claiming resumability you did not test.

- [ ] **Step 3: Update the install and verify**

Follow the runbook's "Update the installed plugin to a new release", then its "Check which version is actually running". The installed version must read `0.7.0`.

---

## Self-Review

**Spec coverage.** §1 classification → Task 1. §2 `actions.jsonl` → Task 2. §3 `decide` → Task 3. §4 `--batched` → Task 4. §5 empty-answer rule → Task 6. §6 conductor commit guard → Task 5. §7 prose → Task 7. Testing section → the test steps in each task. No spec section is unimplemented.

**Placeholders.** Three steps deliberately defer to existing code rather than restating it: Task 1 Step 3 (extract `build_parser` only if it does not exist), Task 3 Step 2 (copy `test_block.py`'s task-seeding helper), and Task 7 Step 3 (copy ids verbatim from `STOPS`). Each names the exact file to read and the exact thing to copy, and each is guarded by a test that fails if it is done wrong. These are directions to existing truth, not deferred decisions.

**Type consistency.** `stop_classes.classify` / `verbs_covered` / `STOPS` / `Stop.stop_class` are used identically in Tasks 1, 2 and 7. `record_action(stop_id, command, *, result, sha, root)` matches its CLI caller. `record_decision(task_id, option, response, *, batched, root)` matches Task 4's `--batched` addition. `guard_conductor_commit(paths)` returns `list[str]`, matching `foreign_paths`. `_blocker_view` gains one parameter, and both call sites are updated in the same step.

**Known ceiling.** Task 6 is a precondition, not a mechanism. It is labelled as such in the row, the docstring and the plan; no test claims more.
