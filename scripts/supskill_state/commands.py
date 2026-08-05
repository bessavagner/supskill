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

from . import blockers as blockers_view
from . import config, stop_classes, store
from .errors import StateError
from .model import (
    ARTIFACT_KEYS,
    ENTRY_STAGES,
    GATE_DECISIONS,
    GATE_KEYS,
    TERMINAL_STATUSES,
    Blocker,
    SprintInfo,
    Stage,
    State,
    Task,
    TaskStatus,
    blocker_to_dict,
    loads_state,
    parse_task_status,
    state_to_dict,
)
from .plan_coverage import headings_for_story, validate_plan_coverage
from .proofs import parse_proof_lines
from .review import aggregate, parse_confidence, parse_reviewer, parse_severity
from .scratch import derive_scratch, normalize_sprint_id
from .transitions import failed_preconditions, next_stage


def init_sprint(
    sprint_id: str,
    *,
    slug: str | None = None,
    entry: str = "SCOPE",
    backlog: str | None = None,
    branch: str | None = None,
    continues: str | None = None,
    archive: bool = False,
    root: Path | None = None,
) -> State:
    root = store.resolve_root(root)
    try:
        entry_stage = Stage(entry)
    except ValueError:
        raise StateError(f"unknown entry stage {entry!r}") from None
    if entry_stage not in ENTRY_STAGES:
        raise StateError(f"--entry must be one of SCOPE|PLAN|EXECUTE, got {entry_stage.value}")
    scratch = derive_scratch(sprint_id)  # validates the id before any disk change
    normalized = normalize_sprint_id(sprint_id)

    if continues is not None:
        if not continues.strip():
            raise StateError("--continues needs a sprint id, not an empty string")
        if entry_stage is Stage.SCOPE:
            raise StateError(
                "a SCOPE-entry sprint continues nothing: it scopes its own doc from the "
                "backlog. --continues names the sprint a PLAN- or EXECUTE-entry sprint "
                "resumes work on"
            )

    # Everything below refuses before anything is archived or written. The backlog check
    # moved here from above (SK-144): it can only run once the state being archived has
    # been read, because that state is where an un-flagged backlog comes from.
    path = store.state_path(root)
    existing = path.exists()
    inherited: str | None = None
    if existing:
        if not archive:
            raise StateError(
                f"{path} already exists; pass --archive to archive the old run first "
                "(prior state is never destroyed)"
            )
        live = _live_sprint_refusal(path)
        if live is not None:
            raise StateError(live)
        inherited = _existing_sprint_id(path)
        # SK-144: the backlog is project-scoped - it is the one top-level field of
        # state.json outside `sprint` - so a sprint that archives another inherits it
        # rather than making the operator retype a path the trail already holds. An
        # explicit --backlog still wins, and no verb sets it after init: this resolves
        # AT init, from disk. Without it a bare `/supskill run <new-id>` cannot open a
        # SCOPE sprint at all, because step 3 has no operator flag to carry forward.
        if backlog is None:
            backlog = _existing_backlog(path)

    if entry_stage is Stage.SCOPE and not backlog:
        raise StateError(
            "a SCOPE-entry sprint has nothing to scope without a backlog: pass --backlog <path> "
            "(no verb can set it after init; PLAN and EXECUTE entries may omit it)"
        )

    if existing:
        _archive_existing(root)
    # SK-116: a PLAN- or EXECUTE-entry sprint that archives one is continuing it. Record
    # that rather than requiring the conductor to remember the flag - the row exists
    # because "s6 continues s5" and "s6's doc is misnamed" were indistinguishable on disk.
    if continues is None and entry_stage is not Stage.SCOPE:
        continues = inherited

    state = State(
        schema=1,
        backlog=backlog,
        sprint=SprintInfo(
            id=sprint_id,
            slug=slug,
            entry=entry_stage,
            branch=branch,
            scratch=scratch,
            continues=continues,
        ),
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


def _live_sprint_refusal(path: Path) -> str | None:
    """The refusal when archiving would retire a sprint nobody has ruled on.

    One evidential stop (`init.archive.undecided`), two shapes. SK-115 is the first:
    a sprint resting at REVIEW with Gate 3 open. SK-143 is the second, found on live
    turmarium a day after 0.7.0 shipped - B5 sat at EXECUTE with six DONE, one BLOCKED
    task and an open blocker, and E10's step-3 fix had made every state but the first
    shape silently archivable. SK-115's refusal protects the case where a *decision* is
    lost; nothing protected the case where *work in progress* is.

    A recorded G3 decision closes both shapes, and that ordering is load-bearing rather
    than incidental: BLOCKED is terminal, so a sprint can legally reach REVIEW carrying
    an open blocker, and its blocker can never resolve afterwards (resolution is derived
    from the task's status, and the task is terminal). Refusing on an open blocker after
    Gate 3 had ruled would strand that sprint permanently - a worse failure than the one
    this fixes. Gate 3 is the operator ruling on the whole sprint, blockers included.

    Returns the refusal text, or None when there is nothing to refuse. An old state that
    cannot be READ returns None: it is archived, never destroyed
    (test_init_archives_unreadable_old_state_under_unknown), and refusing on a parse
    error would turn that guarantee into its opposite.
    """
    try:
        old = loads_state(path.read_text(encoding="utf-8"))
    except Exception:
        return None  # unreadable old state: nothing to refuse, same rule as _archive_existing
    if old.gates[GATE_KEYS["G3"]] is not None:
        return None  # the operator ruled on this sprint at Gate 3
    if old.stage is Stage.REVIEW:
        return _undecided_review_refusal(old)
    pending = [task.id for task in old.tasks if task.status not in TERMINAL_STATUSES]
    open_blockers = [b.task for b in blockers_view.partition(old.blockers, old.tasks)[0]]
    if not pending and not open_blockers:
        return None
    return _live_work_refusal(old, pending, open_blockers)


def _live_work_refusal(old: State, pending: list[str], open_blockers: list[str]) -> str:
    """SK-143: the sprint is mid-flight and no Gate 3 decision exists to close it."""
    reasons = []
    if pending:
        reasons.append(f"{len(pending)} task(s) not terminal ({', '.join(pending)})")
    if open_blockers:
        reasons.append(f"{len(open_blockers)} open blocker(s) ({', '.join(open_blockers)})")
    return (
        f"sprint {old.sprint.id} is still live at {old.stage.value}: {' and '.join(reasons)}. "
        "Archiving it now retires work the operator never ruled on.\n"
        "Nothing would be destroyed - the commits stay on the branch and runs/<id>/*.jsonl "
        "stays put - but a sprint's live state is not the conductor's to close. Only gates "
        "and blockers interrupt a run; this is both of them at once.\n"
        "Finish it, or rule on it, then re-run this init:\n"
        "  supskill-state task --id <id> --status <DONE|DONE_WITH_CONCERNS|BLOCKED|PARKED> "
        '--note "<what happened>"\n'
        '  supskill-state decide --task <id> --option "<label>" --response "<verbatim>"\n'
        "  supskill-state advance --to REVIEW\n"
        "  supskill-state gate --id G3 --decision <approved|rejected|replan> "
        '--response "<what you decided, verbatim>"\n'
        "Nothing was archived and nothing was created; the sprint on disk is untouched.\n"
        "This checks that the work reached a terminal state, not that it reached a good one."
    )


def _existing_backlog(path: Path) -> str | None:
    """The outgoing sprint's backlog, or None if unreadable or unset (SK-144)."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        value = raw["backlog"]
    except Exception:
        return None  # an unreadable old state is archived, not refused; it just names nothing
    return value if isinstance(value, str) and value.strip() else None


def _undecided_review_refusal(old: State) -> str:
    """SK-115: the refusal when the outgoing sprint rests at REVIEW with G3 open.

    A sprint that reached REVIEW and never recorded a Gate 3 decision is the one
    case where archiving keeps the question and loses the answer. ledgerus s5 is
    the instance on record: it halted on a genuine blocker, the operator resolved
    it out of band, s6 was inited over it, and runs/s5/archive-1/gates.jsonl
    holds G1 and G2 and no G3 - how that blocker was decided exists nowhere on
    disk. This is the append-only trail failing at the point it was built for.

    The ceiling: this checks that a decision was RECORDED, not that it was the
    right one. `gate --id G3 --decision approved --response "."` satisfies it.

    Reachability (stage is REVIEW, G3 is null, the state parsed) is the caller's,
    `_live_sprint_refusal`; this composes the text.
    """
    return (
        f"sprint {old.sprint.id} rests at REVIEW with no Gate 3 decision recorded. "
        "Archiving it now would keep the question and lose the answer.\n"
        "What a later reader has is the trail: runs/<id>/archive-N/gates.jsonl. A sprint "
        "that halted on a real blocker and was superseded out of band leaves nothing in it "
        "saying how that blocker was decided - the decision that mattered most is the one "
        "the archive drops.\n"
        "Record it first, with the verb that already exists, then re-run this init:\n"
        f"  supskill-state gate --id G3 --decision <approved|rejected|replan> "
        '--response "<what you decided, verbatim>"\n'
        "Nothing was archived and nothing was created; the sprint on disk is untouched.\n"
        "This checks that a decision was recorded, not that it was the right one."
    )


def _existing_sprint_id(path: Path) -> str | None:
    """The outgoing sprint's id as it was typed, or None if unreadable (SK-116)."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        value = raw["sprint"]["id"]
    except Exception:
        return None  # an unreadable old state is archived, not refused; it just names nothing
    return value if isinstance(value, str) and value.strip() else None


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
    root = store.resolve_root(root)
    state = store.load_state(store.state_path(root))
    gate_rows = _last_gate_rows(root)
    responses = {key: row.get("response", "") for key, row in gate_rows.items()}

    slug = f" ({state.sprint.slug})" if state.sprint.slug else ""
    lines = [
        f"sprint {state.sprint.id}{slug} - stage {state.stage.value} "
        f"(entered at {state.sprint.entry.value})",
        f"backlog: {state.backlog or '-'}",
    ]
    if state.sprint.continues:
        lines.append(f"continues: {state.sprint.continues}")
    lines.append("artifacts:")
    for key in ARTIFACT_KEYS:
        lines.append(f"  {key}: {state.artifacts[key] or '-'}")
    lines.append("gates:")
    for cli_id, key in GATE_KEYS.items():
        decision = state.gates[key] if state.gates[key] is not None else "-"
        line = f"  {cli_id} {key}: {decision}"
        if key in responses:
            line += f'  response: "{responses[key]}"'
        # SK-133: a bulk acceptance is printed as one, so it is not read as a
        # considered decision. Only the true case prints - a gate answered item by
        # item says nothing extra.
        if gate_rows.get(key, {}).get("batched"):
            line += "  (batched)"
        lines.append(line)

    counts = Counter(task.status for task in state.tasks)
    by_status = ", ".join(
        f"{counts[status]} {status.value}" for status in TaskStatus if counts[status]
    )
    lines.append(f"tasks: {len(state.tasks)} total" + (f" - {by_status}" if by_status else ""))

    open_blockers, resolved_blockers = blockers_view.partition(state.blockers, state.tasks)
    notes = _last_task_notes(root, state.sprint.id) if resolved_blockers else {}
    headings = _blocker_plan_headings(root, state.sprint.id) if open_blockers else {}

    if open_blockers:
        lines.append("open blockers:")
        for blocker in open_blockers:
            lines.append(f"  {blocker.task} [{blocker.kind}] {blocker.found}")
            for option in blocker.options:
                lines.append(f"      {option}")
            lines.append(f"    recommend: {blocker.recommend}")
            halted = headings.get(blocker.task, [])
            if halted:
                lines.append("    plan headings this blocker halted:")
                for heading in halted:
                    lines.append(f"      {heading}")
    else:
        lines.append("open blockers: none")

    if resolved_blockers:
        lines.append("resolved blockers:")
        for blocker in resolved_blockers:
            lines.append(f"  {blocker.task} [{blocker.kind}] {blocker.found}")
            # Minor 5: the status printed here is read through the SAME function
            # blockers_view.partition used to decide this blocker belongs in `resolved`
            # at all - not a second, independent read of tasks.jsonl that could disagree.
            status = blockers_view.resolving_status(blocker, state.tasks)
            _, note = notes.get(blocker.task, ("", None))
            lines.append(f"    resolved by: {blocker.task} -> {status.value if status else '?'}")
            if note:
                lines.append(f'    note: "{note}"')
    return "\n".join(lines) + "\n"


def render_show_json(root: Path | None = None) -> str:
    """The resume read-contract: the full state as JSON, plus a `derived` view.

    The conductor's dispatch consumes this instead of parsing state.json
    itself - the schema stays the CLI's concern, never skill prose's.

    `derived` is computed at read time and never written back: state.json has no
    such key and gains none (SK-103). Everything under it is a function of the
    state above it, so a reader that ignores `derived` still sees the whole truth.
    """
    root = store.resolve_root(root)
    state = store.load_state(store.state_path(root))
    payload = state_to_dict(state)
    open_blockers, resolved_blockers = blockers_view.partition(state.blockers, state.tasks)
    headings = (
        _blocker_plan_headings(root, state.sprint.id) if (open_blockers or resolved_blockers) else {}
    )
    notes = _last_task_notes(root, state.sprint.id) if resolved_blockers else {}
    decisions = _blocker_decisions(root, state.sprint.id) if (open_blockers or resolved_blockers) else {}
    gate_rows = _last_gate_rows(root)
    payload["derived"] = {
        "blockers": {
            "open": [_blocker_view(b, headings, state.tasks, notes, decisions) for b in open_blockers],
            "resolved": [_blocker_view(b, headings, state.tasks, notes, decisions) for b in resolved_blockers],
        },
        # SK-133: state.json records WHAT was decided; only the trail records whether
        # one answer accepted a batch. Read-time like everything else under `derived` -
        # state.json gains no key.
        "gates": {
            key: {
                "decision": state.gates[key],
                "batched": bool(gate_rows.get(key, {}).get("batched")),
            }
            for key in GATE_KEYS.values()
        },
    }
    return json.dumps(payload, indent=2) + "\n"


def _blocker_view(
    blocker: Blocker,
    headings: dict[str, list[str]],
    tasks: list[Task],
    notes: dict[str, tuple[str, str | None]],
    decisions: dict[str, dict],
) -> dict:
    """A `derived.blockers.*` entry: `blocker_to_dict` plus the plan headings it
    halted (SK-102) and, once resolved, the evidence of how (Important 3, final
    review of feat/e9-gate3-inputs).

    Before this, `show --json`'s resolved blockers carried `options`/`recommend`/
    `plan_headings` but nothing saying WHICH status resolved them or what the
    operator noted - the very reconstruction SK-103 was filed to remove, still
    required on the JSON path SKILL.md:510 actually names.

    `resolved_by` is read through `blockers.resolving_status` - the SAME function
    `blockers_view.partition` used to decide this blocker belongs in `open` or
    `resolved` in the first place (Minor 5): a second, independent read of the
    trail could disagree with that decision and report a status the blocker was
    never actually partitioned for. It is `None` for an open blocker, by
    construction - `resolving_status` returns `None` for exactly that case.

    `note` is the trail's own free-text field and has no such second source; it
    stays a `_last_task_notes` read, and is only surfaced once `resolved_by` is
    set - an open blocker's task can carry an unrelated non-resolving status note
    (e.g. PARKED) in tasks.jsonl, and that must not leak in as though it settled
    this blocker. `blocker_to_dict` itself is the *state* serializer and stays
    unchanged; everything added here is read-time only (SK-103): state.json
    gains no such key.

    `decision`/`batched` come from the blocker's own `decide` row (SK-132/SK-133),
    unrelated to `resolved_by`: a blocker can be answered without yet being settled
    (the task hasn't moved), which is exactly what makes them worth showing side by
    side rather than folding one into the other.
    """
    status = blockers_view.resolving_status(blocker, tasks)
    _, note = notes.get(blocker.task, (None, None)) if status else (None, None)
    decision = decisions.get(blocker.task)
    return {
        **blocker_to_dict(blocker),
        "plan_headings": headings.get(blocker.task, []),
        "resolved_by": status.value if status else None,
        "note": note,
        "decision": decision["option"] if decision else None,
        "batched": decision["batched"] if decision else False,
    }


def _jsonl_records(path: Path):
    """Every well-formed record in an append-only trail, in file order.

    A missing file yields nothing. A blank line is skipped, and so is a crash-torn or
    malformed tail: these trails are fsync'd appends, but a process killed mid-write
    can still leave a partial final line, and a torn tail must never take `show` down.
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            yield record


def _last_gate_rows(root: Path | None = None) -> dict[str, dict]:
    """Each gate's last recorded row from gates.jsonl, keyed by state key.

    Last wins, the same rule state.gates itself follows: a re-gated stage's newest
    answer is the one `show` reports.
    """
    rows: dict[str, dict] = {}
    for record in _jsonl_records(store.gates_path(root)):
        key = GATE_KEYS.get(record.get("gate"))
        if key is not None:
            rows[key] = record
    return rows


def _last_gate_responses(root: Path | None = None) -> dict[str, str]:
    return {key: row.get("response", "") for key, row in _last_gate_rows(root).items()}


def _last_task_notes(root: Path | None, sprint_id: str) -> dict[str, tuple[str, str | None]]:
    """Each task's last recorded (status, note) from runs/<id>/tasks.jsonl."""
    path = store.runs_dir(root) / normalize_sprint_id(sprint_id) / "tasks.jsonl"
    notes: dict[str, tuple[str, str | None]] = {}
    for record in _jsonl_records(path):
        task = record.get("task")
        if isinstance(task, str):
            notes[task] = (record.get("status", ""), record.get("note"))
    return notes


def _blocker_plan_headings(root: Path | None, sprint_id: str) -> dict[str, list[str]]:
    """Each task's last-recorded halted plan headings from runs/<id>/blockers.jsonl."""
    path = store.runs_dir(root) / normalize_sprint_id(sprint_id) / "blockers.jsonl"
    found: dict[str, list[str]] = {}
    for record in _jsonl_records(path):
        task = record.get("task")
        headings = record.get("plan_headings")
        if isinstance(task, str) and isinstance(headings, list):
            found[task] = [h for h in headings if isinstance(h, str)]
    return found


def _blocker_decisions(root: Path, sprint_id: str) -> dict[str, dict]:
    """task id -> its decision row, for blockers answered through `decide` (SK-132)."""
    path = store.runs_dir(root) / normalize_sprint_id(sprint_id) / "blockers.jsonl"
    found: dict[str, dict] = {}
    for record in _jsonl_records(path):
        if record.get("row") == "decision":
            found[record["task"]] = record
    return found


def record_artifact(name: str, file_path: str, root: Path | None = None) -> State:
    root = store.resolve_root(root)
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


def record_gate(
    gate_id: str,
    decision: str,
    response: str,
    *,
    batched: bool = False,
    root: Path | None = None,
) -> State:
    root = store.resolve_root(root)
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
        "batched": batched,  # SK-133: a bulk acceptance must not read as a considered one
        "at": store.now_utc_iso(),
    }
    store.append_jsonl(store.gates_path(root), record)  # trail FIRST
    state.gates[GATE_KEYS[gate_id]] = decision  # last decision wins in state
    store.dump_state(state, store.state_path(root))  # state SECOND
    return state


