# Sprint 04 — PLAN + Gate 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> Execution mode for this sprint is already decided: **subagent-driven**, fresh subagent per task, review between tasks.

**Goal:** The conductor turns a G1-approved sprint doc into a dev plan that `superpowers:writing-plans` actually produced, refuses to let that plan agent execute anything, records the operator's verbatim Gate 2 decision, and loads `tasks[]` so `advance --to EXECUTE` becomes reachable for the first time.

**Architecture:** Same split as always (D2): the `supskill-state` CLI is the only mutator. It gains one loading verb (`tasks --from <doc> [--plan <plan>]`, built on the existing `proofs.py` parser — never a second parser), one non-mutating guard verb (`plan-guard --before --after`), and two preconditions that turn an empty `tasks[]` from a vacuous pass into a refusal. Two new pure-Python modules (`plan_coverage.py` — the plan-task ↔ story join; `plan_guard.py` — the HEAD-moved predicate) are the offline floor. SKILL.md replaces its PLAN stub with real dispatch choreography built on a third prompt template, and copies Gate 1's section into Gate 2 deliberately. The plan agent produces a document; the conductor alone records it, and a HEAD that moved across the dispatch stops the run.

**Tech Stack:** Python ≥3.11 stdlib only (zero runtime deps), pytest + ruff + pyyaml as dev deps, managed with `uv`. Claude Code plugin layout unchanged.

## Global Constraints

Copied from the sprint spec (`docs/plans/sprints/backlog-01/sprint-04-plan-gate2.md`) and the standing project rules. Every task's requirements implicitly include this section.

- **Tests:** `uv run pytest`. The suite is **pure offline** — no LLM call, no subagent, no network, anywhere under `tests/`. Baseline at commit `133da28`: **159 passed in ~0.4s**. Every task ends with the full suite green.
- **Lint:** `uv run ruff check` must stay clean. Config is `pyproject.toml:22-32` — `line-length = 120`, rules `E,F,I,B,UP`, `src = ["scripts", "tests"]`. Prior sprints tripped over verbatim plan code that ruff rejected (UP042 on `class X(str, Enum)`, UP017, E501, F401). Every code block in this plan has been written to pass those rules as-is: `from __future__ import annotations` at the top of each new module, no unused imports, no line over 120 chars.
- **Zero runtime dependencies:** `pyproject.toml` `[project] dependencies = []`, enforced by `tests/test_scaffold.py`. New packages go in `[dependency-groups] dev` only. Nothing this sprint needs a dependency.
- **No AI attribution of any kind in commit messages or bodies** — no `Co-Authored-By`, no "Generated with" line, no mention of Claude/Anthropic/AI. This is absolute and overrides any harness default.
- **Invariant 3 — no dispatched agent runs `supskill-state` or touches `.supskill/`.** Stage agents produce documents; the conductor alone records them. `skills/supskill/references/plan-prompt.md` states this verbatim, and `tests/test_prompt_templates.py:26-30` (the standing tripwire) grows to cover it. **New this sprint, and standing from now on:** no template may instruct its agent to invoke `superpowers:subagent-driven-development` or `superpowers:executing-plans` — a second assertion beside the first.
- **Invariant 2 / D4 in every template:** dispatched agents can never ask anyone anything (`AskUserQuestion` is stripped from subagents and auto-resolves empty in ~37ms headless — contexts/01 §6). Every template states this verbatim and gives the agent its full input up front.
- **Invariant 5 — the conductor is disposable.** Everything it knows comes from `show --json`. Resume idempotence at PLAN is part of this task's acceptance, not a nicety.
- **Silence is not consent at Gate 2.** No `--yes`, no auto-approve affordance anywhere. An empty or auto-resolved `AskUserQuestion` answer means: no `gate` call, report, stop. The CLI keeps recording empty responses by design (`commands.py:203`) — the refusal lives in the conductor prose only.
- **The proof grammar has a single authority:** `scripts/supskill_state/proofs.py`. `parse_proof_lines` (`proofs.py:50`) is the only thing that reads a proof line. SK-033 adds the verb on top of it and **never a second parser**.
- **The state CLI is always invoked as `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state`, from the target repo's root.** The audit script follows the identical convention: `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-audit`.
- **The conductor never passes `--archive`** — it may only name it in a refusal and stop.
- **The plugin must keep passing `claude plugin validate --strict`** (and `tests/test_plugin_manifest.py` / `tests/test_skill_frontmatter.py`): the frontmatter of `skills/supskill/SKILL.md` is untouched this sprint, the body stays ≤500 lines (it is 186 today and lands near 250), and reference files stay one hop from SKILL.md.
- **EXECUTE stays E5's honest stub.** When G2 approves, advance and land on the stub, which reports and stops. Do not wire SDD (SK-040 is E5's).
- **Commits:** one per task minimum, TDD evidence first (a failing test run before implementation).
- **Commands:** tests `uv run pytest <path> -v`, lint `uv run ruff check`.

## File Structure

| Path | Task | Responsibility |
|---|---|---|
| `scripts/supskill_state/commands.py` | 1, 2 (modify) | `load_tasks` — the `tasks` verb's logic |
| `scripts/supskill_state/plan_coverage.py` | 2 (create) | The plan-task ↔ story join: heading grammar + coverage validator |
| `scripts/supskill_state/transitions.py` | 3 (modify) | `failed_preconditions` refuses an empty `tasks[]` on `→ EXECUTE` and `→ REVIEW` |
| `scripts/supskill_state/plan_guard.py` | 4 (create) | `head_moved` predicate + the refusal text (SK-031 layer 2) |
| `scripts/supskill_state/cli.py` | 1, 2, 4 (modify) | `tasks` and `plan-guard` subcommands |
| `skills/supskill/references/plan-prompt.md` | 5 (create) | PLAN dispatch template; pre-answers the Execution Handoff |
| `skills/supskill/SKILL.md` | 6, 7 (modify) | PLAN row + `## The PLAN stage` + `## Gate 2` — frontmatter untouched |
| `tests/test_tasks.py` | 1 (create), 2 (extend) | The verb, offline; dogfoods this sprint's own doc |
| `tests/test_plan_coverage.py` | 2 (create) | Coverage validator, both directions |
| `tests/test_advance.py` | 3 (modify) | The two new preconditions + the call sites they invalidate |
| `tests/test_plan_guard.py` | 4 (create) | The HEAD-moved predicate + the `plan-guard` verb's exit codes |
| `tests/test_prompt_templates.py` | 5 (extend) | PLAN template exists, states D4 + invariant 3 + the execution-sub-skill ban |
| `docs/plans/sprints/backlog-01/sprint-04-plan-gate2.md` | 1 (commit as-is) | Committed untouched — it is the dogfood fixture for Task 1 |
| `.superpowers/sdd/s4/demo-checklist.md` | 8 (create, gitignored) | Operator-run demo — the sprint's exit criterion |
| `docs/plans/sprints/backlog-01/backlog.md` | 9 (modify) | The six S4 DoR backlog deltas |

