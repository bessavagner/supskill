# Configurable story-id prefix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a consuming project declare its own story-id prefix (e.g. `BLK` instead of `SK`) so `supskill-state` and `supskill-audit` work against any project's backlog convention, and give REFINE/PLAN agents a sanctioned way to evidence findings about supskill's own tooling instead of a citation that can never resolve.

**Architecture:** A new `.supskill/config.json`, read/written by a new `config.py` module, holds one setting: `story_id_prefix` (default `"SK"`). `proofs.py` and `plan_coverage.py` gain an optional `story_prefix` parameter (default `"SK"`, so every existing call site and test is unaffected) instead of a hardcoded `SK-\d+` regex. `commands.py` and `citations.py` load the project's configured prefix and pass it through. A new `supskill-state config --story-id-prefix <PREFIX>` CLI verb writes it. Separately, `refine-prompt.md` and `plan-prompt.md` gain a short carve-out clause so a tooling/mechanism finding is evidenced by a quoted command + output, not a fabricated citation into the plugin's own source tree.

**Tech Stack:** Python 3.11+, pytest, `re`, `json`, `pathlib.Path` — no new dependencies.

## Global Constraints

- Every existing test must keep passing unmodified — the whole feature is additive with a default (`"SK"`) that reproduces today's hardcoded behavior exactly.
- `story_id_prefix` config values are validated on write only (`^[A-Z][A-Z0-9]*$`): uppercase letters/digits, must start with a letter.
- `config.py` never exposes a compiled regex or raw pattern string — `proofs.py` and `plan_coverage.py` stay the sole owners of their own grammars, per the codebase's existing "single vocabulary owner" convention (see `proofs.py`'s own module docstring).
- `.supskill/config.json` resolves exactly like `.supskill/state.json` does today: `(root or Path.cwd()) / ".supskill" / "<file>"`, no upward directory search (`store.py:25-26`).
- Run `.venv/bin/pytest` and `.venv/bin/ruff check .` after every task; both must be clean before moving to the next task.

---

### Task 1: `config.py` — the project-level story-id prefix store

**Files:**
- Create: `scripts/supskill_state/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `config.DEFAULT_STORY_ID_PREFIX: str` (`"SK"`)
- Produces: `config.config_path(root: Path | None = None) -> Path`
- Produces: `config.load_story_id_prefix(root: Path | None = None) -> str`
- Produces: `config.write_story_id_prefix(prefix: str, root: Path | None = None) -> None` — raises `StateError` on an invalid prefix

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config.py`:

```python
"""SK-064: per-project story-id prefix config, separate from state.json.

The scheme is a property of the project, not of one sprint run: it must
survive `init --archive` instead of resetting with each sprint, so it lives
in its own file rather than inside state.json.
"""

import json

import pytest

from supskill_state.config import (
    DEFAULT_STORY_ID_PREFIX,
    config_path,
    load_story_id_prefix,
    write_story_id_prefix,
)
from supskill_state.errors import StateError


def test_load_defaults_to_sk_when_no_config_file_exists(tmp_path):
    assert load_story_id_prefix(tmp_path) == "SK" == DEFAULT_STORY_ID_PREFIX


def test_write_then_load_round_trips(tmp_path):
    write_story_id_prefix("BLK", root=tmp_path)
    assert load_story_id_prefix(tmp_path) == "BLK"
    assert config_path(tmp_path).is_file()


def test_config_path_matches_state_jsons_own_supskill_dir(tmp_path):
    assert config_path(tmp_path) == tmp_path / ".supskill" / "config.json"


def test_write_rejects_lowercase_prefix(tmp_path):
    with pytest.raises(StateError, match="story-id-prefix"):
        write_story_id_prefix("blk", root=tmp_path)


def test_write_rejects_digit_first_prefix(tmp_path):
    with pytest.raises(StateError):
        write_story_id_prefix("1BLK", root=tmp_path)


def test_write_rejects_empty_prefix(tmp_path):
    with pytest.raises(StateError):
        write_story_id_prefix("", root=tmp_path)


def test_write_rejects_punctuation_in_prefix(tmp_path):
    with pytest.raises(StateError):
        write_story_id_prefix("BLK-", root=tmp_path)


def test_write_preserves_other_keys_already_in_the_file(tmp_path):
    path = config_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"future_knob": "keep-me"}) + "\n", encoding="utf-8")
    write_story_id_prefix("BLK", root=tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"future_knob": "keep-me", "story_id_prefix": "BLK"}


def test_overwriting_the_prefix_updates_in_place(tmp_path):
    write_story_id_prefix("BLK", root=tmp_path)
    write_story_id_prefix("PROJ", root=tmp_path)
    assert load_story_id_prefix(tmp_path) == "PROJ"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'supskill_state.config'`

