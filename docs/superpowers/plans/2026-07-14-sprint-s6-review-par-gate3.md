# Sprint 06 — REVIEW (PAR) + Gate 3 + replan shapes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> Execution mode for this sprint is already decided: **subagent-driven**, fresh subagent per task, review between tasks.

**Goal:** The conductor closes the sprint loop: two adversarial reviewer subagents score the executed branch under a fixed, no-negotiation aggregation rule (PAR); Gate 3 batches that plus E5's blocker/concern batch into one decision; the operator's answer resolves into exactly one of four defined replan shapes — a north-star reset is structurally refused, never performed — and the conductor proposes the next sprint and stops.

**Architecture:** Same split as every prior sprint (D2): `supskill-state` is the only mutator, skill prose is the choreography. The CLI gains one verb, `review` (append-only `runs/<id>/review.jsonl`, no `state.json` schema bump — the same shape as `cost`), and one additive change to `GATE_DECISIONS` (`replan` joins `approved`/`rejected`). Two new pure-Python modules carry this sprint's offline-provable logic: `review.py` (the severity/confidence vocabulary and the aggregation rule) and `replan_guard.py` (the north-star-supersede refusal, the same shape as `plan_guard.py`'s `head_moved`). `skills/supskill/SKILL.md` gains a `## The REVIEW stage`, a `## Gate 3` section, a `### Refusing a north-star supersede` subsection, and a `## Propose the next sprint, then stop` section — all necessarily terse, because the file's body is **already at its 500-line hard cap today** (verified: exactly 500 lines). Making room is this plan's own first finding: Gate 1 and Gate 2 shrink to a shared `references/gate.md` (the extraction sprint-04 named as E6's trigger), and PAR's dispatch/aggregation detail and the four replan shapes' mechanics move to `references/review-notes.md` and `references/replan-shapes.md` respectively — conductor-facing reference docs, the same pattern `references/invocation-model.md` already established.

**Tech Stack:** Python ≥3.11 stdlib only (zero runtime deps), pytest + ruff + pyyaml as dev deps, managed with `uv`. Claude Code plugin layout unchanged. `superpowers` **6.1.1** is the composed skill's pinned version (unchanged from S5; this sprint composes no new SDD/writing-plans surface).

## Global Constraints

Copied from the sprint spec (`docs/plans/sprints/backlog-01/sprint-s6-review-par-gate3.md`) and the standing project rules. Every task's requirements implicitly include this section.

- **Tests:** `uv run pytest`. The suite is **pure offline** — no LLM call, no subagent, no network, anywhere under `tests/`. Baseline at the tip of `main` (`8105d2f`): **251 passed in ~0.5s**. Every task ends with the full suite green.
- **Lint:** `uv run ruff check` must stay clean. Config is `pyproject.toml:22-32` — `line-length = 120`, rules `E,F,I,B,UP`, `src = ["scripts", "tests"]`. Every code block in this plan passes those rules as written: `from __future__ import annotations` where the module needs it, no unused imports, no line over 120 chars.
- **Zero runtime dependencies:** `pyproject.toml` `[project] dependencies = []` (`pyproject.toml:6`), enforced by `tests/test_scaffold.py`. Nothing this sprint needs a dependency.
- **No AI attribution of any kind in commit messages or bodies** — no `Co-Authored-By`, no "Generated with" line, no mention of Claude/Anthropic/AI. Absolute; overrides any harness default.
- **Invariant 3 — no dispatched agent runs `supskill-state` or touches `.supskill/`.** This sprint's own version: a reviewer that can write its own finding record, or a reviewer that can see the other reviewer's output, defeats PAR's entire point (F-5, D9). The conductor dispatches both reviewers before reading either's output, and records every finding itself, after both return.
- **Invariant 2 / D4 — dispatched agents can never ask anyone anything.** `AskUserQuestion` is stripped from subagents and auto-resolves empty in headless. `references/review-prompt.md` states this explicitly, the same pattern every prior dispatch template uses.
- **Invariant 7 — the conductor never supersedes a backlog on its own.** A north-star reset is operator-authored, full stop. This sprint is where that stops being aspirational: `replan_guard.py`'s `is_supersede` plus the regression tests in Task 3 prove the structural claim continues to hold.
- **D6 — one sprint per invocation.** The conductor proposes the next sprint's epic and stops; it issues no further tool call after the proposal.
- **The hard 500-line body cap on `skills/supskill/SKILL.md` is binding, starting from zero headroom.** Verified today: the body (everything after the closing `---` of the frontmatter) is **exactly 500 lines** — `tests/test_skill_frontmatter.py:75-77`'s cap with no slack left. This plan's own SKILL.md edits were drafted and measured against a real copy of the file before being written into this document: the net result of every SKILL.md-touching task in this plan (Tasks 5, 6, 8, 9 combined) is a body of **478 lines** — 22 lines of headroom, not zero. If your own wording runs longer and pushes past 500, the fix is never to shorten the load-bearing routing lines (`\`approved\` → ...`, the exact CLI command lines) — it is to move more prose out of `SKILL.md` and into the relevant `references/*.md` file, replacing it with a one-line pointer. Re-run `uv run pytest tests/test_skill_frontmatter.py::test_body_stays_under_500_lines` after every `SKILL.md` edit, not just at the end of a task.
- **The state CLI is always invoked as `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state`, from the target repo's root.** Unchanged from every prior sprint.
- **Commits:** one per task minimum, TDD evidence first (a failing test run before implementation).
- **Commands:** tests `uv run pytest <path> -v`, lint `uv run ruff check`.

## File Structure

| Path | Task | Responsibility |
|---|---|---|
| `scripts/supskill_state/review.py` | 1 (create) | Severity/confidence/reviewer vocabulary, `worse_severity`, and `aggregate` — PAR's whole aggregation rule as one pure function |
| `scripts/supskill_state/commands.py` | 1 (modify) | `record_review_finding` — the verb, its refusals, its trail |
| `scripts/supskill_state/cli.py` | 1 (modify), 2 (modify) | the `review` subcommand; `gate --decision` gains `replan` |
| `tests/test_review.py` | 1 (create) | the verb and the aggregation rule, both offline |
| `scripts/supskill_state/model.py` | 2 (modify) | `GATE_DECISIONS` grows to `("approved", "rejected", "replan")` |
| `tests/test_gate.py` | 2 (extend) | `replan` is a legal, recordable G3 decision |
| `scripts/supskill_state/replan_guard.py` | 3 (create) | the four replan shapes named; `is_supersede`, `refusal` — the guard, TDD'd offline |
| `tests/test_replan_guard.py` | 3 (create) | the guard function, plus the structural regression (no `state.backlog` assignment outside `init_sprint`; every trail file this module writes is `.jsonl`) |
| `skills/supskill/references/review-prompt.md` | 4 (create) | the PAR dispatch template, filled twice, no cross-visibility |
| `tests/test_prompt_templates.py` | 4 (extend) | `TEMPLATES` grows to four; the review template's placeholders and standing constraints |
| `skills/supskill/references/review-notes.md` | 5 (create) | PAR's dispatch/matching/aggregation detail and the `review` verb's exact flags — conductor-facing, not sent to any subagent |
| `skills/supskill/SKILL.md` | 5, 6, 8, 9 (modify) | dispatch table's REVIEW row; the REVIEW-stub paragraph removed; Gate 1/Gate 2 shrink to point at `gate.md`; `## The REVIEW stage`, `## Gate 3`, `### Refusing a north-star supersede`, `## Propose the next sprint, then stop` — frontmatter untouched |
| `skills/supskill/references/gate.md` | 6 (create) | the three steps shared by every gate (ask for real, refuse an empty answer, record verbatim) |
| `tests/test_review_prose.py` | 5 (create), 6, 7, 8, 9 (extend) | prose tripwires for every SKILL.md/`references/*.md` surface this sprint adds |
| `skills/supskill/references/replan-shapes.md` | 7 (create) | the three amending shapes' mechanics; Shape 4 points at the refusal |
| `.superpowers/sdd/s6/demo-checklist.md` | 10 (create, gitignored) | the operator-run demo — the sprint's real exit criterion |
| `docs/plans/sprints/backlog-01/backlog.md` | 11 (modify) | the S6 DoR backlog deltas, plus marking E5's shipped rows |

**Task order honors the sprint doc's own "Capacity & sequencing" waves.** Wave A (Tasks 1–3) is pure offline Python, independent of every line of prose in this sprint, and independent of each other — write it first for the same reason S5 wrote SK-043 first: later prose describes commands that must already exist and refuse correctly. Wave B (Tasks 4–6) is prose and dispatch discipline, and runs in order: 4 (the template) → 5 (the REVIEW stage that dispatches it, and which needs Task 1's verb to exist) → 6 (`gate.md`'s extraction and Gate 3, which needs Task 2's `GATE_DECISIONS` value to be legal). Wave C (Tasks 7–8) are disjoint code paths — the three amending shapes' *content* (Task 7, a new reference doc only) versus the refusal's *wiring* into the section Task 6 created (Task 8, a `SKILL.md` append) — and could run in either order or in parallel; this plan sequences them 7 then 8 only because Task 8's step 1 appends immediately after the anchor Task 6 left, and doing so right after Task 6 (rather than after an intervening Task 7) keeps that diff small. Wave D (Task 9) is last: the proposal is only meaningful once a replan shape or the refusal has actually resolved the sprint, and it appends after Task 8's own new subsection. Task 10 needs 1–9. Task 11 is docs-only and independent of everything.

---

### Task 1: The `review` verb and PAR's aggregation rule (SK-050)

**Files:**
- Create: `scripts/supskill_state/review.py`
- Modify: `scripts/supskill_state/commands.py` (new `record_review_finding`, appended after `record_cost`)
- Modify: `scripts/supskill_state/cli.py:20-30` (register the subparser) plus a new `_add_review` / `_cmd_review` pair, appended after `_cmd_cost`
- Test: `tests/test_review.py` (create)

**Interfaces:**
- Consumes: `store.load_state` / `store.append_jsonl` (`scripts/supskill_state/store.py:64-70`) / `store.now_utc_iso` (`scripts/supskill_state/store.py:73-74`) / `store.runs_dir` (`scripts/supskill_state/store.py:37-38`); `normalize_sprint_id` (`scripts/supskill_state/scratch.py:19-26`); `StateError`.
- Produces (Task 5's prose calls this exact CLI surface; SK-051's Gate 3 reads this exact trail):
  - `review.SEVERITY_TOKENS`, `review.CONFIDENCE_TOKENS`, `review.REVIEWER_TOKENS` — the closed vocabularies.
  - `review.worse_severity(a: str, b: str) -> str` — pure; `Critical > Important > Minor`, order never matters.
  - `review.aggregate(severity_a: str | None, severity_b: str | None) -> tuple[str, str]` — pure; returns `(confidence, severity)` for one already-matched finding.
  - `review.parse_severity(value, where) -> str`, `review.parse_confidence(value, where) -> str`, `review.parse_reviewer(value, where) -> str` — each raises `StateError` naming the valid tokens.
  - `commands.record_review_finding(reviewer: str, severity: str, confidence: str, finding: str, location: str, root: Path | None = None) -> None`.
  - CLI: `supskill-state review --reviewer <reviewer-a|reviewer-b|both> --severity <Critical|Important|Minor> --confidence <high|actionable> --finding "<...>" --location "<...>"` — exit 0 prints `recorded review finding: <reviewer> <severity>/<confidence>`; exit 1 on any refusal.
  - Trail: `.supskill/runs/<normalized-sprint-id>/review.jsonl`, one JSON object per line, `{"reviewer", "severity", "confidence", "finding", "location", "at"}` — the sibling of `blockers.jsonl`/`tasks.jsonl`/`costs.jsonl`.