_OPTION_LABEL = re.compile(r"^\(([a-z0-9]+)\)")


def _blocked_story_headings(state: State, task_id: str, root: Path) -> list[str]:
    """The recorded dev plan's headings that serve `task_id` (SK-102).

    Best-effort by design: no recorded dev_plan, a recorded path that has since
    vanished, or a plan that cannot be decoded all return []. A blocker is the more
    important record of the two - refusing to write one because the plan moved would
    trade the escalation for the annotation.

    These are the story's headings, not its UNRUN headings: state tracks stories, so
    nothing here knows where the drain stopped. Gate 3 reads this as "the blocker
    halted a story the plan spends these headings on".
    """
    plan = state.artifacts.get("dev_plan")
    if not plan:
        return []
    plan_path = root / plan
    try:
        text = plan_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return headings_for_story(text, task_id, story_prefix=config.load_story_id_prefix(root))


def record_blocker(
    task_id: str,
    kind: str,
    found: str,
    options: list[str],
    recommend: str,
    root: Path | None = None,
) -> State:
    root = store.resolve_root(root)
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

    plan_headings = _blocked_story_headings(state, task_id, root)
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
            "plan_headings": plan_headings,  # SK-102: trail only; the schema does not move
            "at": store.now_utc_iso(),
        },
    )
    state.blockers.append(blocker)  # mirror into state
    task.status = TaskStatus.BLOCKED  # flip the task
    store.dump_state(state, store.state_path(root))  # one atomic state write, SECOND
    return state