- [ ] **Step 3: Write the implementation**

Create `scripts/supskill_state/config.py`:

```python
"""Per-project config at .supskill/config.json - the story-id prefix (SK-064).

Separate from state.json: the story-id scheme is a property of the project,
not of one sprint run, so it must survive `init --archive` instead of
resetting with each sprint. proofs.py and plan_coverage.py stay the sole
owners of the grammars built from this prefix - this module only stores and
validates the string.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .errors import StateError

DEFAULT_STORY_ID_PREFIX = "SK"
CONFIG_FILENAME = "config.json"

_PREFIX = re.compile(r"^[A-Z][A-Z0-9]*$")


def config_path(root: Path | None = None) -> Path:
    return (root or Path.cwd()) / ".supskill" / CONFIG_FILENAME


def load_story_id_prefix(root: Path | None = None) -> str:
    """The configured story-id prefix, or DEFAULT_STORY_ID_PREFIX if unset."""
    path = config_path(root)
    if not path.is_file():
        return DEFAULT_STORY_ID_PREFIX
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("story_id_prefix", DEFAULT_STORY_ID_PREFIX)


def write_story_id_prefix(prefix: str, root: Path | None = None) -> None:
    """Validate and persist prefix, preserving any other keys already on disk."""
    if not _PREFIX.match(prefix):
        raise StateError(
            f"--story-id-prefix must be uppercase letters/digits starting with a letter "
            f"(matching {_PREFIX.pattern!r}), got {prefix!r}"
        )
    path = config_path(root)
    data = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    data["story_id_prefix"] = prefix
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Lint and commit**

Run: `.venv/bin/ruff check scripts/supskill_state/config.py tests/test_config.py`
Expected: `All checks passed!`

```bash
git add scripts/supskill_state/config.py tests/test_config.py
git commit -m "feat: add .supskill/config.json for a project's story-id prefix"
```

---

### Task 2: `proofs.py` — parameterize the story-heading pattern

**Files:**
- Modify: `scripts/supskill_state/proofs.py:38` (the `_STORY` module constant), `:50` (`parse_proof_lines` signature), `:64` (where it's matched), `:74` (the violation message)
- Test: `tests/test_proofs.py`

**Interfaces:**
- Consumes: nothing new (no dependency on Task 1 — this module never imports `config`, by design; the caller supplies the prefix)
- Produces: `proofs.parse_proof_lines(text: str, story_prefix: str = "SK") -> list[ProofLine]` (signature grows one keyword-defaultable arg; every existing call site is unaffected)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_proofs.py` (append after the existing tests):

```python
def test_custom_story_prefix_is_honored():
    doc = """## Stories

### BLK-103 — a story · 3 · M
- **proof:** seam=unit · impact=local · provable=offline
"""
    assert parse_proof_lines(doc, story_prefix="BLK") == [
        ProofLine("BLK-103", "unit", "local", "offline")
    ]


def test_a_heading_that_does_not_match_the_configured_prefix_is_not_a_story_heading():
    # SK-001 does not match story_prefix="BLK" - the proof line below it has no heading
    doc = """## Stories

### SK-001 — a story · 3 · M
- **proof:** seam=unit · impact=local · provable=offline
"""
    with pytest.raises(StateError, match="before any"):
        parse_proof_lines(doc, story_prefix="BLK")


def test_the_missing_heading_violation_names_the_configured_prefix():
    with pytest.raises(StateError, match=r"before any ### BLK-xxx heading"):
        parse_proof_lines(
            "- **proof:** seam=unit · impact=local · provable=offline\n", story_prefix="BLK"
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_proofs.py -v`
Expected: FAIL — `TypeError: parse_proof_lines() got an unexpected keyword argument 'story_prefix'`