**The defect this closes** (S6 DoR finding 1). `cli.py`'s full subcommand list is `init | show | artifact | gate | block | task | tasks | advance | plan-guard | cost` (`scripts/supskill_state/cli.py:21-30`) — no `review`. There is no finding shape in `model.py`, no writer in `commands.py`, and no `runs/<id>/review.jsonl` anywhere. "Aggregated findings are written to disk" is not yet a fact about this codebase.

**Why a new module and not a schema field.** Like `costs.jsonl` (`scripts/supskill_state/commands.py:390-434`), `review` is pure telemetry with no `state.json` mirror: it reads state only to place the trail file by `sprint.id`, and writes nothing back. `worse_severity`/`aggregate` live in their own module rather than `model.py` because they carry no schema — `review` has no dataclass, the same way `cost` has none — and because the module is this story's whole offline-provable slice, callable and testable with zero CLI or state machinery, the same shape `plan_guard.py` gives `head_moved`.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_review.py`:

```python
"""SK-050: the review verb + PAR's aggregation rule.

Two slices, both offline: (1) the review verb - Critical|Important|Minor x
high|actionable, appended trail-first to runs/<id>/review.jsonl, exactly
like blockers.jsonl/tasks.jsonl/costs.jsonl (commands.py:256-269, :380-384,
:422-434) but with no state.json mirror - review has no schema field, the
same shape as cost; (2) the aggregation rule itself, review.aggregate(), a
pure function of an already-matched finding's reported severities. Matching
which finding from reviewer-a corresponds to which from reviewer-b is the
conductor's own judgment, done in prose - not this module's job, and not
tested here.
"""

import json

import pytest

from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_review_finding
from supskill_state.errors import StateError
from supskill_state.review import aggregate, worse_severity
from supskill_state.store import require_aware_utc_iso, runs_dir, state_path


def _reviews(tmp_path, sprint_dir="s6"):
    path = runs_dir(tmp_path) / sprint_dir / "review.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_records_one_line_and_touches_nothing_in_state_json(tmp_path):
    init_sprint("s6", backlog="backlog.md", root=tmp_path)
    before = state_path(tmp_path).read_bytes()

    record_review_finding(
        "reviewer-a", "Critical", "actionable",
        "auth_middleware is never called from the router", "src/auth.py:41",
        root=tmp_path,
    )

    assert state_path(tmp_path).read_bytes() == before  # pure telemetry, like cost
    lines = _reviews(tmp_path)
    assert len(lines) == 1
    require_aware_utc_iso(lines[0].pop("at"), "review.jsonl at")
    assert lines[0] == {
        "reviewer": "reviewer-a",
        "severity": "Critical",
        "confidence": "actionable",
        "finding": "auth_middleware is never called from the router",
        "location": "src/auth.py:41",
    }


@pytest.mark.parametrize(
    "overrides,match",
    [
        ({"reviewer": "reviewer-c"}, "unknown reviewer"),
        ({"severity": "Blocker"}, "unknown severity"),
        ({"confidence": "certain"}, "unknown confidence"),
        ({"finding": ""}, "non-empty --finding"),
        ({"finding": "   "}, "non-empty --finding"),
        ({"location": ""}, "non-empty --location"),
    ],
)
def test_the_vocabulary_and_the_two_required_fields_are_refused_with_nothing_written(tmp_path, overrides, match):
    init_sprint("s6", backlog="backlog.md", root=tmp_path)
    call = {
        "reviewer": "reviewer-a", "severity": "Critical", "confidence": "high",
        "finding": "a finding", "location": "src/x.py:1",
    }
    call.update(overrides)
    with pytest.raises(StateError, match=match):
        record_review_finding(
            call["reviewer"], call["severity"], call["confidence"], call["finding"], call["location"],
            root=tmp_path,
        )
    assert _reviews(tmp_path) == []


def test_both_is_a_legal_reviewer_value_for_a_finding_matched_across_both(tmp_path):
    init_sprint("s6", backlog="backlog.md", root=tmp_path)
    record_review_finding("both", "Important", "high", "matched by both reviewers", "src/y.py:9", root=tmp_path)
    assert _reviews(tmp_path)[0]["reviewer"] == "both"


def test_cli_records_and_refuses_with_the_right_exit_codes(tmp_path, monkeypatch, capsys):
    init_sprint("s6", backlog="backlog.md", root=tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main([
        "review", "--reviewer", "reviewer-b", "--severity", "Minor", "--confidence", "actionable",
        "--finding", "a nit", "--location", "src/z.py:3",
    ]) == 0
    assert "recorded review finding: reviewer-b Minor/actionable" in capsys.readouterr().out

    assert main([
        "review", "--reviewer", "nope", "--severity", "Minor", "--confidence", "actionable",
        "--finding", "x", "--location", "y",
    ]) == 1
    assert "unknown reviewer" in capsys.readouterr().err


# --- the aggregation rule: a pure function of an already-matched finding ---

def test_both_reviewers_agree_is_high_confidence_at_that_severity():
    assert aggregate("Important", "Important") == ("high", "Important")


def test_disagreement_always_takes_the_worse_severity_never_the_better():
    assert aggregate("Minor", "Critical") == ("high", "Critical")
    assert aggregate("Critical", "Minor") == ("high", "Critical")  # order never matters
    assert aggregate("Important", "Minor") == ("high", "Important")


def test_one_reviewer_only_is_actionable_at_that_reviewers_severity():
    assert aggregate("Important", None) == ("actionable", "Important")
    assert aggregate(None, "Minor") == ("actionable", "Minor")


def test_aggregate_refuses_a_finding_neither_reviewer_reported():
    with pytest.raises(StateError, match="at least one reviewer"):
        aggregate(None, None)


@pytest.mark.parametrize(
    "a,b,worse",
    [
        ("Critical", "Important", "Critical"),
        ("Important", "Minor", "Important"),
        ("Minor", "Minor", "Minor"),
        ("Critical", "Critical", "Critical"),
    ],
)
def test_worse_severity_ranks_critical_over_important_over_minor(a, b, worse):
    assert worse_severity(a, b) == worse
    assert worse_severity(b, a) == worse  # order never matters
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_review.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'supskill_state.review'`.

- [ ] **Step 3: Write `review.py`**

Create `scripts/supskill_state/review.py`:

```python
"""PAR's severity/confidence vocabulary and its aggregation rule (SK-050).

D9: two reviewer subagents on identical input, aggregated by a FIXED rule -
same finding reported by both -> confidence=high; found by one reviewer only
-> confidence=actionable; the two reviewers disagree on severity -> the worse
one wins, always, no negotiation. Ranked Critical > Important > Minor - the
same three-level vocabulary this repo already imported from SDD for EXECUTE's
fix trigger and roll-up (skills/supskill/SKILL.md:383-385).

Which finding from reviewer-a corresponds to which from reviewer-b is the
conductor's own judgment, done in prose at REVIEW time - matching two finding
lists is not a pure function of their contents, and this module does not try.
What IS pure, and is this story's whole offline-provable slice: given one
already-matched finding's severity as reported by each reviewer that DID
report it (None for a reviewer that did not), what confidence and severity
the fixed rule assigns. That is the whole rule, stated once, in aggregate().
"""

from __future__ import annotations

from .errors import StateError

# worst-first: index 0 always wins a disagreement
SEVERITY_TOKENS: tuple[str, ...] = ("Critical", "Important", "Minor")
CONFIDENCE_TOKENS: tuple[str, ...] = ("high", "actionable")
REVIEWER_TOKENS: tuple[str, ...] = ("reviewer-a", "reviewer-b", "both")


def parse_severity(value: str, where: str) -> str:
    if value not in SEVERITY_TOKENS:
        raise StateError(f"{where}: unknown severity {value!r}; expected one of {list(SEVERITY_TOKENS)}")
    return value


def parse_confidence(value: str, where: str) -> str:
    if value not in CONFIDENCE_TOKENS:
        raise StateError(f"{where}: unknown confidence {value!r}; expected one of {list(CONFIDENCE_TOKENS)}")
    return value


def parse_reviewer(value: str, where: str) -> str:
    if value not in REVIEWER_TOKENS:
        raise StateError(f"{where}: unknown reviewer {value!r}; expected one of {list(REVIEWER_TOKENS)}")
    return value


def worse_severity(a: str, b: str) -> str:
    """Critical > Important > Minor. The worse of the two always wins - no negotiation."""
    return a if SEVERITY_TOKENS.index(a) <= SEVERITY_TOKENS.index(b) else b


def aggregate(severity_a: str | None, severity_b: str | None) -> tuple[str, str]:
    """The whole aggregation rule, as a pure function of an already-matched finding.

    severity_a / severity_b: the severity EACH reviewer reported for this ONE
    matched finding, or None if that reviewer did not report it. Matching
    findings across the two reviewers' lists is the conductor's job, done
    before this is ever called - this function never sees the raw lists.
    """
    if severity_a is not None and severity_b is not None:
        return "high", worse_severity(severity_a, severity_b)
    single = severity_a or severity_b
    if single is None:
        raise StateError("aggregate: at least one reviewer must have reported this finding")
    return "actionable", single
```

- [ ] **Step 4: Implement the verb**

In `scripts/supskill_state/commands.py`, add to the local-package imports (after the existing `from .plan_coverage import validate_plan_coverage` block):

```python
from .review import parse_confidence, parse_reviewer, parse_severity
```

