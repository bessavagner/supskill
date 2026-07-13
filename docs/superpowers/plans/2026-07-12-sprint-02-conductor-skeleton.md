# Sprint 02 — Conductor Skill + Plugin Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the repo into a valid Claude Code plugin with a `/supskill run <sprint-id>` conductor skill that init's-or-resumes strictly from `.supskill/state.json` — invoke it after `/clear` and it lands on the right stage from disk alone.

**Architecture:** The product splits in two (design decision D2): the `supskill-state` CLI (already built in Sprint 01) is the only enforcement and the only mutator of `state.json`; the SKILL.md is pure conductor UX — a checklist that reads state via `show --json` and dispatches on `stage`. This sprint grows the CLI's *read* side (`show` gains `artifacts`, `backlog`, `--json`) and writes the skill prose. No stage is implemented — all five dispatch entries are honest stubs that name the epic that will implement them and stop.

**Tech Stack:** Python ≥3.11 stdlib only (zero runtime deps), pytest + ruff + pyyaml as dev deps, managed with `uv`. Claude Code plugin layout (`.claude-plugin/plugin.json`, `skills/`, `agents/`, `scripts/`).

## Global Constraints

Copied from the sprint spec (`docs/plans/sprints/backlog-01/sprint-02-conductor-skeleton.md`) and the standing project rules. Every task's requirements implicitly include this section.

- **Zero runtime dependencies:** `pyproject.toml` `[project] dependencies = []` — enforced by `tests/test_scaffold.py::test_zero_runtime_dependencies`. New packages go in `[dependency-groups] dev` only.
- **The suite stays pure offline and fast:** no LLM calls, no subagents, no network anywhere in `tests/`.
- **Invariant 3, now with a prose surface:** the script is the only mutator of `state.json`. No line of SKILL.md may instruct editing `state.json` (or anything under `.supskill/`) by hand; every mutation it choreographs must be a `supskill-state` call. This is a named reviewer check.
- **The conductor never passes `--archive`.** It may *name* `supskill-state init <id> --archive` to the operator and must then stop. This is structural: the flag appears in SKILL.md only inside the refusal message.
- **Plugin name is `supskill`** (working title — the slug freeze is SK-060's decision; renaming is free until first publish).
- **Skill frontmatter hard limits** (contexts/02 §1): `name` ≤64 chars, lowercase letters/numbers/hyphens only, must not contain `anthropic` or `claude`; `description` non-empty, ≤1024 chars, no XML tags, third person; combined `description` + `when_to_use` ≤1,536 chars; body ≤500 lines; reference files at most one hop from SKILL.md.
- **The state CLI is always invoked as `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state`** (only `bin/` joins PATH, `scripts/` does not), **from the target repo's root** (`.supskill/` resolves from cwd — `scripts/supskill_state/store.py:26`). Nothing ever persists under the plugin root (wiped on update).
- **Layout stays where S1 put it:** `scripts/supskill_state/` package + `scripts/supskill-state` shim, `pyproject.toml` `pythonpath = ["scripts"]`. Do not move them.
- **Style:** ruff `line-length = 120`, rules `E,F,I,B,UP`. Run `uv run ruff check` before every commit.
- **Commits:** one per task minimum, TDD evidence first (failing test run before implementation). **No AI attribution of any kind in commit messages** — no `Co-Authored-By`, no "Generated with" lines.
- **Commands:** run tests as `uv run pytest <path> -v`, lint as `uv run ruff check`.

## File Structure

| Path | Task | Responsibility |
|---|---|---|
| `.claude-plugin/plugin.json` | 1 (create) | Plugin manifest — the only file allowed in `.claude-plugin/` |
| `skills/supskill/SKILL.md` | 1 (placeholder) → 2 (frontmatter) → 5 (body) | The conductor: frontmatter = discovery contract, body = run checklist + dispatch table |
| `skills/supskill/references/invocation-model.md` | 2 (create) | Records the user-invoked-only decision and its E7 tension (one hop from SKILL.md) |
| `agents/.gitkeep` | 1 (create) | Reserves `agents/` at plugin root for E3's stage agents |
| `tests/test_plugin_manifest.py` | 1 (create) | Offline invariants a `claude plugin validate` run can't be assumed for in CI |
| `tests/test_skill_frontmatter.py` | 2 (create) | The frontmatter lint — fails loudly on the silent malformed-YAML mode |
| `scripts/supskill_state/commands.py` | 3 (modify) | `render_show` grows `backlog` + `artifacts`; new `render_show_json` |
| `scripts/supskill_state/cli.py` | 3 (modify) | `show --json` flag |
| `tests/test_show.py` | 3 (modify) | New show fields + JSON round-trip tests |
| `tests/test_run_matrix.py` | 4 (create) | The init-or-resume-or-refuse matrix, asserted per CLI-reachable cell |
| `.superpowers/sdd/s2/demo-checklist.md` | 6 (create, gitignored) | Operator's invariant-5 demo script — the sprint's exit criterion |
| `docs/plans/sprints/backlog-01/backlog.md` | 7 (modify) | The six DoR backlog deltas |

Task order: 1 → 2 and 1 → 3 are independent of each other (may run in parallel); 4 needs 3 (`show --json`); 5 needs 2, 3, 4 (the body documents the real CLI, not a guess); 6 needs 5; 7 is docs-only and independent.

---

### Task 1: Plugin skeleton (SK-010)

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `skills/supskill/SKILL.md` (placeholder — Tasks 2 and 5 fill it)
- Create: `agents/.gitkeep`
- Test: `tests/test_plugin_manifest.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: the plugin layout every later task sits in — `skills/supskill/SKILL.md` (Tasks 2, 5 edit this exact path), `.claude-plugin/plugin.json` with `name: "supskill"`.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`. If any plugin.json idiom seems off, `context7` for current docs — but `docs/.ai/reports/contexts/02-skill-and-plugin-authoring.md` is the local authority where they disagree with memory.

- [ ] **Step 1: Write the failing test**

Create `tests/test_plugin_manifest.py`:

```python
"""SK-010: the repo is a valid Claude Code plugin - offline invariants.

`claude plugin validate --strict` is the authority; this suite pins the
invariants a validator run cannot be assumed for (CI has no claude binary):
the manifest parses, the name is a legal slug, and components live at the
plugin root, never inside .claude-plugin/ (contexts/02 SS3).
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / ".claude-plugin" / "plugin.json"

KEBAB_CASE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def test_manifest_parses_as_json():
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)


def test_plugin_name_is_a_legal_slug():
    name = json.loads(MANIFEST.read_text(encoding="utf-8"))["name"]
    assert name == "supskill"  # working title; the slug freeze is SK-060's decision
    assert len(name) <= 64
    assert KEBAB_CASE.fullmatch(name)
    assert "claude" not in name and "anthropic" not in name


def test_manifest_carries_version_description_author():
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert raw["version"]
    assert raw["description"]
    assert raw["author"]["name"]


def test_nothing_but_the_manifest_lives_in_dot_claude_plugin():
    entries = sorted(entry.name for entry in (REPO_ROOT / ".claude-plugin").iterdir())
    assert entries == ["plugin.json"]


def test_components_live_at_plugin_root():
    assert (REPO_ROOT / "skills" / "supskill" / "SKILL.md").is_file()
    assert (REPO_ROOT / "agents").is_dir()  # reserved for E3's stage agents
    assert (REPO_ROOT / "scripts" / "supskill-state").is_file()  # untouched where S1 put it
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_plugin_manifest.py -v`
Expected: FAIL — `FileNotFoundError: ... .claude-plugin/plugin.json`

- [ ] **Step 3: Create the skeleton**

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "supskill",
  "version": "0.1.0",
  "description": "Sprint conductor: drives one sprint from a markdown backlog through staged human gates, keeping all authoritative state on disk",
  "author": { "name": "Vagner Bessa" }
}
```

Create `skills/supskill/SKILL.md` (placeholder — deliberately missing the fields Task 2's lint will demand, so that lint has a real red state):

```markdown
---
name: supskill
description: Placeholder - SK-011 replaces this with real triggering conditions.
---