- [ ] **Step 3: Write the implementation**

In `scripts/supskill_state/proofs.py`, replace the module-level `_STORY` constant:

```python
_PROOF = re.compile(r"^- \*\*proof:\*\* seam=(\S+) · impact=(\S+) · provable=(\S+)(?:\s.*)?$")
_SECTION = re.compile(r"^##\s+(?!#)(.+?)\s*$")


def _story_pattern(story_prefix: str) -> re.Pattern[str]:
    return re.compile(rf"^###\s+.*?({re.escape(story_prefix)}-\d+)")
```

(this drops the old `_STORY = re.compile(r"^###\s+.*?(SK-\d+)")` line and moves `_SECTION` above the new function; `_PROOF` is unchanged)

Change the function signature and body:

```python
def parse_proof_lines(text: str, story_prefix: str = "SK") -> list[ProofLine]:
    """Every proof line, in document order; raises StateError listing every violation."""
    story_re = _story_pattern(story_prefix)
    proofs: list[ProofLine] = []
    violations: list[str] = []
    seen: set[str] = set()
    story: str | None = None
    in_stories = False
    required: list[str] = []  # story headings inside the Stories section, in order

    for number, line in enumerate(text.splitlines(), start=1):
        section = _SECTION.match(line)
        if section:
            in_stories = section.group(1).strip().lower() == "stories"
            continue
        heading = story_re.match(line)
        if heading:
            story = heading.group(1)
            if in_stories:
                required.append(story)
            continue
        match = _PROOF.match(line)
        if not match:
            continue
        if story is None:
            violations.append(f"line {number}: proof line before any ### {story_prefix}-xxx heading")
            continue
```

(everything after this point in the function body is unchanged)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_proofs.py -v`
Expected: PASS (18 passed)

- [ ] **Step 5: Run the full suite and lint, then commit**

Run: `.venv/bin/pytest && .venv/bin/ruff check .`
Expected: all tests pass (no other test touches `_STORY` directly), `All checks passed!`

```bash
git add scripts/supskill_state/proofs.py tests/test_proofs.py
git commit -m "feat: parameterize proofs.py's story-heading pattern by prefix"
```

---

### Task 3: `plan_coverage.py` — parameterize the story-id pattern

**Files:**
- Modify: `scripts/supskill_state/plan_coverage.py:24` (the `_STORY_ID` module constant), `:75` (`validate_plan_coverage` signature), `:85` (where it's matched)
- Test: `tests/test_plan_coverage.py`

**Interfaces:**
- Consumes: nothing new (no dependency on `config`, same reasoning as Task 2)
- Produces: `plan_coverage.validate_plan_coverage(plan_text: str, story_ids: list[str], story_prefix: str = "SK") -> list[str]`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_plan_coverage.py` (append after the existing tests):

```python
def test_custom_story_prefix_is_honored():
    plan = """### Task 1: the verb (BLK-030)

### Task 2: the guard (BLK-031)

### Task 3: the demo checklist (process)
"""
    assert validate_plan_coverage(plan, ["BLK-030", "BLK-031"], story_prefix="BLK") == []


def test_a_heading_naming_the_default_sk_prefix_does_not_satisfy_a_configured_blk_prefix():
    failures = validate_plan_coverage("### Task 1: x (SK-030)\n", ["SK-030"], story_prefix="BLK")
    # the heading names no BLK- story (unmarked, non-process) AND SK-030 is reported dropped
    assert len(failures) == 2
    assert any("not marked" in f for f in failures)
    assert any("SK-030" in f and "drops" in f for f in failures)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_plan_coverage.py -v`
Expected: FAIL — `TypeError: validate_plan_coverage() got an unexpected keyword argument 'story_prefix'`

- [ ] **Step 3: Write the implementation**

In `scripts/supskill_state/plan_coverage.py`, replace the module-level `_STORY_ID` constant:

```python
_TASK_HEADING = re.compile(r"^ {0,3}###\s+Task\s+\d+\b.*$")
# A CommonMark fence line: 0-3 leading spaces, then a run of 3+ of the same
# fence character (backtick or tilde), then the rest of the line (info string
# on an opener, or the trailing-whitespace check on a closer).
_FENCE_LINE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def _story_id_pattern(story_prefix: str) -> re.Pattern[str]:
    return re.compile(rf"{re.escape(story_prefix)}-\d+")
```

(this drops the old `_STORY_ID = re.compile(r"SK-\d+")` line; `_TASK_HEADING` and `_FENCE_LINE` and their comment are unchanged, just reordered so the new function sits after them)

Change `validate_plan_coverage`'s signature and the line that used `_STORY_ID`:

```python
def validate_plan_coverage(plan_text: str, story_ids: list[str], story_prefix: str = "SK") -> list[str]:
    """One message per violation; an empty list means the join is clean both ways."""
    headings = plan_task_headings(plan_text)
    if not headings:
        return ["the plan has no `### Task N: ...` headings - there is nothing to join the stories through"]

    story_id_re = _story_id_pattern(story_prefix)
    known = set(story_ids)
    named: set[str] = set()
    failures: list[str] = []
    for heading in headings:
        found = story_id_re.findall(heading)
```

(everything after this point in the function body is unchanged)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_plan_coverage.py -v`
Expected: PASS (11 passed)

- [ ] **Step 5: Run the full suite and lint, then commit**

Run: `.venv/bin/pytest && .venv/bin/ruff check .`
Expected: all tests pass, `All checks passed!`

```bash
git add scripts/supskill_state/plan_coverage.py tests/test_plan_coverage.py
git commit -m "feat: parameterize plan_coverage.py's story-id pattern by prefix"
```

---

### Task 4: `commands.py` — wire config into `load_tasks`, add `set_story_id_prefix`

**Files:**
- Modify: `scripts/supskill_state/commands.py:17-37` (imports), `:276-329` (`load_tasks`)
- Test: `tests/test_tasks.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `config.load_story_id_prefix(root: Path | None = None) -> str` and `config.write_story_id_prefix(prefix: str, root: Path | None = None) -> None` (Task 1); `parse_proof_lines(text, story_prefix=...)` (Task 2); `validate_plan_coverage(plan_text, story_ids, story_prefix=...)` (Task 3)
- Produces: `commands.set_story_id_prefix(prefix: str, *, root: Path | None = None) -> str` — returns the *previous* prefix, for the CLI to report

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tasks.py` (append after the existing tests):

```python
def test_load_tasks_honors_the_projects_configured_story_id_prefix(tmp_path):
    from supskill_state.config import write_story_id_prefix

    init_sprint("s4", backlog="backlog.md", root=tmp_path)
    write_story_id_prefix("BLK", root=tmp_path)
    doc = "## Stories\n\n### BLK-103 — first · 3 · M\n- **proof:** seam=unit · impact=local · provable=offline\n"
    (tmp_path / "doc.md").write_text(doc, encoding="utf-8")
    state = load_tasks("doc.md", root=tmp_path)
    assert [t.id for t in state.tasks] == ["BLK-103"]


def test_load_tasks_with_plan_honors_the_configured_prefix(tmp_path):
    from supskill_state.config import write_story_id_prefix

    init_sprint("s4", backlog="backlog.md", root=tmp_path)
    write_story_id_prefix("BLK", root=tmp_path)
    doc = "## Stories\n\n### BLK-103 — first · 3 · M\n- **proof:** seam=unit · impact=local · provable=offline\n"
    (tmp_path / "doc.md").write_text(doc, encoding="utf-8")
    (tmp_path / "plan.md").write_text("### Task 1: a (BLK-103)\n", encoding="utf-8")
    state = load_tasks("doc.md", plan="plan.md", root=tmp_path)
    assert [t.id for t in state.tasks] == ["BLK-103"]
```

Add to `tests/test_config.py` (append after the existing tests):

```python
def test_commands_set_story_id_prefix_returns_the_previous_value(tmp_path):
    from supskill_state.commands import set_story_id_prefix

    assert set_story_id_prefix("BLK", root=tmp_path) == "SK"
    assert set_story_id_prefix("PROJ", root=tmp_path) == "BLK"
    assert load_story_id_prefix(tmp_path) == "PROJ"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_tasks.py tests/test_config.py -v`