Append after `record_cost` (before `advance_stage`):

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
    """
    root = Path(root) if root is not None else Path.cwd()
    parsed_reviewer = parse_reviewer(reviewer, "review --reviewer")
    parsed_severity = parse_severity(severity, "review --severity")
    parsed_confidence = parse_confidence(confidence, "review --confidence")
    for flag, value in (("--finding", finding), ("--location", location)):
        if not (value or "").strip():
            raise StateError(f"a review finding requires a non-empty {flag}")

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

In `scripts/supskill_state/cli.py`, register the subparser in `build_parser` (after `_add_cost(subparsers)`, `scripts/supskill_state/cli.py:30`):

```python
    _add_cost(subparsers)
    _add_review(subparsers)
    return parser
```

and add the pair, appended after `_cmd_cost` (before `def main`):

```python
def _add_review(subparsers) -> None:
    sub = subparsers.add_parser(
        "review", help="record one aggregated PAR finding to runs/<id>/review.jsonl"
    )
    sub.add_argument("--reviewer", required=True, help="reviewer-a | reviewer-b | both")
    sub.add_argument("--severity", required=True, help="Critical | Important | Minor")
    sub.add_argument("--confidence", required=True, help="high | actionable")
    sub.add_argument("--finding", required=True, help="what was found, in your own words")
    sub.add_argument("--location", required=True, help="file:line or path")
    sub.set_defaults(func=_cmd_review)


def _cmd_review(args) -> int:
    commands.record_review_finding(args.reviewer, args.severity, args.confidence, args.finding, args.location)
    print(f"recorded review finding: {args.reviewer} {args.severity}/{args.confidence}")
    return 0
```

`--reviewer`/`--severity`/`--confidence` deliberately take free strings rather than argparse `choices`, the same reasoning `task --status` used (`scripts/supskill_state/cli.py:130-135`): a refusal must arrive as `supskill-state: refused: … unknown severity …` on exit 1, not as argparse's exit-2 usage error.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_review.py -v && uv run pytest && uv run ruff check`
Expected: all PASS — 251 baseline + the new tests, none broken.

- [ ] **Step 6: Commit**

```bash
git add scripts/supskill_state/review.py scripts/supskill_state/commands.py \
        scripts/supskill_state/cli.py tests/test_review.py
git commit -m "feat: supskill-state review - PAR's aggregation rule and the verb that records a finding (SK-050)"
```

---

### Task 2: `GATE_DECISIONS` grows to include `replan` (SK-051)

**Files:**
- Modify: `scripts/supskill_state/model.py:61`
- Modify: `scripts/supskill_state/cli.py:92`
- Test: `tests/test_gate.py` (extend)

**Interfaces:**
- Consumes: `record_gate` (`scripts/supskill_state/commands.py:196-213`), which validates against `GATE_DECISIONS` generically and needs no further change.
- Produces: `--decision replan` becomes a legal, recordable value for any gate id — Task 6's Gate 3 section is this value's first real caller.

**The defect this closes** (S6 DoR finding 3). `GATE_DECISIONS` is `("approved", "rejected")` today (`scripts/supskill_state/model.py:61`), enforced identically in `cli.py`'s `choices=["approved", "rejected"]` (`scripts/supskill_state/cli.py:92`) and in `_parse_gates`' load-time validation (`scripts/supskill_state/model.py:174-178`, generic over the tuple — no further change needed there). A `gate --id G3 --decision replan` call is refused today with `unknown decision 'replan'; expected one of ['approved', 'rejected']` (`scripts/supskill_state/commands.py:200-201`). This is not an oversight to route around — S1's own sprint doc named it as a deliberate deferral: *"The decision vocabulary is deliberately minimal — G3's four replan shapes are E6's to add"* (`docs/plans/sprints/backlog-01/sprint-01-state-spine.md:104`). This task is where that IOU is paid.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gate.py`:

```python
def test_replan_is_a_legal_g3_decision_deliberately_deferred_since_s1(tmp_path):
    # sprint-01-state-spine.md:104: "G3's four replan shapes are E6's to add" - this pays that IOU
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_gate("G3", "replan", "shape 2: SK-041 parks at a live boundary", root=tmp_path)
    assert load_state(state_path(tmp_path)).gates["G3_review"] == "replan"
    assert _gate_lines(tmp_path)[0]["decision"] == "replan"


def test_cli_gate_accepts_replan(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s1", "--backlog", "backlog.md"]) == 0
    assert main(["gate", "--id", "G3", "--decision", "replan", "--response", "shape 1: writeback"]) == 0
    assert load_state(state_path(tmp_path)).gates["G3_review"] == "replan"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_gate.py -v`
Expected: the two new tests FAIL — `supskill_state.errors.StateError: unknown decision 'replan'; expected one of ['approved', 'rejected']` (raised from `record_gate`, or surfaced as exit 1 by the CLI test).

- [ ] **Step 3: Grow the vocabulary**

In `scripts/supskill_state/model.py`, replace line 61:

```python
GATE_DECISIONS: tuple[str, str, str] = ("approved", "rejected", "replan")
```

In `scripts/supskill_state/cli.py`, replace the `--decision` argument in `_add_gate` (`scripts/supskill_state/cli.py:92`):

```python
    sub.add_argument("--decision", required=True, choices=["approved", "rejected", "replan"])
```

No other change: `_parse_gates` (`scripts/supskill_state/model.py:166-180`) validates against `GATE_DECISIONS` generically, and `record_gate` (`scripts/supskill_state/commands.py:196-213`) does the same.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_gate.py -v && uv run pytest && uv run ruff check`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/supskill_state/model.py scripts/supskill_state/cli.py tests/test_gate.py
git commit -m "feat: GATE_DECISIONS grows to include replan - S1's own deferred IOU, paid (SK-051)"
```

---

### Task 3: Refuse a north-star supersede — the guard function (SK-053)

**Files:**
- Create: `scripts/supskill_state/replan_guard.py`
- Test: `tests/test_replan_guard.py` (create)

**Interfaces:**
- Consumes: nothing from other tasks — pure, offline, no dependency on Tasks 1–2.
- Produces: `replan_guard.REPLAN_SHAPES`, `replan_guard.AMENDING_SHAPES`, `replan_guard.is_supersede(shape: str) -> bool`, `replan_guard.refusal(shape: str) -> str`. Task 8's `SKILL.md` wiring names this module and this function; the sprint's own accept criteria call it "the same shape as `plan_guard.py`'s `head_moved` predicate."

**Context.** Invariant 7 states this without qualification: *"the conductor never supersedes a backlog on its own — a north-star reset is operator-authored, full stop."* The backlog gives no procedure for *detecting* a shape-4-shaped Gate 3 answer, so this task takes the smaller, reversible path named in the sprint doc: it does not try to classify intent from free text — that stays the conductor's own judgment, done in prose at Gate 3 — it removes the capability structurally and gives that judgment a name to refuse the instant it is reached.

**The structural half of this claim already holds today, for free**, and this task's regression tests prove it rather than merely asserting it. `state.backlog` is set exactly once in the whole codebase, as the `backlog=backlog` keyword argument to the `State(...)` constructor inside `init_sprint` (`scripts/supskill_state/commands.py:74-90`, the assignment itself at `:76`); no other function in `commands.py` sets it. And no verb anywhere edits `backlog.md`'s prose at all: every trail file `commands.py` ever opens for writing is built as `store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / "<name>"` (`scripts/supskill_state/commands.py:257`, `:380`, `:423`, and Task 1's new `:` line for `review.jsonl`), and every one of those names ends `.jsonl` — never `.md`. The only thing that has ever changed `backlog.md` is a person, by hand, in a `docs:` commit (`ec22e25`, `62fd0dc`, `133da28`).

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_replan_guard.py`:

```python
"""SK-053: refuse a north-star supersede, structurally.

Two kinds of proof: (1) the guard function itself, TDD'd purely offline -
the same shape as plan_guard.py's head_moved predicate, a pure check plus a
call site (Task 8) that reports and stops; (2) regression tests that the
structural claim it relies on still holds - state.backlog assigned nowhere
but init_sprint, and every trail file commands.py writes ends .jsonl, never
.md (the only way a verb could ever touch backlog.md).
"""

import re
from pathlib import Path

import pytest

from supskill_state import commands
from supskill_state.errors import StateError
from supskill_state.replan_guard import (
    AMENDING_SHAPES,
    REPLAN_SHAPES,
    is_supersede,
    refusal,
)


def test_replan_shapes_names_exactly_the_designs_own_four():
    # docs/.ai/reports/2026-07-12-supskill-design-decisions.md:244-254
    assert REPLAN_SHAPES == (
        "generative-writeback",
        "park-at-boundary",
        "fork-on-live-evidence",
        "north-star-reset",
    )
    assert AMENDING_SHAPES == REPLAN_SHAPES[:3]


@pytest.mark.parametrize("shape", AMENDING_SHAPES)
def test_the_first_three_shapes_amend_and_are_never_supersede(shape):
    assert is_supersede(shape) is False


def test_the_fourth_shape_is_the_one_that_is_always_refused():
    assert is_supersede("north-star-reset") is True


def test_an_unclassified_shape_is_refused_loudly_not_silently():
    with pytest.raises(StateError, match="unknown replan shape"):
        is_supersede("some other reading")


def test_the_refusal_names_the_operators_own_move_and_never_offers_to_help():
    text = refusal("north-star-reset")
    assert "operator's alone" in text
    assert "author the new backlog by hand" in text
    assert "not offered here for convenience" in text


def test_refusal_refuses_to_run_on_an_amending_shape():
    with pytest.raises(StateError, match="not the supersede shape"):
        refusal("generative-writeback")


# --- the structural regression: still true today, by construction ---

def test_state_backlog_is_constructed_nowhere_outside_init_sprint():
    source = Path(commands.__file__).read_text(encoding="utf-8")
    functions = re.split(r"\ndef ", source)
    offenders = [
        chunk.split("(", 1)[0]
        for chunk in functions[1:]
        if re.search(r"backlog\s*=", chunk) and not chunk.startswith("init_sprint")
    ]
    assert offenders == []


def test_every_trail_file_this_module_writes_is_jsonl_never_markdown():
    # the only way a verb could ever touch backlog.md is by naming it in a store
    # write call; every trail file commands.py builds names itself here, and every
    # one of those names must end .jsonl - backlog.md edits are a person's, by hand
    source = Path(commands.__file__).read_text(encoding="utf-8")
    names = re.findall(
        r'runs_dir\(root\)\s*/\s*normalize_sprint_id\(state\.sprint\.id\)\s*/\s*"([^"]+)"',
        source,
    )
    assert len(names) >= 4  # blockers, tasks, costs, review - grows, never shrinks silently
    assert all(name.endswith(".jsonl") for name in names)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_replan_guard.py -v`
Expected: every test FAILs — `ModuleNotFoundError: No module named 'supskill_state.replan_guard'`. The two structural-regression tests would pass even before this module exists (they assert facts about `commands.py` alone) — run them in isolation to confirm: `uv run pytest tests/test_replan_guard.py -v -k structural_regression_or_state_backlog_or_trail` is not needed; the whole file fails at collection because of the top-level `from supskill_state.replan_guard import ...`. State this in the commit message rather than manufacturing a separate red bar for those two.

- [ ] **Step 3: Write the guard**

Create `scripts/supskill_state/replan_guard.py`:

```python
"""SK-053: refuse a north-star-supersede reading of a Gate 3 answer, structurally.

Invariant 7: "the conductor never supersedes a backlog on its own - a
north-star reset is operator-authored, full stop." The backlog gives no
procedure for DETECTING a shape-4-shaped Gate 3 answer, and this module does
not try to build one: classifying what the operator's free-text answer means
is the conductor's own judgment, done in prose, at Gate 3 (Task 8). What this
module gives that judgment is a name for the fourth shape and a refusal that
fires the instant that name is reached - the same shape as plan_guard.py's
head_moved: a pure check plus a call site that reports and stops.

