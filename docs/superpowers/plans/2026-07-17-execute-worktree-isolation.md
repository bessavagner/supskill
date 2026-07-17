# EXECUTE auto-isolates into a worktree instead of blocking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** EXECUTE's branch check stops blocking cold on `main`/detached-HEAD and instead auto-isolates into a `.worktrees/<branch>` git worktree, carrying the still-uncommitted sprint doc and dev plan into it, so the operator never has to manually `git switch -c` before re-invoking.

**Architecture:** One new pure-Python module, `scripts/supskill_state/worktree.py` (`ensure_worktree`), wired into `cli.py` as a new non-mutating verb, `worktree`, exactly parallel to `plan_guard.head_moved`'s own module-and-verb shape (it shells out to git, reads/writes nothing under `.supskill/`, and is dispatched straight from `cli.py` rather than through `commands.py`). `skills/supskill/SKILL.md`'s EXECUTE branch check gets the smallest possible inline edit — the ladder that derives the default branch is untouched; only the "stop" outcome changes to "isolate and continue" — with the mechanics (branch naming, the script's contract, dispatch-root re-homing, the halt handoff) extracted into a new conductor-facing `references/worktree-notes.md`, the same extraction pattern `references/gate.md` and `references/review-notes.md` already established, because `SKILL.md`'s body is at 479 of its hard 500-line cap with no room for inline detail.

**Tech Stack:** Python ≥3.11 stdlib only (zero runtime deps — `subprocess`, `shutil`, `pathlib`), pytest + ruff as dev deps, managed with `uv`. No new dependencies. `tests/test_worktree.py` is the one test file in this codebase that drives a real, disposable git repo (`tmp_path` + `git init` + one commit) rather than markdown/string parsing — the design's own call, because worktree creation is genuinely a git operation, not a state-file shape.

## Global Constraints

Copied from the design spec (`docs/superpowers/specs/2026-07-17-execute-worktree-isolation-design.md`) and the standing project rules. Every task's requirements implicitly include this section.

- **Tests:** `uv run pytest`. The suite is pure offline except this plan's own new git-repo fixture, which uses only local, no-network git commands (`init`, `config`, `add`, `commit`, `branch`, `worktree add/list`). Baseline at the tip of `main` (`c767a03`): **340 passed in 0.62s**. Every task ends with the full suite green.
- **Lint:** `uv run ruff check` must stay clean. Config is `pyproject.toml` — `line-length = 120`, rules `E,F,I,B,UP`, `src = ["scripts", "tests"]`. Every code block in this plan passes those rules as written: `from __future__ import annotations` where the module needs it, no unused imports, no line over 120 chars.
- **Zero runtime dependencies:** `pyproject.toml`'s `[project] dependencies = []`, enforced by `tests/test_scaffold.py`. Nothing this plan needs a dependency — `subprocess` and `shutil` are stdlib.
- **No AI attribution of any kind in commit messages or bodies** — no `Co-Authored-By`, no "Generated with" line, no mention of Claude/Anthropic/AI. Absolute; overrides any harness default.
- **`worktree` never touches `.supskill/` or `state.json`.** Like `plan-guard`, it is a pure query-and-git-mutate verb: it reads `--branch`/`--artifact` from its own CLI flags (the conductor sources those values from `show --json`, but the verb itself never reads state). `.supskill/state.json` and every `supskill-state`/`supskill-audit` invocation stay anchored at the original repo root for the sprint's entire lifecycle — only the code-writing moves into the worktree.
- **The conductor never creates, switches, or deletes a branch itself outside of the one `worktree` script call.** The same restraint that already keeps `--archive` out of the conductor's hands (design Goals). No opt-out flag — there is nothing to opt out of, since the new behavior strictly improves on today's hard block.
- **The hard 500-line body cap on `skills/supskill/SKILL.md` is binding, with only 21 lines of headroom.** Verified today: the body (everything after the closing `---` of the frontmatter) is **479 lines** (`tests/test_skill_frontmatter.py::test_body_stays_under_500_lines`, cap 500). Task 2's SKILL.md edits are drafted and measured against this constraint below; if your own wording runs longer, move detail into `references/worktree-notes.md` and leave a one-line pointer in `SKILL.md` — do not shorten the load-bearing routing lines. Re-run `uv run pytest tests/test_skill_frontmatter.py::test_body_stays_under_500_lines` after every `SKILL.md` edit, not just at the end of the task.
- **The state CLI is always invoked as `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state`, from the target repo's root.** Unchanged from every prior sprint; `worktree` follows the same convention.
- **Commits:** one per task minimum, TDD evidence first (a failing test run before implementation).
- **Commands:** tests `uv run pytest <path> -v`, lint `uv run ruff check`.

## File Structure

| Path | Task | Responsibility |
|---|---|---|
| `scripts/supskill_state/worktree.py` | 1 (create) | `ensure_worktree` — create-or-reuse the `.worktrees/<branch>` worktree, ensure it's gitignored, sync artifacts into it |
| `scripts/supskill_state/cli.py` | 1 (modify) | the `worktree` subcommand, dispatched straight to `worktree.ensure_worktree` (no `commands.py` hop, like `plan-guard`) |
| `tests/test_worktree.py` | 1 (create) | the module and the CLI verb, against a real temp git repo fixture |
| `README.md` | 1 (modify) | the CLI subcommand list gains `worktree` |
| `skills/supskill/references/worktree-notes.md` | 2 (create) | conductor-facing mechanics: branch naming, the script's contract, dispatch-root re-homing, the halt handoff |
| `skills/supskill/SKILL.md` | 2 (modify) | EXECUTE's branch check (step 1), scratch prep (step 2), read-the-plan (step 3), the dispatch-discipline `BASE`/`review-package`/scratch bullets, and the halt's batch list |
| `tests/test_execute_prose.py` | 2 (modify) | replaces the now-stale "stops before dispatching" tripwire; adds tripwires for the worktree-notes extraction and the dispatch-root re-homing |

---

### Task 1: `worktree.py` module, the `worktree` CLI verb, and its tests

**Files:**
- Create: `scripts/supskill_state/worktree.py`
- Modify: `scripts/supskill_state/cli.py`
- Test: `tests/test_worktree.py` (create)
- Modify: `README.md:89`

**Interfaces:**
- Consumes: `StateError` (`scripts/supskill_state/errors.py`).
- Produces:
  - `ensure_gitignored(root: Path) -> None` — appends `.worktrees/` to `root/.gitignore` if not already covered; never truncates or commits.
  - `ensure_worktree(root: Path, branch: str, artifacts: list[str]) -> tuple[Path, bool]` — the whole verb's logic. Returns `(worktree_path, created)`; `created` is `False` on reuse. Raises `StateError` on an empty `--branch`, a stale registration (git knows the worktree, the directory is gone), a missing artifact, or any failing git command.
  - CLI: `supskill-state worktree --branch <name> [--artifact <path> ...]` — prints `worktree ready at <path> (created|reused)` and exits 0 on success; exits 1 via `main`'s existing `except StateError` handler on any refusal.

**Design decisions this task locks in** (per the design doc, section B/E): the `worktree` verb is dispatched directly from `cli.py` to `worktree.py`, bypassing `commands.py` entirely — it is a git-side-effecting query, not a `state.json` mutator, the same shape `plan-guard` already established (`cli.py`'s `_cmd_plan_guard` calls `plan_guard.head_moved` directly). A registered-but-missing worktree directory is a **refusal**, never a silent recreate (design section E, "Stale worktree registration"). Artifacts are re-copied on every call, including reuse, so a `/clear`-and-resume always sees the freshest sprint doc/dev plan (design section B step 3).

**Executor skills:** `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_worktree.py`:

```python
"""SK-092: EXECUTE auto-isolates into a worktree instead of blocking on branch.

The one test file in this codebase that needs a real, disposable git repo
rather than markdown/string parsing (design doc, "Testing plan") - worktree
creation is genuinely a git operation, not a state-file shape.
"""

import subprocess
from pathlib import Path

import pytest

from supskill_state.errors import StateError
from supskill_state.worktree import ensure_gitignored, ensure_worktree


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def test_fresh_creation_creates_worktree_and_gitignores_it(git_repo):
    path, created = ensure_worktree(git_repo, "s15", [])
    assert created is True
    assert path == git_repo / ".worktrees" / "s15"
    assert path.is_dir()
    assert (path / "README.md").exists()
    assert ".worktrees/" in (git_repo / ".gitignore").read_text(encoding="utf-8")


def test_artifacts_are_copied_into_the_worktree(git_repo):
    (git_repo / "sprint.md").write_text("sprint doc\n", encoding="utf-8")
    (git_repo / "docs").mkdir()
    (git_repo / "docs" / "plan.md").write_text("plan\n", encoding="utf-8")
    path, _ = ensure_worktree(git_repo, "s15", ["sprint.md", "docs/plan.md"])
    assert (path / "sprint.md").read_text(encoding="utf-8") == "sprint doc\n"
    assert (path / "docs" / "plan.md").read_text(encoding="utf-8") == "plan\n"


def test_reuse_does_not_duplicate_creation(git_repo):
    path1, created1 = ensure_worktree(git_repo, "s15", [])
    path2, created2 = ensure_worktree(git_repo, "s15", [])
    assert created1 is True
    assert created2 is False
    assert path1 == path2


def test_reuse_re_copies_artifacts_even_when_unchanged(git_repo):
    (git_repo / "sprint.md").write_text("v1\n", encoding="utf-8")
    ensure_worktree(git_repo, "s15", ["sprint.md"])
    (git_repo / "sprint.md").write_text("v2\n", encoding="utf-8")
    path2, created2 = ensure_worktree(git_repo, "s15", ["sprint.md"])
    assert created2 is False
    assert (path2 / "sprint.md").read_text(encoding="utf-8") == "v2\n"


def test_existing_branch_with_no_worktree_attaches_instead_of_erroring(git_repo):
    _git(git_repo, "branch", "s15")
    path, created = ensure_worktree(git_repo, "s15", [])
    assert created is True
    assert path.is_dir()
    result = subprocess.run(
        ["git", "-C", str(path), "branch", "--show-current"],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == "s15"


def test_stale_worktree_registration_raises_state_error(git_repo):
    path, _ = ensure_worktree(git_repo, "s15", [])
    import shutil
    shutil.rmtree(path)
    with pytest.raises(StateError, match="gone"):
        ensure_worktree(git_repo, "s15", [])


def test_gitignore_already_containing_worktrees_is_not_duplicated(git_repo):
    (git_repo / ".gitignore").write_text(".worktrees/\nnode_modules/\n", encoding="utf-8")
    ensure_worktree(git_repo, "s15", [])
    text = (git_repo / ".gitignore").read_text(encoding="utf-8")
    assert text.count(".worktrees/") == 1


def test_ensure_gitignored_appends_without_a_trailing_newline_in_the_source(git_repo):
    (git_repo / ".gitignore").write_text("node_modules", encoding="utf-8")
    ensure_gitignored(git_repo)
    text = (git_repo / ".gitignore").read_text(encoding="utf-8")
    assert text == "node_modules\n.worktrees/\n"


def test_missing_artifact_raises_state_error(git_repo):
    with pytest.raises(StateError, match="artifact not found"):
        ensure_worktree(git_repo, "s15", ["nope.md"])


def test_empty_branch_raises_state_error(git_repo):
    with pytest.raises(StateError, match="--branch"):
        ensure_worktree(git_repo, "", [])


def test_cli_worktree_prints_created_then_reused(git_repo, monkeypatch, capsys):
    from supskill_state.cli import main

    monkeypatch.chdir(git_repo)
    assert main(["worktree", "--branch", "s15"]) == 0
    assert "worktree ready at" in capsys.readouterr().out
    assert main(["worktree", "--branch", "s15"]) == 0
    assert "reused" in capsys.readouterr().out


def test_cli_worktree_passes_artifacts_through(git_repo, monkeypatch, capsys):
    from supskill_state.cli import main

    (git_repo / "sprint.md").write_text("doc\n", encoding="utf-8")
    monkeypatch.chdir(git_repo)
    assert main(["worktree", "--branch", "s15", "--artifact", "sprint.md"]) == 0
    assert (git_repo / ".worktrees" / "s15" / "sprint.md").read_text(encoding="utf-8") == "doc\n"


def test_cli_worktree_refusal_exits_nonzero(git_repo, monkeypatch, capsys):
    from supskill_state.cli import main

    monkeypatch.chdir(git_repo)
    assert main(["worktree", "--branch", "s15", "--artifact", "missing.md"]) == 1
    assert "refused" in capsys.readouterr().err
```

The final `tests/test_worktree.py` has exactly these thirteen test functions, in this order: `test_fresh_creation_creates_worktree_and_gitignores_it`, `test_artifacts_are_copied_into_the_worktree`, `test_reuse_does_not_duplicate_creation`, `test_reuse_re_copies_artifacts_even_when_unchanged`, `test_existing_branch_with_no_worktree_attaches_instead_of_erroring`, `test_stale_worktree_registration_raises_state_error`, `test_gitignore_already_containing_worktrees_is_not_duplicated`, `test_ensure_gitignored_appends_without_a_trailing_newline_in_the_source`, `test_missing_artifact_raises_state_error`, `test_empty_branch_raises_state_error`, `test_cli_worktree_prints_created_then_reused`, `test_cli_worktree_passes_artifacts_through`, `test_cli_worktree_refusal_exits_nonzero`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_worktree.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'supskill_state.worktree'`.

- [ ] **Step 3: Implement `worktree.py`**

Create `scripts/supskill_state/worktree.py`:

```python
"""EXECUTE auto-isolates into a worktree instead of blocking (SK-092).

The EXECUTE branch check used to stop cold when the current branch was the
repo's default branch or HEAD was detached, naming `git switch -c <branch>` as
the operator's one manual move. This module removes that interruption: it
creates (or reuses) a worktree at `.worktrees/<branch>`, purely additive next
to the operator's own checkout, and syncs the sprint doc / dev plan into it -
both are still-uncommitted working-tree files at EXECUTE time (PLAN's
dispatched agent never commits, and nothing else in SCOPE/REFINE/PLAN runs
`git commit` either), and a plain `git worktree add` checks out a commit, not
working-tree state, so it would silently lose them otherwise.

Design: docs/superpowers/specs/2026-07-17-execute-worktree-isolation-design.md
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .errors import StateError

WORKTREE_ROOT = ".worktrees"


def _run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise StateError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _branch_exists(root: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _worktree_is_registered(root: Path, path: Path) -> bool:
    """True iff `git worktree list` already knows about this exact path."""
    target = path.resolve()
    for line in _run_git(root, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            if Path(line[len("worktree "):]).resolve() == target:
                return True
    return False


def ensure_gitignored(root: Path) -> None:
    """Append `.worktrees/` to .gitignore if not already covered. Never commits."""
    gitignore = root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    entry = f"{WORKTREE_ROOT}/"
    if any(line.strip() in (entry, WORKTREE_ROOT) for line in existing.splitlines()):
        return
    with open(gitignore, "a", encoding="utf-8") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(entry + "\n")


def _copy_artifacts(root: Path, worktree_path: Path, artifacts: list[str]) -> None:
    for artifact in artifacts:
        source = root / artifact
        if not source.is_file():
            raise StateError(f"artifact not found: {artifact}")
        destination = worktree_path / artifact
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def ensure_worktree(root: Path, branch: str, artifacts: list[str]) -> tuple[Path, bool]:
    """Ensure a worktree at `.worktrees/<branch>` exists, with artifacts synced into it.

    Returns (worktree_path, created) - created is False on reuse. Artifacts are
    (re-)copied on every call, even on reuse, so the sprint doc and dev plan stay
    fresh across a `/clear`-and-resume.
    """
    if not branch:
        raise StateError("--branch must not be empty")
    root = root.resolve()  # `-C <root>` plus a relative `path` arg would double-nest otherwise
    ensure_gitignored(root)
    path = root / WORKTREE_ROOT / branch
    created = False
    if _worktree_is_registered(root, path):
        if not path.is_dir():
            raise StateError(
                f"git already knows about a worktree at {path}, but the directory is gone. "
                "Refusing to silently recreate it - if you deleted it on purpose, run "
                "`git worktree prune` yourself first, then retry."
            )
    else:
        if _branch_exists(root, branch):
            _run_git(root, "worktree", "add", str(path), branch)
        else:
            _run_git(root, "worktree", "add", str(path), "-b", branch)
        created = True
    _copy_artifacts(root, path, artifacts)
    return path, created
```

- [ ] **Step 4: Wire the `worktree` verb into `cli.py`**

In `scripts/supskill_state/cli.py`, change the import block at the top:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import commands, plan_guard, worktree
from .errors import StateError
```

Register the subcommand in `build_parser`, right after `_add_plan_guard(subparsers)`:

```python
    _add_advance(subparsers)
    _add_plan_guard(subparsers)
    _add_worktree(subparsers)
    _add_cost(subparsers)
```

Add the pair right after `_cmd_plan_guard`, before `_add_cost`:

```python
def _add_worktree(subparsers) -> None:
    sub = subparsers.add_parser(
        "worktree",
        help="isolate EXECUTE into .worktrees/<branch>, syncing artifacts into it",
    )
    sub.add_argument("--branch", required=True, help="branch name for the worktree")
    sub.add_argument(
        "--artifact",
        action="append",
        default=[],
        dest="artifacts",
        help="a file to copy from the repo root into the worktree; repeat the flag",
    )
    sub.set_defaults(func=_cmd_worktree)


def _cmd_worktree(args) -> int:
    path, created = worktree.ensure_worktree(Path.cwd(), args.branch, args.artifacts)
    status = "created" if created else "reused"
    print(f"worktree ready at {path} ({status})")
    return 0
```

`main`'s existing `except StateError` handler (bottom of the file) already turns any refusal — empty `--branch`, a stale registration, a missing artifact, a failing git command — into exit 1 with `supskill-state: refused: ...` on stderr. No new error handling is needed there.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_worktree.py -v`
Expected: all 13 PASS.

Then run: `uv run pytest -q && uv run ruff check`
Expected: `353 passed` (340 baseline + 13 new), ruff clean.

- [ ] **Step 6: Update the README's subcommand list**

In `README.md`, find:

```
init · show · artifact · gate · block · task · tasks · advance · plan-guard · cost
```

Replace with:

```
init · show · artifact · gate · block · task · tasks · advance · plan-guard · worktree · cost
```

- [ ] **Step 7: Commit**

```bash
git add scripts/supskill_state/worktree.py scripts/supskill_state/cli.py tests/test_worktree.py README.md
git commit -m "feat: EXECUTE auto-isolates into a git worktree instead of blocking on branch (SK-092)"
```

---

### Task 2: SKILL.md's EXECUTE prose — auto-isolate, re-home the dispatch, name the worktree at the halt

**Files:**
- Create: `skills/supskill/references/worktree-notes.md`
- Modify: `skills/supskill/SKILL.md` (EXECUTE section, `### Before the first dispatch`, `### The dispatch discipline`, `### The halt`)
- Test: `tests/test_execute_prose.py` (modify)

**Interfaces:**
- Consumes: `supskill-state worktree --branch <name> --artifact <path> [--artifact <path> ...]` (Task 1) — the exact command line named verbatim in both `SKILL.md` and `worktree-notes.md`.
- Produces: no new code interface — this task is prose plus a new reference doc, verified by tripwire tests exactly like `references/gate.md` and `references/review-notes.md` were.

**Design decision this task locks in** (per the design doc's own framing and the project's established extraction pattern — `references/gate.md`, `references/review-notes.md`, `references/replan-shapes.md` all exist for the same reason): `SKILL.md`'s body is at 479 of its hard 500-line cap. Every edit below is deliberately the smallest inline change that still states the load-bearing routing (when the worktree fires, what the dispatch root means, that `state.json` never moves) — full mechanics live in `references/worktree-notes.md`, a conductor-facing doc like `gate.md`, never sent to any dispatched subagent (it is not in `test_prompt_templates.py`'s `TEMPLATES` tuple, and must not be added to it).

**Executor skills:** `superpowers:writing-skills`.

- [ ] **Step 1: Read the current EXECUTE section and confirm the line budget**

Run:

```bash
python3 -c "
text = open('skills/supskill/SKILL.md', encoding='utf-8').read()
closing = text.index('\n---\n', 4)
body = text[closing + len('\n---\n'):].splitlines()
print('body lines:', len(body))
"
```

Expected: `body lines: 479`. If it prints anything else, someone else has edited `SKILL.md` since this plan was written — re-derive the line numbers below from the live file (search by the quoted text, not by line number) before proceeding.

- [ ] **Step 2: Create `skills/supskill/references/worktree-notes.md`**

```markdown
# Auto-isolating EXECUTE into a worktree

Extracted from **The EXECUTE stage**'s branch check to keep `SKILL.md` under
its line cap. Referenced from step 1 (the branch check) and from **The halt**.

## When this fires

Only when `git rev-parse --abbrev-ref HEAD` names the repo's default branch
(from the same derivation ladder step 1 already runs), or the literal `HEAD`
(detached). Any other branch is unchanged: the dispatch root is the repo
root, no worktree, no script call — this file has nothing to say about that
case.

## Computing the branch name

`sprint.branch` from `show --json`, if the operator set one at `init
--branch`. Otherwise the normalized sprint id: lowercase `sprint.id`, the
same normalization `sprint.scratch` already carries (e.g. `S15` → `s15`) —
never invent a different rule.

## The script call

    ${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state worktree --branch <branch-name> \
      --artifact <sprint_doc> --artifact <dev_plan>

`<sprint_doc>` / `<dev_plan>` are `artifacts.sprint_doc` / `artifacts.dev_plan`
from `show --json`, whichever are non-null. Both are **uncommitted**
working-tree files at this point — PLAN's dispatched agent never commits — so
the script copies them into the worktree itself. A plain `git worktree add`
checks out a *commit*, not working-tree state, and would silently lose both
otherwise.

The script:
1. Ensures `.worktrees/` is gitignored (appends if missing; never commits the
   edit).
2. Reuses an already-registered worktree at `.worktrees/<branch>` if its
   directory is still on disk; refuses with a `StateError` if git knows about
   it but the directory is gone (never silently recreates over lost state).
3. Otherwise creates one — attaching to the branch if it already exists (an
   operator who ran a manual `git switch -c`/`branch` before this landed),
   else creating both branch and worktree fresh, from current HEAD.
4. (Re-)copies every `--artifact` on every call, including reuse, so the two
   documents stay fresh across a `/clear`-and-resume.
5. Prints exactly one line: `worktree ready at <path> (created|reused)`.

If the script raises, report its refusal verbatim and stop — the same rule as
every other CLI refusal in this skill. There is no silent fallback to
dispatching on the default branch.

## The dispatch root, for the rest of this run

`<path>` from that one line **is the dispatch root** until this EXECUTE run
ends. Everything that writes code or scratch state runs against it:

- every SDD dispatch's `Work from:` line names it, never an assumed repo root
- `sdd-workspace` and `mkdir -p <scratch>` (step 2) run there
- `task-brief` reads `<dev_plan>` from its synced copy there
- `git rev-parse HEAD` (recording `BASE`) and `review-package` (per-task and
  final) run as `git -C <dispatch-root> ...`

**What never moves:** `.supskill/state.json` and every `supskill-state` /
`supskill-audit` call stay anchored at the **original repo root**, worktree or
not, for the sprint's entire lifecycle. Only the code-writing was ever the
thing needing isolation.

## At the halt

Name the worktree's path and branch explicitly in the halt report, so the
operator can apply the same merge/PR/keep/discard choice — and worktree
cleanup — they would use for any other branch. EXECUTE never auto-merges,
auto-PRs, or auto-cleans a worktree it created; that decision is the
operator's alone, exactly like every other branch-lifecycle call in this
codebase.
```

- [ ] **Step 3: Rewrite the branch check (step 1) in `SKILL.md`**

Find this exact block (the last paragraph of `### Before the first dispatch — four checks, in this order`'s item 1):

```
1. **The branch check.** Derive the default branch, never assume it: it is what
   `git symbolic-ref --short refs/remotes/origin/HEAD` names with `origin/` stripped.
   **If that command fails or prints nothing** — `origin/HEAD` is unset in any repo not
   created by `git clone` — use `git config --get init.defaultBranch`; if that is unset
   too, take whichever of `origin/main` / `origin/master`
   `git rev-parse --verify --quiet` resolves, and if neither or both resolve, that is a
   **blocker**: the ladder never ends in a `main` guess. Then run
   `git rev-parse --abbrev-ref HEAD`. If that is the default branch, **stop before
   dispatching anything**: report that EXECUTE writes commits and will not write them to
   the default branch, and name `git switch -c <branch>` as the operator's move. If it
   returns the literal `HEAD`, you are on a **detached HEAD**: stop exactly the same way,
   and name the same move. Do not create, switch, or delete a branch yourself — the same
   restraint that keeps `--archive` out of your hands.
```

Replace it with:

```
1. **The branch check.** Derive the default branch, never assume it: it is what
   `git symbolic-ref --short refs/remotes/origin/HEAD` names with `origin/` stripped.
   **If that command fails or prints nothing** — `origin/HEAD` is unset in any repo not
   created by `git clone` — use `git config --get init.defaultBranch`; if that is unset
   too, take whichever of `origin/main` / `origin/master`
   `git rev-parse --verify --quiet` resolves, and if neither or both resolve, that is a
   **blocker**: the ladder never ends in a `main` guess. Then run
   `git rev-parse --abbrev-ref HEAD`. Not the default branch, and not the literal `HEAD`
   (detached) → the **dispatch root** is the repo root; go to check 2. Otherwise → do not
   stop: isolate into a worktree and set the dispatch root to its path, per
   [references/worktree-notes.md](references/worktree-notes.md). Do not create, switch,
   or delete a branch yourself outside of that one script call — the same restraint that
   keeps `--archive` out of your hands.
```

- [ ] **Step 4: Root the scratch prep (step 2) and the plan read (step 3) at the dispatch root**

Find:

```
2. **Prepare the scratch.** Run SDD's `sdd-workspace` script once — it creates
   `.superpowers/sdd/` and writes the self-ignoring `.gitignore` that keeps every
   sprint's scratch out of `git status`. Then `mkdir -p <scratch>`, where
   `<scratch>` is `sprint.scratch` from `show --json`. **Neither is optional.**
   `task-brief` writes its `OUTFILE` with a plain shell redirect and never
   creates the parent, so the first brief dies on a missing directory; and
   passing `OUTFILE` is exactly what skips `sdd-workspace`'s own call, so a
   target repo that does not already ignore `.superpowers/` will let an
   implementer's `git add -A` commit this sprint's briefs and diffs.
3. **Read the plan.** `artifacts.dev_plan` from `show --json` is the plan, and
   the only authority for it. Missing from disk → report that and stop.
```

Replace with:

```
2. **Prepare the scratch.** From the dispatch root, run SDD's `sdd-workspace` script
   once — it creates `.superpowers/sdd/` and writes the self-ignoring `.gitignore`
   that keeps every sprint's scratch out of `git status`. Then `mkdir -p <scratch>`,
   also at the dispatch root, where `<scratch>` is `sprint.scratch` from `show --json`.
   **Neither is optional.** `task-brief` writes its `OUTFILE` with a plain shell
   redirect and never creates the parent, so the first brief dies on a missing
   directory; and passing `OUTFILE` is exactly what skips `sdd-workspace`'s own call,
   so a target repo that does not already ignore `.superpowers/` will let an
   implementer's `git add -A` commit this sprint's briefs and diffs.
3. **Read the plan.** `artifacts.dev_plan` from `show --json` is the plan, and the
   only authority for it — read it from the dispatch root (its synced copy, when a
   worktree is in use). Missing from disk → report that and stop.
```

- [ ] **Step 5: Root the dispatch-discipline bullets (`### The dispatch discipline`) at the dispatch root**

Find:

```
- **Every scratch path is passed explicitly, and derived, never typed**
  (invariant 4). `<scratch>` is `sprint.scratch` from `show --json`:
  - brief: `task-brief <dev_plan> <N> <scratch>/task-<N>-brief.md`
  - report: `<scratch>/task-<N>-report.md` — named after the brief, per SDD's
    File Handoffs rule, so re-reading a task's outcome is one `Read`, never a
    re-dispatch
  - review package: `review-package <BASE> HEAD <scratch>/review-<N>.diff`
- **`BASE` is recorded, never derived.** Before each implementer dispatch, run
  `git rev-parse HEAD` and keep that SHA as the task's `BASE`. **Never `HEAD~1`** — SDD
  says in as many words that it silently drops all but the last commit of a multi-commit
  task. EXECUTE also **produces** the final whole-branch review's package — an output it
  leaves for E6, never an input it consumes (see **The halt**):
  `review-package $(git merge-base <default-branch> HEAD) HEAD <scratch>/review-final.diff`,
  with `<default-branch>` derived exactly as in the branch check.
```

Replace with:

```
- **Every scratch path is passed explicitly, and derived, never typed**
  (invariant 4), all of it relative to the dispatch root established in the branch
  check. `<scratch>` is `sprint.scratch` from `show --json`:
  - brief: `task-brief <dev_plan> <N> <scratch>/task-<N>-brief.md`, `<dev_plan>` read
    from the dispatch root's synced copy
  - report: `<scratch>/task-<N>-report.md` — named after the brief, per SDD's
    File Handoffs rule, so re-reading a task's outcome is one `Read`, never a
    re-dispatch
  - review package: `review-package <BASE> HEAD <scratch>/review-<N>.diff`
  - every implementer dispatch's `Work from:` line names the dispatch root, never an
    assumed repo root
- **`BASE` is recorded, never derived.** Before each implementer dispatch, run
  `git -C <dispatch-root> rev-parse HEAD` and keep that SHA as the task's `BASE`.
  **Never `HEAD~1`** — SDD says in as many words that it silently drops all but the
  last commit of a multi-commit task. EXECUTE also **produces** the final
  whole-branch review's package — an output it leaves for E6, never an input it
  consumes (see **The halt**):
  `review-package $(git -C <dispatch-root> merge-base <default-branch> HEAD) HEAD <scratch>/review-final.diff`,
  run from `<dispatch-root>`, with `<default-branch>` derived exactly as in the
  branch check.
```

- [ ] **Step 6: Name the worktree at the halt (`### The halt`)**

Find the last two lines of the halt's batch list:

```
- **any stale `.superpowers/sdd/progress.md`** found on disk: named once, so the
  operator can delete it.
```

Replace with:

```
- **any stale `.superpowers/sdd/progress.md`** found on disk: named once, so the
  operator can delete it;
- **the dispatch root, if it was a worktree:** its path and branch, named explicitly
  — the operator's merge/PR/keep/discard/cleanup call, exactly like any other branch
  ([references/worktree-notes.md](references/worktree-notes.md)).
```

- [ ] **Step 7: Verify the line cap and grep for the removed phrasing**

Run:

```bash
python3 -c "
text = open('skills/supskill/SKILL.md', encoding='utf-8').read()
closing = text.index('\n---\n', 4)
body = text[closing + len('\n---\n'):].splitlines()
print('body lines:', len(body))
"
grep -n "git switch -c\|will not write them to" skills/supskill/SKILL.md
```

Expected: `body lines:` prints a number **≤ 500** (489 expected — verified by applying this exact diff to a scratch copy of the real file while writing this plan). The `grep` prints nothing — both phrases must be fully gone from `SKILL.md` (they described the old blocking behavior).

- [ ] **Step 8: Update `tests/test_execute_prose.py`**

Find:

```python
def test_the_execute_section_stops_before_dispatching_on_the_default_branch():
    section = execute_section()
    assert "git rev-parse --abbrev-ref HEAD" in section
    assert "git switch -c" in section
```

Replace with:

```python
def test_the_execute_section_auto_isolates_into_a_worktree_instead_of_stopping():
    section = execute_section()
    assert "git rev-parse --abbrev-ref HEAD" in section
    assert "dispatch root" in section
    assert "worktree-notes.md" in section
    assert "EXECUTE writes commits and will not write them to" not in section
    assert "git switch -c" not in section


def test_worktree_notes_exist_and_name_the_script_and_its_refusal():
    text = (SKILL_DIR / "references" / "worktree-notes.md").read_text(encoding="utf-8")
    assert "supskill-state worktree --branch" in text
    assert ".worktrees/" in text
    assert "StateError" in text


def test_worktree_notes_state_the_dispatch_root_rule_and_the_frozen_state_json():
    text = (SKILL_DIR / "references" / "worktree-notes.md").read_text(encoding="utf-8")
    assert "Work from:" in text
    assert "git -C <dispatch-root>" in text
    assert "original repo root" in text


def test_worktree_notes_state_the_halt_handoff_never_auto_merges():
    text = (SKILL_DIR / "references" / "worktree-notes.md").read_text(encoding="utf-8")
    assert "never auto-merges" in text.lower()


def test_the_dispatch_discipline_names_the_dispatch_root_for_base_and_review_package():
    section = execute_section()
    assert "git -C <dispatch-root> rev-parse HEAD" in section
    assert "git -C <dispatch-root> merge-base <default-branch> HEAD" in section


def test_the_halt_names_the_worktree_when_one_was_used():
    section = execute_section()
    assert "worktree-notes.md" in section
    assert "if it was a worktree" in section.lower()
```

Add these six functions anywhere in the file after `execute_section()`'s definition (existing test order otherwise unchanged).

- [ ] **Step 9: Run the tests to verify they pass**

Run: `uv run pytest tests/test_execute_prose.py tests/test_skill_frontmatter.py tests/test_prompt_templates.py -v`
Expected: all PASS — `test_prompt_templates.py` stays green because `worktree-notes.md` was never added to its `TEMPLATES` tuple (it is conductor-facing, not sent to any subagent).

Then run: `uv run pytest -q && uv run ruff check`
Expected: `359 passed` (353 from Task 1 + 6 new here), ruff clean.

- [ ] **Step 10: Commit**

```bash
git add skills/supskill/SKILL.md skills/supskill/references/worktree-notes.md tests/test_execute_prose.py
git commit -m "docs: EXECUTE isolates into a worktree instead of stopping on the default branch (SK-092)"
```

---

## Self-Review

**Spec coverage** (against `docs/superpowers/specs/2026-07-17-execute-worktree-isolation-design.md`):

- Section A (trigger condition, dispatch root naming) → Task 2 Step 3.
- Section B (the `worktree` script, all four numbered behaviors + reuse/attach/stale rules) → Task 1 Step 3 (`worktree.py`), tested by Task 1 Step 1's fixture cases.
- Section C (re-homing scratch prep, `Work from:`, `BASE`, `review-package`, `task-brief`, and the "what never moves" invariant) → Task 2 Steps 4–5, `worktree-notes.md`'s "The dispatch root" section.
- Section D (halt names path/branch, no auto-merge/PR/clean) → Task 2 Step 6, `worktree-notes.md`'s "At the halt" section.
- Section E (creation failure → `StateError`, no silent fallback; stale registration → `StateError`; branch collision → attach, not error; non-blocking case unchanged) → `worktree.py`'s `_run_git`/`ensure_worktree`, tested by Task 1 Step 1's `test_stale_worktree_registration_raises_state_error` and `test_existing_branch_with_no_worktree_attaches_instead_of_erroring`.
- Testing plan's exact case list (fresh creation, reuse, existing-branch-attach, stale-registration, gitignore-not-duplicated) → all present in Task 1's `tests/test_worktree.py`. Prose-fidelity tripwires (script named at the right point, `Work from:`/scratch-prep/review-package reference the dispatch root, halt names the worktree) → Task 2 Step 8's six new tests.
- Non-goals (no always-worktree, no auto-commit-as-checkpoint, no opt-out flag, no auto-merge/PR/clean, no `state.json` schema change) — none of this plan's code paths violate any of them: `ensure_worktree` only runs when the branch check calls it (never unconditionally), `_copy_artifacts` copies files rather than committing, there is no `--no-worktree` flag anywhere in Task 1's CLI wiring, `worktree.py` never invokes `git merge`/`gh pr`/`git worktree remove`, and `model.py`/`SprintInfo` are untouched.

**Placeholder scan:** none of the "No Placeholders" red flags appear anywhere in this plan — every code block, in every step, is complete and runnable as written.

**Type consistency:** `ensure_worktree(root: Path, branch: str, artifacts: list[str]) -> tuple[Path, bool]` is the same signature everywhere it's used — Task 1's tests, Task 1's `cli.py` wiring (`worktree.ensure_worktree(Path.cwd(), args.branch, args.artifacts)`), and Task 2's `worktree-notes.md` prose description ("Returns `(worktree_path, created)`" in spirit, matching the CLI's printed `created|reused`). `ensure_gitignored(root: Path) -> None` matches between its Step 3 definition and its Step 1 test.
