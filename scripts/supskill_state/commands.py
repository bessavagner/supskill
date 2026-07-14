"""The verbs of supskill-state. Each verb validates fully, then writes.

Every write to state.json goes through store.dump_state (atomic) and every
audit line through store.append_jsonl (append-only). Where a verb writes both,
the audit trail is written FIRST: a crash between the writes leaves the trail
ahead of state - a decision may need re-applying, but it can never have
silently not happened.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from . import store
from .errors import StateError
from .model import (
    ARTIFACT_KEYS,
    ENTRY_STAGES,
    GATE_DECISIONS,
    GATE_KEYS,
    Blocker,
    SprintInfo,
    Stage,
    State,
    Task,
    TaskStatus,
    parse_task_status,
    state_to_dict,
)
from .plan_coverage import validate_plan_coverage
from .proofs import parse_proof_lines
from .scratch import derive_scratch, normalize_sprint_id
from .transitions import failed_preconditions, next_stage


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

    if entry_stage is Stage.SCOPE and not backlog:
        raise StateError(
            "a SCOPE-entry sprint has nothing to scope without a backlog: pass --backlog <path> "
            "(no verb can set it after init; PLAN and EXECUTE entries may omit it)"
        )

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


def render_show(root: Path | None = None) -> str:
    root = Path(root) if root is not None else Path.cwd()
    state = store.load_state(store.state_path(root))
    responses = _last_gate_responses(root)

    slug = f" ({state.sprint.slug})" if state.sprint.slug else ""
    lines = [
        f"sprint {state.sprint.id}{slug} - stage {state.stage.value} "
        f"(entered at {state.sprint.entry.value})",
        f"backlog: {state.backlog or '-'}",
        "artifacts:",
    ]
    for key in ARTIFACT_KEYS:
        lines.append(f"  {key}: {state.artifacts[key] or '-'}")
    lines.append("gates:")
    for cli_id, key in GATE_KEYS.items():
        decision = state.gates[key] if state.gates[key] is not None else "-"
        line = f"  {cli_id} {key}: {decision}"
        if key in responses:
            line += f'  response: "{responses[key]}"'
        lines.append(line)

    counts = Counter(task.status for task in state.tasks)
    by_status = ", ".join(
        f"{counts[status]} {status.value}" for status in TaskStatus if counts[status]
    )
    lines.append(f"tasks: {len(state.tasks)} total" + (f" - {by_status}" if by_status else ""))

    if state.blockers:
        lines.append("open blockers:")
        for blocker in state.blockers:
            lines.append(f"  {blocker.task} [{blocker.kind}] {blocker.found}")
            for option in blocker.options:
                lines.append(f"      {option}")
            lines.append(f"    recommend: {blocker.recommend}")
    else:
        lines.append("open blockers: none")
    return "\n".join(lines) + "\n"


def render_show_json(root: Path | None = None) -> str:
    """The resume read-contract: the full state as JSON.

    The conductor's dispatch consumes this instead of parsing state.json
    itself - the schema stays the CLI's concern, never skill prose's.
    """
    root = Path(root) if root is not None else Path.cwd()
    state = store.load_state(store.state_path(root))
    return json.dumps(state_to_dict(state), indent=2) + "\n"


def _last_gate_responses(root: Path | None = None) -> dict[str, str]:
    gates_file = store.gates_path(root)
    responses: dict[str, str] = {}
    if not gates_file.exists():
        return responses
    for line in gates_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # a crash-torn tail must not take down show; skip it
        key = GATE_KEYS.get(record.get("gate"))
        if key is not None:
            responses[key] = record.get("response", "")
    return responses


def record_artifact(name: str, file_path: str, root: Path | None = None) -> State:
    root = Path(root) if root is not None else Path.cwd()
    if name not in ARTIFACT_KEYS:
        raise StateError(f"unknown artifact {name!r}; expected one of {list(ARTIFACT_KEYS)}")
    if not file_path:
        raise StateError("artifact path must not be empty")
    if not (root / file_path).exists():
        raise StateError(f"artifact file not found: {file_path}")
    state = store.load_state(store.state_path(root))
    state.artifacts[name] = file_path
    store.dump_state(state, store.state_path(root))
    return state


def record_gate(gate_id: str, decision: str, response: str, root: Path | None = None) -> State:
    root = Path(root) if root is not None else Path.cwd()
    if gate_id not in GATE_KEYS:
        raise StateError(f"unknown gate {gate_id!r}; expected one of {sorted(GATE_KEYS)}")
    if decision not in GATE_DECISIONS:
        raise StateError(f"unknown decision {decision!r}; expected one of {list(GATE_DECISIONS)}")
    # load (and thereby validate) state BEFORE writing the trail, so a refusal writes nothing
    state = store.load_state(store.state_path(root))
    record = {
        "gate": gate_id,
        "decision": decision,
        "response": response,  # verbatim; empty is accepted and recorded by design (F-4)
        "at": store.now_utc_iso(),
    }
    store.append_jsonl(store.gates_path(root), record)  # trail FIRST
    state.gates[GATE_KEYS[gate_id]] = decision  # last decision wins in state
    store.dump_state(state, store.state_path(root))  # state SECOND
    return state


_OPTION_LABEL = re.compile(r"^\(([a-z0-9]+)\)")


def record_blocker(
    task_id: str,
    kind: str,
    found: str,
    options: list[str],
    recommend: str,
    root: Path | None = None,
) -> State:
    root = Path(root) if root is not None else Path.cwd()
    # validate the whole record BEFORE touching disk: a rejected record writes nothing anywhere
    for flag, value in (("--task", task_id), ("--kind", kind), ("--found", found), ("--recommend", recommend)):
        if not value:
            raise StateError(f"a blocker record requires a non-empty {flag}")
    if len(options) < 2:
        raise StateError(
            "a blocker must enumerate at least two --option entries - "
            "a single option is a fait accompli, not a decision"
        )
    labels: list[str] = []
    for option in options:
        match = _OPTION_LABEL.match(option)
        if match is None:
            raise StateError(f"every option must start with a label like '(a) ...': {option!r}")
        if match.group(1) in labels:
            raise StateError(f"duplicate option label ({match.group(1)})")
        labels.append(match.group(1))
    recommend_match = _OPTION_LABEL.match(recommend)
    if recommend_match is None or recommend_match.group(1) not in labels:
        raise StateError(
            "recommend must reference one of the options by its label, e.g. '(a) - because ...'"
        )

    state = store.load_state(store.state_path(root))
    task = next((t for t in state.tasks if t.id == task_id), None)
    if task is None:
        raise StateError(f"no task {task_id!r} in state.json - a blocker must attach to a known task")

    blocker = Blocker(task=task_id, kind=kind, found=found, options=list(options), recommend=recommend)
    blockers_file = store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / "blockers.jsonl"
    store.append_jsonl(  # trail FIRST
        blockers_file,
        {
            "task": blocker.task,
            "kind": blocker.kind,
            "found": blocker.found,
            "options": list(blocker.options),
            "recommend": blocker.recommend,
            "at": store.now_utc_iso(),
        },
    )
    state.blockers.append(blocker)  # mirror into state
    task.status = TaskStatus.BLOCKED  # flip the task
    store.dump_state(state, store.state_path(root))  # one atomic state write, SECOND
    return state


def load_tasks(
    doc: str,
    *,
    plan: str | None = None,
    root: Path | None = None,
) -> State:
    """Load tasks[] from a sprint doc's proof lines (SK-033).

    proofs.py is the single vocabulary owner: this verb parses NOTHING itself.
    Tasks are story-shaped (SK-0xx), which is why a dev plan's task headings must
    name the story they serve - that heading is the only join between what SDD
    reports (Task N) and what state tracks (SK-0xx).

    Non-destructive: a reload that would reset progress refuses instead. The
    operator who really wants a fresh load has `init --archive`; this verb never
    runs it.
    """
    root = Path(root) if root is not None else Path.cwd()
    doc_path = root / doc
    if not doc_path.is_file():
        raise StateError(f"no such doc: {doc}")
    proofs = parse_proof_lines(doc_path.read_text(encoding="utf-8"))
    if not proofs:
        raise StateError(
            f"no proof lines in {doc}: there is nothing to load "
            "(a refined sprint doc carries one proof line per story)"
        )

    state = store.load_state(store.state_path(root))
    started = [task.id for task in state.tasks if task.status is not TaskStatus.PENDING]
    if started:
        raise StateError(
            "tasks[] already carries progress (" + ", ".join(started) + "); refusing to reset it. "
            "A fresh load is an operator decision: archive the run with init --archive"
        )

    if plan is not None:
        plan_path = root / plan
        if not plan_path.is_file():
            raise StateError(f"no such plan: {plan}")
        failures = validate_plan_coverage(
            plan_path.read_text(encoding="utf-8"), [proof.story for proof in proofs]
        )
        if failures:
            raise StateError(
                f"the dev plan does not cover the sprint doc's stories: {'; '.join(failures)}"
            )

    state.tasks = [
        Task(id=proof.story, seam=proof.seam, provable=proof.provable, status=TaskStatus.PENDING)
        for proof in proofs
    ]
    store.dump_state(state, store.state_path(root))
    return state


def record_task_status(
    task_id: str,
    status: str,
    note: str | None = None,
    root: Path | None = None,
) -> State:
    """Record an SDD-reported status for one task (SK-043).

    The missing half of the spine. DONE, DONE_WITH_CONCERNS and PARKED have been
    in TaskStatus since S1 and nothing could write them: `tasks` writes PENDING,
    `block` writes BLOCKED. So advance --to REVIEW - which refuses while any task
    is non-terminal - was unsatisfiable for any task that succeeded, and no sprint
    could ever end.

    Concerns get an append-only trail (runs/<id>/tasks.jsonl) rather than a schema
    field: trail FIRST, state SECOND, exactly like gates.jsonl and blockers.jsonl.
    Re-recording is legal and appends - last status wins in state, every attempt
    stays in the trail. Gate 3 (E6) reads the trail; nothing re-parses prose.
    """
    root = Path(root) if root is not None else Path.cwd()
    if not task_id:
        raise StateError("a status record requires a non-empty --id")
    # the model owns the vocabulary: NEEDS_CONTEXT and unknown statuses raise ITS message
    parsed = parse_task_status(status, "task --status")
    if parsed is TaskStatus.BLOCKED:
        raise StateError(
            "BLOCKED is `block`'s transition, not this verb's: a task is blocked by recording a "
            "blocker WITH its options - a conductor that could set BLOCKED with a bare status "
            "could halt with a shrug"
        )
    if parsed is TaskStatus.PENDING:
        raise StateError(
            "PENDING is where `tasks` starts every task; it is not a status a task is moved TO. "
            "Nothing in this spine walks a task backwards"
        )
    if parsed is TaskStatus.DONE_WITH_CONCERNS and not (note or "").strip():
        raise StateError(
            "DONE_WITH_CONCERNS requires --note: a concern with no text is not a concern, and "
            "Gate 3 reads this trail rather than the conductor's memory"
        )

    state = store.load_state(store.state_path(root))
    task = next((t for t in state.tasks if t.id == task_id), None)
    if task is None:
        raise StateError(
            f"no task {task_id!r} in state.json - a status must attach to a known task; "
            "this verb never creates one"
        )

    tasks_file = store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / "tasks.jsonl"
    store.append_jsonl(  # trail FIRST
        tasks_file,
        {"task": task_id, "status": parsed.value, "note": note, "at": store.now_utc_iso()},
    )
    task.status = parsed
    store.dump_state(state, store.state_path(root))  # state SECOND
    return state


def advance_stage(to: str, root: Path | None = None) -> State:
    root = Path(root) if root is not None else Path.cwd()
    try:
        target = Stage(to)
    except ValueError:
        raise StateError(
            f"unknown stage {to!r}; expected one of {[s.value for s in Stage]}"
        ) from None
    state = store.load_state(store.state_path(root))
    expected = next_stage(state.stage)
    if expected is None:
        raise StateError(f"{state.stage.value} is the final stage; there is nothing to advance to")
    if target is not expected:
        raise StateError(
            f"advance is one-step-forward only: from {state.stage.value} the only legal "
            f"target is {expected.value}; --to {target.value} refused"
        )
    failures = failed_preconditions(state, target, root)
    if failures:
        raise StateError(f"cannot advance to {target.value}: " + "; ".join(failures))
    state.stage = target
    store.dump_state(state, store.state_path(root))
    return state
