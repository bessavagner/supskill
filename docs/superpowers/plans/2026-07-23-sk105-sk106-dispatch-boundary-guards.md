# SK-105 + SK-106 — Dispatch-boundary guards — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close two "guard at the boundary" holes the playset runs exposed: a dispatched subagent that swept foreign harness state (`.omc/`) into a task commit (SK-105), and a stage that dispatches a `superpowers` skill that did not resolve at runtime and improvises (SK-106).

**Architecture:** Both follow the codebase's established guard shape — a pure module (`scripts/supskill_state/plan_guard.py` / `replan_guard.py` are the templates: a check function plus a `refusal()` string), a thin `cli.py` verb that runs the check and reports to stderr on exit 1, a dedicated test file, and one wiring sentence in `SKILL.md`. Neither guard reads `.supskill/state.json`; both are stateless queries that must work before `init` and after a wipe. SK-105 inspects what a task *committed* (the `BASE..HEAD` range the EXECUTE drain already records `BASE` for); SK-106 verifies the concrete artifacts a still-to-run stage's skill must carry, given base directories the conductor resolves and passes in.

**Tech Stack:** Python 3 (stdlib `argparse`, `subprocess`, `pathlib`), pytest, ruff. No new dependencies.

## Global Constraints

- **Test runner:** `uv run pytest` (offline; no network). Lint `uv run ruff check .`. Both cover `tests/` and `scripts/` per `pyproject.toml`. (`mypy` is referenced by older plans but is not installed or declared in this project — do not run it.)
- **Line length:** ruff caps lines at 100 columns.
- **No AI attribution** in any commit message (repository rule) — no `Co-Authored-By`, no "Generated with" line, no mention of Claude/AI.
- **Commit prefix:** `feat(SK-105):` / `feat(SK-106):` / `test(...)` per the repo's conventional-commit style.
- **The guard shape is fixed** (SK-031/SK-053 invariant): a pure check + a `refusal()` string in a module, a thin CLI verb, a dedicated test. Do not put logic in `cli.py`; do not make either guard read a state file.
- **`main(argv) -> int`** in `cli.py` already maps `StateError` → `supskill-state: refused: <msg>` on stderr and returns 1. Raise `StateError` for malformed input; return the refusal via exit-1-plus-stderr for a *detected* violation (the pattern `_cmd_plan_guard` uses).

---

## File Structure

- `scripts/supskill_state/commit_scope.py` (create) — SK-105: `FOREIGN_PREFIXES`, `foreign_paths()`, `git_changed_paths()`, `refusal()`.
- `scripts/supskill_state/preflight.py` (create) — SK-106: `STAGE_ORDER`, `STAGE_SKILLS`, `SKILL_ARTIFACTS`, `required_skills()`, `unresolved()`, `refusal()`.
- `scripts/supskill_state/cli.py` (modify) — add the `commit-scope-guard` verb (Task 1) and the `preflight` verb (Task 2); import both modules.
- `skills/supskill/SKILL.md` (modify) — Task 1 adds one bullet to "The dispatch discipline"; Task 2 adds one run-checklist step before the dispatch table.
- `tests/test_commit_scope.py` (create) — Task 1 unit + CLI-with-git-repo tests.
- `tests/test_preflight.py` (create) — Task 2 unit + CLI + SKILL.md-prose tripwire tests.

**Task order:** Task 1 (SK-105) and Task 2 (SK-106) are independent — different modules, different CLI verbs, different `SKILL.md` sections. Either can be reviewed and merged alone. Do Task 1 first (self-contained drain-cycle wiring), then Task 2 (run-checklist wiring).

---

### Task 1: SK-105 — refuse a task commit that swept in foreign harness state

**Files:**
- Create: `scripts/supskill_state/commit_scope.py`
- Modify: `scripts/supskill_state/cli.py` (import line 9; `build_parser` at line 30-33; new handler)
- Modify: `skills/supskill/SKILL.md` ("The dispatch discipline — every task, no exceptions")
- Test: `tests/test_commit_scope.py`

