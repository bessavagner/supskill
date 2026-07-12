"""Derived SDD scratch paths (D8): computed from the sprint id, never typed.

SDD's default repo-wide scratch dir namespaces task briefs by task number only,
and task numbering restarts every sprint - so two sprints' "Task 3" briefs
silently overwrite each other. Every sprint therefore gets its own
.superpowers/sdd/<normalized-id>/, derived at init, stored in state.json.
There is deliberately NO override flag or parameter anywhere.
"""

import re

from .errors import StateError

SCRATCH_ROOT = ".superpowers/sdd"

_NORMALIZED = re.compile(r"^[a-z0-9-]+$")


def normalize_sprint_id(sprint_id: str) -> str:
    normalized = sprint_id.lower()
    if not _NORMALIZED.fullmatch(normalized):
        raise StateError(
            f"sprint id {sprint_id!r} is not usable: after lowercasing it must contain "
            "only [a-z0-9-]; refusing to mangle it into a path"
        )
    return normalized


def derive_scratch(sprint_id: str) -> str:
    return f"{SCRATCH_ROOT}/{normalize_sprint_id(sprint_id)}/"
