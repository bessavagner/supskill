# SK-055 / SK-056 — PAR's dead code, wired or removed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close E6's own dogfood-review findings — `review.py`'s `aggregate()`/`worse_severity()`
and `replan_guard.py`'s `is_supersede()`/`refusal()` currently have zero production callers — by
giving each a real runtime call site, without changing any behavior these functions' existing
regression tests already lock in.

**Architecture:** SK-055 routes `commands.record_review_finding` through `review.aggregate()` so a
`--confidence` that contradicts PAR's fixed aggregation rule is refused at the recording boundary,
the same "validate fully, then write" shape every other verb in `commands.py` already follows.
SK-056 adds a `replan-guard` CLI subcommand — `scripts/supskill_state/cli.py` wiring for
`replan_guard.py`, structurally identical to the existing `plan-guard` subcommand — then updates
Gate 3's prose (`SKILL.md`, `references/replan-shapes.md`) to name it as the exact command the
conductor runs once it has classified a Gate 3 answer.

**Tech Stack:** Python 3.11+, pytest, ruff. No new dependencies.

## Global Constraints

- Python ≥3.11, offline suite only: `uv run pytest -q` and `uv run ruff check` must stay green after
  every task (`pyproject.toml`: `testpaths = ["tests"]`, `pythonpath = ["scripts"]`, ruff
  `line-length = 120`, `select = ["E", "F", "I", "B", "UP"]`).
- TDD every step: write the failing test before the implementation.
- Every new production code path must have a real caller — no new dead functions; this is the exact
  defect class both stories close.
- No git commit or PR text may name Claude, Anthropic, or carry an AI-attribution trailer (repo-wide
  convention already followed by every commit in this history).
- Do not modify `scripts/supskill_state/review.py` or `scripts/supskill_state/replan_guard.py`
  themselves — their pure functions and existing tests (`tests/test_review.py`'s aggregation section,
  all of `tests/test_replan_guard.py`) are correct and already offline-proven; only their call sites
  are missing.

---

### Task 1: SK-055 — wire `aggregate()` into `record_review_finding`

**Files:**
- Modify: `scripts/supskill_state/commands.py:35` (import line)
- Modify: `scripts/supskill_state/commands.py:453-488` (`record_review_finding`)
- Test: `tests/test_review.py` (append after the existing vocabulary-refusal test)

**Interfaces:**
- Consumes: `aggregate(severity_a: str | None, severity_b: str | None) -> tuple[str, str]` from
  `scripts/supskill_state/review.py:52` — returns `(confidence, severity)`; already imported
  elsewhere as `from .review import aggregate` in `tests/test_review.py:21`. Confidence tokens are
  exactly `"high"` and `"actionable"` (`review.py:25`); severity tokens are exactly `"Critical"`,
  `"Important"`, `"Minor"` (`review.py:24`).
- Produces: `record_review_finding`'s signature is unchanged
  (`reviewer, severity, confidence, finding, location, root=None`). It now raises `StateError` with
  a message containing `"requires --confidence high"` or `"requires --confidence actionable"` when
  the caller's `--confidence` contradicts what `aggregate()` computes for that `--reviewer`/
  `--severity` pair. Nothing is written to `review.jsonl` on that refusal.

- [ ] **Step 1: Write the failing tests**

Open `tests/test_review.py`. Insert the following two tests immediately after
`test_the_vocabulary_and_the_two_required_fields_are_refused_with_nothing_written` (i.e. right before
`def test_both_is_a_legal_reviewer_value_for_a_finding_matched_across_both`):

```python
@pytest.mark.parametrize(
    "overrides,match",
    [
        ({"reviewer": "both", "confidence": "actionable"}, "requires --confidence high"),
        ({"reviewer": "reviewer-a", "confidence": "high"}, "requires --confidence actionable"),
        ({"reviewer": "reviewer-b", "confidence": "high"}, "requires --confidence actionable"),
    ],
)
def test_a_confidence_that_contradicts_the_fixed_aggregation_rule_is_refused_with_nothing_written(
    tmp_path, overrides, match
):
    init_sprint("s6", backlog="backlog.md", root=tmp_path)
    call = {
        "reviewer": "reviewer-a", "severity": "Critical", "confidence": "actionable",
        "finding": "a finding", "location": "src/x.py:1",
    }
    call.update(overrides)
    with pytest.raises(StateError, match=match):
        record_review_finding(
            call["reviewer"], call["severity"], call["confidence"], call["finding"], call["location"],
            root=tmp_path,
        )
    assert _reviews(tmp_path) == []


def test_cli_refuses_a_both_reviewer_finding_recorded_as_only_actionable(tmp_path, monkeypatch, capsys):
    init_sprint("s6", backlog="backlog.md", root=tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main([
        "review", "--reviewer", "both", "--severity", "Important", "--confidence", "actionable",
        "--finding", "x", "--location", "y",
    ]) == 1
    assert "requires --confidence high" in capsys.readouterr().err
```