# supskill (placeholder)

The conductor's frontmatter lands in SK-011; the body in SK-012/SK-013.
```

Create `agents/.gitkeep` as an empty file (git cannot track an empty directory; E3's stage agents will replace it).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_plugin_manifest.py -v`
Expected: 5 passed

- [ ] **Step 5: Full suite, lint, and the real validator**

Run: `uv run pytest && uv run ruff check`
Expected: all tests pass (S1's suite untouched), no lint errors.

Run: `claude plugin validate --strict .` from the repo root.
Expected: validation passes with no errors. (If the CLI rejects that argument order, check `claude plugin validate --help` — the target is the repo root as the plugin dir with strict warnings-as-errors on. If the `claude` binary is unavailable in this environment, record that in the task report — the offline tests above cover the invariants, and the operator runs the validator as part of the Task 6 demo.)

- [ ] **Step 6: Commit**

```bash
git add .claude-plugin/plugin.json skills/supskill/SKILL.md agents/.gitkeep tests/test_plugin_manifest.py
git commit -m "feat: plugin skeleton - manifest, skills dir, reserved agents dir (SK-010)"
```

---

### Task 2: Frontmatter — triggering conditions only, linted (SK-011)

**Files:**
- Modify: `skills/supskill/SKILL.md` (frontmatter block only — leave the placeholder body; Task 5 replaces it)
- Create: `skills/supskill/references/invocation-model.md`
- Modify: `pyproject.toml` (add `pyyaml` to the dev group)
- Test: `tests/test_skill_frontmatter.py`

**Interfaces:**
- Consumes: `skills/supskill/SKILL.md` from Task 1.
- Produces: the final frontmatter (Task 5 must not change it) and a lint suite that keeps enforcing every hard limit against whatever body Task 5 writes. Exposes helper `read_frontmatter_and_body() -> tuple[dict, list[str]]` inside the test module (test-local, not exported).

**Executor skills:** Invoke `superpowers:writing-skills` **first** — it is the primary source for the description regression this story exists to avoid (a workflow-summarizing description causes agents to skip half the process). Then `superpowers:test-driven-development` for the lint.

- [ ] **Step 1: Add pyyaml to the dev dependency group**

Run: `uv add --group dev "pyyaml>=6"`
Expected: `pyproject.toml` `[dependency-groups] dev` now lists `pyyaml>=6`; `uv.lock` updated. Runtime `dependencies` stays `[]` (the scaffold test guards this).

- [ ] **Step 2: Write the failing lint test**

Create `tests/test_skill_frontmatter.py`:

```python
"""SK-011: the skill's frontmatter obeys every hard limit, loudly.

Malformed frontmatter YAML still loads the skill but with NO description, so
it never auto-triggers and only --debug shows why (contexts/02 SS1). This
suite is the CI step that makes that silent failure mode loud, and pins the
hard numbers: name <=64 kebab-case without reserved words, description
non-empty <=1024, combined description + when_to_use <=1536, body <=500 lines.

The no-workflow-summary property is reviewer judgment, not regex (sprint risk
table says so honestly); WORKFLOW_TOKENS below is only a tripwire for the
obvious regression - a stage or gate name appearing in the description.
"""

import re
from pathlib import Path

import pytest
import yaml

SKILL = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "SKILL.md"

KEBAB_CASE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
XML_TAG = re.compile(r"<[^>]+>")
WORKFLOW_TOKENS = re.compile(r"\b(SCOPE|REFINE|PLAN|EXECUTE|REVIEW|G1|G2|G3)\b")


def read_frontmatter_and_body() -> tuple[dict, list[str]]:
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "SKILL.md must open with a frontmatter block"
    closing = text.index("\n---\n", 4)
    parsed = yaml.safe_load(text[4:closing])  # yaml.YAMLError here IS the loud failure
    assert isinstance(parsed, dict), "frontmatter must parse as a YAML mapping"
    body = text[closing + len("\n---\n"):].splitlines()
    return parsed, body


@pytest.fixture(scope="module")
def frontmatter() -> dict:
    return read_frontmatter_and_body()[0]


def test_name_is_explicit_and_legal(frontmatter):
    name = frontmatter["name"]
    assert name == "supskill"
    assert len(name) <= 64
    assert KEBAB_CASE.fullmatch(name)
    assert "claude" not in name and "anthropic" not in name
    assert not XML_TAG.search(name)


def test_description_states_triggering_conditions_within_limits(frontmatter):
    description = frontmatter["description"]
    assert isinstance(description, str) and description.strip()
    assert len(description) <= 1024
    assert not XML_TAG.search(description)
    assert not WORKFLOW_TOKENS.search(description), (
        "a stage or gate name in the description is the documented regression's tripwire"
    )


def test_combined_trigger_text_fits_the_rendered_cap(frontmatter):
    combined = frontmatter["description"] + frontmatter.get("when_to_use", "")
    assert len(combined) <= 1536


def test_conductor_is_user_invoked_only(frontmatter):
    # side-effecting skill: spawns subagents, spends tokens, mutates the repo
    assert frontmatter["disable-model-invocation"] is True


def test_argument_hint_names_the_verb(frontmatter):
    assert frontmatter["argument-hint"] == "run <sprint-id>"


def test_body_stays_under_500_lines():
    _, body = read_frontmatter_and_body()
    assert len(body) <= 500


def test_invocation_model_reference_is_one_hop_from_the_skill():
    reference = SKILL.parent / "references" / "invocation-model.md"
    assert reference.is_file()
    assert "references/invocation-model.md" in SKILL.read_text(encoding="utf-8")
```

- [ ] **Step 3: Run it to verify it fails**

Run: `uv run pytest tests/test_skill_frontmatter.py -v`
Expected: FAIL — `KeyError: 'disable-model-invocation'` and `KeyError: 'argument-hint'` against the Task 1 placeholder, plus `test_invocation_model_reference_is_one_hop_from_the_skill` failing on the missing reference file.

- [ ] **Step 4: Write the real frontmatter**

Replace the frontmatter block in `skills/supskill/SKILL.md` (keep the placeholder body below it for now):

```markdown
---
name: supskill
description: Drives one development sprint from a markdown backlog, and resumes an in-progress sprint from its on-disk state. Use when the operator wants to start or return to a supskill-managed sprint in the current repository.
argument-hint: run <sprint-id>
disable-model-invocation: true
---

# supskill (placeholder)

The conductor body lands in SK-012/SK-013.
See [references/invocation-model.md](references/invocation-model.md) for why
this skill is user-invoked only.
```

Note what the description does and does not say: it names the triggering conditions (driving a sprint from a markdown backlog; returning to one in progress) in third person, and contains **no stage list, no gate list, no workflow summary** — that omission is the entire point of SK-011.

- [ ] **Step 5: Write the invocation-model reference**

Create `skills/supskill/references/invocation-model.md`:

```markdown
# Invocation model — decided at S2 (SK-011)

**Decision:** v1 of the `supskill` skill is user-invoked only —
`disable-model-invocation: true` in the SKILL.md frontmatter.

**Why.** The conductor is side-effecting: it spawns subagents, spends tokens,
and mutates the operator's repository (`.supskill/`, sprint branches, recorded
artifacts). contexts/02's implication #2 applies directly: skills with side
effects the user should control the timing of do not belong on default
auto-invoke. The operator decides when a sprint starts or resumes; the model
does not.

**The flagged tension (E7 revisits).** SK-061's should-trigger /
should-not-trigger eval loop mostly exercises auto-invocation — the very path
this flag disables. Until E7, those evals would measure a hypothetical. E7
either relaxes the flag with eval evidence in hand, or re-scopes SK-061 to
user-invocation UX (argument parsing, wrong-repo refusals). Recorded here so
E7 inherits the tension explicitly instead of rediscovering it.
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_skill_frontmatter.py -v`
Expected: 7 passed

- [ ] **Step 7: Full suite, lint, commit**

Run: `uv run pytest && uv run ruff check`
Expected: all green.

```bash
git add skills/supskill/SKILL.md skills/supskill/references/invocation-model.md tests/test_skill_frontmatter.py pyproject.toml uv.lock
git commit -m "feat: skill frontmatter states triggering conditions only, linted (SK-011)"
```

---

### Task 3: `show` grows the resume read-contract (SK-012, CLI half)

**Files:**
- Modify: `scripts/supskill_state/commands.py:102-135` (`render_show`; new `render_show_json`)
- Modify: `scripts/supskill_state/cli.py:61-68` (`show --json`)
- Test: `tests/test_show.py`

**Interfaces:**
- Consumes: `store.load_state`, `model.state_to_dict` (both exist — `scripts/supskill_state/model.py:248`), `commands.record_artifact`.
- Produces: `render_show_json(root: Path | None = None) -> str` in `commands.py`; CLI surface `supskill-state show --json` printing the full state as JSON. `render_show` text now contains a `backlog:` line and an `artifacts:` section (unset values render as `-`). Tasks 4 and 5 rely on `show --json` exactly as built here.

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`. The suite stays pure offline.

- [ ] **Step 1: Write the failing tests**

In `tests/test_show.py`, change the import block at the top to:

```python
import json

from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_artifact, render_show, render_show_json
from supskill_state.model import Blocker, Task, TaskStatus
from supskill_state.store import append_jsonl, dump_state, gates_path, load_state, state_path
```

Append these tests at the end of the file:

```python
def test_show_prints_backlog_and_recorded_artifacts(tmp_path):
    init_sprint("s1", backlog="docs/backlog.md", root=tmp_path)
    (tmp_path / "sprint-doc.md").write_text("spec\n", encoding="utf-8")
    record_artifact("sprint_doc", "sprint-doc.md", root=tmp_path)
    output = render_show(tmp_path)
    assert "backlog: docs/backlog.md" in output
    assert "artifacts:" in output
    assert "sprint_doc: sprint-doc.md" in output
    assert "dev_plan: -" in output  # unset renders as a dash, same idiom as gates


def test_show_marks_missing_backlog_with_a_dash(tmp_path):
    init_sprint("s1", root=tmp_path)
    output = render_show(tmp_path)
    assert "backlog: -" in output
    assert "sprint_doc: -" in output


def test_show_json_round_trips_against_the_state_file(tmp_path):
    _state_with_activity(tmp_path)
    output = render_show_json(tmp_path)
    assert json.loads(output) == json.loads(state_path(tmp_path).read_text(encoding="utf-8"))


def test_cli_show_json(tmp_path, monkeypatch, capsys):
    _state_with_activity(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["show", "--json"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["stage"] == "SCOPE"
    assert parsed["sprint"]["id"] == "s1"
    assert set(parsed["artifacts"]) == {"sprint_doc", "dev_plan"}
    assert parsed["backlog"] is None
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_show.py -v`
Expected: the 4 new tests FAIL — `ImportError: cannot import name 'render_show_json'`. (Import errors fail the whole module; that is the red state.)

- [ ] **Step 3: Implement**

In `scripts/supskill_state/commands.py`, add `state_to_dict` to the model import (the block at lines 19-29 becomes):

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
    TaskStatus,
    state_to_dict,
)
```

In `render_show`, replace the `lines = [...]` construction (currently lines 108-112) with:

```python
    lines = [
        f"sprint {state.sprint.id}{slug} - stage {state.stage.value} "
        f"(entered at {state.sprint.entry.value})",
        f"backlog: {state.backlog or '-'}",
        "artifacts:",
    ]
    for key in ARTIFACT_KEYS:
        lines.append(f"  {key}: {state.artifacts[key] or '-'}")
    lines.append("gates:")
```

Add after `render_show` (before `_last_gate_responses`):

```python
def render_show_json(root: Path | None = None) -> str:
    """The resume read-contract: the full state as JSON.

    The conductor's dispatch consumes this instead of parsing state.json
    itself - the schema stays the CLI's concern, never skill prose's.
    """
    root = Path(root) if root is not None else Path.cwd()
    state = store.load_state(store.state_path(root))
    return json.dumps(state_to_dict(state), indent=2) + "\n"
```

In `scripts/supskill_state/cli.py`, replace `_add_show` and `_cmd_show` (lines 61-68) with:

```python
def _add_show(subparsers) -> None:
    sub = subparsers.add_parser("show", help="print stage, gates, task counts, open blockers")
    sub.add_argument("--json", action="store_true", help="print the full state as JSON (the resume contract)")
    sub.set_defaults(func=_cmd_show)


def _cmd_show(args) -> int:
    print(commands.render_show_json() if args.json else commands.render_show(), end="")
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_show.py -v`
Expected: all pass, including the five pre-existing show tests (the new `backlog:`/`artifacts:` lines are additive — none of the old assertions match on line positions).

- [ ] **Step 5: Full suite, lint, commit**

Run: `uv run pytest && uv run ruff check`
Expected: all green.

```bash
git add scripts/supskill_state/commands.py scripts/supskill_state/cli.py tests/test_show.py
git commit -m "feat: show grows artifacts, backlog, and --json - the resume read contract (SK-012)"
```

---

### Task 4: The init-or-resume-or-refuse matrix, asserted per cell (SK-013, CLI half)

**Files:**
- Test: `tests/test_run_matrix.py` (create)

**Interfaces:**
- Consumes: `cli.main`, `scratch.normalize_sprint_id`, `store.state_path`, and `show --json` from Task 3.
- Produces: nothing new in production code — this task pins the CLI contract each matrix cell of the conductor's prose (Task 5) relies on. If any of these tests fails, the gap is real production work, not a test bug; fix it before Task 5 documents the behavior.

**Honesty note (per the sprint's TDD exit criterion):** the underlying behavior already exists (`init` refusal at `commands.py:55-61`, `--entry` at `cli.py:34`), so most of these tests pass on first run — they are characterization tests locking the matrix, not red-green cycles. Record that in the task report instead of staging fake failures. The genuinely new assertion (`show --json` as the dispatch input) was TDD'd in Task 3.

- [ ] **Step 1: Write the matrix tests**

Create `tests/test_run_matrix.py`:

```python
"""SK-013: the init-or-resume-or-refuse matrix, one test per CLI-reachable cell.

The conductor's prose (SKILL.md) implements the matrix; this suite pins the
CLI behavior each cell relies on, against a real .supskill/ in a temp dir.
The dangerous cell is the third: init over existing state must refuse and
name --archive - the conductor inherits the refusal, never the flag.
"""

import json

import pytest

from supskill_state.cli import main
from supskill_state.scratch import normalize_sprint_id
from supskill_state.store import state_path


def test_cell_no_state_init_then_dispatch_lands_on_default_entry(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s2"]) == 0
    capsys.readouterr()
    assert main(["show", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["stage"] == "SCOPE"


@pytest.mark.parametrize("entry", ["PLAN", "EXECUTE"])
def test_cell_no_state_entry_flag_lands_dispatch_on_the_entry_stage(tmp_path, monkeypatch, capsys, entry):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s2", "--entry", entry]) == 0
    capsys.readouterr()
    assert main(["show", "--json"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["stage"] == entry
    assert state["sprint"]["entry"] == entry


def test_cell_resume_is_read_only(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s2"]) == 0
    before = state_path(tmp_path).read_bytes()
    assert main(["show", "--json"]) == 0
    assert main(["show"]) == 0
    assert state_path(tmp_path).read_bytes() == before  # resume mutates nothing


def test_same_sprint_in_any_case_normalizes_to_one_id():
    # the conductor compares the requested id with sprint.id via this rule:
    # S2 and s2 are the same sprint and must resume, not collide
    assert normalize_sprint_id("S2") == normalize_sprint_id("s2") == "s2"


def test_cell_mismatch_init_refuses_and_names_archive_without_using_it(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s2"]) == 0
    before = state_path(tmp_path).read_bytes()
    capsys.readouterr()
    assert main(["init", "s99"]) == 1
    err = capsys.readouterr().err
    assert "refused" in err and "--archive" in err
    assert state_path(tmp_path).read_bytes() == before  # nothing archived, nothing clobbered
```

- [ ] **Step 2: Run the matrix**

Run: `uv run pytest tests/test_run_matrix.py -v`
Expected: 6 passed. If any cell fails, the CLI contract the sprint spec asserts is broken — stop and fix production code before proceeding to Task 5.

- [ ] **Step 3: Full suite, lint, commit**

Run: `uv run pytest && uv run ruff check`
Expected: all green.

```bash
git add tests/test_run_matrix.py
git commit -m "test: init-or-resume-or-refuse matrix asserted per CLI cell (SK-013)"
```

---

### Task 5: The conductor body — resume checklist, dispatch table, run matrix (SK-012 + SK-013, prose half)

**Files:**
- Modify: `skills/supskill/SKILL.md` (replace the placeholder body; do **not** touch the Task 2 frontmatter)

**Interfaces:**
- Consumes: the exact CLI surface from Tasks 3-4 (`show --json`, `init <id> [--entry|--backlog|--branch|--slug]`), the frontmatter and reference file from Task 2.
- Produces: the complete v-E2 conductor. E3-E6 will replace individual dispatch-table stubs; nothing else in the body should need to move.

**Executor skills:** `superpowers:writing-skills` for the body. Degrees-of-freedom framing applies: exact CLI invocations are low-freedom (verbatim commands, "do not modify"); "report and stop" behavior is judgment prose.

**Reviewer check (named, recurring every sprint from now on):** no line of this body may instruct editing `state.json` or anything under `.supskill/` by hand — every mutation is a `supskill-state` call. Also verify: `--archive` appears only inside the refusal message; the description (frontmatter) still contains no workflow summary.

- [ ] **Step 1: Replace the placeholder body**

The body of `skills/supskill/SKILL.md` (everything after the closing `---` of the frontmatter — the frontmatter itself is Task 2's and must not change) becomes:

```markdown
# supskill — sprint conductor

Drives one sprint from a markdown backlog. This skill is the conductor's UX;
all enforcement lives in the state CLI. The conductor is disposable: its only
memory is `.supskill/state.json`, and every re-invocation reconstructs
everything from that file. Never rely on anything a previous conversation knew.

## Conventions (read first, apply always)

- The state CLI is always invoked as
  `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state` — an absolute path, never via
  `PATH` (only `bin/` joins `PATH`; `scripts/` does not).
- Always run it from the **target repo's root**: `.supskill/` resolves from the
  current working directory. Nothing is ever read from or written under the
  plugin root — it is wiped on every plugin update.
- **Never edit anything under `.supskill/` yourself.** Every mutation goes
  through a `supskill-state` verb. If the CLI refuses, report its message
  verbatim and stop — never work around a refusal.
- **Never pass `--archive`.** Archiving a half-finished sprint is an operator
  decision. The only thing this skill does with that flag is name it in the
  refusal message of matrix cell 3 below.

## Arguments

`$ARGUMENTS` is `run <sprint-id>` (e.g. `run s2`), optionally followed by
flags that are forwarded to `init` if — and only if — init runs:
`--entry SCOPE|PLAN|EXECUTE`, `--backlog <path>`, `--branch <name>`,
`--slug <slug>`.

- First token is not `run`, or there is no sprint id AND no
  `.supskill/state.json` in the current directory → print exactly this usage
  line and stop. Ask nothing — subagents cannot ask, and the conductor must
  not build a habit the stages cannot share:

      usage: /supskill run <sprint-id> [--entry SCOPE|PLAN|EXECUTE] [--backlog <path>] [--branch <name>]

- No sprint id but `.supskill/state.json` exists → treat as a resume of the
  on-disk sprint: start the run checklist at step 1 and skip the id
  comparison in step 3.

## The run checklist

Copy this checklist into your response and check items off as you go.

1. **Read state.** Run:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state show --json`
   - Refused with "no state file" → go to step 2 (matrix cell 1: init).
   - Refused with anything else (unreadable or invalid state) → report the
     CLI's message verbatim and stop. **Never re-init over a state file that
     exists but cannot be read** — that is the operator's call.
   - Success → go to step 3 (matrix cells 2 and 3).
2. **Init (no state on disk).** Run:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state init <sprint-id>`
   appending only the flags the operator gave in the invocation. Then run
   `show --json` again and continue at step 4.
3. **Compare ids.** Lowercase both the requested sprint id and `sprint.id`
   from the JSON.
   - Equal → this is a resume. Mutate nothing; continue at step 4.
   - Different → refuse and stop. The refusal must name both ids and the
     operator's way forward, verbatim:

         A different sprint is already on disk: state.json holds <sprint.id>,
         you asked for <requested-id>. A half-finished sprint is never
         archived automatically. If you mean to close it out and start fresh,
         run: ${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state init <requested-id> --archive

     Do not run that command. Stop here.
4. **Report the resume surface.** From the same `show --json` output, report:
   the sprint id and slug, current `stage`, `sprint.entry`, each gate's
   decision (`null` = pending), each recorded artifact path, the `backlog`
   path, task counts by status, and open blockers. This report must come from
   the JSON alone — consult no memory of any prior conversation.
5. **Dispatch on `stage`.** Look up `stage` in the table below and do exactly
   what it says. `stage` from `show --json` is the dispatch's only input.

## Dispatch table (v-E2: every stage is an honest stub)

| `stage` | Action |
|---|---|
| `SCOPE` | Report: "SCOPE is not implemented yet — it lands with E3 (SCOPE + REFINE + Gate 1)." Stop. |
| `REFINE` | Report: "REFINE is not implemented yet — it lands with E3 (SCOPE + REFINE + Gate 1)." Stop. |
| `PLAN` | Report: "PLAN is not implemented yet — it lands with E4 (PLAN + Gate 2)." Add: the recorded `artifacts.sprint_doc` is the spec PLAN will hand to `superpowers:writing-plans`. Stop. |
| `EXECUTE` | Report: "EXECUTE is not implemented yet — it lands with E5 (drain-then-halt)." Add: the recorded `artifacts.dev_plan` is the plan EXECUTE will drive. Stop. |
| `REVIEW` | Report: "REVIEW is not implemented yet — it lands with E6 (PAR + Gate 3)." Stop. |

A stub that init's, resumes, and honestly says "not implemented yet; here is
the state" is the correct v-E2 behavior — do not improvise a stage.

## Reference

- Why this skill is user-invoked only:
  [references/invocation-model.md](references/invocation-model.md)
```

- [ ] **Step 2: Run the lint and full suite**

Run: `uv run pytest tests/test_skill_frontmatter.py -v && uv run pytest && uv run ruff check`
Expected: all green — in particular `test_body_stays_under_500_lines` now measures the real body (~110 lines).

- [ ] **Step 3: Self-check the prose against invariant 3**

Grep the body for the forbidden pattern before handing to review:

Run: `grep -n "state.json" skills/supskill/SKILL.md`
Expected: every match is either "read via `show --json`", "never edit", or the refusal text — no line instructs writing it. Confirm `--archive` appears only inside the step-3 refusal message.

- [ ] **Step 4: Commit**

```bash
git add skills/supskill/SKILL.md
git commit -m "feat: conductor body - resume checklist, dispatch stubs, run matrix (SK-012, SK-013)"
```

---

### Task 6: The invariant-5 demo checklist (operator-run exit criterion)

**Files:**
- Create: `.superpowers/sdd/s2/demo-checklist.md` (the sprint scratch — gitignored by design; no commit)

**Interfaces:**
- Consumes: the complete conductor from Task 5, installed or loadable as a plugin.
- Produces: the script the operator runs. `seam: app-level`, `provable: operator` — **the sprint does not close on offline green alone** (F-5: prompt-shaped acceptance criteria must not be certified by the agent that wrote them).

- [ ] **Step 1: Write the demo checklist**

Create `.superpowers/sdd/s2/demo-checklist.md`:

```markdown
# S2 demo — invariant 5 in anger (operator-run)

Run in a scratch repo, NOT in supskill's own repo. Expected outcomes are
written before running; any mismatch fails the demo. <plugin-root> below is
${CLAUDE_PLUGIN_ROOT} as resolved inside the Claude Code session.

- [ ] 1. Scratch repo: `mkdir /tmp/s2-demo && cd /tmp/s2-demo && git init`,
      create any file, e.g. `echo spec > sprint-doc.md`.
- [ ] 2. `/supskill run s2` → the conductor init's, reports stage SCOPE with
      all gates pending and no artifacts, says SCOPE lands with E3, and stops.
      Verify on disk: `.supskill/state.json` exists, `"stage": "SCOPE"`.
- [ ] 3. By hand (the operator plays the missing stages):
      `<plugin-root>/scripts/supskill-state gate --id G1 --decision approved --response "demo approval"`
      `<plugin-root>/scripts/supskill-state artifact --set sprint_doc --path sprint-doc.md`
      `<plugin-root>/scripts/supskill-state advance --to REFINE`
- [ ] 4. `/clear` — the context is now genuinely empty (contexts/01 SS5).
- [ ] 5. `/supskill run s2` → the conductor reports stage REFINE, G1 approved
      with the recorded response, artifacts.sprint_doc = sprint-doc.md — having
      read nothing but disk. It must NOT re-init, and `.supskill/state.json`'s
      mtime must not change from a resume.
- [ ] 6. `/supskill run s99` → refusal that names both ids (s99 requested, s2
      on disk) and names `supskill-state init s99 --archive` WITHOUT running
      it. Verify: no `archive-1/` appeared under `.supskill/runs/`.
- [ ] 7. `claude plugin validate --strict` on the supskill repo → passes.
- [ ] 8. Record pass/fail per step below this line, verbatim.
```

- [ ] **Step 2: Hand it to the operator**

Report to the operator: the demo checklist is at `.superpowers/sdd/s2/demo-checklist.md`, it is the exit criterion for SK-012/SK-013's prompt-shaped acceptance, and the sprint stays open until they run it. No commit — the scratch dir is gitignored by design.

---

### Task 7: Apply the S2 DoR backlog deltas

**Files:**
- Modify: `docs/plans/sprints/backlog-01/backlog.md`

**Interfaces:**
- Consumes: nothing from other tasks (docs-only; may run any time after the operator accepted the sprint doc — which commissioning this plan implies).
- Produces: a backlog that matches what S2 actually committed. The six deltas are listed in the sprint doc's "Backlog deltas — proposed" section; the exact edits follow.

- [ ] **Step 1: Re-point SK-012 (3 → 4)**

In the E2 table, replace the SK-012 row:

```markdown
| SK-012 | Conductor resumes from `state.json` alone. `show` grows `artifacts` + `backlog` and a `--json` mode — the resume read-contract lives in the CLI, not in prose parsing state internals. Test: `/clear` mid-sprint, re-invoke, land on the same stage. (Invariant 5) | 4 | M | ☐ |
```

- [ ] **Step 2: Re-scope and re-point SK-013 (2 → 3)**

Replace the SK-013 row:

```markdown
| SK-013 | `/supskill run <sprint-id>` entry point: the init-or-resume-or-refuse matrix made explicit; the conductor never passes `--archive` itself; normalized-id comparison (case variants resume, never collide). Honours `sprint.entry` ∈ `SCOPE\|PLAN\|EXECUTE`. (**D7**) | 3 | M | ☐ |
```

- [ ] **Step 3: Record the invocation-model decision on SK-011**

Replace the SK-011 row:

```markdown
| SK-011 | `SKILL.md` whose `description` states **only triggering conditions** and does **not** summarize its own workflow — a documented regression causes agents to skip half the process otherwise. Decided at S2 DoR: v1 is user-invoked only (`disable-model-invocation: true`) because the conductor is side-effecting; SK-061 inherits the flagged tension. | 3 | M | ☐ |
```

- [ ] **Step 4: Add SK-033 to E4**

Append after the SK-032 row in the E4 table:

```markdown
| SK-033 | `supskill-state` verb that loads `tasks[]` (id, seam, provable, status=PENDING) from the refined sprint doc / dev plan into state. Today `init` writes `[]` and no verb adds tasks, while `block` requires the task to exist — without this, E5 cannot block, park, or map a single SDD status. (Proposed at S2 DoR, finding 6.) | 3 | M | ☐ |
```

- [ ] **Step 5: Update the totals**

- Summary table: E2 row `| 10 |` → `| 12 |`; E4 row `| 7 |` → `| 10 |`.
- Section headers: `## E2 — Conductor skill + plugin skeleton (10 pts)` → `(12 pts)`; `## E4 — PLAN + Gate 2 (7 pts)` → `(10 pts)`.
- `**Total: 115 pts.**` → `**Total: 120 pts.**` (E2 +2 for the SK-012/SK-013 re-points, E4 +3 for SK-033. The sprint doc's delta 5 names only E2's change explicitly; E4's header and the grand total must move too once SK-033 is a real row, or the backlog's own arithmetic breaks.)

- [ ] **Step 6: Record Gate 1 data point #2**

Append to the final paragraph of backlog.md (the "Open question to settle at S1's Gate 1" block), as a new paragraph:

```markdown
**Data point #2 (S2 DoR, 2026-07-12):** refinement against live source grew scope
+2 pts (10 → 12) and exposed a cross-epic gap — nothing populates `tasks[]`,
which would otherwise have surfaced as an E5 failure (now SK-033). Two sprints,
two data points, same direction. (Report §7.2)
```

- [ ] **Step 7: Commit**

```bash
git add docs/plans/sprints/backlog-01/backlog.md
git commit -m "docs: apply S2 DoR backlog deltas (SK-012 4pts, SK-013 3pts, SK-033 proposed)"
```

---

## Exit criteria mapping (sprint doc → plan)

| Sprint exit criterion | Where it lands |
|---|---|
| SK-010: validate green, real `skills/` dir, only plugin.json in `.claude-plugin/`, layout untouched | Task 1 |
| SK-011: explicit frontmatter, trigger-only description, lint test, decision recorded | Task 2 |
| SK-012: show prints artifacts+backlog, `--json` round-trips, dispatch table, invariant-3 prose review | Tasks 3 + 5 (review pass) |
| SK-013: matrix cells asserted in temp dir, `--entry` lands on stage, mismatch refuses naming `--archive` | Tasks 4 + 5 |
| Suite pure offline and fast, TDD evidence | Every task's step sequence |
| Sprint demo (invariant 5 in anger) | Task 6 — **operator-run; the sprint does not close on offline green alone** |
| Backlog deltas applied | Task 7 |

## Review pass (after all tasks)

Per the sprint's standing skills: author and review are separate lanes. Dispatch `oh-my-claudecode:code-reviewer` then `oh-my-claudecode:verifier` on the branch. The reviewer's named checks, beyond the usual: (1) invariant 3's prose surface — no SKILL.md line instructs editing `state.json`; (2) the frontmatter description contains no workflow summary (judgment, not regex — the lint's token tripwire is only a floor); (3) `--archive` appears in the skill body only inside the refusal message.