The structural half of invariant 7 already holds today, for free: state.backlog
is assigned exactly once in the whole codebase, inside init_sprint
(scripts/supskill_state/commands.py:74-90), and no verb anywhere edits
backlog.md's prose - the only thing that has ever changed that file is a
person, by hand, in a docs: commit. The regression tests beside this module
prove both halves of that claim, not merely assert them.
"""

from __future__ import annotations

from .errors import StateError

# the design's own table (docs/.ai/reports/2026-07-12-supskill-design-decisions.md:244-254)
REPLAN_SHAPES: tuple[str, ...] = (
    "generative-writeback",
    "park-at-boundary",
    "fork-on-live-evidence",
    "north-star-reset",
)

AMENDING_SHAPES: tuple[str, ...] = REPLAN_SHAPES[:3]
_SUPERSEDE_SHAPE = REPLAN_SHAPES[3]


def is_supersede(shape: str) -> bool:
    """True iff this classification is the one shape the conductor may never perform."""
    if shape not in REPLAN_SHAPES:
        raise StateError(f"unknown replan shape {shape!r}; expected one of {list(REPLAN_SHAPES)}")
    return shape == _SUPERSEDE_SHAPE


def refusal(shape: str) -> str:
    """What the conductor reports, verbatim, when a Gate 3 answer reads as shape 4."""
    if not is_supersede(shape):
        raise StateError(f"refusal() called on {shape!r}, which is not the supersede shape")
    return (
        "this Gate 3 answer reads as a north-star supersede - replacing backlog.md wholesale, "
        "not amending it.\n"
        "The conductor is structurally unable to perform this: no code path in this skill "
        "rewrites backlog.md's North star section or repoints state.json.backlog (invariant 7).\n"
        "Nothing was drafted and nothing was executed. The move is the operator's alone: author "
        "the new backlog by hand (or with whatever process produced this one), then start the "
        "next sprint against it.\n"
        "This run is stopped for you to take that step; it is not offered here for convenience."
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_replan_guard.py -v && uv run pytest && uv run ruff check`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/supskill_state/replan_guard.py tests/test_replan_guard.py
git commit -m "feat: refuse a north-star supersede - the guard function, plus regression proof it already holds structurally (SK-053)"
```

---

### Task 4: The PAR dispatch template (SK-050)

**Files:**
- Create: `skills/supskill/references/review-prompt.md`
- Modify: `tests/test_prompt_templates.py` (`TEMPLATES` grows to four; new review-specific assertions)

**Interfaces:**
- Consumes: nothing from other tasks — a static template, the same shape as `scope-prompt.md`/`refine-prompt.md`/`plan-prompt.md`.
- Produces: the filled-twice dispatch template Task 5's REVIEW stage names. `{REVIEWER_LABEL}`, `{REVIEW_PACKAGE_PATH}`, `{REPO_ROOT}` are the placeholders Task 5's prose must fill.

**Context.** EXECUTE deliberately supplies zero templates of its own because it composes SDD's implementer/reviewer prompts verbatim (`tests/test_execute_prose.py:80-82` asserts `references/execute-prompt.md` does not exist). PAR is different: D9 steals it from `iterative-development` as a *mechanism*, not an invocable skill (`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:195-205`), so there is no installed skill to hand this dispatch to. `test_prompt_templates.py`'s own `TEMPLATES` tuple is `(SCOPE, REFINE, PLAN)` today (`tests/test_prompt_templates.py:14`) — three, not four. REVIEW is the first stage since REFINE that needs a genuinely new template, and it needs one dispatched **twice**, with no cross-visibility between the two runs — the competitive frame's entire point (F-5).

**Executor skills:** `superpowers:writing-skills`. Read `plan-prompt.md` in full first (`skills/supskill/references/plan-prompt.md:1-66`) — it is this template's closest sibling in shape: a header naming placeholders, then the dispatched body stating the two standing constraints verbatim.

- [ ] **Step 1: Write the failing tests**

Extend `tests/test_prompt_templates.py`: replace the `TEMPLATES` tuple and add the new template's own assertions.

Replace lines 10–15:

```python
REFERENCES = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "references"
SCOPE = REFERENCES / "scope-prompt.md"
REFINE = REFERENCES / "refine-prompt.md"
PLAN = REFERENCES / "plan-prompt.md"
REVIEW = REFERENCES / "review-prompt.md"

TEMPLATES = (SCOPE, REFINE, PLAN, REVIEW)
EXECUTION_SUB_SKILLS = ("subagent-driven-development", "executing-plans")
```

Append at the end of the file:

```python
def test_review_template_names_its_placeholders():
    text = REVIEW.read_text(encoding="utf-8")
    for placeholder in ("{REVIEWER_LABEL}", "{REVIEW_PACKAGE_PATH}", "{REPO_ROOT}"):
        assert placeholder in text, placeholder


def test_review_template_states_the_two_standing_constraints():
    text = REVIEW.read_text(encoding="utf-8")
    assert "cannot ask anyone anything" in text  # D4 / invariant 2
    assert "must not run `supskill-state`" in text  # invariant 3, fourth surface


def test_review_template_states_the_competitive_frame_and_no_cross_visibility():
    text = REVIEW.read_text(encoding="utf-8")
    assert "false positives are worse than misses" in text  # D9's own framing
    assert "no other agent's" in text.lower()  # no cross-visibility between the two dispatches


def test_review_template_asks_for_severity_and_a_defensible_location():
    text = REVIEW.read_text(encoding="utf-8")
    assert "Critical" in text and "Important" in text and "Minor" in text
    assert "location" in text.lower()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_prompt_templates.py -v`
Expected: FAIL — `FileNotFoundError` (or an assertion failure reading a non-existent file) on every `REVIEW`-referencing test; the three pre-existing SCOPE/REFINE/PLAN tests still collect and pass, since `TEMPLATES` iteration in `test_no_dispatch_template_line_instructs_running_the_state_cli` and `test_no_dispatch_template_line_instructs_an_execution_sub_skill` will itself fail on the missing `REVIEW` path.

- [ ] **Step 3: Write the template**

Create `skills/supskill/references/review-prompt.md`:

```markdown
# REVIEW dispatch template (PAR)

The conductor fills every `{PLACEHOLDER}` below and dispatches the result as
the complete prompt of one general-purpose subagent — **once per reviewer**:
`{REVIEWER_LABEL}` is `reviewer-a` on one dispatch and `reviewer-b` on the
other. Both dispatches use the identical filled template except for that one
label, and both are dispatched before either's output is read.

- `{REVIEWER_LABEL}` — this dispatch's own label, `reviewer-a` or `reviewer-b`
- `{REVIEW_PACKAGE_PATH}` — the whole-branch diff to review, `<scratch>/review-final.diff`
- `{REPO_ROOT}` — the repository this diff was taken against

---

You are {REVIEWER_LABEL}, reviewing a finished sprint's whole-branch diff at
{REVIEW_PACKAGE_PATH} against the repository at {REPO_ROOT}. Read the diff in
full, and read enough of the live source around it to judge whether the
changes are real: wired into something that calls them, covered by a test
that would fail if the change were reverted, and consistent with the rest of
the codebase's conventions.

Two facts about your situation, stated up front because they are structural:

- **You cannot ask anyone anything.** You are a dispatched subagent: the
  question tool is unavailable to you, and in a headless run it would resolve
  instantly with an empty answer. Do not ask; report what you found instead.
- **You must not run `supskill-state`, and you must not read or write anything
  under `.supskill/`.** You produce a finding list; the conductor alone
  records it, after both reviewers have returned.

**The frame: false positives are worse than misses.** Report only what you
can actually point at in the diff or the source around it — a claim you
cannot back with a location is not a finding. A prior review of this exact
codebase shipped 410 passing tests and still missed five mechanisms with zero
production callers; read for exactly that failure mode, not for style.

**Your output: one finding per line you can defend, each with:**
- `severity`: `Critical` (breaks or silently no-ops a shipped claim),
  `Important` (works but violates a stated invariant or leaves a real gap),
  or `Minor` (real, but low-stakes)
- `description`: what you found, in your own words
- `location`: `file:line` or the path — whatever actually pins it down

Report your finding list as your final message. Nothing else consumes your
output, and there is no second round: this is not a conversation. You do not
know whether you are `reviewer-a` or `reviewer-b` to any other agent, and no
other agent's findings are visible to you — review the diff on its own
merits, not against a guess at what a second reviewer might say.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_prompt_templates.py -v && uv run pytest && uv run ruff check`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/supskill/references/review-prompt.md tests/test_prompt_templates.py
git commit -m "feat: the PAR dispatch template - filled twice, no cross-visibility (SK-050)"
```

---

### Task 5: The REVIEW stage exists — dispatch discipline and stub demolition (SK-050)

**Files:**
- Modify: `skills/supskill/SKILL.md` (dispatch table's REVIEW row, `skills/supskill/SKILL.md:97`; the stub paragraph beneath it, `skills/supskill/SKILL.md:99-100`, removed; new `## The REVIEW stage` section inserted before `## Reference`, `skills/supskill/SKILL.md:504`)
- Create: `skills/supskill/references/review-notes.md`
- Test: `tests/test_review_prose.py` (create)

**Interfaces:**
- Consumes: Task 1's `review` verb and its exact CLI flags; Task 4's `review-prompt.md`; `sprint.scratch` from `show --json`; EXECUTE's own halt handoff (`<scratch>/review-final.diff`, `skills/supskill/SKILL.md:344-347`, `:472-475`).
- Produces: the `## The REVIEW stage` section and `references/review-notes.md`. Task 6's Gate 3 section is dispatched from the end of this one ("Then continue at **Gate 3**").

**Two stub surfaces name REVIEW, and both change** (mirrors S5 DoR finding 9, one stage later). The dispatch table's REVIEW row (`skills/supskill/SKILL.md:97`) reads *"Report: 'REVIEW is not implemented yet — it lands with E6 (PAR + Gate 3).' Stop."* — this is the **only** path that reaches REVIEW, exactly as Gate 2's approval line was the only path that reached EXECUTE before S5. The paragraph beneath the table (`skills/supskill/SKILL.md:99-100`) states *"REVIEW is a stub until E6 lands — do not improvise it."* Both are demolished here. After this task, the invariant-3 stub-language check in `tests/test_execute_prose.py::test_no_stub_language_survives_anywhere_except_for_review` still passes — it was written to require "REVIEW" on the same line as any surviving stub phrase, and after this task there is no such line left anywhere.

**Why the aggregation detail moves to `references/review-notes.md` rather than staying inline.** `skills/supskill/SKILL.md`'s body is, as of this plan's own baseline read, **exactly 500 lines** — the hard cap `tests/test_skill_frontmatter.py:75-77` enforces, with zero slack. This task, Task 6, Task 8 and Task 9 together add four new sections. Keeping every mechanical detail inline is not possible inside the remaining budget once Gate 1 and Gate 2 are also shrunk (Task 6). `review-notes.md` is conductor-facing — nothing in it is sent to a subagent, unlike `review-prompt.md` — the same relationship `references/invocation-model.md` already has to the base skill.

**Executor skills:** `superpowers:writing-skills`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_review_prose.py`:

```python
"""E6's prose surfaces: the REVIEW stage exists, PAR's dispatch discipline is
named, and nothing still calls REVIEW a stub.

