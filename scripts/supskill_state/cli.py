"""Thin argparse shim. The CLI is wiring; the logic lives in commands.py."""

from __future__ import annotations

import argparse
import sys

from . import commands
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
    return parser


def _add_init(subparsers) -> None:
    sub = subparsers.add_parser("init", help="create .supskill/ for a new sprint run")
    sub.add_argument("sprint_id", help="sprint id, e.g. s1 (lowercase [a-z0-9-] after normalizing)")
    sub.add_argument("--slug", help="human slug, e.g. state-spine")
    sub.add_argument("--entry", choices=["SCOPE", "PLAN", "EXECUTE"], default="SCOPE")
    sub.add_argument("--backlog", help="path to the backlog driving this sprint")
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except StateError as error:
        print(f"supskill-state: refused: {error}", file=sys.stderr)
        return 1