Expected: FAIL — the two new `test_tasks.py` cases fail because `BLK-103` isn't recognized as a story heading yet (default `"SK"` prefix, no config wired in); the new `test_config.py` case fails with `ImportError: cannot import name 'set_story_id_prefix'`

- [ ] **Step 3: Write the implementation**

In `scripts/supskill_state/commands.py`, add `config` to the imports (the existing import block starts `from . import store` — add a second line right after it):

```python
from . import config, store
```

(this replaces the standalone `from . import store` line; every other import in that block is unchanged)

Modify `load_tasks` (the body from `root = Path(root)...` through the `validate_plan_coverage` call):

```python
    root = Path(root) if root is not None else Path.cwd()
    doc_path = root / doc
    if not doc_path.is_file():
        raise StateError(f"no such doc: {doc}")
    story_prefix = config.load_story_id_prefix(root)
    proofs = parse_proof_lines(doc_path.read_text(encoding="utf-8"), story_prefix=story_prefix)
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

    if plan is not None:
        plan_path = root / plan
        if not plan_path.is_file():
            raise StateError(f"no such plan: {plan}")
        failures = validate_plan_coverage(
            plan_path.read_text(encoding="utf-8"),
            [proof.story for proof in proofs],
            story_prefix=story_prefix,
        )
```

(the rest of `load_tasks`, from `if failures:` to the final `return state`, is unchanged)

Add a new function directly after `load_tasks` (before `record_task_status`):

```python
def set_story_id_prefix(prefix: str, *, root: Path | None = None) -> str:
    """Persist the project's story-id prefix to .supskill/config.json (SK-064).

    Returns the prefix that was configured before this call (DEFAULT_STORY_ID_PREFIX
    if none was set), so the CLI can report what changed.
    """
    root = Path(root) if root is not None else Path.cwd()
    previous = config.load_story_id_prefix(root)
    config.write_story_id_prefix(prefix, root=root)
    return previous
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_tasks.py tests/test_config.py -v`
Expected: PASS (all cases, including the 2 new in `test_tasks.py` and 1 new in `test_config.py`)

- [ ] **Step 5: Run the full suite and lint, then commit**

Run: `.venv/bin/pytest && .venv/bin/ruff check .`
Expected: all tests pass, `All checks passed!`

```bash
git add scripts/supskill_state/commands.py tests/test_tasks.py tests/test_config.py
git commit -m "feat: load_tasks honors the project's configured story-id prefix"
```

---

### Task 5: `cli.py` — the `config` verb

**Files:**
- Modify: `scripts/supskill_state/cli.py:12-32` (`build_parser`), and add `_add_config`/`_cmd_config` near the other `_add_*`/`_cmd_*` pairs (after `_cmd_review`, before `main`)
- Test: `tests/test_init.py`

**Interfaces:**
- Consumes: `commands.set_story_id_prefix(prefix: str, *, root: Path | None = None) -> str` (Task 4)
- Produces: the `supskill-state config --story-id-prefix <PREFIX>` CLI verb

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_init.py`. First add the import at the top of the file (it currently imports `init_sprint`, `StateError`, `Stage`, and store helpers, but not `main`):

```python
from supskill_state.cli import main
```

Then append these tests at the end of the file:

```python
def test_cli_config_sets_the_story_id_prefix_and_reports_the_previous_value(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["config", "--story-id-prefix", "BLK"]) == 0
    assert "set story id prefix: BLK (was: SK)" in capsys.readouterr().out
    assert main(["config", "--story-id-prefix", "PROJ"]) == 0
    assert "set story id prefix: PROJ (was: BLK)" in capsys.readouterr().out


def test_cli_config_rejects_an_invalid_prefix(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["config", "--story-id-prefix", "blk"]) == 1
    assert "story-id-prefix" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_init.py -v`
Expected: FAIL — `argparse` error / `SystemExit` because `config` is not a known subcommand

- [ ] **Step 3: Write the implementation**

In `scripts/supskill_state/cli.py`, add the new subparser registration inside `build_parser` (add this line right after `_add_review(subparsers)`, before `return parser`):

```python
    _add_review(subparsers)
    _add_config(subparsers)
    return parser
