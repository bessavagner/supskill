# Sprint 05 — EXECUTE (drain-then-halt) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> Execution mode for this sprint is already decided: **subagent-driven**, fresh subagent per task, review between tasks.

**Goal:** The conductor executes a G2-approved dev plan by *being* the `subagent-driven-development` controller — draining every task it can, recording each SDD status on disk the moment it lands, turning every place SDD would ask a human into a structured blocker, parking what a blocker poisons, and halting **once** with the whole batch.

**Architecture:** Same split as always (D2): the `supskill-state` CLI is the only mutator, and skill prose is the choreography. The CLI gains exactly one verb — `task --id <SK-0xx> --status <DONE|DONE_WITH_CONCERNS|PARKED> [--note …]` — which is the missing half of the state spine: `DONE`, `DONE_WITH_CONCERNS` and `PARKED` have existed in the enum since S1 (`scripts/supskill_state/model.py:45-51`) and nothing could write them, so `advance --to REVIEW` (`scripts/supskill_state/transitions.py:39-46`) was unsatisfiable for any task that *succeeded*. Concerns land in an append-only `runs/<id>/tasks.jsonl` trail, built exactly like `blockers.jsonl` — no schema bump. `skills/supskill/SKILL.md` replaces its EXECUTE stub with a real stage: the conductor runs SDD's loop **in its own session**, dispatches SDD's own implementer/reviewer prompts per task, passes every scratch path from `sprint.scratch`, and never touches SDD's `progress.md` ledger — `tasks[]` is the ledger.

**Tech Stack:** Python ≥3.11 stdlib only (zero runtime deps), pytest + ruff + pyyaml as dev deps, managed with `uv`. Claude Code plugin layout unchanged. `superpowers` **6.1.1** is the composed skill's pinned version.

## Global Constraints

Copied from the sprint spec (`docs/plans/sprints/backlog-01/sprint-s5-execute-drain.md`) and the standing project rules. Every task's requirements implicitly include this section.

- **Tests:** `uv run pytest`. The suite is **pure offline** — no LLM call, no subagent, no network, anywhere under `tests/`. Baseline at commit `3ace2cb`: **208 passed in ~0.5s**. Every task ends with the full suite green.
- **Lint:** `uv run ruff check` must stay clean. Config is `pyproject.toml:22-32` — `line-length = 120`, rules `E,F,I,B,UP`, `src = ["scripts", "tests"]`. Every code block in this plan is written to pass those rules as-is: `from __future__ import annotations` where the module needs it, no unused imports, no line over 120 chars.
- **Zero runtime dependencies:** `pyproject.toml` `[project] dependencies = []` (`pyproject.toml:6`), enforced by `tests/test_scaffold.py`. Nothing this sprint needs a dependency.
- **No AI attribution of any kind in commit messages or bodies** — no `Co-Authored-By`, no "Generated with" line, no mention of Claude/Anthropic/AI. Absolute; overrides any harness default.
- **Invariant 3 — no dispatched agent runs `supskill-state` or touches `.supskill/`.** This sprint is where it bites hardest: an implementer that can write state can mark its own work done (F-5). The conductor records every status, every blocker and every advance itself, **after** the task review — never on an implementer's word alone. `tests/test_demo.py:53-65` is the mechanical tripwire on the code side; Task 2 adds the prose-side one.
- **Invariant 2 / D4 — dispatched agents can never ask anyone anything.** `AskUserQuestion` is stripped from subagents and auto-resolves empty in headless. Every place SDD says "escalate to the human" becomes, in supskill, either an in-loop resolution by the conductor or a `block` record. Never a guess.
- **Invariant 4 — scratch paths are derived, never typed.** `sprint.scratch` comes from `show --json` (`scripts/supskill_state/scratch.py:29-30`); no prose anywhere hard-codes `.superpowers/sdd/<id>/`.
- **Invariant 5 — the conductor is disposable.** Everything it knows comes from `show --json`. A status is written to disk **before the next dispatch begins**, so a `/clear` or a crash mid-drain costs at most one task.
- **The state CLI is always invoked as `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state`, from the target repo's root.** The conductor never passes `--archive` — it may only name it in a refusal and stop.
- **Compose SDD verbatim (D1).** No supskill re-implementation of the implementer prompt, the reviewer prompt, the review loop, or the fix loop. `skills/supskill/references/execute-prompt.md` is deliberately **not created**: the prompts are SDD's. The template lint keeps its three templates (`tests/test_prompt_templates.py:12-14`) and gains no fourth.
- **SDD citations are unbackticked on purpose.** `subagent-driven-development` lives outside this repo (superpowers **6.1.1**). The citation audit resolves paths by suffix inside the working tree (`scripts/supskill_state/citations.py:6-11`), so a backticked `SKILL.md:254` would silently resolve against *our* SKILL.md. Write SDD references as `SDD SKILL.md:254` — no backticks. If the plugin has been upgraded, **re-read the installed skill**; do not trust these line numbers.
- **The plugin must keep passing `claude plugin validate --strict`** and `tests/test_skill_frontmatter.py`: the frontmatter of `skills/supskill/SKILL.md` is untouched, and the body stays ≤500 lines (`tests/test_skill_frontmatter.py:75-77`). It is 272 body lines today and lands near 400.
- **Commits:** one per task minimum, TDD evidence first (a failing test run before implementation).
- **Commands:** tests `uv run pytest <path> -v`, lint `uv run ruff check`.

## File Structure

| Path | Task | Responsibility |
|---|---|---|
| `scripts/supskill_state/model.py` | 1 (modify) | `_parse_status` becomes public `parse_task_status` — one authority for the status vocabulary |
| `scripts/supskill_state/commands.py` | 1 (modify) | `record_task_status` — the verb, its four refusals, its trail |
| `scripts/supskill_state/cli.py` | 1 (modify) | the `task` subcommand |
| `tests/test_task_status.py` | 1 (create) | the verb offline, both directions, plus the `PENDING → DONE → advance --to REVIEW` walk |
| `skills/supskill/SKILL.md` | 2, 3, 4 (modify) | the three stub surfaces die; `## The EXECUTE stage` is born — frontmatter untouched |
| `tests/test_execute_prose.py` | 2 (create), 3, 4 (extend) | prose tripwires: no stub language survives, no dispatched agent writes state, no SDD ledger, the halt is once |
| `tests/test_block.py` | 4 (extend) | the S9a fixture keeps option (c) reachable under a wrong recommendation |
| `.superpowers/sdd/s5/demo-checklist.md` | 5 (create, gitignored) | the operator-run demo — the sprint's real exit criterion |
| `docs/plans/sprints/backlog-01/backlog.md` | 6 (modify) | the seven S5 DoR backlog deltas |

**Task order (honors the sprint doc's "Capacity & sequencing").** Wave A is Task 1 alone — SK-043's verb, pure offline Python, independent of every line of prose in this sprint. It goes **first, not by preference**: Task 3's drain loop ends every task by calling `task --status …`, so writing that prose before the verb exists produces a stage that describes a command which refuses. Wave B is prose and runs in order: 2 (the stage's spine and the stub demolition) → 3 (the drain, the mapping, the halt — it appends to the section Task 2 creates) → 4 (the blocker rules — they only matter once the loop can produce a blocker). Task 5 needs 2–4. Task 6 is docs-only and independent of everything.

---

### Task 1: `task --id … --status …` — the verb that can finish a task (SK-043)

**Files:**
- Modify: `scripts/supskill_state/model.py:133-146` (rename `_parse_status` → `parse_task_status`) and `scripts/supskill_state/model.py:231` (its only call site)
- Modify: `scripts/supskill_state/commands.py` (new `record_task_status`, appended after `load_tasks`)
- Modify: `scripts/supskill_state/cli.py:20-29` (register the subparser) plus a new `_add_task` / `_cmd_task` pair
- Test: `tests/test_task_status.py` (create)