**Interfaces:**
- Consumes: `StateError` from `.errors`. `git diff --name-only` (via `subprocess`, mirroring `worktree._run_git`).
- Produces:
  - `commit_scope.FOREIGN_PREFIXES: tuple[str, ...]` — dir-anchored posix prefixes a task commit must never introduce.
  - `commit_scope.foreign_paths(changed_paths: Iterable[str]) -> list[str]` — the subset of changed paths under a foreign prefix, order-preserving and deduped. Pure; no git.
  - `commit_scope.git_changed_paths(root: str, before: str, after: str) -> list[str]` — `git -C <root> diff --name-only <before> <after>` as a path list; raises `StateError` on git failure.
  - `commit_scope.refusal(foreign: list[str], before: str, after: str) -> str` — the verbatim stop message; raises `StateError` if `foreign` is empty.
  - CLI `commit-scope-guard --before <SHA> --after <SHA> [--dir <path>]` — exit 1 + stderr refusal when the range carries foreign state; exit 0 otherwise. `--dir` defaults to `.` (the dispatch root, which may be a worktree).

- [ ] **Step 1: Write the failing unit tests for the pure functions**

Create `tests/test_commit_scope.py`:

```python
"""SK-105: the guard that catches a dispatched agent's `git add -A` sweeping
foreign harness state (`.omc/`) into a task's committed range."""

import subprocess
from pathlib import Path

import pytest

from supskill_state.cli import main
from supskill_state.commit_scope import (
    FOREIGN_PREFIXES,
    foreign_paths,
    refusal,
)
from supskill_state.errors import StateError

BEFORE = "133da28f8f2b7c1a9e5d4c3b2a1908070605f4e3"
AFTER = "aa81d4d0e1f2a3b4c5d6e7f8091a2b3c4d5e6f70"


def test_a_clean_range_has_no_foreign_paths():
    assert foreign_paths(["src/app.py", "tests/test_app.py", "README.md"]) == []


def test_omc_state_is_foreign():
    assert foreign_paths(["src/app.py", ".omc/state.json"]) == [".omc/state.json"]


def test_every_denylisted_prefix_is_caught():
    for prefix in FOREIGN_PREFIXES:
        assert foreign_paths([f"{prefix}x/y.txt"]) == [f"{prefix}x/y.txt"]


def test_a_leading_dot_slash_is_normalized():
    assert foreign_paths(["./.omc/x"]) == [".omc/x"]


def test_a_lookalike_outside_the_dir_is_not_foreign():
    # dir-anchored: `.omcfg/` and a file merely NAMED like the dir are not foreign
    assert foreign_paths([".omcfg/x", "src/.omc_notes.md"]) == []


def test_duplicates_are_collapsed():
    assert foreign_paths([".omc/a", ".omc/a"]) == [".omc/a"]


def test_the_refusal_lists_paths_and_names_the_range_and_the_reset():
    text = refusal([".omc/state.json"], BEFORE, AFTER)
    assert ".omc/state.json" in text
    assert BEFORE in text and AFTER in text
    assert "reset --soft" in text


def test_the_refusal_on_no_paths_raises():
    with pytest.raises(StateError, match="nothing to refuse"):
        refusal([], BEFORE, AFTER)
```

- [ ] **Step 2: Run the unit tests to verify they fail**

Run: `uv run pytest tests/test_commit_scope.py -k "foreign or refusal or denylisted or lookalike or normalized or collapsed" -v`
Expected: collection/import error — `supskill_state.commit_scope` does not exist yet.

- [ ] **Step 3: Create `commit_scope.py` with the pure functions**

Create `scripts/supskill_state/commit_scope.py`:

