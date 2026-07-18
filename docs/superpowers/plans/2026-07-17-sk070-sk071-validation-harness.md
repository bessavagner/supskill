# SK-070 / SK-071 — E8 Validation Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the offline harness E8's two validation stories need — a disposable fixture repo with
a toy two-sprint backlog (SK-070) and a runbook for driving blinkebot's real, already-live sprint
(SK-071) — plus a shared report template, so an operator can actually run both gated, real-LLM-call
validations and record a pass/fail verdict.

**Architecture:** This plan does **not** execute either live validation — per the design doc's own
split ("Requires real runs; manual and gated"), an autonomous agent is never the one spending real
API budget against a project the operator depends on. It builds everything offline-provable around
that boundary: the fixture project itself, two runbooks (mirroring `evals/README.md`'s
operator-run-and-live framing, already used for SK-061), and a shared report template — each guarded
by a substring-assertion test in the same style `tests/test_review_prose.py` already uses for
`SKILL.md`. The backlog rows for SK-070/SK-071 and `README.md`'s E8 status stay unflipped until an
operator has actually run both validations for real — this plan explicitly does not flip them.

**Tech Stack:** Python 3.11+, pytest, plain Markdown. No new dependencies.

## Global Constraints

- Python ≥3.11, offline suite only: `uv run pytest -q` and `uv run ruff check` must stay green after
  every task. Every test this plan adds must be genuinely offline — no network calls, no `claude -p`,
  no dependency on either live run having happened.
- TDD every step: write the failing test before the file it asserts on.
- No git commit or PR text may name Claude, Anthropic, or carry an AI-attribution trailer.
- **Do not run either live validation as part of executing this plan.** SK-070's fixture run and
  SK-071's blinkebot drive are real, gated, operator-initiated actions with real token cost against
  a project (blinkebot) that already has a real, uncommitted, in-progress conductor run on disk. This
  plan's tasks build the harness only; running it is a separate step the operator takes afterward.
- Do not flip `docs/plans/sprints/backlog-01/backlog.md`'s SK-070/SK-071 status cells or
  `README.md`'s E8 status row in any task below — that happens by hand, in a separate `docs:` commit,
  only once an operator has filed a passing report for both.

---

### Task 1: SK-070 — the fixture repo's toy two-sprint backlog

**Files:**
- Create: `validation/fixture-repo/README.md`
- Create: `validation/fixture-repo/docs/plans/sprints/backlog-01/backlog.md`
- Test: `tests/test_fixture_backlog.py`

**Interfaces:**
- Consumes: nothing — this is a static fixture.
- Produces: a well-formed two-epic, four-story backlog other tasks' runbooks (Task 2) point at, at
  the fixed path `validation/fixture-repo/docs/plans/sprints/backlog-01/backlog.md`. Story ids are
  `SK-001`..`SK-004`; epics are `E1` ("Greeting core") and `E2` ("Greeting CLI").

- [ ] **Step 1: Write the failing test**

Create `tests/test_fixture_backlog.py`:

```python
"""SK-070: the fixture repo's toy backlog is well-formed offline.

The live end-to-end run through both its sprints is SK-070's actual accept
criteria and needs real LLM calls (validation/fixture-run.md) - deliberately
not part of this offline suite, the same split evals/ already uses for
SK-061. What IS offline and asserted here: the backlog itself parses in the
row format every other backlog in this repo already uses, both epics exist,
and every story id is well-formed - the mechanical floor a real run should
never trip over.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_BACKLOG = (
    REPO_ROOT / "validation" / "fixture-repo" / "docs" / "plans" / "sprints" / "backlog-01" / "backlog.md"
)

ROW = re.compile(r"^\| (SK-\d{3}) \| (.+) \| (\d+) \| ([MSCW]) \| (☐|☑) \|$", re.MULTILINE)


def _rows() -> list[tuple[str, str, str, str, str]]:
    text = FIXTURE_BACKLOG.read_text(encoding="utf-8")
    return ROW.findall(text)


def test_the_fixture_backlog_file_exists():
    assert FIXTURE_BACKLOG.is_file()


def test_every_story_row_matches_the_repos_own_row_format():
    rows = _rows()
    assert len(rows) >= 4  # both epics, at least two stories each


def test_story_ids_are_unique_and_sequential_from_sk_001():
    ids = [row[0] for row in _rows()]
    assert ids == sorted(ids)
    assert ids[0] == "SK-001"
    assert len(ids) == len(set(ids))


def test_both_epics_are_present_in_the_summary_table():
    text = FIXTURE_BACKLOG.read_text(encoding="utf-8")
    assert "| **E1** | Greeting core | 3 | M |" in text
    assert "| **E2** | Greeting CLI | 3 | M |" in text


def test_every_story_starts_todo_not_already_done():
    assert {row[4] for row in _rows()} == {"☐"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_fixture_backlog.py -v`
