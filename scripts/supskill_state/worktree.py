"""EXECUTE auto-isolates into a worktree instead of blocking (SK-092).

The EXECUTE branch check used to stop cold when the current branch was the
repo's default branch or HEAD was detached, naming `git switch -c <branch>` as
the operator's one manual move. This module removes that interruption: it
creates (or reuses) a worktree at `.worktrees/<branch>`, purely additive next
to the operator's own checkout, and syncs the sprint doc / dev plan into it -
both are still-uncommitted working-tree files at EXECUTE time (PLAN's
dispatched agent never commits, and nothing else in SCOPE/PLAN runs
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