def record_decision(
    task_id: str,
    option: str,
    response: str,
    *,
    batched: bool = False,
    root: Path | None = None,
) -> None:
    """Record which option an operator chose for a blocker (SK-132).

    This records the ANSWER, not the RESOLUTION. Whether the blocker is settled
    stays `blockers.resolving_status`'s derivation from task status (SK-103): a
    second independent mover could disagree with the task, and Gate 3 would then
    have two answers and no rule for picking one.

    `option` is matched against the blocker's own recorded options[] labels, so a
    label the operator was never offered cannot be recorded as their choice.
    """
    root = store.resolve_root(root)
    if not response.strip():
        raise StateError("a decision requires a non-empty --response - an empty answer is not a decision (D4)")

    state = store.load_state(store.state_path(root))
    blocker = next((b for b in state.blockers if b.task == task_id), None)
    if blocker is None:
        raise StateError(f"no blocker recorded for task {task_id!r}")

    match = _OPTION_LABEL.match(option)
    if match is None:
        raise StateError(f"--option must be a label like '(a)': {option!r}")
    label = match.group(1)
    offered = [_OPTION_LABEL.match(o).group(1) for o in blocker.options if _OPTION_LABEL.match(o)]
    if label not in offered:
        raise StateError(
            f"option ({label}) was never offered for {task_id}; this blocker offers {offered}"
        )

    sprint_dir = normalize_sprint_id(state.sprint.id)
    blockers_file = store.runs_dir(root) / sprint_dir / "blockers.jsonl"
    for record in _jsonl_records(blockers_file):
        if record.get("row") == "decision" and record.get("task") == task_id:
            raise StateError(
                f"{task_id} was already decided as ({record['option']}); "
                "the trail is append-only and a decision is not re-taken"
            )

    store.append_jsonl(
        blockers_file,
        {
            "row": "decision",
            "task": task_id,
            "option": label,
            "response": response,
            "batched": batched,
            "at": store.now_utc_iso(),
        },
    )


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
    root = store.resolve_root(root)
    doc_path = root / doc
    if not doc_path.is_file():
        raise StateError(f"no such doc: {doc}")
    story_prefix = config.load_story_id_prefix(root)
    proofs = parse_proof_lines(doc_path.read_text(encoding="utf-8"), story_prefix=story_prefix)
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
            plan_path.read_text(encoding="utf-8"),
            [proof.story for proof in proofs],
            story_prefix=story_prefix,
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