```python
"""SK-105: refuse a task commit that swept foreign harness state into the range.

EXECUTE dispatches SDD implementers and fix subagents that commit code. An
implementer's `git add -A` stages the *whole* working tree, so a harness's
untracked state — `.omc/` on the playset s1 run — rides into the commit. The
controller caught it by eye and reset; this is the mechanical net that catches
it instead. Same shape as plan_guard.head_moved: a pure check plus a CLI verb
that reports and stops. It inspects what was COMMITTED (the BASE..HEAD range the
drain already records BASE for), not the working tree — a task's commits are the
thing REVIEW and the merge see.

The denylist is foreign *state* a task deliverable can never legitimately carry:
another harness's dir (`.omc/`), SDD's own scratch (`.superpowers/`, normally
git-ignored — belt and suspenders), the conductor's state (`.supskill/`, whose
implementer commits would violate invariant 3), and a machine-local index
(`.codegraph/`). `.claude/` is deliberately absent: a target repo legitimately
tracks `.claude/commands` and agents, so denylisting it would refuse real work.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable

from .errors import StateError

# Dir-anchored posix prefixes a committed task range must never introduce.
FOREIGN_PREFIXES: tuple[str, ...] = (
    ".omc/",
    ".superpowers/",
    ".supskill/",
    ".codegraph/",
)


def _normalize(path: str) -> str:
    path = path.strip()
    while path.startswith("./"):
        path = path[2:]
    return path


def foreign_paths(changed_paths: Iterable[str]) -> list[str]:
    """The changed paths under a foreign-state prefix, in order, deduped.

    `changed_paths` is `git diff --name-only <before> <after>` output, one path
    per element. An empty range (nothing changed) yields [].
    """
    seen: set[str] = set()
    foreign: list[str] = []
    for raw in changed_paths:
        path = _normalize(raw)
        if not path or path in seen:
            continue
        anchored = any(
            path == prefix.rstrip("/") or path.startswith(prefix) for prefix in FOREIGN_PREFIXES
        )
        if anchored:
            seen.add(path)
            foreign.append(path)
    return foreign


def git_changed_paths(root: str, before: str, after: str) -> list[str]:
    """`git -C <root> diff --name-only <before> <after>` as a path list.

    Raises StateError if git fails — an unreadable range is never a silent pass.
    """
    before, after = before.strip(), after.strip()
    result = subprocess.run(
        ["git", "-C", root, "diff", "--name-only", before, after],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        raise StateError(f"git diff --name-only {before} {after} failed: {detail}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def refusal(foreign: list[str], before: str, after: str) -> str:
    """What the conductor reports, verbatim, when a task's commits carry foreign state."""
    if not foreign:
        raise StateError("refusal() called with no foreign paths; there is nothing to refuse")
    listed = "\n".join(f"    {path}" for path in foreign)
    before, after = before.strip(), after.strip()
    return (
        "a dispatched agent's commit swept foreign state into this task's range "
        f"({before}..{after}). A task commit may carry only its own declared files; these "
        "paths belong to a harness or to the conductor, never to a task deliverable:\n"
        f"{listed}\n"
        "This run is stopped so you can reset the task's commits and re-commit only the "
        f"declared files: git -C <dispatch-root> reset --soft {before}, unstage the paths "
        "above, then commit. Nothing was recorded for this task; its status is still open.\n"
        "This guard inspects what was committed, not the working tree; an agent that leaves "
        "foreign state uncommitted walks past it."
    )
```

- [ ] **Step 4: Run the unit tests to verify they pass**

