# Sprint 01 — State Spine (`supskill-state`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A stdlib-only `supskill-state` CLI whose precondition checks make gate-skipping fail loudly (`advance --to EXECUTE` with `G2 == null` refuses), with every decision and blocker on disk in append-only logs, proven by a fast offline test suite.

**Architecture:** An importable Python package `scripts/supskill_state/` (typed dataclass model + atomic file store + pure transition logic + command functions) wrapped by a thin argparse CLI and an executable shim `scripts/supskill-state`. All state mutation flows through one atomic writer; both audit logs (`gates.jsonl`, `blockers.jsonl`) are append-only and always written *before* `state.json`.

**Tech Stack:** Python ≥3.11 stdlib only (argparse, json, dataclasses, enum, pathlib, tempfile, datetime). Dev tooling: `uv` (present, v0.10.1), pytest, ruff — dev-only, never runtime.

**Spec:** `docs/plans/sprints/backlog-01/sprint-01-state-spine.md` (stories SK-001…SK-007). Design contract: `docs/.ai/reports/2026-07-12-supskill-design-decisions.md` (D2, D4, D5, D7, D8).

## Global Constraints

- **Zero runtime dependencies beyond the stdlib.** `[project] dependencies = []` stays empty forever; pytest/ruff live in the dev dependency group only. A dependency appearing in runtime deps is a spec violation, not a judgment call.
- **Python floor: `requires-python = ">=3.11"`.** (Spec says "whatever Python the operator has"; 3.11 gives `tomllib` for the dev suite. Operator machine runs 3.12.)
- **The suite is pure offline**: no LLM, no subagent, no network, no git-remote, and no subprocess for testing logic — tests import functions directly. One in-process `main(argv)` CLI layer is allowed (it is a function call, not a shell-out).
- **Only `supskill-state` writes `state.json`** (invariant 3). Inside this repo that means: only `store.dump_state` opens `state.json` for writing, and only `store.append_jsonl` opens the `.jsonl` logs. The reviewer checks this explicitly.
- **Writes to `state.json` are atomic**: same-directory temp file + `os.replace`. Audit logs are opened `"a"` (append) only — never `"w"`.
- **Write order where a verb touches both files: audit trail first, `state.json` second** (a crash leaves the trail *ahead of* state, never behind).
- **One datetime convention**: every timestamp anywhere is timezone-aware UTC, ISO-8601 (`datetime.now(timezone.utc).isoformat()`), enforced by `require_aware_utc_iso` in tests.
- **Task status enum is exactly** `PENDING | DONE | DONE_WITH_CONCERNS | BLOCKED | PARKED`; `NEEDS_CONTEXT` is rejected with a message pointing at the loop-signal mapping. The terminal set `{DONE, DONE_WITH_CONCERNS, BLOCKED, PARKED}` is exported once as `TERMINAL_STATUSES`; nothing redefines it.
- **Stage enum is exactly** `SCOPE | REFINE | PLAN | EXECUTE | REVIEW`; `sprint.entry ∈ {SCOPE, PLAN, EXECUTE}`.
- **Layout is plugin-root compatible**: package under `scripts/`, leaving root free for `.claude-plugin/plugin.json`, `skills/`, `agents/` later (SK-010) without moving anything.
- **TDD every task**: failing test first, run it, minimal implementation, run green, `ruff check` green, commit.
- **Commits**: conventional style (`feat:`/`test:`/`chore:`), **no AI attribution of any kind** (no Co-Authored-By, no "Generated with" lines). Work happens on branch `feat/e1-state-spine`.
- **Test/lint commands** (uv is the runner; both must finish in seconds, offline):
  - `uv run pytest` (or `uv run pytest tests/test_x.py::test_name -v`)
  - `uv run ruff check .`

## Decisions recorded (the spec required these to be made on purpose, not left implicit)

