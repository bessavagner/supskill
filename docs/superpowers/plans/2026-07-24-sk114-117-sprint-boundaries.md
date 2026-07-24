# E9 Sprint Boundaries (SK-114, SK-115, SK-116, SK-117) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the four decisions a sprint boundary depends on — what a replan may write to, whether an unfinished sprint may be archived, which sprint a continuation continues, and whether the documents that authorize a sprint are in the branch — checked by a mechanism instead of by an agent's judgment.

**Architecture:** All four rows are the same defect: a guard validates a thing's *shape* and never its *preconditions*, and a conductor's judgment quietly patched the hole. Two rows extend an existing check with the state it never read (`replan-guard`, `init --archive`); one adds a tolerant optional field to the state model (`sprint.continues`); one adds a new guard module in the package's established shape (pure check + `refusal()` + thin `cli.py` verb + dedicated test + one SKILL.md sentence). No stage template changes, no new dispatch, no schema version bump.

**Tech Stack:** Python 3.11, stdlib only (`argparse`, `subprocess`, `json`, `dataclasses`). pytest for tests, ruff for lint. No mypy — it is not installed; older plans in this repo that mention it are stale.

## Global Constraints

- **Branch first.** Work on `feat/e9-sprint-boundaries`, cut from `main`. Merge with `--no-ff` at the end. SK-100/101/105/106/111/112 all did this; it is not optional.
- **No AI attribution** in any commit message or PR body. No `Co-Authored-By`, no "Generated with" line, no mention of Claude/Anthropic/AI. This overrides any harness default.
- **Tests:** `uv run pytest` — offline, currently **431 passed**. Never network.
- **Lint:** `uv run ruff check .` — 100 columns. Run before every commit.
- **No mypy.** Do not add type-checking steps or a mypy config.
- **Never bump `SCHEMA_VERSION`.** A dogfood run (`~/Documents/projetos/ledgerus`, sprint s7) is live against this code right now. Task 4 adds a field that reads tolerantly from state files that do not have it, so an in-flight `state.json` keeps parsing.
- **Guard-module shape** (`plan_guard.py`, `replan_guard.py`, `commit_scope.py` are the templates): a pure check function, a `refusal()` that returns the exact operator-facing text, a thin `cli.py` verb that prints the refusal on **stderr** and returns exit 1, a dedicated test module, and one sentence in `SKILL.md`.
- **Refusal texts state their own ceiling.** Every guard in this package says plainly what it does *not* catch (`plan_guard.py:41-43`, `commit_scope.py:95-96`). Match that voice; do not oversell.
- **supskill never runs git on the operator's behalf.** It will not create, switch, or delete a branch, and it will not `git add`. Task 5 asks git a read-only question and reports; it never stages.
- **SKILL.md body budget:** the body is at **511 lines** against a **515** cap pinned by `tests/test_skill_frontmatter.py::test_body_stays_under_515_lines`. Task 6 owns that budget; earlier tasks that touch `SKILL.md` must edit **in place** without adding lines except where this plan says so.
- **Bookkeeping commits are separate.** Code that closes a row is one commit; marking the backlog row ☑ is its own `docs(backlog): …` commit (Task 6).

---

## File Structure

**Modified:**
- `scripts/supskill_state/replan_guard.py` — Task 1. Gains the precondition check (`lacks_backlog_target`) and its refusal, beside the shape check it already has.
- `scripts/supskill_state/commands.py` — Tasks 3 and 4. `init_sprint` gains the archive precondition and the `continues` parameter; `render_show` prints `continues`.
- `scripts/supskill_state/model.py` — Task 4. `SprintInfo.continues`, read tolerantly, written always.
- `scripts/supskill_state/cli.py` — Tasks 1, 4, 5. `replan-guard` learns `--dir` and reads state; `init` learns `--continues`; the new `artifact-guard` verb is wired.
- `skills/supskill/SKILL.md` — Tasks 2, 6. The step-3 refusal template (in place), and the four one-sentence guard mentions.
- `docs/state-schema.md` — Task 6. `sprint.continues`.
- `docs/plans/sprints/backlog-01/backlog.md` — Task 6. Rows ☑ and the arithmetic.
- `tests/test_replan_guard.py`, `tests/test_init.py`, `tests/test_show.py`, `tests/test_run_matrix.py` — extended by their respective tasks.

**Created:**
- `scripts/supskill_state/artifact_tracking.py` — Task 5. The new guard module.
- `tests/test_artifact_tracking.py` — Task 5.

---

## Task 0: Cut the branch

**Files:** none.

- [ ] **Step 1: Confirm a clean tree on `main`**

```bash
git -C /home/bessa/Documents/projetos/supskill status --short
git -C /home/bessa/Documents/projetos/supskill log --oneline -1
```

Expected: no output from `status`, and `4b3df53 docs(handoff): revise the 0.5.0 handoff against the verified repo state` (or later) from `log`. Anything else — stop and report; do not stash or discard.

- [ ] **Step 2: Cut the branch**

```bash
git checkout -b feat/e9-sprint-boundaries
```

- [ ] **Step 3: Record the baseline**

```bash
uv run pytest -q | tail -3
```

Expected: `431 passed`. This is the number every later task compares against.

---

## Task 1: SK-114 — `replan-guard` refuses an amending shape with no backlog to amend

**Files:**
- Modify: `scripts/supskill_state/replan_guard.py` (append after `refusal`, line 57)
- Modify: `scripts/supskill_state/cli.py:224-243` (`_add_replan_guard`, `_cmd_replan_guard`) and the import line at `cli.py:9`
- Test: `tests/test_replan_guard.py`

**Interfaces:**
- Consumes: `store.resolve_root`, `store.state_path`, `store.load_state` (`scripts/supskill_state/store.py:65,80,92`); `State.backlog`, `State.sprint.id` (`model.py:91-99`).
- Produces: `replan_guard.lacks_backlog_target(shape: str, backlog: str | None) -> bool` and `replan_guard.target_refusal(shape: str, sprint_id: str) -> str`. No later task consumes these.

**Why this exists.** `replan-guard` takes `--shape` and nothing else — it reads no state at all, so it is structurally incapable of checking that an amending shape has a target. On ledgerus s6 it returned exit 0 on a generative writeback for a sprint whose `state.backlog` was `null`; the conductor then appended 63 lines to a path `state.json` never authorized, inferred from `artifacts.sprint_doc`'s parent directory. It inferred correctly. That is the problem: the run was carried by judgment while the mechanical net passed vacuously.

**The one behavior change to be deliberate about.** Today the guard needs no state file at all (`tests/test_replan_guard.py:102-105` pins that). After this task, that stays true **only for the supersede shape** — which is refused for what it is, before any state is read — and the three amending shapes require state. That is the point of the row, and Step 1 rewrites the test that pinned the old contract.

- [ ] **Step 1: Rewrite the two tests that pin the old no-state contract**

In `tests/test_replan_guard.py`, replace `test_cli_exit_codes_for_replan_guard` (lines 92-99) and `test_replan_guard_needs_no_state_file` (lines 102-105) with:

```python
def test_cli_exit_codes_for_replan_guard(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    commands.init_sprint("s1", backlog="docs/backlog.md", root=tmp_path)

    assert main(["replan-guard", "--shape", "generative-writeback"]) == 0
    assert "is an amending shape" in capsys.readouterr().out

    assert main(["replan-guard", "--shape", "north-star-reset"]) == 1
    err = capsys.readouterr().err
    assert "operator's alone" in err
    assert "author the new backlog by hand" in err


def test_the_supersede_shape_still_needs_no_state_file(tmp_path, monkeypatch, capsys):
    # shape 4 is refused for what it IS, before any state is read: it must still
    # work before init and after a wipe, like plan-guard
    monkeypatch.chdir(tmp_path)
    assert main(["replan-guard", "--shape", "north-star-reset"]) == 1
    assert "operator's alone" in capsys.readouterr().err
```

- [ ] **Step 2: Write the failing tests for the new check**

Append to `tests/test_replan_guard.py`:

```python
# --- SK-114: the precondition the shape check never had ---

@pytest.mark.parametrize("shape", AMENDING_SHAPES)
def test_an_amending_shape_with_no_recorded_backlog_lacks_a_target(shape):
    assert lacks_backlog_target(shape, None) is True
    assert lacks_backlog_target(shape, "") is True
    assert lacks_backlog_target(shape, "   ") is True


@pytest.mark.parametrize("shape", AMENDING_SHAPES)
def test_an_amending_shape_with_a_recorded_backlog_has_its_target(shape):
    assert lacks_backlog_target(shape, "docs/plans/sprints/backlog-01/backlog.md") is False


def test_the_supersede_shape_is_never_judged_on_its_target():
    # shape 4 is refused for what it is; a backlog it could write to is beside the point
    assert lacks_backlog_target("north-star-reset", None) is False


def test_an_unknown_shape_still_raises_here_too():
    with pytest.raises(StateError, match="unknown replan shape"):
        lacks_backlog_target("some other reading", None)


def test_the_target_refusal_names_the_sprint_the_null_and_the_operators_move():
    text = target_refusal("generative-writeback", "s6")
    assert "s6" in text
    assert "backlog: null" in text
    assert "--backlog" in text
    assert "inferred" in text  # names the guess it exists to stop


def test_target_refusal_refuses_to_run_on_the_supersede_shape():
    with pytest.raises(StateError, match="its own refusal"):
        target_refusal("north-star-reset", "s6")


def test_cli_refuses_a_writeback_with_no_authorized_destination(tmp_path, monkeypatch, capsys):
    # the ledgerus s6 case, exactly: --entry EXECUTE carries backlog: null to Gate 3
    monkeypatch.chdir(tmp_path)
    commands.init_sprint("s6", entry="EXECUTE", root=tmp_path)
    assert main(["replan-guard", "--shape", "generative-writeback"]) == 1
    err = capsys.readouterr().err
    assert "s6" in err and "backlog: null" in err


def test_cli_reads_state_from_an_explicit_dir(tmp_path, capsys):
    commands.init_sprint("s6", entry="EXECUTE", root=tmp_path)
    assert main(["replan-guard", "--shape", "park-at-boundary", "--dir", str(tmp_path)]) == 1
    assert "s6" in capsys.readouterr().err
```

Extend the import block at `tests/test_replan_guard.py:19-24` to:

```python
from supskill_state.replan_guard import (
    AMENDING_SHAPES,
    REPLAN_SHAPES,
    is_supersede,
    lacks_backlog_target,
    refusal,
    target_refusal,
)
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
uv run pytest tests/test_replan_guard.py -q
```

Expected: FAIL — `ImportError: cannot import name 'lacks_backlog_target'`.

- [ ] **Step 4: Implement the check**

Append to `scripts/supskill_state/replan_guard.py`:

```python
def lacks_backlog_target(shape: str, backlog: str | None) -> bool:
    """True iff this amending shape has no recorded backlog to amend (SK-114).

    The supersede shape is never judged here: it is refused for what it is,
    before any state is read, so it returns False and reaches its own refusal.
    An unknown shape still raises, via is_supersede - the vocabulary has one
    owner and this is not a second one.

    What this asks is narrow on purpose: was a destination AUTHORIZED, not is
    the writeback correct. On ledgerus s6 the conductor inferred the target
    from artifacts.sprint_doc's parent directory and inferred it right; SCOPE's
    own rule is that the recorded artifact is the only authority anything
    downstream reads, and an inference is not a record.
    """
    if is_supersede(shape):
        return False
    return not (backlog or "").strip()


def target_refusal(shape: str, sprint_id: str) -> str:
    """What the conductor reports, verbatim, when an amending shape has no target."""
    if is_supersede(shape):
        raise StateError(
            f"target_refusal() called on {shape!r}; the supersede shape has its own refusal"
        )
    return (
        f"this Gate 3 answer reads as {shape}, which amends the backlog - and this sprint "
        "has no backlog to amend.\n"
        f"state.json records backlog: null for sprint {sprint_id}, so no destination for "
        "the writeback was ever authorized. A path inferred from artifacts.sprint_doc's "
        "directory is a guess: the recorded artifact is the only authority anything "
        "downstream reads, and an inference is not a record.\n"
        "Nothing was drafted and nothing was written. The move is the operator's: name the "
        "backlog this sprint amends when you start the next one -\n"
        "  supskill-state init <next-id> --archive --backlog <path> "
        "(carrying this sprint's --branch and --slug)\n"
        "This guard checks that a target was authorized, not that a writeback would be "
        "correct. A wrong-but-recorded backlog path passes it."
    )
```

- [ ] **Step 5: Give the CLI verb the state**

In `scripts/supskill_state/cli.py`, change the import at line 9 to add `store`:

```python
from . import commands, commit_scope, config, plan_guard, preflight, replan_guard, store, worktree
```

Then replace `_add_replan_guard` / `_cmd_replan_guard` (lines 224-243) with:

```python
def _add_replan_guard(subparsers) -> None:
    sub = subparsers.add_parser(
        "replan-guard",
        help="is this Gate 3 replan shape a supersede, or an amend with no target? exit 1 = refuse",
    )
    sub.add_argument(
        "--shape",
        required=True,
        choices=list(replan_guard.REPLAN_SHAPES),
        help="the conductor's own classification of the operator's Gate 3 answer",
    )
    sub.add_argument(
        "--dir",
        default=None,
        dest="root",
        help="the repo root whose .supskill/ holds this sprint's state; default cwd",
    )
    sub.set_defaults(func=_cmd_replan_guard)


def _cmd_replan_guard(args) -> int:
    # shape 4 is refused for what it is, before any state is read
    if replan_guard.is_supersede(args.shape):
        print(replan_guard.refusal(args.shape), file=sys.stderr)
        return 1
    root = store.resolve_root(Path(args.root) if args.root else None)
    state = store.load_state(store.state_path(root))
    if replan_guard.lacks_backlog_target(args.shape, state.backlog):
        print(replan_guard.target_refusal(args.shape, state.sprint.id), file=sys.stderr)
        return 1
    print(f"replan-guard: {args.shape} is an amending shape; it amends {state.backlog}")
    return 0
```

`Path` is already imported at `cli.py:7`.

- [ ] **Step 6: Run the tests to verify they pass**

```bash
uv run pytest tests/test_replan_guard.py -q
```

Expected: PASS, all tests in the module.

- [ ] **Step 7: Run the full suite and lint**

```bash
uv run pytest -q | tail -3 && uv run ruff check .
```

Expected: **zero failures**, and `All checks passed!`. The count rises from 431 by the net new tests; the number itself is only recorded, never asserted.

- [ ] **Step 8: Commit**