Expected: `test_the_fixture_backlog_file_exists` FAILS (`assert False`); the other four tests ERROR
with `FileNotFoundError` — none of the fixture files exist yet.

- [ ] **Step 3: Create the fixture project**

Create `validation/fixture-repo/README.md`:

```markdown
# fixture-repo

A throwaway Python project used only to drive `supskill` end-to-end for real (SK-070). It starts
with nothing but this README and its backlog; `supskill` builds the rest, sprint by sprint.

Never run a sprint against this copy in place — see `validation/fixture-run.md` for how to copy it
to a scratch directory first.
```

Create `validation/fixture-repo/docs/plans/sprints/backlog-01/backlog.md`:

```markdown
# fixture-repo — Backlog 01: greeter

**Date:** 2026-07-17 · Legend: points = Fibonacci · pri = MoSCoW (M/S/C/W) · status ☐ todo / ☑ done

A throwaway two-epic backlog for supskill's own end-to-end validation (SK-070). It has no other
purpose: every story is deliberately tiny so a real, gated `supskill` run through both sprints stays
cheap.

## Summary — epics, in recommended build order

| # | Epic | Pts | Pri |
|---|------|-----|-----|
| **E1** | Greeting core | 3 | M |
| **E2** | Greeting CLI | 3 | M |

**Total: 6 pts.**

## E1 — Greeting core (3 pts)

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-001 | `greet(name: str) -> str` returns `"Hello, <name>!"`; raises `ValueError` on an empty or whitespace-only name. | 2 | M | ☐ |
| SK-002 | `greet` strips surrounding whitespace from `name` before formatting. | 1 | M | ☐ |

## E2 — Greeting CLI (3 pts)

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-003 | A `greet` CLI script takes one positional `name` argument and prints `greet(name)` to stdout. | 2 | M | ☐ |
| SK-004 | The CLI exits 1 and prints a usage error to stderr when `name` is missing. | 1 | M | ☐ |

## Recommended first sprint

**S1 — Greeting core (E1, 3 pts).** E2 depends on it: the CLI wraps `greet`.
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_fixture_backlog.py -v`
Expected: all five tests PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: PASSES.

Run: `uv run ruff check`
Expected: no lint errors.

- [ ] **Step 6: Commit**

```bash
git add validation/fixture-repo tests/test_fixture_backlog.py
git commit -m "test: add the fixture repo's toy two-sprint backlog for SK-070"
```

---

### Task 2: SK-070 — the fixture-run runbook

**Files:**
- Create: `validation/fixture-run.md`
- Test: `tests/test_validation_docs.py` (new file)

