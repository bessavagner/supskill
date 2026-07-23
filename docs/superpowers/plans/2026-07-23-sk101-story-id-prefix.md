# SK-101 — Finish the story-id-prefix feature — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the configured story-id prefix load-bearing end to end — the Gate-1 audit refuses a doc whose story ids don't match the configured prefix, and the SCOPE/PLAN dispatch templates carry the prefix mechanically instead of hard-coding `SK-0xx`.

**Architecture:** The prefix is already stored (`.supskill/config.json` via `config.py`) and honored by both parsers (`proofs.py`, `plan_coverage.py` take `story_prefix`). Two gaps remain, closed here: (1) `parse_proof_lines` returns `[]` on a prefix *mismatch* — indistinguishable from "no stories" — so `supskill-audit --proofs` and `load-doc` both read a mismatch as a clean pass; (2) the dispatch templates hard-code the literal `SK-0xx`, and on the playset (`PLS`) run only the refining agent's *judgment* caught it — a net SK-100 just thinned by folding REFINE into SCOPE. We add a mismatch refusal in the parser (inherited by every caller), a `config --get` read-path, and a `{STORY_ID_PREFIX}` placeholder the conductor fills.

**Tech Stack:** Python 3 (stdlib `re`, `argparse`, `json`), pytest, ruff, mypy. Prompt templates are Markdown under `skills/supskill/references/`.

## Global Constraints

- **Test runner:** `uv run pytest` (offline; no network, no external binaries). Lint `uv run ruff check .`; types `uv run mypy`. All three cover `tests/` as well as `scripts/` per `pyproject.toml:36`.
- **Line length:** ruff caps lines at 100 columns (`pyproject.toml:28`).
- **No AI attribution** in any commit message (repository rule) — no `Co-Authored-By`, no "Generated with" line, no mention of Claude/AI.
- **Commit prefix:** `feat(SK-101):` / `refactor(SK-101):` / `test(SK-101):` per the repo's conventional-commit style.
- **`proofs.py` is the single owner of the story-grammar** — the mismatch check goes there so `load-doc` and `--proofs` both inherit it; do not add a second parser (SK-022/SK-033 invariant).
- **Prefix validation shape:** an uppercase prefix is `^[A-Z][A-Z0-9]*$` (`config.py:22`); story ids are `<PREFIX>-<digits>`.
- **The narrow rule:** refuse a *mismatch* (Stories section has story-shaped headings, none matching the configured prefix), never mere *emptiness* (a doc with no story headings must still parse to `[]`).

---

## File Structure