`main` is already imported at the top of this file (`from supskill_state.cli import main`, line 18);
no new imports are needed for the test file.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_review.py -k "contradicts_the_fixed_aggregation_rule or refuses_a_both_reviewer" -v`
Expected: both new tests FAIL — no `StateError` is raised (`Failed: DID NOT RAISE`), because
`record_review_finding` has no aggregation check yet.

- [ ] **Step 3: Implement the aggregation check**

In `scripts/supskill_state/commands.py`, change line 35 from:

```python
from .review import parse_confidence, parse_reviewer, parse_severity
```

to:

```python
from .review import aggregate, parse_confidence, parse_reviewer, parse_severity
```

Then replace the body of `record_review_finding` (lines 453-488) with:

```python
def record_review_finding(
    reviewer: str,
    severity: str,
    confidence: str,
    finding: str,
    location: str,
    root: Path | None = None,
) -> None:
    """Record one aggregated PAR finding (SK-050).

    Pure trail, like costs.jsonl: this reads state.json only to place the
    trail file by sprint.id, and writes nothing back to it - review has no
    state.json field, the same shape as cost. Gate 3 (SK-051) reads
    runs/<id>/review.jsonl directly; nothing re-parses prose.

    SK-055: the recorded --confidence is cross-checked against PAR's fixed
    aggregation rule (review.aggregate) before anything is written - a
    finding reported by both reviewers can only be high confidence, and a
    finding reported by one reviewer can only be actionable. The rule has no
    negotiation, so a mismatched --confidence is refused, not accepted.
    """
    root = Path(root) if root is not None else Path.cwd()
    parsed_reviewer = parse_reviewer(reviewer, "review --reviewer")
    parsed_severity = parse_severity(severity, "review --severity")
    parsed_confidence = parse_confidence(confidence, "review --confidence")
    for flag, value in (("--finding", finding), ("--location", location)):
        if not (value or "").strip():
            raise StateError(f"a review finding requires a non-empty {flag}")

    severity_a = parsed_severity if parsed_reviewer in ("reviewer-a", "both") else None
    severity_b = parsed_severity if parsed_reviewer in ("reviewer-b", "both") else None
    expected_confidence, _ = aggregate(severity_a, severity_b)
    if parsed_confidence != expected_confidence:
        raise StateError(
            f"--reviewer {parsed_reviewer} --severity {parsed_severity} requires "
            f"--confidence {expected_confidence} (PAR's fixed aggregation rule, no negotiation); "
            f"got --confidence {parsed_confidence}"
        )

    state = store.load_state(store.state_path(root))
    review_file = store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / "review.jsonl"
    store.append_jsonl(
        review_file,
        {
            "reviewer": parsed_reviewer,
            "severity": parsed_severity,
            "confidence": parsed_confidence,
            "finding": finding,
            "location": location,
            "at": store.now_utc_iso(),
        },
    )
```

The finding/location empty-checks stay ahead of the new aggregation check, so the existing
parametrized refusal tests (`unknown reviewer`, `unknown severity`, `unknown confidence`,
`non-empty --finding`, `non-empty --location`) keep failing for their own original reasons, before
the aggregation check is ever reached.

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `uv run pytest tests/test_review.py -k "contradicts_the_fixed_aggregation_rule or refuses_a_both_reviewer" -v`
Expected: PASS (5 cases: 3 parametrized + 1 CLI test = 4 test IDs, all green).

- [ ] **Step 5: Run the full review test file and the full suite**

Run: `uv run pytest tests/test_review.py -v`
Expected: every test in the file PASSES, including the pre-existing
`test_records_one_line_and_touches_nothing_in_state_json`,
`test_both_is_a_legal_reviewer_value_for_a_finding_matched_across_both`, and
`test_cli_records_and_refuses_with_the_right_exit_codes` — their `--reviewer`/`--confidence` pairs
(`reviewer-a`/`actionable`, `both`/`high`, `reviewer-b`/`actionable`) already satisfy the new rule.

Run: `uv run pytest -q`
Expected: full suite PASSES, no regressions elsewhere.

Run: `uv run ruff check`
Expected: no lint errors.

- [ ] **Step 6: Flip the backlog row and commit**

In `docs/plans/sprints/backlog-01/backlog.md`, change the SK-055 row's status cell from `☐` to `☑`
(line 146, last column).

```bash
git add scripts/supskill_state/commands.py tests/test_review.py docs/plans/sprints/backlog-01/backlog.md
git commit -m "feat: refuse a review finding whose confidence contradicts PAR's aggregation rule"
```

---

### Task 2: SK-056 — add the `replan-guard` CLI subcommand

**Files:**
- Modify: `scripts/supskill_state/cli.py:9` (import line)
- Modify: `scripts/supskill_state/cli.py` (`build_parser`, add `_add_replan_guard(subparsers)`)
- Modify: `scripts/supskill_state/cli.py` (new `_add_replan_guard` / `_cmd_replan_guard` functions)
- Test: `tests/test_replan_guard.py` (append CLI tests)

**Interfaces:**
- Consumes: `replan_guard.REPLAN_SHAPES: tuple[str, ...]`, `replan_guard.is_supersede(shape: str) -> bool`,
  `replan_guard.refusal(shape: str) -> str` from `scripts/supskill_state/replan_guard.py` (all
  existing, unmodified).
- Produces: a new `supskill-state replan-guard --shape <shape>` CLI command. Exit 0 and prints
  `f"replan-guard: {shape} is an amending shape, not a supersede"` to stdout for the first three
  `REPLAN_SHAPES`; exit 1 and prints `replan_guard.refusal(shape)` to stderr for
  `"north-star-reset"`. `--shape` is `choices`-restricted to `REPLAN_SHAPES`, so an unrecognized
  value is rejected by argparse itself (exit 2) before reaching `is_supersede`.

- [ ] **Step 1: Write the failing tests**

Open `tests/test_replan_guard.py`. Add `from supskill_state.cli import main` to the imports (after
the existing `from supskill_state import commands` line). Then append these two tests at the end of
the file, after `test_every_trail_file_this_module_writes_is_jsonl_never_markdown`:

```python
# --- the CLI call site: SK-056 ---

