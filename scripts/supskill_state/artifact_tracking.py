"""SK-117: name the recorded artifacts git does not track, before Gate 3.

SCOPE and PLAN derive their output paths, write the files and record them as
artifacts - and nothing stages them and no stage tells the operator to. So the
two documents that authorize a sprint sit untracked while the code they
authorize is committed. playset's reviewers raised it at s1 and again at s2
("the plan a branch implements is not in the branch"); ledgerus needed a hand
commit after s6. Three occurrences, two projects, every one surfaced by a reader
rather than by a mechanism.

Report, never stage. supskill runs no git command on the operator's behalf that
changes the repo - it will not create, switch or delete a branch, and it will
not `git add`. This module asks git one read-only question and refuses; the
commit stays the operator's, which is the same posture EXECUTE's branch check
already states.

The ceiling, stated here because it will be oversold otherwise: a repo that
deliberately git-ignores its sprint docs refuses here every time, and there is
no bypass flag - the way past a refusal in this package is to change the thing
it names, never the guard. And a tracked-but-stale doc passes: this asks whether
git knows the file, not whether its contents match the sprint.
"""

from __future__ import annotations

import subprocess

from .errors import StateError


def _normalize(path: str) -> str:
    path = path.strip()
    while path.startswith("./"):
        path = path[2:]
    return path


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


def untracked(paths: list[str], tracked: set[str]) -> list[str]:
    """The recorded paths git does not track, in order, deduped."""
    seen: set[str] = set()
    missing: list[str] = []
    for raw in paths:
        path = _normalize(raw)
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
        "This is reported and never fixed here: supskill runs no git command that changes "
        "your repo. Stage and commit the paths above yourself, then re-run this stage.\n"
        "Nothing was recorded and no gate was called: G3 is still open.\n"
        "This asks whether git knows the file, not whether its contents still match the "
        "sprint; a tracked-but-stale doc walks past it."
    )