def set_story_id_prefix(prefix: str, *, root: Path | None = None) -> str:
    """Persist the project's story-id prefix to .supskill/config.json (SK-064).

    Returns the prefix that was configured before this call (DEFAULT_STORY_ID_PREFIX
    if none was set), so the CLI can report what changed.
    """
    root = store.resolve_root(root)
    previous = config.load_story_id_prefix(root)
    config.write_story_id_prefix(prefix, root=root)
    return previous


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
    root = store.resolve_root(root)
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


def record_cost(
    stage: str,
    tokens: int,
    *,
    label: str | None = None,
    tool_uses: int | None = None,
    duration_ms: int | None = None,
    estimated: bool = False,
    root: Path | None = None,
) -> None:
    """Record one subagent dispatch's usage against the running sprint.

    Pure telemetry: unlike every other verb, nothing here reads state.json in
    order to mutate it - sprint.id is looked up only to place the trail file,
    and no write to state.json follows. runs/<id>/costs.jsonl is the whole
    effect, so supskill's own open cost questions (PAR's doubled review cost,
    whether a SCOPE pass earns its keep) get answered from real numbers
    instead of estimation.

    SK-109: `estimated` marks a row whose token count the conductor could not
    retrieve. PAR's reviewers run as mailbox teammates and their transcripts are
    not readable from the controller, so those rows were guessed at 70k and filed
    beside measured ones with nothing to tell them apart. The key is written on
    EVERY row, measured included - a row that predates this field has no key at
    all, and that difference is the point.
    """
    root = store.resolve_root(root)
    try:
        stage_value = Stage(stage).value
    except ValueError:
        raise StateError(
            f"unknown stage {stage!r}; expected one of {[s.value for s in Stage]}"
        ) from None
    if tokens < 0:
        raise StateError("--tokens must not be negative")
    if tool_uses is not None and tool_uses < 0:
        raise StateError("--tool-uses must not be negative")
    if duration_ms is not None and duration_ms < 0:
        raise StateError("--duration-ms must not be negative")

    state = store.load_state(store.state_path(root))
    costs_file = store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / "costs.jsonl"
    store.append_jsonl(
        costs_file,
        {
            "stage": stage_value,
            "label": label,
            "tokens": tokens,
            "tool_uses": tool_uses,
            "duration_ms": duration_ms,
            "estimated": estimated,
            "at": store.now_utc_iso(),
        },
    )


