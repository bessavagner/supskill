# Sprint 07 — Packaging & distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> Execution mode for this sprint is already decided: **subagent-driven**, fresh subagent per task, review between tasks.

**Goal:** supskill stops being a repo you clone and becomes a plugin you install — a first marketplace publish under the immutable `supskill@supskill` slug with its cross-marketplace dependencies resolving at install time, an authored should-trigger / should-not-trigger corpus scored by `skill-creator`'s real eval loop, and a README + build-in-public writeup that lead with the escalation finding phrased to match the corrected runtime.

**Architecture:** This is the first sprint whose deliverables are mostly *not* Python and mostly *not* offline-provable. The offline-provable slice is narrow and honest: an authored eval **corpus** (`evals/description-corpus.json`) validated by a pure pytest, plus two additive manifest **guards** (version consistency; `skill-creator` stays out of the runtime dependency set). Everything else closes on operator-run evidence — a real publish, a real `claude -p` eval run, a published writeup — exactly the honest-scope discipline S5 and S6 applied one and two stages down the loop. Nothing this sprint adds a `supskill-state` verb, mutates `.supskill/`, or bumps `state.json`'s schema.

**Tech Stack:** Python ≥3.11 stdlib only (zero runtime deps), pytest + ruff + pyyaml as dev deps, managed with `uv`. Claude Code plugin layout unchanged. The eval loop composes `skill-creator`'s installed `run_loop.py`/`run_eval.py` (a live `claude -p` loop) at author/eval time only — it is **not** a runtime dependency and is never conductor-dispatched.

## Global Constraints

Copied from the sprint spec (`docs/plans/sprints/backlog-01/sprint-s7-packaging-distribution.md`) and the standing project rules. Every task's requirements implicitly include this section.

