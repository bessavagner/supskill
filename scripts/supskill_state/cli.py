"""Thin argparse shim. The CLI is wiring; the logic lives in commands.py."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import (
    artifact_tracking,
    commands,
    commit_scope,
    config,
    plan_guard,
    preflight,
    replan_guard,
    store,
    worktree,
)
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
    _add_commit_scope_guard(subparsers)
    _add_replan_guard(subparsers)
    _add_artifact_guard(subparsers)
    _add_preflight(subparsers)
    _add_worktree(subparsers)
    _add_cost(subparsers)
    _add_review(subparsers)
    _add_config(subparsers)
    return parser


def _add_init(subparsers) -> None:
    sub = subparsers.add_parser("init", help="create .supskill/ for a new sprint run")
    sub.add_argument("sprint_id", help="sprint id, e.g. s1 (lowercase [a-z0-9-] after normalizing)")
    sub.add_argument("--slug", help="human slug, e.g. state-spine")
    sub.add_argument("--entry", choices=["SCOPE", "PLAN", "EXECUTE"], default="SCOPE")
    sub.add_argument("--backlog", help="path to the backlog driving this sprint (required when entry is SCOPE)")
    sub.add_argument("--branch", help="git branch for this sprint")
    sub.add_argument(
        "--continues",
        metavar="SPRINT_ID",
        help="the sprint this one continues; defaults to the archived sprint's id on a "
             "PLAN or EXECUTE entry, and is refused on a SCOPE entry",
    )
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
        continues=args.continues,
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
    sub.add_argument("--decision", required=True, choices=["approved", "rejected", "replan"])
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
                     help="target stage (must be the next stage in SCOPE-PLAN-EXECUTE-REVIEW)")
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


def _add_commit_scope_guard(subparsers) -> None:
    sub = subparsers.add_parser(
        "commit-scope-guard",
        help="did a task's commits (BASE..HEAD) sweep in foreign harness state? exit 1 = refuse",
    )
    sub.add_argument("--before", required=True, help="the task's BASE SHA (rev-parse HEAD before the dispatch)")
    sub.add_argument("--after", required=True, help="HEAD after the task's implementer and fix dispatches")
    sub.add_argument("--dir", default=".", dest="root", help="the dispatch root (repo or worktree); default cwd")
    sub.set_defaults(func=_cmd_commit_scope_guard)


def _cmd_commit_scope_guard(args) -> int:
    changed = commit_scope.git_changed_paths(args.root, args.before, args.after)
    foreign = commit_scope.foreign_paths(changed)
    if foreign:
        print(commit_scope.refusal(foreign, args.before, args.after), file=sys.stderr)
        return 1
    print(f"commit-scope-guard: no foreign state in {args.before.strip()}..{args.after.strip()}")
    return 0


def _add_replan_guard(subparsers) -> None:
    sub = subparsers.add_parser(
        "replan-guard",
        help="is this Gate 3 replan shape a supersede, or an amend with no target? exit 1 = refuse",
    )
    sub.add_argument(
        "--shape",
        required=True,
        choices=list(replan_guard.REPLAN_SHAPES),
        help="the conductor's own classification of the operator's Gate 3 answer",
    )
    sub.add_argument(
        "--dir",
        default=None,
        dest="root",
        help="the repo root whose .supskill/ holds this sprint's state; default cwd",
    )
    sub.set_defaults(func=_cmd_replan_guard)


def _cmd_replan_guard(args) -> int:
    # shape 4 is refused for what it is, before any state is read
    if replan_guard.is_supersede(args.shape):
        print(replan_guard.refusal(args.shape), file=sys.stderr)
        return 1
    root = store.resolve_root(Path(args.root) if args.root else None)
    state = store.load_state(store.state_path(root))
    if replan_guard.lacks_backlog_target(args.shape, state.backlog):
        print(replan_guard.target_refusal(args.shape, state.sprint.id), file=sys.stderr)
        return 1
    print(f"replan-guard: {args.shape} is an amending shape; it amends {state.backlog}")
    return 0


def _add_artifact_guard(subparsers) -> None:
    sub = subparsers.add_parser(
        "artifact-guard",
        help="are this sprint's recorded artifacts tracked by git? exit 1 means refuse",
    )
    sub.add_argument(
        "--dir",
        default=None,
        dest="root",
        help="the repo root whose .supskill/ holds this sprint's state; default cwd",
    )
    sub.set_defaults(func=_cmd_artifact_guard)


def _cmd_artifact_guard(args) -> int:
    root = store.resolve_root(Path(args.root) if args.root else None)
    state = store.load_state(store.state_path(root))
    recorded = [path for path in state.artifacts.values() if path]
    if not recorded:
        print("artifact-guard: no artifacts recorded; there is nothing to check")
        return 0
    tracked = artifact_tracking.git_tracked(str(root), recorded)
    missing = artifact_tracking.untracked(recorded, tracked, root=str(root))
    if missing:
        print(artifact_tracking.refusal(missing), file=sys.stderr)
        return 1
    print(f"artifact-guard: all {len(recorded)} recorded artifacts are tracked by git")
    return 0


def _add_preflight(subparsers) -> None:
    sub = subparsers.add_parser(
        "preflight",
        help="refuse at run start if a still-to-run stage's dispatched skill will not resolve",
    )
    sub.add_argument("--stage", required=True, help="current stage from show --json (SCOPE|PLAN|EXECUTE|REVIEW)")
    sub.add_argument(
        "--skill",
        action="append",
        default=[],
        dest="skills",
        metavar="NAME=DIR",
        help="a resolved skill as name=base-dir; repeat the flag. Omit one you could not resolve.",
    )
    sub.set_defaults(func=_cmd_preflight)


def _cmd_preflight(args) -> int:
    resolved: dict[str, str] = {}
    for item in args.skills:
        name, sep, base = item.partition("=")
        if not sep or not name or not base:
            raise StateError(f"--skill expects NAME=DIR, got {item!r}")
        resolved[name] = base
    problems = preflight.unresolved(args.stage, resolved)
    if problems:
        print(preflight.refusal(args.stage, problems), file=sys.stderr)
        return 1
    print(f"preflight: every skill the stages from {args.stage} onward dispatch resolves")
    return 0


def _add_worktree(subparsers) -> None:
    sub = subparsers.add_parser(
        "worktree",
        help="isolate EXECUTE into .worktrees/<branch>, syncing artifacts into it",
    )
    sub.add_argument("--branch", required=True, help="branch name for the worktree")
    sub.add_argument(
        "--artifact",
        action="append",
        default=[],
        dest="artifacts",
        help="a file to copy from the repo root into the worktree; repeat the flag",
    )
    sub.set_defaults(func=_cmd_worktree)


def _cmd_worktree(args) -> int:
    path, created = worktree.ensure_worktree(Path.cwd(), args.branch, args.artifacts)
    status = "created" if created else "reused"
    print(f"worktree ready at {path} ({status})")
    return 0


def _add_cost(subparsers) -> None:
    sub = subparsers.add_parser(
        "cost", help="record one subagent dispatch's token usage against the running sprint"
    )
    sub.add_argument("--stage", required=True, help="SCOPE | PLAN | EXECUTE | REVIEW")
    sub.add_argument(
        "--label",
        help="which dispatch within the stage, e.g. implementer|task-reviewer|fix|reviewer-a",
    )
    sub.add_argument("--tokens", required=True, type=int, help="the dispatch's reported subagent_tokens")
    sub.add_argument("--tool-uses", type=int, dest="tool_uses", help="the dispatch's reported tool_uses")
    sub.add_argument("--duration-ms", type=int, dest="duration_ms", help="the dispatch's reported duration_ms")
    sub.set_defaults(func=_cmd_cost)


def _cmd_cost(args) -> int:
    commands.record_cost(
        args.stage,
        args.tokens,
        label=args.label,
        tool_uses=args.tool_uses,
        duration_ms=args.duration_ms,
    )
    where = f"{args.stage}/{args.label}" if args.label else args.stage
    print(f"recorded cost: {where} tokens={args.tokens}")
    return 0


def _add_review(subparsers) -> None:
    sub = subparsers.add_parser(
        "review", help="record one aggregated PAR finding to runs/<id>/review.jsonl"
    )
    sub.add_argument("--reviewer", required=True, help="reviewer-a | reviewer-b | both")
    sub.add_argument("--severity", required=True, help="Critical | Important | Minor")
    sub.add_argument("--confidence", required=True, help="high | actionable")
    sub.add_argument("--finding", required=True, help="what was found, in your own words")
    sub.add_argument("--location", required=True, help="file:line or path")
    sub.set_defaults(func=_cmd_review)


def _cmd_review(args) -> int:
    commands.record_review_finding(args.reviewer, args.severity, args.confidence, args.finding, args.location)
    print(f"recorded review finding: {args.reviewer} {args.severity}/{args.confidence}")
    return 0


def _add_config(subparsers) -> None:
    sub = subparsers.add_parser(
        "config", help="read or set project-level config, e.g. the story-id prefix"
    )
    sub.add_argument(
        "--story-id-prefix",
        dest="story_id_prefix",
        help="uppercase prefix used by this project's story ids, e.g. BLK for BLK-103 (default: SK)",
    )
    sub.add_argument(
        "--get",
        action="store_true",
        help="print the configured story-id prefix (SK if unset) and exit",
    )
    sub.set_defaults(func=_cmd_config)


def _cmd_config(args) -> int:
    if args.get:
        print(config.load_story_id_prefix())
        return 0
    if not args.story_id_prefix:
        raise StateError("config: pass --story-id-prefix <PREFIX> to set, or --get to read")
    previous = commands.set_story_id_prefix(args.story_id_prefix)
    print(f"set story id prefix: {args.story_id_prefix} (was: {previous})")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except StateError as error:
        print(f"supskill-state: refused: {error}", file=sys.stderr)
        return 1
