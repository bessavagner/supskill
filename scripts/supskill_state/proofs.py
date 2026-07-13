"""Proof-line grammar and parser (SK-022; vocabulary stolen from D9's taxonomy).

One exact line per story, directly under the story's ### SK-xxx heading:

    - **proof:** seam=unit|integration|app-level|e2e · impact=none|local|cross-surface|journey
      · provable=offline|operator

This module is the vocabulary's single owner, and it enforces vocabulary ONLY.
Whether `seam=e2e · provable=offline` is a *lie* is judgment - the refine
reviewer's and the operator's at Gate 1 - and this validator does not pretend
otherwise. Typical mapping: unit/integration -> offline; app-level/e2e ->
operator; a mixed story classifies by its least-provable seam.

The missing-proof-line check applies only to ### SK-xxx headings inside a
`## Stories` section; token and duplicate checks apply document-wide. SK-033
(E4) loads tasks[] from these lines - it adds the verb, never a second parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import StateError

SEAM_TOKENS: tuple[str, ...] = ("unit", "integration", "app-level", "e2e")
IMPACT_TOKENS: tuple[str, ...] = ("none", "local", "cross-surface", "journey")
PROVABLE_TOKENS: tuple[str, ...] = ("offline", "operator")

GRAMMAR_LINE = (
    "- **proof:** seam=" + "|".join(SEAM_TOKENS)
    + " · impact=" + "|".join(IMPACT_TOKENS)
    + " · provable=" + "|".join(PROVABLE_TOKENS)
)

# anchored at column 0: the grammar exemplar inside indented code blocks must not parse
_PROOF = re.compile(r"^- \*\*proof:\*\* seam=(\S+) · impact=(\S+) · provable=(\S+)(?:\s.*)?$")
_STORY = re.compile(r"^###\s+.*?(SK-\d+)")
_SECTION = re.compile(r"^##\s+(?!#)(.+?)\s*$")


@dataclass(frozen=True)
class ProofLine:
    story: str
    seam: str
    impact: str
    provable: str


def parse_proof_lines(text: str) -> list[ProofLine]:
    """Every proof line, in document order; raises StateError listing every violation."""
    proofs: list[ProofLine] = []
    violations: list[str] = []
    seen: set[str] = set()
    story: str | None = None
    in_stories = False
    required: list[str] = []  # SK headings inside the Stories section, in order

    for number, line in enumerate(text.splitlines(), start=1):
        section = _SECTION.match(line)
        if section:
            in_stories = section.group(1).strip().lower() == "stories"
            continue
        heading = _STORY.match(line)
        if heading:
            story = heading.group(1)
            if in_stories:
                required.append(story)
            continue
        match = _PROOF.match(line)
        if not match:
            continue
        if story is None:
            violations.append(f"line {number}: proof line before any ### SK-xxx heading")
            continue
        seam, impact, provable = match.groups()
        for token, allowed, field in (
            (seam, SEAM_TOKENS, "seam"),
            (impact, IMPACT_TOKENS, "impact"),
            (provable, PROVABLE_TOKENS, "provable"),
        ):
            if token not in allowed:
                violations.append(
                    f"{story}: unknown {field} token {token!r} (expected one of {'|'.join(allowed)})"
                )
        if story in seen:
            violations.append(f"{story}: duplicate proof line")
            continue
        seen.add(story)
        proofs.append(ProofLine(story=story, seam=seam, impact=impact, provable=provable))

    for story_id in required:
        if story_id not in seen:
            violations.append(f"{story_id}: story in the Stories section has no proof line")

    if violations:
        raise StateError("proof grammar: " + "; ".join(violations))
    return proofs