**Interfaces:**
- Consumes: `store.load_state` / `store.dump_state` / `store.append_jsonl` (`scripts/supskill_state/store.py:64-70`) / `store.now_utc_iso` (`scripts/supskill_state/store.py:73-74`) / `store.runs_dir` (`scripts/supskill_state/store.py:37-38`); `normalize_sprint_id` (`scripts/supskill_state/scratch.py:19-26`); `TaskStatus` (`scripts/supskill_state/model.py:45-51`); `StateError`.
- Produces (Tasks 3 and 4's prose call this exact CLI surface; E6's Gate 3 reads this exact trail):
  - `parse_task_status(value, where: str) -> TaskStatus` — public; raises the NEEDS_CONTEXT refusal (`scripts/supskill_state/model.py:134-139`) and the unknown-status refusal. `state_from_dict` keeps using it, so there is exactly one status vocabulary.
  - `record_task_status(task_id: str, status: str, note: str | None = None, root: Path | None = None) -> State`
  - CLI: `supskill-state task --id <SK-0xx> --status <DONE|DONE_WITH_CONCERNS|PARKED> [--note "<verbatim>"]` — exit 0 prints `recorded SK-040: DONE`; exit 1 on any refusal.
  - Trail: `.supskill/runs/<normalized-sprint-id>/tasks.jsonl`, one JSON object per line, `{"task", "status", "note", "at"}` — the sibling of `blockers.jsonl` (`scripts/supskill_state/commands.py:256`), appended **before** the state write.

**The defect being closed** (S5 DoR finding 1). `cli.py`'s subparser list is `init | show | artifact | gate | block | tasks | advance | plan-guard` (`scripts/supskill_state/cli.py:21-28`) and that is all of it. `tasks` writes `PENDING` (`scripts/supskill_state/commands.py:322-325`); `block` writes `BLOCKED` (`scripts/supskill_state/commands.py:269`); `DONE`, `DONE_WITH_CONCERNS` and `PARKED` are unreachable strings in an enum. A sprint whose every task succeeds can therefore never reach REVIEW — `advance --to REVIEW` refuses while any task is non-terminal (`scripts/supskill_state/transitions.py:39-46`) and nothing can make a successful task terminal. The last test in this task is that walk, and it is impossible on `main` today.

**Why a trail and not a schema field.** `DONE_WITH_CONCERNS` carries prose to Gate 3 (D5) and `Task` has no field for prose (`scripts/supskill_state/model.py:75-80`). The codebase already votes for the smaller move: an append-only trail, trail first and state second, exactly like `gates.jsonl` (`scripts/supskill_state/commands.py:209`) and `blockers.jsonl` (`scripts/supskill_state/commands.py:257-267`). If E6 finds a trail insufficient, adding `Task.note` later is additive. Reversible either way.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_task_status.py`:

```python
"""SK-043: the verb that can finish a task.

Before this, DONE / DONE_WITH_CONCERNS / PARKED were unreachable strings in an
enum (model.py:45-51): `tasks` writes PENDING (commands.py:322-325), `block`
writes BLOCKED (commands.py:269), and nothing wrote a status at all - so
advance --to REVIEW's all-terminal check (transitions.py:39-46) was unsatisfiable
for any task that SUCCEEDED. The last test here is the walk that was impossible.
"""

import json

import pytest

from supskill_state.cli import main
from supskill_state.commands import advance_stage, init_sprint, record_task_status
from supskill_state.errors import StateError
from supskill_state.model import Stage, Task, TaskStatus
from supskill_state.store import (
    dump_state,
    load_state,
    require_aware_utc_iso,
    runs_dir,
    state_path,
)


def _init_with_tasks(tmp_path, *ids):
    # "S5" with a capital S on purpose: the trail path must normalize it, like blockers.jsonl
    init_sprint("S5", entry="EXECUTE", root=tmp_path)
    state = load_state(state_path(tmp_path))
    state.tasks = [
        Task(id=task_id, seam="unit", provable="offline", status=TaskStatus.PENDING)
        for task_id in ids
    ]
    dump_state(state, state_path(tmp_path))


def _trail(tmp_path):
    path = runs_dir(tmp_path) / "s5" / "tasks.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _status(tmp_path, task_id):
    return next(t.status for t in load_state(state_path(tmp_path)).tasks if t.id == task_id)


def test_done_lands_in_state_and_in_the_trail_beside_blockers_jsonl(tmp_path):
    _init_with_tasks(tmp_path, "SK-040")
    record_task_status("SK-040", "DONE", root=tmp_path)

    assert _status(tmp_path, "SK-040") is TaskStatus.DONE
    lines = _trail(tmp_path)
    assert len(lines) == 1
    require_aware_utc_iso(lines[0].pop("at"), "tasks.jsonl at")
    assert lines[0] == {"task": "SK-040", "status": "DONE", "note": None}


def test_a_note_on_done_carries_the_minor_findings_rollup(tmp_path):
    _init_with_tasks(tmp_path, "SK-040")
    record_task_status("SK-040", "DONE", note="Minor: magic number in the drain loop", root=tmp_path)
    assert _trail(tmp_path)[0]["note"] == "Minor: magic number in the drain loop"


def test_done_with_concerns_requires_a_note(tmp_path):
    _init_with_tasks(tmp_path, "SK-041")
    before = state_path(tmp_path).read_bytes()
    for note in (None, "   "):
        with pytest.raises(StateError, match="requires --note"):
            record_task_status("SK-041", "DONE_WITH_CONCERNS", note=note, root=tmp_path)
    assert _trail(tmp_path) == []
    assert state_path(tmp_path).read_bytes() == before

    record_task_status("SK-041", "DONE_WITH_CONCERNS", note="the halt loop is untested", root=tmp_path)
    assert _status(tmp_path, "SK-041") is TaskStatus.DONE_WITH_CONCERNS
    assert _trail(tmp_path)[0]["note"] == "the halt loop is untested"


def test_parked_is_recordable_and_its_note_names_the_blocker(tmp_path):
    _init_with_tasks(tmp_path, "SK-042")
    record_task_status("SK-042", "PARKED", note="parked by SK-041's blocker: no live capture", root=tmp_path)
    assert _status(tmp_path, "SK-042") is TaskStatus.PARKED
    assert _trail(tmp_path)[0]["status"] == "PARKED"


@pytest.mark.parametrize(
    "status,match",
    [
        ("NEEDS_CONTEXT", "controller-loop signal"),
        ("BLOCKED", "is `block`'s transition"),
        ("PENDING", "moved TO"),
        ("SHIPPED", "unknown task status"),
    ],
)
def test_the_statuses_this_verb_refuses_write_nothing_anywhere(tmp_path, status, match):
    _init_with_tasks(tmp_path, "SK-040")
    before = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match=match):
        record_task_status("SK-040", status, root=tmp_path)
    assert _trail(tmp_path) == []
    assert state_path(tmp_path).read_bytes() == before


def test_an_unknown_id_is_a_typo_or_a_hallucination_never_a_new_task(tmp_path):
    _init_with_tasks(tmp_path, "SK-040")
    with pytest.raises(StateError, match="no task 'SK-099'"):
        record_task_status("SK-099", "DONE", root=tmp_path)
    assert _trail(tmp_path) == []
    assert [t.id for t in load_state(state_path(tmp_path)).tasks] == ["SK-040"]


def test_re_recording_appends_and_the_last_status_wins(tmp_path):
    _init_with_tasks(tmp_path, "SK-040")
    record_task_status("SK-040", "DONE", root=tmp_path)
    record_task_status("SK-040", "DONE_WITH_CONCERNS", note="reviewer reopened it", root=tmp_path)
    assert [line["status"] for line in _trail(tmp_path)] == ["DONE", "DONE_WITH_CONCERNS"]
    assert _status(tmp_path, "SK-040") is TaskStatus.DONE_WITH_CONCERNS


def test_cli_records_and_refuses_with_the_right_exit_codes(tmp_path, monkeypatch, capsys):
    _init_with_tasks(tmp_path, "SK-040")
    monkeypatch.chdir(tmp_path)
    assert main(["task", "--id", "SK-040", "--status", "DONE"]) == 0
    assert "recorded SK-040: DONE" in capsys.readouterr().out

    assert main(["task", "--id", "SK-040", "--status", "NEEDS_CONTEXT"]) == 1
    assert "controller-loop signal" in capsys.readouterr().err

    assert main(["task", "--id", "SK-040", "--status", "DONE_WITH_CONCERNS"]) == 1
    assert "requires --note" in capsys.readouterr().err


