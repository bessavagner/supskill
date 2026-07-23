# SK-111 + SK-112 — Worktree state resolution & EXECUTE reviewer file-handoff — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close two EXECUTE-boundary frictions the playset s5 run surfaced: `supskill-state` refusing when the conductor runs it from a linked-worktree cwd (SK-111), and the EXECUTE task-reviewer's findings arriving as a placeholder chat reply instead of a file the conductor can read (SK-112).

**Architecture:** SK-111 centralizes root resolution. Today every `commands.py` entry point repeats `root = Path(root) if root is not None else Path.cwd()` and passes that to `store.state_path(root)`, so state is always looked for under the *current* directory with no upward search (deliberate). During EXECUTE the conductor isolates into `.worktrees/<id>` but `.supskill/` never moves — so a state call made from the worktree cwd looks for `.worktrees/<id>/.supskill/` and is refused. We replace the repeated idiom with one `store.resolve_root()` that keeps the explicit-root and main-worktree behavior identical, and redirects to the main worktree root **only** when git identifies cwd as a linked worktree. SK-112 is a conductor-prose change: the EXECUTE drain's task-review dispatch must tell the reviewer to write its findings to a file under `<scratch>` and return only a status line — the same "read the file, never the reply" discipline supskill already uses for its own dispatches (`7dfb0f9`), applied to the SDD-composed task review it cannot edit the prompt body of.

**Tech Stack:** Python 3 (stdlib `subprocess`, `pathlib`), pytest, ruff. No new dependencies. SKILL.md prose under `skills/supskill/`.

## Global Constraints

- **Test runner:** `uv run pytest` (offline; no network). Lint: `uv run ruff check .`. Both cover `tests/` and `scripts/`. Do **not** run mypy — it is not installed or declared in this project.
- **Line length:** ruff caps lines at 100 columns.
- **No AI attribution** in any commit message (repository rule) — no `Co-Authored-By`, no "Generated with" line, no mention of Claude/AI/Anthropic.
- **Commit prefix:** `feat(SK-111):` / `refactor(SK-111):` / `feat(SK-112):` / `test(...)` per the repo's conventional-commit style.
- **The no-upward-search invariant stays** (`store.py`, SK-004/S2 design): a *main* worktree, a subdirectory of one, and a non-repo cwd must all still resolve `.supskill/` to cwd exactly as today. Only a git **linked** worktree (`--git-dir != --git-common-dir`) redirects — nothing else. This is a safety net, not a new "run from anywhere" workflow; the "run from the target repo's root" convention in SKILL.md is unchanged.
- **`main(argv) -> int`** maps `StateError` → stderr + exit 1. `resolve_root` must never raise on a non-repo cwd — it silently returns cwd.

---

## File Structure

- `scripts/supskill_state/store.py` (modify) — add `resolve_root()` and a private `_linked_worktree_root()` git helper. `supskill_dir`/`state_path`/`gates_path`/`runs_dir` are unchanged (they still take an explicit root).
- `scripts/supskill_state/commands.py` (modify) — replace the 10 repeated `root = Path(root) if root is not None else Path.cwd()` lines with `root = store.resolve_root(root)`.
- `tests/test_store.py` (modify) — unit tests for `resolve_root` (explicit root, main worktree, non-repo) + a real git-repo-plus-linked-worktree integration test proving a CLI call from the worktree cwd finds the main root's state.
- `skills/supskill/SKILL.md` (modify) — SK-112: the EXECUTE drain cycle's task-review dispatch writes findings to `<scratch>/task-<N>-review-findings.md` and returns only a status line.
- `tests/test_execute_prose.py` (modify) — SK-112 tripwire that the EXECUTE section names the review-findings file handoff and the read-the-file rule.

**Task order:** Task 1 (SK-111, code) and Task 2 (SK-112, prose) are independent — different files, different concerns, either mergeable alone. Do Task 1 first.

---

### Task 1: SK-111 — resolve state from the main worktree root when cwd is a linked worktree