1. **Sprint completion is a G3 decision, not a sixth stage.** The `Stage` enum has exactly five values and `REVIEW` is terminal (`advance` from `REVIEW` refuses: nothing to advance to). What happens after REVIEW is Gate 3's recorded decision plus E6's replan verbs. Rationale: D2's schema and the design §3 stage diagram both end at REVIEW → GATE 3 → "propose next sprint, stop"; a sixth stage would need preconditions with no consumer.
2. **stdlib-only** — already decided at brainstorming, restated here as a Global Constraint.
3. **Blocker options carry labels.** "`recommend` must reference one of them" is made deterministic: every `--option` must start with a label like `(a) `, labels must be distinct, and `--recommend` must start with one of those labels. This is exactly the shape of D5's verbatim S9a fixture, and it round-trips.
4. **Plan-time discovery — an `artifact` verb is added** (~1 pt from the sprint's 7-pt headroom). Without it, nothing can set `artifacts.sprint_doc`/`artifacts.dev_plan` (invariant 3 forbids anyone else writing `state.json`), so `advance --to PLAN` could never legally succeed and the sprint demo cannot run CLI-only. The command list becomes `init | show | artifact | advance | gate | block`. **Propose as a backlog delta at review; do not silently expand D2's command list elsewhere.**
5. **`--archive` semantics**: `init --archive` moves the old `state.json` *and* `gates.jsonl` into `runs/<old-normalized-id>/archive-<n>/` (first free `n` — never clobbers a previous archive; an unreadable old state archives under `runs/unknown/`). The fresh sprint then gets a new empty `gates.jsonl`.
6. **`runs/` directories use the normalized sprint id** (same normalization as the scratch path), so `init S1` writes `runs/s1/`.
7. **`show` reads `gates.jsonl`** (last response per gate) so recorded responses — including empty ones — are visible, per F-4. `state.json.gates` stores only the decision string (`null | "approved" | "rejected"`), matching D2's example.
8. **Artifact existence is checked twice**: `artifact --set` refuses a path that does not exist on disk (fail fast), and `advance` re-checks at transition time (the file may have vanished). "Sprint doc exists" in D2 means both: field recorded *and* file present.
9. **`gate` is recordable at any stage** — no ordering validation. The audit trail records what was said, when; *transitions* are what preconditions guard (F-4: loud, not tamper-proof).
10. **Load validation is structural; business rules live in the verbs.** `load` enforces types, enum vocabularies, exact key sets, and schema version; `block` enforces the ≥2-options/labels/recommend rules at record time.

## File structure

```
supskill/                                  (repo root — git init'd by Task 1)
├── .gitignore
├── pyproject.toml                         # project meta + dev group + pytest/ruff config
├── docs/
│   └── state-schema.md                    # schema v1 doc: fields, conventions, mappings (Task 3)
├── scripts/
│   ├── supskill-state                     # executable shim (chmod +x), adjusts sys.path, calls cli.main
│   └── supskill_state/
│       ├── __init__.py                    # version only
│       ├── errors.py                      # StateError
│       ├── model.py                       # schema v1: enums, dataclasses, dict↔model, validation
│       ├── store.py                       # paths, atomic dump, load, append_jsonl, UTC helpers
│       ├── scratch.py                     # SK-004: normalize_sprint_id, derive_scratch
│       ├── transitions.py                 # SK-003: stage order + failed_preconditions (pure)
│       ├── commands.py                    # verbs: init_sprint, render_show, record_artifact,
│       │                                  #        record_gate, record_blocker, advance_stage
│       └── cli.py                         # argparse wiring only; maps StateError → exit 1
└── tests/
    ├── conftest.py                        # make_state factory fixture
    ├── fixtures/state_d2_example.json     # D2's example, realistic values, verbatim structure
    ├── test_scaffold.py                   # Task 1
    ├── test_model.py                      # Task 2
    ├── test_store.py                      # Task 3
    ├── test_scratch.py                    # Task 4
    ├── test_init.py                       # Task 5
    ├── test_show.py                       # Task 6
    ├── test_artifact.py                   # Task 7
    ├── test_gate.py                       # Task 8
    ├── test_block.py                      # Task 9
    ├── test_advance.py                    # Task 10
    └── test_demo.py                       # Task 11: the north-star demo end to end
```

Task order honors the sprint's critical path: scaffold → schema → store → scratch → init/show → artifact → gate → block → **advance last** (its tests exercise the real seams, not stubs) → demo.

---

### Task 1: Repo & package scaffold (SK-007)

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `scripts/supskill_state/__init__.py`
- Create: `scripts/supskill_state/errors.py`
- Create: `scripts/supskill_state/cli.py`
- Create: `scripts/supskill-state` (executable shim)
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: nothing (first task; repo does not exist yet).
- Produces: importable package `supskill_state` with `__version__: str`; `supskill_state.errors.StateError(Exception)`; `supskill_state.cli.build_parser() -> argparse.ArgumentParser` and `supskill_state.cli.main(argv: list[str] | None = None) -> int` (catches `StateError`, prints `supskill-state: refused: <msg>` to stderr, returns 1). Every later task registers its subcommand in `cli.py` and its logic in `commands.py`.

- [ ] **Step 1: Initialize the repo and commit the existing docs**

```bash
cd /home/bessa/Documents/projetos/supskill
git init
```

Create `.gitignore`:

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.venv/
.codegraph/
.omc/
.supskill/
.superpowers/
```

(`.supskill/` and `.superpowers/` cover runtime state from manual demo runs at the repo root; `.codegraph/` and `.omc/` are machine-local and must never be committed.)

```bash
git add .gitignore docs/
git commit -m "chore: import design docs and backlog-01 sprint docs"
git checkout -b feat/e1-state-spine
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "supskill"
version = "0.1.0"
description = "supskill sprint conductor - supskill-state is its state spine"
requires-python = ">=3.11"
dependencies = []

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.8"]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["scripts"]

[tool.ruff]
line-length = 120
src = ["scripts", "tests"]
extend-include = ["scripts/supskill-state"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.ruff.lint.per-file-ignores]
"scripts/supskill-state" = ["E402"]
```

Notes: `package = false` because the package is never installed — pytest imports it via `pythonpath = ["scripts"]` and the shim manages `sys.path` at runtime. `dependencies = []` is load-bearing (Global Constraints).

- [ ] **Step 3: Write the failing test**

`tests/test_scaffold.py`:

```python
"""SK-007: package imports, CLI shim exists and is executable, zero runtime deps."""

import os
import tomllib
from pathlib import Path

import pytest

import supskill_state
from supskill_state.cli import build_parser
from supskill_state.errors import StateError

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_package_importable_and_versioned():
    assert supskill_state.__version__


def test_state_error_is_an_exception():
    assert issubclass(StateError, Exception)


def test_cli_requires_a_subcommand():
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args([])
    assert excinfo.value.code == 2


def test_shim_exists_and_is_executable():
    shim = REPO_ROOT / "scripts" / "supskill-state"
    assert shim.exists()
    assert os.access(shim, os.X_OK)


def test_zero_runtime_dependencies():
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["dependencies"] == []
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `uv run pytest tests/test_scaffold.py -v`
Expected: collection error — `ModuleNotFoundError: No module named 'supskill_state'` (uv will first create `.venv` and install pytest/ruff from the dev group; that is a one-time, local setup).

- [ ] **Step 5: Write the minimal package**

`scripts/supskill_state/__init__.py`:

```python
"""supskill-state - the state spine of supskill.

The only permitted mutator of .supskill/state.json (invariant 3).
"""

__version__ = "0.1.0"
```

`scripts/supskill_state/errors.py`:

```python
class StateError(Exception):
    """A refusal. The message names the violated rule; the CLI maps this to exit 1."""
```

`scripts/supskill_state/cli.py`:

```python
"""Thin argparse shim. The CLI is wiring; the logic lives in commands.py."""

from __future__ import annotations

import argparse
import sys

from .errors import StateError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="supskill-state",
        description=(
            "State spine for supskill sprints: "
            "the only permitted mutator of .supskill/state.json."
        ),
    )
    parser.add_subparsers(dest="command", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except StateError as error:
        print(f"supskill-state: refused: {error}", file=sys.stderr)
        return 1
```

`scripts/supskill-state` (the shim — note: no `.py` extension):

```python
#!/usr/bin/env python3
"""CLI shim: keeps supskill_state importable when run straight from the plugin dir."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from supskill_state.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

```bash
chmod +x scripts/supskill-state
```

- [ ] **Step 6: Run the tests and lint to verify they pass**

Run: `uv run pytest tests/test_scaffold.py -v`
Expected: 5 passed, in well under a second.

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml scripts/ tests/test_scaffold.py
git commit -m "feat: scaffold supskill package with pytest and ruff (SK-007)"
```

---

### Task 2: Schema v1 typed model (SK-001, part 1)

**Files:**
- Create: `scripts/supskill_state/model.py`
- Create: `tests/conftest.py`
- Create: `tests/fixtures/state_d2_example.json`
- Test: `tests/test_model.py`

**Interfaces:**
- Consumes: `supskill_state.errors.StateError` (Task 1).
- Produces (every later task imports from `supskill_state.model`):
  - `SCHEMA_VERSION: int = 1`
  - `class Stage(str, Enum)` with members `SCOPE, REFINE, PLAN, EXECUTE, REVIEW`
  - `STAGE_ORDER: tuple[Stage, ...]` in pipeline order
  - `ENTRY_STAGES: frozenset[Stage]` = `{SCOPE, PLAN, EXECUTE}`
  - `class TaskStatus(str, Enum)` with members `PENDING, DONE, DONE_WITH_CONCERNS, BLOCKED, PARKED`
  - `TERMINAL_STATUSES: frozenset[TaskStatus]` — **the** exported terminal set (SK-003 consumes it)
  - `GATE_KEYS: dict[str, str]` = `{"G1": "G1_sprint_doc", "G2": "G2_plan", "G3": "G3_review"}`
  - `GATE_DECISIONS: tuple[str, str]` = `("approved", "rejected")`
  - `ARTIFACT_KEYS: tuple[str, str]` = `("sprint_doc", "dev_plan")`
  - dataclasses `SprintInfo(id, slug, entry, branch, scratch)`, `Task(id, seam, provable, status)`, `Blocker(task, kind, found, options, recommend)`, `State(schema, backlog, sprint, stage, artifacts, gates, tasks, blockers)`
  - `state_from_dict(raw: dict) -> State`, `state_to_dict(state: State) -> dict`
  - `loads_state(text: str) -> State`, `dumps_state(state: State) -> str`

- [ ] **Step 1: Write the D2 fixture**

`tests/fixtures/state_d2_example.json` — mirrors D2's example verbatim in structure; elided `"…"` values are filled with the real S9a data from D5:

```json
{
  "schema": 1,
  "backlog": "docs/plans/sprints/backlog-02/backlog.md",
  "sprint": {
    "id": "S10",
    "slug": "alerting-spine",
    "entry": "SCOPE",
    "branch": "feat/e10-alerting-spine",
    "scratch": ".superpowers/sdd/s10/"
  },
  "stage": "REFINE",
  "artifacts": {
    "sprint_doc": "docs/plans/sprints/backlog-02/sprint-10-alerting-spine.md",
    "dev_plan": null
  },
  "gates": {
    "G1_sprint_doc": null,
    "G2_plan": null,
    "G3_review": null
  },
  "tasks": [
    {
      "id": "T3",
      "seam": "e2e",
      "provable": "operator",
      "status": "BLOCKED"
    }
  ],
  "blockers": [
    {
      "task": "T3",
      "kind": "needs-live-capture",
      "found": "entity parser returns 0 posts on all 23 profile reads",
      "options": [
        "(a) operator drives a live capture now",
        "(b) defer to next sprint, proceed with the other 4 tasks",
        "(c) re-scope: the drift hypothesis may be wrong"
      ],
      "recommend": "(a) - the drift detector's heuristic may be firing misleadingly"
    }
  ]
}
```

- [ ] **Step 2: Write the shared test fixture**

`tests/conftest.py`:

```python
"""Shared builders: a valid schema-v1 state, small enough to tweak per test."""

import pytest

from supskill_state.model import SprintInfo, Stage, State


@pytest.fixture
def make_state():
    def _make(**overrides):
        state = State(
            schema=1,
            backlog="docs/plans/sprints/backlog-02/backlog.md",
            sprint=SprintInfo(
                id="S10",
                slug="alerting-spine",
                entry=Stage.SCOPE,
                branch="feat/e10-alerting-spine",
                scratch=".superpowers/sdd/s10/",
            ),
            stage=Stage.SCOPE,
            artifacts={"sprint_doc": None, "dev_plan": None},
            gates={"G1_sprint_doc": None, "G2_plan": None, "G3_review": None},
            tasks=[],
            blockers=[],
        )
        for key, value in overrides.items():
            setattr(state, key, value)
        return state

    return _make
```

- [ ] **Step 3: Write the failing tests**

`tests/test_model.py`:

```python
"""SK-001: schema v1 round-trips D2's example; wrong vocabulary refuses loudly."""

import dataclasses
import json
from pathlib import Path

import pytest

from supskill_state.errors import StateError
from supskill_state.model import (
    TERMINAL_STATUSES,
    Stage,
    State,
    TaskStatus,
    dumps_state,
    loads_state,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "state_d2_example.json"


def fixture_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_d2_example_round_trips_field_by_field():
    state = loads_state(fixture_text())
    reloaded = loads_state(dumps_state(state))
    for field in dataclasses.fields(State):
        assert getattr(reloaded, field.name) == getattr(state, field.name), field.name


def test_dump_reproduces_the_fixture_json_exactly():
    state = loads_state(fixture_text())
    assert json.loads(dumps_state(state)) == json.loads(fixture_text())


def test_unknown_schema_version_refuses_loudly():
    raw = json.loads(fixture_text())
    raw["schema"] = 2
    with pytest.raises(StateError, match="unsupported schema version 2"):
        loads_state(json.dumps(raw))


def test_missing_schema_field_refuses():
    raw = json.loads(fixture_text())
    del raw["schema"]
    with pytest.raises(StateError, match="schema"):
        loads_state(json.dumps(raw))


def test_invalid_json_refuses_without_traceback_vocabulary():
    with pytest.raises(StateError, match="not valid JSON"):
        loads_state('{"schema": 1,')


def test_needs_context_is_rejected_as_a_status():
    raw = json.loads(fixture_text())
    raw["tasks"][0]["status"] = "NEEDS_CONTEXT"
    with pytest.raises(StateError, match="controller-loop signal"):
        loads_state(json.dumps(raw))


def test_unknown_status_is_rejected():
    raw = json.loads(fixture_text())
    raw["tasks"][0]["status"] = "IN_PROGRESS"
    with pytest.raises(StateError, match="unknown task status"):
        loads_state(json.dumps(raw))


def test_status_vocabulary_is_exact():
    assert {s.value for s in TaskStatus} == {
        "PENDING",
        "DONE",
        "DONE_WITH_CONCERNS",
        "BLOCKED",
        "PARKED",
    }


def test_terminal_set_is_exported_and_exact():
    assert TERMINAL_STATUSES == frozenset(
        {TaskStatus.DONE, TaskStatus.DONE_WITH_CONCERNS, TaskStatus.BLOCKED, TaskStatus.PARKED}
    )
    assert TaskStatus.PENDING not in TERMINAL_STATUSES


def test_stage_vocabulary_is_exact():
    assert [s.value for s in Stage] == ["SCOPE", "REFINE", "PLAN", "EXECUTE", "REVIEW"]


@pytest.mark.parametrize("bad_entry", ["REFINE", "REVIEW", "execute", "START"])
def test_entry_outside_scope_plan_execute_is_rejected(bad_entry):
    raw = json.loads(fixture_text())
    raw["sprint"]["entry"] = bad_entry
    with pytest.raises(StateError):
        loads_state(json.dumps(raw))


def test_gate_value_outside_vocabulary_is_rejected():
    raw = json.loads(fixture_text())
    raw["gates"]["G1_sprint_doc"] = "maybe"
    with pytest.raises(StateError, match="gates.G1_sprint_doc"):
        loads_state(json.dumps(raw))


def test_gates_keys_must_be_exactly_the_three():
    raw = json.loads(fixture_text())
    raw["gates"]["G4_extra"] = None
    with pytest.raises(StateError, match="exactly"):
        loads_state(json.dumps(raw))
    raw = json.loads(fixture_text())
    del raw["gates"]["G2_plan"]
    with pytest.raises(StateError, match="exactly"):
        loads_state(json.dumps(raw))


def test_artifacts_keys_must_be_exactly_sprint_doc_and_dev_plan():
    raw = json.loads(fixture_text())
    raw["artifacts"]["extra"] = "x"
    with pytest.raises(StateError, match="exactly"):
        loads_state(json.dumps(raw))


def test_make_state_fixture_is_valid(make_state):
    state = make_state()
    assert loads_state(dumps_state(state)) == state
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_model.py -v`
Expected: collection error — `ModuleNotFoundError`/`ImportError` (no `supskill_state.model` yet).

- [ ] **Step 5: Write the model**

`scripts/supskill_state/model.py`:

```python
"""state.json schema v1 - typed model and validation.

Human-readable schema doc: docs/state-schema.md. Two conventions enforced here:

* Task status vocabulary. SDD implementers report DONE / DONE_WITH_CONCERNS /
  NEEDS_CONTEXT / BLOCKED. NEEDS_CONTEXT is a controller-loop signal (the
  controller supplies missing info and re-dispatches the same subagent), not a
  resting state: E5 resolves it in-loop, else the task becomes BLOCKED plus a
  blocker record (D5). It is therefore rejected as a persistable status.

* Sprint completion is a G3 decision, not a sixth stage: REVIEW is terminal,
  and what happens next is Gate 3's recorded decision plus E6's replan verbs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from .errors import StateError

SCHEMA_VERSION = 1


class Stage(str, Enum):
    SCOPE = "SCOPE"
    REFINE = "REFINE"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    REVIEW = "REVIEW"


STAGE_ORDER: tuple[Stage, ...] = (
    Stage.SCOPE,
    Stage.REFINE,
    Stage.PLAN,
    Stage.EXECUTE,
    Stage.REVIEW,
)

ENTRY_STAGES: frozenset[Stage] = frozenset((Stage.SCOPE, Stage.PLAN, Stage.EXECUTE))


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    DONE_WITH_CONCERNS = "DONE_WITH_CONCERNS"
    BLOCKED = "BLOCKED"
    PARKED = "PARKED"


# The terminal set advance --to REVIEW consumes (SK-003). Nothing redefines this.
TERMINAL_STATUSES: frozenset[TaskStatus] = frozenset(
    (TaskStatus.DONE, TaskStatus.DONE_WITH_CONCERNS, TaskStatus.BLOCKED, TaskStatus.PARKED)
)

# CLI gate ids -> state.json gate keys, one-to-one (docs/state-schema.md, "Gates").
GATE_KEYS: dict[str, str] = {"G1": "G1_sprint_doc", "G2": "G2_plan", "G3": "G3_review"}

GATE_DECISIONS: tuple[str, str] = ("approved", "rejected")

ARTIFACT_KEYS: tuple[str, str] = ("sprint_doc", "dev_plan")


@dataclass
class SprintInfo:
    id: str
    slug: str | None
    entry: Stage
    branch: str | None
    scratch: str


@dataclass
class Task:
    id: str
    seam: str
    provable: str
    status: TaskStatus


@dataclass
class Blocker:
    task: str
    kind: str
    found: str
    options: list[str]
    recommend: str


@dataclass
class State:
    schema: int
    backlog: str | None
    sprint: SprintInfo
    stage: Stage
    artifacts: dict[str, str | None]
    gates: dict[str, str | None]
    tasks: list[Task]
    blockers: list[Blocker]


def _require(mapping: dict, key: str, where: str):
    if key not in mapping:
        raise StateError(f"{where}: missing required field {key!r}")
    return mapping[key]


def _opt_str(value, where: str) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise StateError(f"{where}: expected a string or null, got {type(value).__name__}")


def _req_str(mapping: dict, key: str, where: str) -> str:
    value = _require(mapping, key, where)
    if not isinstance(value, str):
        raise StateError(f"{where}.{key}: expected a string, got {type(value).__name__}")
    return value


def _parse_stage(value, where: str) -> Stage:
    try:
        return Stage(value)
    except ValueError:
        raise StateError(
            f"{where}: unknown stage {value!r}; expected one of "
            f"{[s.value for s in Stage]}"
        ) from None


def _parse_status(value, where: str) -> TaskStatus:
    if value == "NEEDS_CONTEXT":
        raise StateError(
            f"{where}: NEEDS_CONTEXT is a controller-loop signal, not a task state - "
            "resolve it in-loop, else record BLOCKED plus a blocker "
            "(see docs/state-schema.md)"
        )
    try:
        return TaskStatus(value)
    except ValueError:
        raise StateError(
            f"{where}: unknown task status {value!r}; expected one of "
            f"{[s.value for s in TaskStatus]}"
        ) from None


def _parse_sprint(raw, where: str) -> SprintInfo:
    if not isinstance(raw, dict):
        raise StateError(f"{where}: expected an object")
    entry = _parse_stage(_require(raw, "entry", where), f"{where}.entry")
    if entry not in ENTRY_STAGES:
        raise StateError(
            f"{where}.entry: must be one of SCOPE|PLAN|EXECUTE, got {entry.value}"
        )
    return SprintInfo(
        id=_req_str(raw, "id", where),
        slug=_opt_str(_require(raw, "slug", where), f"{where}.slug"),
        entry=entry,
        branch=_opt_str(_require(raw, "branch", where), f"{where}.branch"),
        scratch=_req_str(raw, "scratch", where),
    )


def _parse_gates(raw, where: str) -> dict[str, str | None]:
    if not isinstance(raw, dict):
        raise StateError(f"{where}: expected an object")
    expected = set(GATE_KEYS.values())
    if set(raw) != expected:
        raise StateError(f"{where}: must have exactly the keys {sorted(expected)}, got {sorted(raw)}")
    gates: dict[str, str | None] = {}
    for key in GATE_KEYS.values():
        value = _opt_str(raw[key], f"{where}.{key}")
        if value is not None and value not in GATE_DECISIONS:
            raise StateError(
                f"{where}.{key}: expected null or one of {list(GATE_DECISIONS)}, got {value!r}"
            )
        gates[key] = value
    return gates


def _parse_artifacts(raw, where: str) -> dict[str, str | None]:
    if not isinstance(raw, dict):
        raise StateError(f"{where}: expected an object")
    if set(raw) != set(ARTIFACT_KEYS):
        raise StateError(
            f"{where}: must have exactly the keys {sorted(ARTIFACT_KEYS)}, got {sorted(raw)}"
        )
    return {key: _opt_str(raw[key], f"{where}.{key}") for key in ARTIFACT_KEYS}


def blocker_from_dict(raw, where: str) -> Blocker:
    if not isinstance(raw, dict):
        raise StateError(f"{where}: expected an object")
    options = _require(raw, "options", where)
    if not isinstance(options, list) or not all(isinstance(o, str) for o in options):
        raise StateError(f"{where}.options: expected a list of strings")
    return Blocker(
        task=_req_str(raw, "task", where),
        kind=_req_str(raw, "kind", where),
        found=_req_str(raw, "found", where),
        options=list(options),
        recommend=_req_str(raw, "recommend", where),
    )


def state_from_dict(raw: dict) -> State:
    if not isinstance(raw, dict):
        raise StateError("state: expected a JSON object")
    schema = _require(raw, "schema", "state")
    if schema != SCHEMA_VERSION:
        raise StateError(
            f"unsupported schema version {schema!r}: this tool reads schema "
            f"{SCHEMA_VERSION} only, refusing to guess"
        )
    tasks_raw = _require(raw, "tasks", "state")
    blockers_raw = _require(raw, "blockers", "state")
    if not isinstance(tasks_raw, list) or not isinstance(blockers_raw, list):
        raise StateError("state: tasks and blockers must be lists")
    tasks = []
    for index, task_raw in enumerate(tasks_raw):
        where = f"tasks[{index}]"
        if not isinstance(task_raw, dict):
            raise StateError(f"{where}: expected an object")
        tasks.append(
            Task(
                id=_req_str(task_raw, "id", where),
                seam=_req_str(task_raw, "seam", where),
                provable=_req_str(task_raw, "provable", where),
                status=_parse_status(_require(task_raw, "status", where), f"{where}.status"),
            )
        )
    return State(
        schema=SCHEMA_VERSION,
        backlog=_opt_str(_require(raw, "backlog", "state"), "state.backlog"),
        sprint=_parse_sprint(_require(raw, "sprint", "state"), "sprint"),
        stage=_parse_stage(_require(raw, "stage", "state"), "state.stage"),
        artifacts=_parse_artifacts(_require(raw, "artifacts", "state"), "artifacts"),
        gates=_parse_gates(_require(raw, "gates", "state"), "gates"),
        tasks=tasks,
        blockers=[
            blocker_from_dict(b, f"blockers[{i}]") for i, b in enumerate(blockers_raw)
        ],
    )


def state_to_dict(state: State) -> dict:
    return {
        "schema": state.schema,
        "backlog": state.backlog,
        "sprint": {
            "id": state.sprint.id,
            "slug": state.sprint.slug,
            "entry": state.sprint.entry.value,
            "branch": state.sprint.branch,
            "scratch": state.sprint.scratch,
        },
        "stage": state.stage.value,
        "artifacts": {key: state.artifacts[key] for key in ARTIFACT_KEYS},
        "gates": {key: state.gates[key] for key in GATE_KEYS.values()},
        "tasks": [
            {"id": t.id, "seam": t.seam, "provable": t.provable, "status": t.status.value}
            for t in state.tasks
        ],
        "blockers": [
            {
                "task": b.task,
                "kind": b.kind,
                "found": b.found,
                "options": list(b.options),
                "recommend": b.recommend,
            }
            for b in state.blockers
        ],
    }


def loads_state(text: str) -> State:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise StateError(f"state is not valid JSON: {error}") from error
    return state_from_dict(raw)


def dumps_state(state: State) -> str:
    return json.dumps(state_to_dict(state), indent=2) + "\n"
```

- [ ] **Step 6: Run the tests and lint to verify they pass**

Run: `uv run pytest tests/test_model.py -v`
Expected: all pass.

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add scripts/supskill_state/model.py tests/conftest.py tests/fixtures/ tests/test_model.py
git commit -m "feat: state.json schema v1 typed model with strict validation (SK-001)"
```

---

### Task 3: Atomic store, append-only logs, one datetime convention (SK-001, part 2)

**Files:**
- Create: `scripts/supskill_state/store.py`
- Create: `docs/state-schema.md`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `StateError` (Task 1); `State`, `loads_state`, `dumps_state` (Task 2).
- Produces (every command task imports from `supskill_state.store`):
  - `SUPSKILL_DIR: str = ".supskill"`
  - `supskill_dir(root: Path | None = None) -> Path` (defaults to `Path.cwd()`)
  - `state_path(root=None) -> Path` → `<root>/.supskill/state.json`
  - `gates_path(root=None) -> Path` → `<root>/.supskill/gates.jsonl`
  - `runs_dir(root=None) -> Path` → `<root>/.supskill/runs`
  - `load_state(path: Path) -> State` — refuses (StateError) on missing file with a message naming `init`
  - `dump_state(state: State, path: Path) -> None` — atomic: same-dir temp + `os.replace`
  - `append_jsonl(path: Path, record: dict) -> None` — opens `"a"` only, one JSON line
  - `now_utc_iso() -> str` — aware-UTC ISO-8601 timestamp
  - `require_aware_utc_iso(value: str, where: str) -> None` — StateError unless aware UTC ISO-8601

- [ ] **Step 1: Write the failing tests**

`tests/test_store.py`:

```python
"""SK-001: atomic writes survive a mid-write kill; timestamps are aware-UTC everywhere."""

import json

import pytest

from supskill_state import store
from supskill_state.errors import StateError
from supskill_state.model import Stage
from supskill_state.store import (
    append_jsonl,
    dump_state,
    load_state,
    now_utc_iso,
    require_aware_utc_iso,
    state_path,
)


def test_load_missing_file_refuses_with_a_clear_message(tmp_path):
    with pytest.raises(StateError, match="init"):
        load_state(state_path(tmp_path))


def test_dump_then_load_round_trips(tmp_path, make_state):
    path = state_path(tmp_path)
    state = make_state(stage=Stage.REFINE)
    dump_state(state, path)
    assert load_state(path) == state


def test_partial_temp_file_from_a_killed_write_is_ignored_on_load(tmp_path, make_state):
    # simulate a process killed mid-write: a truncated temp file beside a valid state.json
    path = state_path(tmp_path)
    state = make_state()
    dump_state(state, path)
    (path.parent / "state.json.tmp-killed").write_text('{"schema": 1, "backlog": "docs/')
    assert load_state(path) == state


def test_interrupted_write_leaves_previous_state_intact(tmp_path, make_state, monkeypatch):
    path = state_path(tmp_path)
    dump_state(make_state(), path)
    before = path.read_bytes()

    def crash(src, dst):
        raise RuntimeError("killed mid-write")

    monkeypatch.setattr(store.os, "replace", crash)
    with pytest.raises(RuntimeError):
        dump_state(make_state(stage=Stage.REFINE), path)
    assert path.read_bytes() == before
    # and the crashed write's temp file was cleaned up
    assert [p.name for p in path.parent.iterdir()] == ["state.json"]


def test_append_jsonl_appends_and_never_truncates(tmp_path):
    path = tmp_path / "gates.jsonl"
    append_jsonl(path, {"n": 1})
    append_jsonl(path, {"n": 2})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["n"] for line in lines] == [1, 2]