def test_the_walk_that_is_impossible_on_main_today(tmp_path):
    # PENDING -> terminal -> advance --to REVIEW. No sprint could take this walk before:
    # nothing could make a task that SUCCEEDED terminal (transitions.py:39-46).
    _init_with_tasks(tmp_path, "SK-040", "SK-041", "SK-042")
    record_task_status("SK-040", "DONE", root=tmp_path)
    record_task_status("SK-041", "DONE_WITH_CONCERNS", note="not proven - operator seam", root=tmp_path)

    with pytest.raises(StateError, match="terminal"):
        advance_stage("REVIEW", root=tmp_path)  # SK-042 is still PENDING

    record_task_status("SK-042", "PARKED", note="parked by SK-041's blocker", root=tmp_path)
    assert advance_stage("REVIEW", root=tmp_path).stage is Stage.REVIEW
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_task_status.py -v`
Expected: FAIL — `ImportError: cannot import name 'record_task_status' from 'supskill_state.commands'`.

- [ ] **Step 3: Make the status parser public (one vocabulary, one authority)**

In `scripts/supskill_state/model.py`, rename `_parse_status` (`scripts/supskill_state/model.py:133`) to `parse_task_status` — the body is unchanged:

```python
def parse_task_status(value, where: str) -> TaskStatus:
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
```

and update its only call site, inside `state_from_dict` (`scripts/supskill_state/model.py:231`):

```python
                status=parse_task_status(_require(task_raw, "status", where), f"{where}.status"),
```

The rename is the whole point: the verb must refuse `NEEDS_CONTEXT` with **the model's own message**, not a second copy of it.

- [ ] **Step 4: Implement the verb**

In `scripts/supskill_state/commands.py`, add `parse_task_status` to the `.model` import block (ruff's `I` rule sorts the lowercase names last, alphabetically before `state_to_dict`):

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
    parse_task_status,
    state_to_dict,
)
```

Append after `load_tasks` (before `advance_stage`):

```python
def record_task_status(
    task_id: str,
    status: str,
    note: str | None = None,
    root: Path | None = None,
) -> State:
    """Record an SDD-reported status for one task (SK-043).

    The missing half of the spine. DONE, DONE_WITH_CONCERNS and PARKED have been
    in TaskStatus since S1 and nothing could write them: `tasks` writes PENDING,
    `block` writes BLOCKED. So advance --to REVIEW - which refuses while any task
    is non-terminal - was unsatisfiable for any task that succeeded, and no sprint
    could ever end.

    Concerns get an append-only trail (runs/<id>/tasks.jsonl) rather than a schema
    field: trail FIRST, state SECOND, exactly like gates.jsonl and blockers.jsonl.
    Re-recording is legal and appends - last status wins in state, every attempt
    stays in the trail. Gate 3 (E6) reads the trail; nothing re-parses prose.
    """
    root = Path(root) if root is not None else Path.cwd()
    if not task_id:
        raise StateError("a status record requires a non-empty --id")
    # the model owns the vocabulary: NEEDS_CONTEXT and unknown statuses raise ITS message
    parsed = parse_task_status(status, "task --status")
    if parsed is TaskStatus.BLOCKED:
        raise StateError(
            "BLOCKED is `block`'s transition, not this verb's: a task is blocked by recording a "
            "blocker WITH its options - a conductor that could set BLOCKED with a bare status "
            "could halt with a shrug"
        )
    if parsed is TaskStatus.PENDING:
        raise StateError(
            "PENDING is where `tasks` starts every task; it is not a status a task is moved TO. "
            "Nothing in this spine walks a task backwards"
        )
    if parsed is TaskStatus.DONE_WITH_CONCERNS and not (note or "").strip():
        raise StateError(
            "DONE_WITH_CONCERNS requires --note: a concern with no text is not a concern, and "
            "Gate 3 reads this trail rather than the conductor's memory"
        )

    state = store.load_state(store.state_path(root))
    task = next((t for t in state.tasks if t.id == task_id), None)
    if task is None:
        raise StateError(
            f"no task {task_id!r} in state.json - a status must attach to a known task; "
            "this verb never creates one"
        )

    tasks_file = store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / "tasks.jsonl"
    store.append_jsonl(  # trail FIRST
        tasks_file,
        {"task": task_id, "status": parsed.value, "note": note, "at": store.now_utc_iso()},
    )
    task.status = parsed
    store.dump_state(state, store.state_path(root))  # state SECOND
    return state
```

In `scripts/supskill_state/cli.py`, register the subparser in `build_parser` (after `_add_block(subparsers)`, `scripts/supskill_state/cli.py:25`):

```python
    _add_block(subparsers)
    _add_task(subparsers)
    _add_tasks(subparsers)
```

and add the pair (before `_add_tasks`):

```python
def _add_task(subparsers) -> None:
    sub = subparsers.add_parser(
        "task",
        help="record one task's SDD-reported status (DONE|DONE_WITH_CONCERNS|PARKED)",
    )
    sub.add_argument("--id", required=True, dest="task_id", help="the story id, e.g. SK-041")
    sub.add_argument(
        "--status",
        required=True,
        help="DONE | DONE_WITH_CONCERNS | PARKED (BLOCKED belongs to `block`; NEEDS_CONTEXT is not a state)",
    )
    sub.add_argument(
        "--note",
        help="required for DONE_WITH_CONCERNS (the concern, verbatim); on DONE it carries the "
             "Minor-findings roll-up; on PARKED it names the blocker that parked the task",
    )
    sub.set_defaults(func=_cmd_task)


def _cmd_task(args) -> int:
    state = commands.record_task_status(args.task_id, args.status, note=args.note)
    task = next(t for t in state.tasks if t.id == args.task_id)
    print(f"recorded {task.id}: {task.status.value}")
    return 0
```

`--status` deliberately takes a free string rather than argparse `choices`: a refusal must arrive as `supskill-state: refused: … NEEDS_CONTEXT is a controller-loop signal …` on exit 1, not as argparse's exit-2 usage error. The existing `except StateError` in `main` (`scripts/supskill_state/cli.py:170-174`) already does the rest.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_task_status.py -v && uv run pytest && uv run ruff check`
Expected: all PASS — 208 baseline + the new tests. `tests/test_demo.py:53-65` (no module outside `store.py` opens a file for writing) stays green: `record_task_status` writes only through `store`.

- [ ] **Step 6: Commit**

```bash
git add scripts/supskill_state/model.py scripts/supskill_state/commands.py \
        scripts/supskill_state/cli.py tests/test_task_status.py
git commit -m "feat: supskill-state task --status - the verb that can finish a task, with its append-only trail (SK-043)"
```

---

### Task 2: The EXECUTE stage exists — stub demolition, branch check, scratch, dispatch discipline (SK-040)

**Files:**
- Modify: `skills/supskill/SKILL.md:94` (the dispatch table's EXECUTE row), `skills/supskill/SKILL.md:97-98` (the "honest stubs" paragraph), `skills/supskill/SKILL.md:174-175` (Gate 1's approval step — see below), `skills/supskill/SKILL.md:261-262` (Gate 2's approval step), and a new `## The EXECUTE stage` section inserted after the Gate 2 section, before `## Reference` (`skills/supskill/SKILL.md:275-278`) — frontmatter untouched
- Test: `tests/test_execute_prose.py` (create)

**Interfaces:**
- Consumes: `show --json` (`sprint.scratch`, `artifacts.dev_plan`, `tasks[]`); SDD's three scripts, by name — `sdd-workspace`, `task-brief PLAN_FILE N [OUTFILE]`, `review-package BASE HEAD [OUTFILE]`; SDD's two prompt templates, `implementer-prompt.md` and `task-reviewer-prompt.md`.
- Produces: the `## The EXECUTE stage` section with two subsections — `### Before the first dispatch` and `### The dispatch discipline`. Task 3 appends `### The drain` and `### The halt` **to this same section**; Task 4 appends `### The blocker rules`. The section's own last line is a pointer that Task 3 replaces.

**Three surfaces call EXECUTE a stub, and all three change** (S5 DoR finding 9). The dispatch-table row (`skills/supskill/SKILL.md:94`) is the obvious one. The paragraph beneath it (`skills/supskill/SKILL.md:97-98`) says "EXECUTE and REVIEW are honest stubs". And the one that actually bites: Gate 2's approval step (`skills/supskill/SKILL.md:261-262`) tells the conductor to "continue at the `EXECUTE` dispatch row (E5's honest stub: it reports and stops — do not improvise EXECUTE)" — and Gate 2's approval is the **only path that reaches EXECUTE**. Miss it and this sprint ships a stage the conductor is instructed not to run.

**A fourth surface, found while writing this plan and not in the sprint doc:** Gate 1's approval step still says "continue at the `PLAN` dispatch row (E4's honest stub: it reports and stops — do not improvise PLAN)" (`skills/supskill/SKILL.md:174-175`). PLAN shipped in S4 (`5fd62d1`) and this line was never updated — it is finding 9's exact failure, one stage back, live on `main` right now: the only path that reaches PLAN tells the conductor not to run it. It is one line, it is the same class of defect, and leaving it for a later sprint would mean shipping the fix for EXECUTE while the identical bug sits two screens above it. It is fixed here, and the Step 1 test is what forbids its return. The scan in Step 1 fails until **all four** stub surfaces are gone.