```bash
git add scripts/supskill_state/replan_guard.py scripts/supskill_state/cli.py tests/test_replan_guard.py
git commit -m "fix(replan-guard): refuse an amending shape with no recorded backlog

SK-114. The guard took --shape and nothing else, so it validated the shape
of a Gate 3 answer while never checking the target existed. On ledgerus s6
it exited 0 on a generative writeback for a sprint carrying backlog: null;
the conductor inferred the destination from artifacts.sprint_doc's parent
and inferred it correctly, which is exactly the failure - the mechanical
net passed vacuously and judgment carried the run.

The guard now reads state for the three amending shapes and refuses when
state.backlog is null. The supersede shape still needs no state file: it is
refused for what it is, before anything is read."
```

---

## Task 2: SK-114 (folded SK-118) — the step-3 refusal keeps the operator's flags

**Files:**
- Modify: `skills/supskill/SKILL.md:73-80` (the step-3 refusal template) — **in place, no net new lines**
- Test: `tests/test_run_matrix.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: nothing consumed later. This is prose plus a prose test.

**Why this exists.** Same root cause as Task 1, from the other end: when the operator asks for a sprint id that does not match the one on disk, step 3 tells them to run `init <requested-id> --archive` — dropping the `--backlog`, `--branch` and `--slug` they typed. Following that command verbatim produces exactly the `backlog: null` sprint Task 1 now refuses at Gate 3. On ledgerus the conductor re-added the flags by judgment. The target is deduced rather than authorized in both halves.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_run_matrix.py`:

```python
def test_the_step_three_refusal_carries_the_operators_own_flags_forward():
    # SK-114/SK-118: the template dropped --backlog/--branch/--slug from the command
    # it tells the operator to run, producing the backlog: null sprint replan-guard
    # now refuses at Gate 3. The conductor re-added them by judgment; prose must not
    # need that.
    skill = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    start = text.index("3. **Compare ids.**")
    section = text[start : text.index("\n4. **", start)]
    assert "--archive" in section
    assert "--backlog" in section
    assert "the flags you gave this invocation" in section
    assert "Do not run that command." in section  # the restraint survives the edit
```

Add `from pathlib import Path` to the imports at the top of `tests/test_run_matrix.py`.

- [ ] **Step 2: Run it to verify it fails**

```bash
uv run pytest tests/test_run_matrix.py -q
```

Expected: FAIL — `AssertionError` on `assert "--backlog" in section`.

- [ ] **Step 3: Rewrite the template in place**

In `skills/supskill/SKILL.md`, replace lines 73-80 (from `   - Different → refuse and stop.` through `     Do not run that command. Stop here.`) with exactly this — same line count, 8 lines:

```markdown
   - Different → refuse and stop. The refusal must name both ids, the flags you
     gave this invocation, and the operator's way forward, verbatim:

         A different sprint is already on disk: state.json holds <sprint.id>,
         you asked for <requested-id>. A half-finished sprint is never
         archived automatically. If you mean to close it out and start fresh, run:
         ${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state init <requested-id> --archive <every --entry/--backlog/--branch/--slug flag from this invocation, verbatim>

     Never drop a flag the operator typed: an init that loses `--backlog` starts
     a sprint with `backlog: null`, which `replan-guard` refuses at Gate 3.
     Do not run that command. Stop here.
```

Count the result: the replacement is 11 lines against 8 removed, so this task adds **3 lines** to the body (511 → 514, one under the 515 cap). Task 6 owns the remaining budget and will raise the cap if it needs to.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run pytest tests/test_run_matrix.py tests/test_skill_frontmatter.py -q
```

Expected: PASS — including `test_body_stays_under_515_lines`. If the body test fails here, stop: recount the replacement and remove the excess from within it rather than raising the cap in this task.

- [ ] **Step 5: Run the full suite**

```bash
uv run pytest -q | tail -3 && uv run ruff check .
```

Expected: zero failures, `All checks passed!`.

- [ ] **Step 6: Commit**

```bash
git add skills/supskill/SKILL.md tests/test_run_matrix.py
git commit -m "fix(skill): the id-mismatch refusal carries the operator's flags forward

SK-114, folding SK-118. The step-3 template told the operator to run
init <id> --archive and dropped the --backlog/--branch/--slug they typed;
following it verbatim produces the backlog: null sprint the replan guard
now refuses. Same root cause as the guard fix: the target was deduced
rather than authorized."
```

---

## Task 3: SK-115 — `init --archive` refuses over a sprint resting at REVIEW with G3 open

**Files:**
- Modify: `scripts/supskill_state/commands.py:40-111` (`init_sprint` and a new module-level helper)
- Test: `tests/test_init.py`

**Interfaces:**
- Consumes: `loads_state` (`model.py:291`), `Stage`, `GATE_KEYS` — `Stage` and `GATE_KEYS` are already imported at `commands.py:19-32`; `loads_state` is not and must be added to that import block.
- Produces: `commands._undecided_review_refusal(path: Path) -> str | None`. Task 4 calls `init_sprint` around it but does not call it directly.

**Why this exists.** ledgerus s5 halted correctly: a real `AGENTS.md` self-contradiction blocked SK-052, three downstream stories parked, all four terminal, advanced to REVIEW. The operator resolved the contradiction out of band and re-inited s6 at `--entry EXECUTE`. `runs/s5/archive-1/gates.jsonl` holds G1 and G2 and no G3, so **how that blocker was decided exists nowhere on disk**. The append-only audit trail preserved the question and lost the answer, at the one point it was built for.

**The design call, already made:** refuse the archive; do not add a fourth gate decision. `gate --decision` keeps its three values (`approved`, `rejected`, `replan`) and the schema does not change. The operator records the decision with the verb that already exists, then re-runs the init.

**Two behaviors that must survive unchanged:**
1. An old state that cannot be *read* is still archived, never destroyed (`tests/test_init.py:82-86`). An unparseable file returns `None` here — no refusal.
2. Validation happens **before any disk change**. `init_sprint` already validates the id, the entry stage and the backlog before touching disk; this check goes in the same window, before `_archive_existing` runs.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_init.py`:

```python
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
```

- [ ] **Step 2: Run them to verify they fail**

```bash
uv run pytest tests/test_init.py -q -k "gate_three or unreadable_old_state_is_still"
```

Expected: FAIL — `DID NOT RAISE StateError` on the first test.

- [ ] **Step 3: Implement the precondition**

In `scripts/supskill_state/commands.py`, add `loads_state` to the `.model` import block (lines 19-32), keeping the list alphabetical among the lowercase names:

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
    loads_state,
    parse_task_status,
    state_to_dict,
)
```

Replace the archive block in `init_sprint` (lines 66-73) with:

```python
    path = store.state_path(root)
    if path.exists():
        if not archive:
            raise StateError(
                f"{path} already exists; pass --archive to archive the old run first "
                "(prior state is never destroyed)"
            )
        undecided = _undecided_review_refusal(path)
        if undecided is not None:
            raise StateError(undecided)
        _archive_existing(root)
