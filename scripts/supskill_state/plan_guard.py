"""The HEAD guard (SK-031, layer 2; S4 DoR findings 1 and 6).

Layer 1 is prose: plan-prompt.md pre-answers writing-plans' Execution Handoff
(subagent-driven, always) and forbids the two execution sub-skills. Prose is not
enforcement, so this is layer 2: the conductor records `git rev-parse HEAD`
before the PLAN dispatch and compares after. If HEAD moved, the plan agent
committed - it executed - and the run stops for the operator.

The ceiling, stated here and in the refusal text because it will be oversold
otherwise: this catches an agent that COMMITS, which is precisely what
subagent-driven-development does, per task, by design. An agent that edits the
working tree without committing walks past it. That is F-4's ceiling - loud and
auditable, not impossible. This is not a sandbox and is not sold as one.
"""

from __future__ import annotations

from .errors import StateError


def head_moved(before: str, after: str) -> bool:
    """True iff the two SHAs differ. An unreadable HEAD raises - it is never a silent pass."""
    before, after = before.strip(), after.strip()
    if not before or not after:
        raise StateError(
            "the HEAD guard needs two non-empty SHAs (git rev-parse HEAD, before and after the "
            "dispatch); a HEAD that cannot be read is never a silent pass"
        )
    return before != after


def refusal(before: str, after: str) -> str:
    """What the conductor reports, verbatim, when the plan stage produced commits."""
    return (
        "the PLAN stage produced commits, so the plan agent executed rather than planned.\n"
        f"  HEAD before the dispatch: {before.strip()}\n"
        f"  HEAD after the dispatch:  {after.strip()}\n"
        "a plan is a document; a plan is not a commit. This run is stopped so you can inspect "
        f"the commits yourself: git log --oneline {before.strip()}..{after.strip()}\n"
        "Nothing was recorded and no gate was called: state.json still reads PLAN and G2 is "
        "still open.\n"
        "This guard's ceiling, stated plainly: it catches an agent that COMMITS. An agent that "
        "edits files without committing walks past it. It is not a sandbox."
    )