def record_action(
    stop_id: str,
    command: str,
    *,
    operator_answered: bool,
    result: str = "ok",
    sha: str | None = None,
    root: Path | None = None,
) -> None:
    """Record one action the conductor took on the operator's behalf (SK-131).

    Only a `remediable` stop may produce one: an evidential stop is a refusal, and
    a refusal that writes an action record would be claiming it fixed the thing it
    was built to surface.

    `reason` is copied from the classification table's own `condition`, never
    supplied by the caller - the record says why the stop fired, not why the
    conductor felt like acting.

    `operator_answered` is SK-136: a run that cannot reach an operator does not act
    on their behalf. AskUserQuestion auto-resolves with an EMPTY answer in ~37ms in
    headless runs (D4), so before E10 that cost a missing record and here it would
    cost an executed action nobody chose. It is keyword-only with NO default, so a
    caller that forgets it raises rather than silently acting, and the attestation is
    written onto the row so a later reader can see what was claimed.

    What that check IS, stated exactly, because the wording it inherited overclaimed:
    this is a post-hoc RECORD gate, not a pre-action gate. Both remediable prose flows
    execute and then record - SKILL.md's step 3 archives then calls this, Gate 3 stages
    and commits then calls this - so on the one path the refusal exists for, the action
    has already happened and refusing here only leaves it unrecorded. The refusal says
    so. The rejected `preflight.interactive_refusal(answered)` design ran before the
    action and could honestly claim nothing had; this one cannot, and the precondition
    "a run establishes an operator answer before its first remediable action" is carried
    by conductor discipline in SKILL.md, not by this function.

    The ceiling, stated plainly: this records what the conductor attests, not what a
    human did - F-4 applies here exactly as it applies to the gates.

    Pure telemetry in the same sense as record_cost: state.json never changes.
    """
    root = store.resolve_root(root)
    stop = stop_classes.classify(stop_id)  # refuses an unknown id, writing nothing
    if not operator_answered:
        raise StateError(
            "this run has not received a non-empty answer from an operator, so it will not act "
            "on one's behalf: AskUserQuestion auto-resolves with an empty answer in headless runs, "
            "and an empty answer is not consent. Nothing was recorded here. This check fires when "
            "an action is REPORTED, not before it is taken - so if the conductor already ran the "
            "command, that action has happened and is now unrecorded: look for a sprint that was "
            "archived or a commit that was made without a row in actions.jsonl before continuing."
        )
    if stop.stop_class != stop_classes.REMEDIABLE:
        raise StateError(
            f"{stop_id} is {stop.stop_class}, not remediable - it is a refusal to relay, "
            "not an action to take"
        )
    if not command.strip():
        raise StateError("an action record requires a non-empty --command")

    state = store.load_state(store.state_path(root))
    actions_file = store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / "actions.jsonl"
    store.append_jsonl(
        actions_file,
        {
            "stop": stop.id,
            "reason": stop.condition,
            "command": command,
            "sha": sha,
            "result": result,
            "operator_answered": operator_answered,  # SK-136: attested, not inferred
            "at": store.now_utc_iso(),
        },
    )