```

Add this helper immediately above `_archive_existing` (currently line 94):

```python
def _undecided_review_refusal(path: Path) -> str | None:
    """SK-115: the refusal when the outgoing sprint rests at REVIEW with G3 open.

    A sprint that reached REVIEW and never recorded a Gate 3 decision is the one
    case where archiving keeps the question and loses the answer. ledgerus s5 is
    the instance on record: it halted on a genuine blocker, the operator resolved
    it out of band, s6 was inited over it, and runs/s5/archive-1/gates.jsonl
    holds G1 and G2 and no G3 - how that blocker was decided exists nowhere on
    disk. This is the append-only trail failing at the point it was built for.

    Returns the refusal text, or None when there is nothing to refuse. An old
    state that cannot be READ returns None: it is archived, never destroyed
    (test_init_archives_unreadable_old_state_under_unknown), and refusing on a
    parse error would turn that guarantee into its opposite.

    The ceiling: this checks that a decision was RECORDED, not that it was the
    right one. `gate --id G3 --decision approved --response "."` satisfies it.
    """
    try:
        old = loads_state(path.read_text(encoding="utf-8"))
    except (OSError, StateError):
        return None
    if old.stage is not Stage.REVIEW or old.gates[GATE_KEYS["G3"]] is not None:
        return None
    return (
        f"sprint {old.sprint.id} rests at REVIEW with no Gate 3 decision recorded. "
        "Archiving it now would keep the question and lose the answer.\n"
        "What a later reader has is the trail: runs/<id>/archive-N/gates.jsonl. A sprint "
        "that halted on a real blocker and was superseded out of band leaves nothing in it "
        "saying how that blocker was decided - the decision that mattered most is the one "
        "the archive drops.\n"
        "Record it first, with the verb that already exists, then re-run this init:\n"
        f"  supskill-state gate --id G3 --decision <approved|rejected|replan> "
        '--response "<what you decided, verbatim>"\n'
        "Nothing was archived and nothing was created; the sprint on disk is untouched.\n"
        "This checks that a decision was recorded, not that it was the right one."
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_init.py -q
```

Expected: PASS — the whole module, including the seven pre-existing archive tests.

- [ ] **Step 5: Run the full suite and lint**

```bash
uv run pytest -q | tail -3 && uv run ruff check .
```

Expected: zero failures, `All checks passed!`.

- [ ] **Step 6: Commit**

```bash
git add scripts/supskill_state/commands.py tests/test_init.py
git commit -m "fix(init): refuse --archive over a sprint at REVIEW with no G3 decision

SK-115. ledgerus s5 halted correctly on a real blocker, the operator
resolved it out of band, and s6 was inited over it - so archive-1's
gates.jsonl holds G1 and G2 and no G3, and how that blocker was decided
exists nowhere on disk. The append-only trail kept the question and lost
the answer.

Refuse the archive and name the gate verb, rather than adding a fourth
gate decision: gate --decision keeps its three values and the schema is
unchanged. An unreadable old state is still archived, never refused."
```

---

## Task 4: SK-116 — `sprint.continues` records what a continuation continues

**Files:**
- Modify: `scripts/supskill_state/model.py:64-71` (`SprintInfo`), `:161-175` (`_parse_sprint`), `:260-273` (`state_to_dict`)
- Modify: `scripts/supskill_state/commands.py` (`init_sprint` signature and body, `render_show`)
- Modify: `scripts/supskill_state/cli.py:41-69` (`_add_init`, `_cmd_init`)
- Test: `tests/test_model.py`, `tests/test_init.py`, `tests/test_show.py`

**Interfaces:**
- Consumes: `commands._undecided_review_refusal` runs before this task's inheritance logic in `init_sprint` (Task 3).
- Produces: `SprintInfo.continues: str | None`; `init_sprint(..., continues: str | None = None, ...)`; the `--continues` CLI flag; a `continues: <id>` line in `show`'s human output and a `sprint.continues` key in `show --json`. Task 6 documents the field.

**Why this exists.** ledgerus s6 carries `sprint.id: s6` with `artifacts.sprint_doc: …/sprint-s5.md`, `dev_plan: …/2026-07-23-sprint-s5.md` and `branch: s5`. It ran no SCOPE and no PLAN, then spent 2.78M tokens — the largest EXECUTE on record — against a plan written for a different sprint id. The run was correct; the defect is that state cannot distinguish "s6 continues s5" from "s6 has its own doc that happens to be misnamed", so the cost ledger and the artifact pointers disagree about which sprint they describe.

**Two design calls, both deliberate:**
1. **The field is read tolerantly and written always.** `_parse_sprint` uses `raw.get("continues")`, not `_require` — every other field in that function is required, and this one is the exception on purpose. A `state.json` written before this change has no `continues` key, and a dogfood run is live against one right now (ledgerus s7). `SCHEMA_VERSION` stays at 1: this adds an optional field, it does not change how anything already-written is read.
2. **A non-SCOPE entry that archives inherits the outgoing sprint's id by default.** Requiring the conductor to remember `--continues` would reproduce the row's own defect — a fact recorded only when an agent thinks to record it. An explicit `--continues` always wins; `--continues` with `--entry SCOPE` is refused, because a SCOPE sprint scopes its own doc from the backlog and continues nothing.

- [ ] **Step 1: Write the failing model tests**

Append to `tests/test_model.py`:

```python
# --- SK-116: the continuation a sprint's state could not express ---

def test_sprint_continues_defaults_to_none(make_state):
    assert make_state().sprint.continues is None


def test_a_state_file_written_before_this_field_still_parses(make_state):
    # the field is read tolerantly on purpose: a dogfood run is live against a
    # state.json that has no `continues` key, and the schema version is unchanged
    raw = state_to_dict(make_state())
    del raw["sprint"]["continues"]
    assert state_from_dict(raw).sprint.continues is None


def test_continues_round_trips_through_json(make_state):
    state = make_state()
    state.sprint.continues = "s5"
    assert state_from_dict(json.loads(dumps_state(state))).sprint.continues == "s5"


def test_state_to_dict_always_writes_the_key(make_state):
    assert "continues" in state_to_dict(make_state())["sprint"]


def test_a_non_string_continues_is_refused(make_state):
    raw = state_to_dict(make_state())
    raw["sprint"]["continues"] = 5
    with pytest.raises(StateError, match="continues"):
        state_from_dict(raw)
```

Check the module's existing imports and add whichever of `json`, `pytest`, `StateError`, `state_from_dict`, `state_to_dict`, `dumps_state` are missing — `tests/test_model.py` already exercises this module, so most will be present.

- [ ] **Step 2: Run them to verify they fail**

```bash
uv run pytest tests/test_model.py -q
```

Expected: FAIL — `AttributeError: 'SprintInfo' object has no attribute 'continues'`.

- [ ] **Step 3: Add the field to the model**

In `scripts/supskill_state/model.py`, change `SprintInfo` (lines 64-70) to:

```python
@dataclass
class SprintInfo:
    id: str
    slug: str | None
    entry: Stage
    branch: str | None
    scratch: str
    # SK-116: the sprint this one continues, when it entered at PLAN or EXECUTE
    # rather than scoping its own doc. Optional on read (a state.json written
    # before this field simply has no key) and always written back.
    continues: str | None = None
```

In `_parse_sprint` (lines 161-175), add the tolerant read as the last constructor argument:

```python
    return SprintInfo(
        id=_req_str(raw, "id", where),
        slug=_opt_str(_require(raw, "slug", where), f"{where}.slug"),
        entry=entry,
        branch=_opt_str(_require(raw, "branch", where), f"{where}.branch"),
        scratch=_req_str(raw, "scratch", where),
        # .get, not _require: this field post-dates schema v1's other fields and a
        # state file written without it must still resume (SK-116)
        continues=_opt_str(raw.get("continues"), f"{where}.continues"),
    )
```

In `state_to_dict` (lines 264-270), add the key:

```python
        "sprint": {
            "id": state.sprint.id,
            "slug": state.sprint.slug,
            "entry": state.sprint.entry.value,
            "branch": state.sprint.branch,
            "scratch": state.sprint.scratch,
            "continues": state.sprint.continues,
        },
```

- [ ] **Step 4: Run the model tests to verify they pass**

```bash
uv run pytest tests/test_model.py -q
```

Expected: PASS.

- [ ] **Step 5: Write the failing init and show tests**

Append to `tests/test_init.py`:

```python
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
```

Append to `tests/test_show.py`:

```python
def test_show_names_the_sprint_a_continuation_continues(tmp_path):
    init_sprint("s5", backlog="backlog.md", root=tmp_path)
    init_sprint("s6", entry="EXECUTE", archive=True, root=tmp_path)
    assert "continues: s5" in render_show(root=tmp_path)


def test_show_says_nothing_about_continuation_when_there_is_none(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    assert "continues:" not in render_show(root=tmp_path)
```

Match `tests/test_show.py`'s existing call convention for `render_show` — read the module's other tests first and use the same one.

- [ ] **Step 6: Run them to verify they fail**

```bash
uv run pytest tests/test_init.py tests/test_show.py -q
```

Expected: FAIL — `TypeError: init_sprint() got an unexpected keyword argument 'continues'`.

- [ ] **Step 7: Implement it in `init_sprint`**

Change the signature (`commands.py:40-49`) to add the parameter after `branch`:

```python
def init_sprint(
    sprint_id: str,
    *,
    slug: str | None = None,
    entry: str = "SCOPE",
    backlog: str | None = None,
    branch: str | None = None,
    continues: str | None = None,
    archive: bool = False,
    root: Path | None = None,
) -> State:
```

Add this validation immediately after the existing SCOPE/backlog check (after line 64), so it runs before any disk change:

```python
    if continues is not None:
        if not continues.strip():
            raise StateError("--continues needs a sprint id, not an empty string")
        if entry_stage is Stage.SCOPE:
            raise StateError(
                "a SCOPE-entry sprint continues nothing: it scopes its own doc from the "
                "backlog. --continues names the sprint a PLAN- or EXECUTE-entry sprint "
                "resumes work on"
            )
```

Change the archive block (as left by Task 3) to capture the outgoing id, and derive the default after it:

```python
    path = store.state_path(root)
    inherited: str | None = None
    if path.exists():
        if not archive:
            raise StateError(
                f"{path} already exists; pass --archive to archive the old run first "
                "(prior state is never destroyed)"
            )
        undecided = _undecided_review_refusal(path)
        if undecided is not None:
            raise StateError(undecided)
        inherited = _existing_sprint_id(path)
        _archive_existing(root)
    # SK-116: a PLAN- or EXECUTE-entry sprint that archives one is continuing it. Record
    # that rather than requiring the conductor to remember the flag - the row exists
    # because "s6 continues s5" and "s6's doc is misnamed" were indistinguishable on disk.
    if continues is None and entry_stage is not Stage.SCOPE:
        continues = inherited
```

Pass it into the `State` constructor (line 78):

```python
        sprint=SprintInfo(
            id=sprint_id,
            slug=slug,
            entry=entry_stage,
            branch=branch,
            scratch=scratch,
            continues=continues,
        ),
```

Add the id reader beside `_archive_existing`:

```python
def _existing_sprint_id(path: Path) -> str | None:
    """The outgoing sprint's id as it was typed, or None if unreadable (SK-116)."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        value = raw["sprint"]["id"]
    except Exception:
        return None  # an unreadable old state is archived, not refused; it just names nothing
    return value if isinstance(value, str) and value.strip() else None
```

In `render_show`, add the line right after the `backlog:` line (currently `commands.py:122`):

```python
    if state.sprint.continues:
        lines.append(f"continues: {state.sprint.continues}")
```

- [ ] **Step 8: Wire the CLI flag**

In `scripts/supskill_state/cli.py`, add to `_add_init` after the `--branch` argument (line 47):

```python
    sub.add_argument(
        "--continues",
        metavar="SPRINT_ID",
        help="the sprint this one continues; defaults to the archived sprint's id on a "
             "PLAN or EXECUTE entry, and is refused on a SCOPE entry",
    )
```

and pass it through in `_cmd_init`:

```python
    state = commands.init_sprint(
        args.sprint_id,
        slug=args.slug,
        entry=args.entry,
        backlog=args.backlog,
        branch=args.branch,
        continues=args.continues,
        archive=args.archive,
    )
```

- [ ] **Step 9: Run the tests to verify they pass**

```bash
uv run pytest tests/test_init.py tests/test_show.py tests/test_model.py -q
```

Expected: PASS.

- [ ] **Step 10: Run the full suite and lint**

```bash
uv run pytest -q | tail -3 && uv run ruff check .
```

Expected: zero failures, `All checks passed!`. `tests/test_store.py` and `tests/test_run_matrix.py` both round-trip state — if either fails, the cause is the new key in `state_to_dict`, and the fix is in the test's expectation, not in the tolerant read.

- [ ] **Step 11: Commit**

```bash
git add scripts/supskill_state/model.py scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_model.py tests/test_init.py tests/test_show.py
git commit -m "feat(state): record the sprint a continuation continues

SK-116. ledgerus s6 carried sprint.id s6 with s5's sprint_doc, dev_plan
and branch, ran no SCOPE and no PLAN, and spent 2.78M tokens against a
plan written for another sprint id. The run was correct; state could not
distinguish 's6 continues s5' from 's6's doc is misnamed', so the cost
ledger and the artifact pointers disagreed about which sprint they
described.

sprint.continues is set explicitly by --continues and, on a PLAN or
EXECUTE entry that archives, defaults to the outgoing sprint's id -
requiring the conductor to remember the flag would reproduce the defect.
Read tolerantly (raw.get) so a state.json written before this field still
resumes; SCHEMA_VERSION is unchanged."
```

---

## Task 5: SK-117 — a Gate 3 guard that names recorded artifacts git does not track

**Files:**
- Create: `scripts/supskill_state/artifact_tracking.py`
- Create: `tests/test_artifact_tracking.py`
- Modify: `scripts/supskill_state/cli.py` (import line 9, `build_parser` line 31-ish, and the new verb)

**Interfaces:**
- Consumes: `store.resolve_root`, `store.state_path`, `store.load_state`; `State.artifacts` (`model.py:96`).
- Produces: `artifact_tracking.git_tracked(root: str, paths: list[str]) -> set[str]`, `artifact_tracking.untracked(paths: list[str], tracked: set[str]) -> list[str]`, `artifact_tracking.refusal(missing: list[str]) -> str`, and the `artifact-guard` CLI verb. Task 6 adds its SKILL.md sentence.

**Why this exists.** SCOPE and PLAN derive their output paths, write the files and record them as artifacts — and nothing stages them and no stage tells the operator to. The two documents that authorize a sprint sit untracked while the code they authorize is committed. playset's reviewers raised it at s1 and again at s2 ("the plan a branch implements is not in the branch"); ledgerus needed a hand commit after s6. Three occurrences, two projects, every one caught by a reader rather than a mechanism.

**Report, do not stage.** supskill runs no git command on the operator's behalf that changes the repo — EXECUTE's branch check already states that posture ("Do not create, switch, or delete a branch yourself"), and an automatic `git add` breaks it. This asks git one read-only question and refuses.

- [ ] **Step 1: Write the failing pure-function tests**

Create `tests/test_artifact_tracking.py`:

```python
"""SK-117: the guard that names recorded artifacts git does not track.

The sprint doc and the dev plan authorize a sprint; three times across two
projects they were left untracked while the code they authorize was committed,
and every time a human reader caught it rather than a mechanism.
"""

import subprocess
from pathlib import Path

import pytest

from supskill_state.artifact_tracking import git_tracked, refusal, untracked
from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_artifact
from supskill_state.errors import StateError


def test_everything_tracked_leaves_nothing_to_report():
    assert untracked(["docs/sprint-s6.md"], {"docs/sprint-s6.md"}) == []


def test_an_untracked_path_is_named():
    assert untracked(["docs/sprint-s6.md", "docs/plan.md"], {"docs/plan.md"}) == [
        "docs/sprint-s6.md"
    ]


def test_a_leading_dot_slash_is_normalized_before_comparing():
    assert untracked(["./docs/sprint-s6.md"], {"docs/sprint-s6.md"}) == []


def test_duplicates_are_collapsed():
    assert untracked(["docs/a.md", "docs/a.md"], set()) == ["docs/a.md"]


def test_blank_entries_are_ignored():
    assert untracked(["", "   "], set()) == []


def test_no_recorded_paths_asks_git_nothing(tmp_path):
    # an empty question needs no subprocess and no repo
    assert git_tracked(str(tmp_path), []) == set()


def test_the_refusal_lists_the_paths_and_refuses_to_stage_them():
    text = refusal(["docs/sprints/sprint-s6.md"])
    assert "docs/sprints/sprint-s6.md" in text
    assert "never fixed here" in text
    assert "G3 is still open" in text


def test_the_refusal_on_no_paths_raises():
    with pytest.raises(StateError, match="nothing to refuse"):
        refusal([])
```

- [ ] **Step 2: Run them to verify they fail**

```bash
uv run pytest tests/test_artifact_tracking.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'supskill_state.artifact_tracking'`.

- [ ] **Step 3: Write the module**

Create `scripts/supskill_state/artifact_tracking.py`:

```python
"""SK-117: name the recorded artifacts git does not track, before Gate 3.

SCOPE and PLAN derive their output paths, write the files and record them as
artifacts - and nothing stages them and no stage tells the operator to. So the
two documents that authorize a sprint sit untracked while the code they
authorize is committed. playset's reviewers raised it at s1 and again at s2
("the plan a branch implements is not in the branch"); ledgerus needed a hand
commit after s6. Three occurrences, two projects, every one surfaced by a reader
rather than by a mechanism.

Report, never stage. supskill runs no git command on the operator's behalf that
changes the repo - it will not create, switch or delete a branch, and it will
not `git add`. This module asks git one read-only question and refuses; the
commit stays the operator's, which is the same posture EXECUTE's branch check
already states.

The ceiling, stated here because it will be oversold otherwise: a repo that
deliberately git-ignores its sprint docs refuses here every time, and there is
no bypass flag - the way past a refusal in this package is to change the thing
it names, never the guard. And a tracked-but-stale doc passes: this asks whether
git knows the file, not whether its contents match the sprint.
"""

from __future__ import annotations

import subprocess

from .errors import StateError


def _normalize(path: str) -> str:
    path = path.strip()
    while path.startswith("./"):
        path = path[2:]
    return path


def git_tracked(root: str, paths: list[str]) -> set[str]:
    """The subset of `paths` git tracks, as `git ls-files` names them.

    Raises StateError if git fails - an unanswerable question is never a silent
    pass. An empty `paths` asks git nothing and returns the empty set.
    """
    if not paths:
        return set()
    result = subprocess.run(
        ["git", "-C", root, "ls-files", "--", *paths],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        raise StateError(f"git ls-files failed in {root}: {detail}")
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def untracked(paths: list[str], tracked: set[str]) -> list[str]:
    """The recorded paths git does not track, in order, deduped."""
    seen: set[str] = set()
    missing: list[str] = []
    for raw in paths:
        path = _normalize(raw)
        if not path or path in seen:
            continue
        seen.add(path)
        if path not in tracked:
            missing.append(path)
    return missing


def refusal(missing: list[str]) -> str:
    """What the conductor reports, verbatim, when a recorded artifact is untracked."""
    if not missing:
        raise StateError(
            "refusal() called with no untracked artifacts; there is nothing to refuse"
        )
    listed = "\n".join(f"    {path}" for path in missing)
    return (
        "this sprint's recorded artifacts are not tracked by git, so the documents that "
        "authorize this work are not in the branch that implements it:\n"
        f"{listed}\n"
        "Gate 3 asks the operator to rule on a sprint; a reader who comes to this branch "
        "later gets the code and not the plan it was held to.\n"
        "This is reported and never fixed here: supskill runs no git command that changes "
        "your repo. Stage and commit the paths above yourself, then re-run this stage.\n"
        "Nothing was recorded and no gate was called: G3 is still open.\n"
        "This asks whether git knows the file, not whether its contents still match the "
        "sprint; a tracked-but-stale doc walks past it."
    )
```

- [ ] **Step 4: Run the pure-function tests to verify they pass**

```bash
uv run pytest tests/test_artifact_tracking.py -q
```

Expected: PASS.

- [ ] **Step 5: Write the failing CLI tests**

Append to `tests/test_artifact_tracking.py`:

```python
def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def sprint_repo(tmp_path):
    """A git repo with a supskill sprint whose sprint doc exists on disk."""
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "initial")
    (repo / "docs" / "sprint-s6.md").write_text("# sprint s6\n", encoding="utf-8")
    init_sprint("s6", backlog="docs/backlog.md", root=repo)
    record_artifact("sprint_doc", "docs/sprint-s6.md", root=repo)
    return repo


def test_cli_refuses_an_untracked_sprint_doc(sprint_repo, capsys):
    assert main(["artifact-guard", "--dir", str(sprint_repo)]) == 1
    err = capsys.readouterr().err
    assert "docs/sprint-s6.md" in err
    assert "never fixed here" in err


def test_cli_passes_once_the_doc_is_committed(sprint_repo, capsys):
    _git(sprint_repo, "add", "docs/sprint-s6.md")
    _git(sprint_repo, "commit", "-q", "-m", "docs: the sprint doc")
    assert main(["artifact-guard", "--dir", str(sprint_repo)]) == 0
    assert "tracked by git" in capsys.readouterr().out


def test_cli_passes_when_no_artifact_is_recorded_yet(sprint_repo, capsys):
    init_sprint("s7", entry="EXECUTE", archive=True, root=sprint_repo)
    assert main(["artifact-guard", "--dir", str(sprint_repo)]) == 0
    assert "no artifacts recorded" in capsys.readouterr().out


def test_cli_defaults_to_cwd(sprint_repo, monkeypatch, capsys):
    monkeypatch.chdir(sprint_repo)
    assert main(["artifact-guard"]) == 1
    assert "docs/sprint-s6.md" in capsys.readouterr().err


def test_cli_refuses_when_there_is_no_state_to_read(tmp_path, monkeypatch, capsys):
    # unlike plan-guard, this reads state: it is a Gate 3 check, and Gate 3 implies state
    monkeypatch.chdir(tmp_path)
    assert main(["artifact-guard"]) == 1
    assert "no state file" in capsys.readouterr().err
```

Note: `test_cli_passes_when_no_artifact_is_recorded_yet` archives a sprint at SCOPE with no G3 involved, so Task 3's refusal does not fire.

- [ ] **Step 6: Run them to verify they fail**

```bash
uv run pytest tests/test_artifact_tracking.py -q
```

Expected: FAIL — `argparse` error, `invalid choice: 'artifact-guard'` (SystemExit 2).

- [ ] **Step 7: Wire the CLI verb**

In `scripts/supskill_state/cli.py`, extend the import at line 9:

```python
from . import (
    artifact_tracking,
    commands,
    commit_scope,
    config,
    plan_guard,
    preflight,
    replan_guard,
    store,
    worktree,
)
```

Register it in `build_parser`, right after `_add_replan_guard(subparsers)`:

```python
    _add_artifact_guard(subparsers)
```

Add the verb beside the other guards:

```python
def _add_artifact_guard(subparsers) -> None:
    sub = subparsers.add_parser(
        "artifact-guard",
        help="are this sprint's recorded artifacts tracked by git? exit 1 means refuse",
    )
    sub.add_argument(
        "--dir",
        default=None,
        dest="root",
        help="the repo root whose .supskill/ holds this sprint's state; default cwd",
    )
    sub.set_defaults(func=_cmd_artifact_guard)


def _cmd_artifact_guard(args) -> int:
    root = store.resolve_root(Path(args.root) if args.root else None)
    state = store.load_state(store.state_path(root))
    recorded = [path for path in state.artifacts.values() if path]
    if not recorded:
        print("artifact-guard: no artifacts recorded; there is nothing to check")
        return 0
    tracked = artifact_tracking.git_tracked(str(root), recorded)
    missing = artifact_tracking.untracked(recorded, tracked)
    if missing:
        print(artifact_tracking.refusal(missing), file=sys.stderr)
        return 1
    print(f"artifact-guard: all {len(recorded)} recorded artifacts are tracked by git")
    return 0
```

- [ ] **Step 8: Run the tests to verify they pass**

```bash
uv run pytest tests/test_artifact_tracking.py -q
```

Expected: PASS.

- [ ] **Step 9: Run the full suite and lint**

```bash
uv run pytest -q | tail -3 && uv run ruff check .
```

Expected: zero failures, `All checks passed!`.

- [ ] **Step 10: Commit**

```bash
git add scripts/supskill_state/artifact_tracking.py scripts/supskill_state/cli.py tests/test_artifact_tracking.py
git commit -m "feat(artifact-guard): refuse a Gate 3 whose recorded artifacts are untracked

SK-117. The sprint doc and dev plan are derived, written and recorded as
artifacts, and nothing stages them - so the documents that authorize a
sprint sit untracked while the code they authorize is committed. playset's
reviewers raised it at s1 and s2; ledgerus needed a hand commit after s6.
Three occurrences, two projects, every one caught by a reader.

Report, never stage: the guard asks git one read-only question and
refuses. supskill runs no git command that changes the operator's repo,
and an automatic git add would break the posture EXECUTE's branch check
already states."
```

---

## Task 6: The prose, the schema doc, and the backlog bookkeeping

**Files:**
- Modify: `skills/supskill/SKILL.md` — Gate 3 (line 508), the REVIEW/Gate 3 opening (line 500), the Arguments block (lines 38-41), the `--archive` convention (lines 26-29)
- Modify: `tests/test_skill_frontmatter.py:81-83` — only if the body exceeds the cap
- Modify: `docs/state-schema.md:30-31`
- Modify: `docs/plans/sprints/backlog-01/backlog.md`

**Interfaces:**
- Consumes: every verb and flag Tasks 1-5 produced — `replan-guard --dir`, `init --continues`, `artifact-guard`.
- Produces: nothing consumed by code.

**The line budget.** The body was 511 lines before this plan; Task 2 took it to 514, one under the 515 cap. This task adds text to **existing** long paragraph lines wherever possible (`SKILL.md:497`, `:500` and `:508` are each a single long line), which costs zero new lines. Step 5 measures the result and, if it is over, raises the cap deliberately — recording the reason in the test's docstring, exactly as the 500 → 515 raise was recorded. Never raise it as a reflex to make a red test green.

- [ ] **Step 1: Write the failing prose tests**

Append to `tests/test_artifact_tracking.py`:

```python
def test_gate_three_prose_names_the_artifact_guard():
    skill = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    start = text.index("## Gate 3")
    section = text[start : text.index("\n## ", start + 1)]
    assert "artifact-guard" in section
    assert "commit" in section  # the operator's move, named
```

Append to `tests/test_replan_guard.py`:

```python
def test_gate_three_prose_names_what_the_replan_guard_now_checks():
    skill = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    start = text.index("### Refusing a north-star supersede")
    section = text[start : text.index("\n## ", start + 1)]
    assert "backlog" in section and "amend" in section
```

`Path` is already imported in `tests/test_replan_guard.py` (line 12).

- [ ] **Step 2: Run them to verify they fail**

```bash
uv run pytest tests/test_artifact_tracking.py tests/test_replan_guard.py -q -k "prose"
```

Expected: FAIL — `assert "artifact-guard" in section`.

- [ ] **Step 3: Edit the SKILL.md prose**

**(a) Gate 3 opening** — append to the end of the existing line 500 (the paragraph beginning `Ask for real, refuse an empty answer`), in place, no new line:

```
 Before you ask the question, run `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state artifact-guard`: exit 1 means a recorded artifact — the sprint doc or the dev plan — is untracked by git, so the documents that authorize this sprint are not in the branch that implements it. Relay the refusal verbatim and stop; the commit is the operator's, and this skill never runs `git add`.
```

**(b) The supersede section** — append to the end of the existing line 508, in place, no new line:

```
 The guard also reads state: on an amending shape it refuses when `state.backlog` is null, because a writeback whose destination was never recorded is a path you inferred, not a path anything authorized (SK-114). Relay that refusal verbatim too.
```

**(c) The Arguments block** — extend line 41 in place so the flag list reads:

```markdown
`--entry SCOPE|PLAN|EXECUTE`, `--backlog <path>`, `--branch <name>`,
`--slug <slug>`, `--continues <sprint-id>` (the sprint a PLAN- or EXECUTE-entry
sprint resumes; `init` defaults it to the archived sprint's id).
```

That replaces one line with three: **+2 lines**.

**(d) The `--archive` convention** — extend line 29 in place (the paragraph ending `or the SCOPE stage's backlog check below`):

```
 `init --archive` itself refuses over a sprint resting at `REVIEW` with no `G3` decision recorded — archiving it would keep the question and lose the answer (SK-115).
```

- [ ] **Step 4: Run the prose tests to verify they pass**

```bash
uv run pytest tests/test_artifact_tracking.py tests/test_replan_guard.py -q -k "prose"
```

Expected: PASS.

- [ ] **Step 5: Measure the body against its cap**

```bash
uv run python -c "
from pathlib import Path
t = Path('skills/supskill/SKILL.md').read_text(encoding='utf-8')
c = t.index('\n---\n', 4)
print('body lines:', len(t[c+5:].splitlines()))
"
uv run pytest tests/test_skill_frontmatter.py -q
```

Expected: 516 body lines and one FAIL on `test_body_stays_under_515_lines`. If it is 515 or fewer, skip Step 6 entirely.

- [ ] **Step 6: Raise the cap, deliberately**

Only if Step 5 failed. In `tests/test_skill_frontmatter.py`, change `515` to `525` in the docstring (line 7), in `test_body_stays_under_515_lines`'s body (line 83) and in its name, and add to the docstring after line 13:

```
Raised again to 525 for SK-114..117: four guard sentences at Gate 3 and in the
Arguments block. Three of the four went into existing paragraph lines at no line
cost; the --continues flag needed its own. Same decision as the 515 raise -
deliberate, with the reason recorded, never a reflex to make a red test green.
```

Rename the test to `test_body_stays_under_525_lines` and update line 83 to `assert len(body) <= 525`.

- [ ] **Step 7: Document the schema field**

In `docs/state-schema.md`, replace line 31 with:

```markdown
- `sprint.slug` (string|null), `sprint.branch` (string|null).
- `sprint.continues` (string|null): the sprint this one continues, when it
  entered at `PLAN` or `EXECUTE` rather than scoping its own doc. `init` sets it
  from `--continues`, and defaults it to the archived sprint's id on a non-`SCOPE`
  entry that passes `--archive`. Read tolerantly: a `state.json` written before
  this field simply has no key and parses as null, which is why adding it did not
  bump `schema` (SK-116).
```

- [ ] **Step 8: Run the full suite and lint**

```bash
uv run pytest -q | tail -3 && uv run ruff check .
```

Expected: zero failures, `All checks passed!`.

- [ ] **Step 9: Commit the code-adjacent docs**

```bash
git add skills/supskill/SKILL.md docs/state-schema.md tests/test_skill_frontmatter.py tests/test_artifact_tracking.py tests/test_replan_guard.py
git commit -m "docs(skill): name the four sprint-boundary checks in the conductor's prose

Gate 3 runs artifact-guard before asking its question and relays the
replan guard's null-backlog refusal; the Arguments block names
--continues; the --archive convention names the REVIEW/G3 refusal.
state-schema.md documents sprint.continues and why it did not bump the
schema version."
```

- [ ] **Step 10: Mark the backlog rows done**

In `docs/plans/sprints/backlog-01/backlog.md`, change the `Status` cell from `☐` to `☑` on rows **SK-114, SK-115, SK-116, SK-117**.

Then append a `**Sprint deltas — <date>**` note under E9's sequencing paragraph recording the two divergences between what the rows asked for and what shipped — **do not rewrite the rows themselves**; a row records the finding as filed, not as fixed:

```markdown
**Delivered 2026-07-24 (SK-114..117).** Two divergences from the rows as filed, recorded
here rather than by editing them: SK-115 asked for "refuse, or record an explicit
superseded/abandoned decision" — the refusal was chosen, so `gate --decision` keeps its
three values and the schema is unchanged. SK-117 asked for "a Gate 3 check"; it shipped as
the `artifact-guard` verb the conductor runs before Gate 3's question, which is the same
check at the same point, under a name the row does not use.
```

- [ ] **Step 11: Verify the epic's arithmetic**

E9 was 51 pts with 24 closed and 27 open across 12 rows. These four rows are SK-114 (3), SK-115 (2), SK-116 (2), SK-117 (2) = **9 pts**, leaving **33 closed, 18 open across 8 rows**. The `## E9 — Findings from real runs (51 pts)` header, the summary table's `51`, and the intro prose's `51 points` are all totals, not open counts — they do **not** change.

```bash
uv run python -c "
import re
rows = [l for l in open('docs/plans/sprints/backlog-01/backlog.md') if re.match(r'\| SK-\d+ \|', l)]
e9 = [r for r in rows if int(re.match(r'\| SK-(\d+)', r).group(1)) >= 100]
pts = lambda rs: sum(int(r.rsplit('|', 4)[1].strip()) for r in rs)
open_rows = [r for r in e9 if r.rstrip().endswith('☐ |')]
print('E9 rows', len(e9), 'total', pts(e9), '| open rows', len(open_rows), 'open pts', pts(open_rows))
"
```

Expected: `E9 rows 18 total 51 | open rows 8 open pts 18`. If the totals disagree, fix the row edits — never the arithmetic.

- [ ] **Step 12: Commit the bookkeeping separately**

```bash
git add docs/plans/sprints/backlog-01/backlog.md
git commit -m "docs(backlog): mark SK-114..117 done

E9: 33 closed, 18 open across 8 rows. The epic total stays 51. Two
divergences between the rows as filed and what shipped are recorded as a
sprint-delta note rather than by rewriting the rows."
```

---

## Task 7: Verify the whole branch and hand it over

**Files:** none.

- [ ] **Step 1: Full verification from a clean state**

```bash
uv run pytest -q | tail -3
uv run ruff check .
git status --short
```

Expected: zero test failures, `All checks passed!`, and an empty `status`. Record the exact passing count — it is what the next handoff cites.

- [ ] **Step 2: Exercise the three new refusals end to end**

In a scratch directory outside the repo, confirm each guard refuses for the reason it exists:

```bash
cd "$(mktemp -d)" && git init -q . && git config user.email t@e.com && git config user.name T
SUP=/home/bessa/Documents/projetos/supskill/scripts/supskill-state

$SUP init s6 --entry EXECUTE                    # expect: initialized sprint s6 at EXECUTE
$SUP replan-guard --shape generative-writeback  # expect: EXIT 1, naming s6 and "backlog: null"
$SUP artifact-guard                             # expect: EXIT 0, "no artifacts recorded"
$SUP show                                       # expect: "backlog: -", and NO continues line
```

Then the continuation default (`s7` continues `s6`, recorded without anyone passing a flag):

```bash
$SUP init s7 --entry EXECUTE --archive          # expect: initialized sprint s7 at EXECUTE
$SUP show                                       # expect: a "continues: s6" line
```

The `--archive` refusal needs a sprint resting at `REVIEW`, which this scratch sprint cannot
reach without tasks. It is covered by `tests/test_init.py` instead; do not hand-edit
`state.json` to stage it — that is the one thing this package forbids everywhere else.

Report anything that does not behave as the plan describes — a surprise here is a finding, not a nuisance.

- [ ] **Step 3: Hand the branch over**

Do **not** merge, push, or open a PR without asking. Use `superpowers:finishing-a-development-branch`, which presents merge / PR / keep / discard rather than guessing. When merging: `--no-ff`, and no AI attribution in the merge commit.

---

## Notes for whoever executes this

- **Dispatched subagents' final chat messages routinely collapse to a placeholder** in this environment. Hand work over as files and read the file back. If you dispatch, the `Agent` subagent type names here are `oh-my-claudecode:executor` and `oh-my-claudecode:code-reviewer` — plain `executor` fails.
- **Count before trusting a number in this plan.** The last plan's grep count was 10 and the truth was 12. Every `grep -c` in this plan is worth re-running rather than assuming.
- **The line numbers cited here are from `4b3df53`.** Tasks 3 and 4 both edit `init_sprint`, so Task 4's line references shift by roughly the size of Task 3's insertion. Locate code by its text, never by its line number alone.
- **A dogfood run is live** at `~/Documents/projetos/ledgerus` (sprint s7, stage PLAN). Task 4's tolerant read is what keeps it resuming; do not "tidy" `raw.get("continues")` into `_require`.
