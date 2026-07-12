"""The verbs of supskill-state. Each verb validates fully, then writes.

Every write to state.json goes through store.dump_state (atomic) and every
audit line through store.append_jsonl (append-only). Where a verb writes both,
the audit trail is written FIRST: a crash between the writes leaves the trail
ahead of state - a decision may need re-applying, but it can never have
silently not happened.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import store
from .errors import StateError
from .model import (
    ARTIFACT_KEYS,
    ENTRY_STAGES,
    GATE_KEYS,
    SprintInfo,
    Stage,
    State,
)
from .scratch import derive_scratch, normalize_sprint_id


def init_sprint(
    sprint_id: str,
    *,
    slug: str | None = None,
    entry: str = "SCOPE",
    backlog: str | None = None,
    branch: str | None = None,
    archive: bool = False,
    root: Path | None = None,
) -> State:
    root = Path(root) if root is not None else Path.cwd()
    try:
        entry_stage = Stage(entry)
    except ValueError:
        raise StateError(f"unknown entry stage {entry!r}") from None
    if entry_stage not in ENTRY_STAGES:
        raise StateError(f"--entry must be one of SCOPE|PLAN|EXECUTE, got {entry_stage.value}")
    scratch = derive_scratch(sprint_id)  # validates the id before any disk change
    normalized = normalize_sprint_id(sprint_id)

    path = store.state_path(root)
    if path.exists():
        if not archive:
            raise StateError(
                f"{path} already exists; pass --archive to archive the old run first "
                "(prior state is never destroyed)"
            )
        _archive_existing(root)

    state = State(
        schema=1,
        backlog=backlog,
        sprint=SprintInfo(id=sprint_id, slug=slug, entry=entry_stage, branch=branch, scratch=scratch),
        stage=entry_stage,
        artifacts={key: None for key in ARTIFACT_KEYS},
        gates={key: None for key in GATE_KEYS.values()},
        tasks=[],
        blockers=[],
    )
    (store.runs_dir(root) / normalized).mkdir(parents=True, exist_ok=True)
    gates_file = store.gates_path(root)
    if not gates_file.exists():  # touch, never truncate (append-only invariant)
        gates_file.parent.mkdir(parents=True, exist_ok=True)
        gates_file.touch()
    store.dump_state(state, path)
    return state


def _archive_existing(root: Path) -> Path:
    supdir = store.supskill_dir(root)
    old_id = "unknown"
    try:
        raw = json.loads((supdir / "state.json").read_text(encoding="utf-8"))
        old_id = normalize_sprint_id(str(raw["sprint"]["id"]))
    except Exception:
        pass  # an unreadable old state is still archived, never destroyed
    number = 1
    while (supdir / "runs" / old_id / f"archive-{number}").exists():
        number += 1
    destination = supdir / "runs" / old_id / f"archive-{number}"
    destination.mkdir(parents=True)
    (supdir / "state.json").rename(destination / "state.json")
    old_gates = supdir / "gates.jsonl"
    if old_gates.exists():
        old_gates.rename(destination / "gates.jsonl")
    return destination