**Files:**
- Modify: `scripts/supskill_state/store.py`
- Modify: `scripts/supskill_state/commands.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `git rev-parse --path-format=absolute --git-dir` / `--git-common-dir` (via `subprocess`).
- Produces:
  - `store.resolve_root(root: Path | None = None) -> Path` — with an explicit `root`, returns `Path(root)` unchanged. With `root=None`: if `cwd/.supskill/` exists, returns cwd (fast path, no git); else if cwd is a git linked worktree, returns the main worktree root; else returns cwd.
  - `store._linked_worktree_root(cwd: Path) -> Path | None` — the main worktree root iff `cwd` is a linked worktree (`--git-dir != --git-common-dir`), else `None`. Never raises: a non-repo cwd or a missing `git` binary yields `None`.
  - `commands.py` entry points call `store.resolve_root(root)` in place of the old idiom; their external signatures and behavior are otherwise unchanged.

- [ ] **Step 1: Write the failing unit tests for `resolve_root`**

Add to `tests/test_store.py` (it already imports `store` and `state_path` and uses `make_state`):

```python
import subprocess

from supskill_state.cli import main
from supskill_state.store import dump_state, resolve_root


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def test_resolve_root_returns_an_explicit_root_unchanged(tmp_path):
    assert resolve_root(tmp_path) == tmp_path


def test_resolve_root_uses_cwd_when_state_is_present(tmp_path, monkeypatch, make_state):
    dump_state(make_state(), state_path(tmp_path))  # tmp_path/.supskill/state.json now exists
    monkeypatch.chdir(tmp_path)
    assert resolve_root() == tmp_path


def test_resolve_root_falls_back_to_cwd_outside_a_repo(tmp_path, monkeypatch):
    # no .supskill/, not a git repo: unchanged no-upward-search behavior
    monkeypatch.chdir(tmp_path)
    assert resolve_root() == tmp_path
```

- [ ] **Step 2: Run the unit tests to verify they fail**

Run: `uv run pytest tests/test_store.py -k "resolve_root" -v`
Expected: import error — `resolve_root` does not exist in `supskill_state.store` yet.

- [ ] **Step 3: Add `resolve_root` and `_linked_worktree_root` to `store.py`**

In `scripts/supskill_state/store.py`, add `import subprocess` to the imports (after `import os`), then add these functions directly after `supskill_dir` (line 25-26):

```python
def _linked_worktree_root(cwd: Path) -> Path | None:
    """The MAIN worktree's root iff `cwd` is a git LINKED worktree, else None.

    SK-111: EXECUTE isolates into `.worktrees/<id>` but `.supskill/` never moves,
    so a state call from the worktree cwd must find the main root's `.supskill/`.
    A linked worktree is exactly the case where `--git-dir`
    (`<main>/.git/worktrees/<id>`) differs from `--git-common-dir` (`<main>/.git`);
    the main root is the common dir's parent. A main worktree, a subdirectory of
    one, or a non-repo cwd all return None here, preserving the deliberate
    no-upward-search behavior everywhere except the linked-worktree case git can
    identify unambiguously. Never raises: a missing git binary or a non-repo cwd
    is None, not a crash.
    """
    try:
        git_dir = _rev_parse_abs(cwd, "--git-dir")
        common = _rev_parse_abs(cwd, "--git-common-dir")
    except (OSError, StateError):
        return None
    if git_dir is None or common is None or git_dir == common:
        return None
    return common.parent


def _rev_parse_abs(cwd: Path, what: str) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--path-format=absolute", what],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    out = result.stdout.strip()
    return Path(out) if out else None


def resolve_root(root: Path | None = None) -> Path:
    """The directory whose `.supskill/` holds this sprint's state.

    An explicit `root` wins unchanged. Otherwise: cwd if it already carries
    `.supskill/` (the fast path — no git call); else the main worktree root when
    cwd is a linked worktree (SK-111); else cwd, unchanged.
    """
    if root is not None:
        return Path(root)
    cwd = Path.cwd()
    if (cwd / SUPSKILL_DIR).is_dir():
        return cwd
    return _linked_worktree_root(cwd) or cwd
```

- [ ] **Step 4: Run the unit tests to verify they pass**

Run: `uv run pytest tests/test_store.py -k "resolve_root" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Write the failing linked-worktree integration tests**

Add to `tests/test_store.py`:

```python
import pytest


@pytest.fixture
def repo_with_worktree(tmp_path, make_state):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "initial")
    # state lives at the MAIN root only
    dump_state(make_state(), state_path(repo))
    # a linked worktree, exactly like the EXECUTE stage's `supskill-state worktree`
    worktree = repo / ".worktrees" / "s1"
    _git(repo, "worktree", "add", "-q", "-b", "s1", str(worktree))
    return repo, worktree


def test_resolve_root_redirects_from_a_linked_worktree_to_the_main_root(
    repo_with_worktree, monkeypatch
):
    repo, worktree = repo_with_worktree
    monkeypatch.chdir(worktree)
    assert resolve_root().resolve() == repo.resolve()


def test_resolve_root_in_the_main_worktree_stays_at_cwd(repo_with_worktree, monkeypatch):
    repo, _worktree = repo_with_worktree
    monkeypatch.chdir(repo)
    assert resolve_root().resolve() == repo.resolve()


def test_a_cli_command_run_from_the_worktree_cwd_finds_the_main_root_state(
    repo_with_worktree, monkeypatch, capsys
):
    # the exact s5 failure: `supskill-state` from the worktree cwd was refused
    repo, worktree = repo_with_worktree
    monkeypatch.chdir(worktree)
    assert main(["show", "--json"]) == 0
    import json

    assert json.loads(capsys.readouterr().out)["sprint"]["id"] == "S10"
```

(The `make_state` conftest fixture builds a sprint with `sprint.id == "S10"`.)

- [ ] **Step 6: Run the integration tests to verify they fail**

Run: `uv run pytest tests/test_store.py -k "worktree or main_root_state" -v`
Expected: FAIL — `render_show_json` still resolves via `Path.cwd()` (the worktree), so `show` refuses with "no state file"; `resolve_root` is not yet wired into `commands.py`.

- [ ] **Step 7: Wire `resolve_root` through `commands.py`**

In `scripts/supskill_state/commands.py`, replace **every** occurrence of the line

```python
    root = Path(root) if root is not None else Path.cwd()
```

with

```python
    root = store.resolve_root(root)
```

Use an editor replace-all — there are 10 identical occurrences (in `init_sprint`, `render_show`, `render_show_json`, `record_artifact`, `record_gate`, `record_blocker`, `record_task_status`, `set_story_id_prefix`, `load_tasks`, `record_cost`). All are the same string; `store` is already imported. After replacing, confirm none remain:

Run: `grep -n "if root is not None else Path.cwd()" scripts/supskill_state/commands.py`
Expected: no output.

- [ ] **Step 8: Run the integration tests to verify they pass**

Run: `uv run pytest tests/test_store.py -v`
Expected: PASS — including the three linked-worktree tests and every pre-existing store test.

- [ ] **Step 9: Run the full suite and lint**

Run: `uv run pytest && uv run ruff check .`
Expected: all green (test count strictly greater than before). The `render_show`/command tests that chdir to a non-repo `tmp_path` are unaffected: `resolve_root` fast-fails to cwd there.

- [ ] **Step 10: Commit**

```bash
git add scripts/supskill_state/store.py scripts/supskill_state/commands.py tests/test_store.py
git commit -m "feat(SK-111): resolve state from the main root when cwd is a linked worktree

During EXECUTE the conductor isolates into .worktrees/<id> but .supskill/ never
moves, so a supskill-state call from the worktree cwd was refused (no state file)
three times on the playset s5 run. Centralize the repeated cwd resolution into
store.resolve_root: explicit root and main-worktree behavior are unchanged; only
a git linked worktree (--git-dir != --git-common-dir) redirects to the main
root. The deliberate no-upward-search behavior is preserved everywhere else.
(playset s5.)"
```

---

### Task 2: SK-112 — the EXECUTE task reviewer writes findings to a file, not the reply

**Files:**
- Modify: `skills/supskill/SKILL.md` (the EXECUTE drain cycle)
- Test: `tests/test_execute_prose.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: the EXECUTE drain cycle instructs the conductor, when dispatching the task reviewer, to have it write findings to `<scratch>/task-<N>-review-findings.md` and return only a one-line status; the conductor reads that file, never the reply. A tripwire in `tests/test_execute_prose.py` asserts the EXECUTE section carries this instruction.

- [ ] **Step 1: Write the failing prose tripwire**

Add to `tests/test_execute_prose.py` (it already defines `execute_section()`):

```python
def test_the_task_review_dispatch_writes_findings_to_a_file_not_the_reply():
    # SK-112: SDD's task-reviewer prompt returns findings as its final message,
    # which collapsed to a placeholder on the playset s5 run. The conductor must
    # point the reviewer at a file and read that, never the chat reply.
    section = execute_section()
    assert "task-<N>-review-findings.md" in section
    assert "read that file" in section
    assert "never the reply" in section
