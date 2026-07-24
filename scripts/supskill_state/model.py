"""state.json schema v1 - typed model and validation.

Human-readable schema doc: docs/state-schema.md. Two conventions enforced here:

* Task status vocabulary. SDD implementers report DONE / DONE_WITH_CONCERNS /
  NEEDS_CONTEXT / BLOCKED. NEEDS_CONTEXT is a controller-loop signal (the
  controller supplies missing info and re-dispatches the same subagent), not a
  resting state: E5 resolves it in-loop, else the task becomes BLOCKED plus a
  blocker record (D5). It is therefore rejected as a persistable status.

* Sprint completion is a G3 decision, not a sixth stage: REVIEW is terminal,
  and what happens next is Gate 3's recorded decision plus E6's replan verbs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from .errors import StateError

SCHEMA_VERSION = 1


class Stage(str, Enum):  # noqa: UP042
    SCOPE = "SCOPE"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    REVIEW = "REVIEW"


STAGE_ORDER: tuple[Stage, ...] = (
    Stage.SCOPE,
    Stage.PLAN,
    Stage.EXECUTE,
    Stage.REVIEW,
)

ENTRY_STAGES: frozenset[Stage] = frozenset((Stage.SCOPE, Stage.PLAN, Stage.EXECUTE))


class TaskStatus(str, Enum):  # noqa: UP042
    PENDING = "PENDING"
    DONE = "DONE"
    DONE_WITH_CONCERNS = "DONE_WITH_CONCERNS"
    BLOCKED = "BLOCKED"
    PARKED = "PARKED"


# The terminal set advance --to REVIEW consumes (SK-003). Nothing redefines this.
TERMINAL_STATUSES: frozenset[TaskStatus] = frozenset(
    (TaskStatus.DONE, TaskStatus.DONE_WITH_CONCERNS, TaskStatus.BLOCKED, TaskStatus.PARKED)
)

# CLI gate ids -> state.json gate keys, one-to-one (docs/state-schema.md, "Gates").
GATE_KEYS: dict[str, str] = {"G1": "G1_sprint_doc", "G2": "G2_plan", "G3": "G3_review"}

GATE_DECISIONS: tuple[str, str, str] = ("approved", "rejected", "replan")

ARTIFACT_KEYS: tuple[str, str] = ("sprint_doc", "dev_plan")


@dataclass
class SprintInfo:
    id: str
    slug: str | None
    entry: Stage
    branch: str | None
    scratch: str
    # SK-116: the sprint this one continues, when it entered at PLAN or EXECUTE
    # rather than scoping its own doc. Optional on read (a state.json written
    # before this field simply has no key) and always written back.
    continues: str | None = None


@dataclass
class Task:
    id: str
    seam: str
    provable: str
    status: TaskStatus


@dataclass
class Blocker:
    task: str
    kind: str
    found: str
    options: list[str]
    recommend: str


@dataclass
class State:
    schema: int
    backlog: str | None
    sprint: SprintInfo
    stage: Stage
    artifacts: dict[str, str | None]
    gates: dict[str, str | None]
    tasks: list[Task]
    blockers: list[Blocker]


def _require(mapping: dict, key: str, where: str):
    if key not in mapping:
        raise StateError(f"{where}: missing required field {key!r}")
    return mapping[key]


def _opt_str(value, where: str) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise StateError(f"{where}: expected a string or null, got {type(value).__name__}")


def _req_str(mapping: dict, key: str, where: str) -> str:
    value = _require(mapping, key, where)
    if not isinstance(value, str):
        raise StateError(f"{where}.{key}: expected a string, got {type(value).__name__}")
    return value


def _parse_stage(value, where: str) -> Stage:
    try:
        return Stage(value)
    except ValueError:
        raise StateError(
            f"{where}: unknown stage {value!r}; expected one of "
            f"{[s.value for s in Stage]}"
        ) from None


# SK-100 collapsed SCOPE and REFINE into one stage. A state.json frozen at the
# old REFINE stage across the upgrade is remapped to SCOPE on load, so an
# in-progress sprint resumes instead of failing to parse. Applies to the
# persisted `stage` field only, never to `entry`: REFINE was never a valid
# entry, and remapping it there would silently accept an invalid --entry.
_LEGACY_STAGE_ALIASES = {"REFINE": "SCOPE"}


def _parse_persisted_stage(value, where: str) -> Stage:
    if value in _LEGACY_STAGE_ALIASES:
        value = _LEGACY_STAGE_ALIASES[value]
    return _parse_stage(value, where)


def parse_task_status(value, where: str) -> TaskStatus:
    if value == "NEEDS_CONTEXT":
        raise StateError(
            f"{where}: NEEDS_CONTEXT is a controller-loop signal, not a task state - "
            "resolve it in-loop, else record BLOCKED plus a blocker "
            "(see docs/state-schema.md)"
        )
    try:
        return TaskStatus(value)
    except ValueError:
        raise StateError(
            f"{where}: unknown task status {value!r}; expected one of "
            f"{[s.value for s in TaskStatus]}"
        ) from None


def _parse_sprint(raw, where: str) -> SprintInfo:
    if not isinstance(raw, dict):
        raise StateError(f"{where}: expected an object")
    entry = _parse_stage(_require(raw, "entry", where), f"{where}.entry")
    if entry not in ENTRY_STAGES:
        raise StateError(
            f"{where}.entry: must be one of SCOPE|PLAN|EXECUTE, got {entry.value}"
        )
    return SprintInfo(
        id=_req_str(raw, "id", where),
        slug=_opt_str(_require(raw, "slug", where), f"{where}.slug"),
        entry=entry,
        branch=_opt_str(_require(raw, "branch", where), f"{where}.branch"),
        scratch=_req_str(raw, "scratch", where),
        # .get, not _require: this field post-dates schema v1's other fields and a
        # state file written without it must still resume (SK-116)
        continues=_opt_str(raw.get("continues"), f"{where}.continues"),
    )


def _parse_gates(raw, where: str) -> dict[str, str | None]:
    if not isinstance(raw, dict):
        raise StateError(f"{where}: expected an object")
    expected = set(GATE_KEYS.values())
    if set(raw) != expected:
        raise StateError(f"{where}: must have exactly the keys {sorted(expected)}, got {sorted(raw)}")
    gates: dict[str, str | None] = {}
    for key in GATE_KEYS.values():
        value = _opt_str(raw[key], f"{where}.{key}")
        if value is not None and value not in GATE_DECISIONS:
            raise StateError(
                f"{where}.{key}: expected null or one of {list(GATE_DECISIONS)}, got {value!r}"
            )
        gates[key] = value
    return gates


def _parse_artifacts(raw, where: str) -> dict[str, str | None]:
    if not isinstance(raw, dict):
        raise StateError(f"{where}: expected an object")
    if set(raw) != set(ARTIFACT_KEYS):
        raise StateError(
            f"{where}: must have exactly the keys {sorted(ARTIFACT_KEYS)}, got {sorted(raw)}"
        )
    return {key: _opt_str(raw[key], f"{where}.{key}") for key in ARTIFACT_KEYS}


def blocker_from_dict(raw, where: str) -> Blocker:
    if not isinstance(raw, dict):
        raise StateError(f"{where}: expected an object")
    options = _require(raw, "options", where)
    if not isinstance(options, list) or not all(isinstance(o, str) for o in options):
        raise StateError(f"{where}.options: expected a list of strings")
    return Blocker(
        task=_req_str(raw, "task", where),
        kind=_req_str(raw, "kind", where),
        found=_req_str(raw, "found", where),
        options=list(options),
        recommend=_req_str(raw, "recommend", where),
    )


def state_from_dict(raw: dict) -> State:
    if not isinstance(raw, dict):
        raise StateError("state: expected a JSON object")
    schema = _require(raw, "schema", "state")
    if schema != SCHEMA_VERSION:
        raise StateError(
            f"unsupported schema version {schema!r}: this tool reads schema "
            f"{SCHEMA_VERSION} only, refusing to guess"
        )
    tasks_raw = _require(raw, "tasks", "state")
    blockers_raw = _require(raw, "blockers", "state")
    if not isinstance(tasks_raw, list) or not isinstance(blockers_raw, list):
        raise StateError("state: tasks and blockers must be lists")
    tasks = []
    for index, task_raw in enumerate(tasks_raw):
        where = f"tasks[{index}]"
        if not isinstance(task_raw, dict):
            raise StateError(f"{where}: expected an object")
        tasks.append(
            Task(
                id=_req_str(task_raw, "id", where),
                seam=_req_str(task_raw, "seam", where),
                provable=_req_str(task_raw, "provable", where),
                status=parse_task_status(_require(task_raw, "status", where), f"{where}.status"),
            )
        )
    return State(
        schema=SCHEMA_VERSION,
        backlog=_opt_str(_require(raw, "backlog", "state"), "state.backlog"),
        sprint=_parse_sprint(_require(raw, "sprint", "state"), "sprint"),
        stage=_parse_persisted_stage(_require(raw, "stage", "state"), "state.stage"),
        artifacts=_parse_artifacts(_require(raw, "artifacts", "state"), "artifacts"),
        gates=_parse_gates(_require(raw, "gates", "state"), "gates"),
        tasks=tasks,
        blockers=[
            blocker_from_dict(b, f"blockers[{i}]") for i, b in enumerate(blockers_raw)
        ],
    )


def state_to_dict(state: State) -> dict:
    return {
        "schema": state.schema,
        "backlog": state.backlog,
        "sprint": {
            "id": state.sprint.id,
            "slug": state.sprint.slug,
            "entry": state.sprint.entry.value,
            "branch": state.sprint.branch,
            "scratch": state.sprint.scratch,
            "continues": state.sprint.continues,
        },
        "stage": state.stage.value,
        "artifacts": {key: state.artifacts[key] for key in ARTIFACT_KEYS},
        "gates": {key: state.gates[key] for key in GATE_KEYS.values()},
        "tasks": [
            {"id": t.id, "seam": t.seam, "provable": t.provable, "status": t.status.value}
            for t in state.tasks
        ],
        "blockers": [
            {
                "task": b.task,
                "kind": b.kind,
                "found": b.found,
                "options": list(b.options),
                "recommend": b.recommend,
            }
            for b in state.blockers
        ],
    }


def loads_state(text: str) -> State:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise StateError(f"state is not valid JSON: {error}") from error
    return state_from_dict(raw)


def dumps_state(state: State) -> str:
    return json.dumps(state_to_dict(state), indent=2) + "\n"
