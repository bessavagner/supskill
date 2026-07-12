"""Thin argparse shim. The CLI is wiring; the logic lives in commands.py."""

from __future__ import annotations

import argparse
import sys

from .errors import StateError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="supskill-state",
        description=(
            "State spine for supskill sprints: "
            "the only permitted mutator of .supskill/state.json."
        ),
    )
    parser.add_subparsers(dest="command", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except StateError as error:
        print(f"supskill-state: refused: {error}", file=sys.stderr)
        return 1