Run: `uv run pytest tests/test_commit_scope.py -k "foreign or refusal or denylisted or lookalike or normalized or collapsed" -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Write the failing CLI integration tests (real git repo)**

Append to `tests/test_commit_scope.py`:

```python
def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _head(root: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


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


def test_cli_passes_a_clean_range(git_repo, capsys):
    before = _head(git_repo)
    (git_repo / "src").mkdir()
    (git_repo / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    _git(git_repo, "add", "src/app.py")
    _git(git_repo, "commit", "-q", "-m", "feat: app")
    after = _head(git_repo)
    code = main(["commit-scope-guard", "--before", before, "--after", after, "--dir", str(git_repo)])
    assert code == 0
    assert "no foreign state" in capsys.readouterr().out


def test_cli_refuses_a_commit_that_swept_in_omc_state(git_repo, capsys):
    before = _head(git_repo)
    (git_repo / ".omc").mkdir()
    (git_repo / ".omc" / "state.json").write_text("{}\n", encoding="utf-8")
    (git_repo / "src.py").write_text("y = 2\n", encoding="utf-8")
    _git(git_repo, "add", "-A")  # the exact footgun: stages the whole tree
    _git(git_repo, "commit", "-q", "-m", "feat: work (and swept .omc/)")
    after = _head(git_repo)
    code = main(["commit-scope-guard", "--before", before, "--after", after, "--dir", str(git_repo)])
    assert code == 1
    assert ".omc/state.json" in capsys.readouterr().err


def test_cli_reports_a_git_failure_on_bogus_shas(git_repo, capsys):
    code = main(["commit-scope-guard", "--before", "deadbeef", "--after", "cafef00d", "--dir", str(git_repo)])
    assert code == 1
    assert "failed" in capsys.readouterr().err


def test_the_guard_needs_no_state_file(git_repo, monkeypatch, capsys):
    # a query, not a verb: it must work before init and after a wipe
    monkeypatch.chdir(git_repo)
    before = _head(git_repo)
    assert main(["commit-scope-guard", "--before", before, "--after", before]) == 0
```

- [ ] **Step 6: Run the CLI tests to verify they fail**

Run: `uv run pytest tests/test_commit_scope.py -k "cli or needs_no_state" -v`
Expected: FAIL — `commit-scope-guard` is an unrecognized argparse command (SystemExit 2).

- [ ] **Step 7: Wire the `commit-scope-guard` verb into `cli.py`**

In `scripts/supskill_state/cli.py`, change the import at line 9 to add `commit_scope`:

```python
from . import commands, commit_scope, config, plan_guard, replan_guard, worktree
```

In `build_parser` (line 30-33 area), add the registration call right after `_add_plan_guard(subparsers)`:

```python
    _add_plan_guard(subparsers)
    _add_commit_scope_guard(subparsers)
```

Add the parser and handler next to `_add_plan_guard` / `_cmd_plan_guard`:

```python
def _add_commit_scope_guard(subparsers) -> None:
    sub = subparsers.add_parser(
        "commit-scope-guard",
        help="did a task's commits (BASE..HEAD) sweep in foreign harness state? exit 1 = refuse",
    )
    sub.add_argument("--before", required=True, help="the task's BASE SHA (rev-parse HEAD before the dispatch)")
    sub.add_argument("--after", required=True, help="HEAD after the task's implementer and fix dispatches")
    sub.add_argument("--dir", default=".", dest="root", help="the dispatch root (repo or worktree); default cwd")
    sub.set_defaults(func=_cmd_commit_scope_guard)


def _cmd_commit_scope_guard(args) -> int:
    changed = commit_scope.git_changed_paths(args.root, args.before, args.after)
    foreign = commit_scope.foreign_paths(changed)
    if foreign:
        print(commit_scope.refusal(foreign, args.before, args.after), file=sys.stderr)
        return 1
    print(f"commit-scope-guard: no foreign state in {args.before.strip()}..{args.after.strip()}")
    return 0
```

- [ ] **Step 8: Run the CLI tests to verify they pass**

Run: `uv run pytest tests/test_commit_scope.py -v`
Expected: PASS (all unit + CLI tests).

- [ ] **Step 9: Write the failing SKILL.md prose tripwire**

Append to `tests/test_commit_scope.py`:

```python
def test_the_execute_dispatch_discipline_names_the_commit_scope_guard():
    skill = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    start = text.index("### The dispatch discipline")
    section = text[start : text.index("\n### ", start + 1)]
    assert "commit-scope-guard" in section
    assert ".omc/" in section  # names the harness state it exists to catch
```

- [ ] **Step 10: Run the tripwire to verify it fails**

Run: `uv run pytest tests/test_commit_scope.py -k "dispatch_discipline_names" -v`
Expected: FAIL — `SKILL.md` does not yet mention `commit-scope-guard`.

- [ ] **Step 11: Wire the guard into the EXECUTE dispatch discipline (SKILL.md)**

In `skills/supskill/SKILL.md`, under "### The dispatch discipline — every task, no exceptions", add this bullet immediately after the `**No dispatched agent runs `supskill-state`**` bullet (the last bullet in that list, ending "…mark its own work done."):

```markdown
- **Scope every task's commits to its own files.** After a task's implementer and
  fix dispatches have committed — before recording any status — run, from the
  dispatch root:
  `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state commit-scope-guard --before <BASE> --after $(git -C <dispatch-root> rev-parse HEAD) --dir <dispatch-root>`
  Exit 1 → **stop.** An implementer's `git add -A` swept a harness's state
  (`.omc/`) or the conductor's own (`.supskill/`) into the commit. Report the
  guard's message verbatim; do not record the task's status — its commit is
  tainted. The remedy is the reset the guard names; this run is stopped for the
  operator, the same restraint as the HEAD guard at PLAN.
```

- [ ] **Step 12: Run the tripwire, the full suite, and lint**

Run: `uv run pytest && uv run ruff check .`
Expected: all green (test count strictly greater than before).

- [ ] **Step 13: Commit**

```bash
git add scripts/supskill_state/commit_scope.py scripts/supskill_state/cli.py skills/supskill/SKILL.md tests/test_commit_scope.py
git commit -m "feat(SK-105): guard a task's commits against foreign harness state

A fix subagent's git add -A swept .omc/ harness state into a task commit on the
playset s1 run; the controller caught it by eye. Add commit-scope-guard: it
inspects the task's BASE..HEAD range and refuses any path under a foreign-state
prefix (.omc/, .superpowers/, .supskill/, .codegraph/). The EXECUTE dispatch
discipline runs it after each task's commits, before recording status. (playset s1.)"
```

---

### Task 2: SK-106 — refuse at run start when a stage's dispatched skill will not resolve

**Files:**
- Create: `scripts/supskill_state/preflight.py`
- Modify: `scripts/supskill_state/cli.py` (import line 9; `build_parser`; new handler)
- Modify: `skills/supskill/SKILL.md` ("The run checklist" — a new step before "## Dispatch table")
- Test: `tests/test_preflight.py`

**Interfaces:**
- Consumes: `StateError` from `.errors`. `Path.is_file()` for artifact existence.
- Produces:
  - `preflight.STAGE_ORDER: tuple[str, ...]` = `("SCOPE", "PLAN", "EXECUTE", "REVIEW")`.
  - `preflight.STAGE_SKILLS: dict[str, tuple[str, ...]]` — the external skill each stage dispatches (SCOPE/REVIEW dispatch none).
  - `preflight.SKILL_ARTIFACTS: dict[str, tuple[str, ...]]` — the files each skill must carry, relative to its base dir.
  - `preflight.required_skills(stage: str) -> tuple[str, ...]` — union over stages from `stage` onward, in order; raises `StateError` on an unknown stage.
  - `preflight.unresolved(stage: str, resolved: dict[str, str]) -> list[tuple[str, str]]` — `(skill, reason)` for each required skill not passed (could not resolve) or passed but missing artifacts.
  - `preflight.refusal(stage: str, problems: list[tuple[str, str]]) -> str` — verbatim stop message; raises `StateError` if `problems` is empty.
  - CLI `preflight --stage <STAGE> [--skill NAME=DIR ...]` — exit 1 + stderr refusal when any required skill is unresolvable; exit 0 otherwise.

- [ ] **Step 1: Write the failing unit tests for the pure functions**

Create `tests/test_preflight.py`:

```python
"""SK-106: refuse at run start when a still-to-run stage would dispatch a
`superpowers` skill that did not resolve at runtime, rather than improvise."""

from pathlib import Path

import pytest

from supskill_state.cli import main
from supskill_state.errors import StateError
from supskill_state.preflight import (
    SKILL_ARTIFACTS,
    refusal,
    required_skills,
    unresolved,
)


def test_required_skills_accumulate_from_the_stage_onward():
    assert required_skills("SCOPE") == ("writing-plans", "subagent-driven-development")
    assert required_skills("PLAN") == ("writing-plans", "subagent-driven-development")
    assert required_skills("EXECUTE") == ("subagent-driven-development",)
    assert required_skills("REVIEW") == ()


def test_an_unknown_stage_raises():
    with pytest.raises(StateError, match="unknown stage"):
        required_skills("BOGUS")


def test_a_required_skill_not_passed_reads_as_unresolvable():
    problems = unresolved("EXECUTE", {})
    assert [skill for skill, _ in problems] == ["subagent-driven-development"]
    assert "could not be resolved" in problems[0][1]


def _plant_skill(base: Path, skill: str) -> Path:
    d = base / skill
    for rel in SKILL_ARTIFACTS[skill]:
        target = d / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")
    return d


def test_a_fully_present_skill_is_resolved(tmp_path):
    sdd = _plant_skill(tmp_path, "subagent-driven-development")
    assert unresolved("EXECUTE", {"subagent-driven-development": str(sdd)}) == []


def test_a_resolved_skill_missing_a_script_is_unresolvable(tmp_path):
    sdd = tmp_path / "sdd"
    (sdd).mkdir()
    (sdd / "SKILL.md").write_text("x", encoding="utf-8")  # present, but no scripts/
    problems = unresolved("EXECUTE", {"subagent-driven-development": str(sdd)})
    assert len(problems) == 1
    assert "task-brief" in problems[0][1]


def test_writing_plans_needs_only_its_skill_md(tmp_path):
    wp = tmp_path / "wp"
    wp.mkdir()
    (wp / "SKILL.md").write_text("x", encoding="utf-8")
    sdd = _plant_skill(tmp_path, "subagent-driven-development")
    resolved = {
        "writing-plans": str(wp),
        "subagent-driven-development": str(sdd),
    }
    assert unresolved("PLAN", resolved) == []


def test_the_refusal_names_the_skill_and_the_install_remedy():
    text = refusal("EXECUTE", [("subagent-driven-development", "could not be resolved")])
    assert "subagent-driven-development" in text
    assert "superpowers" in text
    assert "install" in text.lower()


def test_the_refusal_on_no_problems_raises():
    with pytest.raises(StateError, match="nothing to refuse"):
        refusal("EXECUTE", [])
```

- [ ] **Step 2: Run the unit tests to verify they fail**

Run: `uv run pytest tests/test_preflight.py -k "required_skills or unresolvable or resolved or writing_plans or refusal or unknown_stage" -v`
Expected: collection/import error — `supskill_state.preflight` does not exist yet.

- [ ] **Step 3: Create `preflight.py`**

Create `scripts/supskill_state/preflight.py`:

```python
"""SK-106: refuse at run start when a stage's dispatched skill will not resolve.

supskill composes skills that ship in the `superpowers` plugin: PLAN dispatches
`writing-plans`, EXECUTE dispatches `subagent-driven-development` and invokes its
three scripts by absolute path. plugin.json declares the dependency, and
test_plugin_manifest.py proves the declaration cannot drift — but a *declared*
dependency can still be missing at runtime (install failed, the plugin is
disabled, its marketplace was unreachable). Then a stage dispatches a skill that
does not exist and improvises — the one failure this product exists to prevent.

This is the runtime half. The conductor resolves each still-to-run stage's skills
to a base directory (it loads the skill; the payload's first line is
`Base directory for this skill: <abs path>`) and passes them here. A skill it
could not resolve is simply not passed — and preflight refuses by omission. A
skill it did resolve is checked for the concrete artifacts the stage invokes:
`subagent-driven-development` must carry its three scripts, or EXECUTE dies on a
missing `task-brief` mid-drain. Same shape as the other guards: a pure check
plus a CLI verb that reports and stops. Needs no state file — it is a query.
"""

from __future__ import annotations

from pathlib import Path

from .errors import StateError

STAGE_ORDER: tuple[str, ...] = ("SCOPE", "PLAN", "EXECUTE", "REVIEW")

# The external skill each stage dispatches. SCOPE dispatches none since SK-100
# dropped the pm-execution:sprint-plan dispatch; REVIEW uses supskill's own
# references/review-prompt.md, not an external skill.
STAGE_SKILLS: dict[str, tuple[str, ...]] = {
    "SCOPE": (),
    "PLAN": ("writing-plans",),
    "EXECUTE": ("subagent-driven-development",),
    "REVIEW": (),
}

# The concrete artifacts each skill must carry, relative to its base directory.
# For SDD these are the scripts EXECUTE invokes by absolute path; a missing one
# is a mid-drain crash, so it is a run-start refusal instead.
SKILL_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "writing-plans": ("SKILL.md",),
    "subagent-driven-development": (
        "SKILL.md",
        "scripts/sdd-workspace",
        "scripts/task-brief",
        "scripts/review-package",
    ),
}

_UNRESOLVED = (
    "could not be resolved (not installed, disabled, or its marketplace was unreachable)"
)


def required_skills(stage: str) -> tuple[str, ...]:
    """Every external skill the run may still dispatch from `stage` onward, in order."""
    if stage not in STAGE_ORDER:
        raise StateError(f"unknown stage {stage!r}; expected one of {list(STAGE_ORDER)}")
    skills: list[str] = []
    for later in STAGE_ORDER[STAGE_ORDER.index(stage):]:
        for skill in STAGE_SKILLS[later]:
            if skill not in skills:
                skills.append(skill)
    return tuple(skills)


def unresolved(stage: str, resolved: dict[str, str]) -> list[tuple[str, str]]:
    """(skill, reason) for every required skill that will not resolve.

    `resolved` maps a skill name to the base directory the conductor resolved it
    to. A required skill absent from `resolved` is one the conductor could not
    resolve at all (missing/disabled). A resolved skill missing an expected
    artifact names the missing paths.
    """
    problems: list[tuple[str, str]] = []
    for skill in required_skills(stage):
        base = resolved.get(skill)
        if base is None:
            problems.append((skill, _UNRESOLVED))
            continue
        missing = [rel for rel in SKILL_ARTIFACTS[skill] if not (Path(base) / rel).is_file()]
        if missing:
            problems.append((skill, f"resolved to {base} but is missing: {', '.join(missing)}"))
    return problems


def refusal(stage: str, problems: list[tuple[str, str]]) -> str:
    """What the conductor reports, verbatim, when a required skill will not resolve."""
    if not problems:
        raise StateError("refusal() called with no problems; there is nothing to refuse")
    listed = "\n".join(f"    {skill}: {reason}" for skill, reason in problems)
    return (
        f"a skill a stage from {stage} onward will dispatch does not resolve at run start:\n"
        f"{listed}\n"
        "supskill dispatches these from the `superpowers` plugin (claude-plugins-official). "
        "Install or enable it before running, e.g. "
        "`claude plugin install superpowers@claude-plugins-official`.\n"
        "This run is stopped before the first dispatch: a stage that cannot load the skill it "
        "dispatches improvises, which is the one failure this conductor exists to prevent."
    )
```

- [ ] **Step 4: Run the unit tests to verify they pass**

Run: `uv run pytest tests/test_preflight.py -k "required_skills or unresolvable or resolved or writing_plans or refusal or unknown_stage" -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Write the failing CLI tests**

Append to `tests/test_preflight.py`:

```python
def test_cli_passes_when_every_required_skill_resolves(tmp_path, capsys):
    sdd = _plant_skill(tmp_path, "subagent-driven-development")
    code = main(["preflight", "--stage", "EXECUTE", "--skill", f"subagent-driven-development={sdd}"])
    assert code == 0
    assert "resolves" in capsys.readouterr().out


def test_cli_refuses_a_required_skill_that_was_not_resolved(capsys):
    # --stage EXECUTE requires SDD; passing no --skill means the conductor could not resolve it
    code = main(["preflight", "--stage", "EXECUTE"])
    assert code == 1
    err = capsys.readouterr().err
    assert "subagent-driven-development" in err
    assert "superpowers" in err


def test_cli_rejects_a_malformed_skill_argument(capsys):
    code = main(["preflight", "--stage", "EXECUTE", "--skill", "no-equals-sign"])
    assert code == 1
    assert "NAME=DIR" in capsys.readouterr().err


def test_cli_preflight_needs_no_state_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["preflight", "--stage", "REVIEW"]) == 0  # REVIEW dispatches no external skill
```

- [ ] **Step 6: Run the CLI tests to verify they fail**

Run: `uv run pytest tests/test_preflight.py -k "cli or needs_no_state" -v`
Expected: FAIL — `preflight` is an unrecognized argparse command (SystemExit 2).

- [ ] **Step 7: Wire the `preflight` verb into `cli.py`**

In `scripts/supskill_state/cli.py`, update the import at line 9 so it also imports `preflight`. If Task 1 already added `commit_scope`, the line reads:

```python
from . import commands, commit_scope, config, plan_guard, preflight, replan_guard, worktree
```

(If Task 1 has not landed yet, add `preflight` to whatever the current line is — the token list is alphabetical after `commands`.)

In `build_parser`, add the registration after `_add_replan_guard(subparsers)`:

```python
    _add_replan_guard(subparsers)
    _add_preflight(subparsers)
```

Add the parser and handler (place them next to `_add_replan_guard` / `_cmd_replan_guard`):

```python
def _add_preflight(subparsers) -> None:
    sub = subparsers.add_parser(
        "preflight",
        help="refuse at run start if a still-to-run stage's dispatched skill will not resolve",
    )
    sub.add_argument("--stage", required=True, help="current stage from show --json (SCOPE|PLAN|EXECUTE|REVIEW)")
    sub.add_argument(
        "--skill",
        action="append",
        default=[],
        dest="skills",
        metavar="NAME=DIR",
        help="a resolved skill as name=base-dir; repeat the flag. Omit one you could not resolve.",
    )
    sub.set_defaults(func=_cmd_preflight)


def _cmd_preflight(args) -> int:
    resolved: dict[str, str] = {}
    for item in args.skills:
        name, sep, base = item.partition("=")
        if not sep or not name or not base:
            raise StateError(f"--skill expects NAME=DIR, got {item!r}")
        resolved[name] = base
    problems = preflight.unresolved(args.stage, resolved)
    if problems:
        print(preflight.refusal(args.stage, problems), file=sys.stderr)
        return 1
    print(f"preflight: every skill the stages from {args.stage} onward dispatch resolves")
    return 0
```

Note: `preflight.unresolved` raises `StateError` on an unknown `--stage`, which `main` already maps to exit 1 with a "refused:" message — no extra handling needed.

- [ ] **Step 8: Run the CLI tests to verify they pass**

Run: `uv run pytest tests/test_preflight.py -v`
Expected: PASS (all unit + CLI tests).

- [ ] **Step 9: Write the failing run-checklist prose tripwire**

Append to `tests/test_preflight.py`:

```python
def test_the_run_checklist_preflights_before_the_dispatch_table():
    skill = (Path(__file__).resolve().parent.parent / "skills" / "supskill" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "supskill-state preflight --stage" in skill
    # the refusal must be reached BEFORE the conductor dispatches on stage
    assert skill.index("preflight --stage") < skill.index("## Dispatch table")
```

- [ ] **Step 10: Run the tripwire to verify it fails**

Run: `uv run pytest tests/test_preflight.py -k "run_checklist_preflights" -v`
Expected: FAIL — `SKILL.md` does not yet mention `preflight`.

- [ ] **Step 11: Add the preflight step to the run checklist (SKILL.md)**

In `skills/supskill/SKILL.md`, "## The run checklist", insert a new numbered step **between** step 4 ("Report the resume surface", which ends "…consult no memory of any prior conversation.") and the current step 5 ("Dispatch on `stage`"). Renumber the current step 5 to 6. The inserted step 5:

```markdown
5. **Preflight the skills the remaining stages dispatch.** Before dispatching,
   confirm every external skill a stage from the current `stage` onward will
   dispatch actually resolves — a declared dependency can still be missing,
   disabled, or its marketplace unreachable, and a stage that cannot load the
   skill it dispatches improvises. For each required skill (PLAN dispatches
   `superpowers:writing-plans`; EXECUTE dispatches
   `superpowers:subagent-driven-development`), resolve its base directory by
   loading the skill — its payload's first line is
   `Base directory for this skill: <abs path>`. A skill that will not load at all
   is already the refusal: report it and stop. Then run, passing each resolved
   skill as `name=<base-dir>`:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state preflight --stage <stage> --skill writing-plans=<dir> --skill subagent-driven-development=<dir>`
   (pass only the skills the remaining stages need; omit any you could not
   resolve, and the guard refuses by omission). Exit 1 → report the guard's
   message verbatim and stop; do not dispatch. Exit 0 → continue at step 6.
```

Then change the current step 5 heading from `5. **Dispatch on `stage`.**` to `6. **Dispatch on `stage`.**`.

- [ ] **Step 12: Run the tripwire, the full suite, and lint**

Run: `uv run pytest && uv run ruff check .`
Expected: all green (test count strictly greater than before). `test_run_matrix.py` asserts CLI behavior, not the checklist numbering, so the renumber does not affect it.

- [ ] **Step 13: Commit**

```bash
git add scripts/supskill_state/preflight.py scripts/supskill_state/cli.py skills/supskill/SKILL.md tests/test_preflight.py
git commit -m "feat(SK-106): preflight that a stage's dispatched skills resolve at run start

A declared superpowers dependency can still be missing, disabled, or its
marketplace unreachable at runtime; the stage then dispatches a skill that does
not exist and improvises. Add a preflight verb: given the base dirs the conductor
resolved for each still-to-run stage's skills, it refuses when a required skill
is absent or missing the scripts EXECUTE invokes. The run checklist runs it before
the first dispatch. (both playset runs, by construction.)"
```

---

## Self-Review

**1. Spec coverage:**
- SK-105 "a dispatched subagent must not be able to stage the whole working tree — scope its commits to its declared files, or guard foreign state at the dispatch boundary" → Task 1: `commit-scope-guard` inspects `BASE..HEAD` and refuses foreign-state prefixes, wired into the EXECUTE dispatch discipline. The finding names `.omc/` specifically; it is the first entry in `FOREIGN_PREFIXES` and is asserted in both the CLI test and the prose tripwire.
- SK-106 "Runtime preflight that the dispatched skills resolve … Refuse at run start when a required skill is unresolvable, the way playset's own PLS-040 refuses on a missing binary" → Task 2: `preflight` refuses at run start (a new checklist step before the dispatch table) when a required skill is unresolved-by-omission or missing its invocable scripts. The PLS-040 analogy (a `shutil.which`-style existence refusal) is realized as `Path.is_file()` checks over the concrete artifacts.
- Both are cross-checked against the existing `test_plugin_manifest.py` (the *static* declaration half) — SK-106 is explicitly the *runtime* complement, and the plan does not duplicate the declaration assertions.

**2. Placeholder scan:** every code step shows complete source; every command has expected output. No "TBD"/"add validation"/"similar to Task N". The one cross-task note (Task 2's import line depending on whether Task 1 landed) is stated explicitly with both forms, not left implicit.

**3. Type consistency:** `foreign_paths(Iterable[str]) -> list[str]`, `git_changed_paths(str, str, str) -> list[str]`, `refusal(list[str], str, str) -> str` (Task 1) and `required_skills(str) -> tuple[str, ...]`, `unresolved(str, dict[str, str]) -> list[tuple[str, str]]`, `refusal(str, list[tuple[str, str]]) -> str` (Task 2) are each used at their defined signatures in the CLI handlers and tests. `main(argv) -> int` is unchanged. Both modules import only `StateError` (and stdlib), matching `plan_guard.py` / `replan_guard.py`. The `--dir`/`--skill` arg `dest` names (`root`, `skills`) match their handler reads.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-23-sk105-sk106-dispatch-boundary-guards.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
