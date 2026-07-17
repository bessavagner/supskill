"""Citation audit (SK-024): the mechanical floor under REFINE (F-5, S3 DoR finding 4).

Extracts backtick-wrapped `path:line` / `path:start-end` tokens (the path must
carry a file extension - `file:line` prose placeholders and skill names like
`pm-execution:sprint-plan` are not citations) and verifies each resolves.

Resolution is by path suffix, matched on whole segments: sprint docs cite bare
module names (`commands.py:178`) for nested files, so a citation resolves iff
at least one file under the root whose path ends with the cited path has at
least the cited number of lines. .git, __pycache__, .venv and node_modules are
pruned.

Honesty (stated in --help too): this proves citations RESOLVE, not that the
claims they support are true. Truth stays with the reviewer and the operator
at Gate 1; the script only removes the cheapest way to fake depth (F-4's
shape: loud and auditable, not impossible).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import config
from .errors import StateError
from .proofs import parse_proof_lines

_CITATION = re.compile(r"`([A-Za-z0-9_\-./]+\.[A-Za-z0-9_]+):(\d+)(?:-(\d+))?`")
_SKIP_DIRS = frozenset((".git", "__pycache__", ".venv", "node_modules"))


def _tree_index(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and not _SKIP_DIRS.intersection(path.relative_to(root).parts)
    ]


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def audit_citations(text: str, root: Path) -> list[str]:
    """One message per unique unresolved citation; empty means every citation resolves."""
    failures: list[str] = []
    seen: set[str] = set()
    index: list[Path] | None = None
    for match in _CITATION.finditer(text):
        token = match.group(0)
        if token in seen:
            continue
        seen.add(token)
        cited = match.group(1)
        start = int(match.group(2))
        end = int(match.group(3)) if match.group(3) else start
        if end < start:
            failures.append(f"{token}: backwards range")
            continue
        if index is None:
            index = _tree_index(root)
        suffix = Path(cited).parts
        candidates = [p for p in index if p.relative_to(root).parts[-len(suffix):] == suffix]
        if not candidates:
            failures.append(f"{token}: no file matching {cited} under {root}")
            continue
        longest = max(_line_count(path) for path in candidates)
        if longest < end:
            failures.append(f"{token}: cites line {end} but the longest matching file has {longest} lines")
    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="supskill-audit",
        description=(
            "Verify every backtick-wrapped path:line citation in a doc resolves against "
            "the working tree (paths resolve from the cwd). This proves citations resolve "
            "- NOT that the claims they support are true; truth stays with the reviewer "
            "and the operator at the gate."
        ),
    )
    parser.add_argument("doc", help="markdown doc to audit")
    parser.add_argument(
        "--proofs",
        action="store_true",
        help="also validate the doc's proof lines against the SK-022 grammar (proofs.py is the authority)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    doc = Path(args.doc)
    if not doc.is_file():
        print(f"supskill-audit: no such doc: {args.doc}", file=sys.stderr)
        return 1
    text = doc.read_text(encoding="utf-8")
    failures = audit_citations(text, Path.cwd())
    if args.proofs:
        try:
            story_prefix = config.load_story_id_prefix(Path.cwd())
            parse_proof_lines(text, story_prefix=story_prefix)
        except StateError as error:
            failures.append(str(error))
    if failures:
        for failure in failures:
            print(f"supskill-audit: {failure}", file=sys.stderr)
        return 1
    print("supskill-audit: ok")
    return 0