**Task order (honors the sprint doc's "Capacity & sequencing"):** 1 → 2 → 3 sequential (all three are SK-033 and each builds on the last; 2 and 3 both touch code 1 creates). 4 is independent pure Python — wave A alongside 1–3. 5 needs 4 (it forbids what 4 catches) and 1–2 (it states the heading rule 2 enforces). 6 needs 1, 2, 4, 5. 7 needs 6. 8 needs 7. 9 is docs-only and independent.

---

### Task 1: `tasks --from <doc>` loads story-shaped tasks (SK-033)

**Files:**
- Modify: `scripts/supskill_state/commands.py` (new `load_tasks`, appended after `record_blocker`)
- Modify: `scripts/supskill_state/cli.py:26` (register the subparser) and a new `_add_tasks` / `_cmd_tasks` pair
- Test: `tests/test_tasks.py` (create)
- Commit (as-is, it is the fixture): `docs/plans/sprints/backlog-01/sprint-04-plan-gate2.md`

**Interfaces:**
- Consumes: `parse_proof_lines` and `ProofLine` (`proofs.py:50`, `proofs.py:43`) — the single vocabulary authority; `store.load_state` / `store.dump_state`; `Task` (`model.py:76-80`) and `TaskStatus` (`model.py:45-50`); `StateError`.
- Produces (Task 2 extends this exact signature with `plan`, Task 3's preconditions consume its output, E5 drains it):
  - `load_tasks(doc: str, *, plan: str | None = None, root: Path | None = None) -> State` — writes `state.tasks` as one `Task(id=<SK-0xx>, seam, provable, status=PENDING)` per proof line, **in document order**. `plan` is unused in this task (Task 2 wires it); declare it now so the CLI and the signature do not churn.
  - CLI: `supskill-state tasks --from <doc> [--plan <plan>]` — exit 0 prints `loaded N tasks: SK-030, SK-031, ...`; exit 1 on any refusal.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tasks.py`:

```python
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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_tasks.py -v`
Expected: FAIL — `ImportError: cannot import name 'load_tasks' from 'supskill_state.commands'`.

- [ ] **Step 3: Implement the verb**

In `scripts/supskill_state/commands.py`, extend the `.model` import block with `Task` and add `parse_proof_lines` to the imports:

```python
from .model import (
    ARTIFACT_KEYS,
    ENTRY_STAGES,
    GATE_DECISIONS,
    GATE_KEYS,
    Blocker,
    SprintInfo,
    Stage,
    State,
    Task,
    TaskStatus,
    state_to_dict,
)
from .proofs import parse_proof_lines
from .scratch import derive_scratch, normalize_sprint_id
from .transitions import failed_preconditions, next_stage
```

(`Task` slots in alphabetically between `Stage`/`State` and `TaskStatus` — ruff's `I` rule sorts the names; keep the block exactly as shown.)

Append after `record_blocker` (before `advance_stage`):

```python
def load_tasks(
    doc: str,
    *,
    plan: str | None = None,
    root: Path | None = None,
) -> State:
    """Load tasks[] from a sprint doc's proof lines (SK-033).

    proofs.py is the single vocabulary owner: this verb parses NOTHING itself.
    Tasks are story-shaped (SK-0xx), which is why a dev plan's task headings must
    name the story they serve - that heading is the only join between what SDD
    reports (Task N) and what state tracks (SK-0xx).

    Non-destructive: a reload that would reset progress refuses instead. The
    operator who really wants a fresh load has `init --archive`; this verb never
    runs it.
    """
    root = Path(root) if root is not None else Path.cwd()
    doc_path = root / doc
    if not doc_path.is_file():
        raise StateError(f"no such doc: {doc}")
    proofs = parse_proof_lines(doc_path.read_text(encoding="utf-8"))
    if not proofs:
        raise StateError(
            f"no proof lines in {doc}: there is nothing to load "
            "(a refined sprint doc carries one proof line per story)"
        )

    state = store.load_state(store.state_path(root))
    started = [task.id for task in state.tasks if task.status is not TaskStatus.PENDING]
    if started:
        raise StateError(
            "tasks[] already carries progress (" + ", ".join(started) + "); refusing to reset it. "
            "A fresh load is an operator decision: archive the run with init --archive"
        )

    state.tasks = [
        Task(id=proof.story, seam=proof.seam, provable=proof.provable, status=TaskStatus.PENDING)
        for proof in proofs
    ]
    store.dump_state(state, store.state_path(root))
    return state
```

In `scripts/supskill_state/cli.py`, register the subparser in `build_parser` (after `_add_block(subparsers)`):

```python
    _add_block(subparsers)
    _add_tasks(subparsers)
    _add_advance(subparsers)
```

and add the pair (before `_add_advance`):

```python
def _add_tasks(subparsers) -> None:
    sub = subparsers.add_parser("tasks", help="load tasks[] from a refined sprint doc's proof lines")
    sub.add_argument("--from", required=True, dest="doc", metavar="DOC",
                     help="the refined sprint doc; its proof lines are the task list")
    sub.add_argument("--plan", help="the dev plan; every story must be named by a '### Task N ... (SK-0xx)' heading")
    sub.set_defaults(func=_cmd_tasks)


def _cmd_tasks(args) -> int:
    state = commands.load_tasks(args.doc, plan=args.plan)
    print(f"loaded {len(state.tasks)} tasks: " + ", ".join(task.id for task in state.tasks))
    return 0
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_tasks.py -v && uv run pytest && uv run ruff check`
Expected: all PASS — 159 + the new tests. In particular `test_demo.py::test_no_module_outside_store_opens_files_for_writing` stays green (`load_tasks` writes only through `store.dump_state`).

- [ ] **Step 5: Commit (including the sprint doc — it is the fixture)**

The sprint spec is currently untracked; the dogfood test makes it load-bearing for CI. Commit it byte-for-byte as it stands (do not edit it):

```bash
git add scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_tasks.py \
        docs/plans/sprints/backlog-01/sprint-04-plan-gate2.md
git commit -m "feat: supskill-state tasks --from loads story-shaped tasks[] from proof lines (SK-033)"
```

---

### Task 2: Load-time plan coverage — `--plan` refuses a plan that drops a story (SK-033)

**Files:**
- Create: `scripts/supskill_state/plan_coverage.py`
- Modify: `scripts/supskill_state/commands.py` (`load_tasks` wires the `plan` argument it already declares)
- Test: `tests/test_plan_coverage.py` (create), `tests/test_tasks.py` (extend)

**Interfaces:**
- Consumes: `load_tasks`'s `plan` parameter from Task 1; the story ids returned by `parse_proof_lines`.
- Produces:
  - `PROCESS_MARKER: str` = `"(process)"` — the literal a plan task uses when it serves no backlog story
  - `plan_task_headings(text: str) -> list[str]` — every `### Task N…` heading line, in order
  - `validate_plan_coverage(plan_text: str, story_ids: list[str]) -> list[str]` — one message per violation; empty list means the join is clean
  - `load_tasks(..., plan=...)` raises `StateError` listing every violation, **before** writing anything

**Why this exists** (state it in the module docstring): `tasks[]` is story-shaped (`SK-0xx`); SDD reports per plan task (`Task N`). Nothing joins them, so E5's `SK-043` mapping would have had nothing to map through. The heading is the join key. Caught here it costs a validator; caught at E5 it would have been a re-plan.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plan_coverage.py`:

```python
"""SK-033: the plan-task <-> story join key, validated at load time.

Every story in tasks[] must be named by at least one '### Task N: ... (SK-0xx)'
heading; every plan task heading must name a known story or the literal (process).
"""

from supskill_state.plan_coverage import PROCESS_MARKER, plan_task_headings, validate_plan_coverage

STORIES = ["SK-030", "SK-031"]

PLAN = """# A plan

### Task 1: the verb (SK-030)

prose

### Task 2: the guard (SK-031)

### Task 3: the demo checklist (process)
"""


def test_a_clean_plan_reports_no_violations():
    assert validate_plan_coverage(PLAN, STORIES) == []


def test_headings_are_extracted_in_document_order():
    assert [h.split(":")[0] for h in plan_task_headings(PLAN)] == ["### Task 1", "### Task 2", "### Task 3"]


def test_a_plan_that_drops_a_story_is_refused_naming_the_story():
    failures = validate_plan_coverage(PLAN.replace("### Task 2: the guard (SK-031)", "### Task 2: x (SK-030)"), STORIES)
    assert len(failures) == 1 and "SK-031" in failures[0] and "drops" in failures[0]


def test_a_heading_naming_no_story_and_not_marked_process_is_refused():
    failures = validate_plan_coverage(PLAN + "\n### Task 4: mystery work\n", STORIES)
    assert len(failures) == 1 and PROCESS_MARKER in failures[0]


def test_a_heading_naming_an_unknown_story_is_refused():
    failures = validate_plan_coverage(PLAN + "\n### Task 4: from another sprint (SK-099)\n", STORIES)
    assert len(failures) == 1 and "SK-099" in failures[0] and "unknown" in failures[0]


def test_one_heading_may_serve_two_stories():
    plan = "### Task 1: the template (SK-030, SK-031)\n"
    assert validate_plan_coverage(plan, STORIES) == []


def test_a_plan_with_no_task_headings_at_all_is_refused():
    failures = validate_plan_coverage("# a plan with prose only\n", STORIES)
    assert len(failures) == 1 and "no `### Task N" in failures[0]


def test_every_violation_is_reported_at_once():
    failures = validate_plan_coverage("### Task 1: mystery\n### Task 2: ghost (SK-099)\n", STORIES)
    assert len(failures) == 4  # unmarked heading, unknown story, and both stories dropped
```

Append to `tests/test_tasks.py`:

```python
def test_a_plan_that_covers_every_story_loads(tmp_path):
    doc = _sprint(tmp_path)
    (tmp_path / "plan.md").write_text(
        "### Task 1: a (SK-001)\n### Task 2: b (SK-002)\n### Task 3: the deltas (process)\n",
        encoding="utf-8",
    )
    state = load_tasks(doc, plan="plan.md", root=tmp_path)
    assert [t.id for t in state.tasks] == ["SK-001", "SK-002"]


def test_a_plan_that_drops_a_story_refuses_before_tasks_are_written(tmp_path):
    doc = _sprint(tmp_path)
    (tmp_path / "plan.md").write_text("### Task 1: a (SK-001)\n", encoding="utf-8")
    with pytest.raises(StateError, match="SK-002"):
        load_tasks(doc, plan="plan.md", root=tmp_path)
    assert load_state(state_path(tmp_path)).tasks == []  # the operator never gates a plan with a hole


def test_a_missing_plan_refuses(tmp_path):
    doc = _sprint(tmp_path)
    with pytest.raises(StateError, match="no such plan"):
        load_tasks(doc, plan="ghost.md", root=tmp_path)


def test_cli_tasks_with_plan_refuses_and_lists_every_violation(tmp_path, monkeypatch, capsys):
    doc = _sprint(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "plan.md").write_text("### Task 1: mystery\n", encoding="utf-8")
    assert main(["tasks", "--from", doc, "--plan", "plan.md"]) == 1
    err = capsys.readouterr().err
    assert "SK-001" in err and "SK-002" in err and "(process)" in err
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_plan_coverage.py tests/test_tasks.py -v`
Expected: `tests/test_plan_coverage.py` FAILs with `ModuleNotFoundError: No module named 'supskill_state.plan_coverage'`; the four new `test_tasks.py` tests FAIL (`load_tasks` ignores `plan` today).

- [ ] **Step 3: Implement the validator**

Create `scripts/supskill_state/plan_coverage.py`:

```python
"""The plan-task <-> story join key (SK-033, S4 DoR finding 3).

tasks[] is story-shaped (SK-0xx): parse_proof_lines keys on the story id and
Task stores id/seam/provable. SDD reports per PLAN TASK ("Task 3 DONE"). Nothing
joins the two vocabularies, so E5's status mapping would have had nothing to map
through - unless every plan task heading names the story it serves:

    ### Task N: <what> (SK-0xx)          # serves a backlog story
    ### Task N: <what> (process)         # serves none (the demo checklist, the backlog deltas)

This module enforces exactly that, in both directions, and nothing else. Whether
a plan task actually IMPLEMENTS the story it names is judgment - the reviewer's
and the operator's at Gate 2 - and this validator does not pretend otherwise
(F-4's shape: loud and auditable, not impossible).
"""

from __future__ import annotations

import re

PROCESS_MARKER = "(process)"

_TASK_HEADING = re.compile(r"^###\s+Task\s+\d+\b.*$")
_STORY_ID = re.compile(r"SK-\d+")


def plan_task_headings(text: str) -> list[str]:
    """Every '### Task N ...' heading line, in document order."""
    return [line.rstrip() for line in text.splitlines() if _TASK_HEADING.match(line)]


def validate_plan_coverage(plan_text: str, story_ids: list[str]) -> list[str]:
    """One message per violation; an empty list means the join is clean both ways."""
    headings = plan_task_headings(plan_text)
    if not headings:
        return [
            "the plan has no `### Task N: ...` headings - there is nothing to join the stories through"
        ]

    known = set(story_ids)
    named: set[str] = set()
    failures: list[str] = []
    for heading in headings:
        found = _STORY_ID.findall(heading)
        if not found:
            if PROCESS_MARKER not in heading:
                failures.append(
                    f"plan task names no story and is not marked {PROCESS_MARKER}: {heading}"
                )
            continue
        for story in found:
            if story in known:
                named.add(story)
            else:
                failures.append(f"plan task names an unknown story {story}: {heading}")

    for story in story_ids:
        if story not in named:
            failures.append(f"{story}: no plan task heading names it - the plan drops this story")
    return failures
```

- [ ] **Step 4: Wire it into `load_tasks`**

In `scripts/supskill_state/commands.py`, add the import beside `parse_proof_lines`:

```python
from .plan_coverage import validate_plan_coverage
from .proofs import parse_proof_lines
```

and, inside `load_tasks`, insert the coverage block between the progress guard and the `state.tasks = [...]` write:

```python
    if plan is not None:
        plan_path = root / plan
        if not plan_path.is_file():
            raise StateError(f"no such plan: {plan}")
        failures = validate_plan_coverage(
            plan_path.read_text(encoding="utf-8"), [proof.story for proof in proofs]
        )
        if failures:
            raise StateError(
                f"the dev plan does not cover the sprint doc's stories: {'; '.join(failures)}"
            )
```

Everything before the `store.dump_state` call is validation, so a refusal writes nothing — that is why the coverage check sits above the write and not below it.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_plan_coverage.py tests/test_tasks.py -v && uv run pytest && uv run ruff check`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/supskill_state/plan_coverage.py scripts/supskill_state/commands.py \
        tests/test_plan_coverage.py tests/test_tasks.py
git commit -m "feat: load-time plan coverage - a plan that drops a story refuses before Gate 2 (SK-033)"
```

---

### Task 3: An empty `tasks[]` refuses on `→ EXECUTE` and `→ REVIEW` (SK-033)

**Files:**
- Modify: `scripts/supskill_state/transitions.py:24-42` (`failed_preconditions`)
- Test: `tests/test_advance.py` (two new tests; three existing call sites the precondition invalidates)

**Interfaces:**
- Consumes: `failed_preconditions(state, to, root)` and its `_check_gate` / `_check_artifact` helpers (`transitions.py:45-57`) as they exist today.
- Produces: a `_check_tasks_loaded(state, failures)` helper called from **both** the EXECUTE and the REVIEW branch. Failure string: `tasks[] is empty: ...`. The existing non-terminal check on `→ REVIEW` (`transitions.py:36-41`) is unchanged — this adds the case it never covered.

**The defect being closed** (S4 DoR finding 2): `failed_preconditions` refuses `→ REVIEW` while any task is non-terminal. Over an **empty** list nothing is non-terminal, so the check passes vacuously — and `init` always writes `tasks=[]` (`commands.py:77`). Today a sprint can reach REVIEW having executed nothing while the spine's strongest precondition raises no objection. An `entry: EXECUTE` sprint never crosses `→ EXECUTE`, so the REVIEW guard is the one that covers it — hence both guards, and an EXECUTE-entry fixture, not only a SCOPE-entry one.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_advance.py`:

```python
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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_advance.py -v -k empty_task_list`
Expected: both FAIL — `advance_stage` succeeds where `_refused` expects a `StateError` (today an empty `tasks[]` passes both transitions).

- [ ] **Step 3: Implement the two preconditions**

In `scripts/supskill_state/transitions.py`, `failed_preconditions` becomes:

```python
def failed_preconditions(state: State, to: Stage, root: Path) -> list[str]:
    """Empty list means the transition may proceed. Gate failures are listed first."""
    failures: list[str] = []
    if to is Stage.REFINE:
        _check_artifact(state, "sprint_doc", root, failures)
    elif to is Stage.PLAN:
        _check_gate(state, "G1_sprint_doc", failures)
        _check_artifact(state, "sprint_doc", root, failures)
    elif to is Stage.EXECUTE:
        _check_gate(state, "G2_plan", failures)
        _check_artifact(state, "dev_plan", root, failures)
        _check_tasks_loaded(state, failures)
    elif to is Stage.REVIEW:
        _check_tasks_loaded(state, failures)
        open_tasks = [task.id for task in state.tasks if task.status not in TERMINAL_STATUSES]
        if open_tasks:
            failures.append(
                "every task must be terminal (DONE|DONE_WITH_CONCERNS|BLOCKED|PARKED); "
                "still open: " + ", ".join(open_tasks)
            )
    return failures
```

and gains a third helper beside `_check_gate` / `_check_artifact`:

```python
def _check_tasks_loaded(state: State, failures: list[str]) -> None:
    """An empty tasks[] made the non-terminal check pass vacuously (S4 DoR finding 2)."""
    if not state.tasks:
        failures.append(
            "tasks[] is empty: a sprint with no tasks has nothing to execute and nothing to "
            "review; run `supskill-state tasks --from <sprint doc>` first"
        )
```

Also extend the module docstring's second paragraph with one sentence:

```python
"""Stage transitions and their preconditions (D2).

Preconditions attach to *transitions taken*, not to stages: a sprint that
init's at EXECUTE never crosses the G2 check; a sprint entering at SCOPE
cannot reach EXECUTE without G1 and G2 approved. advance is strictly
one-step-forward; the replan shapes that move backwards are E6's explicit
verbs, never a loosened advance.

An empty tasks[] is refused on BOTH -> EXECUTE and -> REVIEW: an entry=EXECUTE
sprint never crosses the first, so the second is the one that covers it.
"""
```

- [ ] **Step 4: Fix the three call sites the precondition invalidates**

Three existing tests in `tests/test_advance.py` advance past a guard with an empty `tasks[]` and must now load tasks first (line numbers as of commit `133da28`):

- `test_review_is_final_nothing_to_advance_to` (`tests/test_advance.py:76-79`): the comment `# no tasks -> vacuously terminal` is now a lie. Replace the body:

```python
def test_review_is_final_nothing_to_advance_to(tmp_path):
    init_sprint("s1", entry="EXECUTE", root=tmp_path)
    _set_tasks(tmp_path, TaskStatus.DONE)  # an empty tasks[] no longer passes vacuously
    advance_stage("REVIEW", root=tmp_path)
    _refused(tmp_path, "SCOPE", "final stage")
```

- `test_advance_to_execute_requires_g2_and_dev_plan` (`tests/test_advance.py:127-134`): add `_set_tasks(tmp_path, TaskStatus.PENDING)` immediately after the `init_sprint` line. The `_refused(..., "dev_plan is not recorded")` assertion in the middle is unaffected.
- `test_entry_scope_can_never_reach_execute_without_both_gates` (`tests/test_advance.py:164-190`): add `_set_tasks(tmp_path, TaskStatus.PENDING)` immediately after the two `record_artifact` calls. The three `_refused` assertions are unaffected.

Left alone deliberately (verify, do not assume): `test_artifact_that_vanished_from_disk_refuses` and `test_cli_refusal_is_nonzero_and_names_the_precondition` only assert refusals, and their `match` strings (`missing file`, `G2_plan`) still appear — the new failure is appended to the same list, not substituted for it. `tests/test_demo.py:35` likewise asserts the `→ EXECUTE` refusal names `G2_plan`, which it still does.

- [ ] **Step 5: Run the full suite and lint**

Run: `uv run pytest && uv run ruff check`
Expected: all green. Then confirm no other advance-past-a-guard call site was missed:

Run: `grep -rn 'advance_stage("EXECUTE"\|advance_stage("REVIEW"' tests/`
Expected: every hit is either inside a `_refused(...)` helper call or preceded by a `_set_tasks(...)` in the same test.

- [ ] **Step 6: Commit**

```bash
git add scripts/supskill_state/transitions.py tests/test_advance.py
git commit -m "feat: an empty tasks[] refuses on --to EXECUTE and --to REVIEW, closing the vacuous pass (SK-033)"
```

---

### Task 4: The HEAD guard — `plan_guard.py` and the `plan-guard` verb (SK-031)

**Files:**
- Create: `scripts/supskill_state/plan_guard.py`
- Modify: `scripts/supskill_state/cli.py` (a `plan-guard` subcommand)
- Test: `tests/test_plan_guard.py` (create)

**Interfaces:**
- Consumes: `StateError`.
- Produces:
  - `head_moved(before: str, after: str) -> bool` — `True` iff the two SHAs differ after stripping. Raises `StateError` when either is empty: **an unreadable HEAD is never a silent pass.**
  - `refusal(before: str, after: str) -> str` — the multi-line refusal text, naming both SHAs, what it means, and the guard's ceiling.
  - CLI: `supskill-state plan-guard --before <sha> --after <sha>` — exit **0** when HEAD did not move (prints `plan-guard: HEAD unchanged (<sha>)`), exit **1** when it did (prints `refusal(...)` to stderr) or when an argument is empty. This verb **reads nothing and writes nothing** — like `show`, it is a query, and it is the only non-mutating verb besides `show`.

**Design decision this task locks in** (the spec leaves the call site open — "a pure function plus the shell-out at the call site"): the shell-out to `git rev-parse HEAD` stays in the conductor (SKILL.md), but the **comparison is a CLI verb, not prose**. A guard whose comparison an LLM performs in its head is a guard that can be talked out of firing; a guard with an exit code cannot. The module would otherwise be imported by nothing, which is dead code a reviewer would rightly reject.

**The guard's ceiling, stated in its own refusal text and here** (S4 DoR finding 6): it catches an agent that **commits** — which is exactly what `subagent-driven-development` does, per task, by design. An agent that edits the working tree without committing walks straight past it. That is F-4's ceiling (loud and auditable, not impossible). Do not let a reviewer accept "the guard makes plan-stage execution impossible" — it does not, and this story does not claim it.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plan_guard.py`:

```python
"""SK-031 layer 2: the first mechanism in this product that catches a disobedient agent.

writing-plans' Execution Handoff names a REQUIRED SUB-SKILL per branch, and a
dispatched agent's AskUserQuestion auto-resolves empty (D4). If the template's
pre-answer fails to hold, the plan agent can implement the whole sprint inside
the PLAN stage - state.json still reading PLAN, G2_plan still null. HEAD moving
across the dispatch is the evidence.
"""

import pytest

from supskill_state.cli import main
from supskill_state.errors import StateError
from supskill_state.plan_guard import head_moved, refusal

BEFORE = "133da28f8f2b7c1a9e5d4c3b2a1908070605f4e3"
AFTER = "aa81d4d0e1f2a3b4c5d6e7f8091a2b3c4d5e6f70"


def test_an_unchanged_head_did_not_move():
    assert head_moved(BEFORE, BEFORE) is False


def test_a_changed_head_moved():
    assert head_moved(BEFORE, AFTER) is True


def test_surrounding_whitespace_is_stripped_before_comparing():
    # git rev-parse's output carries a trailing newline
    assert head_moved(f"{BEFORE}\n", f"  {BEFORE}  ") is False


def test_an_unreadable_head_is_never_a_silent_pass():
    for before, after in ((BEFORE, ""), ("", AFTER), ("", ""), (BEFORE, "   \n")):
        with pytest.raises(StateError, match="non-empty"):
            head_moved(before, after)


def test_the_refusal_names_both_shas_and_its_own_ceiling():
    text = refusal(BEFORE, AFTER)
    assert BEFORE in text and AFTER in text
    assert "a plan is a document" in text
    assert "without committing" in text  # the ceiling: an editing agent walks past this


def test_cli_exit_codes(capsys):
    assert main(["plan-guard", "--before", BEFORE, "--after", BEFORE]) == 0
    assert "HEAD unchanged" in capsys.readouterr().out

    assert main(["plan-guard", "--before", BEFORE, "--after", AFTER]) == 1
    err = capsys.readouterr().err
    assert BEFORE in err and AFTER in err

    assert main(["plan-guard", "--before", BEFORE, "--after", ""]) == 1
    assert "non-empty" in capsys.readouterr().err


def test_the_guard_needs_no_state_file(tmp_path, monkeypatch):
    # it is a query, not a verb: it must work before init and after a wipe
    monkeypatch.chdir(tmp_path)
    assert main(["plan-guard", "--before", BEFORE, "--after", BEFORE]) == 0
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_plan_guard.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'supskill_state.plan_guard'`.

- [ ] **Step 3: Implement the guard**

Create `scripts/supskill_state/plan_guard.py`:

```python
"""The HEAD guard (SK-031, layer 2; S4 DoR findings 1 and 6).

Layer 1 is prose: plan-prompt.md pre-answers writing-plans' Execution Handoff
(subagent-driven, always) and forbids the two execution sub-skills. Prose is not
enforcement, so this is layer 2: the conductor records `git rev-parse HEAD`
before the PLAN dispatch and compares after. If HEAD moved, the plan agent
committed - it executed - and the run stops for the operator.

The ceiling, stated here and in the refusal text because it will be oversold
otherwise: this catches an agent that COMMITS, which is precisely what
subagent-driven-development does, per task, by design. An agent that edits the
working tree without committing walks past it. That is F-4's ceiling - loud and
auditable, not impossible. This is not a sandbox and is not sold as one.
"""

from __future__ import annotations

from .errors import StateError


def head_moved(before: str, after: str) -> bool:
    """True iff the two SHAs differ. An unreadable HEAD raises - it is never a silent pass."""
    before, after = before.strip(), after.strip()
    if not before or not after:
        raise StateError(
            "the HEAD guard needs two non-empty SHAs (git rev-parse HEAD, before and after the "
            "dispatch); a HEAD that cannot be read is never a silent pass"
        )
    return before != after


def refusal(before: str, after: str) -> str:
    """What the conductor reports, verbatim, when the plan stage produced commits."""
    return (
        "the PLAN stage produced commits, so the plan agent executed rather than planned.\n"
        f"  HEAD before the dispatch: {before.strip()}\n"
        f"  HEAD after the dispatch:  {after.strip()}\n"
        "A plan is a document; a plan is not a commit. This run is stopped so you can inspect "
        f"the commits yourself: git log --oneline {before.strip()}..{after.strip()}\n"
        "Nothing was recorded and no gate was called: state.json still reads PLAN and G2 is "
        "still open.\n"
        "This guard's ceiling, stated plainly: it catches an agent that COMMITS. An agent that "
        "edits files without committing walks past it. It is not a sandbox."
    )
```

In `scripts/supskill_state/cli.py`, import the module and register the verb. Add to the imports:

```python
from . import commands, plan_guard
from .errors import StateError
```

Register it in `build_parser` after `_add_advance(subparsers)`:

```python
    _add_advance(subparsers)
    _add_plan_guard(subparsers)
    return parser
```

and add the pair at the end of the module, before `main`:

```python
def _add_plan_guard(subparsers) -> None:
    sub = subparsers.add_parser(
        "plan-guard",
        help="did HEAD move across the PLAN dispatch? exit 1 means the plan agent committed",
    )
    sub.add_argument("--before", required=True, help="git rev-parse HEAD, taken BEFORE the dispatch")
    sub.add_argument("--after", required=True, help="git rev-parse HEAD, taken AFTER the dispatch")
    sub.set_defaults(func=_cmd_plan_guard)


def _cmd_plan_guard(args) -> int:
    if plan_guard.head_moved(args.before, args.after):
        print(plan_guard.refusal(args.before, args.after), file=sys.stderr)
        return 1
    print(f"plan-guard: HEAD unchanged ({args.before.strip()})")
    return 0
```

`main`'s existing `except StateError` (`cli.py:136-140`) already turns the empty-SHA refusal into exit 1 with `supskill-state: refused: ...` on stderr — no new error handling is needed. Note `_cmd_plan_guard` returns 1 by itself for the moved case (it is a verdict, not a refusal), which is why it prints its own text rather than raising.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_plan_guard.py -v && uv run pytest && uv run ruff check`
Expected: all PASS. `test_no_module_outside_store_opens_files_for_writing` stays green — `plan_guard.py` neither reads nor writes a file.

- [ ] **Step 5: Commit**

```bash
git add scripts/supskill_state/plan_guard.py scripts/supskill_state/cli.py tests/test_plan_guard.py
git commit -m "feat: the HEAD guard - a plan stage that produced commits stops the run (SK-031)"
```

---

### Task 5: `plan-prompt.md` — the template that pre-answers the Execution Handoff (SK-030, SK-031)

**Files:**
- Create: `skills/supskill/references/plan-prompt.md`
- Test: `tests/test_prompt_templates.py` (extend — the standing lint grows a second assertion)

**Interfaces:**
- Consumes: nothing from the CLI at runtime — a template is a document. It states the heading rule Task 2 enforces and the citation rule `supskill-audit` enforces.
- Produces: `plan-prompt.md` with placeholders `{SPRINT_DOC_PATH}`, `{OUTPUT_PATH}`, `{REPO_ROOT}`, `{EXEMPLAR_PLAN}`; Task 6's SKILL.md section fills exactly those four.

**The thing being defused.** `superpowers:writing-plans` does not merely *end by asking* which execution mode to use — its **Execution Handoff** section ends by **routing into execution**: "Two execution options… **1. Subagent-Driven (recommended)** … **2. Inline Execution** … Which approach?", and each branch names a **REQUIRED SUB-SKILL** the agent is expected to invoke next (`subagent-driven-development` or `executing-plans`). The plan header the skill mandates repeats the instruction inside the plan document itself. A dispatched subagent cannot ask anyone anything (D4) — in headless the question auto-resolves empty in ~37ms — and an agent holding an empty answer plus two REQUIRED SUB-SKILL instructions is one plausible step from implementing the entire sprint inside the PLAN stage. Read the live `writing-plans` SKILL.md before writing this template; the exact wording is what you are answering.

**Executor skills:** `superpowers:writing-skills`. Degrees of freedom: the pre-answer, the two forbidden sub-skills, the output path, the heading format, and the citation rule are **low-freedom** (verbatim). "What the right task decomposition is" is judgment and belongs to `writing-plans`, not to this template — say so instead of pretending to specify it.

- [ ] **Step 1: Extend the tests (failing first)**

In `tests/test_prompt_templates.py`, add `PLAN` beside the other two constants:

```python
REFERENCES = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "references"
SCOPE = REFERENCES / "scope-prompt.md"
REFINE = REFERENCES / "refine-prompt.md"
PLAN = REFERENCES / "plan-prompt.md"

TEMPLATES = (SCOPE, REFINE, PLAN)
EXECUTION_SUB_SKILLS = ("subagent-driven-development", "executing-plans")
```

Change the existing tripwire (`tests/test_prompt_templates.py:26-30`) to loop over `TEMPLATES`:

```python
def test_no_dispatch_template_line_instructs_running_the_state_cli():
    for template in TEMPLATES:
        for line in template.read_text(encoding="utf-8").splitlines():
            if "supskill-state" in line:
                assert "not" in line.lower(), f"{template.name}: {line!r}"
```

and append the second standing assertion plus the PLAN template's own tests:

```python
def test_no_dispatch_template_line_instructs_an_execution_sub_skill():
    # SK-031: writing-plans' Execution Handoff names a REQUIRED SUB-SKILL per branch. No
    # template may route its agent into one - a plan agent that executes bypasses Gate 2
    # entirely (state.json still reads PLAN while the branch carries the commits).
    for template in TEMPLATES:
        for line in template.read_text(encoding="utf-8").splitlines():
            if any(skill in line for skill in EXECUTION_SUB_SKILLS):
                assert "not" in line.lower(), f"{template.name}: {line!r}"


def test_plan_template_names_its_placeholders():
    text = PLAN.read_text(encoding="utf-8")
    for placeholder in ("{SPRINT_DOC_PATH}", "{OUTPUT_PATH}", "{REPO_ROOT}", "{EXEMPLAR_PLAN}"):
        assert placeholder in text, placeholder


def test_plan_template_states_the_two_standing_constraints():
    text = PLAN.read_text(encoding="utf-8")
    assert "cannot ask anyone anything" in text  # D4 / invariant 2
    assert "must not run `supskill-state`" in text  # invariant 3, third surface


def test_plan_template_pre_answers_the_execution_handoff_and_stops():
    text = PLAN.read_text(encoding="utf-8")
    assert "subagent-driven, always" in text  # the question is already answered
    assert "superpowers:writing-plans" in text  # the skill it must actually invoke
    assert "do not implement, test, or commit anything" in text.lower()


def test_plan_template_states_the_join_key_and_the_citation_rule():
    text = PLAN.read_text(encoding="utf-8")
    assert "(SK-0xx)" in text and "(process)" in text  # the heading grammar SK-033 validates
    assert "exists today" in text  # cite lines only for code that exists today
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_prompt_templates.py -v`
Expected: the four PLAN tests and both tripwires FAIL with `FileNotFoundError: ... references/plan-prompt.md`; nothing else changes.

- [ ] **Step 3: Write the template**

Create `skills/supskill/references/plan-prompt.md`:

```markdown
# PLAN dispatch template

The conductor fills every `{PLACEHOLDER}` below and dispatches the result as
the complete prompt of one general-purpose subagent:

- `{SPRINT_DOC_PATH}` — the G1-approved sprint doc; it is the spec
- `{OUTPUT_PATH}` — where the dev plan must be written (derived by the conductor)
- `{REPO_ROOT}` — the repository the plan will be executed against
- `{EXEMPLAR_PLAN}` — an existing dev plan under `docs/superpowers/plans/`, or `none`

---

You are writing the implementation plan for the sprint specified at
{SPRINT_DOC_PATH}. Invoke the `superpowers:writing-plans` skill and follow it:
the sprint doc is the spec that skill asks for. Read it in full first, and read
the live source under {REPO_ROOT} for every file the plan will touch.

Three facts about your situation, stated up front because they are structural:

- **You cannot ask anyone anything.** You are a dispatched subagent: the
  question tool is unavailable to you, and in a headless run it would resolve
  instantly with an empty answer. Everything you need is in this prompt, in the
  sprint doc, and on disk. Where the spec leaves something open, make the
  smaller, reversible choice and say so in the plan — the operator reads this
  plan at a gate and can overrule you there.
- **You must not run `supskill-state`, and you must not read or write anything
  under `.supskill/`.** You produce one document; the conductor alone records it.
- **The execution question is already answered: subagent-driven, always.**
  `writing-plans` ends with an Execution Handoff that offers you two execution
  modes and names a REQUIRED SUB-SKILL for each. Do not answer it, and do not
  route into it. **Do not invoke `superpowers:subagent-driven-development` or
  `superpowers:executing-plans`.** Do not implement, test, or commit anything.
  Write the plan, save it, report the path, and stop. A plan is a document; the
  stage that executes it is a different stage, behind a gate you cannot see.
  The plan document's own mandated header keeps naming
  `superpowers:subagent-driven-development` as the execution sub-skill — leave
  it there: that instruction is for the conductor at a later stage, not for you.

Your task:

1. Write the plan to {OUTPUT_PATH} — exactly that path, nowhere else. This
   overrides `writing-plans`' own dated-path default; the conductor supplies the
   path because the date is not derivable from a plan it has not read yet.
2. **Every task heading names the story it serves:**
   `### Task N: <what> (SK-0xx)` — or the literal `### Task N: <what> (process)`
   for a task that serves no backlog story (a demo checklist, a docs-only
   delta). This is a join key, not a decoration: a script checks that every
   story in the sprint doc is named by at least one task heading and that every
   task heading names a known story or `(process)`. A plan that drops a story is
   refused before the operator ever sees it. One heading may name two stories.
3. **Citations: cite `file:line` only for code that exists today.** A script
   resolves every backtick-wrapped `path:line` (and `path:start-end`) citation
   in your plan against the working tree and fails this stage on any that does
   not resolve. A task that CREATES a file names the path with no line number —
   `Create: \`scripts/foo.py\`` — because a line number for a file that does not
   exist yet cannot resolve and never will. Read the live source before citing
   it; the sprint doc was written earlier and its line numbers may have shifted.
4. Shape target: {EXEMPLAR_PLAN}. Honor the sprint doc's own sequencing section
   if it has one — it was written by someone who knew what blocks what.

How to decompose the work into tasks is `writing-plans`' business and your
judgment; this prompt does not pretend to specify it.

Report back exactly two lines: the path you wrote, and the number of tasks. The
document is the deliverable, not your report.
```

- [ ] **Step 4: Run the tests, lint, and the two invariant greps**

Run: `uv run pytest tests/test_prompt_templates.py -v && uv run pytest && uv run ruff check`
Expected: all PASS.

Run: `grep -n "supskill-state\|\.supskill/" skills/supskill/references/plan-prompt.md`
Expected: only the "must not run" statement.

Run: `grep -n "subagent-driven-development\|executing-plans" skills/supskill/references/*.md`
Expected: hits only in `plan-prompt.md`, and every one of them on a line that forbids or defers the sub-skill.

- [ ] **Step 5: Commit**

```bash
git add skills/supskill/references/plan-prompt.md tests/test_prompt_templates.py
git commit -m "feat: plan-prompt.md - pre-answers writing-plans' execution handoff, forbids both sub-skills (SK-030, SK-031)"
```

---

### Task 6: The PLAN stage — dispatch, HEAD guard, audit, record, load tasks (SK-030, SK-031)

**Files:**
- Modify: `skills/supskill/SKILL.md:87-98` (the dispatch table's PLAN row and its closing paragraph) and a new `## The PLAN stage` section inserted after `## Gate 1 — the operator reads the refined doc` (`skills/supskill/SKILL.md:158-180`), before `## Reference` — frontmatter untouched

**Interfaces:**
- Consumes: `plan-prompt.md` (Task 5) and its four placeholders; `supskill-state plan-guard --before --after` (Task 4); `supskill-state tasks --from <doc> --plan <plan>` (Tasks 1–2); `supskill-audit <doc>` (`scripts/supskill-audit`, S3) — **without** `--proofs`, because a dev plan carries no proof lines; `artifact --set dev_plan --path <path>`, which refuses a path that does not exist (`commands.py:184-185`) and whose `dev_plan` key has been valid since S1 (`model.py:63`, `cli.py:74`).
- Produces: the `## The PLAN stage` section, whose last step falls through to **Gate 2** (Task 7 writes that section).

**No CLI work in this task.** The artifact half of E4 was built in S1 and has been waiting.

**Executor skills:** `superpowers:writing-skills`. The SCOPE section (`skills/supskill/SKILL.md:100-133`) is the shape to copy; the REFINE section's mechanical-verification step (`skills/supskill/SKILL.md:150-156`) is the shape of step 7.

- [ ] **Step 1: Replace the PLAN row and fix the stub paragraph**

In `skills/supskill/SKILL.md`, the dispatch table's PLAN row (`skills/supskill/SKILL.md:93`) becomes:

```markdown
| `PLAN` | Follow **The PLAN stage** below. |
```

and the paragraph under the table (`skills/supskill/SKILL.md:97-98`) becomes:

```markdown
EXECUTE and REVIEW are honest stubs until their epics land — do not improvise a
stage. An implemented stage follows its section below exactly.
```

- [ ] **Step 2: Write the stage section**

Insert into `skills/supskill/SKILL.md` after the Gate 1 section, before `## Reference`:

```markdown
## The PLAN stage

Same pattern as SCOPE (dispatch → verify → record → advance), plus one thing no
earlier stage needed. The plan agent is the first dispatched agent whose own
skill tries to route it into *executing* what it just planned: `writing-plans`
ends by naming a REQUIRED SUB-SKILL per execution mode, and a subagent's
question tool auto-resolves empty. The template pre-answers that (layer 1). Step
6 catches it if the prompt fails to hold (layer 2).

1. **Resume idempotence.** If `artifacts.dev_plan` is recorded AND the file
   exists, PLAN already dispatched — skip to step 7 (record and load tasks),
   then Gate 2. A crash between `artifact` and the gate must not re-spend a plan
   run.
2. **Locate the spec:** `artifacts.sprint_doc` from `show --json` — the doc the
   operator approved at Gate 1. Missing from disk → report that and stop.
3. **Derive the output path:**
   `docs/superpowers/plans/<YYYY-MM-DD>-sprint-<id>-<slug>.md`, where
   `<YYYY-MM-DD>` is today's date as the environment reports it, `<id>` is the
   sprint id lowercased, and `-<slug>` is dropped when `sprint.slug` is null.
   `writing-plans` has a dated-path convention of its own and honors an explicit
   override — supply this path and nothing else. Create the directory if needed.
   As always: `artifacts.dev_plan` is the only authority anything downstream
   reads.
4. **Record HEAD.** Run `git rev-parse HEAD` from the repo root and keep the SHA.
5. **Fill the template**
   [references/plan-prompt.md](references/plan-prompt.md) — `{SPRINT_DOC_PATH}`,
   `{OUTPUT_PATH}`, `{REPO_ROOT}`, `{EXEMPLAR_PLAN}` (an existing plan under
   `docs/superpowers/plans/`, or `none`) — and dispatch one general-purpose
   subagent whose entire prompt is the filled template.
6. **The HEAD guard.** Run `git rev-parse HEAD` again, then:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state plan-guard --before <before> --after <after>`
   - Exit 0 → continue.
   - Exit 1 → **stop here.** Do not record the artifact, do not load tasks, do
     not advance, do not call `gate`. Report the guard's message verbatim,
     followed by the output of `git log --oneline <before>..<after>` so the
     operator can see exactly what the plan agent committed. The plan stage
     produced commits; a plan is a document, and this run is stopped for you to
     inspect them.
7. **Verify and audit the plan.** The file must now exist at the derived output
   path. If it does not, report the agent's returned output verbatim and stop —
   never guess a path the agent may have used instead. Then, from the repo root:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-audit <plan path>` — citations only,
   **no `--proofs`**: a dev plan carries no proof lines. Exit 1 → report the
   failures verbatim and stop. This is a hard failure, not advisory; there is no
   re-dispatch loop at PLAN.
8. **Record and load tasks.** Run
   `artifact --set dev_plan --path <plan path>`, then
   `tasks --from <sprint doc path> --plan <plan path>`. The second call is where
   a plan that silently dropped a story is caught: every story in the sprint doc
   must be named by a `### Task N … (SK-0xx)` heading, and every task heading
   must name a known story or the literal `(process)`. On a refusal, report it
   verbatim and stop — the operator never approves a plan with a hole in it.
9. Continue at **Gate 2** (next section).
```

- [ ] **Step 3: Run the suite and the prose self-checks**

Run: `uv run pytest && uv run ruff check`
Expected: all green — including `tests/test_skill_frontmatter.py::test_body_stays_under_500_lines` (the body grows from 186 lines to ~230; the frontmatter is untouched).

Run: `grep -n "supskill-audit\|plan-guard\|tasks --from" skills/supskill/SKILL.md`
Expected: the audit runs **without** `--proofs` at PLAN and **with** it at REFINE; `plan-guard` appears once (step 6); `tasks --from` appears once (step 8), with `--plan`.

- [ ] **Step 4: Commit**

```bash
git add skills/supskill/SKILL.md
git commit -m "feat: PLAN stage - dispatch writing-plans, HEAD guard, citation audit, load tasks (SK-030, SK-031)"
```

---

### Task 7: Gate 2 — the operator reads the plan (SK-032)

**Files:**
- Modify: `skills/supskill/SKILL.md` (one new section, after `## The PLAN stage`, before `## Reference`; the PLAN section's step 9 already points at it)

**Interfaces:**
- Consumes: Task 6's PLAN section ("Continue at **Gate 2**"); the `gate` verb (`gate --id G2 --decision approved|rejected --response "<verbatim>"`), which accepts and records empty responses **by design** (`commands.py:203`); `advance --to EXECUTE` enforcement (`transitions.py:32-34`, plus Task 3's empty-`tasks[]` refusal).
- Produces: the `## Gate 2 — the operator reads the dev plan` section. E6's G3 copies this UX a third time.

**This is a deliberate copy of Gate 1's section** (`skills/supskill/SKILL.md:158-180`) — the empty-answer refusal included. Enforcement already exists (`advance --to EXECUTE` refuses without `G2_plan == approved` and a recorded, existing `dev_plan`, built at S1); this story is the gate's UX. If a third repetition starts to itch at E6, that is the signal to extract a shared `references/gate.md` — **not now.** Two instances is a coincidence; three is a pattern; E6 is the epic that will know which parts actually vary. Do not "clean this up" mid-sprint (S4 DoR finding 5).

**Executor skills:** `superpowers:writing-skills`. `docs/.ai/reports/contexts/01-claude-code-context-mechanics.md` §6 is the local authority on `AskUserQuestion` mechanics (subagent-stripped; headless auto-resolve empty in ~37ms) — do not re-derive its behavior from memory.

- [ ] **Step 1: Write the section**

Insert into `skills/supskill/SKILL.md` after `## The PLAN stage`, before `## Reference`:

```markdown
## Gate 2 — the operator reads the dev plan

The same shape as Gate 1, deliberately. The CLI records empty gate responses BY
DESIGN — a fabricated approval must leave a readable empty quote in the trail.
So the refusal to treat silence as consent lives here, in the conductor, and
nowhere else.

1. **Ask for real.** Use the `AskUserQuestion` tool: approve / reject the dev
   plan at its recorded path, free text welcome. Name the plan path in the
   question so the operator knows what they are approving.
2. **An empty or auto-resolved answer is not a decision.** In headless runs the
   question tool resolves instantly with an empty answer. If the answer comes
   back empty, do NOT call `gate`. Report that Gate 2 requires an interactive
   operator, and stop.
3. **Record verbatim.** A non-empty answer — the selected label plus any free
   text, unedited — goes to:
   `gate --id G2 --decision <approved|rejected> --response "<verbatim>"`
4. `approved` → `advance --to EXECUTE` → continue at the `EXECUTE` dispatch row
   (E5's honest stub: it reports and stops — do not improvise EXECUTE).
5. `rejected` → the decision is recorded and final for this pass; report it and
   stop, naming the rework loop: the operator edits the plan directly or asks
   for a fresh PLAN pass, then re-invokes `/supskill run <sprint-id>` and
   re-gates. The last decision wins in state while every attempt stays in the
   trail.
```

- [ ] **Step 2: Run the suite and the prose self-checks**

Run: `uv run pytest && uv run ruff check`
Expected: all green (the body lands near 250 lines, well under the 500-line cap).

Run: `grep -n "gate --id G" skills/supskill/SKILL.md`
Expected: exactly two hits — `gate --id G1` in Gate 1 step 3 and `gate --id G2` in Gate 2 step 3.

Run: `grep -in "auto-approve\|--yes" skills/supskill/SKILL.md`
Expected: no hits. Nothing anywhere offers a shortcut past either gate.

- [ ] **Step 3: Commit**

```bash
git add skills/supskill/SKILL.md
git commit -m "feat: Gate 2 - the operator reads the plan; an empty answer is not a decision (SK-032)"
```

---

### Task 8: The sprint demo checklist (process)

**Files:**
- Create: `.superpowers/sdd/s4/demo-checklist.md` (sprint scratch — gitignored by design; no commit)

**Interfaces:**
- Consumes: everything — the complete E4 conductor, installed or loadable as a plugin, plus real tokens.
- Produces: the script the operator runs. `seam: app-level`, `provable: operator` — **the sprint does not close on offline green alone.** The offline suite proves the tasks verb, the coverage validator, the two preconditions, and the HEAD-guard predicate. It cannot prove that a dispatched agent *obeys* a template; only the demo can. Its output is a real dev plan for S5, which the operator needed anyway.

- [ ] **Step 1: Write the demo checklist**

Create `.superpowers/sdd/s4/demo-checklist.md`:

```markdown
# S4 demo — PLAN → Gate 2 in anger (operator-run, real tokens)

Run in THIS repo (supskill's own), at the repo root. Expected outcomes are
written before running; any mismatch fails the demo. The sprint being scoped is
S5 (E5, drain-then-halt), so the artifact is a real S5 dev plan.

- [ ] 1. Preflight: working tree clean (the HEAD guard is meaningless otherwise);
      no `.supskill/` at the repo root, or archive an old run deliberately, by
      hand. `docs/plans/sprints/backlog-01/backlog.md` exists.
- [ ] 2. `/supskill run s5 --backlog docs/plans/sprints/backlog-01/backlog.md --slug execute-drain`
      → SCOPE + REFINE + Gate 1 (S3's stages, now load-bearing for a stage they
      did not build). Approve at Gate 1 with real words.
- [ ] 3. PLAN dispatches `writing-plans` against the S5 sprint doc. Watch for:
      the conductor took `git rev-parse HEAD` BEFORE dispatching.
- [ ] 4. The plan lands at the supplied path
      (`docs/superpowers/plans/<today>-sprint-s5-execute-drain.md`) — not at a
      date the agent invented, and not anywhere else.
- [ ] 5. **HEAD has not moved.** `plan-guard` exits 0. If it exits 1, the demo
      has found the sprint's headline failure: STOP, keep the commits, and read
      them — that is a finding, not a demo failure, and it belongs in the
      retro.
- [ ] 6. `supskill-audit <plan>` passes (citations only, no `--proofs`). If it
      fails on a `Create:` line, the template is at fault, not the audit — fix
      the template.
- [ ] 7. `tasks --from <S5 sprint doc> --plan <plan>` loads with coverage clean:
      every S5 story is named by at least one `### Task N … (SK-0xx)` heading.
      `show --json` now has a non-empty `tasks[]` for the first time in this
      project's history.
- [ ] 8. **`/clear`** — the context is now genuinely empty (invariant 5).
- [ ] 9. `/supskill run s5` → resumes onto Gate 2 from disk alone: `dev_plan` is
      recorded and exists, so PLAN skips the dispatch (no second plan run) and
      asks the gate.
- [ ] 10. Gate 2 asks FOR REAL via AskUserQuestion. Read the S5 plan first.
      Answer with real words, not a bare click.
- [ ] 11. Verify the trail: the last line of `.supskill/gates.jsonl` is G2 with
      your decision and a NON-EMPTY verbatim response.
- [ ] 12. approved → the conductor ran `advance --to EXECUTE` (which now also
      required a non-empty `tasks[]`) and stopped on the honest E5 stub.
      rejected → stage is still PLAN and the conductor named the rework loop.
- [ ] 13. Record below, verbatim: pass/fail per step, the G2 decision, whether
      HEAD moved, and your honest read on the plan's quality. Step 5's outcome
      is the sprint's single most important data point.
```

- [ ] **Step 2: Hand it to the operator**

Report: the demo checklist is at `.superpowers/sdd/s4/demo-checklist.md`; it is the exit criterion for SK-030/031/032's prompt-shaped acceptance; the sprint stays open until the operator runs it. No commit — the scratch dir is gitignored by design.

---

### Task 9: Apply the S4 DoR backlog deltas (process)

**Files:**
- Modify: `docs/plans/sprints/backlog-01/backlog.md`

**Interfaces:**
- Consumes: nothing from other tasks (docs-only; the operator commissioning this plan is the acceptance the sprint doc's "once the operator accepts" clause names).
- Produces: a backlog that matches what S4 actually committed — the six deltas from the sprint doc's "Backlog deltas — proposed" section.

- [ ] **Step 1: Re-point SK-030 (3 → 4)**

In the E4 table (`docs/plans/sprints/backlog-01/backlog.md:123`), replace the SK-030 row:

```markdown
| SK-030 | PLAN stage: dispatch `superpowers:writing-plans` with the refined sprint doc as the spec. S4 DoR: the conductor supplies the output path (`writing-plans`' own convention is dated and not derivable from a doc it has not read); the plan's citations are audited before Gate 2; the stage is resume-idempotent; and every plan task heading must name the story it serves — the join key E5 maps SDD statuses through. | 4 | M | ☐ |
```

- [ ] **Step 2: Re-point SK-031 (2 → 3) and correct its description**

Replace the SK-031 row (`docs/plans/sprints/backlog-01/backlog.md:124`):

```markdown
| SK-031 | Intercept `writing-plans`' Execution Handoff. S4 DoR corrected this: it does **not** merely end by asking — each branch names a REQUIRED SUB-SKILL, so a headless plan agent can execute the entire sprint inside the PLAN stage, bypassing `advance --to EXECUTE`'s `G2_plan` precondition entirely while `state.json` still reads `PLAN`. Resolution, two layers: the template pre-answers *subagent-driven, always* and forbids both execution sub-skills (lint-asserted), and a HEAD-moved guard stops the run if the agent committed. The guard catches a committing agent, not an editing one — F-4's ceiling, stated. | 3 | M | ☐ |
```

- [ ] **Step 3: Re-point SK-033 (3 → 5) and re-classify it from plumbing to enforcement**

Replace the SK-033 row (`docs/plans/sprints/backlog-01/backlog.md:126`):

```markdown
| SK-033 | `supskill-state tasks --from <doc>` loads `tasks[]` (id, seam, provable, status=PENDING) from the refined sprint doc's proof lines — `proofs.py` stays the only parser. **Enforcement, not plumbing** (S4 DoR finding 2): `advance --to REVIEW` refuses while any task is non-terminal, which over an empty `tasks[]` passed vacuously — so a sprint could reach REVIEW having executed nothing. The verb also adds empty-list refusals on `→ EXECUTE` and `→ REVIEW`, plus load-time coverage validation joining plan task headings to story ids. (Proposed at S2 DoR, finding 6; grown at S4 DoR.) | 5 | M | ☐ |
```

- [ ] **Step 4: Note the join key on SK-043 (E5, points unchanged)**

Replace the SK-043 row (`docs/plans/sprints/backlog-01/backlog.md:135`):

```markdown
| SK-043 | Map SDD's `DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT` onto task status. `DONE_WITH_CONCERNS` proceeds but carries the concern to Gate 3. (**D5**) The join is the `SK-0xx` id in each plan task's heading, established by SK-030 and validated by SK-033: E5 adds no parser and invents no second id scheme. | 3 | M | ☐ |
```

- [ ] **Step 5: Update the totals**

- Section header (`docs/plans/sprints/backlog-01/backlog.md:119`): `## E4 — PLAN + Gate 2 (10 pts)` → `## E4 — PLAN + Gate 2 (14 pts)`.
- Summary table E4 row (`docs/plans/sprints/backlog-01/backlog.md:67`): `| 10 |` → `| 14 |`, and its "Why it's here" cell — the word "Thin" is now wrong in one direction — becomes: `Thin in code, sharp in consequence: wiring \`writing-plans\` and stopping it from executing the sprint it is planning.`
- `**Total: 124 pts.**` (`docs/plans/sprints/backlog-01/backlog.md:73`) → `**Total: 128 pts.**`

- [ ] **Step 6: Record Gate 1 data point #4**

Append after the "Data point #3" paragraph at the end of `docs/plans/sprints/backlog-01/backlog.md`:

```markdown
**Data point #4 (S4 DoR, 2026-07-13):** refinement against live source grew scope
+4 pts (10 → 14), and — for the fourth consecutive sprint — the sharpest finding
was structural, not cosmetic: a headless PLAN stage could have executed the
entire sprint before its own approval gate (`writing-plans`' Execution Handoff
names a REQUIRED SUB-SKILL per branch), and an empty `tasks[]` made the spine's
strongest precondition a no-op. Neither is visible from a backlog one-liner.
Four sprints, four data points, same direction — §7.2 can be closed at E6 with
the answer *the gate earns its keep because the refinement does*. (Report §7.2)
```

- [ ] **Step 7: Commit**

```bash
git add docs/plans/sprints/backlog-01/backlog.md
git commit -m "docs: apply S4 DoR backlog deltas (SK-030 4pts, SK-031 3pts, SK-033 5pts, E4 14pts, total 128)"
```

---

## Exit criteria mapping (sprint doc → plan)

| Sprint exit criterion | Where it lands |
|---|---|
| SK-030: `plan-prompt.md` exists with the D4 and invariant-3 clauses and the story-id heading requirement | Task 5 |
| SK-030: the PLAN row dispatches, audits, records `dev_plan`, loads tasks, and resumes idempotently | Task 6 |
| SK-031: the template forbids both execution sub-skills, asserted by the template lint | Task 5 |
| SK-031: the HEAD guard is TDD'd offline, stops the run with both SHAs named, and states its ceiling in its own refusal text | Task 4 (predicate + verb), Task 6 (the choreography that calls it) |
| SK-032: Gate 2 asks for real, refuses an empty answer without calling `gate`, records verbatim words; `advance --to EXECUTE` succeeds only after it | Task 7 |
| SK-033: `tasks --from` loads this sprint doc's four proof lines in its fixture test | Task 1 |
| SK-033: coverage validation refuses a plan that drops a story | Task 2 |
| SK-033: `→ EXECUTE` and `→ REVIEW` both refuse an empty `tasks[]`, tested with SCOPE-entry and EXECUTE-entry fixtures | Task 3 |
| Full suite pure offline and fast; every Python story TDD'd with failing-test-first evidence | Tasks 1–4 step sequences |
| The sprint demo (operator-run, real tokens, `/clear` mid-sprint, HEAD unmoved, verbatim G2 words on disk) | Task 8 — **operator-run; the sprint does not close on offline green alone** |
| Backlog deltas applied | Task 9 |

## Review pass (after all tasks)

Author↔review separation holds: dispatch `oh-my-claudecode:code-reviewer`, then `oh-my-claudecode:verifier`, in fresh contexts. Named checks this sprint, beyond the standing ones:

1. **Invariant 3, three surfaces:** no module outside `store.py` carries a write primitive (tripwire test); no line of SKILL.md instructs editing `.supskill/` by hand; no template under `skills/supskill/references/` instructs an agent to run `supskill-state` or touch `.supskill/`.
2. **The execution-sub-skill ban (new, standing):** no template instructs its agent to invoke `subagent-driven-development` or `executing-plans`. `plan-prompt.md` names both only to forbid them, and the lint asserts it.
3. **The guard is not oversold.** If anyone — reviewer, executor, or report — says "plan-stage execution is now impossible", that is the failure this check exists to catch. Uncommitted edits slip past the guard; that is stated in the refusal text, in `plan_guard.py`'s docstring, and in the sprint doc (finding 6). It is F-4's ceiling, not a bug.
4. **One parser, one vocabulary.** `load_tasks` calls `parse_proof_lines` and parses nothing itself. `plan_coverage.py` owns the *heading* grammar only — a different vocabulary, deliberately in its own module.
5. **No G2 shortcut:** nothing anywhere offers `--yes`, auto-approve, or a default answer; the empty-answer refusal is present and unconditional, in Gate 1 and Gate 2 alike.
6. **Gate 2 is a copy on purpose.** Do not factor out a shared gate reference this sprint — E6's third instance is the named trigger (finding 5). A reviewer who suggests the extraction is right about the smell and wrong about the timing.
7. **E5 boundary:** the EXECUTE row is still the untouched honest stub; SDD is not dispatched anywhere; no status mapping exists yet.
