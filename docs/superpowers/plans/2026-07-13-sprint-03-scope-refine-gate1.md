# Sprint 03 — SCOPE + REFINE + Gate 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The conductor drives its first real stages — a dispatched `sprint-plan` subagent writes the sprint doc at a derived path, a refine subagent grows it against live source with citations a script audits, and `advance --to PLAN` succeeds only after the operator's verbatim Gate 1 approval is in `gates.jsonl`.

**Architecture:** Same split as always (D2): the `supskill-state` CLI is the only mutator and gains two preconditions (SCOPE entry requires a backlog; `→ REFINE` requires a recorded, existing `sprint_doc`); two new pure-Python modules (`proofs.py` grammar parser, `citations.py` audit behind a new `scripts/supskill-audit` shim) are the mechanical floor under REFINE; SKILL.md replaces its SCOPE/REFINE stubs with real dispatch choreography built on two prompt templates in `skills/supskill/references/`. Stage agents produce documents; the conductor alone records them.

**Tech Stack:** Python ≥3.11 stdlib only (zero runtime deps), pytest + ruff + pyyaml as dev deps, managed with `uv`. Claude Code plugin layout unchanged.

## Global Constraints

Copied from the sprint spec (`docs/plans/sprints/backlog-01/sprint-03-scope-refine-gate1.md`) and the standing project rules. Every task's requirements implicitly include this section.

- **Zero runtime dependencies:** `pyproject.toml` `[project] dependencies = []` — enforced by `tests/test_scaffold.py`. New packages go in `[dependency-groups] dev` only.
- **The suite stays pure offline and fast:** no LLM calls, no subagents, no network anywhere in `tests/`.
- **Invariant 3 now has a THIRD surface — subagent prompt templates.** No template under `skills/supskill/references/` may instruct its agent to run `supskill-state` or touch `.supskill/`. Stage agents produce documents; the conductor alone records them. This is a named reviewer check, plus a tripwire test (Task 5).
- **Invariant 2 / D4 in every template:** dispatched agents can never ask anyone anything (`AskUserQuestion` is stripped from subagents and auto-resolves empty in ~37ms headless — contexts/01 §6). Every template written this sprint states this verbatim and gives the agent its full input up front.
- **The proof grammar has a single authority:** `scripts/supskill_state/proofs.py`. `refine-prompt.md` quotes it; the quote is pinned to the parser's token constants by test (grammar-drift risk from the sprint risks table).
- **Silence is not consent at Gate 1.** No `--yes`, no auto-approve affordance anywhere. An empty or auto-resolved `AskUserQuestion` answer means: no `gate` call, report, stop. The CLI keeps recording empty responses by design (F-4, `commands.py:197`) — the refusal lives in the conductor prose only.
- **PLAN stays E4's honest stub.** When G1 approves, advance and land on the stub, which reports and stops. Do not wire `superpowers:writing-plans` (SK-031's terminal-question trap belongs to E4).
- **No blocker records from E3 stages:** `record_blocker` requires the task to exist and `tasks[]` is empty until SK-033 (finding 7). SCOPE/REFINE failures escalate by report-verbatim-and-stop. Do not invent placeholder tasks.
- **Skill frontmatter limits still hold** (enforced by `tests/test_skill_frontmatter.py`): the frontmatter of `skills/supskill/SKILL.md` is untouched this sprint; the body stays ≤500 lines; reference files at most one hop from SKILL.md.
- **The state CLI is always invoked as `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state`, from the target repo's root.** The new audit script follows the identical convention: `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-audit`.
- **The conductor never passes `--archive`** — it may only name it in a refusal and stop.
- **Style:** ruff `line-length = 120`, rules `E,F,I,B,UP`. Run `uv run ruff check` before every commit.
- **Commits:** one per task minimum, TDD evidence first (failing test run before implementation). **No AI attribution of any kind in commit messages** — no `Co-Authored-By`, no "Generated with" lines.
- **Commands:** run tests as `uv run pytest <path> -v`, lint as `uv run ruff check`.

## File Structure

| Path | Task | Responsibility |
|---|---|---|
| `scripts/supskill_state/commands.py` | 1 (modify) | `init_sprint` refuses SCOPE entry without a backlog |
| `scripts/supskill_state/cli.py` | 1 (modify) | `--backlog` help text names the new requirement |
| `scripts/supskill_state/transitions.py` | 2 (modify) | `failed_preconditions` gains the REFINE branch |
| `scripts/supskill_state/proofs.py` | 3 (create) | Proof-line grammar + parser — the vocabulary's single owner |
| `scripts/supskill_state/citations.py` | 4 (create) | Citation extraction/resolution + the `supskill-audit` CLI (incl. `--proofs`) |
| `scripts/supskill-audit` | 4 (create) | Self-bootstrapping shim, same pattern as `scripts/supskill-state` |
| `skills/supskill/references/scope-prompt.md` | 5 (create) | SCOPE dispatch template |
| `skills/supskill/references/refine-prompt.md` | 6 (create) | REFINE dispatch template (quotes the grammar) |
| `skills/supskill/SKILL.md` | 5, 6, 7 (modify) | SCOPE/REFINE rows become real; Gate 1 section; one new convention bullet |
| `tests/test_init.py`, `tests/test_advance.py`, plus mechanical edits across the suite | 1, 2 (modify) | The two preconditions, both directions; existing call sites updated |
| `tests/test_proofs.py` | 3 (create) | Grammar accepted/rejected offline; dogfoods this sprint's own doc |
| `tests/test_citations.py` | 4 (create) | Good/bad fixtures; dogfoods this sprint's own doc; `--help` honesty |
| `tests/test_prompt_templates.py` | 5 (create), 6 (extend) | Templates exist, quote the grammar, state D4 + invariant 3 |
| `docs/plans/sprints/backlog-01/sprint-03-scope-refine-gate1.md` | 3 (commit as-is) | Committed untouched — it is the dogfood fixture for Tasks 3 and 4 |
| `.superpowers/sdd/s3/demo-checklist.md` | 8 (create, gitignored) | Operator-run demo — the sprint's exit criterion |
| `docs/plans/sprints/backlog-01/backlog.md` | 9 (modify) | The five S3 DoR backlog deltas |

Task order: 1 → 2 sequential (both edit `tests/test_advance.py` / `tests/test_demo.py`); 3 is independent of 1–2; 4's core is independent but its final `--proofs` step needs 3; 5 needs 1–2 (documents the real CLI); 6 needs 3, 4, 5; 7 needs 6; 8 needs 7; 9 is docs-only and independent.

---

### Task 1: `init` refuses SCOPE entry without `--backlog` (SK-020 CLI half, DoR finding 2)

**Files:**
- Modify: `scripts/supskill_state/commands.py:52-53` (insert after the id normalization)
- Modify: `scripts/supskill_state/cli.py:35` (help text)
- Test: `tests/test_init.py` (new tests + call-site updates)
- Modify (call sites only): `tests/test_advance.py`, `tests/test_run_matrix.py`, `tests/test_demo.py`, `tests/test_show.py`, `tests/test_artifact.py`, `tests/test_gate.py`, `tests/test_block.py`

**Interfaces:**
- Consumes: `init_sprint(sprint_id, *, slug, entry, backlog, branch, archive, root)` as it exists today (`commands.py:35`); `StateError`.
- Produces: `init_sprint` raises `StateError` (message contains `--backlog`) when the effective entry stage is SCOPE and `backlog` is falsy, before anything touches disk. Validation order becomes: entry → sprint-id → **backlog** → disk. Later tasks rely on: at stage SCOPE reached via `init`, `state.backlog` is always non-null.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_init.py`:

```python
def test_init_scope_entry_without_backlog_refuses_before_touching_disk(tmp_path):
    # a SCOPE sprint with backlog null has nothing to scope and no verb to fix it (S3 DoR finding 2)
    with pytest.raises(StateError, match="--backlog"):
        init_sprint("s1", root=tmp_path)  # SCOPE is the default entry
    with pytest.raises(StateError, match="--backlog"):
        init_sprint("s1", entry="SCOPE", root=tmp_path)
    assert not supskill_dir(tmp_path).exists()


@pytest.mark.parametrize("entry", ["PLAN", "EXECUTE"])
def test_init_non_scope_entry_still_allows_a_null_backlog(tmp_path, entry):
    assert init_sprint("s9b", entry=entry, root=tmp_path).backlog is None


