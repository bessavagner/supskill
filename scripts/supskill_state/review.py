"""PAR's severity/confidence vocabulary and its aggregation rule (SK-050).

D9: two reviewer subagents on identical input, aggregated by a FIXED rule -
same finding reported by both -> confidence=high; found by one reviewer only
-> confidence=actionable; the two reviewers disagree on severity -> the worse
one wins, always, no negotiation. Ranked Critical > Important > Minor - the
same three-level vocabulary this repo already imported from SDD for EXECUTE's
fix trigger and roll-up (skills/supskill/SKILL.md:383-385).

Which finding from reviewer-a corresponds to which from reviewer-b is the
conductor's own judgment, done in prose at REVIEW time - matching two finding
lists is not a pure function of their contents, and this module does not try.
What IS pure, and is this story's whole offline-provable slice: given one
already-matched finding's severity as reported by each reviewer that DID
report it (None for a reviewer that did not), what confidence and severity
the fixed rule assigns. That is the whole rule, stated once, in aggregate().
"""

from __future__ import annotations

from .errors import StateError

# worst-first: index 0 always wins a disagreement
SEVERITY_TOKENS: tuple[str, ...] = ("Critical", "Important", "Minor")
CONFIDENCE_TOKENS: tuple[str, ...] = ("high", "actionable")
REVIEWER_TOKENS: tuple[str, ...] = ("reviewer-a", "reviewer-b", "both")


def parse_severity(value: str, where: str) -> str:
    if value not in SEVERITY_TOKENS:
        raise StateError(f"{where}: unknown severity {value!r}; expected one of {list(SEVERITY_TOKENS)}")
    return value


def parse_confidence(value: str, where: str) -> str:
    if value not in CONFIDENCE_TOKENS:
        raise StateError(f"{where}: unknown confidence {value!r}; expected one of {list(CONFIDENCE_TOKENS)}")
    return value


def parse_reviewer(value: str, where: str) -> str:
    if value not in REVIEWER_TOKENS:
        raise StateError(f"{where}: unknown reviewer {value!r}; expected one of {list(REVIEWER_TOKENS)}")
    return value


def worse_severity(a: str, b: str) -> str:
    """Critical > Important > Minor. The worse of the two always wins - no negotiation."""
    return a if SEVERITY_TOKENS.index(a) <= SEVERITY_TOKENS.index(b) else b


def aggregate(severity_a: str | None, severity_b: str | None) -> tuple[str, str]:
    """The whole aggregation rule, as a pure function of an already-matched finding.

    severity_a / severity_b: the severity EACH reviewer reported for this ONE
    matched finding, or None if that reviewer did not report it. Matching
    findings across the two reviewers' lists is the conductor's job, done
    before this is ever called - this function never sees the raw lists.
    """
    if severity_a is not None and severity_b is not None:
        return "high", worse_severity(severity_a, severity_b)
    single = severity_a or severity_b
    if single is None:
        raise StateError("aggregate: at least one reviewer must have reported this finding")
    return "actionable", single