def test_cli_exit_codes_for_replan_guard(capsys):
    assert main(["replan-guard", "--shape", "generative-writeback"]) == 0
    assert "is an amending shape" in capsys.readouterr().out

    assert main(["replan-guard", "--shape", "north-star-reset"]) == 1
    err = capsys.readouterr().err
    assert "operator's alone" in err
    assert "author the new backlog by hand" in err


def test_replan_guard_needs_no_state_file(tmp_path, monkeypatch):
    # it is a query, not a verb: it must work before init and after a wipe, like plan-guard
    monkeypatch.chdir(tmp_path)
    assert main(["replan-guard", "--shape", "park-at-boundary"]) == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_replan_guard.py -k replan_guard_for_or_replan_guard_needs -v`
Expected: both FAIL with `argparse` reporting `invalid choice: 'replan-guard'` (exit code 2, not 0/1)
— the subcommand does not exist yet.

- [ ] **Step 3: Wire the CLI subcommand**

In `scripts/supskill_state/cli.py`, change line 9 from:

```python
from . import commands, plan_guard, worktree
```

to:

```python
from . import commands, plan_guard, replan_guard, worktree
```

In `build_parser`, add the new subcommand registration right after `_add_plan_guard(subparsers)`:

```python
    _add_plan_guard(subparsers)
    _add_replan_guard(subparsers)
    _add_worktree(subparsers)
```

Then add the two new functions immediately after `_cmd_plan_guard` (right before the
`def _add_worktree(subparsers) -> None:` section):

```python
def _add_replan_guard(subparsers) -> None:
    sub = subparsers.add_parser(
        "replan-guard",
        help="does this Gate 3 replan shape read as a north-star supersede? exit 1 means refuse",
    )
    sub.add_argument(
        "--shape",
        required=True,
        choices=list(replan_guard.REPLAN_SHAPES),
        help="the conductor's own classification of the operator's Gate 3 answer",
    )
    sub.set_defaults(func=_cmd_replan_guard)


def _cmd_replan_guard(args) -> int:
    if replan_guard.is_supersede(args.shape):
        print(replan_guard.refusal(args.shape), file=sys.stderr)
        return 1
    print(f"replan-guard: {args.shape} is an amending shape, not a supersede")
    return 0