def record_package(
    base: str,
    head: str,
    path: str,
    *,
    dispatch_root: str | None = None,
    root: Path | None = None,
) -> None:
    """Record the review package EXECUTE just cut (SK-104).

    Pure telemetry, the same shape as record_cost: state.json is read only to place
    the trail file by sprint.id, and nothing is written back to it. What this buys is
    the one fact REVIEW cannot otherwise have - EXECUTE and REVIEW are separate
    `/supskill run` invocations, so the SHA the package covers has to survive on disk
    or not at all (invariant 5).

    `dispatch_root` is optional: EXECUTE isolates into a worktree (SK-111), and when it
    does, the package is cut there - not at the state root `.supskill/` never moves
    from. Recording it here is what lets `review-guard` rev-parse the right repo instead
    of inferring one; omitted, it means the dispatch root and the state root are the
    same (the non-worktree case), and the guard falls back accordingly.
    """
    root = store.resolve_root(root)
    for flag, value in (("--base", base), ("--head", head), ("--path", path)):
        if not (value or "").strip():
            raise StateError(f"a review package record requires a non-empty {flag}")
    state = store.load_state(store.state_path(root))
    package_file = store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / "package.jsonl"
    store.append_jsonl(
        package_file,
        {
            "base": base.strip(),
            "head": head.strip(),
            "path": path.strip(),
            "dispatch_root": (dispatch_root or "").strip() or None,
            "at": store.now_utc_iso(),
        },
    )