def test_cli_init_scope_without_backlog_refuses(tmp_path, monkeypatch, capsys):
    from supskill_state.cli import main

    monkeypatch.chdir(tmp_path)
    assert main(["init", "s1"]) == 1
    assert "--backlog" in capsys.readouterr().err
    assert not supskill_dir(tmp_path).exists()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_init.py -v -k backlog`
Expected: the three new tests FAIL (`DID NOT RAISE StateError` / exit 0 instead of 1); everything else passes.

- [ ] **Step 3: Implement the refusal**

In `scripts/supskill_state/commands.py`, directly after `normalized = normalize_sprint_id(sprint_id)` (line 53) and before `path = store.state_path(root)`:

```python
    if entry_stage is Stage.SCOPE and not backlog:
        raise StateError(
            "a SCOPE-entry sprint has nothing to scope without a backlog: pass --backlog <path> "
            "(no verb can set it after init; PLAN and EXECUTE entries may omit it)"
        )
```

Ordering matters and is deliberate: the entry check and the id check (`derive_scratch`) stay ahead of it, so `test_init_rejects_bad_sprint_id_before_touching_disk` (which inits SCOPE without a backlog but with a bad id) keeps matching `"refusing"`. The backlog check stays ahead of every disk read/write, so nothing is created or archived on refusal.

In `scripts/supskill_state/cli.py:35`, update the flag's help text:

```python
    sub.add_argument("--backlog", help="path to the backlog driving this sprint (required when entry is SCOPE)")
```

- [ ] **Step 4: Update the suite's existing call sites**

Every `init` that lands on the default SCOPE entry must now carry a backlog (the path is not existence-checked at init, so the literal `"backlog.md"` is fine). Two exact patterns:

- Python API: `init_sprint("<id>", root=tmp_path)` → `init_sprint("<id>", backlog="backlog.md", root=tmp_path)` (insert the kwarg before `root=`; calls with `entry="PLAN"` / `entry="EXECUTE"` are untouched — that is the point of Step 1's parametrized test).
- CLI: `main(["init", "<id>"])` → `main(["init", "<id>", "--backlog", "backlog.md"])` (calls that pass `--entry PLAN|EXECUTE` are untouched).

Per file (line numbers as of commit `b0c6e85`):

- `tests/test_init.py`: lines 12 (add `backlog="backlog.md"` to the S1 init), 50, 53, 58, 62, 72, 73, 74, 82 (API); 99, 100 (CLI). Lines 30, 39, 45, 90 stay untouched.
- `tests/test_advance.py`: lines 45, 59, 83, 91, 96, 110, 165 (API). Lines 71, 77, 119, 128, 136, 156, 187 stay untouched (non-SCOPE entries).
- `tests/test_run_matrix.py`: lines 20, 46, 61, 64 (CLI — including the `s99` mismatch init: argument validation now precedes the clobber check, so the cell-3 test must supply `--backlog` to reach the `--archive` refusal it pins). Line 36 stays untouched.
- `tests/test_demo.py`: line 17 → `main(["init", "s1", "--backlog", "backlog.md"])`.
- `tests/test_artifact.py`: lines 12, 20, 27 (API); 42 (CLI).
- `tests/test_gate.py`: lines 28, 43, 54, 70, 77 (API); 95 (CLI).
- `tests/test_block.py`: line 34 (API, inside `_init_with_task`).
- `tests/test_show.py`: lines 12 (`_state_with_activity`), 50, 74 (API). Line 97 (`test_show_marks_missing_backlog_with_a_dash`) switches to `init_sprint("s1", entry="PLAN", root=tmp_path)` instead — a null backlog is still a legal state, just no longer reachable via SCOPE entry, and the dash rendering is what that test pins. Line 117 (`test_cli_show_json`) changes `assert parsed["backlog"] is None` → `assert parsed["backlog"] == "backlog.md"`.

- [ ] **Step 5: Run the full suite and lint**

Run: `uv run pytest && uv run ruff check`
Expected: all green. Verify no call site was missed:

Run: `grep -rn 'init_sprint("' tests/ | grep -v 'backlog=' | grep -v 'entry='`
Expected: only the deliberate refusal-path tests (bad id, bad entry, the new SCOPE-without-backlog tests).

- [ ] **Step 6: Commit**

```bash
git add scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/
git commit -m "feat: init refuses SCOPE entry without --backlog (SK-020, S3 DoR finding 2)"
```

---

### Task 2: `advance --to REFINE` requires a recorded, existing `sprint_doc` (SK-020 CLI half, DoR finding 1)

**Files:**
- Modify: `scripts/supskill_state/transitions.py:24-40` (`failed_preconditions`)
- Test: `tests/test_advance.py` (one new test, three reworked)
- Modify: `tests/test_demo.py` (reorder the north-star flow)

**Interfaces:**
- Consumes: `failed_preconditions(state, to, root)` and `_check_artifact` (`transitions.py:50-55`) as they exist today.
- Produces: a REFINE branch in `failed_preconditions` reusing `_check_artifact(state, "sprint_doc", root, failures)` — failure strings are exactly the existing idiom: `artifacts.sprint_doc is not recorded` / `artifacts.sprint_doc points at a missing file: <path>`. Task 5's SCOPE choreography (record → advance) relies on this transition refusing a doc-less advance. No gate guards `SCOPE → REFINE`; entry=PLAN/EXECUTE sprints never take this transition (preconditions attach to transitions *taken* — D2), so they are structurally unaffected.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing test**

In `tests/test_advance.py`, replace `test_scope_to_refine_needs_no_gate` (lines 90-92) with:

```python
def test_advance_to_refine_requires_a_recorded_existing_sprint_doc(tmp_path):
    # no gate guards SCOPE -> REFINE; the recorded doc does. Entry=PLAN/EXECUTE sprints
    # never take this transition, so the precondition cannot reach them (D2).
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    message = _refused(tmp_path, "REFINE", "sprint_doc is not recorded")
    assert "G1" not in message  # a doc-less REFINE is an artifact problem, not a gate problem

    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)
    (tmp_path / "doc.md").unlink()
    _refused(tmp_path, "REFINE", "missing file")

    _write_doc(tmp_path, "doc.md")
    assert advance_stage("REFINE", root=tmp_path).stage is Stage.REFINE
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_advance.py::test_advance_to_refine_requires_a_recorded_existing_sprint_doc -v`
Expected: FAIL — `advance_stage("REFINE")` succeeds where `_refused` expects a `StateError` (today `failed_preconditions` has no REFINE branch).

- [ ] **Step 3: Implement the precondition**

In `scripts/supskill_state/transitions.py`, `failed_preconditions` grows a first branch:

```python
    if to is Stage.REFINE:
        _check_artifact(state, "sprint_doc", root, failures)
    elif to is Stage.PLAN:
        _check_gate(state, "G1_sprint_doc", failures)
        _check_artifact(state, "sprint_doc", root, failures)
    elif to is Stage.EXECUTE:
```

(The existing PLAN/EXECUTE/REVIEW branches are otherwise unchanged; `→ PLAN` keeps re-checking the artifact — that redundancy is deliberate, the doc may vanish between stages.)

- [ ] **Step 4: Rework the tests the new precondition invalidates**

Three tests in `tests/test_advance.py` advance to REFINE before recording the doc; the flow order changes (record first, advance second — which is exactly the choreography SKILL.md will encode):

Replace `test_advance_to_plan_requires_doc_and_g1` (lines 95-106) with:

```python
def test_advance_to_plan_requires_g1_on_top_of_the_doc(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    record_artifact("sprint_doc", _write_doc(tmp_path, "doc.md"), root=tmp_path)
    advance_stage("REFINE", root=tmp_path)

    _refused(tmp_path, "PLAN", "G1_sprint_doc")  # the doc is recorded; the gate alone refuses

    record_gate("G1", "approved", "approved", root=tmp_path)
    (tmp_path / "doc.md").unlink()  # a doc that vanished after REFINE is re-caught at -> PLAN
    _refused(tmp_path, "PLAN", "missing file")

    _write_doc(tmp_path, "doc.md")
    assert advance_stage("PLAN", root=tmp_path).stage is Stage.PLAN
```

In `test_a_rejected_gate_is_not_approved` (lines 109-115), swap the order of the `advance_stage("REFINE", ...)` and `record_artifact(...)` lines (record first).

In `test_entry_scope_can_never_reach_execute_without_both_gates` and `test_advance_to_execute_with_g2_null_refuses`, no reorder is needed — they already record `sprint_doc` before advancing (verify, don't assume).

In `tests/test_demo.py::test_north_star_demo`, move the artifact block ahead of the advance and fix the comments (lines 19-24):

```python
    # SCOPE produced the sprint doc; record it (REFINE refines this same doc in place)
    (tmp_path / "sprint-doc.md").write_text("# sprint doc\n")
    assert main(["artifact", "--set", "sprint_doc", "--path", "sprint-doc.md"]) == 0

    # the REFINE stage happens (no gate guards SCOPE -> REFINE; the recorded doc does)
    assert main(["advance", "--to", "REFINE"]) == 0
```

- [ ] **Step 5: Run the full suite and lint**

Run: `uv run pytest && uv run ruff check`
Expected: all green, including the reworked tests.

- [ ] **Step 6: Commit**

```bash
git add scripts/supskill_state/transitions.py tests/test_advance.py tests/test_demo.py
git commit -m "feat: advance --to REFINE requires a recorded, existing sprint_doc (SK-020, S3 DoR finding 1)"
```

---

### Task 3: Proof-line grammar + parser (SK-022)

**Files:**
- Create: `scripts/supskill_state/proofs.py`
- Test: `tests/test_proofs.py`
- Commit (as-is, it is the fixture): `docs/plans/sprints/backlog-01/sprint-03-scope-refine-gate1.md`

**Interfaces:**
- Consumes: `StateError` from `scripts/supskill_state/errors.py`.
- Produces (SK-033 adds only the verb on top of these, never a second parser):
  - `SEAM_TOKENS: tuple[str, ...]`, `IMPACT_TOKENS: tuple[str, ...]`, `PROVABLE_TOKENS: tuple[str, ...]`
  - `GRAMMAR_LINE: str` — the exact one-line grammar, derived from the token tuples (Task 6's template test pins the refine-prompt quote against this constant)
  - `@dataclass(frozen=True) ProofLine(story: str, seam: str, impact: str, provable: str)`
  - `parse_proof_lines(text: str) -> list[ProofLine]` — returns proof lines in document order, or raises `StateError` listing **every** violation (unknown tokens, duplicate line per story, proof line before any story heading, story in the `## Stories` section without a proof line)

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_proofs.py`:

```python
"""SK-022: the proof grammar is a parseable fact fixed in E3 - SK-033 adds the verb, never a parser."""

from pathlib import Path

import pytest

from supskill_state.errors import StateError
from supskill_state.proofs import GRAMMAR_LINE, ProofLine, parse_proof_lines

SPRINT_03 = (
    Path(__file__).resolve().parent.parent
    / "docs" / "plans" / "sprints" / "backlog-01" / "sprint-03-scope-refine-gate1.md"
)

GOOD = """## Stories

### SK-001 — a story · 3 · M
- **proof:** seam=unit · impact=local · provable=offline
"""


def test_dogfood_this_sprints_own_doc_parses():
    # the sprint spec classifies its own five stories; the parser must agree with it verbatim
    proofs = parse_proof_lines(SPRINT_03.read_text(encoding="utf-8"))
    assert proofs == [
        ProofLine("SK-020", "app-level", "cross-surface", "operator"),
        ProofLine("SK-021", "app-level", "journey", "operator"),
        ProofLine("SK-022", "unit", "cross-surface", "offline"),
        ProofLine("SK-023", "app-level", "journey", "operator"),
        ProofLine("SK-024", "unit", "local", "offline"),
    ]


def test_trailing_annotation_after_the_three_tokens_is_allowed():
    # SK-020's real proof line carries a parenthetical after provable=operator
    doc = GOOD.replace("provable=offline", "provable=offline *(the CLI half is seam=unit)*")
    assert parse_proof_lines(doc)[0].provable == "offline"


def test_unknown_tokens_are_rejected_naming_story_field_and_token():
    with pytest.raises(StateError, match="SK-001.*unknown seam token 'vibes'"):
        parse_proof_lines(GOOD.replace("seam=unit", "seam=vibes"))
    with pytest.raises(StateError, match="unknown impact token"):
        parse_proof_lines(GOOD.replace("impact=local", "impact=huge"))
    with pytest.raises(StateError, match="unknown provable token"):
        parse_proof_lines(GOOD.replace("provable=offline", "provable=maybe"))


def test_duplicate_proof_line_for_one_story_rejected():
    with pytest.raises(StateError, match="SK-001.*duplicate"):
        parse_proof_lines(GOOD + "- **proof:** seam=unit · impact=local · provable=offline\n")


def test_story_in_the_stories_section_without_a_proof_line_rejected():
    with pytest.raises(StateError, match="SK-002.*no proof line"):
        parse_proof_lines(GOOD + "\n### SK-002 — another story · 2 · M\n\nprose only\n")


def test_sk_headings_outside_the_stories_section_do_not_require_proof_lines():
    doc = GOOD + "\n## Deferred\n\n### SK-099 — parked, mentioned in an appendix\n"
    assert len(parse_proof_lines(doc)) == 1


def test_proof_line_before_any_story_heading_rejected():
    with pytest.raises(StateError, match="before any"):
        parse_proof_lines("- **proof:** seam=unit · impact=local · provable=offline\n")


def test_all_violations_are_reported_at_once():
    doc = GOOD.replace("seam=unit", "seam=vibes") + "\n### SK-002 — missing · 2 · M\n"
    with pytest.raises(StateError) as excinfo:
        parse_proof_lines(doc)
    assert "vibes" in str(excinfo.value) and "SK-002" in str(excinfo.value)


def test_grammar_line_constant_is_the_documented_grammar():
    assert GRAMMAR_LINE == (
        "- **proof:** seam=unit|integration|app-level|e2e"
        " · impact=none|local|cross-surface|journey"
        " · provable=offline|operator"
    )
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_proofs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'supskill_state.proofs'`.

- [ ] **Step 3: Implement the parser**

Create `scripts/supskill_state/proofs.py`:

```python
"""Proof-line grammar and parser (SK-022; vocabulary stolen from D9's taxonomy).

One exact line per story, directly under the story's ### SK-xxx heading:

    - **proof:** seam=unit|integration|app-level|e2e · impact=none|local|cross-surface|journey · provable=offline|operator

This module is the vocabulary's single owner, and it enforces vocabulary ONLY.
Whether `seam=e2e · provable=offline` is a *lie* is judgment - the refine
reviewer's and the operator's at Gate 1 - and this validator does not pretend
otherwise. Typical mapping: unit/integration -> offline; app-level/e2e ->
operator; a mixed story classifies by its least-provable seam.

The missing-proof-line check applies only to ### SK-xxx headings inside a
`## Stories` section; token and duplicate checks apply document-wide. SK-033
(E4) loads tasks[] from these lines - it adds the verb, never a second parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import StateError

SEAM_TOKENS: tuple[str, ...] = ("unit", "integration", "app-level", "e2e")
IMPACT_TOKENS: tuple[str, ...] = ("none", "local", "cross-surface", "journey")
PROVABLE_TOKENS: tuple[str, ...] = ("offline", "operator")

GRAMMAR_LINE = (
    "- **proof:** seam=" + "|".join(SEAM_TOKENS)
    + " · impact=" + "|".join(IMPACT_TOKENS)
    + " · provable=" + "|".join(PROVABLE_TOKENS)
)

# anchored at column 0: the grammar exemplar inside indented code blocks must not parse
_PROOF = re.compile(r"^- \*\*proof:\*\* seam=(\S+) · impact=(\S+) · provable=(\S+)(?:\s.*)?$")
_STORY = re.compile(r"^###\s+.*?(SK-\d+)")
_SECTION = re.compile(r"^##\s+(?!#)(.+?)\s*$")


@dataclass(frozen=True)
class ProofLine:
    story: str
    seam: str
    impact: str
    provable: str


def parse_proof_lines(text: str) -> list[ProofLine]:
    """Every proof line, in document order; raises StateError listing every violation."""
    proofs: list[ProofLine] = []
    violations: list[str] = []
    seen: set[str] = set()
    story: str | None = None
    in_stories = False
    required: list[str] = []  # SK headings inside the Stories section, in order

    for number, line in enumerate(text.splitlines(), start=1):
        section = _SECTION.match(line)
        if section:
            in_stories = section.group(1).strip().lower() == "stories"
            continue
        heading = _STORY.match(line)
        if heading:
            story = heading.group(1)
            if in_stories:
                required.append(story)
            continue
        match = _PROOF.match(line)
        if not match:
            continue
        if story is None:
            violations.append(f"line {number}: proof line before any ### SK-xxx heading")
            continue
        seam, impact, provable = match.groups()
        for token, allowed, field in (
            (seam, SEAM_TOKENS, "seam"),
            (impact, IMPACT_TOKENS, "impact"),
            (provable, PROVABLE_TOKENS, "provable"),
        ):
            if token not in allowed:
                violations.append(
                    f"{story}: unknown {field} token {token!r} (expected one of {'|'.join(allowed)})"
                )
        if story in seen:
            violations.append(f"{story}: duplicate proof line")
            continue
        seen.add(story)
        proofs.append(ProofLine(story=story, seam=seam, impact=impact, provable=provable))

    for story_id in required:
        if story_id not in seen:
            violations.append(f"{story_id}: story in the Stories section has no proof line")

    if violations:
        raise StateError("proof grammar: " + "; ".join(violations))
    return proofs
```

Note on `_PROOF`: `(\S+)` for `provable` followed by the optional `(?:\s.*)?` tail is what tolerates SK-020's real trailing annotation (`provable=operator *(...)`) while still rejecting a mangled token — `\S+` cannot cross the space before the annotation.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_proofs.py -v && uv run pytest && uv run ruff check`
Expected: all PASS — in particular the dogfood test agrees with the five real proof lines, and `test_demo.py::test_no_module_outside_store_opens_files_for_writing` stays green (proofs.py writes nothing).

- [ ] **Step 5: Commit (including the sprint doc — it is the fixture)**

The sprint spec is currently untracked; the dogfood test makes it load-bearing for CI. Commit it byte-for-byte as it stands (do not edit it):

```bash
git add scripts/supskill_state/proofs.py tests/test_proofs.py docs/plans/sprints/backlog-01/sprint-03-scope-refine-gate1.md
git commit -m "feat: proof-line grammar + parser, dogfooded on the S3 sprint doc (SK-022)"
```

---

### Task 4: `supskill-audit` — the citation floor under REFINE (SK-024)

**Files:**
- Create: `scripts/supskill_state/citations.py`
- Create: `scripts/supskill-audit` (executable shim)
- Test: `tests/test_citations.py`

**Interfaces:**
- Consumes: `parse_proof_lines` + `StateError` from Task 3 (only in the `--proofs` path); the sprint doc committed in Task 3 (dogfood test).
- Produces:
  - `audit_citations(text: str, root: Path) -> list[str]` — one message per unique unresolved citation; empty list means every citation resolves
  - `build_parser() -> argparse.ArgumentParser`, `main(argv: list[str] | None = None) -> int`
  - CLI: `supskill-audit <doc> [--proofs]` — exit 0 all-clear, exit 1 on any failure, every failure printed to stderr with its reason. Task 6's conductor wiring invokes `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-audit --proofs <doc>`.

**Design decisions this task locks in** (the spec leaves both open; state them in the module docstring):
1. **Suffix resolution.** The S3 doc itself — the exit-criterion fixture — cites bare module names (`commands.py:178`) for files living at `scripts/supskill_state/commands.py`. A citation therefore resolves iff at least one file under the root whose path *ends with* the cited path (matched on whole path segments, `.git`/`__pycache__`/`.venv`/`node_modules` pruned) has at least the cited number of lines. Anything stricter fails the spec's own dogfood.
2. **`--proofs` lives here.** SK-021 requires the conductor to run "the proof-grammar validator", but SK-022's CLI verb is explicitly deferred to SK-033. Rather than invent a throwaway second shim, `supskill-audit --proofs` additionally runs `parse_proof_lines` on the doc; `proofs.py` stays the single vocabulary owner and the default (no flag) behavior is exactly SK-024's contract.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_citations.py`:

```python
"""SK-024: a hallucinated or stale citation fails a script before it can impress an operator."""

from pathlib import Path

from supskill_state.citations import audit_citations, build_parser, main

REPO_ROOT = Path(__file__).resolve().parent.parent
SPRINT_03 = REPO_ROOT / "docs" / "plans" / "sprints" / "backlog-01" / "sprint-03-scope-refine-gate1.md"


def _tree(tmp_path):
    nested = tmp_path / "scripts" / "pkg"
    nested.mkdir(parents=True)
    (nested / "mod.py").write_text("\n".join(f"line {i}" for i in range(1, 51)) + "\n")


def test_resolvable_citations_pass_exact_suffix_and_range(tmp_path):
    _tree(tmp_path)
    text = "see `scripts/pkg/mod.py:50`, the bare `mod.py:7`, and the range `mod.py:1-10`"
    assert audit_citations(text, tmp_path) == []


def test_fabricated_file_fails_with_reason(tmp_path):
    _tree(tmp_path)
    failures = audit_citations("see `ghost.py:3`", tmp_path)
    assert len(failures) == 1 and "no file matching ghost.py" in failures[0]


def test_line_past_end_of_file_fails_with_reason(tmp_path):
    _tree(tmp_path)
    failures = audit_citations("see `mod.py:51`", tmp_path)
    assert len(failures) == 1 and "51" in failures[0] and "50 lines" in failures[0]


def test_range_end_is_checked_and_backwards_range_fails(tmp_path):
    _tree(tmp_path)
    assert "50 lines" in audit_citations("`mod.py:40-60`", tmp_path)[0]
    assert "backwards" in audit_citations("`mod.py:9-3`", tmp_path)[0]


def test_suffix_must_match_whole_path_segments(tmp_path):
    _tree(tmp_path)
    # "od.py" is a substring of mod.py's name but not a path suffix - must not resolve
    assert "no file matching" in audit_citations("`od.py:1`", tmp_path)[0]


def test_prose_placeholders_and_skill_names_are_not_citations(tmp_path):
    _tree(tmp_path)
    # no extension dot before the colon, or no numeric line -> not a citation token
    text = "cite `file:line` or `path:start-end`; invoke `pm-execution:sprint-plan`"
    assert audit_citations(text, tmp_path) == []


def test_repeated_citations_are_reported_once(tmp_path):
    _tree(tmp_path)
    assert len(audit_citations("`ghost.py:3` and again `ghost.py:3`", tmp_path)) == 1


def test_dogfood_every_citation_in_the_sprint_doc_resolves():
    # the sprint's own exit criterion: this doc's citations all resolve in this repo
    assert audit_citations(SPRINT_03.read_text(encoding="utf-8"), REPO_ROOT) == []


def test_help_states_the_resolve_not_truth_limit():
    assert "claims they support are true" in build_parser().format_help()


def test_cli_exit_codes_and_failure_output(tmp_path, monkeypatch, capsys):
    _tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "good.md").write_text("see `mod.py:5`\n")
    (tmp_path / "bad.md").write_text("see `ghost.py:3`\n")
    assert main(["good.md"]) == 0
    assert main(["bad.md"]) == 1
    assert "ghost.py" in capsys.readouterr().err
    assert main(["no-such-doc.md"]) == 1


def test_proofs_flag_also_validates_the_grammar(tmp_path, monkeypatch, capsys):
    _tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    doc = tmp_path / "doc.md"
    doc.write_text("## Stories\n\n### SK-001 — s · 1 · M\n- **proof:** seam=vibes · impact=local · provable=offline\n")
    assert main(["doc.md", "--proofs"]) == 1
    assert "vibes" in capsys.readouterr().err
    doc.write_text("## Stories\n\n### SK-001 — s · 1 · M\n- **proof:** seam=unit · impact=local · provable=offline\n")
    assert main(["doc.md", "--proofs"]) == 0
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_citations.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'supskill_state.citations'`.

- [ ] **Step 3: Implement the module**

Create `scripts/supskill_state/citations.py`:

```python
"""Citation audit (SK-024): the mechanical floor under REFINE (F-5, S3 DoR finding 4).

Extracts backtick-wrapped `path:line` / `path:start-end` tokens (the path must
carry a file extension - `file:line` prose placeholders and skill names like
`pm-execution:sprint-plan` are not citations) and verifies each resolves.

Resolution is by path suffix, matched on whole segments: sprint docs cite bare
module names (`commands.py:178`) for nested files, so a citation resolves iff
at least one file under the root whose path ends with the cited path has at
least the cited number of lines. .git, __pycache__, .venv and node_modules are
pruned.

Honesty (stated in --help too): this proves citations RESOLVE, not that the
claims they support are true. Truth stays with the reviewer and the operator
at Gate 1; the script only removes the cheapest way to fake depth (F-4's
shape: loud and auditable, not impossible).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .errors import StateError
from .proofs import parse_proof_lines

_CITATION = re.compile(r"`([A-Za-z0-9_\-./]+\.[A-Za-z0-9_]+):(\d+)(?:-(\d+))?`")
_SKIP_DIRS = frozenset((".git", "__pycache__", ".venv", "node_modules"))


def _tree_index(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and not _SKIP_DIRS.intersection(path.relative_to(root).parts)
    ]


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def audit_citations(text: str, root: Path) -> list[str]:
    """One message per unique unresolved citation; empty means every citation resolves."""
    failures: list[str] = []
    seen: set[str] = set()
    index: list[Path] | None = None
    for match in _CITATION.finditer(text):
        token = match.group(0)
        if token in seen:
            continue
        seen.add(token)
        cited = match.group(1)
        start = int(match.group(2))
        end = int(match.group(3)) if match.group(3) else start
        if end < start:
            failures.append(f"{token}: backwards range")
            continue
        if index is None:
            index = _tree_index(root)
        suffix = Path(cited).parts
        candidates = [p for p in index if p.relative_to(root).parts[-len(suffix):] == suffix]
        if not candidates:
            failures.append(f"{token}: no file matching {cited} under {root}")
            continue
        longest = max(_line_count(path) for path in candidates)
        if longest < end:
            failures.append(f"{token}: cites line {end} but the longest matching file has {longest} lines")
    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="supskill-audit",
        description=(
            "Verify every backtick-wrapped path:line citation in a doc resolves against "
            "the working tree (paths resolve from the cwd). This proves citations resolve "
            "- NOT that the claims they support are true; truth stays with the reviewer "
            "and the operator at the gate."
        ),
    )
    parser.add_argument("doc", help="markdown doc to audit")
    parser.add_argument(
        "--proofs",
        action="store_true",
        help="also validate the doc's proof lines against the SK-022 grammar (proofs.py is the authority)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    doc = Path(args.doc)
    if not doc.is_file():
        print(f"supskill-audit: no such doc: {args.doc}", file=sys.stderr)
        return 1
    text = doc.read_text(encoding="utf-8")
    failures = audit_citations(text, Path.cwd())
    if args.proofs:
        try:
            parse_proof_lines(text)
        except StateError as error:
            failures.append(str(error))
    if failures:
        for failure in failures:
            print(f"supskill-audit: {failure}", file=sys.stderr)
        return 1
    print("supskill-audit: ok")
    return 0
```

Create `scripts/supskill-audit` (then `chmod +x scripts/supskill-audit`):

```python
#!/usr/bin/env python3
"""Audit shim: keeps supskill_state importable when run straight from the plugin dir."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from supskill_state.citations import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_citations.py -v && uv run pytest && uv run ruff check`
Expected: all PASS — including the dogfood test (if it fails, the extraction regex is matching something in the sprint doc that is not a real citation; fix the regex, never the doc) and the write-primitive tripwire in `test_demo.py` (citations.py only reads).

Also verify the shim end-to-end:

Run: `./scripts/supskill-audit docs/plans/sprints/backlog-01/sprint-03-scope-refine-gate1.md --proofs`
Expected: `supskill-audit: ok`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/supskill_state/citations.py scripts/supskill-audit tests/test_citations.py
git commit -m "feat: supskill-audit - citation resolution floor under REFINE, --proofs grammar check (SK-024)"
```

---

### Task 5: SCOPE stage — dispatch template + conductor row (SK-020 prose half)

**Files:**
- Create: `skills/supskill/references/scope-prompt.md`
- Modify: `skills/supskill/SKILL.md` (Conventions bullet, SCOPE dispatch row, new stage section — frontmatter untouched)
- Test: `tests/test_prompt_templates.py` (create)

**Interfaces:**
- Consumes: the CLI semantics from Tasks 1–2 (`backlog` guaranteed non-null at SCOPE entry via init; `advance --to REFINE` refuses without a recorded doc); `artifact --set sprint_doc` refusing a missing file (`commands.py:178`).
- Produces: `scope-prompt.md` with placeholders `{SPRINT_ID}`, `{BACKLOG_PATH}`, `{OUTPUT_PATH}`, `{EXEMPLAR_DOCS}`; the SKILL.md section `## The SCOPE stage` whose last action is `advance --to REFINE` and fall-through (Task 6 writes the REFINE section it falls into).

**Executor skills:** `superpowers:writing-skills`. Degrees-of-freedom framing: exact CLI invocations, the output path, the heading format, and the capacity numbers are low-freedom (verbatim); "what to do where the backlog underspecifies" is judgment and the template says so instead of pretending to specify it.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_prompt_templates.py`:

```python
"""E3 prose surfaces: templates exist, quote the single-authority grammar, state D4 + invariant 3.

The authoritative invariant-3 check is the reviewer reading every template;
the tests here are tripwires for the obvious regressions only.
"""

from pathlib import Path

REFERENCES = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "references"
SCOPE = REFERENCES / "scope-prompt.md"
REFINE = REFERENCES / "refine-prompt.md"


def test_scope_template_names_its_placeholders():
    text = SCOPE.read_text(encoding="utf-8")
    for placeholder in ("{SPRINT_ID}", "{BACKLOG_PATH}", "{OUTPUT_PATH}", "{EXEMPLAR_DOCS}"):
        assert placeholder in text, placeholder


def test_scope_template_states_the_two_constraints():
    text = SCOPE.read_text(encoding="utf-8")
    assert "cannot ask anyone anything" in text  # D4 / invariant 2
    assert "must not run `supskill-state`" in text  # invariant 3, third surface


def test_no_dispatch_template_line_instructs_running_the_state_cli():
    for template in (SCOPE,):  # Task 6 adds REFINE here
        for line in template.read_text(encoding="utf-8").splitlines():
            if "supskill-state" in line:
                assert "not" in line.lower(), f"{template.name}: {line!r}"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_prompt_templates.py -v`
Expected: FAIL — `FileNotFoundError: ... references/scope-prompt.md`.

- [ ] **Step 3: Write the template**

Create `skills/supskill/references/scope-prompt.md`:

```markdown
# SCOPE dispatch template

The conductor fills every `{PLACEHOLDER}` below and dispatches the result as
the complete prompt of one general-purpose subagent:

- `{SPRINT_ID}` — the sprint being scoped, e.g. `s4`
- `{BACKLOG_PATH}` — the markdown backlog driving this sprint
- `{OUTPUT_PATH}` — where the sprint doc must be written (derived by the conductor)
- `{EXEMPLAR_DOCS}` — up to two existing sprint docs beside the backlog, or `none`

---

You are drafting the sprint document for sprint {SPRINT_ID}.

Two facts about your situation, stated up front because they are structural:

- **You cannot ask anyone anything.** You are a dispatched subagent: the
  question tool is unavailable to you, and in a headless run it would resolve
  instantly with an empty answer. Everything you need is in this prompt and on
  disk. Where the backlog leaves something open, make the smaller, reversible
  choice and record it in the doc's risks table — the operator reads this doc
  at a gate and can overrule you there. What counts as "the smaller choice" is
  your judgment; this prompt does not pretend to specify it.
- **You must not run `supskill-state`, and you must not read or write anything
  under `.supskill/`.** You produce one document; the conductor alone records
  it in state.

Your task:

1. Read {BACKLOG_PATH} in full.
2. Your scope is the epic this sprint commits: the first epic in the backlog's
   recommended build order whose stories are still unchecked (☐). Name it on
   the doc's header line.
3. Invoke the `pm-execution:sprint-plan` skill against that epic's story rows.
   The rows are your input — do not invent stories the backlog does not have.
4. Reframe capacity in this repo's committable-points model: working capacity
   ~34 pts, ~18% buffer, ~28 pts committable. `sprint-plan`'s own checklist
   assumes team rosters, PTO, and standups — none of that exists here. One
   operator, one conductor: no team members, no ceremonies.
5. Every story heading carries its backlog id, exactly one story per id:
   `### SK-0xx — <title> · <points> · <priority>`. Downstream stages join
   backlog rows to stories by these ids; a missing id breaks the join.
6. Shape the doc like the exemplars: {EXEMPLAR_DOCS}. Target sections: an H1
   title; an Epic / Points / Milestone header line; a one-line sprint goal;
   why this sprint; capacity & sequencing; the stories; a risks & mitigations
   table; exit criteria.
7. Write the finished doc to {OUTPUT_PATH} — exactly that path, nowhere else.

Report back exactly two lines: the path you wrote, and the committed points.
The document is the deliverable, not your report.
```

- [ ] **Step 4: Wire the SCOPE row in SKILL.md**

Four edits to `skills/supskill/SKILL.md` (body only — the frontmatter must not change):

(a) In `## Conventions (read first, apply always)`, append one bullet:

```markdown
- **Stage agents never touch state.** Stages dispatch subagents from templates
  under `references/`; the conductor runs every `supskill-state` call itself,
  and no template instructs an agent to run one or to write under `.supskill/`.
```

(b) Retitle the dispatch table heading and its closing paragraph:

`## Dispatch table (v-E2: every stage is an honest stub)` becomes `## Dispatch table`, and the paragraph after the table becomes:

```markdown
PLAN, EXECUTE, and REVIEW are honest stubs until their epics land — do not
improvise a stage. An implemented stage follows its section below exactly.
```

(c) Replace the SCOPE row of the table:

```markdown
| `SCOPE` | Follow **The SCOPE stage** below. |
```

(d) Insert the stage section between the dispatch table's closing paragraph and `## Reference`:

```markdown
## The SCOPE stage

The stage pattern (E4–E6 copy this shape): dispatch a fresh-context subagent
from a template, verify its artifact mechanically, record it via
`supskill-state`, advance, fall through.

1. **Resume idempotence.** If `artifacts.sprint_doc` is recorded AND the file
   exists, SCOPE already ran — a crash between `artifact` and `advance` must
   not re-spend a run. Run `advance --to REFINE` and continue at the REFINE
   stage.
2. **Check the backlog.** If `backlog` is null (a pre-S3 state file; `init`
   now refuses to create this), report that a SCOPE sprint without a backlog
   has nothing to scope, name
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state init <sprint-id> --archive --backlog <path>`
   as the operator's way forward WITHOUT running it, and stop.
3. **Derive the output path** — a default the prompt supplies; the recorded
   artifact is the only authority anything downstream reads. The path is the
   backlog's own directory + `sprint-<id>-<slug>.md`, where `<id>` is the
   sprint id lowercased and `-<slug>` is dropped when `sprint.slug` is null.
   Example: backlog `docs/plans/sprints/backlog-01/backlog.md`, sprint `s4`,
   slug `plan-gate2` → `docs/plans/sprints/backlog-01/sprint-s4-plan-gate2.md`.
4. **Fill the template** [references/scope-prompt.md](references/scope-prompt.md)
   — every `{PLACEHOLDER}` it names. `{EXEMPLAR_DOCS}` is up to two existing
   `sprint-*.md` files in the backlog's directory (never the output path
   itself); if none exist, fill it with `none`.
5. **Dispatch** one general-purpose subagent whose entire prompt is the filled
   template.
6. **Verify mechanically.** The file must now exist at the derived output
   path. If it does not, report the agent's returned output verbatim and stop
   — no blocker verb is available before tasks exist, and the operator is one
   gate away.
7. **Record and advance.** Run
   `artifact --set sprint_doc --path <output path>`, then
   `advance --to REFINE`, then continue at the REFINE stage.
```

- [ ] **Step 5: Run the tests, the lint suite, and the invariant-3 grep**

Run: `uv run pytest tests/test_prompt_templates.py tests/test_skill_frontmatter.py -v && uv run pytest && uv run ruff check`
Expected: all PASS (body still well under 500 lines).

Run: `grep -n "state.json\|\.supskill/" skills/supskill/SKILL.md skills/supskill/references/scope-prompt.md`
Expected: every match is a read, a "never edit"/"must not" statement, or refusal text — no line instructs a write. `--archive` appears only inside the two refusal messages (run-checklist step 3 and SCOPE step 2).

- [ ] **Step 6: Commit**

```bash
git add skills/supskill/references/scope-prompt.md skills/supskill/SKILL.md tests/test_prompt_templates.py
git commit -m "feat: SCOPE stage - dispatch template, derived doc path, resume-idempotent row (SK-020)"
```

---

### Task 6: REFINE stage — the bridge, with the audit re-dispatch-once loop (SK-021)

**Files:**
- Create: `skills/supskill/references/refine-prompt.md`
- Modify: `skills/supskill/SKILL.md` (REFINE dispatch row + new stage section)
- Test: `tests/test_prompt_templates.py` (extend)

**Interfaces:**
- Consumes: `GRAMMAR_LINE` from `supskill_state.proofs` (Task 3); `supskill-audit --proofs <doc>` exit semantics (Task 4); the SCOPE fall-through (Task 5).
- Produces: `refine-prompt.md` with placeholders `{SPRINT_DOC_PATH}`, `{BACKLOG_PATH}`, `{REPO_ROOT}`, `{EXEMPLAR_DOC}`, `{AUDIT_FAILURES}`; the SKILL.md section `## The REFINE stage` ending at the hook Task 7 fills (`Gate 1 — next section`).

**Executor skills:** `superpowers:writing-skills`. Degrees of freedom: the citation duty, the in-place edit, the grammar quote, and the field list are low-freedom (exact); "what counts as a gap worth surfacing" is judgment and the template says so explicitly rather than pretending to specify it.

- [ ] **Step 1: Extend the tests (failing first)**

In `tests/test_prompt_templates.py`, add `REFINE` to the tripwire loop in `test_no_dispatch_template_line_instructs_running_the_state_cli` (`for template in (SCOPE, REFINE):`) and append:

```python
def test_refine_template_names_its_placeholders():
    text = REFINE.read_text(encoding="utf-8")
    for placeholder in (
        "{SPRINT_DOC_PATH}", "{BACKLOG_PATH}", "{REPO_ROOT}", "{EXEMPLAR_DOC}", "{AUDIT_FAILURES}",
    ):
        assert placeholder in text, placeholder


def test_refine_template_quotes_the_grammar_verbatim():
    # grammar-drift risk from the sprint risks table: proofs.py is the single
    # authority; the quote in the prompt is pinned to the parser's own constant
    from supskill_state.proofs import GRAMMAR_LINE

    assert GRAMMAR_LINE in REFINE.read_text(encoding="utf-8")


def test_refine_template_states_the_two_constraints_and_the_field_list():
    text = REFINE.read_text(encoding="utf-8")
    assert "cannot ask anyone anything" in text
    assert "must not run `supskill-state`" in text
    # the spec-shaped definition appears as a concrete field list, not as the word "spec-shaped"
    assert "DoR findings (refined at pull time)" in text
    assert "in place" in text
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_prompt_templates.py -v`
Expected: the four REFINE tests FAIL (`FileNotFoundError: ... refine-prompt.md`); the SCOPE tests still pass.

- [ ] **Step 3: Write the template**

Create `skills/supskill/references/refine-prompt.md` (the grammar line below must stay byte-identical to `proofs.GRAMMAR_LINE` — the test enforces it):

```markdown
# REFINE dispatch template

The conductor fills every `{PLACEHOLDER}` below and dispatches the result as
the complete prompt of one general-purpose subagent. On an audit failure the
conductor re-dispatches ONCE, with the audit's output filled into
`{AUDIT_FAILURES}`:

- `{SPRINT_DOC_PATH}` — the sprint doc to refine, in place
- `{BACKLOG_PATH}` — the backlog the doc was scoped from
- `{REPO_ROOT}` — the repository the stories will be executed against
- `{EXEMPLAR_DOC}` — a refined sprint doc whose shape is the target, or `none`
- `{AUDIT_FAILURES}` — `none` on the first dispatch; the audit's verbatim output on the second

---

You are refining the sprint document at {SPRINT_DOC_PATH} against the live
source under {REPO_ROOT}, at pull time. This pass exists because the backlog's
one-liners were written before the code moved beneath them; your job is to
surface what they could not know.

Two facts about your situation, stated up front because they are structural:

- **You cannot ask anyone anything.** You are a dispatched subagent: the
  question tool is unavailable to you, and in a headless run it would resolve
  instantly with an empty answer. Everything you need is in this prompt and on
  disk. Record open questions as numbered DoR findings with your recommended
  answer — the operator reads this doc at the very next gate.
- **You must not run `supskill-state`, and you must not read or write anything
  under `.supskill/`.** You edit one document; the conductor alone talks to
  state.

Duties, in order:

1. Read the doc, the backlog rows it commits, and then the live source those
   stories touch — the actual functions they will change, not just READMEs
   and docstrings. What counts as a gap worth surfacing is your judgment;
   this prompt does not pretend to specify it. What is NOT judgment: every
   claim you make about current behavior carries a backtick-wrapped
   `path:line` (or `path:start-end`) citation that resolves in {REPO_ROOT}'s
   working tree. A script audits every citation and fails this stage on any
   that does not resolve.
2. Grow the doc until it carries ALL of the following (this list is the
   contract, item by item):
   - a **Context** paragraph per story, grounded in `file:line` citations;
   - exact acceptance criteria per story — testable statements, not themes;
   - named interfaces and exact paths for everything a story creates or edits;
   - a `## DoR findings (refined at pull time)` section with numbered findings;
   - point deltas recorded story-by-story, inline: `N → M at pull time`;
   - one proof line per story, directly under the story heading, in exactly
     this grammar (three tokens, one value each, middot-separated):

     - **proof:** seam=unit|integration|app-level|e2e · impact=none|local|cross-surface|journey · provable=offline|operator

     Typical mapping: unit/integration → offline; app-level/e2e → operator; a
     mixed story classifies by its least-provable seam. Whether a
     classification is honest is the operator's judgment at the gate — the
     script only checks the vocabulary.
3. Edit {SPRINT_DOC_PATH} **in place**. Do not write a second file, do not
   rename it: the recorded artifact path never changes.
4. Shape target: {EXEMPLAR_DOC}.

If this is a re-dispatch, fix every audit failure below before anything else:

{AUDIT_FAILURES}

Report back a short summary only: the point deltas and the count of findings.
The document is the deliverable, not your report — nobody trusts the report
alone.
```

- [ ] **Step 4: Wire the REFINE row in SKILL.md**

Replace the REFINE row of the dispatch table:

```markdown
| `REFINE` | Follow **The REFINE stage** below. |
```

Insert after `## The SCOPE stage` (before `## Reference`):

```markdown
## The REFINE stage

Re-invoked at stage REFINE, always re-dispatch on the doc's current content.
Worst case an already-refined doc is refined again — acceptable, because
Gate 1 still guards the result. Detecting "already refined" would mean parsing
prose for state, which is exactly the coupling the resume contract refuses.

1. **Locate the doc:** `artifacts.sprint_doc` from `show --json`. If the file
   is missing from disk, report that and stop.
2. **Fill the template**
   [references/refine-prompt.md](references/refine-prompt.md):
   `{SPRINT_DOC_PATH}`, `{BACKLOG_PATH}`, `{REPO_ROOT}` (the repo root the
   conductor runs from), `{EXEMPLAR_DOC}` (an existing refined sprint doc in
   the backlog's directory, or `none`), `{AUDIT_FAILURES}` = `none`. Dispatch
   one general-purpose subagent with the filled template.
3. **Audit mechanically.** From the repo root, run:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-audit --proofs <doc path>`
   - Exit 0 → continue at **Gate 1** (next section).
   - Exit 1 → re-dispatch **once**: the same filled template with
     `{AUDIT_FAILURES}` set to the audit's failure output, quoted verbatim.
     Run the audit again. A second failure → report the failures verbatim and
     stop. Never dispatch a third time — there is no retry loop.
```

- [ ] **Step 5: Run the tests, lint, and the invariant-3 grep**

Run: `uv run pytest tests/test_prompt_templates.py tests/test_skill_frontmatter.py -v && uv run pytest && uv run ruff check`
Expected: all PASS.

Run: `grep -n "supskill-state\|\.supskill/" skills/supskill/references/refine-prompt.md`
Expected: only the "must not run" statement lines.

- [ ] **Step 6: Commit**

```bash
git add skills/supskill/references/refine-prompt.md skills/supskill/SKILL.md tests/test_prompt_templates.py
git commit -m "feat: REFINE stage - live-source refine template + audit re-dispatch-once loop (SK-021)"
```

---

### Task 7: Gate 1 — the operator reads the refined doc (SK-023)

**Files:**
- Modify: `skills/supskill/SKILL.md` (one new section; the REFINE section's step 3 already points at it)

**Interfaces:**
- Consumes: Task 6's REFINE section ("Exit 0 → continue at **Gate 1**"); the `gate` verb (`gate --id G1 --decision approved|rejected --response "<verbatim>"`, which accepts and records empty responses by design — `commands.py:197`); `advance --to PLAN` enforcement (`transitions.py:27-29`).
- Produces: the `## Gate 1 — the operator reads the refined doc` section. E6's G2/G3 stories copy this UX pattern.

**Executor skills:** `superpowers:writing-skills`. `docs/.ai/reports/contexts/01-claude-code-context-mechanics.md` §6 is the local authority on `AskUserQuestion` mechanics (subagent-stripped; headless auto-resolve empty in ~37ms, closed "not planned") — do not re-derive its behavior from memory.

- [ ] **Step 1: Write the section**

Insert into `skills/supskill/SKILL.md` after `## The REFINE stage` (before `## Reference`):

```markdown
## Gate 1 — the operator reads the refined doc

The CLI records empty gate responses BY DESIGN — a fabricated approval must
leave a readable empty quote in the trail. So the refusal to treat silence as
consent lives here, in the conductor, and nowhere else.

1. **Ask for real.** Use the `AskUserQuestion` tool: approve / reject the
   refined sprint doc at its recorded path, free text welcome. Name the doc
   path in the question so the operator knows what they are approving.
2. **An empty or auto-resolved answer is not a decision.** In headless runs
   the question tool resolves instantly with an empty answer. If the answer
   comes back empty, do NOT call `gate`. Report that Gate 1 requires an
   interactive operator, and stop.
3. **Record verbatim.** A non-empty answer — the selected label plus any free
   text, unedited — goes to:
   `gate --id G1 --decision <approved|rejected> --response "<verbatim>"`
4. `approved` → `advance --to PLAN` → continue at the `PLAN` dispatch row
   (E4's honest stub: it reports and stops — do not improvise PLAN).
5. `rejected` → the decision is recorded and final for this pass; report it
   and stop, naming the rework loop: the operator edits the doc directly or
   asks for a fresh REFINE pass, then re-invokes `/supskill run <sprint-id>`
   and re-gates. The last decision wins in state while every attempt stays in
   the trail.
```

- [ ] **Step 2: Run the suite and the prose self-checks**

Run: `uv run pytest && uv run ruff check`
Expected: all green (`test_body_stays_under_500_lines` now measures the full E3 body, ~190 lines).

Run: `grep -cn "AskUserQuestion" skills/supskill/SKILL.md && grep -n "gate --id G1" skills/supskill/SKILL.md`
Expected: `AskUserQuestion` appears in the Gate 1 section; the `gate` call appears exactly once, in step 3, and nothing anywhere offers `--yes` or auto-approval (grep `-i "auto-approve\|--yes"` → no hits).

- [ ] **Step 3: Commit**

```bash
git add skills/supskill/SKILL.md
git commit -m "feat: Gate 1 - verbatim operator decision; an empty answer is not a decision (SK-023)"
```

---

### Task 8: The sprint demo checklist (operator-run exit criterion — the heart in anger)

**Files:**
- Create: `.superpowers/sdd/s3/demo-checklist.md` (sprint scratch — gitignored by design; no commit)

**Interfaces:**
- Consumes: everything — the complete E3 conductor, installed or loadable as a plugin, plus real tokens.
- Produces: the script the operator runs, and the F-5 / PAR-deferral data point. `seam: app-level`, `provable: operator` — **the sprint does not close on offline green alone**; its output is a real S4 sprint doc the operator was going to need anyway.

- [ ] **Step 1: Write the demo checklist**

Create `.superpowers/sdd/s3/demo-checklist.md`:

```markdown
# S3 demo — SCOPE → REFINE → Gate 1 in anger (operator-run, real tokens)

Run in THIS repo (supskill's own), at the repo root. Expected outcomes are
written before running; any mismatch fails the demo. Either G1 verdict on the
S4 doc's quality is the F-5 / PAR-deferral data point (S3 DoR finding 4) —
record it either way; a rejection is the gate WORKING, not a demo failure.

- [ ] 1. Preflight: working tree clean enough to spot new files; no
      `.supskill/` at the repo root (or archive an old run deliberately, by
      hand). `docs/plans/sprints/backlog-01/backlog.md` exists.
- [ ] 2. `/supskill run s4 --backlog docs/plans/sprints/backlog-01/backlog.md --slug plan-gate2`
      → the conductor init's s4 at SCOPE and dispatches the scope agent; a
      real `docs/plans/sprints/backlog-01/sprint-s4-plan-gate2.md` appears
      (beside this repo's hand-authored sprint docs), gets recorded, and the
      conductor advances to REFINE.
- [ ] 3. Interrupt (Esc) once the conductor reports the doc recorded and the
      stage advanced — before REFINE's dispatch completes. Verify on disk:
      `scripts/supskill-state show --json` → `"stage": "REFINE"`,
      `artifacts.sprint_doc` = the derived path.
- [ ] 4. `/clear` — the context is now genuinely empty (invariant 5).
- [ ] 5. `/supskill run s4` → resumes onto REFINE from disk alone (re-init is
      a fail), re-dispatches REFINE on the doc's current content; the doc
      grows a cited "DoR findings (refined at pull time)" section, point
      deltas, and one proof line per story; the conductor runs
      `supskill-audit --proofs` on it and it passes (one re-dispatch allowed).
- [ ] 6. Gate 1 asks FOR REAL via AskUserQuestion. Read the refined S4 doc
      first. Answer with real words, not a bare click.
- [ ] 7. Verify the trail: the last line of `.supskill/gates.jsonl` is G1
      with your decision and a NON-EMPTY verbatim response.
- [ ] 8. approved → the conductor ran `advance --to PLAN` and stopped on the
      honest E4 stub ("PLAN … lands with E4"). rejected → stage is still
      REFINE and the conductor named the rework loop, then stopped.
- [ ] 9. Record below, verbatim: pass/fail per step, the G1 decision, and
      your honest read on the refinement's depth (did it cite real code or
      cluster on READMEs?) — this is the PAR-at-REFINE revisit-trigger
      evidence.
```

- [ ] **Step 2: Hand it to the operator**

Report: the demo checklist is at `.superpowers/sdd/s3/demo-checklist.md`; it is the exit criterion for SK-020/021/023's prompt-shaped acceptance and the F-5 data point; the sprint stays open until the operator runs it. No commit — the scratch dir is gitignored by design.

---

### Task 9: Apply the S3 DoR backlog deltas

**Files:**
- Modify: `docs/plans/sprints/backlog-01/backlog.md`

**Interfaces:**
- Consumes: nothing from other tasks (docs-only; the operator commissioning this plan is the acceptance the sprint doc's "once the operator accepts" clause names).
- Produces: a backlog that matches what S3 actually committed — the five deltas from the sprint doc's "Backlog deltas — proposed" section.

- [ ] **Step 1: Re-point and re-scope SK-020 (3 → 4)**

In the E3 table, replace the SK-020 row:

```markdown
| SK-020 | SCOPE stage: dispatch `pm-execution:sprint-plan` as a subagent; write the sprint doc; record the artifact path. `sprint-plan` has **no output-path convention** — supskill supplies `<backlog-dir>/sprint-<normalized-id>-<slug>.md` as the dispatch default; `artifacts.sprint_doc` stays the only authority. Grown at S3 DoR: `init` refuses SCOPE entry without `--backlog`; `advance --to REFINE` requires a recorded, existing `sprint_doc` (`transitions.py` previously had no REFINE branch). | 4 | M | ☐ |
```

- [ ] **Step 2: Record the grammar decision on SK-022**

Replace the SK-022 row:

```markdown
| SK-022 | Proof-seam classification per story (`seam:`, `impact:`) → `provable: offline \| operator`. **E5 cannot drain-then-halt without this.** S3 DoR: the grammar and its parser (`proofs.py`) land in E3 so the format is fixed before E4 parses it; SK-033 only adds the state-loading verb (its points unchanged). | 5 | M | ☐ |
```

- [ ] **Step 3: Add SK-024 to E3**

Append after the SK-023 row in the E3 table:

```markdown
| SK-024 | Citation audit: `scripts/supskill-audit` verifies every backtick-wrapped `file:line` citation in a sprint doc resolves against the working tree; the conductor runs it before Gate 1. The mechanical floor under F-5 — it proves citations *resolve*, not that claims are true. PAR at REFINE deferred with a named revisit trigger: if S3's demo shows a shallow refinement passing both the audit and the operator, E6's PAR story extends to REFINE. (New at S3 DoR, finding 4.) | 3 | M | ☐ |
```

- [ ] **Step 4: Update the totals**

- Summary table: E3 row `| 19 |` → `| 23 |`.
- Section header: `## E3 — SCOPE + REFINE + Gate 1 (19 pts) — **the heart**` → `(23 pts)`.
- `**Total: 120 pts.**` → `**Total: 124 pts.**`

- [ ] **Step 5: Record Gate 1 data point #3**

Append after the "Data point #2" paragraph at the end of backlog.md:

```markdown
**Data point #3 (S3 DoR, 2026-07-13):** refinement against live source grew scope
+4 pts (19 → 23), and the sharpest finding was again structural — a headless
conductor would have silently self-approved its own gate (`AskUserQuestion`
auto-resolves empty × `gate`'s by-design acceptance of empty responses), which
no backlog one-liner mentioned. The refusal now lives in the conductor
(SK-023). Three sprints, three data points, same direction. (Report §7.2)
```

- [ ] **Step 6: Commit**

```bash
git add docs/plans/sprints/backlog-01/backlog.md
git commit -m "docs: apply S3 DoR backlog deltas (SK-020 4pts, SK-024 new, E3 23pts, total 124)"
```

---

## Exit criteria mapping (sprint doc → plan)

| Sprint exit criterion | Where it lands |
|---|---|
| SK-020: `init` (entry SCOPE) refuses without `--backlog`; `advance --to REFINE` refuses without a recorded, existing `sprint_doc` — both TDD'd offline | Tasks 1 + 2 |
| SK-020: `scope-prompt.md` with the D4 and invariant-3 statements; SCOPE row dispatches, records, advances, resumes idempotently | Task 5 |
| SK-021: `refine-prompt.md` with the concrete field list and grammar quote; audit → re-dispatch-once → stop loop in the REFINE row | Task 6 |
| SK-022: `proofs.py` parses this sprint doc's five proof lines; unknown/duplicate/missing all rejected offline | Task 3 |
| SK-023: real `AskUserQuestion`; empty answer is not a decision; verbatim response to `gate`; approved → PLAN stub | Task 7 |
| SK-024: `supskill-audit` resolves every citation in the sprint doc, fails fabricated cites, `--help` states the resolve-not-truth limit | Task 4 |
| Suite pure offline and fast; TDD evidence per Python story | Tasks 1–4 step sequences |
| The sprint demo (operator-run, real tokens, `/clear` mid-sprint, verbatim G1 words on disk) | Task 8 — **operator-run; the sprint does not close on offline green alone** |
| Backlog deltas applied | Task 9 |

## Review pass (after all tasks)

Author↔review separation holds: dispatch `oh-my-claudecode:code-reviewer`, then `oh-my-claudecode:verifier`, in fresh contexts. Named checks this sprint (beyond the standing ones):

1. **Invariant 3, three surfaces:** no line of `commands.py`/new modules writes outside `store.py`'s primitives (the tripwire test covers the obvious case); no line of SKILL.md instructs editing `.supskill/` by hand; **new this sprint and recurring from now on** — no template under `skills/supskill/references/` instructs an agent to run `supskill-state` or touch `.supskill/`.
2. **Grammar drift:** the grammar line quoted in `refine-prompt.md` is byte-identical to `proofs.GRAMMAR_LINE` (pinned by test; diff-check anyway).
3. **D4 statements:** both templates state the agent cannot ask and give full input up front; the only `AskUserQuestion` in the whole flow is Gate 1's, in the conductor.
4. **No G1 shortcut:** nothing anywhere offers `--yes`, auto-approve, or a default answer; the empty-answer refusal is present and unconditional.
5. **E4 boundary:** the PLAN row is still the untouched honest stub; `superpowers:writing-plans` is not invoked anywhere.