**Interfaces:**
- Consumes: `validation/fixture-repo/` from Task 1.
- Produces: `validation/fixture-run.md`, the operator runbook for driving both fixture sprints for
  real. Referenced by `validation/README.md` (Task 5) and pointing at `validation/report-template.md`
  (Task 4).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_validation_docs.py`:

```python
"""E8's runbooks state their own gated, operator-run status - tripwires for a runbook that quietly
loses the "not in the offline suite" framing SK-070/SK-071 depend on. Asserted the same way
tests/test_review_prose.py asserts SKILL.md's own prose, and mirrors evals/README.md's framing.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATION = REPO_ROOT / "validation"


def test_the_fixture_runbook_exists_and_states_it_is_gated():
    text = (VALIDATION / "fixture-run.md").read_text(encoding="utf-8")
    assert "operator-run and live" in text


def test_the_fixture_runbook_names_both_toy_sprints():
    text = (VALIDATION / "fixture-run.md").read_text(encoding="utf-8")
    assert "s1" in text.lower() and "s2" in text.lower()


def test_the_fixture_runbook_warns_against_running_in_place():
    text = (VALIDATION / "fixture-run.md").read_text(encoding="utf-8")
    assert "git init" in text
    assert "scratch" in text.lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_validation_docs.py -v`
Expected: all three tests ERROR with `FileNotFoundError` — `validation/fixture-run.md` does not exist
yet.

- [ ] **Step 3: Write the runbook**

Create `validation/fixture-run.md`:

```markdown
# Driving the fixture repo for real (SK-070)

**Status: operator-run and live** — a real, gated `supskill` run through both sprints of
`validation/fixture-repo`'s toy backlog. Deliberately **not** part of the offline `uv run pytest`
suite, the same split `evals/README.md` already uses for SK-061. The only offline artifact is the
fixture itself (`validation/fixture-repo/`) and its shape test (`tests/test_fixture_backlog.py`).

## What this proves

The design doc's own validation bar: "v1 is built by hand, then earns its keep by driving a real
sprint. If it cannot run one sprint the operator would have run anyway, it does not ship."
(`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:345`.) SK-070 is the cheap, disposable
version of that bar — two tiny sprints, six points total, run against a project nobody actually
depends on — before SK-071 spends real effort on blinkebot.

## Set up an isolated copy

Never run this against `validation/fixture-repo/` in place — the run mutates it (`.supskill/`,
committed files, git history). Copy it to a scratch directory and `git init` there:

```bash
cp -r validation/fixture-repo /tmp/supskill-fixture-run
cd /tmp/supskill-fixture-run
git init -q
git add -A
git commit -q -m "fixture: initial state"
```

## Install the plugin

Install `supskill` from your marketplace into this scratch repo the same way any real project would
(this repo's own `README.md` Installation section) — not a symlink or clone into `.claude-plugin/`.

## Run both sprints

From `/tmp/supskill-fixture-run`, invoke the conductor per `skills/supskill/SKILL.md`'s entry point
for sprint `s1` (E1 — Greeting core), then again for `s2` (E2 — Greeting CLI) once `s1`'s Gate 3
proposes it. Follow every stage and gate exactly as the skill instructs — do not skip a gate because
the fixture is small; a skipped gate proves nothing about the real one.

## Record the result

Fill in `validation/report-template.md` (copy it to `validation/reports/fixture-run-<date>.md`) once
both sprints reach Gate 3. Name every gate decision, every blocker or parked task, and the total
tokens spent per stage (`.supskill/runs/<id>/costs.jsonl` in the scratch copy).

## What a pass looks like

Both sprints reach Gate 3 approved, `greet` and its CLI exist and satisfy every story's acceptance
criteria named in the backlog, and nothing in the run required stepping outside `supskill-state` to
make progress. Anything short of that is a finding for the report, not a reason to patch the fixture
until it passes.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_validation_docs.py -v`
Expected: all three tests PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: PASSES.

Run: `uv run ruff check`
Expected: no lint errors.

- [ ] **Step 6: Commit**

```bash
git add validation/fixture-run.md tests/test_validation_docs.py
git commit -m "docs: add the SK-070 fixture-run runbook"
```

---

### Task 3: SK-071 — the blinkebot-run runbook

**Files:**
- Create: `validation/blinkebot-run.md`
- Test: `tests/test_validation_docs.py` (append)

**Interfaces:**
- Consumes: nothing from this repo — points at the sibling `blinkebot` checkout on disk (path is the
  operator's own; the runbook says "wherever your blinkebot checkout lives" rather than hardcoding
  one).
- Produces: `validation/blinkebot-run.md`, referenced by `validation/README.md` (Task 5) and pointing
  at `validation/report-template.md` (Task 4).

**Context the runbook must reflect (verified while writing this plan, 2026-07-17):** the backlog's
SK-071 row, written 2026-07-12, says "Drive blinkebot S11 for real." blinkebot's own backlog
(`docs/plans/sprints/backlog-02/backlog.md:187-192` in that repo) now shows S11 already shipped —
a daemon and read-budget allocator landed under that sprint id before this story was ever picked up.
Separately, blinkebot already has a live, uncommitted, in-progress `supskill` run on disk right now:
its `.supskill/state.json` reads sprint `s15`, stage `REFINE`, with `docs/plans/sprints/backlog-02/
sprint-s15.md` recorded as the `sprint_doc` artifact and three SCOPE/REFINE dispatches already
costed in `.supskill/runs/s15/costs.jsonl` (roughly 446k tokens total, timestamped 2026-07-17). The
runbook must not hardcode "S11" as a target — it must tell the operator to read blinkebot's live
state and resume whatever is actually in flight.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_validation_docs.py`:

```python
def test_the_blinkebot_runbook_exists_and_states_it_is_gated():
    text = (VALIDATION / "blinkebot-run.md").read_text(encoding="utf-8")
    assert "operator-run and live" in text


def test_the_blinkebot_runbook_warns_the_s11_label_is_historical():
    text = (VALIDATION / "blinkebot-run.md").read_text(encoding="utf-8")
    assert "already shipped" in text
    assert "supskill-state show --json" in text


def test_the_blinkebot_runbook_forbids_init_over_a_live_run():
    text = (VALIDATION / "blinkebot-run.md").read_text(encoding="utf-8")
    assert "do **not** `init` over it" in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_validation_docs.py -k blinkebot -v`
Expected: all three tests ERROR with `FileNotFoundError` — `validation/blinkebot-run.md` does not
exist yet.

- [ ] **Step 3: Write the runbook**

Create `validation/blinkebot-run.md`:

```markdown
# Driving blinkebot for real (SK-071)

**Status: operator-run and live** — the actual bar E8 exists to clear: "drive a real sprint against
a project the operator actually depends on. If it cannot run one sprint the operator would have run
anyway, it does not ship." (`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:345`.)
Deliberately **not** part of the offline `uv run pytest` suite — the live run itself is the accept
criteria, not a test file.

## "S11" is a historical label, not a target

The backlog names this story "Drive blinkebot S11 for real," written 2026-07-12. blinkebot's own
backlog (`docs/plans/sprints/backlog-02/backlog.md:187-192` in that repo) now shows S11 **already
shipped** — a daemon and read-budget allocator landed under that sprint id before this story was ever
picked up. Do not chase the literal string "S11": read blinkebot's live state instead.

## Read the live state before doing anything

blinkebot may already have a `.supskill/` directory — a real conductor run against it may already be
in progress, not hypothetical:

```bash
cd /path/to/your/blinkebot/checkout
supskill-state show --json
```

If that command refuses, naming "no state file", there is no run in flight and you are starting one
fresh, per `skills/supskill/SKILL.md`'s entry point, against whatever sprint is next in blinkebot's
own current backlog. If it succeeds, it names the sprint id, stage, and recorded artifacts of a run
already under way — resume that, per the next section. Trust this command's live output over any
snapshot in this file; state moves.

## Resume, do not restart

If `show --json` reports an in-flight sprint, resume it exactly where `skills/supskill/SKILL.md`'s
entry point says a live `state.json` resumes — do **not** `init` over it. `init` over an existing run
refuses by design (`tests/test_run_matrix.py::test_cell_mismatch_init_refuses_and_names_archive_without_using_it`)
and `--archive` is never the conductor's call to make; if a fresh sprint really is warranted, that is
a decision for you, the operator, made explicitly outside this runbook.

## Follow the conductor to Gate 3

Continue the sprint through Gate 1 (approve or send back the refined sprint doc), PLAN + Gate 2,
EXECUTE's drain-then-halt, REVIEW's PAR, and Gate 3 — every gate a real `AskUserQuestion` answer, per
`skills/supskill/references/gate.md`. Let it run into whatever it actually finds; do not pre-decide
the outcome to make the validation look clean.

## Record the result

Fill in `validation/report-template.md` (copy it to `validation/reports/blinkebot-<sprint-id>-
<date>.md`) once the sprint closes at Gate 3. This is the artifact that answers the design doc's own
question — did it "run one sprint the operator would have run anyway"? A yes ships E8; a no is a real
finding, not a reason to rerun until it looks better.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_validation_docs.py -v`
Expected: all six tests in the file PASS (three from Task 2, three new).

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: PASSES.

Run: `uv run ruff check`
Expected: no lint errors.

- [ ] **Step 6: Commit**

```bash
git add validation/blinkebot-run.md tests/test_validation_docs.py
git commit -m "docs: add the SK-071 blinkebot-run runbook"
```

---

### Task 4: shared report template

**Files:**
- Create: `validation/report-template.md`
- Modify: `validation/fixture-run.md` (add a pointer, if not already present from Task 2's text)
- Modify: `validation/blinkebot-run.md` (add a pointer, if not already present from Task 3's text)
- Modify: `.gitignore` (ignore filled-in reports, keep the directory tracked)
- Create: `validation/reports/.gitkeep`
- Test: `tests/test_validation_docs.py` (append)

**Interfaces:**
- Consumes: nothing.
- Produces: `validation/report-template.md`, a single shared template both runbooks point at (already
  named as `validation/report-template.md` in both Task 2's and Task 3's runbook text above, so no
  further edit to those two files is needed here — this task only needs to create the template
  itself and verify the cross-links).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_validation_docs.py`:

```python
def test_the_report_template_exists_and_names_every_required_section():
    text = (VALIDATION / "report-template.md").read_text(encoding="utf-8")
    for heading in ("## Run identity", "## Gate decisions", "## Cost", "## Findings", "## Verdict"):
        assert heading in text


def test_the_report_template_points_at_the_designs_own_validation_bar():
    text = (VALIDATION / "report-template.md").read_text(encoding="utf-8")
    assert "docs/.ai/reports/2026-07-12-supskill-design-decisions.md:345" in text


def test_both_runbooks_point_at_the_shared_report_template():
    fixture = (VALIDATION / "fixture-run.md").read_text(encoding="utf-8")
    blinkebot = (VALIDATION / "blinkebot-run.md").read_text(encoding="utf-8")
    assert "report-template.md" in fixture
    assert "report-template.md" in blinkebot
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_validation_docs.py -k "report_template" -v`
Expected: the first two tests ERROR with `FileNotFoundError` (`validation/report-template.md` does
not exist yet); the cross-link test PASSES already (both runbooks already name
`report-template.md` from Tasks 2/3's text) — confirm this with the run, do not treat an early pass
as a mistake.

- [ ] **Step 3: Write the template**

Create `validation/report-template.md`:

```markdown
# E8 validation report — <fixture-run | blinkebot-<sprint-id>> — <date>

Copy this file to `validation/reports/<name>-<date>.md` and fill in every section before treating
the run as evidence. An incomplete report is not a pass.

## Run identity

- Target: `<validation/fixture-repo scratch copy at PATH | blinkebot at PATH>`
- Sprint id(s) driven: `<>`
- Conductor / plugin version: `<supskill vX.Y.Z, from .claude-plugin/plugin.json>`
- Date range: `<start>` – `<end>`

## Gate decisions

| Gate | Sprint | Decision | Operator's verbatim response (or a pointer to `gates.jsonl`) |
|---|---|---|---|
| G1 | | | |
| G2 | | | |
| G3 | | | |

## Cost

Pull from `.supskill/runs/<id>/costs.jsonl` in the run's own working tree.

| Stage | Label | Tokens | Tool uses |
|---|---|---|---|
| | | | |

## Findings

- Blockers recorded (`blockers.jsonl`): `<>`
- Tasks parked, and why: `<>`
- PAR review findings at `confidence=high` or `confidence=actionable`: `<>`
- Anything that required stepping outside `supskill-state` to make progress: `<>`

## Verdict

Did this run one sprint the operator would have run anyway — the design doc's own bar
(`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:345`)? **Yes / No**, and why, in your own
words — not a restatement of the checklist above.
```

Create `validation/reports/.gitkeep` (empty file), then add this line to `.gitignore`, after the
existing `.worktrees/` line:

```
validation/reports/*.md
```

This keeps `validation/reports/` itself tracked (via `.gitkeep`) while every filled-in report — a
point-in-time record of one real run, not a tracked source file — stays untracked, the same shape
`.supskill/` already uses for run state.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_validation_docs.py -v`
Expected: all nine tests in the file PASS (six from Tasks 2-3, three new).

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: PASSES.

Run: `uv run ruff check`
Expected: no lint errors.

- [ ] **Step 6: Commit**

```bash
git add validation/report-template.md validation/reports/.gitkeep .gitignore tests/test_validation_docs.py
git commit -m "docs: add the shared E8 validation report template"
```

---

### Task 5: `validation/README.md` index

**Files:**
- Create: `validation/README.md`
- Test: `tests/test_validation_docs.py` (append)

**Interfaces:**
- Consumes: `validation/fixture-run.md`, `validation/blinkebot-run.md`, `validation/report-template.md`
  from Tasks 1-4.
- Produces: `validation/README.md`, the top-level index for E8's harness (mirrors `evals/README.md`'s
  role for SK-061). Nothing downstream in this repo consumes it — it is the operator's entry point.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_validation_docs.py`:

```python
def test_the_validation_readme_lists_both_stories_and_their_runbooks():
    text = (VALIDATION / "README.md").read_text(encoding="utf-8")
    assert "SK-070" in text and "fixture-run.md" in text
    assert "SK-071" in text and "blinkebot-run.md" in text


def test_the_validation_readme_states_the_backlog_flip_is_not_automatic():
    text = (VALIDATION / "README.md").read_text(encoding="utf-8")
    assert "no task in this plan does it for you" in text.lower() or "by hand" in text.lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_validation_docs.py -k validation_readme -v`
Expected: both ERROR with `FileNotFoundError` — `validation/README.md` does not exist yet.

- [ ] **Step 3: Write the index**

Create `validation/README.md`:

```markdown
# supskill validation (E8)

Two gated, operator-run, live validations — deliberately **not** part of the offline `uv run pytest`
suite, the same split `evals/README.md` uses for SK-061's eval loop. What's offline here is the
harness: a disposable fixture repo and the runbooks/report template below. The runs themselves cost
real tokens and real time and are never automated by a subagent.

| Story | Runbook | What it proves |
|---|---|---|
| SK-070 | [fixture-run.md](fixture-run.md) | A real, cheap, two-sprint run against a throwaway toy backlog (`fixture-repo/`) — the harness works at all. |
| SK-071 | [blinkebot-run.md](blinkebot-run.md) | A real sprint against blinkebot, a project the operator actually depends on — the design doc's own validation bar. |

Both write their result into a copy of [report-template.md](report-template.md) under
`validation/reports/` (gitignored except for `.gitkeep` — reports document a point-in-time run, not a
tracked source file).

## This directory's own limits

Building this harness is not the same as clearing E8. The backlog rows for SK-070 and SK-071, and
`README.md`'s E8 status row, stay unchecked / `⬜ backlog` until an operator has actually run both
validations and filed a passing report — flip them by hand, in a `docs:` commit, at that time; no
task in this plan does it for you.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_validation_docs.py -v`
Expected: all eleven tests in the file PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: PASSES.

Run: `uv run ruff check`
Expected: no lint errors.

- [ ] **Step 6: Commit**

```bash
git add validation/README.md tests/test_validation_docs.py
git commit -m "docs: add the E8 validation harness index"
```

---

## Self-review notes

- **Spec coverage:** SK-070 (Tasks 1-2) and SK-071 (Task 3) each get a fixture/runbook plus an
  offline shape test; Task 4 gives both a shared report template; Task 5 ties them together the way
  `evals/README.md` ties together SK-061's corpus and eval loop.
- **What this plan deliberately does not do:** neither live validation run, and neither backlog
  checkbox nor `README.md`'s E8 status flip — all three are explicitly out of scope per the Global
  Constraints and restated in `validation/README.md` itself, so the boundary is visible to whoever
  reads the harness later, not just to whoever executes this plan.
- **The blinkebot discovery:** at plan-writing time, blinkebot already has a live, uncommitted
  `supskill` run sitting at sprint `s15`, stage `REFINE`. `validation/blinkebot-run.md` (Task 3) is
  written to resume whatever is actually live rather than hardcode that snapshot, since it will be
  stale by the time an operator runs this.
- **Type/path consistency:** `validation/report-template.md` is named identically in Task 2's,
  Task 3's, and Task 5's prose, and Task 4 is the only task that creates it — checked against every
  other task's text above.