def test_now_utc_iso_is_aware_utc():
    require_aware_utc_iso(now_utc_iso(), "test")


@pytest.mark.parametrize(
    "bad",
    [
        "2026-07-12T18:00:00",        # naive
        "2026-07-12T18:00:00+02:00",  # aware but not UTC
        "12/07/2026 18:00",           # not ISO-8601
        "",
    ],
)
def test_non_aware_utc_timestamps_are_rejected(bad):
    with pytest.raises(StateError):
        require_aware_utc_iso(bad, "test")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_store.py -v`
Expected: collection error — no module `supskill_state.store`.

- [ ] **Step 3: Write the store**

`scripts/supskill_state/store.py`:

```python
"""Reading and writing supskill state on disk.

state.json writes are atomic (same-directory temp + os.replace): state.json is
the resume mechanism for a disposable conductor (invariant 5), so a process
killed mid-write must leave the previous valid file, never a truncated one.

The .jsonl audit logs are append-only, structurally: this module only ever
opens them with mode "a" and nothing here can truncate or rewrite them.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .errors import StateError
from .model import State, dumps_state, loads_state

SUPSKILL_DIR = ".supskill"


def supskill_dir(root: Path | None = None) -> Path:
    return (root or Path.cwd()) / SUPSKILL_DIR


def state_path(root: Path | None = None) -> Path:
    return supskill_dir(root) / "state.json"


def gates_path(root: Path | None = None) -> Path:
    return supskill_dir(root) / "gates.jsonl"


def runs_dir(root: Path | None = None) -> Path:
    return supskill_dir(root) / "runs"


def load_state(path: Path) -> State:
    if not path.exists():
        raise StateError(f"no state file at {path} - run 'supskill-state init' first")
    return loads_state(path.read_text(encoding="utf-8"))


def dump_state(state: State, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(dumps_state(state))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def append_jsonl(path: Path, record: dict) -> None:
    """Append one record. Opens in append mode only - never truncates or rewrites."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_aware_utc_iso(value: str, where: str) -> None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise StateError(f"{where}: not an ISO-8601 timestamp: {value!r}") from error
    if parsed.utcoffset() != timedelta(0):
        raise StateError(f"{where}: timestamps must be timezone-aware UTC, got {value!r}")