```

Add the new functions after `_cmd_review` and before `def main(...)`:

```python
def _add_config(subparsers) -> None:
    sub = subparsers.add_parser("config", help="set project-level config, e.g. the story-id prefix")
    sub.add_argument(
        "--story-id-prefix",
        required=True,
        dest="story_id_prefix",
        help="uppercase prefix used by this project's story ids, e.g. BLK for BLK-103 (default: SK)",
    )
    sub.set_defaults(func=_cmd_config)


def _cmd_config(args) -> int:
    previous = commands.set_story_id_prefix(args.story_id_prefix)
    print(f"set story id prefix: {args.story_id_prefix} (was: {previous})")
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_init.py -v`
Expected: PASS (all cases, including the 2 new ones)

- [ ] **Step 5: Run the full suite and lint, then commit**

Run: `.venv/bin/pytest && .venv/bin/ruff check .`
Expected: all tests pass, `All checks passed!`

```bash
git add scripts/supskill_state/cli.py tests/test_init.py
git commit -m "feat: add 'supskill-state config --story-id-prefix' CLI verb"
```

---

### Task 6: `citations.py` — `supskill-audit --proofs` honors the configured prefix

**Files:**
- Modify: `scripts/supskill_state/citations.py:1-27` (imports), `:93-112` (`main`)
- Test: `tests/test_citations.py`

**Interfaces:**
- Consumes: `config.load_story_id_prefix(root: Path | None = None) -> str` (Task 1); `parse_proof_lines(text, story_prefix=...)` (Task 2)
- Produces: no new public function — `main`'s existing `--proofs` behavior now resolves the project's prefix from `.supskill/config.json` under `Path.cwd()`, exactly as `store.py` resolves `state.json`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_citations.py` (append after the existing tests):

```python
def test_proofs_flag_honors_the_projects_configured_story_id_prefix(tmp_path, monkeypatch, capsys):
    from supskill_state.config import write_story_id_prefix

    _tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    write_story_id_prefix("BLK", root=tmp_path)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "## Stories\n\n### BLK-103 — s · 1 · M\n"
        "- **proof:** seam=unit · impact=local · provable=offline\n"
    )
    assert main(["doc.md", "--proofs"]) == 0


def test_proofs_flag_without_config_still_gates_on_the_default_sk_prefix(tmp_path, monkeypatch, capsys):
    _tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    doc = tmp_path / "doc.md"
    doc.write_text(
        "## Stories\n\n### BLK-103 — s · 1 · M\n"
        "- **proof:** seam=unit · impact=local · provable=offline\n"
    )
    assert main(["doc.md", "--proofs"]) == 1
    assert "before any" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_citations.py -v`
Expected: FAIL — the first new test fails (exit code 1, not 0) because `--proofs` still hardcodes the `SK` default and doesn't yet read `.supskill/config.json`

- [ ] **Step 3: Write the implementation**

In `scripts/supskill_state/citations.py`, change the import block. `ruff`'s isort rule sorts a bare
`from . import X` before `from .errors import X` (see `commands.py`'s own import block for the
precedent: `from . import store` comes first), so:

```python
from . import config
from .errors import StateError
from .proofs import parse_proof_lines
```

Change `main`'s `--proofs` branch:

```python
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
            story_prefix = config.load_story_id_prefix(Path.cwd())
            parse_proof_lines(text, story_prefix=story_prefix)
        except StateError as error:
            failures.append(str(error))
    if failures:
        for failure in failures:
            print(f"supskill-audit: {failure}", file=sys.stderr)
        return 1
    print("supskill-audit: ok")
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_citations.py -v`
Expected: PASS (all cases, including the 2 new ones)

- [ ] **Step 5: Run the full suite and lint, then commit**

Run: `.venv/bin/pytest && .venv/bin/ruff check .`
Expected: all tests pass, `All checks passed!`

```bash
git add scripts/supskill_state/citations.py tests/test_citations.py
git commit -m "feat: supskill-audit --proofs honors the project's configured story-id prefix"
```

---

### Task 7: Prompt guidance — a citation carve-out for tooling findings