- `scripts/supskill_state/proofs.py` (modify) — add `_STORY_SHAPED` and a mismatch refusal to `parse_proof_lines`. The parser stays the sole grammar owner.
- `scripts/supskill_state/cli.py` (modify) — add a `--get` read-path to the `config` subcommand; import `config`.
- `skills/supskill/references/scope-prompt.md`, `plan-prompt.md` (modify) — replace the `SK-0xx` literal with the `{STORY_ID_PREFIX}` placeholder the conductor fills.
- `skills/supskill/references/replan-shapes.md` (modify) — this file is conductor-facing guidance, **not** a `{PLACEHOLDER}`-filled subagent template, so its `<SK-0xx>` becomes the prefix-neutral `<story-id>` (the conductor already holds real ids in `tasks[]`).
- `skills/supskill/SKILL.md` (modify) — the SCOPE and PLAN fill steps read the prefix via `config --get` and fill `{STORY_ID_PREFIX}`. The illustrative `SK-0xx` literals elsewhere in SKILL.md (the conductor's own instructions, which know the prefix) are left as-is by design.
- `tests/test_proofs.py`, `tests/test_citations.py`, `tests/test_config.py`, `tests/test_prompt_templates.py` (modify) — cover each change.

**Task order:** Task 1 (audit refusal) is the highest-value, fully independent mechanical net. Task 2 (read-path) is a prerequisite for Task 3's conductor fill. Task 3 depends on Task 2.

---

### Task 1: The proof parser refuses a story-id prefix mismatch

**Files:**
- Modify: `scripts/supskill_state/proofs.py`
- Test: `tests/test_proofs.py`, `tests/test_citations.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `parse_proof_lines(text, story_prefix="SK")` now raises `StateError` (message contains `"prefix mismatch"`, both prefixes, and `"supskill config --story-id-prefix <PREFIX>"`) when the `## Stories` section contains story-shaped headings (`[A-Z][A-Z0-9]*-\d+`) but none match `story_prefix`. Behavior is unchanged for matching-prefix docs and for docs with no story headings (still returns `list[ProofLine]` / `[]`). Both `supskill-audit --proofs` (`citations.py`) and `load-doc` (`commands.py:298`) inherit the refusal with no change of their own.

- [ ] **Step 1: Write the failing parser tests**

Add to `tests/test_proofs.py` (the module already imports `StateError` and `parse_proof_lines` and defines `GOOD`):

```python
def test_a_stories_section_with_a_foreign_prefix_is_refused():
    doc = GOOD.replace("SK-001", "PLS-001")
    with pytest.raises(StateError, match="prefix mismatch"):
        parse_proof_lines(doc, story_prefix="SK")


def test_the_mismatch_message_names_both_prefixes_and_the_config_command():
    doc = GOOD.replace("SK-001", "PLS-009")
    with pytest.raises(StateError) as exc:
        parse_proof_lines(doc, story_prefix="SK")
    message = str(exc.value)
    assert "PLS" in message and "SK" in message
    assert "supskill config --story-id-prefix PLS" in message


def test_a_matching_configured_prefix_still_parses():
    doc = GOOD.replace("SK-001", "PLS-001")
    assert parse_proof_lines(doc, story_prefix="PLS")[0].story == "PLS-001"


def test_a_stories_section_with_no_story_headings_is_not_a_mismatch():
    # narrow rule: refuse a MISMATCH, not mere emptiness
    doc = "## Stories\n\nprose only, no story headings yet\n"
    assert parse_proof_lines(doc, story_prefix="SK") == []
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run pytest tests/test_proofs.py -k "foreign_prefix or mismatch_message or matching_configured or no_story_headings" -v`
Expected: `test_a_stories_section_with_a_foreign_prefix_is_refused` and `test_the_mismatch_message_...` FAIL (no exception raised — the parser returns `[]`, the exact vacuous-pass bug). The other two PASS already.

- [ ] **Step 3: Add the story-shape regex to `proofs.py`**

Insert directly after the `_SECTION` definition (`scripts/supskill_state/proofs.py:38`):

```python
# A story-shaped heading with ANY uppercase prefix. Used only to tell a prefix
# MISMATCH (a Stories section full of PLS-009 under an SK config) from a doc
# that genuinely has no stories. SK-101: without this, parse_proof_lines returns
# [] on a mismatch and every caller (supskill-audit --proofs, load-doc) reads
# that as a clean pass — the exact hole the playset PLS run fell through.
_STORY_SHAPED = re.compile(r"^###\s+.*?([A-Z][A-Z0-9]*-\d+)")
```

- [ ] **Step 4: Detect foreign-prefixed headings and refuse in `parse_proof_lines`**

In `parse_proof_lines`, add a `foreign_ids` accumulator next to the other locals (`scripts/supskill_state/proofs.py:56-61`):

```python
    foreign_ids: list[str] = []  # story-shaped headings in Stories that miss story_prefix
```

Then, inside the loop, insert the foreign-heading branch **between** the configured-prefix heading block (the one ending `continue` at line 73) and the `match = _PROOF.match(line)` line:

```python
        if in_stories:
            shaped = _STORY_SHAPED.match(line)
            if shaped:
                foreign_ids.append(shaped.group(1))
                continue
```

Finally, after the loop and **before** the `for story_id in required:` missing-proof check (`scripts/supskill_state/proofs.py:96`), add the refusal:

```python
    if not required and foreign_ids:
        prefixes = sorted({fid.rsplit("-", 1)[0] for fid in foreign_ids})
        suggestion = "/".join(prefixes)
        raise StateError(
            f"story-id prefix mismatch: the Stories section uses {suggestion} "
            f"(e.g. {foreign_ids[0]}) but the configured prefix is {story_prefix}; "
            f"run: supskill config --story-id-prefix {prefixes[0]}"
        )
```

- [ ] **Step 5: Run the proof tests to verify they pass and nothing regressed**

Run: `uv run pytest tests/test_proofs.py -v`
Expected: PASS, including the four new tests and the existing `test_dogfood_this_sprints_own_doc_parses`, `test_story_in_the_stories_section_without_a_proof_line_rejected`, and `test_sk_headings_outside_the_stories_section_do_not_require_proof_lines` (which uses `## Deferred`, so `in_stories` is False and the foreign branch never fires).

- [ ] **Step 6: Write the failing audit integration test**

Add to `tests/test_citations.py` (it already imports `main` and defines `_tree`):

```python
def test_proofs_flag_refuses_a_story_id_prefix_mismatch(tmp_path, monkeypatch, capsys):
    _tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "## Stories\n\n"
        "### PLS-009 — close the guard · 2 · M\n"
        "- **proof:** seam=unit · impact=local · provable=offline\n",
        encoding="utf-8",
    )
    # config defaults to SK; the doc uses PLS -> the audit must refuse, not pass vacuously
    assert main(["doc.md", "--proofs"]) == 1
    assert "prefix mismatch" in capsys.readouterr().err
```

- [ ] **Step 7: Run the audit test to verify it passes**

Run: `uv run pytest tests/test_citations.py::test_proofs_flag_refuses_a_story_id_prefix_mismatch -v`
Expected: PASS. (`citations.py`'s `main` catches the `StateError`, appends it to `failures`, and returns 1 — no change to `citations.py` was needed; the refusal is inherited from `proofs.py`.)

- [ ] **Step 8: Run the full suite, lint, and types**

Run: `uv run pytest && uv run ruff check . && uv run mypy`
Expected: all green (test count strictly greater than before).

- [ ] **Step 9: Commit**

```bash
git add scripts/supskill_state/proofs.py tests/test_proofs.py tests/test_citations.py
git commit -m "feat(SK-101): refuse a story-id prefix mismatch in the proof parser

parse_proof_lines returned [] on a prefix mismatch, which supskill-audit
--proofs and load-doc both read as a clean pass; on the playset PLS run only
the refining agent's judgment caught it. Detect story-shaped headings whose
prefix misses the configured one and refuse with the config-command remedy.
The audit inherits it with no change of its own. (playset s1.)"
```

---

### Task 2: A read-path for the configured prefix (`config --get`)

**Files:**
- Modify: `scripts/supskill_state/cli.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `config.load_story_id_prefix()` (`config.py:29`), `commands.set_story_id_prefix` (`commands.py:335`).
- Produces: `supskill-state config --get` prints the configured prefix (or `SK` if unset) on stdout and returns 0. `config --story-id-prefix <PREFIX>` keeps its existing set-and-report behavior. `config` with neither flag returns 1 with a stderr message naming `--story-id-prefix`. The conductor uses `config --get` in Task 3 to fill `{STORY_ID_PREFIX}`.

- [ ] **Step 1: Write the failing CLI tests**

Add to `tests/test_config.py`:

```python
def test_cli_config_get_prints_the_configured_prefix(tmp_path, monkeypatch, capsys):
    from supskill_state.cli import main

    monkeypatch.chdir(tmp_path)
    assert main(["config", "--story-id-prefix", "PLS"]) == 0
    capsys.readouterr()  # drain the "set story id prefix" line
    assert main(["config", "--get"]) == 0
    assert capsys.readouterr().out.strip() == "PLS"


def test_cli_config_get_defaults_to_sk_when_unset(tmp_path, monkeypatch, capsys):
    from supskill_state.cli import main

    monkeypatch.chdir(tmp_path)
    assert main(["config", "--get"]) == 0
    assert capsys.readouterr().out.strip() == "SK"


def test_cli_config_with_neither_flag_is_refused(tmp_path, monkeypatch, capsys):
    from supskill_state.cli import main

    monkeypatch.chdir(tmp_path)
    assert main(["config"]) == 1
    assert "story-id-prefix" in capsys.readouterr().err
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run pytest tests/test_config.py -k "cli_config" -v`
Expected: FAIL — `config --get` is an unrecognized argument (argparse error), and `config` currently requires `--story-id-prefix`.

- [ ] **Step 3: Import `config` into `cli.py`**

Change the import line at `scripts/supskill_state/cli.py:9`:

```python
from . import commands, config, plan_guard, replan_guard, worktree
```

- [ ] **Step 4: Add `--get` to the config subcommand and its handler**

Replace `_add_config` and `_cmd_config` (`scripts/supskill_state/cli.py:292-306`) with:

```python
def _add_config(subparsers) -> None:
    sub = subparsers.add_parser(
        "config", help="read or set project-level config, e.g. the story-id prefix"
    )
    sub.add_argument(
        "--story-id-prefix",
        dest="story_id_prefix",
        help="uppercase prefix used by this project's story ids, e.g. BLK for BLK-103 (default: SK)",
    )
    sub.add_argument(
        "--get",
        action="store_true",
        help="print the configured story-id prefix (SK if unset) and exit",
    )
    sub.set_defaults(func=_cmd_config)


def _cmd_config(args) -> int:
    if args.get:
        print(config.load_story_id_prefix())
        return 0
    if not args.story_id_prefix:
        raise StateError("config: pass --story-id-prefix <PREFIX> to set, or --get to read")
    previous = commands.set_story_id_prefix(args.story_id_prefix)
    print(f"set story id prefix: {args.story_id_prefix} (was: {previous})")
    return 0
```

(Removing `required=True` is deliberate: the flag is now optional so `--get` can stand alone; the `if not args.story_id_prefix` guard restores a clear refusal when neither is given. `main` already maps `StateError` → stderr + exit 1.)

- [ ] **Step 5: Run the CLI tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS, including the three new tests and every existing `config.py` test (the module functions are unchanged).

- [ ] **Step 6: Run the full suite, lint, and types**

Run: `uv run pytest && uv run ruff check . && uv run mypy`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add scripts/supskill_state/cli.py tests/test_config.py
git commit -m "feat(SK-101): add a config --get read-path for the story-id prefix

Only the setter existed, so the conductor had no way to read the configured
prefix back to fill a template. Add config --get (prints the prefix, SK if
unset); make --story-id-prefix optional with a clear refusal when neither
flag is given."
```

---

### Task 3: Parameterize the dispatch templates on `{STORY_ID_PREFIX}`

**Files:**
- Modify: `skills/supskill/references/scope-prompt.md`, `skills/supskill/references/plan-prompt.md`, `skills/supskill/references/replan-shapes.md`, `skills/supskill/SKILL.md`
- Test: `tests/test_prompt_templates.py`

**Interfaces:**
- Consumes: `config --get` from Task 2 (the conductor reads the prefix and fills `{STORY_ID_PREFIX}`).
- Produces: `scope-prompt.md` and `plan-prompt.md` name a `{STORY_ID_PREFIX}` placeholder in place of the literal `SK-0xx`; `replan-shapes.md` uses the prefix-neutral `<story-id>`; none of the three reference files contains the literal `SK-0xx`. `SKILL.md`'s SCOPE and PLAN fill steps instruct the conductor to read the prefix via `config --get` and fill `{STORY_ID_PREFIX}`.

- [ ] **Step 1: Update the template tests to expect the placeholder (write the failing tests)**

In `tests/test_prompt_templates.py`, add `"{STORY_ID_PREFIX}"` to the scope placeholder tuple in `test_scope_template_names_its_placeholders`:

```python
    for placeholder in (
        "{SPRINT_ID}", "{BACKLOG_PATH}", "{OUTPUT_PATH}", "{REPO_ROOT}",
        "{EXEMPLAR_DOCS}", "{AUDIT_FAILURES}", "{STORY_ID_PREFIX}",
    ):
        assert placeholder in text, placeholder
```

Add `"{STORY_ID_PREFIX}"` to the plan placeholder tuple in `test_plan_template_names_its_placeholders`:

```python
    for placeholder in (
        "{SPRINT_DOC_PATH}", "{OUTPUT_PATH}", "{REPO_ROOT}", "{EXEMPLAR_PLAN}",
        "{STORY_ID_PREFIX}",
    ):
        assert placeholder in text, placeholder
```

Update the join-key assertion in `test_plan_template_states_the_join_key_and_the_citation_rule` from `"(SK-0xx)"` to the parameterized form:

```python
    assert "({STORY_ID_PREFIX}-0xx)" in text and "(process)" in text  # the heading grammar SK-033 validates
```

Add a new regression tripwire (the durable encoding of SK-101's acceptance) at the end of the file:

```python
def test_no_reference_template_hardcodes_the_sk_prefix_example():
    # SK-101: the SK-0xx literal is what anchored the playset PLS run onto SK.
    # scope/plan carry {STORY_ID_PREFIX}; replan-shapes is prefix-neutral.
    for reference in (SCOPE, PLAN, REFERENCES / "replan-shapes.md"):
        assert "SK-0xx" not in reference.read_text(encoding="utf-8"), reference.name
```

- [ ] **Step 2: Run the template tests to verify they fail**

Run: `uv run pytest tests/test_prompt_templates.py -k "names_its_placeholders or join_key or hardcodes_the_sk_prefix" -v`
Expected: FAIL — the templates still contain `SK-0xx` and no `{STORY_ID_PREFIX}`.

- [ ] **Step 3: Parameterize `scope-prompt.md`**

In `skills/supskill/references/scope-prompt.md:66-67`, replace:

```
     `### SK-0xx — <title> · <points> · <priority>` (use the backlog's own
     story-id prefix). Downstream stages join backlog rows to stories by these
```

with:

```
     `### {STORY_ID_PREFIX}-0xx — <title> · <points> · <priority>` — the
     `{STORY_ID_PREFIX}` is this project's configured story-id prefix, filled in
     by the conductor. Downstream stages join backlog rows to stories by these
```

- [ ] **Step 4: Parameterize `plan-prompt.md`**

In `skills/supskill/references/plan-prompt.md:46`, replace `(SK-0xx)` with `({STORY_ID_PREFIX}-0xx)`:

```
   `### Task N: <what> ({STORY_ID_PREFIX}-0xx)` — or the literal `### Task N: <what> (process)`
```

- [ ] **Step 5: Make `replan-shapes.md` prefix-neutral**

`replan-shapes.md` is conductor-facing guidance, not a `{PLACEHOLDER}`-filled subagent template, so it takes the prefix-neutral form rather than a placeholder. In `skills/supskill/references/replan-shapes.md:23`, replace:

```
`task --id <SK-0xx> --status PARKED --note "<the blocker that parked it>"` —
```

with:

```
`task --id <story-id> --status PARKED --note "<the blocker that parked it>"` —
```

- [ ] **Step 6: Run the template tests to verify they pass**

Run: `uv run pytest tests/test_prompt_templates.py -v`
Expected: PASS — including the two placeholder tests, the join-key test, the new `test_no_reference_template_hardcodes_the_sk_prefix_example`, and every pre-existing tripwire.

- [ ] **Step 7: Wire the conductor to read the prefix and fill the placeholder (SKILL.md)**

In `skills/supskill/SKILL.md`, extend the SCOPE fill step (step 4, `SKILL.md:122-126`) — append this sentence to it:

```
`{STORY_ID_PREFIX}` is this project's configured story-id prefix: read it once
with `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state config --get` and fill it verbatim.
```

In the PLAN fill step (step 5, `SKILL.md:177-181`), add `{STORY_ID_PREFIX}` to the listed placeholders and the same read instruction. Change:

```
   [references/plan-prompt.md](references/plan-prompt.md) — `{SPRINT_DOC_PATH}`,
   `{OUTPUT_PATH}`, `{REPO_ROOT}`, `{EXEMPLAR_PLAN}` (an existing plan under
   `docs/superpowers/plans/`, or `none`) — dispatch one general-purpose
```

to:

```
   [references/plan-prompt.md](references/plan-prompt.md) — `{SPRINT_DOC_PATH}`,
   `{OUTPUT_PATH}`, `{REPO_ROOT}`, `{EXEMPLAR_PLAN}` (an existing plan under
   `docs/superpowers/plans/`, or `none`), and `{STORY_ID_PREFIX}` (read once with
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state config --get`) — dispatch one general-purpose
```

(The illustrative `SK-0xx` literals elsewhere in `SKILL.md` — the conductor's own instructions, e.g. `SKILL.md:202,285,341-346,375` — are left as-is: the conductor knows the real prefix and they are examples, not agent-facing skeleton text.)

- [ ] **Step 8: Run the full suite, lint, and types**

Run: `uv run pytest && uv run ruff check . && uv run mypy`
Expected: all green. (`test_skill_frontmatter.py` checks frontmatter, not body prose, so the SKILL.md body edits do not affect it.)

- [ ] **Step 9: Commit**

```bash
git add skills/supskill/references/scope-prompt.md skills/supskill/references/plan-prompt.md skills/supskill/references/replan-shapes.md skills/supskill/SKILL.md tests/test_prompt_templates.py
git commit -m "feat(SK-101): parameterize the dispatch templates on the story-id prefix

The SCOPE and PLAN templates hard-coded SK-0xx; on the playset PLS run only the
refining agent's judgment kept the prefix right, and SK-100 thinned that net.
Replace the literal with a {STORY_ID_PREFIX} placeholder the conductor fills
from config --get; make replan-shapes prefix-neutral. A tripwire test forbids
the SK-0xx literal returning to any reference template. (playset s1/s2.)"
```

---

## Self-Review

**1. Spec coverage** (against the SK-101 backlog row and the scope):
- "prompt templates still hard-code `SK-0xx` (`scope-prompt.md:41`, `plan-prompt.md:46`, `replan-shapes.md:23`)" → Task 3 (Steps 3–5), enforced by the tripwire test. (The live `SK-0xx` in scope-prompt is at line 66, not 41; the row's line number is stale, the string is the target.)
- "templates parameterize on the prefix" → Task 3, `{STORY_ID_PREFIX}` + SKILL.md fill wiring (Step 7).
- "`supskill-audit --proofs` passes vacuously on a prefix mismatch rather than refusing … the audit refuses a doc whose story ids do not match the configured prefix" → Task 1 (parser refusal inherited by `--proofs`, Steps 3–7).
- Hidden dependency found while scoping — no read-path for the prefix → Task 2 (`config --get`), prerequisite for Task 3.
- "parsers honor the configured prefix (`plan_coverage.py:31,78`, `proofs.py`)" → already shipped; no task needed (verified in scope).

**2. Placeholder scan:** every code step shows complete code; every command has expected output. No "TBD"/"add validation"/"similar to Task N". The one intentional literal — `{STORY_ID_PREFIX}` — is a template token, not a plan placeholder.

**3. Type consistency:** `parse_proof_lines(text, story_prefix="SK") -> list[ProofLine]` signature is unchanged (raises on mismatch, as it already raises on grammar violations). `config.load_story_id_prefix() -> str` and `commands.set_story_id_prefix(prefix, *, root=None) -> str` are used at their existing signatures. `_STORY_SHAPED` and `foreign_ids: list[str]` are new, self-contained in `proofs.py`. `main(argv) -> int` (both `cli.py` and `citations.py`) is unchanged. The placeholder token `{STORY_ID_PREFIX}` is spelled identically in the templates, the SKILL.md fill steps, and the tests.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-23-sk101-story-id-prefix.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
