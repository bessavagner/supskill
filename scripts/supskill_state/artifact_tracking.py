"""SK-117: name the recorded artifacts git does not track, before Gate 3.

SCOPE and PLAN derive their output paths, write the files and record them as
artifacts - and nothing stages them and no stage tells the operator to. So the
two documents that authorize a sprint sit untracked while the code they
authorize is committed. playset's reviewers raised it at s1 and again at s2
("the plan a branch implements is not in the branch"); ledgerus needed a hand
commit after s6. Three occurrences, two projects, every one surfaced by a reader
rather than by a mechanism.

Report, never stage - in this module. It asks git one read-only question and
refuses; it creates no branch, stages nothing and commits nothing. What happens
after the refusal is the conductor's business, not this module's: under E10
`artifact-guard.untracked` is a *remediable* stop (`stop_classes.py`), so the
conductor checks the named paths against the conductor-commit denylist, commits
exactly them, and records that commit to `actions.jsonl`. The distinction
matters because this refusal is relayed verbatim - it is a remediable stop's
report, not a refusal that hands the work back to the operator, and it must not
claim supskill will never touch the repo when at this one seam it now does.

The ceiling, stated here because it will be oversold otherwise: a repo that
deliberately git-ignores its sprint docs refuses here every time, and there is
no bypass flag - the way past a refusal in this package is to change the thing
it names, never the guard. And a tracked-but-stale doc passes: this asks whether
git knows the file, not whether its contents match the sprint.
"""

from __future__ import annotations

import os
import subprocess

from .errors import StateError


def _normalize(path: str, root: str | None = None) -> str:
    """A recorded path in git's own comparison frame, not the frame it was typed in.

    `git ls-files` prints the canonical relative form regardless of how a pathspec
    was written - `docs//x.md`, `docs/../docs/x.md` and an absolute path all resolve
    to the same tracked file. Comparing that canonical output against a raw recorded
    string false-refuses a genuinely tracked artifact, so this collapses the recorded
    string into the same frame before the comparison ever happens: `os.path.normpath`
    resolves the redundant separators and internal `..`, and an absolute path that
    lands under `root` is rewritten relative to it. An absolute path outside `root`,
    or a `..` that escapes it, is left alone - `git_tracked` already turns that into a
    loud StateError rather than a silent pass, and this function never overrides that.
    """
    path = path.strip()
    if not path:
        return ""
    normalized = os.path.normpath(path)
    if root is not None and os.path.isabs(normalized):
        relative = os.path.relpath(normalized, os.path.normpath(root))
        if relative != os.pardir and not relative.startswith(os.pardir + os.sep):
            normalized = relative
    return normalized


def git_tracked(root: str, paths: list[str]) -> set[str]:
    """The subset of `paths` git tracks, as `git ls-files` names them.

    Raises StateError if git fails - an unanswerable question is never a silent
    pass. An empty `paths` asks git nothing and returns the empty set.
    """
    if not paths:
        return set()
    result = subprocess.run(
        ["git", "-C", root, "ls-files", "--", *paths],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        raise StateError(f"git ls-files failed in {root}: {detail}")
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def untracked(paths: list[str], tracked: set[str], root: str | None = None) -> list[str]:
    """The recorded paths git does not track, in order, deduped.

    `tracked` is `git ls-files`' canonical output (see `git_tracked`); `root` lets a
    recorded path that was written as an absolute path under the repo normalize to
    that same canonical form before comparison. Omit `root` only when every path is
    already relative and canonically shaped, e.g. in a pure unit test.
    """
    seen: set[str] = set()
    missing: list[str] = []
    for raw in paths:
        path = _normalize(raw, root)
        if not path or path in seen:
            continue
        seen.add(path)
        if path not in tracked:
            missing.append(path)
    return missing


def refusal(missing: list[str]) -> str:
    """What the conductor reports, verbatim, when a recorded artifact is untracked."""
    if not missing:
        raise StateError(
            "refusal() called with no untracked artifacts; there is nothing to refuse"
        )
    listed = "\n".join(f"    {path}" for path in missing)
    return (
        "this sprint's recorded artifacts are not tracked by git, so the documents that "
        "authorize this work are not in the branch that implements it:\n"
        f"{listed}\n"
        "Gate 3 asks the operator to rule on a sprint; a reader who comes to this branch "
        "later gets the code and not the plan it was held to.\n"
        "This is reported and never fixed here: this guard asks git one read-only question "
        "and stages nothing. It is artifact-guard.untracked, a remediable stop: the conductor "
        "checks these paths against the conductor-commit denylist, commits exactly them, and "
        "records that commit with `action --stop artifact-guard.untracked`. Outside a supskill "
        "run, stage and commit the paths above yourself, then re-run this stage.\n"
        "Nothing was recorded by this guard and no gate was called: G3 is still open.\n"
        "This asks whether git knows the file, not whether its contents still match the "
        "sprint; a tracked-but-stale doc walks past it."
    )