**The design decision this task locks in, stated for the operator** (S5 DoR finding 3): **the conductor is the SDD controller**, running SDD's loop in its own session. "Dispatch SDD" reads naturally as "hand SDD to a subagent" and that is the wrong placement: the controller loop is where every status, blocker and concern appears, and a subagent controller can neither run `supskill-state` (invariant 3) nor ask the operator anything (D4) — while SDD itself instructs it to "escalate to the human" it does not have. The fresh-context boundary the product promises stays exactly where SDD puts it: per task. This is the smaller, reversible choice — if it proves wrong, what moves is *where the loop runs*, not what the verbs do.

**Executor skills:** `superpowers:writing-skills`. **Read the live `superpowers:subagent-driven-development` SKILL.md and its three `scripts/` before writing a line of this section** — the version composed here is superpowers **6.1.1**, and its Model Selection, Handling Implementer Status, File Handoffs, Durable Progress and Red Flags sections are the contract. If the installed version has moved, re-read it. The PLAN section (`skills/supskill/SKILL.md:182-242`) is the shape to copy.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_execute_prose.py`:

```python
"""E5's prose surfaces: the EXECUTE stage exists, and nothing still calls it a stub.

The authoritative check is the reviewer reading the section; these are tripwires
for the regressions that would silently ship a stage nobody can reach (S5 DoR
finding 9) or an implementer that can mark its own work done (invariant 3, F-5).
"""

from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "supskill"
SKILL = SKILL_DIR / "SKILL.md"


def execute_section() -> str:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("## The EXECUTE stage")
    rest = text.index("\n## ", start + 1)
    return text[start:rest]


def test_the_dispatch_table_and_gate_2_both_route_into_the_real_stage():
    text = SKILL.read_text(encoding="utf-8")
    assert "| `EXECUTE` | Follow **The EXECUTE stage** below. |" in text
    assert "## The EXECUTE stage" in text
    # Gate 2's approval is the ONLY path that reaches EXECUTE (S5 DoR finding 9)
    assert "`approved` → `advance --to EXECUTE` → continue at **The EXECUTE stage**" in text


def test_gate_1_routes_into_the_plan_stage_that_shipped_in_s4():
    # the same defect one stage back, live on main until this sprint: Gate 1's approval is
    # the only path that reaches PLAN, and it still called PLAN an honest stub
    assert "`approved` → `advance --to PLAN` → continue at **The PLAN stage**" in SKILL.read_text(
        encoding="utf-8"
    )