def record_review_finding(
    reviewer: str,
    severity: str,
    confidence: str,
    finding: str,
    location: str,
    root: Path | None = None,
) -> None:
    """Record one aggregated PAR finding (SK-050).

    Pure trail, like costs.jsonl: this reads state.json only to place the
    trail file by sprint.id, and writes nothing back to it - review has no
    state.json field, the same shape as cost. Gate 3 (SK-051) reads
    runs/<id>/review.jsonl directly; nothing re-parses prose.

    SK-055: the recorded --confidence is cross-checked against PAR's fixed
    aggregation rule (review.aggregate) before anything is written - a
    finding reported by both reviewers can only be high confidence, and a
    finding reported by one reviewer can only be actionable. The rule has no
    negotiation, so a mismatched --confidence is refused, not accepted.
    """
    root = store.resolve_root(root)
    parsed_reviewer = parse_reviewer(reviewer, "review --reviewer")
    parsed_severity = parse_severity(severity, "review --severity")
    parsed_confidence = parse_confidence(confidence, "review --confidence")
    for flag, value in (("--finding", finding), ("--location", location)):
        if not (value or "").strip():
            raise StateError(f"a review finding requires a non-empty {flag}")

    severity_a = parsed_severity if parsed_reviewer in ("reviewer-a", "both") else None
    severity_b = parsed_severity if parsed_reviewer in ("reviewer-b", "both") else None
    expected_confidence, _ = aggregate(severity_a, severity_b)
    if parsed_confidence != expected_confidence:
        raise StateError(
            f"--reviewer {parsed_reviewer} --severity {parsed_severity} requires "
            f"--confidence {expected_confidence} (PAR's fixed aggregation rule, no negotiation); "
            f"got --confidence {parsed_confidence}"
        )

    state = store.load_state(store.state_path(root))
    review_file = store.runs_dir(root) / normalize_sprint_id(state.sprint.id) / "review.jsonl"
    store.append_jsonl(
        review_file,
        {
            "reviewer": parsed_reviewer,
            "severity": parsed_severity,
            "confidence": parsed_confidence,
            "finding": finding,
            "location": location,
            "at": store.now_utc_iso(),
        },
    )


def advance_stage(to: str, root: Path | None = None) -> State:
    root = store.resolve_root(root)
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