```

- [ ] **Step 4: Write the schema doc**

`docs/state-schema.md`:

```markdown
# `.supskill/` state - schema v1

`supskill-state` (in `scripts/`) is the **only** permitted mutator of these
files (invariant 3). Layout:

    .supskill/
      state.json              # authoritative; the only file the conductor reads to resume
      gates.jsonl             # every gate decision + the operator's verbatim response (append-only)
      runs/<normalized-id>/
        blockers.jsonl        # every blocker record raised during execution (append-only)
        archive-<n>/          # a prior run's state.json + gates.jsonl, moved by `init --archive`

## Conventions

- **Datetime**: every timestamp anywhere in these files is timezone-aware UTC,
  ISO-8601 (e.g. `2026-07-12T18:00:00+00:00`). Naive or non-UTC timestamps are
  a validation error.
- **Atomicity**: `state.json` is written via same-directory temp + rename; the
  `.jsonl` logs are opened append-only and never truncated or rewritten.
- **Write order**: where one verb writes a log and `state.json`, the log is
  written first. A crash between the writes leaves the audit trail *ahead of*
  state, never behind.

## `state.json` fields

- `schema` (int): always `1`. Any other value refuses on load - no silent
  migration.
- `backlog` (string|null): path to the backlog driving this sprint.
- `sprint.id` (string): as the operator typed it (e.g. `S10`).
- `sprint.slug` (string|null), `sprint.branch` (string|null).
- `sprint.entry` (string): `SCOPE | PLAN | EXECUTE` (D7). Preconditions attach
  to *transitions taken*, not stages - a sprint entering at EXECUTE never
  crosses the G2 check.
- `sprint.scratch` (string): **derived** from the id, never typed:
  `.superpowers/sdd/<normalized-id>/` where normalization is lowercase and only
  `[a-z0-9-]` is accepted (anything else refuses; D8).
- `stage` (string): `SCOPE | REFINE | PLAN | EXECUTE | REVIEW`. Sprint
  completion is a **G3 decision, not a sixth stage**.
- `artifacts`: exactly `sprint_doc` and `dev_plan`, each a path or null.
- `gates`: exactly `G1_sprint_doc`, `G2_plan`, `G3_review`; each
  `null | "approved" | "rejected"` (last decision wins; full history lives in
  `gates.jsonl`).
- `tasks[]`: `{id, seam, provable, status}`. `seam` and `provable` use D9's
  taxonomy (`unit|integration|app-level|e2e`; `offline|operator`) and are
  stored as free strings in v1.
- `blockers[]`: `{task, kind, found, options[], recommend}` (D5). Options are
  labeled `(a) ...`; `recommend` starts with one of those labels.

## Task status

`PENDING -> DONE | DONE_WITH_CONCERNS | BLOCKED | PARKED`.
The terminal set `{DONE, DONE_WITH_CONCERNS, BLOCKED, PARKED}` is exported as
`supskill_state.model.TERMINAL_STATUSES`; consume it, never redefine it.

**`NEEDS_CONTEXT` is not a state** (for E5): SDD implementers may report it,
but its defined handling is "controller supplies missing info, re-dispatches
the same subagent" - a loop signal. Resolve it in-loop; if it cannot be
resolved, the task becomes `BLOCKED` plus a blocker record. `supskill-state`
rejects `NEEDS_CONTEXT` as a status value.

## Gates

CLI ids map one-to-one onto state keys:

| CLI id | state key      | guards transition    |
|--------|----------------|----------------------|
| `G1`   | `G1_sprint_doc`| `advance --to PLAN`   |
| `G2`   | `G2_plan`      | `advance --to EXECUTE`|
| `G3`   | `G3_review`    | (E6's replan verbs)   |

`gates.jsonl` records `{gate, decision, response, at}` per decision, where
`gate` is the CLI id, `decision` is `approved|rejected`, `response` is the
operator's verbatim words (an **empty response is accepted and recorded** -
the audit trail's job is to make a fabricated approval readable, F-4), and
`at` is aware-UTC ISO-8601.
```

- [ ] **Step 5: Run the tests and lint to verify they pass**

Run: `uv run pytest tests/test_store.py -v`
Expected: all pass.

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add scripts/supskill_state/store.py docs/state-schema.md tests/test_store.py
git commit -m "feat: atomic state writes, append-only jsonl, UTC timestamp enforcement (SK-001)"
```

---

### Task 4: Derived scratch paths (SK-004)

**Files:**
- Create: `scripts/supskill_state/scratch.py`
- Test: `tests/test_scratch.py`

**Interfaces:**
- Consumes: `StateError` (Task 1).
- Produces (Task 5's `init` and Task 9's `block` consume these):
  - `SCRATCH_ROOT: str = ".superpowers/sdd"`
  - `normalize_sprint_id(sprint_id: str) -> str` — lowercase; StateError unless result matches `^[a-z0-9-]+$`
  - `derive_scratch(sprint_id: str) -> str` — `".superpowers/sdd/<normalized>/"`

**No user-typed override exists anywhere** — no function parameter, no CLI flag, in this task or any later one. Derived, never typed (D8).

- [ ] **Step 1: Write the failing tests**

`tests/test_scratch.py`:

```python
"""SK-004: scratch paths are derived from the sprint id; collisions are impossible."""

import pytest

from supskill_state.errors import StateError
from supskill_state.scratch import derive_scratch, normalize_sprint_id


def test_s9a_scratch_path_differs_from_s9():
    # the design's own named test (design decisions, section 6)
    assert derive_scratch("S9a") != derive_scratch("S9")


def test_path_shape():
    assert derive_scratch("S10") == ".superpowers/sdd/s10/"


def test_case_variants_are_the_same_sprint():
    assert derive_scratch("S9") == derive_scratch("s9")
    assert normalize_sprint_id("SPRINT-01") == "sprint-01"


@pytest.mark.parametrize(
    "bad_id",
    ["s9_a", "s 9", "s9/../s10", "", "S9.A", "sprint#1", "s9é", ".", "s9/"],
)
def test_ids_that_will_not_normalize_cleanly_are_rejected_never_mangled(bad_id):
    with pytest.raises(StateError, match="refusing"):
        normalize_sprint_id(bad_id)


def test_distinct_normalized_ids_always_yield_distinct_paths():
    # property-style: derive over a broad id sample; distinct normal forms -> distinct paths
    ids = (
        [f"s{n}" for n in range(60)]
        + [f"s{n}a" for n in range(60)]
        + [f"sprint-{n:02d}" for n in range(30)]
        + ["backlog-02-s3", "s9b", "e1-state-spine"]
    )
    normalized = [normalize_sprint_id(i) for i in ids]
    paths = [derive_scratch(i) for i in ids]
    assert len(set(paths)) == len(set(normalized)) == len(ids)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scratch.py -v`
Expected: collection error — no module `supskill_state.scratch`.

- [ ] **Step 3: Write the implementation**

`scripts/supskill_state/scratch.py`:

```python
"""Derived SDD scratch paths (D8): computed from the sprint id, never typed.

SDD's default repo-wide scratch dir namespaces task briefs by task number only,
and task numbering restarts every sprint - so two sprints' "Task 3" briefs
silently overwrite each other. Every sprint therefore gets its own
.superpowers/sdd/<normalized-id>/, derived at init, stored in state.json.
There is deliberately NO override flag or parameter anywhere.
"""

import re

from .errors import StateError

SCRATCH_ROOT = ".superpowers/sdd"

_NORMALIZED = re.compile(r"^[a-z0-9-]+$")


def normalize_sprint_id(sprint_id: str) -> str:
    normalized = sprint_id.lower()
    if not _NORMALIZED.fullmatch(normalized):
        raise StateError(
            f"sprint id {sprint_id!r} is not usable: after lowercasing it must contain "
            "only [a-z0-9-]; refusing to mangle it into a path"
        )
    return normalized


def derive_scratch(sprint_id: str) -> str:
    return f"{SCRATCH_ROOT}/{normalize_sprint_id(sprint_id)}/"
```

- [ ] **Step 4: Run the tests and lint to verify they pass**

Run: `uv run pytest tests/test_scratch.py -v`
Expected: all pass.

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add scripts/supskill_state/scratch.py tests/test_scratch.py
git commit -m "feat: derive sprint scratch path from sprint id (SK-004)"
```

---

### Task 5: `supskill-state init` (SK-002, part 1)

**Files:**
- Create: `scripts/supskill_state/commands.py`
- Modify: `scripts/supskill_state/cli.py` (register the `init` subcommand)
- Test: `tests/test_init.py`

**Interfaces:**
- Consumes: `State`, `SprintInfo`, `Stage`, `ENTRY_STAGES`, `ARTIFACT_KEYS`, `GATE_KEYS` (Task 2); `store.state_path/gates_path/runs_dir/supskill_dir/dump_state` (Task 3); `derive_scratch`, `normalize_sprint_id` (Task 4).
- Produces:
  - `commands.init_sprint(sprint_id: str, *, slug: str | None = None, entry: str = "SCOPE", backlog: str | None = None, branch: str | None = None, archive: bool = False, root: Path | None = None) -> State`
  - CLI: `supskill-state init <sprint-id> [--slug S] [--entry SCOPE|PLAN|EXECUTE] [--backlog P] [--branch B] [--archive]`
  - Every command function takes `root: Path | None = None` (defaults to CWD) so tests never chdir for library-level calls.

- [ ] **Step 1: Write the failing tests**

`tests/test_init.py`:

```python
"""SK-002: init creates the sprint layout, honors entry points, never clobbers."""

import json

import pytest

from supskill_state.commands import init_sprint
from supskill_state.errors import StateError
from supskill_state.model import Stage
from supskill_state.store import gates_path, load_state, runs_dir, state_path, supskill_dir


def test_init_creates_state_gates_and_runs_dir(tmp_path):
    state = init_sprint("S1", slug="state-spine", branch="feat/e1-state-spine", root=tmp_path)
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
    init_sprint("s1", root=tmp_path)
    before = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match="--archive"):
        init_sprint("s2", root=tmp_path)
    assert state_path(tmp_path).read_bytes() == before


def test_init_archive_preserves_old_state_and_gates(tmp_path):
    init_sprint("s1", root=tmp_path)
    gates_path(tmp_path).write_text('{"gate": "G1"}\n')  # stand-in for a recorded decision
    old_state = state_path(tmp_path).read_bytes()

    state = init_sprint("s2", archive=True, root=tmp_path)

    archive = runs_dir(tmp_path) / "s1" / "archive-1"
    assert (archive / "state.json").read_bytes() == old_state
    assert (archive / "gates.jsonl").read_text() == '{"gate": "G1"}\n'
    assert state.sprint.id == "s2"
    assert gates_path(tmp_path).read_text() == ""  # fresh, empty trail for the new run


def test_init_archive_twice_numbers_archives(tmp_path):
    init_sprint("s1", root=tmp_path)
    init_sprint("s1", archive=True, root=tmp_path)
    init_sprint("s1", archive=True, root=tmp_path)
    assert (runs_dir(tmp_path) / "s1" / "archive-1" / "state.json").exists()
    assert (runs_dir(tmp_path) / "s1" / "archive-2" / "state.json").exists()