```

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `uv run pytest tests/test_replan_guard.py -v`
Expected: every test in the file PASSES, including the two new ones and every pre-existing pure-function
test (`is_supersede`, `refusal`, the two structural regressions) — none of those were touched.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: PASSES, no regressions.

Run: `uv run ruff check`
Expected: no lint errors.

- [ ] **Step 6: Commit**

```bash
git add scripts/supskill_state/cli.py tests/test_replan_guard.py
git commit -m "feat: add a replan-guard CLI subcommand for Gate 3's north-star-supersede check"
```

---

### Task 3: SK-056 — wire Gate 3's prose to the new command

**Files:**
- Modify: `skills/supskill/SKILL.md:484-486` (the "Refusing a north-star supersede" subsection)
- Modify: `skills/supskill/references/replan-shapes.md` (the "Shape 4 — north-star reset" section)
- Test: `tests/test_review_prose.py` (append one new test)

**Interfaces:**
- Consumes: the `replan-guard --shape <shape>` command from Task 2.
- Produces: no code interface — this task is prose only. The existing substring-assertion tests in
  `tests/test_review_prose.py` (`test_gate_3_section_wires_in_the_refusal_subsection_right_after_it`,
  `test_the_refusal_subsection_matches_the_guard_functions_own_language`,
  `test_shape_4_points_at_the_refusal_and_adds_no_mutator`) must keep passing unmodified — every
  substring they assert on is preserved verbatim in the new text below.

- [ ] **Step 1: Write the failing test**

Open `tests/test_review_prose.py`. Add this test immediately after
`test_the_refusal_subsection_matches_the_guard_functions_own_language`:

```python
def test_the_refusal_subsection_names_the_replan_guard_command():
    section = gate3_section()
    assert "replan-guard --shape" in section
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_review_prose.py -k replan_guard_command -v`
Expected: FAIL — `"replan-guard --shape"` is not yet in `SKILL.md`'s Gate 3 section.

- [ ] **Step 3: Update `SKILL.md`'s "Refusing a north-star supersede" subsection**

In `skills/supskill/SKILL.md`, replace lines 484-486:

```markdown
### Refusing a north-star supersede

No code path here can rewrite `backlog.md`'s North star or repoint `state.json.backlog` (true today by construction; a regression test guards it). A Shape-4 reading gets a report, never a `gate` call, a draft, or an edit - the move is the operator's alone: author the new backlog by hand, then start the next sprint against it.
```

with:

```markdown
### Refusing a north-star supersede

No code path here can rewrite `backlog.md`'s North star or repoint `state.json.backlog` (true today by construction; a regression test guards it). Confirm your own classification against [references/replan-shapes.md](references/replan-shapes.md) with `replan-guard --shape <generative-writeback|park-at-boundary|fork-on-live-evidence|north-star-reset>`: on the first three shapes it exits 0 and you continue as that shape's row describes; on `north-star-reset` it exits 1 and prints the refusal verbatim on stderr - relay that text to the operator. A Shape-4 reading gets a report, never a `gate` call, a draft, or an edit - the move is the operator's alone: author the new backlog by hand, then start the next sprint against it.
```

- [ ] **Step 4: Update `replan-shapes.md`'s Shape 4 section**

In `skills/supskill/references/replan-shapes.md`, replace:

```markdown
## Shape 4 — north-star reset

Out of scope by construction: no verb reachable from any shape above
supersedes `backlog.md` wholesale. See `SKILL.md`'s "Refusing a north-star
supersede".
```

with:

```markdown
## Shape 4 — north-star reset

Out of scope by construction: no verb reachable from any shape above
supersedes `backlog.md` wholesale. `replan-guard --shape north-star-reset`
confirms this reading and prints the refusal verbatim, read-only like
`plan-guard`. See `SKILL.md`'s "Refusing a north-star supersede".
```

- [ ] **Step 5: Run the new test, the full prose file, and the full suite**

Run: `uv run pytest tests/test_review_prose.py -v`
Expected: every test in the file PASSES — the new one and every pre-existing substring assertion.

Run: `uv run pytest -q`
Expected: PASSES.

Run: `uv run ruff check`
Expected: no lint errors (markdown files are not linted by ruff; this confirms nothing else broke).

- [ ] **Step 6: Flip the backlog row and commit**

In `docs/plans/sprints/backlog-01/backlog.md`, change the SK-056 row's status cell from `☐` to `☑`
(line 147, last column).

```bash
git add skills/supskill/SKILL.md skills/supskill/references/replan-shapes.md tests/test_review_prose.py docs/plans/sprints/backlog-01/backlog.md
git commit -m "docs: wire Gate 3's north-star-supersede prose to the replan-guard command"
```

---

## Self-review notes

- **Spec coverage:** SK-055 (Task 1) and SK-056 (Tasks 2-3) are both fully covered; Task 3's prose
  change is split from Task 2's CLI change because a reviewer could plausibly accept the CLI wiring
  while asking for different wording in the SKILL.md subsection.
- **No dead code left behind:** `aggregate()` now has a production caller
  (`commands.record_review_finding`), which itself calls `worse_severity()` internally
  (`review.py:61`). `is_supersede()`/`refusal()` now have a production caller
  (`cli._cmd_replan_guard`). Neither `review.py` nor `replan_guard.py` needed any changes — only
  their call sites were missing, exactly as both backlog rows diagnosed.
- **No test regressions:** every existing assertion in `tests/test_review.py`,
  `tests/test_replan_guard.py`, and `tests/test_review_prose.py` was traced against the new code and
  confirmed to still hold (documented inline in Task 1 Step 3 and Task 3's Interfaces section).