def test_no_stub_language_survives_anywhere_except_for_review():
    for path in sorted(SKILL_DIR.rglob("*.md")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            assert "improvise EXECUTE" not in line, f"{path.name}:{number}: {line!r}"
            if "not implemented yet" in line or "honest stub" in line:
                assert "REVIEW" in line, f"{path.name}:{number}: {line!r}"


def test_the_execute_section_forbids_a_dispatched_agent_writing_state():
    # an implementer that can write state can mark its own work done (F-5)
    assert "No dispatched agent runs `supskill-state`" in execute_section()


def test_the_execute_section_refuses_sdds_progress_ledger():
    # keyed by task number; task numbers restart every sprint (S5 DoR finding 2)
    section = execute_section()
    assert "Do not read or write `.superpowers/sdd/progress.md`" in section
    assert "`tasks[]` is the ledger" in section


def test_the_execute_section_prepares_the_scratch_before_the_first_dispatch():
    # passing OUTFILE is exactly what skips sdd-workspace (S5 DoR finding 8)
    section = execute_section()
    assert "sdd-workspace" in section
    assert "mkdir -p <scratch>" in section


def test_the_execute_section_records_base_and_never_derives_it():
    section = execute_section()
    assert "Never `HEAD~1`" in section
    assert "git merge-base" in section  # the final whole-branch review gets its own package


def test_the_execute_section_names_a_model_on_every_dispatch():
    assert "Every dispatch names its model explicitly" in execute_section()


def test_the_execute_section_stops_before_dispatching_on_the_default_branch():
    section = execute_section()
    assert "git rev-parse --abbrev-ref HEAD" in section
    assert "git switch -c" in section


def test_supskill_contributes_no_fourth_prompt_template():
    # the implementer and reviewer prompts are SDD's; supskill has no opinion (D1)
    assert not (SKILL_DIR / "references" / "execute-prompt.md").exists()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_execute_prose.py -v`
Expected: every test FAILs — `ValueError: substring not found` from `execute_section()` (there is no `## The EXECUTE stage`), and `test_no_stub_language_survives_anywhere_except_for_review` fails on `skills/supskill/SKILL.md:94`'s "not implemented yet", `skills/supskill/SKILL.md:97`'s "honest stubs", `skills/supskill/SKILL.md:175`'s "E4's honest stub" and `skills/supskill/SKILL.md:262`'s "improvise EXECUTE".

- [ ] **Step 3: Demolish the four stub surfaces**

In `skills/supskill/SKILL.md`, the dispatch table's EXECUTE row (`skills/supskill/SKILL.md:94`) becomes:

```markdown
| `EXECUTE` | Follow **The EXECUTE stage** below. |
```

The paragraph under the table (`skills/supskill/SKILL.md:97-98`) becomes:

```markdown
REVIEW is a stub until E6 lands — do not improvise it. An implemented stage
follows its section below exactly.
```

(The words "honest stub" leave the file entirely; the test in Step 1 allows them
only on a line that also names REVIEW, and this paragraph no longer needs them.)

Gate 1's approval step (`skills/supskill/SKILL.md:174-175`) — stale since S4 shipped
PLAN — becomes:

```markdown
4. `approved` → `advance --to PLAN` → continue at **The PLAN stage** (below).
```

Gate 2's approval step (`skills/supskill/SKILL.md:261-262`) becomes:

```markdown
4. `approved` → `advance --to EXECUTE` → continue at **The EXECUTE stage**
   (below). That transition also re-checks that `tasks[]` is non-empty; a
   refusal there is reported verbatim and stops the run.
```

- [ ] **Step 4: Write the stage's spine**

Insert into `skills/supskill/SKILL.md` after the Gate 2 section, before `## Reference`:

```markdown
## The EXECUTE stage

**You are the controller.** Invoke `superpowers:subagent-driven-development` in
**your own session** and run its loop yourself — that is the same-session mode
SDD's own decision tree names. Do not hand the loop to a subagent: the loop is
where every status, blocker and concern appears, and a subagent can neither run
`supskill-state` (invariant 3) nor ask the operator anything (D4). The
fresh-context boundary is still there — SDD puts it per *task*, which is where
it belongs.

Compose SDD verbatim (D1): its implementer prompt, its task-reviewer prompt, its
review loop, its fix loop, its model selection. supskill re-implements none of
it and adds no prompt template of its own. What supskill adds is the discipline
below. **Read SDD's SKILL.md and its three `scripts/` before the first
dispatch** — Model Selection, Handling Implementer Status, File Handoffs,
Durable Progress and Red Flags are the contract you are composing.

### Before the first dispatch — four checks, in this order

1. **The branch check.** Run `git rev-parse --abbrev-ref HEAD`. If it is the
   repo's default branch, **stop before dispatching anything**: report that
   EXECUTE writes commits and will not write them to the default branch, and name
   `git switch -c <branch>` as the operator's move. Do not create, switch, or
   delete a branch yourself — the same restraint that keeps `--archive` out of
   your hands. (SDD forbids implementing on main without explicit consent, and a
   subagent cannot give it.)
2. **Prepare the scratch.** Run SDD's `sdd-workspace` script once — it creates
   `.superpowers/sdd/` and writes the self-ignoring `.gitignore` that keeps every
   sprint's scratch out of `git status`. Then `mkdir -p <scratch>`, where
   `<scratch>` is `sprint.scratch` from `show --json`. **Neither is optional.**
   `task-brief` writes its `OUTFILE` with a plain shell redirect and never
   creates the parent, so the first brief dies on a missing directory; and
   passing `OUTFILE` is exactly what skips `sdd-workspace`'s own call, so a
   target repo that does not already ignore `.superpowers/` will let an
   implementer's `git add -A` commit this sprint's briefs and diffs.
3. **Read the plan.** `artifacts.dev_plan` from `show --json` is the plan, and
   the only authority for it. Missing from disk → report that and stop.
4. **SDD's pre-flight plan review.** Scan the plan once for conflicts, as SDD
   requires. SDD batches them into one question to a human; you have none. Every
   conflict becomes a blocker on the task it affects — with real options, per the
   blocker rules below — and that task is parked. If the scan blocks every task,
   the drain runs nothing and the halt is immediate. That is correct, and it is
   not a crash.

### The dispatch discipline — every task, no exceptions

- **Every scratch path is passed explicitly, and derived, never typed**
  (invariant 4). `<scratch>` is `sprint.scratch` from `show --json`:
  - brief: `task-brief <dev_plan> <N> <scratch>/task-<N>-brief.md`
  - report: `<scratch>/task-<N>-report.md` — named after the brief, per SDD's
    File Handoffs rule, so re-reading a task's outcome is one `Read`, never a
    re-dispatch
  - review package: `review-package <BASE> HEAD <scratch>/review-<N>.diff`
- **`BASE` is recorded, never derived.** Before each implementer dispatch, run
  `git rev-parse HEAD` and keep that SHA as the task's `BASE`. **Never `HEAD~1`**
  — SDD says in as many words that it silently drops all but the last commit of a
  multi-commit task. The final whole-branch review gets its own package:
  `review-package $(git merge-base <default-branch> HEAD) HEAD <scratch>/review-final.diff`.
  `sprint.branch` is optional at init and is not the authority here — `git` is.
- **Every dispatch names its model explicitly.** An omitted model silently
  inherits this session's — usually the most capable and most expensive one.
  *Which* model per role is SDD's Model Selection section's call, not this
  skill's; do not restate it, follow it.
- **The ledger is `state.json`.** Do not read or write
  `.superpowers/sdd/progress.md`. It is keyed by task number, task numbers
  restart every sprint, and its contract is "listed complete = do not
  re-dispatch" — so a ledger left by one sprint tells the next that its Task 1 is
  already finished. `tasks[]` is the ledger: sprint-scoped by construction, and
  the file you resume from (invariant 5). A stale `progress.md` on disk is
  ignored and named once in the halt report, so the operator can delete it.
- **No dispatched agent runs `supskill-state`** or touches `.supskill/`
  (invariant 3). SDD's implementers commit code; you record every status, every
  blocker and every advance yourself — **after** the task review, never on an
  implementer's word alone. An implementer that can write state can mark its own
  work done.

The drain that uses all of this is the next subsection.
```

- [ ] **Step 5: Run the tests and the prose self-checks**

Run: `uv run pytest tests/test_execute_prose.py -v && uv run pytest && uv run ruff check`
Expected: `test_the_execute_section_forbids_a_dispatched_agent_writing_state`, `…refuses_sdds_progress_ledger`, `…prepares_the_scratch…`, `…records_base…`, `…names_a_model…`, `…default_branch`, `…no_fourth_prompt_template`, `…route_into_the_real_stage` and `…no_stub_language…` all PASS. Full suite green, including `tests/test_skill_frontmatter.py::test_body_stays_under_500_lines` (the body grows from 272 to roughly 340).

Run: `grep -rn "improvise EXECUTE\|improvise PLAN\|not implemented yet\|honest stub" skills/supskill/`
Expected: exactly one hit — REVIEW's dispatch-table row (`REVIEW is not implemented yet`). Nothing else.

- [ ] **Step 6: Commit**

```bash
git add skills/supskill/SKILL.md tests/test_execute_prose.py
git commit -m "feat: the EXECUTE stage exists - conductor as SDD controller, scratch prepared, BASE recorded; the four stub surfaces (incl. Gate 1's stale PLAN stub) are gone (SK-040)"
```

---

### Task 3: The drain, the status mapping, and the halt (SK-041, SK-043)

**Files:**
- Modify: `skills/supskill/SKILL.md` — replace the pointer line at the end of `## The EXECUTE stage` (Task 2's last line, "The drain that uses all of this is the next subsection.") with two new subsections, `### The drain` and `### The halt`, still inside the same section and still before `## Reference`
- Test: `tests/test_execute_prose.py` (extend)

**Interfaces:**
- Consumes: Task 2's `## The EXECUTE stage` section and its dispatch discipline; Task 1's CLI surface — `task --id <SK-0xx> --status <DONE|DONE_WITH_CONCERNS|PARKED> [--note "<verbatim>"]`; the existing `block --task --kind --found --option --option --recommend` (`scripts/supskill_state/commands.py:218-271`); `tasks[]` with `id`, `seam`, `provable`, `status` (`scripts/supskill_state/model.py:75-80`).
- Produces: the drain loop, the four-row status mapping table, and the halt report's contents. Task 4 appends `### The blocker rules` after `### The halt`; E6's Gate 3 batches exactly what the halt report lists.

**The two definitions the backlog never gave** (S5 DoR findings 4 and 5), both settled here in the smaller, reversible direction:

1. **"Downstream of a blocker" is not computable from state.** `Task` carries `id`, `seam`, `provable`, `status` and nothing else (`scripts/supskill_state/model.py:75-80`) — there is no dependency edge anywhere, and inventing one means a schema change plus a second parser over the dev plan. So **downstream is discovered, not predicted**: the drain runs in plan order; a blocked task stops its *chain*, not the drain; a later task that itself comes back `BLOCKED` for the **same root cause** is recorded `PARKED`, not blocked a second time. Cost: at most one wasted implementer dispatch per genuinely-dependent task. The operator can overrule this at Gate 1 by requiring an explicit `depends:` declaration in the plan instead.
2. **`provable` is not a run/skip filter.** Every non-blocked, non-parked task runs. `provable` decides what the halt report *claims*: `offline` → proven, with the test command and its output; `operator` → "implemented and reviewed; **not proven** — verify by hand". Without it the conductor would report a journey-seam story as green because its unit tests passed (F-5, one level up).

**Executor skills:** `superpowers:writing-skills`. Degrees of freedom: the CLI calls, the scratch paths and the mapping table are **exact**. "What counts as the same root cause" is judgment — the prose says so rather than pretending to specify it. Do not invent a `depends:` field; do not add a parser.

- [ ] **Step 1: Extend the tests (failing first)**

Append to `tests/test_execute_prose.py`:

```python
def test_the_drain_maps_all_four_sdd_statuses_onto_a_verb():
    section = execute_section()
    assert "`task --id <SK-0xx> --status DONE`" in section
    assert "--status DONE_WITH_CONCERNS --note" in section
    assert "`block --task <SK-0xx>" in section
    assert "re-dispatch the same task **once**" in section  # NEEDS_CONTEXT is bounded


def test_the_drain_writes_each_status_before_the_next_dispatch():
    assert "before the next dispatch begins" in execute_section()


def test_the_drain_skips_terminal_tasks_and_resumes_from_state_alone():
    section = execute_section()
    assert "never re-dispatched" in section
    assert "the first `PENDING` task" in section


def test_downstream_is_discovered_not_predicted():
    section = execute_section()
    assert "same root cause" in section
    assert "--status PARKED" in section


def test_provable_gates_the_claim_and_not_the_run():
    section = execute_section()
    assert "**not proven** — verify by hand" in section
    assert "every task runs" in section


def test_the_halt_happens_exactly_once_and_advances_nothing():
    section = execute_section()
    assert "**exactly once**" in section
    assert "Do not advance to REVIEW" in section
    assert "A halt is the target shape, not an error" in section


def test_sdds_two_remaining_human_decisions_become_blockers_or_resolutions():
    section = execute_section()
    assert "plan-mandated" in section
    assert "cannot verify from diff" in section


def test_the_drain_never_guesses():
    section = execute_section()
    assert "do not invent a blocker's options" in section
    assert "without the task review" in section
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_execute_prose.py -v`
Expected: the eight new tests FAIL with `AssertionError` (the section exists but says nothing about the drain); Task 2's tests still PASS.

- [ ] **Step 3: Write the drain and the halt**

In `skills/supskill/SKILL.md`, **replace** the line

```markdown
The drain that uses all of this is the next subsection.
```

with:

```markdown
### The drain

In plan order, for every task in `tasks[]` whose status is `PENDING`:

1. Record `BASE` (`git rev-parse HEAD`), write the brief, dispatch a fresh
   implementer, then the task reviewer, then a fix subagent on any Critical or
   Important finding. That is SDD's cycle, unchanged.
2. Map what SDD reported onto the spine, **before the next dispatch begins** — a
   `/clear` or a crash mid-drain then costs at most one task's work:

   | SDD reports | You run |
   |---|---|
   | `DONE` | `task --id <SK-0xx> --status DONE` — `--note` carries the task's Minor-findings roll-up, which the final whole-branch review reads. A roll-up nobody reads is a silent discard. |
   | `DONE_WITH_CONCERNS` | `task --id <SK-0xx> --status DONE_WITH_CONCERNS --note "<the concern, verbatim>"`. The drain continues; the concern surfaces in the halt batch. |
   | `BLOCKED` | `block --task <SK-0xx> --kind … --found … --option "(a) …" --option "(b) …" --recommend "(a) — because …"`, which flips the status itself. |
   | `NEEDS_CONTEXT` | Supply the missing context and re-dispatch the same task **once**. Still `NEEDS_CONTEXT` → `block`. It is a controller-loop signal, not a resting state, and there is no unbounded loop anywhere in this stage. |

3. **The join is the plan task's heading** — `### Task N: <what> (SK-0xx)`, the
   one required by PLAN and validated when `tasks` loaded. This stage adds no
   parser. A heading marked `(process)` serves no story and gets no status call.
   Where several plan tasks serve one story: the story is `DONE` only when **all**
   of them are; any `DONE_WITH_CONCERNS` among them makes the story
   `DONE_WITH_CONCERNS`; any blocker among them blocks the story.
4. A task already terminal in `tasks[]` is skipped and **never re-dispatched** —
   SDD's ledger rule, on our ledger. This is also the resume path: re-invoking
   `/supskill run <sprint-id>` restarts the drain at the first `PENDING` task,
   read from `state.json` alone.

**Downstream is discovered, not predicted.** A blocker stops its chain, not the
drain. A later task that comes back `BLOCKED` for the **same root cause** — its
report names the already-blocked story, or the artifact that story was to produce
— is recorded `task --id <SK-0xx> --status PARKED --note "<the blocker that
parked it>"`, not blocked a second time. One blocker per root cause; the options
are enumerated once. What counts as the same root cause is your judgment, and
this prose does not pretend otherwise.

**`provable` gates the claim, not the run.** Every task runs — `provable` is not
a skip filter. It decides what the halt report may claim about a finished task:
an `offline` task is *proven*, with its test command and that command's output;
an `operator` task is *implemented and reviewed, **not proven** — verify by hand*.

**SDD's two remaining "ask the human" points become blockers, not guesses.**

- A reviewer finding labelled **plan-mandated** — or any finding that
  contradicts the plan's text — is the human's decision in SDD. Do not dismiss
  the finding because the plan mandates it, and do not dispatch a fix that
  contradicts the plan. Record a blocker whose `--found` is the finding beside
  the plan text that mandates it, and whose options are the two courses that
  actually exist: fix it against the plan, or keep the plan and carry the
  finding.
- A reviewer's "⚠️ cannot verify from diff" item is the opposite case: SDD
  requires the **controller** to resolve it, and you hold the plan and the
  cross-task context the reviewer lacks. Resolve it. If you genuinely cannot,
  block. An empty answer is never a decision.

**Never guess.** Do not skip a task because it looks hard; do not mark a task
`DONE` without the task review, on an implementer's word alone; do not
re-dispatch a task with unchanged input; and do not invent a blocker's options. A
situation with no legal move is a blocker — and a blocker halts the chain, never
the drain.

### The halt

The drain ends when no `PENDING` task remains. Then, **exactly once**, report one
batch:

- **per task:** its status, its commits, and what its `provable` class does and
  does not claim (above);
- **every blocker:** its `found`, its `options[]`, and its `recommend`;
- **every parked task:** with the blocker that parked it;
- **every `DONE_WITH_CONCERNS` concern:** verbatim;
- **any stale `.superpowers/sdd/progress.md`** found on disk: named once, so the
  operator can delete it.

Then stop. Do not advance to REVIEW, do not open a gate, and do not ask a
question — Gate 3 is E6's, and until E6 lands the halt report *is* this stage's
deliverable.

**A halt is the target shape, not an error.** A sprint that drains 4 of 6 tasks
and halts with two blockers is a **successful** EXECUTE. Say so in those words.
Do not apologize for it, and do not try once more.
```

- [ ] **Step 4: Run the tests and the prose self-checks**

Run: `uv run pytest tests/test_execute_prose.py -v && uv run pytest && uv run ruff check`
Expected: all PASS. The SKILL.md body lands near 400 lines — still under the 500-line cap asserted by `tests/test_skill_frontmatter.py:75-77`.

Run: `grep -n "supskill-state\|task --id\|block --task" skills/supskill/SKILL.md`
Expected: every `task --id` and `block --task` hit is inside the EXECUTE section, and no line anywhere instructs a *dispatched agent* to run a state verb.

- [ ] **Step 5: Commit**

```bash
git add skills/supskill/SKILL.md tests/test_execute_prose.py
git commit -m "feat: the drain, the SDD status mapping, and a halt that happens once (SK-041, SK-043)"
```

---

### Task 4: The blocker is a decision, not a shrug (SK-042)

**Files:**
- Modify: `skills/supskill/SKILL.md` (append `### The blocker rules` at the end of `## The EXECUTE stage`, after `### The halt`, before `## Reference`)
- Test: `tests/test_block.py` (extend — one test), `tests/test_execute_prose.py` (extend — two tests)

**Interfaces:**
- Consumes: `record_blocker`'s existing validation (`scripts/supskill_state/commands.py:228-253`) and the S9a fixture already on disk (`tests/test_block.py:19-30`); Task 3's drain, which is what produces a blocker in the first place.
- Produces: the conductor's blocker-authoring rules. Nothing else consumes them — they are read by the operator and by the reviewer.

**This story shrank, and the shrink is the finding** (S5 DoR finding 6): **the enforcement already shipped in S1.** `record_blocker` refuses fewer than two options, an unlabelled option, a duplicate label, a `recommend` that references none of them, and a task it cannot find (`scripts/supskill_state/commands.py:228-253`); it writes the trail before the state and flips the task to `BLOCKED` (`scripts/supskill_state/commands.py:257-269`). Nothing in the CLI is missing. What is missing is the **conductor's** half: turning an implementer's `BLOCKED` report into options that are genuinely different courses of action rather than three phrasings of "ask the operator". That is prose plus one fixture assertion, and padding it would be dishonest.

**The fixture is blinkebot's real S9a blocker, verbatim, and it is already in the suite** (`tests/test_block.py:19-30`). What no test asserts yet is the property the story exists for: its *recommended* option — `(a)` — was **wrong**, and option `(c)` was right. A blocker format in which a wrong recommendation misleads the operator has failed at exactly the moment it mattered. Take the fixture as it stands; do not improve it.

**Executor skills:** `superpowers:writing-skills`, `fullstack-dev-skills:python-pro` (for the one test).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_block.py`:

```python
def test_a_wrong_recommendation_still_leaves_the_operator_the_right_option(tmp_path):
    # S9a's recommendation was WRONG - option (c) was the correct one (D5). The record
    # must survive validation with (c) intact and reachable, in state AND in the trail:
    # a blocker whose wrong recommendation buries the right option has failed at exactly
    # the moment it mattered.
    _init_with_task(tmp_path)
    record_blocker(S9A["task"], S9A["kind"], S9A["found"], S9A["options"], S9A["recommend"], root=tmp_path)

    right_option = "(c) re-scope: the drift hypothesis may be wrong"
    blocker = load_state(state_path(tmp_path)).blockers[0]
    assert blocker.recommend.startswith("(a)")  # the recommendation the operator overruled
    assert [option[:3] for option in blocker.options] == ["(a)", "(b)", "(c)"]
    assert right_option in blocker.options
    assert right_option in _blocker_lines(tmp_path)[0]["options"]
```

Append to `tests/test_execute_prose.py`:

```python
def test_the_blocker_rules_forbid_a_fabricated_second_option():
    section = execute_section()
    assert "materially different courses of action" in section
    assert "Never fabricate an option" in section
    assert "what was **observed**" in section


def test_the_conductor_never_acts_on_its_own_recommendation():
    assert "advice, not a decision" in execute_section()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_block.py tests/test_execute_prose.py -v`
Expected: the two `test_execute_prose.py` tests FAIL with `AssertionError` (the blocker rules are not written yet). `test_a_wrong_recommendation_still_leaves_the_operator_the_right_option` **passes immediately** — that is not a mistake: it is the S5 DoR finding made mechanical. S1's `record_blocker` already preserves the record; this test is the regression lock that says so out loud, and it belongs in the suite regardless of whether it was ever red. State that in the commit message rather than manufacturing a red bar.

- [ ] **Step 3: Write the blocker rules**

Append to `skills/supskill/SKILL.md`, at the end of `## The EXECUTE stage` (after `### The halt`, before `## Reference`):

```markdown
### The blocker rules

The CLI already refuses a blocker with fewer than two options, an unlabelled
option, a duplicate label, or a `--recommend` that names none of them. It cannot
refuse three phrasings of the same option. That part is yours.

- Options are **materially different courses of action** — do X / do Y / stop and
  change the plan — each labelled `(a) …`, `(b) …`, `(c) …`.
- **Never fabricate an option** to satisfy the two-option floor. If there is
  genuinely only one move, there is no decision to escalate, and the task was not
  blocked.
- `--found` is what was **observed**, never what was inferred from it.
- `--recommend` names one option and says why in the same breath.
- The recommendation is **advice, not a decision**. You never act on your own
  recommendation, at any point, for any reason — you halt (D4: escalation is
  out-of-band, always). A wrong recommendation must still leave the operator the
  right option: blinkebot's S9a blocker is on record as exactly that case — the
  recommended option was wrong and option (c) was right.
```

- [ ] **Step 4: Run the tests, the suite, and lint**

Run: `uv run pytest tests/test_block.py tests/test_execute_prose.py -v && uv run pytest && uv run ruff check`
Expected: all PASS.

Run: `grep -in "auto-approve\|--yes\|continue anyway" skills/supskill/SKILL.md`
Expected: no hits. Nothing anywhere offers a way past a blocker or a gate.

- [ ] **Step 5: Commit**

```bash
git add skills/supskill/SKILL.md tests/test_block.py tests/test_execute_prose.py
git commit -m "feat: blocker authoring rules - materially different options, a recommendation the conductor never acts on (SK-042)"
```

---

### Task 5: The sprint demo checklist (process)

**Files:**
- Create: `.superpowers/sdd/s5/demo-checklist.md` (sprint scratch — gitignored by `.gitignore:9`; no commit)

**Interfaces:**
- Consumes: everything — the whole E5 conductor, installed or loadable as a plugin, plus real tokens and real production code.
- Produces: the script the operator runs. **The sprint does not close on offline green.** The offline suite proves the `task` verb, its refusals and its trail. It cannot prove that the conductor *actually* halts instead of guessing, *actually* parks instead of double-blocking, or *actually* refuses to mark a task done on an implementer's word. Only the demo can. This is the first sprint where a green suite and a broken product are perfectly compatible.

- [ ] **Step 1: Write the demo checklist**

Create `.superpowers/sdd/s5/demo-checklist.md`:

```markdown
# S5 demo — EXECUTE in anger (operator-run, real tokens, first production code)

Run in THIS repo, at the repo root. Expected outcomes are written before running;
any mismatch fails the demo. The sprint being driven is **S6** (E6 — REVIEW/PAR +
Gate 3), so the artifact is a partly-implemented E6 the operator wanted anyway.

- [ ] 1. Preflight: working tree clean; no `.supskill/` at the repo root (or
      archive an old run deliberately, by hand). **You are on a feature branch,
      not the default branch** — if you are not, step 5 must stop the run, and
      that is itself a passing check.
- [ ] 2. `/supskill run s6 --backlog docs/plans/sprints/backlog-01/backlog.md --slug review-par`
      → SCOPE + REFINE + Gate 1 + PLAN + Gate 2. S3's and S4's stages are now
      load-bearing for a stage they did not build. Approve both gates with real
      words, after actually reading the artifacts.
- [ ] 3. Before the first dispatch, the conductor ran `sdd-workspace` and
      `mkdir -p .superpowers/sdd/s6/`. Verify: the directory exists and
      `.superpowers/sdd/.gitignore` contains `*`.
- [ ] 4. The conductor did **not** read `.superpowers/sdd/progress.md`. The stale
      one from S1–S4 is still there; it must be named in the halt report and
      otherwise ignored.
- [ ] 5. **The branch check.** If HEAD is the default branch, the run stops here
      naming `git switch -c` and running nothing. That is a pass, not a failure.
- [ ] 6. EXECUTE drains S6's plan for real: implementers land E6's stories on the
      branch, a task reviewer runs after each, and each status is recorded as it
      lands. Watch `.supskill/runs/s6/tasks.jsonl` grow, one line per task.
- [ ] 7. **`/clear`** mid-drain — the context is now genuinely empty (invariant 5).
- [ ] 8. `/supskill run s6` → resumes at the first `PENDING` task from
      `state.json` alone. **No completed task is re-dispatched.** This is the
      single most expensive failure SDD names, and our ledger is what prevents it.
- [ ] 9. The run halts **once**, with the whole batch: every task's status and its
      honest `provable` claim, every blocker with its options and recommendation,
      every parked task with its cause, every concern verbatim. It does not
      advance to REVIEW and it does not ask a question.
- [ ] 10. **If a blocker appeared, that is the demo SUCCEEDING.** Read its options.
      Are they materially different courses of action, or three phrasings of "ask
      the operator"? Could you make the decision from the batch alone? That answer
      is this sprint's single most important data point.
- [ ] 11. Verify no dispatched agent wrote state: `git log` on the branch shows
      implementer commits, and **no commit touches `.supskill/`**.
- [ ] 12. Verify no implementer's scratch was committed:
      `git show --stat` on each task's commits contains no `.superpowers/` path.
- [ ] 13. Record below, verbatim: pass/fail per step, whether the conductor ever
      guessed, whether it halted or stalled, and your honest read on the code the
      drain produced. Steps 8, 10 and 11 are the ones that decide whether E5 is
      real.
```

- [ ] **Step 2: Hand it to the operator**

Report: the demo checklist is at `.superpowers/sdd/s5/demo-checklist.md`; it is the exit criterion for SK-040/041/042's operator-provable acceptance; the sprint stays open until the operator runs it. No commit — the scratch dir is gitignored by design (`.gitignore:9`).

---

### Task 6: Apply the S5 DoR backlog deltas (process)

**Files:**
- Modify: `docs/plans/sprints/backlog-01/backlog.md`

**Interfaces:**
- Consumes: nothing from other tasks (docs-only; the operator commissioning this plan is the acceptance the sprint doc's "once the operator accepts" clause names).
- Produces: a backlog that matches what S5 actually committed — the seven deltas from the sprint doc's "Backlog deltas — proposed" section.

- [ ] **Step 1: Re-point SK-040 (5 → 7) and re-scope its row**

Replace the SK-040 row (`docs/plans/sprints/backlog-01/backlog.md:132`):

```markdown
| SK-040 | Dispatch `superpowers:subagent-driven-development` **from the conductor, which IS the SDD controller** — a subagent controller could neither record state (invariant 3) nor escalate to a human it does not have (D4). Every scratch artifact goes under the derived `sprint.scratch` via the `OUTFILE` override `task-brief` / `review-package` accept. S5 DoR: SDD's progress ledger has **no** override and is keyed by task number, reopening the D8 collision across sprints — so `state.json`'s `tasks[]` is the ledger and `progress.md` is never touched; **passing `OUTFILE` skips `sdd-workspace`**, the only thing that creates the scratch dir and git-ignores it, so the first `task-brief` dies on a missing parent and a target repo commits SDD's scratch; `BASE` is recorded before each dispatch (never `HEAD~1`); every dispatch names its model; the default-branch check stops the run before any dispatch; and **three** SKILL.md surfaces called EXECUTE a stub, including Gate 2's approval step — the only path that reaches the stage. | 7 | M | ☐ |
```

- [ ] **Step 2: Re-point SK-042 (3 → 2) and record why**

Replace the SK-042 row (`docs/plans/sprints/backlog-01/backlog.md:134`):

```markdown
| SK-042 | Blocker records carry `options[]` + `recommend`. blinkebot's real S9a blocker is the fixture: the *recommended* option was wrong and option (c) was right — a bare "blocked" would have misled the operator. S5 DoR re-pointed this **down**: every structural rule shipped in S1 (`commands.py:228-253` — two-option floor, labelled options, a `recommend` that must reference one, a task that must exist). What remains is the conductor's authoring discipline and the fixture assertion that a wrong recommendation still leaves (c) reachable. Points moved to where the risk actually is (SK-043). | 2 | M | ☐ |
```

- [ ] **Step 3: Re-point SK-043 (3 → 6) and re-classify it from mapping to enforcement**

Replace the SK-043 row (`docs/plans/sprints/backlog-01/backlog.md:135`):

```markdown
| SK-043 | Map SDD's `DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT` onto task status. `DONE_WITH_CONCERNS` proceeds but carries the concern to Gate 3. (**D5**) The join is the `SK-0xx` id in each plan task's heading, established by SK-030 and validated by SK-033: E5 adds no parser. **S5 DoR: the mapping was never the missing half — the VERB was.** No subcommand could write `DONE`, `DONE_WITH_CONCERNS` or `PARKED` (`cli.py:21-28`), so `advance --to REVIEW` (`transitions.py:39-46`) was unsatisfiable for any task that succeeded and no sprint could ever end. The story now carries `task --id … --status … [--note]`, its append-only `runs/<id>/tasks.jsonl` trail, its four refusals (unknown id, `NEEDS_CONTEXT`, `BLOCKED`, a note-less `DONE_WITH_CONCERNS`), and the multi-plan-task → one-story rollup rule. | 6 | M | ☐ |
```

- [ ] **Step 4: Note SK-041's two definitions (points unchanged at 8)**

Replace the SK-041 row (`docs/plans/sprints/backlog-01/backlog.md:133`):

```markdown
| SK-041 | **Drain-then-halt**: run every task that is neither `BLOCKED` nor downstream of a blocker; park the rest; then stop and escalate the batch. Target shape, not an error state. (**D4**) S5 DoR gave the row two definitions it never had: "downstream of a blocker" is **discovered, not predicted** — `Task` has no dependency edge (`model.py:75-80`), so a same-root-cause block is `PARKED` rather than double-blocked, at a cost of at most one wasted dispatch and with no schema change; and `provable` is a filter on **claims**, not on which tasks run. It also absorbs SDD's remaining human-decision points — the pre-flight conflict scan, a plan-mandated review finding, and a reviewer's "cannot verify from diff" item — as blockers or in-loop resolutions, never as guesses. | 8 | M | ☐ |
```

- [ ] **Step 5: Update the totals**

- E5 section header (`docs/plans/sprints/backlog-01/backlog.md:128`):
  `## E5 — EXECUTE, drain-then-halt (19 pts)` → `## E5 — EXECUTE, drain-then-halt (23 pts)`
- Summary table E5 row (`docs/plans/sprints/backlog-01/backlog.md:68`): `| 19 |` → `| 23 |`
- `**Total: 128 pts.**` (`docs/plans/sprints/backlog-01/backlog.md:73`) → `**Total: 132 pts.**`

- [ ] **Step 6: Correct the status column for everything that shipped**

Every story in E1–E4 shipped in S1–S4 and every one of them still reads ☐. Change the Status cell to ☑ for the **19 rows** SK-001…SK-006, SK-010…SK-013, SK-020…SK-024 and SK-030…SK-033 (`docs/plans/sprints/backlog-01/backlog.md:86-91`, `:100-103`, `:109-113`, `:123-126`). Leave E5–E8 untouched: they have not shipped.

Verify:

```bash
grep -c "☑" docs/plans/sprints/backlog-01/backlog.md   # expected: 19
grep -n "^| SK-0[0-3][0-9] .*☐" docs/plans/sprints/backlog-01/backlog.md   # expected: no output
```

The epic-selection rule ("the first epic whose stories are unchecked") reads E1 as open if this column is taken literally — which is exactly the risk the sprint doc's own risks table records against itself.

- [ ] **Step 7: Record Gate 1 data point #5**

Append after the "Data point #4" paragraph at the end of `docs/plans/sprints/backlog-01/backlog.md`:

```markdown
**Data point #5 (S5 DoR, 2026-07-13):** refinement against live source grew scope
+4 pts (19 → 23), and — for the fifth consecutive sprint — the sharpest finding
was structural: **no verb in the CLI could mark a task done** (`cli.py:21-28`), so
`advance --to REVIEW` was unsatisfiable for any task that succeeded and no sprint
could ever reach REVIEW. Two of the pass's ten findings would have failed on the
first command of the first run: the derived scratch directory that nothing
creates, and Gate 2 still forbidding the very stage it opens. None of it is
visible from a backlog one-liner. Five sprints, five data points, same direction —
§7.2's answer at E6 stands: *the gate earns its keep because the refinement does.*
(Report §7.2)
```

- [ ] **Step 8: Commit**

```bash
git add docs/plans/sprints/backlog-01/backlog.md
git commit -m "docs: apply S5 DoR backlog deltas (SK-040 7pts, SK-042 2pts, SK-043 6pts, E5 23pts, total 132)"
```

---

## Exit criteria mapping (sprint doc → plan)

| Sprint exit criterion | Where it lands |
|---|---|
| SK-043: `task --id … --status …` exists, TDD'd offline; refuses unknown ids, `NEEDS_CONTEXT`, `BLOCKED`, a note-less `DONE_WITH_CONCERNS` | Task 1, Steps 1–4 |
| SK-043: writes `runs/<id>/tasks.jsonl` before state; a fixture sprint walks `PENDING → DONE → advance --to REVIEW` | Task 1 (`test_done_lands_in_state_and_in_the_trail_beside_blockers_jsonl`, `test_the_walk_that_is_impossible_on_main_today`) |
| SK-043: the SKILL.md mapping rows, one per SDD status, and the multi-plan-task rollup | Task 3, Step 3 |
| SK-040: the EXECUTE section dispatches SDD from the conductor with every scratch path derived from `sprint.scratch` | Task 2, Step 4 |
| SK-040: `sdd-workspace` + `mkdir -p <scratch>` before the first dispatch; `BASE` recorded per task; `merge-base` package for the final review; every dispatch names its model; `progress.md` neither read nor written; the branch check | Task 2, Step 4 (each with a tripwire test in Step 1) |
| SK-040: all three EXECUTE stub surfaces gone; the grep returns only REVIEW's stub | Task 2, Steps 3 and 5 (plus a fourth, found while planning: Gate 1 still calls the shipped PLAN stage a stub, `skills/supskill/SKILL.md:174-175`) |
| SK-041: the drain runs every `PENDING` task in plan order, writes each status before the next dispatch, parks same-root-cause blocks, bounds `NEEDS_CONTEXT` at one re-dispatch | Task 3, Step 3 |
| SK-041: halts **once** with the full batch; each task's `provable` claim stated honestly; resume after `/clear` lands on the first `PENDING` task | Task 3, Step 3 (prose) + Task 5, steps 7–9 (proof) |
| SK-042: the S9a blocker survives `record_blocker` with option (c) reachable | Task 4, Step 1 (`tests/test_block.py`) |
| SK-042: SKILL.md rules forbid a fabricated second option | Task 4, Step 3 |
| Full suite pure offline and fast; every Python story TDD'd, failing test first | Task 1's step sequence |
| The sprint demo (operator-run, real tokens, `/clear` mid-drain, a halt with real options) | Task 5 — **operator-run; the sprint does not close on offline green alone** |
| Backlog deltas applied | Task 6 |

## Review pass (after all tasks)

Author↔review separation holds: dispatch `oh-my-claudecode:code-reviewer`, then `oh-my-claudecode:verifier`, in fresh contexts. Named checks this sprint, beyond the standing ones:

1. **Invariant 3, where it now bites hardest.** No line of the EXECUTE section instructs a dispatched agent to run `supskill-state` or touch `.supskill/`. The conductor records every status **after** the task review — never on an implementer's word. An implementer that can write state can mark its own work done; that is F-5, one layer deeper than before.
2. **One vocabulary, one authority.** `record_task_status` refuses `NEEDS_CONTEXT` by calling `parse_task_status` — the model's own message — not by re-copying it. There is exactly one place that knows what a status string means.
3. **The trail is trail-first.** `store.append_jsonl` runs before `store.dump_state` in `record_task_status`, like `record_gate` and `record_blocker` before it. A refusal writes nothing anywhere.
4. **No second parser and no schema bump.** This sprint adds no parser over the dev plan, no `depends:` field, and no `Task.note`. If a reviewer wants a dependency graph, they are describing E6 or later, not this.
5. **The halt is not sold as a failure.** If any prose, report, or commit message calls a blocked halt a failure or an incomplete sprint, that is the regression this check exists to catch. Drain-then-halt is the product.
6. **SDD is composed, not reimplemented** (D1). No fourth prompt template exists. No supskill prose restates SDD's Model Selection, its implementer contract, or its review loop — they are named and followed.
7. **The SDD line numbers are pinned to superpowers 6.1.1.** If the installed plugin has moved, the composed contracts were re-read, not assumed. Confirm this explicitly rather than trusting the plan.
8. **E6 boundary:** the REVIEW row is still the honest stub; no Gate 3 exists; nothing advances past EXECUTE; the halt report is the deliverable.