def test_init_archives_unreadable_old_state_under_unknown(tmp_path):
    supskill_dir(tmp_path).mkdir(parents=True)
    state_path(tmp_path).write_text("{corrupted")
    init_sprint("s1", archive=True, root=tmp_path)
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
    assert main(["init", "s1"]) == 0
    assert main(["init", "s2"]) == 1
    assert "refused" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_init.py -v`
Expected: collection error — no module `supskill_state.commands`.

- [ ] **Step 3: Write the implementation**

`scripts/supskill_state/commands.py`:

```python
"""The verbs of supskill-state. Each verb validates fully, then writes.

Every write to state.json goes through store.dump_state (atomic) and every
audit line through store.append_jsonl (append-only). Where a verb writes both,
the audit trail is written FIRST: a crash between the writes leaves the trail
ahead of state - a decision may need re-applying, but it can never have
silently not happened.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import store
from .errors import StateError
from .model import (
    ARTIFACT_KEYS,
    ENTRY_STAGES,
    GATE_KEYS,
    SprintInfo,
    Stage,
    State,
)
from .scratch import derive_scratch, normalize_sprint_id


def init_sprint(
    sprint_id: str,
    *,
    slug: str | None = None,
    entry: str = "SCOPE",
    backlog: str | None = None,
    branch: str | None = None,
    archive: bool = False,
    root: Path | None = None,
) -> State:
    root = Path(root) if root is not None else Path.cwd()
    try:
        entry_stage = Stage(entry)
    except ValueError:
        raise StateError(f"unknown entry stage {entry!r}") from None
    if entry_stage not in ENTRY_STAGES:
        raise StateError(f"--entry must be one of SCOPE|PLAN|EXECUTE, got {entry_stage.value}")
    scratch = derive_scratch(sprint_id)  # validates the id before any disk change
    normalized = normalize_sprint_id(sprint_id)

    path = store.state_path(root)
    if path.exists():
        if not archive:
            raise StateError(
                f"{path} already exists; pass --archive to archive the old run first "
                "(prior state is never destroyed)"
            )
        _archive_existing(root)

    state = State(
        schema=1,
        backlog=backlog,
        sprint=SprintInfo(id=sprint_id, slug=slug, entry=entry_stage, branch=branch, scratch=scratch),
        stage=entry_stage,
        artifacts={key: None for key in ARTIFACT_KEYS},
        gates={key: None for key in GATE_KEYS.values()},
        tasks=[],
        blockers=[],
    )
    (store.runs_dir(root) / normalized).mkdir(parents=True, exist_ok=True)
    gates_file = store.gates_path(root)
    if not gates_file.exists():  # touch, never truncate (append-only invariant)
        gates_file.parent.mkdir(parents=True, exist_ok=True)
        gates_file.touch()
    store.dump_state(state, path)
    return state


def _archive_existing(root: Path) -> Path:
    supdir = store.supskill_dir(root)
    old_id = "unknown"
    try:
        raw = json.loads((supdir / "state.json").read_text(encoding="utf-8"))
        old_id = normalize_sprint_id(str(raw["sprint"]["id"]))
    except Exception:
        pass  # an unreadable old state is still archived, never destroyed
    number = 1
    while (supdir / "runs" / old_id / f"archive-{number}").exists():
        number += 1
    destination = supdir / "runs" / old_id / f"archive-{number}"
    destination.mkdir(parents=True)
    (supdir / "state.json").rename(destination / "state.json")
    old_gates = supdir / "gates.jsonl"
    if old_gates.exists():
        old_gates.rename(destination / "gates.jsonl")
    return destination
```

Modify `scripts/supskill_state/cli.py` — replace its full contents with:

```python
"""Thin argparse shim. The CLI is wiring; the logic lives in commands.py."""

from __future__ import annotations

import argparse
import sys

from . import commands
from .errors import StateError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="supskill-state",
        description=(
            "State spine for supskill sprints: "
            "the only permitted mutator of .supskill/state.json."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_init(subparsers)
    return parser


def _add_init(subparsers) -> None:
    sub = subparsers.add_parser("init", help="create .supskill/ for a new sprint run")
    sub.add_argument("sprint_id", help="sprint id, e.g. s1 (lowercase [a-z0-9-] after normalizing)")
    sub.add_argument("--slug", help="human slug, e.g. state-spine")
    sub.add_argument("--entry", choices=["SCOPE", "PLAN", "EXECUTE"], default="SCOPE")
    sub.add_argument("--backlog", help="path to the backlog driving this sprint")
    sub.add_argument("--branch", help="git branch for this sprint")
    sub.add_argument(
        "--archive",
        action="store_true",
        help="archive an existing run under runs/<old-id>/ instead of refusing",
    )
    sub.set_defaults(func=_cmd_init)


def _cmd_init(args) -> int:
    state = commands.init_sprint(
        args.sprint_id,
        slug=args.slug,
        entry=args.entry,
        backlog=args.backlog,
        branch=args.branch,
        archive=args.archive,
    )
    print(
        f"initialized sprint {state.sprint.id} at {state.stage.value} "
        f"(scratch: {state.sprint.scratch})"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except StateError as error:
        print(f"supskill-state: refused: {error}", file=sys.stderr)
        return 1
```

(Note: `test_cli_requires_a_subcommand` in `tests/test_scaffold.py` still passes — `parse_args([])` still exits 2 because a subcommand is required.)

- [ ] **Step 4: Run the whole suite and lint to verify green**

Run: `uv run pytest -v`
Expected: all pass (all prior tasks' tests plus the new ones).

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_init.py
git commit -m "feat: supskill-state init with archive-not-clobber and entry points (SK-002)"
```

---

### Task 6: `supskill-state show` (SK-002, part 2)

**Files:**
- Modify: `scripts/supskill_state/commands.py` (add `render_show`, `_last_gate_responses`)
- Modify: `scripts/supskill_state/cli.py` (register `show`)
- Test: `tests/test_show.py`

**Interfaces:**
- Consumes: `init_sprint` (Task 5); `store.load_state/dump_state/append_jsonl/gates_path/state_path` (Task 3); `Task`, `TaskStatus`, `Blocker`, `GATE_KEYS` (Task 2).
- Produces:
  - `commands.render_show(root: Path | None = None) -> str` — human-readable summary; raises StateError when no state exists
  - `commands._last_gate_responses(root: Path | None = None) -> dict[str, str]` — state-key → last recorded verbatim response, read from `gates.jsonl`
  - CLI: `supskill-state show`

If the sprint tightens, THIS task's output polish is the designated cut — never a precondition.

- [ ] **Step 1: Write the failing tests**

`tests/test_show.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_show.py -v`
Expected: FAIL — `ImportError: cannot import name 'render_show'`.

- [ ] **Step 3: Write the implementation**

Append to `scripts/supskill_state/commands.py` (and extend its imports: add `from collections import Counter` under the stdlib imports, and add `TaskStatus` to the `.model` import list):

```python
def render_show(root: Path | None = None) -> str:
    root = Path(root) if root is not None else Path.cwd()
    state = store.load_state(store.state_path(root))
    responses = _last_gate_responses(root)

    slug = f" ({state.sprint.slug})" if state.sprint.slug else ""
    lines = [
        f"sprint {state.sprint.id}{slug} - stage {state.stage.value} "
        f"(entered at {state.sprint.entry.value})",
        "gates:",
    ]
    for cli_id, key in GATE_KEYS.items():
        decision = state.gates[key] if state.gates[key] is not None else "-"
        line = f"  {cli_id} {key}: {decision}"
        if key in responses:
            line += f'  response: "{responses[key]}"'
        lines.append(line)

    counts = Counter(task.status for task in state.tasks)
    by_status = ", ".join(
        f"{counts[status]} {status.value}" for status in TaskStatus if counts[status]
    )
    lines.append(f"tasks: {len(state.tasks)} total" + (f" - {by_status}" if by_status else ""))

    if state.blockers:
        lines.append("open blockers:")
        for blocker in state.blockers:
            lines.append(f"  {blocker.task} [{blocker.kind}] {blocker.found}")
            for option in blocker.options:
                lines.append(f"      {option}")
            lines.append(f"    recommend: {blocker.recommend}")
    else:
        lines.append("open blockers: none")
    return "\n".join(lines) + "\n"


def _last_gate_responses(root: Path | None = None) -> dict[str, str]:
    gates_file = store.gates_path(root)
    responses: dict[str, str] = {}
    if not gates_file.exists():
        return responses
    for line in gates_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        key = GATE_KEYS.get(record.get("gate"))
        if key is not None:
            responses[key] = record.get("response", "")
    return responses
```

Modify `scripts/supskill_state/cli.py` — add `_add_show(subparsers)` right after `_add_init(subparsers)` inside `build_parser()`, and add:

```python
def _add_show(subparsers) -> None:
    sub = subparsers.add_parser("show", help="print stage, gates, task counts, open blockers")
    sub.set_defaults(func=_cmd_show)


def _cmd_show(args) -> int:
    print(commands.render_show(), end="")
    return 0
```

- [ ] **Step 4: Run the whole suite and lint to verify green**

Run: `uv run pytest -v`
Expected: all pass.

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_show.py
git commit -m "feat: supskill-state show (SK-002)"
```

---

### Task 7: `supskill-state artifact` (plan-time discovery — see Decision 4)

**Files:**
- Modify: `scripts/supskill_state/commands.py` (add `record_artifact`)
- Modify: `scripts/supskill_state/cli.py` (register `artifact`)
- Test: `tests/test_artifact.py`

**Interfaces:**
- Consumes: `ARTIFACT_KEYS` (Task 2); `store.load_state/dump_state/state_path` (Task 3); `init_sprint` (Task 5).
- Produces:
  - `commands.record_artifact(name: str, file_path: str, root: Path | None = None) -> State` — `name ∈ {"sprint_doc", "dev_plan"}`; refuses if the file does not exist under `root`
  - CLI: `supskill-state artifact --set sprint_doc|dev_plan --path <path>`

This is the seam E3 (SCOPE output) and E4 (PLAN output) will call to record what a stage produced; `advance`'s preconditions read it (Task 10). It was not in the sprint's story list — it is proposed as a backlog delta (see "Backlog deltas" at the end of this plan).

- [ ] **Step 1: Write the failing tests**

`tests/test_artifact.py`:

```python
"""Plan-time discovery: recording stage artifacts, the field advance's preconditions read."""

import pytest

from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_artifact
from supskill_state.errors import StateError
from supskill_state.store import load_state, state_path


def test_artifact_records_the_path(tmp_path):
    init_sprint("s1", root=tmp_path)
    (tmp_path / "sprint-doc.md").write_text("# sprint doc\n")
    state = record_artifact("sprint_doc", "sprint-doc.md", root=tmp_path)
    assert state.artifacts["sprint_doc"] == "sprint-doc.md"
    assert load_state(state_path(tmp_path)).artifacts["sprint_doc"] == "sprint-doc.md"


def test_artifact_unknown_name_refused(tmp_path):
    init_sprint("s1", root=tmp_path)
    (tmp_path / "x.md").write_text("x")
    with pytest.raises(StateError, match="unknown artifact"):
        record_artifact("review_doc", "x.md", root=tmp_path)


def test_artifact_missing_file_refused_and_state_untouched(tmp_path):
    init_sprint("s1", root=tmp_path)
    before = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match="not found"):
        record_artifact("sprint_doc", "no-such-file.md", root=tmp_path)
    assert state_path(tmp_path).read_bytes() == before


def test_artifact_requires_an_initialized_sprint(tmp_path):
    (tmp_path / "doc.md").write_text("x")
    with pytest.raises(StateError, match="init"):
        record_artifact("sprint_doc", "doc.md", root=tmp_path)