```

- [ ] **Step 2: Run the tripwire to verify it fails**

Run: `uv run pytest tests/test_execute_prose.py -k "writes_findings_to_a_file" -v`
Expected: FAIL — the EXECUTE section does not yet carry the file-handoff instruction.

- [ ] **Step 3: Add the file-handoff instruction to the EXECUTE drain cycle**

In `skills/supskill/SKILL.md`, in "### The drain", the cycle's step 1 currently reads (the paragraph beginning `1. Record `BASE` (`git rev-parse HEAD`), write the brief, dispatch a fresh`). Immediately **after** that numbered step 1 paragraph (before step 2's `Map what SDD reported…` table), insert this paragraph:

```markdown
   **The task reviewer writes its findings to a file, never to its reply.** SDD's
   task-reviewer prompt returns its findings as its final chat message, and a
   dispatched agent's final message is exactly what collapses to a placeholder
   (the same failure `7dfb0f9` fixed for supskill's own dispatches). So when you
   dispatch the task reviewer, tell it — in addition to SDD's prompt — to write
   its full findings and its two verdicts (spec compliance, task quality) to
   `<scratch>/task-<N>-review-findings.md` and to return only a one-line status.
   You then **read that file** for the verdicts and act on them; you rely on the
   file, **never the reply**. A reviewer that cannot write the file says so in the
   one line it returns, which is loud — a lost finding read as an approval is not.
```

- [ ] **Step 4: Run the tripwire to verify it passes**

Run: `uv run pytest tests/test_execute_prose.py -k "writes_findings_to_a_file" -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite and lint**

Run: `uv run pytest && uv run ruff check .`
Expected: all green. `test_skill_frontmatter.py` checks frontmatter only, so the body edit does not affect it.

- [ ] **Step 6: Commit**

```bash
git add skills/supskill/SKILL.md tests/test_execute_prose.py
git commit -m "feat(SK-112): the EXECUTE task reviewer writes findings to a file, not its reply

On the playset s5 run both task-review dispatches came back as a placeholder
final message (Done./.), and the conductor had to resume the agent and persist
its findings to a file to recover them. supskill already reads the file and never
the reply for its own dispatches (7dfb0f9); the EXECUTE drain now applies the same
discipline to the SDD-composed task review whose prompt body it cannot edit — the
reviewer writes to <scratch>/task-N-review-findings.md and returns one status line.
(playset s5.)"
```

---

## Self-Review

**1. Spec coverage:**
- SK-111 "`supskill-state` refuses when run from a worktree cwd … have `supskill-state` resolve `.supskill/` from the main worktree's root when cwd is a registered linked worktree" → Task 1: `store.resolve_root` + `_linked_worktree_root`, wired through `commands.py`, proven by a CLI-from-worktree-cwd integration test. The narrow rule (only a linked worktree redirects; main worktree / subdir / non-repo unchanged) is enforced by the `--git-dir != --git-common-dir` check and covered by `test_resolve_root_in_the_main_worktree_stays_at_cwd` and `test_resolve_root_falls_back_to_cwd_outside_a_repo`.
- SK-112 "the EXECUTE dispatch should require the task reviewer to write findings to a file … return only a status line" → Task 2: SKILL.md drain-cycle paragraph + tripwire. It reuses supskill's own "read the file, never the reply" framing (`7dfb0f9`) rather than inventing a second mechanism.

**2. Placeholder scan:** every code step shows complete source; every command has expected output. The one replace-all (Task 1 Step 7) names the exact string, the exact replacement, and a grep to confirm zero remain — not a "similar to" hand-wave.

**3. Type consistency:** `resolve_root(root: Path | None = None) -> Path` and `_linked_worktree_root(cwd: Path) -> Path | None` are used at those signatures in `commands.py` (which passes its own `root: Path | None`) and the tests. `_rev_parse_abs(cwd: Path, what: str) -> Path | None` is internal to `store.py`. `store` is already imported in `commands.py`; `dump_state`, `state_path`, `resolve_root`, and `main` are imported by the test at their real names. No `commands.py` entry-point signature changes, so no caller or existing test is affected.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-23-sk111-sk112-worktree-state-and-reviewer-handoff.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