- **Tests:** `uv run pytest`. The suite is **pure offline** — no LLM call, no subagent, no network, anywhere under `tests/`. Baseline at the tip of `main` (`2bd2ff5`): **306 passed in ~0.5s** (measured at pull time — the README's own `251` at `README.md:110` and `README.md:125` is already stale from S6 and is corrected in this sprint by SK-062). Every task ends with the full suite green.
- **Lint:** `uv run ruff check` must stay clean. Config is `pyproject.toml:22-32` — `line-length = 120`, rules `E,F,I,B,UP`, `src = ["scripts", "tests"]`. Every code block in this plan passes those rules as written: `from __future__ import annotations` only where needed, no unused imports, no line over 120 chars.
- **Zero runtime dependencies:** `pyproject.toml` `[project] dependencies = []` (`pyproject.toml:6`). `skill-creator` is composed at author/eval time via its own installed scripts — it is **not** added to `pyproject.toml`, to `plugin.json`'s `dependencies` (`.claude-plugin/plugin.json:10-13`), or to the `DISPATCHED_SKILL_PLUGINS` set (`tests/test_plugin_manifest.py:71-74`). (SK-061, DoR finding 6.)
- **The immutable slug ships as committed.** `plugin.json:2`, `.claude-plugin/marketplace.json:11`, and `README.md:132` already read `supskill` / `supskill@supskill`. SK-060 ships under it; no rename. After publish the slug is permanent.
- **No dependency version pins.** The live guard `tests/test_plugin_manifest.py:126-136` fails the suite if either declared dependency gains a `version`. A pin resolves against a `{plugin}--v*` tag neither upstream marketplace publishes and would *disable* supskill. SK-060 must not add one. (DoR finding 4.)
- **No AI attribution of any kind in commit messages or bodies** — no `Co-Authored-By`, no "Generated with" line, no mention of Claude/Anthropic/AI. Absolute; overrides any harness default.
- **Invariant 3 — no dispatched agent runs `supskill-state` or touches `.supskill/`.** Nothing in this sprint dispatches a state-writing subagent; the publish and the eval run touch neither `.supskill/` nor the state CLI.
- **Invariant 1 — compose, never reinvent.** SK-061 composes `skill-creator`'s real loop rather than building a bespoke scorer; SK-062 credits the composed skills.
- **The state CLI is always invoked as `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state`, from the target repo's root.** Unchanged from every prior sprint (no verb is added this sprint).
- **Commits:** one per code/doc task minimum, TDD evidence first (a failing — or, for a regression guard of an already-true invariant, an immediately-passing — test run before implementation). Operator-run tasks (publish, eval run, writeup, demo) close on operator evidence, not a commit.
- **Commands:** tests `uv run pytest <path> -v`, lint `uv run ruff check`.

## File Structure

| Path | Task | Responsibility |
|---|---|---|
| `evals/description-corpus.json` | 1 (create) | The authored should-trigger / should-not-trigger corpus for the conductor's shipped `description` — the offline artifact `skill-creator`'s loop consumes as `--eval-set` |
| `tests/test_eval_corpus.py` | 1 (create) | Pure-offline validation of the corpus's shape and near-miss coverage — the sprint's one genuinely new offline-provable slice |
| `tests/test_plugin_manifest.py` | 2 (extend) | Two additive guards: `plugin.json` version matches `pyproject.toml` (SK-060 tag hygiene); `skill-creator` is absent from the runtime dependency set (SK-061, DoR finding 6) |
| `evals/README.md` | 3 (create) | The eval-composition runbook: the exact `skill-creator` `run_eval.py`/`run_loop.py` invocation, the token budget, the disable-model-invocation separation, and why this is operator-run and out of the offline suite. Lives OUTSIDE `skills/` so the dependency-scan never reads `skill-creator` from it |
| *(git tag `v0.1.0` + GitHub release)* | 4 (operator) | The publish itself — release hygiene, not an install-resolution requirement; no in-tree file |
| `README.md` | 5 (modify), 8 (modify) | Task 5: finalize finding-first framing, refresh the stale test count, verify the install snippet against the published plugin. Task 8: flip the E7 status row to shipped |
| *(external `bessavagner-page`)* | 6 (operator) | The build-in-public writeup — external to this repo; leads with the corrected finding. Priority C, the deferrable half |
| `.superpowers/sdd/s7/demo-checklist.md` | 7 (create, gitignored) | The operator-run demo — the sprint's real exit criterion for SK-060/061/062 |
| `docs/plans/sprints/backlog-01/backlog.md` | 8 (modify) | Mark SK-060/061/062 shipped; record Data point #7 (0-point DoR, six corrections) |

**Task order honors the sprint doc's own "Capacity & sequencing" waves.** Wave A (Tasks 1–3) is the offline-first work — the corpus, the manifest guards, and the runbook — independent of the publish, the same reason S5 and S6 wrote their pure slices first: later operator steps consume artifacts that must already exist and be correct. Wave B (Task 4) is SK-060's operator-run publish; it depends on nothing in Wave A structurally but is the thing SK-061's live run and SK-062's install snippet are only *true* against (the sprint doc's critical path SK-060 → SK-061 → SK-062). Wave C (Tasks 5–6) is SK-062's prose: the README (in-tree, mostly already shipped) and the external writeup, which runs in parallel with B. Process tasks 7–8 come last: the demo (Task 7) is the operator-run exit criterion that consumes everything — a published plugin, the corpus, the runbook — and the backlog delta (Task 8) records the close. The **live eval run and the clean-environment install both live in the demo (Task 7)**, not in Wave A, because both need real tokens / a published artifact and are operator-gated.

**A note on internal spec tension, and the call this plan makes.** The sprint doc's SK-061 *accept bullets* (its authoritative, post-Gate-1 criteria) mandate composing `skill-creator`'s real `run_loop.py`/`run_eval.py` at `provable=operator` with a token budget, corpus-as-offline-artifact. Its older *exit-criteria* line still speaks of "an offline scorer" — the superseded option (a) from DoR finding 2, before Gate 1 picked option (b) on 2026-07-15. **This plan follows the accept bullets and the Gate 1 decision:** there is no bespoke offline scorer; the only offline artifact is the corpus and its shape test. The report SK-061 produces must state plainly that the hit rate is a real trigger rate for a command-registered copy of the shipped `description` (DoR finding 3), a fair proxy for auto-invoke were the flag ever relaxed — not a literal reading of the disabled auto-invoke path, and not an offline number that claims to predict live triggering.

---

### Task 1: The eval corpus + its offline shape test (SK-061)

**Files:**
- Create: `evals/description-corpus.json`
- Create: `tests/test_eval_corpus.py`

**Interfaces:**
- Consumes: nothing from other tasks — a static authored artifact plus a pure test.
- Produces: `evals/description-corpus.json`, a JSON list of `{"query": str, "should_trigger": bool, "category": str}` objects. `skill-creator`'s `run_eval.py` reads only `item["query"]` and `item["should_trigger"]` (verified by direct read of the installed `run_eval.py`, `run_single_query` / `run_eval`); the extra `"category"` key is ignored by that consumer and exists solely so Task 1's own test can assert near-miss coverage. Task 3's runbook names this file as `--eval-set`; Task 7's demo runs the loop against it.

**Context.** The corpus is the offline artifact unconditionally (sprint doc, Wave A). Its should-not-trigger half must include the near-misses that matter for a **side-effecting** conductor whose SKILL.md carries `disable-model-invocation: true` (`skills/supskill/SKILL.md:5`): read-only sprint questions, other-repo sprint tooling, and prompts that merely name "sprint" without wanting to *run* one. The conductor's shipped `description` under test is `skills/supskill/SKILL.md:3`. `skill-creator`'s flat schema is `{query, should_trigger}`; we add an optional `category` tag purely for our own coverage assertion — it does not reach the model and does not change what the loop scores.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_eval_corpus.py`:

```python
"""SK-061: the should-trigger / should-not-trigger corpus is well-formed offline.

The corpus is the one genuinely offline-provable slice of E7. The SCORING is a
live claude -p spend, composed from skill-creator's real loop and run by the
operator (evals/README.md) - NOT reproduced here, and NOT in this suite. What
IS offline and is asserted here: the corpus parses, every entry is well-formed,
both classes are represented, and the should-not-trigger half covers the three
near-miss buckets that matter for a side-effecting conductor (sprint doc,
SK-061 accept criteria): read-only sprint questions, other-repo sprint tooling,
and prompts that name "sprint" without wanting to run one.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS = REPO_ROOT / "evals" / "description-corpus.json"

# The should-not-trigger buckets SK-061's accept criteria name explicitly.
REQUIRED_NEGATIVE_CATEGORIES = {
    "read-only-sprint-question",
    "other-repo-tooling",
    "names-sprint-not-run",
}
# The should-trigger intents the description exists to catch.
REQUIRED_POSITIVE_CATEGORIES = {"start-sprint", "resume-sprint"}


def _corpus() -> list[dict]:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def test_corpus_parses_as_a_nonempty_list():
    corpus = _corpus()
    assert isinstance(corpus, list)
    assert len(corpus) >= 10  # enough for a meaningful trigger rate, both classes


def test_every_entry_is_well_formed_for_skill_creators_consumer():
    for entry in _corpus():
        assert set(entry) >= {"query", "should_trigger", "category"}, entry
        assert isinstance(entry["query"], str) and entry["query"].strip(), entry
        assert isinstance(entry["should_trigger"], bool), entry
        assert isinstance(entry["category"], str) and entry["category"].strip(), entry


def test_both_classes_are_represented():
    flags = {entry["should_trigger"] for entry in _corpus()}
    assert flags == {True, False}


def test_the_positive_half_covers_start_and_resume():
    present = {e["category"] for e in _corpus() if e["should_trigger"]}
    assert REQUIRED_POSITIVE_CATEGORIES <= present, REQUIRED_POSITIVE_CATEGORIES - present


def test_the_negative_half_covers_the_three_side_effecting_near_misses():
    present = {e["category"] for e in _corpus() if not e["should_trigger"]}
    assert REQUIRED_NEGATIVE_CATEGORIES <= present, REQUIRED_NEGATIVE_CATEGORIES - present


def test_queries_are_unique():
    queries = [e["query"] for e in _corpus()]
    assert len(queries) == len(set(queries))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_eval_corpus.py -v`
Expected: FAIL — `FileNotFoundError` (the corpus does not exist yet) on every test.

- [ ] **Step 3: Author the corpus**

Create `evals/description-corpus.json`:

```json
[
  {"query": "start a new sprint from my backlog", "should_trigger": true, "category": "start-sprint"},
  {"query": "run the next sprint in this repo", "should_trigger": true, "category": "start-sprint"},
  {"query": "kick off sprint s3 from docs/plans/sprints/backlog-01/backlog.md", "should_trigger": true, "category": "start-sprint"},
  {"query": "drive a sprint from my markdown backlog", "should_trigger": true, "category": "start-sprint"},
  {"query": "resume the sprint I was running", "should_trigger": true, "category": "resume-sprint"},
  {"query": "pick up my supskill sprint where it left off", "should_trigger": true, "category": "resume-sprint"},
  {"query": "continue the in-progress sprint from its saved state", "should_trigger": true, "category": "resume-sprint"},
  {"query": "what stage is the current sprint on?", "should_trigger": false, "category": "read-only-sprint-question"},
  {"query": "summarize what happened in the last sprint", "should_trigger": false, "category": "read-only-sprint-question"},
  {"query": "show me the sprint backlog file", "should_trigger": false, "category": "read-only-sprint-question"},
  {"query": "create a sprint for the team in Jira", "should_trigger": false, "category": "other-repo-tooling"},
  {"query": "plan a scrum sprint in Linear", "should_trigger": false, "category": "other-repo-tooling"},
  {"query": "run our CI pipeline in GitHub Actions", "should_trigger": false, "category": "other-repo-tooling"},
  {"query": "what does the word sprint mean in agile?", "should_trigger": false, "category": "names-sprint-not-run"},
  {"query": "write a blog post about sprint planning", "should_trigger": false, "category": "names-sprint-not-run"},
  {"query": "refactor the sprint burndown chart component", "should_trigger": false, "category": "names-sprint-not-run"}
]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_eval_corpus.py -v && uv run pytest && uv run ruff check`
Expected: all PASS — the 306 baseline plus the six new corpus tests, none broken.

- [ ] **Step 5: Commit**

```bash
git add evals/description-corpus.json tests/test_eval_corpus.py
git commit -m "feat: the should-trigger/should-not-trigger corpus for the conductor description, validated offline (SK-061)"
```

---

### Task 2: Two additive manifest guards — version consistency and skill-creator exclusion (SK-060, SK-061)

**Files:**
- Modify: `tests/test_plugin_manifest.py` (two new tests appended after `test_marketplace_lists_this_plugin`, `tests/test_plugin_manifest.py:139-144`)

**Interfaces:**
- Consumes: `MANIFEST` and `REPO_ROOT` (`tests/test_plugin_manifest.py:13-14`), `DISPATCHED_SKILL_PLUGINS` (`tests/test_plugin_manifest.py:71-74`), and `_declared_dependencies` (`tests/test_plugin_manifest.py:77-85`) — all already defined in the file.
- Produces: two regression guards. Neither changes behavior; both pin an invariant already true today, the same shape as the S6 plan's structural-regression tests (`docs/superpowers/plans/2026-07-14-sprint-s6-review-par-gate3.md` Task 3). So this task's step 2 does **not** manufacture a red bar — the guards pass immediately, and that fact is stated in the commit, exactly as S6 did.

**Context — why these two, and why now.**
- **Version consistency (SK-060):** SK-060 cuts a `v0.1.0` tag from `pyproject.toml`'s `version = "0.1.0"` (`pyproject.toml:3`) as release hygiene (DoR finding 4). `plugin.json` carries its own `"version": "0.1.0"` (`.claude-plugin/plugin.json:3`). A future bump to one and not the other would silently ship a tag that names a version the manifest disagrees with. This guard pins them equal so the tag is always consistent — it does not make the tag load-bearing for install (finding 4 is explicit that `source: "./"` at `.claude-plugin/marketplace.json:12` resolves install, not the tag).
- **skill-creator exclusion (SK-061, DoR finding 6):** SK-061 composes `skill-creator` at author/eval time only; the conductor never dispatches it. This guard asserts it is absent from both `DISPATCHED_SKILL_PLUGINS` and the declared runtime dependencies, so no one "helpfully" adds it — which would make `test_every_dispatched_skill_has_its_plugin_declared_as_a_dependency` (`tests/test_plugin_manifest.py:98`) demand a manifest entry for a tool no stage dispatches and pull a third cross-marketplace dep into the install path for no runtime reason.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the guard tests**

Append to `tests/test_plugin_manifest.py` (the module already imports `json` and `re` and defines `REPO_ROOT` / `MANIFEST` at `tests/test_plugin_manifest.py:9-14`; add `import tomllib` beside them at the top of the file):

```python
def test_plugin_version_matches_pyproject_so_the_release_tag_is_consistent():
    # SK-060: the v0.1.0 tag is cut from pyproject's version (release hygiene,
    # DoR finding 4 - NOT what install resolves against). Keep the manifest's
    # own version equal to it so the tag never names a version they disagree on.
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert manifest["version"] == pyproject["project"]["version"]


def test_skill_creator_is_not_a_runtime_dependency():
    # SK-061, DoR finding 6: skill-creator is an author/eval-time tool composed
    # by evals/README.md's loop - the conductor never dispatches it. It must stay
    # out of both the dispatched-skill set and the declared runtime dependencies,
    # or the declaration guard above would demand a manifest entry for a tool no
    # stage dispatches and pull a third cross-marketplace dep into the install.
    assert "skill-creator" not in DISPATCHED_SKILL_PLUGINS
    assert "skill-creator" not in _declared_dependencies()
```

- [ ] **Step 2: Run them — they pass immediately (regression guards, not behavior change)**

Run: `uv run pytest tests/test_plugin_manifest.py -v`
Expected: PASS immediately. These encode invariants already true today (version `0.1.0` on both sides; `skill-creator` absent from the manifest), the same shape as the S6 plan's structural-regression tests. There is no red bar to manufacture; state this in the commit rather than faking one.

- [ ] **Step 3: Run the full suite and lint**

Run: `uv run pytest && uv run ruff check`
Expected: all PASS — baseline plus the two guards.

- [ ] **Step 4: Commit**

```bash
git add tests/test_plugin_manifest.py
git commit -m "test: guard plugin/pyproject version parity and skill-creator's exclusion from runtime deps (SK-060, SK-061)"
```

---

### Task 3: The eval-composition runbook (SK-061)

**Files:**
- Create: `evals/README.md`

**Interfaces:**
- Consumes: Task 1's `evals/description-corpus.json`; the shipped `description` at `skills/supskill/SKILL.md:3`; the installed `skill-creator` scripts.
- Produces: `evals/README.md`, the operator-facing runbook Task 7's demo follows to run the eval. It lives outside `skills/` on purpose: `_skill_namespaces_dispatched` scans `skills/**/*.md` (`tests/test_plugin_manifest.py:88-95`), so keeping the runbook — which names `skill-creator` — out of that tree is what keeps the dependency-declaration guard from ever seeing `skill-creator` as a dispatched skill.

**Context.** The eval mechanism is `skill-creator`'s installed loop. Its `run_eval.py` writes a synthetic command file into a project's `.claude/commands/` so the description appears in Claude's `available_skills` list, then runs `claude -p <query>` three times per query (`runs_per_query` default 3), detecting a trigger from stream events. `run_loop.py` wraps that with an improve/train-test loop. Both are external plugin files (installed under `~/.claude/plugins/.../skill-creator/skills/skill-creator/scripts/`), read directly and verified — they carry no audit-resolvable in-tree `path:line`, so this runbook names them by path without a line citation. Two facts this runbook must record so the flag decision and the offline decision are never conflated (DoR finding 3): (1) the command-registration path is **separate** from `skills/supskill/SKILL.md:5`'s `disable-model-invocation: true`, which stays untouched; (2) the hit rate is therefore a real trigger rate for a command-registered copy of the shipped `description` — a fair proxy for auto-invoke were the flag relaxed, not a literal reading of the disabled path, and it does not claim to predict live auto-invocation.

**Executor skills:** `superpowers:writing-skills`.

- [ ] **Step 1: Write the runbook**

Create `evals/README.md`:

````markdown
# supskill description eval (SK-061)

This measures whether the conductor's shipped `description`
(`skills/supskill/SKILL.md`) fires on prompts that should start or resume a
sprint and stays silent on the near-misses that should not. It is **operator-run
and live** — a real `claude -p` spend — and is deliberately **not** part of the
offline `uv run pytest` suite. The only offline artifact is the corpus
(`evals/description-corpus.json`) and its shape test (`tests/test_eval_corpus.py`).

## What runs it

We compose `skill-creator`'s real eval loop (invariant 1 — compose, never
reinvent), not a bespoke scorer. `skill-creator` is installed under the
`claude-plugins-official` marketplace:

```
~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator
```

Its `scripts/run_eval.py` registers the description as a command in a project's
`.claude/commands/`, then runs `claude -p <query>` three times per query and
reports a per-query trigger rate. `scripts/run_loop.py` adds a description-
improvement loop with a train/test holdout.

`skill-creator` is an **author/eval-time tool only**. It is NOT a supskill
runtime dependency: it is absent from `pyproject.toml`, from
`.claude-plugin/plugin.json`'s `dependencies`, and from the conductor's
dispatched-skill set — guarded by
`tests/test_plugin_manifest.py::test_skill_creator_is_not_a_runtime_dependency`.

## The invocation

Set `SC` to the skill-creator skill directory above, `SUP` to this repo's root,
and `MODEL` to the model you are budgeting for. A single scoring pass:

```bash
SC=~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator
SUP=<absolute path to this repo>
cd "$SC"
python -m scripts.run_eval \
  --eval-set "$SUP/evals/description-corpus.json" \
  --skill-path "$SUP/skills/supskill" \
  --model "$MODEL" \
  --runs-per-query 3 \
  --verbose
```

`run_eval.py` reads the description straight from `skills/supskill/SKILL.md`; do
not pass `--description` unless you are testing an alternative. For the
description-improvement loop instead of a single pass, use `python -m
scripts.run_loop` with the same `--eval-set` / `--skill-path` / `--model` and
its `--holdout` default.

> **Open wiring detail, stated so the operator confirms it at run time.**
> `run_eval.py` discovers its project root by walking up from the working
> directory for a `.claude/` dir, and writes the synthetic command file there.
> Run from `$SC` (so its `from scripts...` imports resolve) it will use the
> nearest `.claude/` on that path. This does not change *what* is scored — the
> synthetic command carries the description under test — but confirm the run
> completes and reports rates before trusting the number. This is the smaller,
> reversible default; if the wiring misbehaves, run `run_eval.py` by absolute
> path with `$SC` on `PYTHONPATH` from `$SUP` instead.

## The token budget

Cost is `len(corpus) × runs-per-query` `claude -p` calls per pass (16 × 3 = 48
for the corpus as authored), times the number of loop iterations if you use
`run_loop.py`. **Set and record a bounded budget before running.** This is an
operator-gated spend, not an offline check.

## What the number means, and does not

The command-registration path above is **separate** from the conductor's own
`disable-model-invocation: true` frontmatter (`skills/supskill/SKILL.md`), which
stays untouched. So the hit rate is a **real trigger rate for a command-
registered copy of the shipped description** — a fair proxy for what auto-invoke
would do if that flag were ever relaxed, not a literal reading of the disabled
auto-invoke path, and not a prediction of live auto-invocation. Report it that
way. Relaxing the flag remains a separate, operator-owned call
(`skills/supskill/references/invocation-model.md:13-18`), with this hit rate as
evidence — not a packaging default.
````

- [ ] **Step 2: Verify it reads true against the installed scripts and the tree**

Run:
```bash
ls ~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator/scripts/run_eval.py
ls ~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator/scripts/run_loop.py
uv run pytest && uv run ruff check
```
Expected: both scripts exist at the documented path; the offline suite stays green (the runbook is prose, adds no test surface, and lives outside `skills/` so no dependency-scan reads `skill-creator` from it).

- [ ] **Step 3: Commit**

```bash
git add evals/README.md
git commit -m "docs: the eval-composition runbook - skill-creator's real loop, operator-run, budget and flag-separation stated (SK-061)"
```

---

### Task 4: Publish to the marketplace + cut v0.1.0 (SK-060) — operator-run

**Files:**
- No in-tree file. Produces a git tag `v0.1.0`, a GitHub release, and a verified clean-environment install. This task closes on **operator-run evidence**, not a commit — the same honest-scope shape S5/S6 gave their operator-provable stories.

**Interfaces:**
- Consumes: the already-committed manifests (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`), the public repo (`origin` → `github.com/bessavagner/supskill`, `"visibility":"PUBLIC"` at pull time), and Task 2's version-parity guard.
- Produces: an installable plugin. Task 5's install-snippet verification and Task 7's demo both consume a real published artifact.

**Context.** DoR finding 1: the repo is already public — that half is a verify, not a do. What is genuinely unwalked is `claude plugin marketplace add` + `install` from a clean environment and the cross-marketplace resolution underneath (`.claude-plugin/marketplace.json:8`'s `allowCrossMarketplaceDependenciesOn`), which today is only asserted by a test (`tests/test_plugin_manifest.py:113`), never walked against a published plugin (`README.md:142`). DoR finding 4: the `v0.1.0` tag is release hygiene, not the thing install resolves against (`source: "./"`, `.claude-plugin/marketplace.json:12`) — do not gate "install succeeds" on it, and do not add version pins (guard at `tests/test_plugin_manifest.py:126-136`). Every step below is operator-run and hard to reverse (a pushed tag, a public release, a permanent slug); confirm each before proceeding.

- [ ] **Step 1: Confirm the preconditions on disk**

Run:
```bash
gh repo view bessavagner/supskill --json visibility
git tag                       # expect empty - no release cut yet
uv run pytest && uv run ruff check   # green, including Task 2's version-parity guard
```
Expected: `"visibility":"PUBLIC"`; no existing tags; suite green. If any fails, stop — the publish is not ready.

- [ ] **Step 2: Cut and push the release tag (operator-confirmed)**

The tag matches `pyproject.toml`'s `version = "0.1.0"` (`pyproject.toml:3`), which Task 2's guard pins equal to `plugin.json`'s version. Confirm with the operator before pushing — a pushed tag and a public release are hard to reverse.

```bash
git tag -a v0.1.0 -m "supskill v0.1.0 - first packaged release (E7)"
git push origin v0.1.0
gh release create v0.1.0 \
  --title "supskill v0.1.0" \
  --notes "First packaged release. The finding this is built on: a delegated agent has no channel to escalate a decision (see README and docs/.ai/reports/2026-07-12-supskill-design-decisions.md). Composes superpowers and pm-execution as cross-marketplace dependencies."
```

The release notes reference the finding and the design record (the sprint's fourth SK-060 accept bullet). The tag is a GitHub marker only; it is **not** what install resolves against (DoR finding 4).

- [ ] **Step 3: Install from a clean environment and confirm resolution**

From a directory that is **not** this checkout (a clean environment, so nothing resolves from local files):
```bash
claude plugin marketplace add bessavagner/supskill
claude plugin install supskill@supskill
```
Expected: the marketplace adds and the plugin installs under the committed slug `supskill@supskill` (`README.md:132`), with **no rename**. Confirm the two cross-marketplace dependencies actually **resolve at install time**, not merely appear in the manifest: `superpowers` (from `claude-plugins-official`) and `pm-execution` (from `pm-skills`) are fetched, exercising `allowCrossMarketplaceDependenciesOn` (`.claude-plugin/marketplace.json:8`). Confirm `/supskill` is then available.

- [ ] **Step 4: Confirm the publish touched nothing it must not**

Verify: no `.supskill/` was created or mutated by the publish, no `supskill-state` verb was added, and no dependency in `.claude-plugin/plugin.json` gained a `version` field (re-run `uv run pytest tests/test_plugin_manifest.py::test_dependencies_are_unversioned_while_upstream_ships_no_tags -v` — still green). Record the install result (success, the resolved dependency list, any error) for Task 7's demo log.

---

### Task 5: README finalization — finding-first, fresh counts, verified install (SK-062)

**Files:**
- Modify: `README.md` (test-count corrections at `README.md:110` and `README.md:125`; finding-first framing at `README.md:14-22` confirmed; install snippet at `README.md:128-142` verified)

**Interfaces:**
- Consumes: Task 4's published plugin (for the install-snippet verification).
- Produces: a README whose quickstart is true rather than aspirational, and whose test count is accurate. Task 8 later flips the E7 status row; this task does not.

**Context.** The README already leads with the finding (`README.md:14-22`) and already carries the corrected runtime claim — commit `2bd2ff5` walked back the "silent empty answer" wording, and `README.md:18` now records that on Claude Code 2.1.210 `AskUserQuestion` returns a loud error rather than a silent empty answer. So the finding-first work is largely a **confirm**, not a rewrite. What is genuinely stale and in-tree is the **test count**: the suite is 306 today but `README.md:110` still reads `251 passed in 0.60s` and `README.md:125` still reads `251 passing, offline, <1s` — S6 grew the suite and the README was not updated. This task corrects both to the real, measured number (306 plus this sprint's six corpus tests plus Task 2's two guards). The install snippet (`README.md:128-142`) is verified against the plugin SK-060 actually published.

**Executor skills:** `superpowers:writing-skills`.

- [ ] **Step 1: Confirm the finding-first framing is correct and current**

Read `README.md:14-22`. Confirm it leads with the escalation finding and that `README.md:18` states the corrected runtime (loud error, not silent empty answer) — do **not** re-introduce the walked-back "silently receive an empty answer" claim as present-tense fact. If both hold, no edit here; if any phrasing drifted from the corrected runtime, fix it to match `README.md:18`.

- [ ] **Step 2: Refresh the stale test count**

Run `uv run pytest -q` and read the reported total (e.g. `314 passed in 0.5s` — 306 baseline + 6 corpus + 2 guards; use the **actual** printed number). Then update both occurrences in `README.md`:
- `README.md:110`: replace `251 passed in 0.60s` with `<N> passed in <observed>s`.
- `README.md:125`: replace `251 passing, offline, <1s` with `<N> passing, offline, <1s`.

Use the single number `uv run pytest -q` actually prints — do not guess. (The `[ 28%]` progress lines at `README.md:106-109` are illustrative and need no edit.)

- [ ] **Step 3: Verify the install snippet against the published plugin**

With SK-060's plugin published (Task 4), confirm the quickstart block at `README.md:128-142` is literally true: `claude plugin marketplace add bessavagner/supskill` then `claude plugin install supskill@supskill` is exactly what a cold reader runs, and the dependency table (`README.md:137-141`) names the deps that actually resolved. Fix any drift; do not oversell (`README.md:154` — "Alpha, and honest about it").

- [ ] **Step 4: Run the suite and commit**

Run: `uv run pytest && uv run ruff check`
Expected: green (README is prose; no test asserts its count, so the edit is safe).

```bash
git add README.md
git commit -m "docs: README quickstart verified against the published plugin; test count refreshed to the real suite size (SK-062)"
```

---

### Task 6: The build-in-public writeup (SK-062) — operator-run, priority C

**Files:**
- No in-tree file. The writeup ships to the external `bessavagner-page`; it is outside this repo and this plan cannot cite or verify it in-tree. Closes on operator-run evidence (a published page).

**Interfaces:**
- Consumes: the corrected finding (`README.md:18`), the composed-skills credit (the dependency table `README.md:137-141`), and the design record (`docs/.ai/reports/2026-07-12-supskill-design-decisions.md`, linked from `README.md:183`).
- Produces: a published build-in-public writeup. Nothing in this repo depends on it — hence priority C, the deferrable half if Gate 1 trims scope.

**Context.** The backlog's row gives the lede verbatim (`docs/plans/sprints/backlog-01/backlog.md:155`), but its second clause — "and in headless they silently receive an empty answer" — is now stale, walked back in commit `2bd2ff5`. The load-bearing half survives (a delegated agent has no channel to escalate); the "silent empty answer" detail is the historical `#50728` report, not the current behaviour. Shipping the walked-back claim in public would undo `2bd2ff5`.

**Executor skills:** `superpowers:writing-skills`, `humanizer`.

- [ ] **Step 1: Draft the writeup, lede-first**

Lead with the escalation finding phrased to match the corrected runtime (`README.md:18`): a delegated agent has no channel to escalate a decision — stated **without** the walked-back "silent empty answer" as present-tense fact. If the `#50728` history is mentioned, frame it as the historical report on the Python Agent SDK path, not current CLI/subagent behaviour, exactly as `README.md:18` does.

- [ ] **Step 2: Credit the composition and link the record**

Credit the composed skills (`superpowers` → `writing-plans`/`subagent-driven-development`; `pm-execution` → `sprint-plan`; and `skill-creator` for the eval), consistent with invariant 1, and link the design record (`docs/.ai/reports/2026-07-12-supskill-design-decisions.md`). Do not oversell the alpha.

- [ ] **Step 3: Publish to `bessavagner-page` and record the URL**

Publish the writeup to the external `bessavagner-page`. Record the published URL for Task 7's demo log. **This is the deferrable half**: if Gate 1 trimmed scope, the writeup defers and the README (Task 5, which the plugin ships with) does not. No commit in this repo — the artifact is external.

---

### Task 7: The sprint demo checklist (process)

**Files:**
- Create: `.superpowers/sdd/s7/demo-checklist.md` (sprint scratch — gitignored by `.gitignore` `.superpowers/`; no commit)

**Interfaces:**
- Consumes: everything — the published plugin (Task 4), the corpus and runbook (Tasks 1, 3), real tokens, and a clean environment.
- Produces: the script the operator runs. **The sprint does not close on offline green.** The offline suite proves only that the corpus is well-formed and the manifest guards hold. It cannot prove that install actually resolves the cross-marketplace deps from a clean environment, that the eval loop actually produces a defensible hit rate for the shipped description, or that the README + writeup actually lead with the finding for a cold reader. Only the demo can — the same honest-scope shape S5 and S6 named one and two stages down the loop.

- [ ] **Step 1: Write the demo checklist**

Create `.superpowers/sdd/s7/demo-checklist.md`:

```markdown
# S7 demo — packaging & distribution in anger (operator-run, real tokens)

Run from a CLEAN environment (not this checkout) except where a step says
otherwise. Expected outcomes are written before running; any mismatch fails the
demo.

- [ ] 1. **Clean-environment install (SK-060).** From a directory that is not
      this checkout: `claude plugin marketplace add bessavagner/supskill` then
      `claude plugin install supskill@supskill`. Verify: it installs under the
      committed slug, no rename, and `/supskill` becomes available.
- [ ] 2. **Cross-marketplace resolution (SK-060).** Confirm `superpowers`
      (claude-plugins-official) and `pm-execution` (pm-skills) actually resolved
      at install, not merely appear in the manifest. This is the fact
      README.md:142 only ever asserted by a test — walk it for real.
- [ ] 3. **Nothing touched .supskill/ (SK-060).** Confirm the install created no
      `.supskill/` and needed no `supskill-state` verb.
- [ ] 4. **The eval loop runs (SK-061).** Follow evals/README.md: set a bounded
      token budget and record it first, then run skill-creator's run_eval.py
      against evals/description-corpus.json and skills/supskill. Read the hit
      rate. Record it as a REAL trigger rate for a command-registered copy of
      the description - a proxy for auto-invoke, not a prediction of it, and NOT
      a reason to flip disable-model-invocation (that stays a separate call).
- [ ] 5. **The description discriminates (SK-061).** Spot-check: do the
      should-not-trigger near-misses (read-only sprint questions, other-repo
      tooling, "sprint" without wanting to run one) actually stay silent, and do
      the start/resume prompts actually fire? Note any category that misbehaves.
- [ ] 6. **README is true, not aspirational (SK-062).** Read README's quickstart
      as a cold reader: the install snippet is exactly what you ran in step 1,
      the finding leads (README.md:14-22), and the test count matches
      `uv run pytest -q`. The "silent empty answer" claim is NOT present-tense.
- [ ] 7. **The writeup leads with the finding (SK-062).** Open the published
      bessavagner-page writeup: the escalation finding is the lede, phrased to
      match the corrected runtime (no walked-back "silent empty answer" as
      fact), the composed skills are credited, and the design record is linked.
- [ ] 8. Record below, verbatim: pass/fail per step, the eval hit rate and the
      token spend, whether cross-marketplace resolution actually worked from a
      clean environment, and whether the writeup's lede matched the corrected
      runtime. Steps 1-2 and 4 are the ones that decide whether E7 is real.
```

- [ ] **Step 2: Hand it to the operator**

Report: the demo checklist is at `.superpowers/sdd/s7/demo-checklist.md`; it is the exit criterion for SK-060/061/062's operator-provable acceptance; the sprint stays open until the operator runs it. No commit — the scratch dir is gitignored by design.

---

### Task 8: Apply the S7 backlog deltas and flip the E7 status (process)

**Files:**
- Modify: `docs/plans/sprints/backlog-01/backlog.md` (SK-060/061/062 status; Data point #7)
- Modify: `README.md` (E7 status-table row, `README.md:164`)

**Interfaces:**
- Consumes: nothing from other tasks (docs-only; the operator's acceptance of the demo is what authorizes marking the rows shipped — the same "once the operator accepts" clause S6's own backlog task named).
- Produces: a backlog and status table that record what S7 shipped. Unlike every prior sprint, **there is no re-point**: S7's DoR grew 0 points (the sprint doc's own finding — E7's stories are mostly not-Python and not-offline, so the pass found corrections, not missing plumbing). So this task only marks status and records the data point; the E7 header `(9 pts)` (`docs/plans/sprints/backlog-01/backlog.md:149`) and the `**Total: 136 pts.**` line (`docs/plans/sprints/backlog-01/backlog.md:73`) are unchanged.

- [ ] **Step 1: Mark the three E7 rows shipped**

In `docs/plans/sprints/backlog-01/backlog.md`, change the Status cell from `☐` to `☑` on each of SK-060, SK-061, SK-062 (`docs/plans/sprints/backlog-01/backlog.md:153-155`). Story text and points are unchanged — S7's DoR grew no points.

- [ ] **Step 2: Flip the E7 status row in the README table**

In `README.md`, change the E7 row (`README.md:164`) from `| **E7** | Packaging & distribution | ⬜ backlog |` to `| **E7** | Packaging & distribution | ✅ shipped |`. Leave E8's row (`README.md:165`) as `⬜ backlog`.

- [ ] **Step 3: Record Data point #7**

Append after the "Data point #6" paragraph (`docs/plans/sprints/backlog-01/backlog.md:226`):

```markdown
**Data point #7 (S7 DoR, 2026-07-15):** for the first time in this backlog,
refinement against live source grew scope by **0 pts**. E7's stories are mostly
not-Python and mostly not-offline-provable, so the sharpest things the pass
found were not missing plumbing to build but claims the live world contradicts:
a repo already public, an "offline" eval whose named mechanism (`skill-creator`)
runs live, and a `v0.1.0` tag that resolves nothing at install. Correcting a
claim is not adding scope — the honest delta is 0 points and six corrections.
The gate still earned its keep: the corrections kept the plan from re-doing done
work, mislabelling a live spend as offline, or gating install on a tag. (Report
§7.2 — the refinement earns the gate whether it grows points or only fixes them.)
```

- [ ] **Step 4: Verify and commit**

Run:
```bash
grep -n "^| SK-06[012] .*☑" docs/plans/sprints/backlog-01/backlog.md   # expect three rows
grep -n "E7.*shipped" README.md                                         # expect the flipped row
uv run pytest && uv run ruff check
```
Expected: three shipped E7 rows; the README E7 row reads shipped; suite green.

```bash
git add docs/plans/sprints/backlog-01/backlog.md README.md
git commit -m "docs: mark E7 shipped (SK-060/061/062) and record Data point #7 - the first 0-point DoR"
```

---

## Self-Review

**1. Spec coverage.** Every story in the sprint doc is named by at least one task heading:
- **SK-060** — Task 2 (version-parity guard), Task 4 (publish + tag + clean install).
- **SK-061** — Task 1 (corpus + offline test), Task 2 (skill-creator exclusion guard), Task 3 (composition runbook).
- **SK-062** — Task 5 (README finalization), Task 6 (external writeup).
- **process** — Task 7 (demo checklist), Task 8 (backlog deltas + README status).

Every SK-060/061/062 accept bullet maps to a task (see the mapping table below). The two `Deliberately NOT in scope` items — flipping `disable-model-invocation` and pinning dependency versions — are held out: the runbook (Task 3) states the flag stays untouched, and the Global Constraints + Task 2 guard forbid version pins.

**2. Placeholder scan.** No `TBD`/`TODO`/"add error handling"/"similar to Task N". The one deliberately operator-filled value is the measured test count in Task 5, which is a *command to read a real number*, not a placeholder; and the eval hit rate / token spend in Task 7, which are operator-run outputs by design.

**3. Type consistency.** The corpus schema `{query, should_trigger, category}` is defined in Task 1 and consumed unchanged by Task 3's runbook and Task 7's demo. `skill-creator`'s consumer reads only `query`/`should_trigger` (verified against the installed `run_eval.py`); the extra `category` key is inert to it. The two Task 2 guards reuse `DISPATCHED_SKILL_PLUGINS`, `_declared_dependencies`, `MANIFEST`, `REPO_ROOT` exactly as the existing module names them.

## Exit criteria mapping (sprint doc → plan)

| Sprint exit criterion | Where it lands |
|---|---|
| SK-060: `marketplace add` + `install supskill@supskill` succeeds from a clean environment; slug ships as committed, no rename | Task 4 (steps 3), Task 7 (demo step 1) |
| SK-060: `superpowers` + `pm-execution` resolve across marketplaces at install time | Task 4 (step 3), Task 7 (demo step 2) |
| SK-060: a `v0.1.0` release is tagged as hygiene, not gated on for install; no version pins added | Task 4 (step 2), Task 2 (version-parity guard; the unversioned guard stays green) |
| SK-060: nothing about the publish touches `.supskill/` or adds a `supskill-state` verb | Task 4 (step 4), Task 7 (demo step 3) |
| SK-061: the corpus is authored with should-not-trigger near-misses (read-only, other-repo, names-not-run) | Task 1 |
| SK-061: the eval is `skill-creator`'s real `run_eval.py`/`run_loop.py`, not a bespoke proxy; a bounded token budget is set and recorded; operator-gated | Task 3 (runbook), Task 7 (demo step 4) |
| SK-061: `disable-model-invocation: true` untouched; skill-creator's command path is separate (finding 3); the report frames the number as a real trigger rate for a command-registered copy, not a live-auto-invoke prediction | Task 3 (runbook prose), Task 7 (demo step 4) |
| SK-061: `skill-creator` NOT in `plugin.json` dependencies or `DISPATCHED_SKILL_PLUGINS` | Task 2 (skill-creator exclusion guard) |
| SK-062: README leads with the finding; install snippet verified against the published plugin | Task 5 (steps 1, 3) |
| SK-062: the writeup leads with the escalation finding matched to the corrected runtime, credits the composed skills, links the record, does not re-introduce the walked-back claim | Task 6 |
| SK-062: priority C — the external writeup is the deferrable half; the README is not | Task 6 (step 3 note); Task 5 is the non-deferrable half |
| The offline suite still passes for SK-061's corpus; SK-060 and SK-062 close on operator-run evidence | Task 1 (offline corpus test); Tasks 4/6/7 (operator evidence) |
| The sprint demo (operator-run): clean-environment install, deps resolved, `/supskill` available, eval loop run and hit rate read, README + writeup published with the finding as the lede | Task 7 — **operator-run; the sprint does not close on offline green alone** |
| Backlog deltas applied | Task 8 |

## Skills for executors

Standing skills apply (author↔review separation, verify-before-claim, no self-approval, TDD, `karpathy-guidelines`, no AI attribution in commits). Domain additions, matching the sprint doc's own shape:

- **Task 1 (the corpus + its test)** — `fullstack-dev-skills:python-pro` + `superpowers:test-driven-development`. The corpus test stays pure offline: no LLM, no subagent, no network. Read `tests/test_plugin_manifest.py` for the module-level `REPO_ROOT` pattern before writing the new test file.
- **Task 2 (the two guards)** — `fullstack-dev-skills:python-pro`. These are regression guards of already-true invariants (like the S6 plan's structural-regression tests); do not manufacture a red bar.
- **Task 3 (the runbook)** — `superpowers:writing-skills`. Read the installed `skill-creator` `run_eval.py`/`run_loop.py` in full before writing the invocation; the flag-separation and budget prose is load-bearing (DoR findings 3 and 6).
- **Task 4 (the publish)** — operator-run; confirm each hard-to-reverse step (tag push, release, install) with the operator. No self-approval of the publish.
- **Task 5 (README)** — `superpowers:writing-skills`. Confirm the corrected-runtime phrasing at `README.md:18` before touching the finding section.
- **Task 6 (the writeup)** — `superpowers:writing-skills` + `humanizer`. External artifact; leads with the corrected finding.
- **Tasks 7 / 8** — `oh-my-claudecode:verifier` for the demo hand-off and the backlog-delta verification.

## Risks & mitigations

| Risk | Owner | Trigger / signal | Mitigation |
|------|-------|------------------|------------|
| **The eval is mislabelled — a live `claude -p` spend sold as "offline", or an offline number sold as a live-triggering prediction** (DoR finding 2) | operator / executor (Task 3) | the report claims the hit rate is offline, or that it predicts live auto-invocation | Gate 1 picked option (b): the corpus is the only offline artifact (Task 1); the scorer is `skill-creator`'s real loop, operator-run with a recorded budget (Task 3). The runbook and the demo both state the number is a real trigger rate for a command-registered copy — a proxy, not a prediction |
| **`skill-creator` gets "helpfully" declared as a dependency** (DoR finding 6) | executor (Task 2) | it lands in `plugin.json` deps or `DISPATCHED_SKILL_PLUGINS`, pulling a third cross-marketplace dep into install | Task 2's `test_skill_creator_is_not_a_runtime_dependency` guard fails the suite if either happens; the runbook lives outside `skills/` so the dispatch-scan never reads it |
| **A `v0.1.0` tag is treated as what makes install work, or version pins get added to "match" it** (DoR finding 4) | executor (Task 4) | the publish is gated on the tag, or a dependency gains a `version` (which disables supskill) | Task 4 resolves install via `source: "./"` at the default branch and treats the tag as a GitHub marker only; the live guard `tests/test_plugin_manifest.py:126-136` fails the suite on any version pin |
| **The writeup ships the walked-back "silent empty answer" claim as present fact** (`README.md:18`, commit `2bd2ff5`) | operator (Task 6) | the lede re-introduces what the project already corrected | Task 6 keeps the load-bearing half (no escalation channel) and frames the "silent empty answer" as the historical `#50728` report; the demo (Task 7 step 7) checks the lede matches the corrected runtime |
| **Cross-marketplace resolution has only ever been asserted by a test, never walked against a published plugin** (`README.md:142`) | executor (Task 4) | `install supskill@supskill` fails to resolve `superpowers` or `pm-execution` from a clean environment | Task 4 step 3 and the demo (Task 7 step 2) exercise the real install and confirm both deps fetch, not merely that `allowCrossMarketplaceDependenciesOn` is present |
| **The immutable slug is decided by omission** — the manifests already commit `supskill`, but the backlog row asks to "decide the name before this ships" | operator (Task 4) | a rename is proposed after publish, when the slug can no longer change | Treated as already-decided on disk (`plugin.json:2`, `.claude-plugin/marketplace.json:11`, `README.md:132`) and shipped as-is; after Task 4 publishes, it is permanent |
| **A green suite is read as "E7 done"** — most of E7 is not offline-provable | operator / reviewer | the sprint closes on offline green while the publish and writeup are the actual deliverables | Stated in the Architecture and Task 7: SK-060 and SK-062 close on operator-run evidence (a real clean-environment install, a published writeup), not on tests |
| **The README's test count is already stale (251 vs 306) and will drift again** | executor (Task 5) | the README quotes a count no `uv run pytest -q` ever prints | Task 5 reads the real number from `uv run pytest -q` and sets both occurrences; the count is prose (no test asserts it), so it must be refreshed by hand whenever the suite grows |

## Exit criteria

- [ ] **Task 1 (SK-061 offline slice):** `evals/description-corpus.json` exists with both should-trigger and should-not-trigger entries covering start/resume and the three near-miss buckets; `tests/test_eval_corpus.py` validates its shape purely offline; the full suite stays green.
- [ ] **Task 2 (SK-060, SK-061 guards):** `plugin.json` version equals `pyproject.toml`'s; `skill-creator` is absent from `DISPATCHED_SKILL_PLUGINS` and the declared dependencies — both guarded and green.
- [ ] **Task 3 (SK-061):** `evals/README.md` documents `skill-creator`'s real `run_eval.py`/`run_loop.py` invocation, a token budget, the disable-model-invocation separation (finding 3), and that this is operator-run and out of the offline suite; it lives outside `skills/`.
- [ ] **Task 4 (SK-060):** a `v0.1.0` release is tagged; `claude plugin marketplace add bessavagner/supskill` then `install supskill@supskill` succeeds from a clean environment with `superpowers` and `pm-execution` resolving; the slug ships as committed; the publish touches no `.supskill/` and adds no verb or version pin. **Operator-run.**
- [ ] **Task 5 (SK-062):** README leads with the finding at the corrected runtime, its test count matches `uv run pytest -q`, and its install snippet is verified against the published plugin.
- [ ] **Task 6 (SK-062):** the `bessavagner-page` writeup leads with the escalation finding matched to `README.md:18`, credits the composed skills, links the design record, and does not re-introduce the walked-back claim. **Operator-run; deferrable (priority C).**
- [ ] **Task 7 (process):** the operator runs `.superpowers/sdd/s7/demo-checklist.md` — clean-environment install, resolved cross-marketplace deps, `/supskill` available, the eval loop run and its hit rate read, README + writeup published with the finding as the lede.
- [ ] **Task 8 (process):** SK-060/061/062 marked shipped, the README E7 row flipped to shipped, Data point #7 recorded (the first 0-point DoR); E7's `(9 pts)` header and the `136 pts` total unchanged.

> **Honest scope note:** Task 1's corpus test is this sprint's *entire* offline-provable core — a single well-formed artifact, a fraction of 9 points. Everything the epic is actually named for is a loop the test suite cannot execute: whether install resolves the cross-marketplace deps from a clean environment, whether the shipped description actually discriminates should-trigger from should-not-trigger under real tokens, and whether the README and writeup actually land the finding for a cold reader. All three are visible only in Task 7's demo. This is E5's and E6's honest-scope problem at the packaging seam: a green suite here proves the corpus is well-formed and the manifest guards hold, not that supskill is installable, discoverable, or legible — which is the whole of E7.
