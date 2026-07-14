"""Thin argparse shim. The CLI is wiring; the logic lives in commands.py."""

from __future__ import annotations

import argparse
import sys

from . import commands, plan_guard
from .errors import StateError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="supskill-state",
        description=(
            "State spine for supskill sprints: "
            "the only permitted mutator of .supskill/state.json."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_init(subparsers)
    _add_show(subparsers)
    _add_artifact(subparsers)
    _add_gate(subparsers)
    _add_block(subparsers)
    _add_task(subparsers)
    _add_tasks(subparsers)
    _add_advance(subparsers)
    _add_plan_guard(subparsers)
    return parser


def _add_init(subparsers) -> None:
    sub = subparsers.add_parser("init", help="create .supskill/ for a new sprint run")
    sub.add_argument("sprint_id", help="sprint id, e.g. s1 (lowercase [a-z0-9-] after normalizing)")
    sub.add_argument("--slug", help="human slug, e.g. state-spine")
    sub.add_argument("--entry", choices=["SCOPE", "PLAN", "EXECUTE"], default="SCOPE")
    sub.add_argument("--backlog", help="path to the backlog driving this sprint (required when entry is SCOPE)")
    sub.add_argument("--branch", help="git branch for this sprint")
    sub.add_argument(
        "--archive",
        action="store_true",
        help="archive an existing run under runs/<old-id>/ instead of refusing",
    )
    sub.set_defaults(func=_cmd_init)


def _cmd_init(args) -> int:
    state = commands.init_sprint(
        args.sprint_id,
        slug=args.slug,
        entry=args.entry,
        backlog=args.backlog,
        branch=args.branch,
        archive=args.archive,
    )
    print(
        f"initialized sprint {state.sprint.id} at {state.stage.value} "
        f"(scratch: {state.sprint.scratch})"
    )
    return 0


def _add_show(subparsers) -> None:
    sub = subparsers.add_parser("show", help="print stage, gates, task counts, open blockers")
    sub.add_argument("--json", action="store_true", help="print the full state as JSON (the resume contract)")
    sub.set_defaults(func=_cmd_show)


def _cmd_show(args) -> int:
    print(commands.render_show_json() if args.json else commands.render_show(), end="")
    return 0


def _add_artifact(subparsers) -> None:
    sub = subparsers.add_parser("artifact", help="record a stage's produced artifact path")
    sub.add_argument("--set", required=True, choices=["sprint_doc", "dev_plan"], dest="name")
    sub.add_argument("--path", required=True, help="path to the produced artifact (must exist)")
    sub.set_defaults(func=_cmd_artifact)


def _cmd_artifact(args) -> int:
    state = commands.record_artifact(args.name, args.path)
    print(f"recorded artifacts.{args.name} = {state.artifacts[args.name]}")
    return 0


def _add_gate(subparsers) -> None:
    sub = subparsers.add_parser("gate", help="record a gate decision with the operator's verbatim words")
    sub.add_argument("--id", required=True, choices=["G1", "G2", "G3"], dest="gate_id")
    sub.add_argument("--decision", required=True, choices=["approved", "rejected"])
    sub.add_argument("--response", required=True, help="the operator's verbatim response (may be empty)")
    sub.set_defaults(func=_cmd_gate)


def _cmd_gate(args) -> int:
    commands.record_gate(args.gate_id, args.decision, args.response)
    print(f"recorded {args.gate_id}: {args.decision}")
    return 0


def _add_block(subparsers) -> None:
    sub = subparsers.add_parser("block", help="record a structured blocker and mark its task BLOCKED")
    sub.add_argument("--task", required=True, dest="task_id")
    sub.add_argument("--kind", required=True)
    sub.add_argument("--found", required=True, help="what was actually observed")
    sub.add_argument(
        "--option",
        action="append",
        default=[],
        dest="options",
        help="a labeled alternative like '(a) ...'; repeat the flag (at least twice)",
    )
    sub.add_argument("--recommend", required=True, help="the recommended option, e.g. '(a) - because ...'")
    sub.set_defaults(func=_cmd_block)


def _cmd_block(args) -> int:
    commands.record_blocker(args.task_id, args.kind, args.found, args.options, args.recommend)
    print(f"recorded blocker on {args.task_id}; task is now BLOCKED")
    return 0


def _add_task(subparsers) -> None:
    sub = subparsers.add_parser(
        "task",
        help="record one task's SDD-reported status (DONE|DONE_WITH_CONCERNS|PARKED)",
    )
    sub.add_argument("--id", required=True, dest="task_id", help="the story id, e.g. SK-041")
    sub.add_argument(
        "--status",
        required=True,
        help="DONE | DONE_WITH_CONCERNS | PARKED (BLOCKED belongs to `block`; NEEDS_CONTEXT is not a state)",
    )
    sub.add_argument(
        "--note",
        help="required for DONE_WITH_CONCERNS (the concern, verbatim); on DONE it carries the "
             "Minor-findings roll-up; on PARKED it names the blocker that parked the task",
    )
    sub.set_defaults(func=_cmd_task)


def _cmd_task(args) -> int:
    state = commands.record_task_status(args.task_id, args.status, note=args.note)
    task = next(t for t in state.tasks if t.id == args.task_id)
    print(f"recorded {task.id}: {task.status.value}")
    return 0


def _add_tasks(subparsers) -> None:
    sub = subparsers.add_parser("tasks", help="load tasks[] from a refined sprint doc's proof lines")
    sub.add_argument("--from", required=True, dest="doc", metavar="DOC",
                     help="the refined sprint doc; its proof lines are the task list")
    sub.add_argument("--plan", help="the dev plan; every story must be named by a '### Task N ... (SK-0xx)' heading")
    sub.set_defaults(func=_cmd_tasks)


def _cmd_tasks(args) -> int:
    state = commands.load_tasks(args.doc, plan=args.plan)
    print(f"loaded {len(state.tasks)} tasks: " + ", ".join(task.id for task in state.tasks))
    return 0


def _add_advance(subparsers) -> None:
    sub = subparsers.add_parser("advance", help="advance one stage forward, if preconditions hold")
    sub.add_argument("--to", required=True, dest="to", metavar="STAGE",
                     help="target stage (must be the next stage in SCOPE-REFINE-PLAN-EXECUTE-REVIEW)")
    sub.set_defaults(func=_cmd_advance)


def _cmd_advance(args) -> int:
    state = commands.advance_stage(args.to)
    print(f"advanced to {state.stage.value}")
    return 0


def _add_plan_guard(subparsers) -> None:
    sub = subparsers.add_parser(
        "plan-guard",
        help="did HEAD move across the PLAN dispatch? exit 1 means the plan agent committed",
    )
    sub.add_argument("--before", required=True, help="git rev-parse HEAD, taken BEFORE the dispatch")
    sub.add_argument("--after", required=True, help="git rev-parse HEAD, taken AFTER the dispatch")
    sub.set_defaults(func=_cmd_plan_guard)


def _cmd_plan_guard(args) -> int:
    if plan_guard.head_moved(args.before, args.after):
        print(plan_guard.refusal(args.before, args.after), file=sys.stderr)
        return 1
    print(f"plan-guard: HEAD unchanged ({args.before.strip()})")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except StateError as error:
        print(f"supskill-state: refused: {error}", file=sys.stderr)
        return 1
