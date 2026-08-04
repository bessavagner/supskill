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


def guard_conductor_commit(paths: Iterable[str]) -> list[str]:
    """The foreign paths among a set the CONDUCTOR is about to stage (SK-134).

    `foreign_paths` inspects a committed range, which is right for a task's
    implementer: the commits already exist and REVIEW will see them. A conductor
    commit is checked before it lands, so the input is the staged set instead.
    The denylist is shared - the actor that gains the most reach under E10 must
    not be the one the guard exempts.
    """
    return foreign_paths(paths)


def conductor_refusal(foreign: list[str]) -> str:
    """What the conductor reports, verbatim, when its OWN staged set carries foreign state.

    `refusal` names a committed range and tells the operator to reset it; there is
    nothing to reset here, because this runs before the commit. So this names the
    paths, the prefix that caught them, and stops - the conductor's remediable action
    at that seam (`artifact-guard.untracked`, `replan-guard.writeback-uncommitted`)
    does not extend to a path on the denylist, and nothing is recorded.
    """
    if not foreign:
        raise StateError("conductor_refusal() called with no foreign paths; there is nothing to refuse")
    listed = "\n".join(f"    {path}" for path in foreign)
    prefixes = ", ".join(FOREIGN_PREFIXES)
    return (
        "these paths are not the conductor's to commit - they belong to a harness or to "
        "supskill's own state, never to a sprint's deliverables:\n"
        f"{listed}\n"
        f"The denylist is dir-anchored: {prefixes}. This is commit-scope-guard.foreign's shape "
        "reached before the commit rather than after it, so there is nothing to reset - stage "
        "nothing, commit nothing, and relay this with the path and its prefix named.\n"
        "Nothing was recorded: no action row, and the gate this ran before is still open."
    )


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