**Files:**
- Modify: `skills/supskill/references/refine-prompt.md:41` (end of item 1's citation sentence)
- Modify: `skills/supskill/references/plan-prompt.md:58` (end of item 3's citation sentence)
- Test: `tests/test_prompt_templates.py`

**Interfaces:**
- Consumes: nothing (prose-only; no code interface)
- Produces: nothing (no code interface) — a documented carve-out both prompt files now state verbatim

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_prompt_templates.py` (append after the existing tests):

```python
def test_refine_template_carves_out_tooling_findings_from_the_repo_root_citation_rule():
    text = REFINE.read_text(encoding="utf-8")
    assert "supskill's own tooling or mechanism" in text
    assert "reproduced symptom" in text


def test_plan_template_carves_out_tooling_findings_from_the_repo_root_citation_rule():
    text = PLAN.read_text(encoding="utf-8")
    assert "supskill's own tooling or mechanism" in text
    assert "reproduced symptom" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_prompt_templates.py -v`
Expected: FAIL — both new assertions fail (`"supskill's own tooling or mechanism" not in text`)

- [ ] **Step 3: Write the implementation**

In `skills/supskill/references/refine-prompt.md`, item 1 currently ends (line 41):

```
   `path:line` (or `path:start-end`) citation that resolves in {REPO_ROOT}'s
   working tree. A script audits every citation and fails this stage on any
   that does not resolve.
```

Insert this new paragraph directly after it (still inside item 1, before item 2 starts):

```
   A finding about supskill's own tooling or mechanism — not {REPO_ROOT}'s
   code — is not evidenced by a citation into the plugin's installed source
   tree; it doesn't live under {REPO_ROOT} and no such citation can resolve.
   Evidence for a tooling finding is the reproduced symptom itself: quote the
   exact command and its verbatim output in prose, with no backtick
   `path:line` token, so the citation audit has nothing to (mis)resolve.
```

In `skills/supskill/references/plan-prompt.md`, item 3 currently ends (line 58):

```
   `Create: \`scripts/foo.py\`` — because a line number for a file that does not
   exist yet cannot resolve and never will. Read the live source before citing
   it; the sprint doc was written earlier and its line numbers may have shifted.
```

Insert this new paragraph directly after it (still inside item 3, before item 4 starts):

```
   A finding about supskill's own tooling or mechanism — not {REPO_ROOT}'s
   code — is not evidenced by a citation into the plugin's installed source
   tree; it doesn't live under {REPO_ROOT} and no such citation can resolve.
   Evidence for a tooling finding is the reproduced symptom itself: quote the
   exact command and its verbatim output in prose, with no backtick
   `path:line` token, so the citation audit has nothing to (mis)resolve.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_prompt_templates.py -v`
Expected: PASS (all cases, including the 2 new ones)

- [ ] **Step 5: Run the full suite and lint, then commit**

Run: `.venv/bin/pytest && .venv/bin/ruff check .`
Expected: all tests pass, `All checks passed!`

```bash
git add skills/supskill/references/refine-prompt.md skills/supskill/references/plan-prompt.md tests/test_prompt_templates.py
git commit -m "docs: carve out tooling findings from REFINE/PLAN's repo-root citation rule"
```

---

## Plan self-review notes

- **Spec coverage:** section A → Task 1; section B → Tasks 4 (commands) + 5 (CLI); section C → Tasks 2, 3, 4, 6; section D → Task 7; section E → each task's own test additions plus the dedicated integration cases in Tasks 4 and 6; section F (non-goals) → no task touches `show`, no second citable root, no auto-detection, no `cli.py` help-string changes.
- **Placeholder scan:** every step has literal code, exact file paths, exact run commands and expected output; no "TBD"/"add error handling"/"similar to Task N" language anywhere.
- **Type/signature consistency:** `parse_proof_lines(text, story_prefix="SK")` (Task 2) and `validate_plan_coverage(plan_text, story_ids, story_prefix="SK")` (Task 3) are the exact signatures Task 4 calls; `commands.set_story_id_prefix(prefix, *, root=None) -> str` (Task 4) is the exact signature Task 5's `_cmd_config` calls; `config.load_story_id_prefix`/`write_story_id_prefix` (Task 1) are the exact names every later task imports.