The authoritative check is the reviewer reading every section; these are
tripwires for the regressions that would silently ship a stage nobody can
reach, or a reviewer that can see the other reviewer's output (F-5, D9).
"""

from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "supskill"
SKILL = SKILL_DIR / "SKILL.md"
REFERENCES = SKILL_DIR / "references"


def _section(heading: str, next_marker: str = "\n## ") -> str:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index(heading)
    rest = text.index(next_marker, start + 1)
    return text[start:rest]


def review_section() -> str:
    return _section("## The REVIEW stage")


def test_the_dispatch_table_routes_into_the_real_review_stage():
    text = SKILL.read_text(encoding="utf-8")
    assert "| `REVIEW` | Follow **The REVIEW stage** below. |" in text
    assert "## The REVIEW stage" in text


def test_no_review_stub_language_survives_anywhere():
    for path in sorted(SKILL_DIR.rglob("*.md")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            assert "REVIEW is not implemented yet" not in line, f"{path.name}:{number}: {line!r}"
            assert "REVIEW is a stub" not in line, f"{path.name}:{number}: {line!r}"


def test_the_review_stage_names_the_dispatch_and_forbids_state_access():
    section = review_section()
    assert "reviewer-a" in section and "reviewer-b" in section
    assert "review-final.diff" in section
    assert "No dispatched reviewer runs `supskill-state`" in section


def test_the_review_stage_costs_each_dispatch_and_points_at_gate_3():
    section = review_section()
    assert "cost --stage REVIEW --label reviewer-a|reviewer-b" in section
    assert "Gate 3" in section


def test_review_notes_exist_and_state_no_cross_visibility():
    text = (REFERENCES / "review-notes.md").read_text(encoding="utf-8")
    assert "neither reviewer sees the other's" in text.lower()


def test_review_notes_state_the_aggregation_rule_and_the_verbs_exact_flags():
    text = (REFERENCES / "review-notes.md").read_text(encoding="utf-8")
    assert "confidence=high" in text.lower() or "`high`" in text
    assert "confidence=actionable" in text.lower() or "`actionable`" in text
    assert "Critical > Important > Minor" in text
    assert "--reviewer" in text and "--severity" in text and "--confidence" in text
    assert "--finding" in text and "--location" in text
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_review_prose.py -v`
Expected: every test FAILs — `ValueError: substring not found` from `review_section()` (there is no `## The REVIEW stage` yet), `FileNotFoundError` for `review-notes.md`, and `test_the_dispatch_table_routes_into_the_real_review_stage` fails on the still-present stub row text.

- [ ] **Step 3: Demolish the two REVIEW stub surfaces**

In `skills/supskill/SKILL.md`, the dispatch table's REVIEW row (`skills/supskill/SKILL.md:97`) becomes:

```markdown
| `REVIEW` | Follow **The REVIEW stage** below. |
```

Remove the paragraph beneath the table entirely (`skills/supskill/SKILL.md:99-100`, the two lines beginning *"REVIEW is a stub until E6 lands"* and their trailing blank line) — nothing replaces it; every stage's row now routes to a real section, so the paragraph has nothing left to say.

- [ ] **Step 4: Write `references/review-notes.md`**

Create `skills/supskill/references/review-notes.md`:

```markdown
# PAR dispatch and aggregation (SK-050)

Referenced from **The REVIEW stage** in `SKILL.md`. This file is
conductor-facing: nothing here is sent to a subagent — that is
`review-prompt.md`'s job.

## Dispatch

Two fresh general-purpose subagents, `reviewer-a` and `reviewer-b`, each
dispatched from `references/review-prompt.md` filled once for its own
`{REVIEWER_LABEL}`, on the identical `{REVIEW_PACKAGE_PATH}` =
`<scratch>/review-final.diff` — EXECUTE's own last act before it halted
(`skills/supskill/SKILL.md:344-347`, `:472-475`). Dispatch both before
reading either's output; **neither reviewer sees the other's**, which is the
competitive frame's entire point (D9). Cost each dispatch as it completes:
`cost --stage REVIEW --label reviewer-a` / `cost --stage REVIEW --label
reviewer-b`.

## Matching

Which finding from `reviewer-a` corresponds to which from `reviewer-b` is
your judgment — a string comparison is not enough, and this doc does not
pretend otherwise. Match on what the finding actually points at (the same
location, the same mechanism), not on identical wording.

## Aggregation — fixed, no negotiation

Once matched:

| Reported by | confidence | severity |
|---|---|---|
| both, same severity | `high` | that severity |
| both, different severities | `high` | the worse of the two, always — `Critical > Important > Minor` |
| one reviewer only | `actionable` | that reviewer's severity |

`scripts/supskill_state/review.py`'s `aggregate()` is this table, as a pure
function of one already-matched finding's reported severities.

## Recording

One `review` call per finding, after both dispatches have returned:

    review --reviewer <reviewer-a|reviewer-b|both> \
      --severity <Critical|Important|Minor> \
      --confidence <high|actionable> \
      --finding "<description>" \
      --location "<file:line or path>"

`--reviewer both` is for a finding matched across both dispatches;
`--reviewer reviewer-a` or `--reviewer reviewer-b` for a finding only one of
them reported. The verb refuses an empty `--finding`/`--location` and an
unknown `--reviewer`/`--severity`/`--confidence` token, writing nothing on
any refusal — the same shape as `record_blocker`
(`scripts/supskill_state/commands.py:219-272`). Findings land in
`runs/<id>/review.jsonl`, append-only, before Gate 3 opens.
```

- [ ] **Step 5: Write `## The REVIEW stage`**

In `skills/supskill/SKILL.md`, insert immediately before `## Reference`:

```markdown
## The REVIEW stage

PAR: two adversarial reviewers on the identical `<scratch>/review-final.diff` package, worse severity wins (D9). Dispatch discipline, the aggregation rule, and the `review` verb's exact flags: [references/review-notes.md](references/review-notes.md). No dispatched reviewer runs `supskill-state`; cost each as it completes, `cost --stage REVIEW --label reviewer-a|reviewer-b`. Then continue at **Gate 3**.
```

- [ ] **Step 6: Run the tests and the frontmatter cap**

Run: `uv run pytest tests/test_review_prose.py tests/test_execute_prose.py tests/test_skill_frontmatter.py -v && uv run pytest && uv run ruff check`
Expected: all PASS. Confirm the line budget directly:

```bash
python3 -c "
text = open('skills/supskill/SKILL.md', encoding='utf-8').read()
closing = text.index('\n---\n', 4)
print(len(text[closing + len('\n---\n'):].splitlines()))
"
```
Expected: a number well under 500 (Tasks 5 alone should land in the high 400s; Task 6 shrinks it further before Tasks 8–9 add their own small sections — see the running total noted in Task 6's own verification step).

- [ ] **Step 7: Commit**

```bash
git add skills/supskill/SKILL.md skills/supskill/references/review-notes.md tests/test_review_prose.py
git commit -m "feat: the REVIEW stage exists - PAR dispatch discipline, no cross-visibility, the two REVIEW stub surfaces gone (SK-050)"
```

---

### Task 6: `references/gate.md`, and Gate 3 (SK-051)

**Files:**
- Create: `skills/supskill/references/gate.md`
- Modify: `skills/supskill/SKILL.md` (Gate 1 section shrinks, `skills/supskill/SKILL.md:156-178`; Gate 2 section shrinks, `skills/supskill/SKILL.md:241-272`; new `## Gate 3 — one decision, not two` section inserted before `## Reference`)
- Test: `tests/test_review_prose.py` (extend)

**Interfaces:**
- Consumes: Task 2's `GATE_DECISIONS` value `"replan"`; Task 1's `runs/<id>/review.jsonl`; E5's halt-report data (blockers, parked tasks, `DONE_WITH_CONCERNS` notes).
- Produces: `references/gate.md`, shared by Gate 1, Gate 2 and Gate 3. `## Gate 3`'s step 5 names `references/replan-shapes.md` (Task 7) and its step 6 names "**Refusing a north-star supersede**" (Task 8's anchor to append after).

**Context.** The CLI enforcement mostly already exists: `GATE_KEYS` has carried `"G3": "G3_review"` since S1 (`scripts/supskill_state/model.py:59`), and the `gate` subparser's `--id` already accepts `G3` (`scripts/supskill_state/cli.py:91`) — the generic `gate` verb needs no new plumbing for the gate *mechanism*, and Task 2 already paid the one CLI IOU (`--decision replan`). This task, like SK-032's Gate 2 before it, is mostly the UX and the batching — and the extraction sprint-04 named as E6's trigger: *"If a third repetition of this block starts to itch at E6, that is the signal to extract a shared `references/gate.md` — not now: two instances is a coincidence, three is a pattern"* (`docs/plans/sprints/backlog-01/sprint-04-plan-gate2.md:67`). This is that third instance.

**The shared file keeps each gate's own routing where it is used.** `references/gate.md` holds only the three steps identical across every gate — ask for real, refuse an empty answer, record verbatim — never the routing after the decision (`→ advance --to PLAN` vs `→ advance --to EXECUTE` vs G3's shape dispatch), which stays inline in each gate's own `SKILL.md` section. Verified in Step 6 of this task: the exact routing lines `tests/test_execute_prose.py::test_the_dispatch_table_and_gate_2_both_route_into_the_real_stage` and `::test_gate_1_routes_into_the_plan_stage_that_shipped_in_s4` already assert survive this task's edit unchanged (confirmed by a dry run against a real copy of the file before this plan was written).

**Executor skills:** `superpowers:writing-skills`. Read Gate 1 and Gate 2's current sections in full before shrinking them (`skills/supskill/SKILL.md:156-178`, `:241-272`) — the shared file must carry every fact both sections state today, only once.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_review_prose.py`:

```python
def gate3_section() -> str:
    return _section("## Gate 3")


def test_gate_1_and_gate_2_still_route_correctly_after_the_extraction():
    # the exact substrings tests/test_execute_prose.py already asserts must survive
    text = SKILL.read_text(encoding="utf-8")
    assert "`approved` → `advance --to PLAN` → continue at **The PLAN stage**" in text
    assert "`approved` → `advance --to EXECUTE` → continue at **The EXECUTE stage**" in text


def test_all_three_gates_point_at_the_shared_gate_doc():
    text = SKILL.read_text(encoding="utf-8")
    assert text.count("references/gate.md") >= 3  # Gate 1, Gate 2, Gate 3


def test_gate_md_states_the_three_shared_steps():
    text = (REFERENCES / "gate.md").read_text(encoding="utf-8")
    assert "Ask for real" in text
    assert "empty" in text.lower() and "not a decision" in text.lower()
    assert "Record verbatim" in text
    assert "gate --id <G1|G2|G3> --decision" in text or "gate --id" in text


def test_gate_3_batches_every_source_the_sprint_produced():
    section = gate3_section()
    assert "blocker" in section.lower()
    assert "parked" in section.lower()
    assert "DONE_WITH_CONCERNS" in section
    assert "review.jsonl" in section
    assert "confidence=high" in section and "confidence=actionable" in section


def test_gate_3_decision_routing_is_exact_for_all_three_outcomes():
    section = gate3_section()
    assert '`gate --id G3 --decision approved --response "<verbatim>"`' in section
    assert '`gate --id G3 --decision replan --response' in section
    assert "replan-shapes.md" in section
    assert "Refusing a north-star supersede" in section


def test_gate_3_never_records_a_decision_for_a_shape_4_reading():
    # SK-052's own accept criteria: Shape 4 is never a `gate` call at all
    section = gate3_section()
    assert "**no** `gate` call" in section
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_review_prose.py -v`
Expected: the six new tests FAIL — `ValueError: substring not found` from `gate3_section()` (no `## Gate 3` yet), and the two `references/gate.md`-reading tests fail with `FileNotFoundError`. `test_gate_1_and_gate_2_still_route_correctly_after_the_extraction` passes already (nothing has touched Gate 1/2 yet) — this is expected, and is the tripwire this task's own edit must not break.

- [ ] **Step 3: Write `references/gate.md`**

Create `skills/supskill/references/gate.md`:

```markdown
# The gate shape (shared by G1, G2, G3)

Extracted at E6 per a trigger named at S4: "two instances is a coincidence,
three is a pattern" (`docs/plans/sprints/backlog-01/sprint-04-plan-gate2.md:67`).
Referenced from each gate's own section in `SKILL.md`, which keeps its own
stage-specific routing — what happens after the decision — inline. Only the
three steps below are shared.

1. **Ask for real.** Use the `AskUserQuestion` tool: approve / reject the
   artifact this gate is reading, at its recorded path, free text welcome.
   Name the path in the question so the operator knows what they are
   approving.
2. **An empty or auto-resolved answer is not a decision.** In headless runs
   the question tool resolves instantly with an empty answer
   (`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:118-122`, D4).
   If the answer comes back empty, do NOT call `gate`. Report that this gate
   requires an interactive operator, and stop.
3. **Record verbatim.** A non-empty answer — the selected label plus any
   free text, unedited — goes to `gate --id <G1|G2|G3> --decision <value>
   --response "<verbatim>"`. The CLI records empty responses by design
   (`scripts/supskill_state/commands.py:196-213`) — a fabricated approval
   must leave a readable, empty quote in the trail (F-4) — which is exactly
   why step 2's refusal lives here, in the conductor, and nowhere else.

What happens after the decision is recorded is each gate's own — see Gate 1,
Gate 2, or Gate 3 in `SKILL.md`.
```

- [ ] **Step 4: Shrink Gate 1 and Gate 2, and write Gate 3**

In `skills/supskill/SKILL.md`, replace the whole block from `## Gate 1 — the operator reads the refined doc` up to (not including) `## The PLAN stage` with:

```markdown
## Gate 1 — the operator reads the refined doc

Ask for real, refuse an empty answer, record verbatim: [references/gate.md](references/gate.md).

4. `approved` → `advance --to PLAN` → continue at **The PLAN stage** (below).
5. `rejected` → recorded and final for this pass; report it and stop, naming the rework loop: edit the doc or ask for a fresh REFINE pass, then re-invoke and re-gate. Last decision wins in state; every attempt stays in the trail.

```

Replace the whole block from `## Gate 2 — the operator reads the dev plan` up to (not including) `## The EXECUTE stage` with:

```markdown
## Gate 2 — the operator reads the dev plan

Ask for real, refuse an empty answer, record verbatim - the same shape as Gate 1: [references/gate.md](references/gate.md).

4. `approved` → `advance --to EXECUTE` → continue at **The EXECUTE stage** (below). That transition also re-checks that `tasks[]` is non-empty; a refusal there is reported verbatim and stops the run.
5. `rejected` → recorded and final for this pass; report it and stop. PLAN's resume idempotence means re-invoking with the rejected plan still on disk skips the dispatch and re-gates the same file, so the operator edits the recorded plan **at its path** directly, then re-invokes. To force a fresh PLAN run, the operator removes the recorded plan file first - the conductor never deletes an artifact itself.

```

Insert, immediately before `## Reference` (i.e. immediately after Task 5's `## The REVIEW stage`):

```markdown
## Gate 3 — one decision, not two

Ask for real, refuse an empty answer, record verbatim — the same shape as Gate 1 and Gate 2: [references/gate.md](references/gate.md). The question batches every open blocker, every parked task, every `DONE_WITH_CONCERNS` note, and every `runs/<id>/review.jsonl` finding at `confidence=high` or `confidence=actionable` — nothing silently dropped.

4. Closes cleanly → `gate --id G3 --decision approved --response "<verbatim>"`. `REVIEW` is the last stage; nothing advances past it.
5. Resolves into Shape 1, 2 or 3 → `gate --id G3 --decision replan --response "<verbatim>"`, then run the shape's own verb: [references/replan-shapes.md](references/replan-shapes.md).
6. Reads as Shape 4 → **no** `gate` call — see **Refusing a north-star supersede**, next.
```

- [ ] **Step 5: Run the tests and the frontmatter cap**

Run: `uv run pytest tests/test_review_prose.py tests/test_execute_prose.py tests/test_skill_frontmatter.py -v && uv run pytest && uv run ruff check`
Expected: all PASS, including the two pre-existing routing-line assertions in `tests/test_execute_prose.py`. Confirm the running body-line total is comfortably under 500 (measured against a real trial of every edit through this task: **478 lines** — 22 lines of headroom left for Tasks 8 and 9's smaller additions):

```bash
python3 -c "
text = open('skills/supskill/SKILL.md', encoding='utf-8').read()
closing = text.index('\n---\n', 4)
print(len(text[closing + len('\n---\n'):].splitlines()))
"
```

Note: `[references/replan-shapes.md](references/replan-shapes.md)` in step 5's routing line points at a file Task 7 has not created yet, and "**Refusing a north-star supersede**" in step 6 names a subsection Task 8 has not appended yet. Both are forward references within this same sprint's own plan, exactly as `plan-prompt.md`'s header (`skills/supskill/references/plan-prompt.md:35-38`) already forward-references a stage's own later behavior. Leaving them unresolved between this commit and Task 7/8's commits is expected and does not fail any test in this task.

- [ ] **Step 6: Commit**

```bash
git add skills/supskill/SKILL.md skills/supskill/references/gate.md tests/test_review_prose.py
git commit -m "feat: references/gate.md extraction (sprint-04's own named trigger) and Gate 3's batched decision (SK-051)"
```

---

### Task 7: The three amending replan shapes (SK-052)

**Files:**
- Create: `skills/supskill/references/replan-shapes.md`
- Test: `tests/test_review_prose.py` (extend)

**Interfaces:**
- Consumes: Task 6's Gate 3 section, whose step 5 already points here.
- Produces: `references/replan-shapes.md`. Nothing else consumes it programmatically — it is read by the conductor and by the reviewer, the same relationship `review-notes.md` has to Task 5.

**Context.** The backlog's row names "the four replan shapes, incl. generative writeback" without listing all four; the authoritative list is the design doc's own table, carried forward here rather than re-derived: *review generates new items* (S9 → S9a — appends new `pending` rows); *execution stops at a live boundary* (S9a — parks a task, sprint stays open); *live evidence overturns the diagnosis* (S9a → S9b — forks a new sprint and, where warranted, a branch rename, with the operator ruling on process weight before any code moves); *north-star reset* (backlog-01 → 02 — supersedes the whole backlog) (`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:244-254`). The first three **amend**; the fourth **replaces** and is refused by Task 3/Task 8's guard, not described as an executable procedure here.

**Every shape is recorded through a verb that already exists.** Direct `backlog.md` edits are already this project's own practice: every prior sprint's own "Backlog deltas — proposed" section has been applied by hand, outside `supskill-state`, in its own `docs:` commit (`ec22e25`, `62fd0dc`, `133da28`). Invariant 3 binds `state.json` specifically (`docs/plans/sprints/backlog-01/backlog.md:29-30`), and `backlog.md` was never inside that boundary. `task --id <SK-0xx> --status PARKED --note "<...>"` already exists (`scripts/supskill_state/commands.py:331-387`), and a fork's `init` already exists (`scripts/supskill_state/commands.py:39-90`). This task adds no new mutator.

**Executor skills:** `superpowers:writing-skills`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_review_prose.py`:

```python
def test_replan_shapes_doc_names_all_four_and_marks_the_fourth_out_of_scope():
    text = (REFERENCES / "replan-shapes.md").read_text(encoding="utf-8")
    for shape in ("generative writeback", "park at a live boundary", "fork on live evidence",
                  "north-star reset"):
        assert shape in text.lower()
    assert "out of scope" in text.lower()


def test_shape_1_matches_the_existing_backlog_row_format_and_only_appends():
    text = (REFERENCES / "replan-shapes.md").read_text(encoding="utf-8")
    assert "| ID | Story | Pts | Pri | Status |" in text
    assert "Only append" in text or "only append" in text.lower()


def test_shape_2_uses_the_task_status_verb_that_already_exists():
    text = (REFERENCES / "replan-shapes.md").read_text(encoding="utf-8")
    assert '`task --id <SK-0xx> --status PARKED --note' in text
    assert "not** advanced past" in text.lower() or "not advanced past" in text.lower()


def test_shape_3_names_the_fork_verb_and_never_runs_a_branch_rename():
    text = (REFERENCES / "replan-shapes.md").read_text(encoding="utf-8")
    assert "`init`" in text
    assert "Name the rename" in text or "name the rename" in text.lower()
    assert "do not" in text.lower() and "run it" in text.lower()


def test_shape_4_points_at_the_refusal_and_adds_no_mutator():
    text = (REFERENCES / "replan-shapes.md").read_text(encoding="utf-8")
    assert "Refusing a north-star supersede" in text
    assert "never a new mutator" in text.lower() or "no new mutator" in text.lower()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_review_prose.py -v`
Expected: the five new tests FAIL — `FileNotFoundError` (no `replan-shapes.md` yet).

- [ ] **Step 3: Write `references/replan-shapes.md`**

Create `skills/supskill/references/replan-shapes.md`:

```markdown
# The four replan shapes (SK-052)

Referenced from Gate 3 in `SKILL.md`. Pulled verbatim from the design's own
table (`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:244-254`):
the first three amend the backlog; the fourth replaces it and is refused —
see `SKILL.md`'s "Refusing a north-star supersede".

## Shape 1 — generative writeback

Append new rows to `backlog.md` under the relevant epic (or a new epic, if
none fits), in the existing row format — `| ID | Story | Pts | Pri | Status
|` (`docs/plans/sprints/backlog-01/backlog.md:84`), status `☐` — each citing
the PAR finding or blocker that motivated it. Only append: never edit an
existing row's points or status here — that is a backlog-delta ritual owned
by the sprint that actually implements the change, per every prior sprint's
own "Backlog deltas — proposed" section. This is a direct edit to
`backlog.md`, outside `supskill-state` — invariant 3 binds `state.json`
specifically (`docs/plans/sprints/backlog-01/backlog.md:29-30`); `backlog.md`
was never inside that boundary, and every prior sprint's delta pass has
already edited it this way, by hand, in a `docs:` commit.

## Shape 2 — park at a live boundary

`task --id <SK-0xx> --status PARKED --note "<the blocker that parked it>"` —
the verb that already exists (`scripts/supskill_state/commands.py:331-387`).
The sprint itself is **not** advanced past `REVIEW`; name which live boundary
stopped it in the report.

## Shape 3 — fork on live evidence

Draft a forked sprint id, and a branch-rename recommendation where
warranted, but do not execute either unasked — the operator rules on the
fork's process weight first. A fork's `init` is the verb that already exists
(`scripts/supskill_state/commands.py:39-90`); a branch rename is not a verb
at all and this shape does not add one — the same restraint EXECUTE's own
branch check already states: "Do not create, switch, or delete a branch
yourself" (`skills/supskill/SKILL.md:312-313`). Name the rename; do not run
it.

## Shape 4 — north-star reset

Out of scope by construction: no verb reachable from any shape above
supersedes `backlog.md` wholesale. See `SKILL.md`'s "Refusing a north-star
supersede".

---

Every shape above is recorded through a verb that already exists — a
`backlog.md` edit, `task --status PARKED`, a fresh `init` — never a new
mutator.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_review_prose.py -v && uv run pytest && uv run ruff check`
Expected: all PASS. This task touches no `.py` file and no `SKILL.md` line — the full suite's count and the frontmatter body count are both unchanged from Task 6's end state.

- [ ] **Step 5: Commit**

```bash
git add skills/supskill/references/replan-shapes.md tests/test_review_prose.py
git commit -m "feat: the three amending replan shapes - every one recorded through a verb that already exists (SK-052)"
```

---

### Task 8: Wiring the north-star refusal into Gate 3 (SK-053)

**Files:**
- Modify: `skills/supskill/SKILL.md` (append `### Refusing a north-star supersede` immediately after Task 6's `## Gate 3` section, before `## Reference`)
- Test: `tests/test_review_prose.py` (extend)

**Interfaces:**
- Consumes: Task 3's `replan_guard.is_supersede` / `replan_guard.refusal` — named, not called from prose (there is no CLI surface that invokes a Python function from `SKILL.md`; the guard's existence and its regression tests are what make the structural claim provable, and this subsection is where the conductor's own report echoes that guard's `refusal()` text in spirit).
- Produces: the subsection Task 6's Gate 3 step 6 already points at.

**Context.** This story shrank for the same reason SK-042 shrank in S5: the enforcement is already built (Task 3), and what remains is the conductor's own half — naming, in the one place a shape-4 reading is ever encountered, that it produces a report and never a `gate` call, a draft, or an edit. The guard function's regression tests (Task 3) prove the structural claim continues to hold; this task's own reviewer check (see "Skills for executors" and "Review pass", below) is the one that confirms this subsection's wording matches what the guard's `refusal()` actually says, so the two never drift apart.

**Executor skills:** `superpowers:writing-skills`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_review_prose.py`:

```python
def test_gate_3_section_wires_in_the_refusal_subsection_right_after_it():
    section = gate3_section()
    assert "### Refusing a north-star supersede" in section


def test_the_refusal_subsection_matches_the_guard_functions_own_language():
    section = gate3_section()
    assert "backlog.md" in section and "North star" in section
    assert "state.json.backlog" in section
    assert "operator's alone" in section
    assert "author the new backlog by hand" in section
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_review_prose.py -v`
Expected: both new tests FAIL — `### Refusing a north-star supersede` does not exist yet, so it is not inside `gate3_section()`'s range.

- [ ] **Step 3: Append the refusal subsection**

In `skills/supskill/SKILL.md`, insert immediately after Task 6's Gate 3 step 6 (`6. Reads as Shape 4 → **no** \`gate\` call — see **Refusing a north-star supersede**, next.`), still before `## Reference`:

```markdown

### Refusing a north-star supersede

No code path here can rewrite `backlog.md`'s North star or repoint `state.json.backlog` (true today by construction; a regression test guards it). A Shape-4 reading gets a report, never a `gate` call, a draft, or an edit - the move is the operator's alone: author the new backlog by hand, then start the next sprint against it.
```

- [ ] **Step 4: Run the tests and the frontmatter cap**

Run: `uv run pytest tests/test_review_prose.py tests/test_execute_prose.py tests/test_skill_frontmatter.py -v && uv run pytest && uv run ruff check`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/supskill/SKILL.md tests/test_review_prose.py
git commit -m "feat: wire the north-star refusal into Gate 3 (SK-053)"
```

---

### Task 9: Propose the next sprint, then stop (SK-054)

**Files:**
- Modify: `skills/supskill/SKILL.md` (append `## Propose the next sprint, then stop` immediately after Task 8's refusal subsection, before `## Reference`)
- Test: `tests/test_review_prose.py` (extend)

**Interfaces:**
- Consumes: the backlog's own build-order convention this skill's dispatcher already used to pick this sprint's epic (no new mechanism — the same reading a human does of the Summary table, `docs/plans/sprints/backlog-01/backlog.md:60-73`).
- Produces: nothing further downstream — this is the sprint's last section.

**Context.** D6: *"v1 runs exactly one sprint per invocation. Plans go stale. No look-ahead planning."* (`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:163-173`). This task is the sprint's last mile: once a replan shape or the refusal above has resolved the sprint, the conductor names the next epic and stops. **One structural backstop already exists for free.** `Stage.REVIEW` is the last entry in `STAGE_ORDER` (`scripts/supskill_state/model.py:34-40`), so `next_stage(Stage.REVIEW)` returns `None` (`scripts/supskill_state/transitions.py:20-24`) and `advance_stage` refuses any `--to` at all from `REVIEW` with *"REVIEW is the final stage; there is nothing to advance to"* (`scripts/supskill_state/commands.py:447-448`). The state machine cannot advance past REVIEW even if the conductor tried. What this task must still cover is broader than `advance`: a further `gate`, `task`, `block`, `cost`, `init`, or another subagent dispatch are all still legal CLI calls the state machine does not refuse on its own.

**This prose tripwire is honest about its own ceiling.** A static grep over `SKILL.md`'s own text cannot prove a live conversation actually stops issuing tool calls — only a real transcript can, and the sprint doc's own exit criteria name this explicitly as something "verified against a REVIEW-stage transcript," not a pytest assertion (`docs/plans/sprints/backlog-01/sprint-s6-review-par-gate3.md:160`). Task 10's demo checklist is where that verification actually happens; this task's test is the same class of tripwire `tests/test_execute_prose.py`'s stub-language check is for EXECUTE — it catches the prose regressing, not the conductor disobeying it.

**Executor skills:** `superpowers:writing-skills`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_review_prose.py`:

```python
def propose_section() -> str:
    return _section("## Propose the next sprint, then stop", next_marker="\n## Reference")


def test_propose_section_exists_and_names_the_backlog_build_order_rule():
    section = propose_section()
    assert "build order" in section
    assert "D6" in section


def test_propose_section_forbids_every_further_state_mutating_call():
    section = propose_section()
    for verb in ("`advance`", "`gate`", "`task`", "`block`", "`cost`", "`init`"):
        assert verb in section, verb
    assert "subagent dispatch" in section


def test_propose_section_applies_regardless_of_which_shape_closed_the_sprint():
    section = propose_section()
    assert "fork" in section.lower() or "Shape 3" in section
    assert "refus" in section.lower()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_review_prose.py -v`
Expected: all three new tests FAIL — `## Propose the next sprint, then stop` does not exist yet.

- [ ] **Step 3: Append the proposal section**

In `skills/supskill/SKILL.md`, insert immediately after Task 8's `### Refusing a north-star supersede` subsection, still before `## Reference`:

```markdown

## Propose the next sprint, then stop

Once a replan shape or the refusal above has resolved the sprint, name the first unchecked epic in the backlog's build order, its points, and why (D6) - that is next sprint's SCOPE stage, not this run's. Then stop: no `advance`, `gate`, `task`, `block`, `cost`, `init`, or subagent dispatch follows the proposal, fork (Shape 3) and refusal alike.
```

- [ ] **Step 4: Run the tests, the frontmatter cap, and the full suite**

Run: `uv run pytest tests/test_review_prose.py tests/test_execute_prose.py tests/test_skill_frontmatter.py -v && uv run pytest && uv run ruff check`
Expected: all PASS. Confirm the final body-line count is under 500:

```bash
python3 -c "
text = open('skills/supskill/SKILL.md', encoding='utf-8').read()
closing = text.index('\n---\n', 4)
print(len(text[closing + len('\n---\n'):].splitlines()))
"
```
Expected: **478** (this plan's own measured total across every `SKILL.md` edit in Tasks 5, 6, 8 and 9 — if your own wording differs, any number ≤ 500 is a pass; anything over means trimming into `references/*.md` per the Global Constraints note before this task can close).

- [ ] **Step 5: Commit**

```bash
git add skills/supskill/SKILL.md tests/test_review_prose.py
git commit -m "feat: propose the next sprint, then stop - the run ends here regardless of which shape closed it (SK-054)"
```

---

### Task 10: The sprint demo checklist (process)

**Files:**
- Create: `.superpowers/sdd/s6/demo-checklist.md` (sprint scratch — gitignored by `.gitignore:9`; no commit)

**Interfaces:**
- Consumes: everything — the whole E6 conductor, installed or loadable as a plugin, plus real tokens, a real executed branch, and real PAR dispatches.
- Produces: the script the operator runs. **The sprint does not close on offline green.** The offline suite proves the `review` verb, its refusals, the aggregation rule as a pure function, the `GATE_DECISIONS` extension, and the north-star-supersede guard. It cannot prove that two reviewers actually catch what one would have missed, that Gate 3's batch is genuinely legible in one pass, or that the conductor actually stops instead of drifting into "one more thing." Only the demo can — the same honest-scope shape S5's own demo named for EXECUTE, one stage further up the loop.

- [ ] **Step 1: Write the demo checklist**

Create `.superpowers/sdd/s6/demo-checklist.md`:

```markdown
# S6 demo — REVIEW/PAR/Gate 3 in anger (operator-run, real tokens)

Run in THIS repo, at the repo root. Expected outcomes are written before running;
any mismatch fails the demo. Drive REVIEW on an already-executed branch — S6's
own, per the sprint doc's exit criteria — since EXECUTE now exists (S5) and this
sprint's own branch has real commits to review.

- [ ] 1. Preflight: an executed branch exists with `<scratch>/review-final.diff`
      on disk (EXECUTE's own last act before it halted). `state.json` reads
      stage `REVIEW`. If it does not, first drive `EXECUTE` to completion on
      this sprint's own plan.
- [ ] 2. `/supskill run s6` at stage `REVIEW` dispatches `reviewer-a` and
      `reviewer-b`, each from `review-prompt.md`, on the identical
      `review-final.diff`. Verify: `.supskill/runs/s6/costs.jsonl` gains two
      new `REVIEW` lines, labelled `reviewer-a` and `reviewer-b`.
- [ ] 3. **Neither reviewer's prompt or transcript ever mentions the other's
      findings.** Read both dispatches' prompts side by side; they differ only
      in `{REVIEWER_LABEL}`.
- [ ] 4. The conductor matches and aggregates, then records via `review`. Watch
      `.supskill/runs/s6/review.jsonl` grow, one line per aggregated finding.
      Spot-check one finding both reviewers reported at different severities:
      confirm the recorded severity is the worse of the two, not an average.
- [ ] 5. Gate 3 opens as **one** `AskUserQuestion`, batching every open blocker,
      every parked task, every `DONE_WITH_CONCERNS` note, and every
      `confidence=high`/`confidence=actionable` review finding. Read it: is it
      genuinely legible in one pass, or a wall of text? That answer is this
      sprint's single most important data point.
- [ ] 6. Answer Gate 3 with real words. If the answer resolves into a replan
      shape, confirm: Shape 1 only appends to `backlog.md`; Shape 2 records
      `task --status PARKED` and does not advance past `REVIEW`; Shape 3 drafts
      a fork and a branch-rename recommendation but runs neither unasked.
- [ ] 7. **Deliberately test the refusal once**, in a second scratch run: answer
      Gate 3 with words that read as "replace the whole backlog." Verify: no
      `gate` call is made, nothing is drafted, nothing is executed, and the
      report names the operator's own move (author the new backlog by hand).
- [ ] 8. After the sprint closes (by any shape, or by the refusal), the
      conductor proposes the next epic — name, points, one sentence why — and
      then issues **nothing further**: no `advance`, `gate`, `task`, `block`,
      `cost`, `init`, or subagent dispatch. Confirm by reading the transcript
      tail, not by trusting the report.
- [ ] 9. Verify no dispatched reviewer wrote state: neither reviewer's own
      transcript shows a `supskill-state` invocation.
- [ ] 10. Record below, verbatim: pass/fail per step, whether Gate 3's batch was
      actually legible, whether the aggregation rule ever felt wrong on a real
      finding, and whether the conductor's stop was clean or you had to
      intervene. Steps 3, 5, 7 and 8 are the ones that decide whether E6 is
      real.
```

- [ ] **Step 2: Hand it to the operator**

Report: the demo checklist is at `.superpowers/sdd/s6/demo-checklist.md`; it is the exit criterion for SK-050/051/052/053/054's operator-provable acceptance; the sprint stays open until the operator runs it. No commit — the scratch dir is gitignored by design (`.gitignore:9`).

---

### Task 11: Apply the S6 DoR backlog deltas (process)

**Files:**
- Modify: `docs/plans/sprints/backlog-01/backlog.md`

**Interfaces:**
- Consumes: nothing from other tasks (docs-only; the operator commissioning this plan is the acceptance the sprint doc's "once the operator accepts" clause names).
- Produces: a backlog that matches what S5 actually shipped and what S6 actually commits — the seven deltas from the sprint doc's own "Backlog deltas — proposed" section, plus marking E5's rows shipped (an S5 loose end this task closes, since S5's own backlog task marked only E1–E4).

- [ ] **Step 1: Mark E5's rows shipped (an S5 loose end)**

S5 (SK-040–043) shipped on `main` (`5cfa51b`…`8105d2f`), but `docs/plans/sprints/backlog-01/backlog.md`'s E5 rows still read `☐` — S5's own Task 6 only marked E1–E4. Change the Status cell to `☑` for `SK-040`, `SK-041`, `SK-042`, `SK-043` (`docs/plans/sprints/backlog-01/backlog.md:132-135`).

- [ ] **Step 2: Re-point SK-050 (8 → 11) and re-scope its row**

Replace the SK-050 row (`docs/plans/sprints/backlog-01/backlog.md:141`):

```markdown
| SK-050 | **PAR**: two reviewer subagents on identical input, competitive frame ("false positives are worse than misses"), fixed aggregation — both agree → high confidence; one only → still actionable; **severity disagreement → always take the worse, no negotiation.** (**D9**, F-5) S6 DoR: no verb wrote a review finding (`cli.py:21-30` had no `review`) and PAR needed a genuinely new prompt template — unlike EXECUTE, which composes SDD's verbatim and adds none of its own. The story now carries the `review` verb (`Critical\|Important\|Minor` severity, `high\|actionable` confidence, append-only `runs/<id>/review.jsonl`, no schema bump), `scripts/supskill_state/review.py`'s pure aggregation function, and `skills/supskill/references/review-prompt.md`, dispatched twice with no cross-visibility. | 11 | M | ☑ |
```

- [ ] **Step 3: Re-point SK-051 (3 → 4) and re-scope its row**

Replace the SK-051 row (`docs/plans/sprints/backlog-01/backlog.md:142`):

```markdown
| SK-051 | Gate 3: present batched blockers + review findings as **one** high-information decision. S6 DoR: `GATE_DECISIONS` was `("approved", "rejected")` and refused `replan` outright — S1 flagged this exact gap as deliberately deferred to E6 (`sprint-01-state-spine.md:104`). The story now carries the additive `GATE_DECISIONS` extension and the `references/gate.md` extraction sprint-04 named as E6's trigger (`sprint-04-plan-gate2.md:67`). | 4 | M | ☑ |
```

- [ ] **Step 4: Mark SK-052, SK-053, SK-054 shipped (unchanged points)**

Replace the three remaining E6 rows (`docs/plans/sprints/backlog-01/backlog.md:143-145`), changing only the Status cell to `☑` on each — points and story text unchanged, per the sprint doc's own "Backlog deltas — proposed" note that these three "gained citations and one restraint, not scope."

- [ ] **Step 5: Update the totals**

- E6 section header (`docs/plans/sprints/backlog-01/backlog.md:137`):
  `## E6 — REVIEW (PAR) + Gate 3 + replan shapes (23 pts)` → `## E6 — REVIEW (PAR) + Gate 3 + replan shapes (27 pts)`
- Summary table E6 row (`docs/plans/sprints/backlog-01/backlog.md:69`): `| 23 |` → `| 27 |`
- `**Total: 132 pts.**` (`docs/plans/sprints/backlog-01/backlog.md:73`) → `**Total: 136 pts.**`

Verify:

```bash
grep -c "☑" docs/plans/sprints/backlog-01/backlog.md   # expected: 19 (E1-E4) + 4 (E5) + 5 (E6) = 28
grep -n "^| SK-0[0-5][0-9] .*☐" docs/plans/sprints/backlog-01/backlog.md   # expected: no output through SK-054
```

- [ ] **Step 6: Record Gate 1 data point #6**

Append after the "Data point #5" paragraph at the end of `docs/plans/sprints/backlog-01/backlog.md`:

```markdown
**Data point #6 (S6 DoR, 2026-07-14):** refinement against live source grew scope
+4 pts (23 → 27) for the sixth consecutive sprint — the same magnitude as S3, S4
and S5, even though E6's own code did not exist yet and so carried no live
defects to find. The findings this time were about what was *absent* rather
than what was *wrong*: two verbs and a prompt template no story before this one
ever needed to build (SK-050), and a CLI value S1 itself flagged as deliberately
deferred (SK-051). Six sprints, six data points, same direction — §7.2's answer
holds a sixth time: *the gate earns its keep because the refinement does,
whether or not the code under review yet exists.* (Report §7.2)
```

- [ ] **Step 7: Commit**

```bash
git add docs/plans/sprints/backlog-01/backlog.md
git commit -m "docs: mark E5 shipped and apply S6 DoR backlog deltas (SK-050 11pts, SK-051 4pts, E6 27pts, total 136)"
```

---

## Exit criteria mapping (sprint doc → plan)

| Sprint exit criterion | Where it lands |
|---|---|
| SK-050: two reviewer subagents dispatched via `review-prompt.md` on the identical package, no cross-visibility | Task 4 (template), Task 5 (dispatch discipline) |
| SK-050: the aggregation rule TDD'd offline as a pure function; the `review` verb and its refusals TDD'd offline | Task 1 |
| SK-050: every dispatch names its model and logs a `cost` entry; findings land in `runs/<id>/review.jsonl` before Gate 3 opens | Task 5 (`references/review-notes.md`, `## The REVIEW stage`) |
| SK-050: `test_prompt_templates.py`'s `TEMPLATES` tuple carries four entries | Task 4 |
| SK-051: `GATE_DECISIONS` carries `replan`, TDD'd offline | Task 2 |
| SK-051: Gate 3 is one `AskUserQuestion` batching every open blocker, parked task, concern, and PAR finding at `confidence=high`/`confidence=actionable` | Task 6 |
| SK-051: an empty answer is refused as a non-decision; a non-empty answer records `approved` or `replan` | Task 6 (`references/gate.md`, inherited from Gate 1/2's own standing behavior) |
| SK-051: `references/gate.md` exists and G3's section uses it | Task 6 |
| SK-052: all three amending shapes reachable through verbs that already exist; no new mutator; a branch rename is named, never run; generative writeback matches `backlog.md`'s row format | Task 7 |
| SK-053: a guard function, TDD'd offline, refuses any shape-4-classified answer | Task 3 |
| SK-053: a regression test confirms no code path anywhere in E6 rewrites `backlog.md`'s North star or `state.json.backlog` | Task 3 |
| SK-053: the refusal is wired into the REVIEW/Gate 3 flow | Task 8 |
| SK-054: the proposal names the next unchecked epic, its points, and why; nothing dispatches or advances state after it | Task 9 |
| SK-054: `advance`'s own structural refusal past REVIEW requires no new test | Task 9 (cited, not re-tested — `scripts/supskill_state/commands.py:447-448`) |
| Full suite pure offline and fast for every offline-provable story (SK-053 in full; SK-050's aggregation-rule and `review`-verb slice; SK-051's `GATE_DECISIONS` slice) | Tasks 1, 2, 3 |
| The sprint demo (operator-run, real tokens): two reviewer dispatches, aggregated findings, a single batched Gate 3 question, an operator answer resolving into a shape, a next-sprint proposal, then nothing further | Task 10 — **operator-run; the sprint does not close on offline green alone** |
| Backlog deltas applied; E5's own shipped rows marked | Task 11 |

## Skills for executors

Standing skills apply (author↔review separation, verify-before-claim, no self-approval, TDD, `karpathy-guidelines`, no AI attribution in commits). Domain additions, matching the sprint doc's own list:

- **Tasks 1 / 3 (the pure slices)** — `fullstack-dev-skills:python-pro` + `superpowers:test-driven-development`. The `review` verb's refusals, the severity/confidence vocabulary, and the north-star guard function stay pure offline: no LLM, no subagent, no network.
- **Task 4 (the dispatch template)** — `superpowers:writing-skills`. Read `test_prompt_templates.py`'s existing assertions per template (`tests/test_prompt_templates.py:18-27` for the shape) before writing it.
- **Tasks 5 / 6 (the REVIEW stage, `references/gate.md`, Gate 3)** — `superpowers:writing-skills`. Read Gate 1 and Gate 2's sections in `skills/supskill/SKILL.md` in full before extracting; the shared file must still let each gate's stage-specific routing live where it is used, not get flattened into one generic paragraph that loses the routing.
- **Tasks 7 / 8** — `oh-my-claudecode:code-reviewer` → `oh-my-claudecode:verifier`. The standing invariant-3 prose check over `skills/supskill/SKILL.md` and `skills/supskill/references/*.md` gains a fifth assertion: **no code path anywhere in the REVIEW section rewrites `backlog.md`'s North star section or `state.json.backlog`** — and Task 8's own reviewer pass additionally confirms the SKILL.md refusal subsection's wording actually matches what `replan_guard.refusal()` says, so the two do not drift apart over time.
- **Task 9** — same reviewer pass, extended with the transcript-shaped check `tests/test_execute_prose.py:37-42` already models for EXECUTE's stub language, applied here to REVIEW's proposal-then-stop guarantee.

## Risks & mitigations

| Risk | Owner | Trigger / signal | Mitigation |
|------|-------|------------------|------------|
| **`SKILL.md`'s body starts this sprint at its exact 500-line cap, zero slack** | operator (this plan) / every executor touching `SKILL.md` | `tests/test_skill_frontmatter.py::test_body_stays_under_500_lines` fails on any of Tasks 5, 6, 8, 9 | This plan's own SKILL.md diff was measured against a real trial copy before being written into this document: net **478** lines, 22 lines of headroom. Every SKILL.md-touching task's own verification step re-measures the body count directly; the fallback is always to move prose into a `references/*.md` file, never to shorten a load-bearing routing line |
| **PAR findings had no defined on-disk shape or writer** | operator (this plan) / executor (Task 1) | Gate 3's question omits a PAR finding because nothing wrote it | Resolved in this plan: the `review` verb, append-only `runs/<id>/review.jsonl`, no `state.json` schema bump — the same pattern as `blockers.jsonl`/`tasks.jsonl`/`costs.jsonl` |
| **PAR needs a fourth prompt template with genuinely no cross-visibility between the two reviewer dispatches** | executor (Task 4/5) | `reviewer-b`'s output echoes or references `reviewer-a`'s finding language | Fresh subagent dispatch per reviewer, exactly SDD's fresh-implementer-per-task pattern; the template names neither reviewer's own label to the other |
| **`--decision replan` did not exist and the CLI refused it before Task 2** | executor (Task 2) | `gate --id G3 --decision replan` returns `unknown decision 'replan'` | `GATE_DECISIONS` grows to `("approved", "rejected", "replan")`, additive in `model.py` and `cli.py`; S1 already flagged this as E6's IOU to pay (`sprint-01-state-spine.md:104`) |
| **SK-053's detection of a "shape-4 attempt" is not specified by the backlog** | operator (this plan) | a Gate 3 answer that reads as a backlog supersede advances anyway | Structural refusal instead of detection: no verb in this epic's scope can rewrite the North star section or repoint `state.json.backlog`; a shape-4 reading produces a report, never a write. Confirmed already true today by the regression tests in Task 3, not merely asserted |
| **SK-054's "stop" guarantee is a prose promise until it has a mechanical check** | executor (Task 9) / reviewer | a REVIEW transcript shows a dispatch or a state-mutating call after the proposal | `advance` is already structurally refused past REVIEW (`scripts/supskill_state/commands.py:447-448`); a grep-style prose tripwire, the same class of test the invariant-3 checks already use, covers the remaining calls — but the real guarantee is only visible in Task 10's demo |
| **PAR's doubled review cost was an open question in the design doc, not a decided budget** | executor (Task 5) | REVIEW's token spend materially exceeds EXECUTE's per-task dispatches | The `cost` verb already exists for exactly this (`fcc78f7`); Task 5's dispatches log to it from day one so the real number is on disk before it becomes a debate |

## Exit criteria

- [ ] **Task 1 (SK-050 pure slice):** `review.aggregate()` is TDD'd offline as a pure function of an already-matched finding (same → high, one-only → actionable, disagreement → worse wins, `Critical > Important > Minor`); the `review` verb and its refusals (unknown reviewer/severity/confidence, empty finding/location) are TDD'd offline; findings land in `runs/<id>/review.jsonl`, no `state.json` schema bump.
- [ ] **Task 2 (SK-051 pure slice):** `GATE_DECISIONS` carries `replan` alongside `approved`/`rejected`, TDD'd offline.
- [ ] **Task 3 (SK-053):** `replan_guard.is_supersede`/`refusal` TDD'd offline; a regression test confirms `state.backlog` is set nowhere but `init_sprint` and every trail file this codebase writes ends `.jsonl`, never `.md`.
- [ ] **Task 4 (SK-050):** `review-prompt.md` exists, filled twice with `{REVIEWER_LABEL}`; `test_prompt_templates.py`'s `TEMPLATES` tuple carries four entries.
- [ ] **Task 5 (SK-050):** `## The REVIEW stage` exists; both REVIEW stub surfaces are gone; `references/review-notes.md` states the dispatch, matching, aggregation and recording discipline; `SKILL.md`'s body stays under 500 lines.
- [ ] **Task 6 (SK-051):** `references/gate.md` exists and Gate 1, Gate 2 and Gate 3 all reference it while keeping their own routing inline; `## Gate 3` batches every source and records `approved`/`replan` correctly; a Shape-4 reading is never a `gate` call.
- [ ] **Task 7 (SK-052):** `references/replan-shapes.md` names all four shapes; the first three are executable through verbs that already exist; the fourth points at the refusal.
- [ ] **Task 8 (SK-053):** `### Refusing a north-star supersede` is wired directly under Gate 3's own step 6.
- [ ] **Task 9 (SK-054):** `## Propose the next sprint, then stop` names the build-order rule and forbids every further state-mutating call or dispatch.
- [ ] Full suite pure offline and fast for every offline-provable story (Task 3 in full; Task 1's aggregation-rule and `review`-verb slice; Task 2's `GATE_DECISIONS` slice); every Python task TDD'd with failing-test-first evidence in the sprint scratch.
- [ ] **The sprint demo (operator-run, real tokens):** Task 10 — drive REVIEW on an already-executed branch through two reviewer dispatches, aggregated findings, a single batched Gate 3 question, an operator answer that resolves into a shape (and, separately, a deliberate test of the refusal), and a next-sprint proposal after which the conductor issues nothing further.

> **Honest scope note:** Tasks 1, 2 and 3 in full are this sprint's offline-provable core — a small fraction of 27 points. Everything else is a loop the test suite cannot execute on its own: whether two reviewers actually catch what one would have missed, whether Gate 3's batch is genuinely legible in a single pass rather than a wall of text, and whether the conductor actually stops instead of drifting into "one more thing" — all three are visible only in Task 10's demo. This is E5's honest-scope problem one layer up: a green suite here proves the aggregation rule, the new verb, and the refusal guard are correct, not that the review gate the whole product is named for actually catches what F-5 says a single reviewer will miss.
