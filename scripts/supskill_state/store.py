"""Reading and writing supskill state on disk.

state.json writes are atomic (same-directory temp + os.replace): state.json is
the resume mechanism for a disposable conductor (invariant 5), so a process
killed mid-write must leave the previous valid file, never a truncated one.

The .jsonl audit logs are append-only, structurally: this module only ever
opens them with mode "a" and nothing here can truncate or rewrite them.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .errors import StateError
from .model import State, dumps_state, loads_state

SUPSKILL_DIR = ".supskill"


def supskill_dir(root: Path | None = None) -> Path:
    return (root or Path.cwd()) / SUPSKILL_DIR


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


def state_path(root: Path | None = None) -> Path:
    return supskill_dir(root) / "state.json"


def gates_path(root: Path | None = None) -> Path:
    return supskill_dir(root) / "gates.jsonl"


def runs_dir(root: Path | None = None) -> Path:
    return supskill_dir(root) / "runs"


def load_state(path: Path) -> State:
    if not path.exists():
        raise StateError(f"no state file at {path} - run 'supskill-state init' first")
    return loads_state(path.read_text(encoding="utf-8"))


def dump_state(state: State, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(dumps_state(state))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def append_jsonl(path: Path, record: dict) -> None:
    """Append one record. Opens in append mode only - never truncates or rewrites."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_json_config(path: Path, data: dict) -> None:
    """Write a JSON configuration file (e.g., .supskill/config.json).

    Unlike dump_state, config files are not part of the sprint resume mechanism,
    so we write directly without temp-file atomicity.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()  # noqa: UP017


def require_aware_utc_iso(value: str, where: str) -> None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise StateError(f"{where}: not an ISO-8601 timestamp: {value!r}") from error
    if parsed.utcoffset() != timedelta(0):
        raise StateError(f"{where}: timestamps must be timezone-aware UTC, got {value!r}")