def test_cli_artifact(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s1"]) == 0
    (tmp_path / "doc.md").write_text("x")
    assert main(["artifact", "--set", "sprint_doc", "--path", "doc.md"]) == 0
    assert main(["artifact", "--set", "sprint_doc", "--path", "missing.md"]) == 1
    assert "refused" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_artifact.py -v`
Expected: FAIL — `ImportError: cannot import name 'record_artifact'`.

- [ ] **Step 3: Write the implementation**

Append to `scripts/supskill_state/commands.py`:

```python
def record_artifact(name: str, file_path: str, root: Path | None = None) -> State:
    root = Path(root) if root is not None else Path.cwd()
    if name not in ARTIFACT_KEYS:
        raise StateError(f"unknown artifact {name!r}; expected one of {list(ARTIFACT_KEYS)}")
    if not file_path:
        raise StateError("artifact path must not be empty")
    if not (root / file_path).exists():
        raise StateError(f"artifact file not found: {file_path}")
    state = store.load_state(store.state_path(root))
    state.artifacts[name] = file_path
    store.dump_state(state, store.state_path(root))
    return state
```

Modify `scripts/supskill_state/cli.py` — add `_add_artifact(subparsers)` after `_add_show(subparsers)` inside `build_parser()`, and add:

```python
def _add_artifact(subparsers) -> None:
    sub = subparsers.add_parser("artifact", help="record a stage's produced artifact path")
    sub.add_argument("--set", required=True, choices=["sprint_doc", "dev_plan"], dest="name")
    sub.add_argument("--path", required=True, help="path to the produced artifact (must exist)")
    sub.set_defaults(func=_cmd_artifact)


def _cmd_artifact(args) -> int:
    state = commands.record_artifact(args.name, args.path)
    print(f"recorded artifacts.{args.name} = {state.artifacts[args.name]}")
    return 0
```

- [ ] **Step 4: Run the whole suite and lint to verify green**

Run: `uv run pytest -v`
Expected: all pass.

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_artifact.py
git commit -m "feat: supskill-state artifact records stage artifacts (plan-time discovery)"
```

---

### Task 8: `supskill-state gate` (SK-005)

**Files:**
- Modify: `scripts/supskill_state/commands.py` (add `record_gate`)
- Modify: `scripts/supskill_state/cli.py` (register `gate`)
- Test: `tests/test_gate.py`

**Interfaces:**
- Consumes: `GATE_KEYS`, `GATE_DECISIONS` (Task 2); `store.load_state/dump_state/append_jsonl/gates_path/state_path/now_utc_iso/require_aware_utc_iso` (Task 3); `render_show` (Task 6, for the visible-in-show assertion).
- Produces:
  - `commands.record_gate(gate_id: str, decision: str, response: str, root: Path | None = None) -> State` — appends `{gate, decision, response, at}` to `gates.jsonl` **first**, then updates `state.json.gates[GATE_KEYS[gate_id]] = decision` (last-wins)
  - CLI: `supskill-state gate --id G1|G2|G3 --decision approved|rejected --response <verbatim>`

- [ ] **Step 1: Write the failing tests**

`tests/test_gate.py`:

```python
"""SK-005: every gate decision leaves a verbatim, append-only, trail-first audit record."""

import json

import pytest

from supskill_state import commands
from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_gate, render_show
from supskill_state.errors import StateError
from supskill_state.store import (
    gates_path,
    load_state,
    require_aware_utc_iso,
    state_path,
)


def _gate_lines(tmp_path):
    return [
        json.loads(line)
        for line in gates_path(tmp_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_gate_appends_record_and_updates_state(tmp_path):
    init_sprint("s1", root=tmp_path)
    record_gate("G1", "approved", "yes - looks right, go ahead", root=tmp_path)

    lines = _gate_lines(tmp_path)
    assert len(lines) == 1
    record = lines[0]
    assert record["gate"] == "G1"
    assert record["decision"] == "approved"
    assert record["response"] == "yes - looks right, go ahead"
    require_aware_utc_iso(record["at"], "gates.jsonl at")

    assert load_state(state_path(tmp_path)).gates["G1_sprint_doc"] == "approved"


def test_second_decision_on_same_gate_appends_history_and_last_wins(tmp_path):
    init_sprint("s1", root=tmp_path)
    record_gate("G1", "rejected", "no - the scope section is wrong", root=tmp_path)
    record_gate("G1", "approved", "fixed, approved", root=tmp_path)

    lines = _gate_lines(tmp_path)
    assert [(r["gate"], r["decision"]) for r in lines] == [("G1", "rejected"), ("G1", "approved")]
    assert load_state(state_path(tmp_path)).gates["G1_sprint_doc"] == "approved"


def test_write_order_trail_lands_before_state(tmp_path, monkeypatch):
    # fail the SECOND write (state.json): the trail must already be on disk
    init_sprint("s1", root=tmp_path)
    before = state_path(tmp_path).read_bytes()

    def crash(state, path):
        raise RuntimeError("killed between the two writes")

    monkeypatch.setattr(commands.store, "dump_state", crash)
    with pytest.raises(RuntimeError):
        record_gate("G2", "approved", "plan approved", root=tmp_path)

    assert [r["gate"] for r in _gate_lines(tmp_path)] == ["G2"]  # trail ahead of state
    assert state_path(tmp_path).read_bytes() == before  # state untouched


def test_empty_response_is_accepted_recorded_and_visible_in_show(tmp_path):
    # F-4: a fabricated approval must leave a readable (empty) quote, not be rejected
    init_sprint("s1", root=tmp_path)
    record_gate("G1", "approved", "", root=tmp_path)
    assert _gate_lines(tmp_path)[0]["response"] == ""
    assert 'response: ""' in render_show(tmp_path)


def test_unknown_gate_id_and_decision_refused_with_nothing_written(tmp_path):
    init_sprint("s1", root=tmp_path)
    before_state = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match="unknown gate"):
        record_gate("G4", "approved", "x", root=tmp_path)
    with pytest.raises(StateError, match="unknown decision"):
        record_gate("G1", "maybe", "x", root=tmp_path)
    assert _gate_lines(tmp_path) == []
    assert state_path(tmp_path).read_bytes() == before_state


def test_gate_requires_an_initialized_sprint_before_writing_the_trail(tmp_path):
    with pytest.raises(StateError, match="init"):
        record_gate("G1", "approved", "x", root=tmp_path)
    assert not gates_path(tmp_path).exists()


def test_cli_gate(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s1"]) == 0
    assert main(["gate", "--id", "G1", "--decision", "approved", "--response", "approved, go"]) == 0
    assert load_state(state_path(tmp_path)).gates["G1_sprint_doc"] == "approved"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_gate.py -v`
Expected: FAIL — `ImportError: cannot import name 'record_gate'`.

- [ ] **Step 3: Write the implementation**

Append to `scripts/supskill_state/commands.py` (extend the `.model` import list with `GATE_DECISIONS`):

```python
def record_gate(gate_id: str, decision: str, response: str, root: Path | None = None) -> State:
    root = Path(root) if root is not None else Path.cwd()
    if gate_id not in GATE_KEYS:
        raise StateError(f"unknown gate {gate_id!r}; expected one of {sorted(GATE_KEYS)}")
    if decision not in GATE_DECISIONS:
        raise StateError(f"unknown decision {decision!r}; expected one of {list(GATE_DECISIONS)}")
    # load (and thereby validate) state BEFORE writing the trail, so a refusal writes nothing
    state = store.load_state(store.state_path(root))
    record = {
        "gate": gate_id,
        "decision": decision,
        "response": response,  # verbatim; empty is accepted and recorded by design (F-4)
        "at": store.now_utc_iso(),
    }
    store.append_jsonl(store.gates_path(root), record)  # trail FIRST
    state.gates[GATE_KEYS[gate_id]] = decision  # last decision wins in state
    store.dump_state(state, store.state_path(root))  # state SECOND
    return state
```

Modify `scripts/supskill_state/cli.py` — add `_add_gate(subparsers)` after `_add_artifact(subparsers)` inside `build_parser()`, and add:

```python
def _add_gate(subparsers) -> None:
    sub = subparsers.add_parser("gate", help="record a gate decision with the operator's verbatim words")
    sub.add_argument("--id", required=True, choices=["G1", "G2", "G3"], dest="gate_id")
    sub.add_argument("--decision", required=True, choices=["approved", "rejected"])
    sub.add_argument("--response", required=True, help="the operator's verbatim response (may be empty)")
    sub.set_defaults(func=_cmd_gate)


def _cmd_gate(args) -> int:
    commands.record_gate(args.gate_id, args.decision, args.response)
    print(f"recorded {args.gate_id}: {args.decision}")
    return 0
```

- [ ] **Step 4: Run the whole suite and lint to verify green**

Run: `uv run pytest -v`
Expected: all pass.

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_gate.py
git commit -m "feat: supskill-state gate appends audit trail before state (SK-005)"
```

---

### Task 9: `supskill-state block` (SK-006)

**Files:**
- Modify: `scripts/supskill_state/commands.py` (add `record_blocker` and `_OPTION_LABEL`)
- Modify: `scripts/supskill_state/cli.py` (register `block`)
- Test: `tests/test_block.py`

**Interfaces:**
- Consumes: `Blocker`, `Task`, `TaskStatus` (Task 2); `store.load_state/dump_state/append_jsonl/runs_dir/state_path/now_utc_iso/require_aware_utc_iso` (Task 3); `normalize_sprint_id` (Task 4); `init_sprint` (Task 5).
- Produces:
  - `commands.record_blocker(task_id: str, kind: str, found: str, options: list[str], recommend: str, root: Path | None = None) -> State` — one command, three effects: appends `{task, kind, found, options, recommend, at}` to `runs/<normalized-id>/blockers.jsonl` **first**, then mirrors the 5-field record into `state.json.blockers` and flips the task's status to `BLOCKED` (both in one atomic state write)
  - CLI: `supskill-state block --task <id> --kind <k> --found <text> --option "(a) ..." --option "(b) ..." --recommend "(a) - ..."` (`--option` repeats; ≥2 required)
  - Validation (all before any write): `task`/`kind`/`found`/`recommend` non-empty; task id present in `state.tasks`; ≥2 options; every option starts with a distinct label matching `^\([a-z0-9]+\)`; `recommend` starts with one of those labels.

- [ ] **Step 1: Write the failing tests**

`tests/test_block.py`:

```python
"""SK-006: a blocker is a decision, not an acknowledgment - enumerated options required."""

import json

import pytest

from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_blocker
from supskill_state.errors import StateError
from supskill_state.model import Task, TaskStatus
from supskill_state.store import (
    dump_state,
    load_state,
    require_aware_utc_iso,
    runs_dir,
    state_path,
)

# D5's verbatim S9a blocker - the fixture the spec names
S9A = {
    "task": "T3",
    "kind": "needs-live-capture",
    "found": "entity parser returns 0 posts on all 23 profile reads",
    "options": [
        "(a) operator drives a live capture now",
        "(b) defer to next sprint, proceed with the other 4 tasks",
        "(c) re-scope: the drift hypothesis may be wrong",
    ],
    "recommend": "(a) - the drift detector's heuristic may be firing misleadingly",
}


def _init_with_task(tmp_path, task_id="T3"):
    init_sprint("s9a", root=tmp_path)
    state = load_state(state_path(tmp_path))
    state.tasks = [Task(id=task_id, seam="e2e", provable="operator", status=TaskStatus.PENDING)]
    dump_state(state, state_path(tmp_path))


def _blocker_lines(tmp_path):
    path = runs_dir(tmp_path) / "s9a" / "blockers.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_one_command_three_effects_asserted_together(tmp_path):
    _init_with_task(tmp_path)
    record_blocker(S9A["task"], S9A["kind"], S9A["found"], S9A["options"], S9A["recommend"], root=tmp_path)

    # effect 1: append-only audit record in runs/<sprint-id>/blockers.jsonl
    lines = _blocker_lines(tmp_path)
    assert len(lines) == 1
    require_aware_utc_iso(lines[0].pop("at"), "blockers.jsonl at")
    assert lines[0] == S9A  # D5's fixture round-trips verbatim

    state = load_state(state_path(tmp_path))
    # effect 2: mirrored into state.json.blockers
    assert len(state.blockers) == 1
    blocker = state.blockers[0]
    assert (blocker.task, blocker.kind, blocker.found, blocker.options, blocker.recommend) == (
        S9A["task"], S9A["kind"], S9A["found"], S9A["options"], S9A["recommend"],
    )
    # effect 3: the task is now BLOCKED
    assert state.tasks[0].status is TaskStatus.BLOCKED


@pytest.mark.parametrize(
    "override,match",
    [
        ({"task": ""}, "non-empty"),
        ({"kind": ""}, "non-empty"),
        ({"found": ""}, "non-empty"),
        ({"recommend": ""}, "non-empty"),
        ({"options": ["(a) only one option"]}, "at least two"),
        ({"options": []}, "at least two"),
        ({"options": ["no label here", "(b) fine"]}, "label"),
        ({"options": ["(a) first", "(a) duplicate label"]}, "duplicate"),
        ({"recommend": "(z) - references nothing"}, "reference one of the options"),
        ({"recommend": "do option a"}, "reference one of the options"),
    ],
)
def test_invalid_records_are_rejected_with_nothing_written_anywhere(tmp_path, override, match):
    _init_with_task(tmp_path)
    before = state_path(tmp_path).read_bytes()
    record = {**S9A, **override}
    with pytest.raises(StateError, match=match):
        record_blocker(
            record["task"], record["kind"], record["found"], record["options"],
            record["recommend"], root=tmp_path,
        )
    assert _blocker_lines(tmp_path) == []
    assert state_path(tmp_path).read_bytes() == before


def test_unknown_task_refused(tmp_path):
    _init_with_task(tmp_path, task_id="T1")
    with pytest.raises(StateError, match="no task 'T3'"):
        record_blocker(S9A["task"], S9A["kind"], S9A["found"], S9A["options"], S9A["recommend"], root=tmp_path)
    assert _blocker_lines(tmp_path) == []


def test_scope_boundary_block_records_one_blocker_and_parks_nothing(tmp_path):
    # computing the downstream cone to PARK is E5's drain logic, not block's
    _init_with_task(tmp_path)
    state = load_state(state_path(tmp_path))
    state.tasks.append(Task(id="T4", seam="unit", provable="offline", status=TaskStatus.PENDING))
    dump_state(state, state_path(tmp_path))

    record_blocker(S9A["task"], S9A["kind"], S9A["found"], S9A["options"], S9A["recommend"], root=tmp_path)

    state = load_state(state_path(tmp_path))
    downstream = next(task for task in state.tasks if task.id == "T4")
    assert downstream.status is TaskStatus.PENDING  # untouched


def test_cli_block_with_repeated_option_flags(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_with_task(tmp_path)
    assert (
        main(
            [
                "block", "--task", "T3", "--kind", "needs-live-capture",
                "--found", "entity parser returns 0 posts on all 23 profile reads",
                "--option", "(a) operator drives a live capture now",
                "--option", "(b) defer to next sprint, proceed with the other 4 tasks",
                "--recommend", "(a) - the drift detector's heuristic may be firing misleadingly",
            ]
        )
        == 0
    )
    assert load_state(state_path(tmp_path)).tasks[0].status is TaskStatus.BLOCKED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_block.py -v`
Expected: FAIL — `ImportError: cannot import name 'record_blocker'`.

- [ ] **Step 3: Write the implementation**

Append to `scripts/supskill_state/commands.py` (extend the stdlib imports with `import re`, and the `.model` import list with `Blocker` and `TaskStatus` if not already present):

```python
_OPTION_LABEL = re.compile(r"^\(([a-z0-9]+)\)")


def record_blocker(
    task_id: str,
    kind: str,
    found: str,
    options: list[str],
    recommend: str,
    root: Path | None = None,
) -> State:
    root = Path(root) if root is not None else Path.cwd()
    # validate the whole record BEFORE touching disk: a rejected record writes nothing anywhere
    for flag, value in (("--task", task_id), ("--kind", kind), ("--found", found), ("--recommend", recommend)):
        if not value:
            raise StateError(f"a blocker record requires a non-empty {flag}")
    if len(options) < 2:
        raise StateError(
            "a blocker must enumerate at least two --option entries - "
            "a single option is a fait accompli, not a decision"
        )
    labels: list[str] = []
    for option in options:
        match = _OPTION_LABEL.match(option)
        if match is None:
            raise StateError(f"every option must start with a label like '(a) ...': {option!r}")
        if match.group(1) in labels:
            raise StateError(f"duplicate option label ({match.group(1)})")
        labels.append(match.group(1))
    recommend_match = _OPTION_LABEL.match(recommend)
    if recommend_match is None or recommend_match.group(1) not in labels:
        raise StateError(
            "recommend must reference one of the options by its label, e.g. '(a) - because ...'"
        )

    state = store.load_state(store.state_path(root))
    task = next((t for t in state.tasks if t.id == task_id), None)
    if task is None:
        raise StateError(f"no task {task_id!r} in state.json - a blocker must attach to a known task")

    blocker = Blocker(task=task_id, kind=kind, found=found, options=list(options), recommend=recommend)
    blockers_file = store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / "blockers.jsonl"
    store.append_jsonl(  # trail FIRST
        blockers_file,
        {
            "task": blocker.task,
            "kind": blocker.kind,
            "found": blocker.found,
            "options": list(blocker.options),
            "recommend": blocker.recommend,
            "at": store.now_utc_iso(),
        },
    )
    state.blockers.append(blocker)  # mirror into state
    task.status = TaskStatus.BLOCKED  # flip the task
    store.dump_state(state, store.state_path(root))  # one atomic state write, SECOND
    return state
```

Modify `scripts/supskill_state/cli.py` — add `_add_block(subparsers)` after `_add_gate(subparsers)` inside `build_parser()`, and add:

```python
def _add_block(subparsers) -> None:
    sub = subparsers.add_parser("block", help="record a structured blocker and mark its task BLOCKED")
    sub.add_argument("--task", required=True, dest="task_id")
    sub.add_argument("--kind", required=True)
    sub.add_argument("--found", required=True, help="what was actually observed")
    sub.add_argument(
        "--option",
        action="append",
        default=[],
        dest="options",
        help="a labeled alternative like '(a) ...'; repeat the flag (at least twice)",
    )
    sub.add_argument("--recommend", required=True, help="the recommended option, e.g. '(a) - because ...'")
    sub.set_defaults(func=_cmd_block)


def _cmd_block(args) -> int:
    commands.record_blocker(args.task_id, args.kind, args.found, args.options, args.recommend)
    print(f"recorded blocker on {args.task_id}; task is now BLOCKED")
    return 0
```

- [ ] **Step 4: Run the whole suite and lint to verify green**

Run: `uv run pytest -v`
Expected: all pass.

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_block.py
git commit -m "feat: supskill-state block validates and records structured blockers (SK-006)"
```

---

### Task 10: `supskill-state advance` with precondition validation (SK-003 — the single most important story)

**Files:**
- Create: `scripts/supskill_state/transitions.py`
- Modify: `scripts/supskill_state/commands.py` (add `advance_stage`)
- Modify: `scripts/supskill_state/cli.py` (register `advance`)
- Test: `tests/test_advance.py`

**Interfaces:**
- Consumes: `STAGE_ORDER`, `TERMINAL_STATUSES`, `Stage`, `State` (Task 2 — `TERMINAL_STATUSES` is consumed, never redefined); `store.load_state/dump_state/state_path` (Task 3); `init_sprint` (Task 5), `record_artifact` (Task 7), `record_gate` (Task 8) — its tests exercise the real seams, not stubs.
- Produces:
  - `transitions.next_stage(current: Stage) -> Stage | None` — the only legal target, `None` from `REVIEW`
  - `transitions.failed_preconditions(state: State, to: Stage, root: Path) -> list[str]` — pure; empty list means the transition may proceed; each entry names one failed precondition (gate checks listed before artifact checks)
  - `commands.advance_stage(to: str, root: Path | None = None) -> State`
  - CLI: `supskill-state advance --to <STAGE>`

D2's preconditions, verbatim: `PLAN` requires the sprint doc **and** `G1 == approved`; `EXECUTE` requires `G2 == approved` (and `artifacts.dev_plan`); `REVIEW` requires every task terminal. Preconditions attach to *transitions taken*, not stages; `advance` is strictly one-step-forward.

- [ ] **Step 1: Write the failing tests**

`tests/test_advance.py`:

```python
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
    init_sprint("s1", root=tmp_path)
    record_gate("G1", "approved", "approved", root=tmp_path)
    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)
    advance_stage("REFINE", root=tmp_path)
    advance_stage("PLAN", root=tmp_path)

    message = _refused(tmp_path, "EXECUTE", "G2_plan")
    assert "null" in message  # the reason names the failed precondition and its value


# --- one-step-forward only ---


def test_skipping_a_stage_is_impossible_regardless_of_gate_state(tmp_path):
    init_sprint("s1", root=tmp_path)
    # even with every gate approved and artifacts present, SCOPE -> PLAN is not expressible
    record_gate("G1", "approved", "x", root=tmp_path)
    record_gate("G2", "approved", "x", root=tmp_path)
    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)
    record_artifact("dev_plan", _write_doc(tmp_path, "plan.md"), root=tmp_path)
    _refused(tmp_path, "PLAN", "one-step-forward")
    _refused(tmp_path, "EXECUTE", "one-step-forward")
    _refused(tmp_path, "REVIEW", "one-step-forward")


def test_backwards_and_self_transitions_are_not_expressible(tmp_path):
    init_sprint("s1", entry="EXECUTE", root=tmp_path)
    _refused(tmp_path, "SCOPE", "one-step-forward")
    _refused(tmp_path, "EXECUTE", "one-step-forward")


def test_review_is_final_nothing_to_advance_to(tmp_path):
    init_sprint("s1", entry="EXECUTE", root=tmp_path)
    advance_stage("REVIEW", root=tmp_path)  # no tasks -> vacuously terminal
    _refused(tmp_path, "SCOPE", "final stage")


def test_unknown_target_stage_refused(tmp_path):
    init_sprint("s1", root=tmp_path)
    _refused(tmp_path, "SHIP", "unknown stage")


# --- the three preconditions, each way ---


def test_scope_to_refine_needs_no_gate(tmp_path):
    init_sprint("s1", root=tmp_path)
    assert advance_stage("REFINE", root=tmp_path).stage is Stage.REFINE


def test_advance_to_plan_requires_doc_and_g1(tmp_path):
    init_sprint("s1", root=tmp_path)
    advance_stage("REFINE", root=tmp_path)

    message = _refused(tmp_path, "PLAN", "G1_sprint_doc")  # neither: names the gate...
    assert "sprint_doc is not recorded" in message  # ...and the missing artifact

    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)
    _refused(tmp_path, "PLAN", "G1_sprint_doc")  # doc alone is not enough

    record_gate("G1", "approved", "approved", root=tmp_path)
    assert advance_stage("PLAN", root=tmp_path).stage is Stage.PLAN  # both -> proceeds


def test_a_rejected_gate_is_not_approved(tmp_path):
    init_sprint("s1", root=tmp_path)
    advance_stage("REFINE", root=tmp_path)
    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)
    record_gate("G1", "rejected", "no - redo the scope section", root=tmp_path)
    message = _refused(tmp_path, "PLAN", "G1_sprint_doc")
    assert "rejected" in message


def test_advance_to_execute_requires_g2_and_dev_plan(tmp_path):
    init_sprint("s1", entry="PLAN", root=tmp_path)
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
    init_sprint("s1", root=tmp_path)
    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)
    record_artifact("dev_plan", _write_doc(tmp_path, "plan.md"), root=tmp_path)

    _refused(tmp_path, "EXECUTE", "one-step-forward")  # from SCOPE
    advance_stage("REFINE", root=tmp_path)
    _refused(tmp_path, "EXECUTE", "one-step-forward")  # from REFINE
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_advance.py -v`
Expected: collection error — no module `supskill_state.transitions` / no `advance_stage`.

- [ ] **Step 3: Write the transition machine**

`scripts/supskill_state/transitions.py`:

```python
"""Stage transitions and their preconditions (D2).

Preconditions attach to *transitions taken*, not to stages: a sprint that
init's at EXECUTE never crosses the G2 check; a sprint entering at SCOPE
cannot reach EXECUTE without G1 and G2 approved. advance is strictly
one-step-forward; the replan shapes that move backwards are E6's explicit
verbs, never a loosened advance.
"""

from __future__ import annotations

from pathlib import Path

from .model import STAGE_ORDER, TERMINAL_STATUSES, Stage, State


def next_stage(current: Stage) -> Stage | None:
    index = STAGE_ORDER.index(current)
    if index + 1 == len(STAGE_ORDER):
        return None
    return STAGE_ORDER[index + 1]


def failed_preconditions(state: State, to: Stage, root: Path) -> list[str]:
    """Empty list means the transition may proceed. Gate failures are listed first."""
    failures: list[str] = []
    if to is Stage.PLAN:
        _check_gate(state, "G1_sprint_doc", failures)
        _check_artifact(state, "sprint_doc", root, failures)
    elif to is Stage.EXECUTE:
        _check_gate(state, "G2_plan", failures)
        _check_artifact(state, "dev_plan", root, failures)
    elif to is Stage.REVIEW:
        open_tasks = [task.id for task in state.tasks if task.status not in TERMINAL_STATUSES]
        if open_tasks:
            failures.append(
                "every task must be terminal (DONE|DONE_WITH_CONCERNS|BLOCKED|PARKED); "
                "still open: " + ", ".join(open_tasks)
            )
    return failures


def _check_gate(state: State, key: str, failures: list[str]) -> None:
    value = state.gates[key]
    if value != "approved":
        shown = value if value is not None else "null"
        failures.append(f"{key} must be approved (currently {shown})")


def _check_artifact(state: State, key: str, root: Path, failures: list[str]) -> None:
    value = state.artifacts[key]
    if not value:
        failures.append(f"artifacts.{key} is not recorded")
    elif not (root / value).exists():
        failures.append(f"artifacts.{key} points at a missing file: {value}")
```

Append to `scripts/supskill_state/commands.py` (extend its imports: add `from .transitions import failed_preconditions, next_stage`):

```python
def advance_stage(to: str, root: Path | None = None) -> State:
    root = Path(root) if root is not None else Path.cwd()
    try:
        target = Stage(to)
    except ValueError:
        raise StateError(
            f"unknown stage {to!r}; expected one of {[s.value for s in Stage]}"
        ) from None
    state = store.load_state(store.state_path(root))
    expected = next_stage(state.stage)
    if expected is None:
        raise StateError(f"{state.stage.value} is the final stage; there is nothing to advance to")
    if target is not expected:
        raise StateError(
            f"advance is one-step-forward only: from {state.stage.value} the only legal "
            f"target is {expected.value}; --to {target.value} refused"
        )
    failures = failed_preconditions(state, target, root)
    if failures:
        raise StateError(f"cannot advance to {target.value}: " + "; ".join(failures))
    state.stage = target
    store.dump_state(state, store.state_path(root))
    return state
```

Modify `scripts/supskill_state/cli.py` — add `_add_advance(subparsers)` after `_add_block(subparsers)` inside `build_parser()`, and add:

```python
def _add_advance(subparsers) -> None:
    sub = subparsers.add_parser("advance", help="advance one stage forward, if preconditions hold")
    sub.add_argument("--to", required=True, dest="to", metavar="STAGE",
                     help="target stage (must be the next stage in SCOPE-REFINE-PLAN-EXECUTE-REVIEW)")
    sub.set_defaults(func=_cmd_advance)


def _cmd_advance(args) -> int:
    state = commands.advance_stage(args.to)
    print(f"advanced to {state.stage.value}")
    return 0
```

(`--to` deliberately has no `choices=` — unknown stages flow through `advance_stage` so the refusal is a named StateError, byte-identical state, exit 1, matching every other refusal path.)

- [ ] **Step 4: Run the whole suite and lint to verify green**

Run: `uv run pytest -v`
Expected: all pass — including `test_advance_to_execute_with_g2_null_refuses`, the design's own named test.

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add scripts/supskill_state/transitions.py scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_advance.py
git commit -m "feat: advance with transition-attached preconditions (SK-003)"
```

---

### Task 11: The north-star demo, end to end

**Files:**
- Test: `tests/test_demo.py`

**Interfaces:**
- Consumes: the full CLI (`supskill_state.cli.main`) — every verb from Tasks 5–10; `store.state_path/gates_path`; `load_state`.
- Produces: nothing new — this is the sprint's exit-criteria demo as a permanent regression test.

The sprint demo, verbatim from the exit criteria: `init s1` → gate G1 approved with the operator's actual words → `advance --to PLAN` succeeds → `advance --to EXECUTE` **refuses, loudly, naming G2** → `gates.jsonl` shows the whole story in order → kill mid-write, resume from a valid `state.json`.

- [ ] **Step 1: Write the test (it should pass immediately — this is integration, everything exists)**

`tests/test_demo.py`:

```python
"""The sprint demo - the north star in miniature, as one end-to-end CLI test."""

import json
import re
from pathlib import Path

import supskill_state
from supskill_state.cli import main
from supskill_state.model import Stage
from supskill_state.store import gates_path, load_state, state_path


def test_north_star_demo(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    # init s1
    assert main(["init", "s1"]) == 0

    # the REFINE stage happens (no gate guards SCOPE -> REFINE)
    assert main(["advance", "--to", "REFINE"]) == 0

    # REFINE produced the sprint doc; record it
    (tmp_path / "sprint-doc.md").write_text("# refined sprint doc\n")
    assert main(["artifact", "--set", "sprint_doc", "--path", "sprint-doc.md"]) == 0

    # gate G1: the operator's actual words
    assert main(["gate", "--id", "G1", "--decision", "approved",
                 "--response", "read it - scope grew but it is right. approved."]) == 0

    # advance --to PLAN succeeds
    assert main(["advance", "--to", "PLAN"]) == 0

    # advance --to EXECUTE refuses, loudly, naming G2 - and changes nothing
    before = state_path(tmp_path).read_bytes()
    assert main(["advance", "--to", "EXECUTE"]) == 1
    error = capsys.readouterr().err
    assert "refused" in error and "G2_plan" in error
    assert state_path(tmp_path).read_bytes() == before

    # gates.jsonl shows the whole story in order
    records = [json.loads(line) for line in gates_path(tmp_path).read_text().splitlines()]
    assert [(r["gate"], r["decision"]) for r in records] == [("G1", "approved")]
    assert records[0]["response"] == "read it - scope grew but it is right. approved."

    # kill the process mid-write, then resume from a valid state.json
    (state_path(tmp_path).parent / "state.json.tmp-killed").write_text('{"schema": 1, "back')
    state = load_state(state_path(tmp_path))
    assert state.stage is Stage.PLAN  # the previous valid state, never a truncated one
    assert main(["show"]) == 0
    assert "stage PLAN" in capsys.readouterr().out


def test_no_module_outside_store_opens_files_for_writing():
    # invariant 3, mechanically: store.py is the only module with file-write
    # primitives; every other module goes through store.dump_state/append_jsonl.
    # The authoritative check is the reviewer reading every write site - this
    # test guards the obvious regression.
    package_dir = Path(supskill_state.__file__).parent
    write_call = re.compile(r"""open\([^)]*["'][wax]|\.write_text\(|\.write_bytes\(""")
    offenders = [
        source.name
        for source in package_dir.glob("*.py")
        if source.name != "store.py" and write_call.search(source.read_text(encoding="utf-8"))
    ]
    assert offenders == []
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/test_demo.py -v`
Expected: PASS (both tests). If the demo test fails, a previous task is wrong — fix it there, not here.

- [ ] **Step 3: Exit-criteria sweep (whole suite, lint, speed)**

Run: `time uv run pytest`
Expected: **every test passes, total runtime in seconds** (the spec's bar: seconds, not minutes; expect well under 5s).

Run: `uv run ruff check .`
Expected: `All checks passed!`

Run: `grep -rn "dump_state\|append_jsonl\|write_text\|open(" scripts/supskill_state/ | grep -v store.py | grep -v "\.pyc"`
Expected: hits are only *calls into* `store.dump_state`/`store.append_jsonl` from `commands.py` — no direct file-write primitives outside `store.py` (invariant 3 evidence for the reviewer).

- [ ] **Step 4: Commit**

```bash
git add tests/test_demo.py
git commit -m "test: north-star demo - gate skipping fails loudly end to end"
```

---

## Backlog deltas to propose at review (do not apply silently)

On top of the six deltas the sprint doc already queues for `backlog.md`, this plan adds:

1. **`artifact` verb added to `supskill-state`** (~1 pt of the sprint's 7-pt headroom, Decision 4): D2's command list `init | advance | gate | block | show` becomes `init | show | artifact | advance | gate | block`. Rationale: invariant 3 makes the script the only writer of `state.json`, so the artifacts that `advance`'s own preconditions check must have a CLI seam; without it the sprint demo cannot run and E3/E4 have no way to record their outputs.
2. **SK-002 note**: `runs/` directories and archives use the normalized sprint id; `init --archive` moves `state.json` *and* `gates.jsonl` into `runs/<old-id>/archive-<n>/` (numbered, never clobbered).
3. **SK-006 note**: "recommend references an option" is implemented as labeled options — every option starts with a distinct `(x)` label and `recommend` starts with one of them (the exact shape of D5's fixture). E5's mapping must emit labeled options.

## Verification against the sprint's exit criteria

| Exit criterion | Where it is proven |
|---|---|
| SK-007 scaffold: pytest+ruff green offline, importable package, stdlib-only, plugin-root-compatible layout | Task 1 (`test_scaffold.py`, `dependencies = []` test) |
| SK-001: D2 round-trip field-by-field; unknown schema refused; exact status enum + exported terminal set + `NEEDS_CONTEXT` rejected; atomic write; aware-UTC everywhere | Tasks 2–3 (`test_model.py`, `test_store.py`) |
| SK-002: init refuses to clobber / archives explicitly; `--entry` honored for all three; `show` readable with sane no-state failure | Tasks 5–6 (`test_init.py`, `test_show.py`) |
| SK-003: three preconditions refuse with named reason + byte-identical state; one-step-forward only; entry-aware both ways; **`advance --to EXECUTE` with `G2 == null` → refused** | Task 10 (`test_advance.py`) |
| SK-004: scratch derived at init, no override exists; loud normalization; S9a ≠ S9 + distinct-ids ⇒ distinct-paths property | Task 4 (`test_scratch.py`), Task 5 (init wiring) |
| SK-005: append to `gates.jsonl`, history preserved, last-wins; trail-before-state asserted by failing the second write; empty response accepted & visible | Task 8 (`test_gate.py`) |
| SK-006: rejected per missing field with nothing written; ≥2 options; recommend references an option; three effects as one command; S9a fixture round-trips | Task 9 (`test_block.py`) |
| Reviewer confirms invariant 3 | Task 11 step 3 grep + the standing review pass |
| Full suite offline & fast; ruff green | every task's step 4; Task 11 step 3 |
| The sprint demo | Task 11 (`test_demo.py`) |
