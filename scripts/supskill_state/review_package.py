"""SK-104: is the recorded review package still this branch? (the guard)

EXECUTE's last act is to leave `<scratch>/review-final.diff` on disk for REVIEW to
read, and then the run STOPS - REVIEW is the next `/supskill run` invocation. On
playset s1, out-of-band commits landed in that gap, the diff no longer matched the
branch, and nothing checked: only the conductor's judgment caught it and
regenerated. PAR handed a diff that is not the branch returns a clean review of the
wrong code, which is the most expensive way this product can fail, because it fails
quietly and at the one gate that is irreversible.

Refuse, never regenerate. This is `artifact_tracking`'s posture: the guard reports
and the operator acts, and the way past a refusal in this package is to change the
thing it names. The refusal prints the exact `review-package` command.

Because EXECUTE and REVIEW are separate invocations, the package's HEAD cannot live
in the conductor's memory across the boundary (invariant 5). It is recorded to
`runs/<id>/package.jsonl` - an append-only trail, so the schema does not move.

The ceiling: this compares SHAs. A package regenerated at the right HEAD but written
from the wrong base, or a diff hand-edited after the fact, walks past it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from . import store
from .errors import StateError
from .scratch import normalize_sprint_id


def is_stale(recorded_head: str, current_head: str) -> bool:
    """Has HEAD moved since the package was cut?

    An empty or whitespace-only recorded head is stale: missing evidence is never
    read as freshness. Surrounding whitespace is stripped from both sides first, so
    a SHA captured with a trailing newline does not false-refuse.
    """
    recorded = (recorded_head or "").strip()
    if not recorded:
        return True
    return recorded != (current_head or "").strip()


def git_head(root: str) -> str:
    """`git rev-parse HEAD` in `root`. Raises rather than guessing (read-only)."""
    result = subprocess.run(
        ["git", "-C", root, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        raise StateError(f"git rev-parse HEAD failed in {root}: {detail}")
    return result.stdout.strip()


def package_path(root: Path, sprint_id: str) -> Path:
    return store.runs_dir(Path(root)) / normalize_sprint_id(sprint_id) / "package.jsonl"


def dispatch_root_for(root: Path, record: dict) -> Path:
    """Where `review-guard` should rev-parse HEAD: the package's own dispatch root.

    SK-104 fix: EXECUTE isolates into a worktree (SK-111), and `.supskill/` never
    moves - so a package cut in `.worktrees/<branch>` records `dispatch_root` and this
    reads it back rather than guessing. That mirrors this repo's own rule that a
    recorded artifact is the only authority anything downstream reads (SK-114); a
    `--dispatch-root` flag on the guard itself would repeat the mistake SK-114 fixed.

    A relative `dispatch_root` resolves against `root` (the state root), so
    `.worktrees/s7` works regardless of which directory `review-guard` was invoked
    from. Absent, blank, or non-string `dispatch_root` - an older record, or the
    non-worktree case where dispatch root and state root are the same - falls back to
    `root` unchanged.
    """
    raw = record.get("dispatch_root")
    if not isinstance(raw, str) or not raw.strip():
        return Path(root)
    candidate = Path(raw.strip())
    return candidate if candidate.is_absolute() else Path(root) / candidate


def last_record(root: Path, sprint_id: str) -> dict | None:
    """The most recently recorded package, or None if EXECUTE never recorded one.

    A crash-torn or malformed tail line is skipped, the same rule `show` applies to
    gates.jsonl: a torn trail must not take the guard down.
    """
    path = package_path(root, sprint_id)
    if not path.exists():
        return None
    found: dict | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            found = record
    return found


def missing_file_refusal(record: dict, dispatch_root: Path) -> str:
    """What the conductor reports when the recorded package names a diff that is
    not on disk (SK-104 Critical fix, final review of feat/e9-gate3-inputs).

    `_archive_existing` moves `state.json` and `gates.jsonl` into `runs/<id>/archive-N/`
    on `init --archive`, but leaves `runs/<id>/package.jsonl` where it is. Reuse the same
    sprint id across an archive and `last_record` reads the PREVIOUS run's package as
    though it belonged to this one - and that record's SHA can still "match HEAD" if
    nothing has committed since, the exact false pass this guard exists to prevent. A
    package whose diff is gone cannot be the package under review, whatever its recorded
    SHA says, so this is checked before staleness rather than instead of it.
    """
    path = str(record.get("path", "<scratch>/review-final.diff"))
    return (
        f"the recorded review package names a diff that is not on disk: {path}\n"
        f"  looked in: {dispatch_root}\n"
        "A package whose diff is gone cannot be the package under review, whatever its "
        "recorded SHA says.\n"
        "The likely cause is a sprint id reused across `init --archive`: the archive moves "
        "state.json and gates.jsonl into runs/<id>/archive-N/, but package.jsonl is not "
        "part of that move, so a previous run's last-recorded package survives under the "
        "same id and is read as though it belonged to this one.\n"
        "Cut the package again from the current dispatch root, record it, then re-run this "
        "stage:\n"
        f"  review-package $(git -C <dispatch-root> merge-base <default-branch> HEAD) HEAD {path}\n"
        f"  supskill-state package --base $(git -C <dispatch-root> merge-base <default-branch> HEAD) "
        f"--head $(git -C <dispatch-root> rev-parse HEAD) --path {path} --dispatch-root <dispatch-root>\n"
        "Nothing was dispatched and no gate was called: G3 is still open."
    )


def missing_refusal(sprint_id: str) -> str:
    """What the conductor reports when EXECUTE recorded no package at all."""
    return (
        f"no review package was recorded for sprint {sprint_id}, so there is nothing to "
        "prove PAR would review this branch.\n"
        "EXECUTE's halt is what records it, right after it writes the diff:\n"
        "  supskill-state package --base <merge-base> --head <HEAD> "
        "--path <scratch>/review-final.diff --dispatch-root <dispatch-root>\n"
        "--dispatch-root is required whenever the package was cut in a worktree - the "
        "guard rev-parses HEAD there, not at the state root (SK-104).\n"
        "An unrecorded package is exactly the state that hid this defect on playset s1: "
        "the diff on disk looked fine and nothing could say which commits it covered.\n"
        "Nothing was dispatched and no gate was called."
    )


def refusal(record: dict, current_head: str) -> str:
    """What the conductor reports, verbatim, when the recorded package is stale."""
    recorded_head = str(record.get("head", ""))
    if not is_stale(recorded_head, current_head):
        raise StateError(
            "refusal() called on a package that matches HEAD; there is nothing to refuse"
        )
    base = str(record.get("base", "?"))
    path = str(record.get("path", "<scratch>/review-final.diff"))
    dispatch_root = str(record.get("dispatch_root") or "").strip() or "<dispatch-root>"
    return (
        "the recorded review package is stale: HEAD has moved since EXECUTE cut it.\n"
        f"  package base:  {base}\n"
        f"  package head:  {recorded_head.strip() or '(none recorded)'}\n"
        f"  HEAD now:      {current_head}\n"
        f"  package file:  {path}\n"
        "PAR would review a diff that is not this branch, and a review of the wrong code "
        "comes back clean - which is why this refuses instead of proceeding.\n"
        "Regenerate the package from the dispatch root, re-record it, then re-run this "
        "stage:\n"
        f"  review-package $(git -C {dispatch_root} merge-base <default-branch> HEAD) HEAD {path}\n"
        f"  supskill-state package --base $(git -C {dispatch_root} merge-base <default-branch> HEAD) "
        f"--head {current_head} --path {path} --dispatch-root {dispatch_root}\n"
        "--dispatch-root is required whenever the package was cut in a worktree - the "
        "guard rev-parses HEAD there, not at the state root (SK-104).\n"
        "Nothing was dispatched and no gate was called: G3 is still open.\n"
        "This compares SHAs; a package cut at the right HEAD from the wrong base walks "
        "past it."
    )
