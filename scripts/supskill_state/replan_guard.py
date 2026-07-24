"""SK-053: refuse a north-star-supersede reading of a Gate 3 answer, structurally.

Invariant 7: "the conductor never supersedes a backlog on its own - a
north-star reset is operator-authored, full stop." The backlog gives no
procedure for DETECTING a shape-4-shaped Gate 3 answer, and this module does
not try to build one: classifying what the operator's free-text answer means
is the conductor's own judgment, done in prose, at Gate 3 (Task 8). What this
module gives that judgment is a name for the fourth shape and a refusal that
fires the instant that name is reached - the same shape as plan_guard.py's
head_moved: a pure check plus a call site that reports and stops.

The structural half of invariant 7 already holds today, for free: state.backlog
is assigned exactly once in the whole codebase, inside init_sprint
(scripts/supskill_state/commands.py:74-90), and no verb anywhere edits
backlog.md's prose - the only thing that has ever changed that file is a
person, by hand, in a docs: commit. The regression tests beside this module
prove both halves of that claim, not merely assert them.
"""

from __future__ import annotations

from .errors import StateError

# the design's own table (docs/.ai/reports/2026-07-12-supskill-design-decisions.md:244-254)
REPLAN_SHAPES: tuple[str, ...] = (
    "generative-writeback",
    "park-at-boundary",
    "fork-on-live-evidence",
    "north-star-reset",
)

AMENDING_SHAPES: tuple[str, ...] = REPLAN_SHAPES[:3]
_SUPERSEDE_SHAPE = REPLAN_SHAPES[3]


def is_supersede(shape: str) -> bool:
    """True iff this classification is the one shape the conductor may never perform."""
    if shape not in REPLAN_SHAPES:
        raise StateError(f"unknown replan shape {shape!r}; expected one of {list(REPLAN_SHAPES)}")
    return shape == _SUPERSEDE_SHAPE


def refusal(shape: str) -> str:
    """What the conductor reports, verbatim, when a Gate 3 answer reads as shape 4."""
    if not is_supersede(shape):
        raise StateError(f"refusal() called on {shape!r}, which is not the supersede shape")
    return (
        "this Gate 3 answer reads as a north-star supersede - replacing backlog.md wholesale, "
        "not amending it.\n"
        "The conductor is structurally unable to perform this: no code path in this skill "
        "rewrites backlog.md's North star section or repoints state.json.backlog (invariant 7).\n"
        "Nothing was drafted and nothing was executed. The move is the operator's alone: author "
        "the new backlog by hand (or with whatever process produced this one), then start the "
        "next sprint against it.\n"
        "This run is stopped for you to take that step; it is not offered here for convenience."
    )


def lacks_backlog_target(shape: str, backlog: str | None) -> bool:
    """True iff this amending shape has no recorded backlog to amend (SK-114).

    The supersede shape is never judged here: it is refused for what it is,
    before any state is read, so it returns False and reaches its own refusal.
    An unknown shape still raises, via is_supersede - the vocabulary has one
    owner and this is not a second one.

    What this asks is narrow on purpose: was a destination AUTHORIZED, not is
    the writeback correct. On ledgerus s6 the conductor inferred the target
    from artifacts.sprint_doc's parent directory and inferred it right; SCOPE's
    own rule is that the recorded artifact is the only authority anything
    downstream reads, and an inference is not a record.
    """
    if is_supersede(shape):
        return False
    return not (backlog or "").strip()


def target_refusal(shape: str, sprint_id: str) -> str:
    """What the conductor reports, verbatim, when an amending shape has no target."""
    if is_supersede(shape):
        raise StateError(
            f"target_refusal() called on {shape!r}; the supersede shape has its own refusal"
        )
    return (
        f"this Gate 3 answer reads as {shape}, which amends the backlog - and this sprint "
        "has no backlog to amend.\n"
        f"state.json records backlog: null for sprint {sprint_id}, so no destination for "
        "the writeback was ever authorized. A path inferred from artifacts.sprint_doc's "
        "directory is a guess: the recorded artifact is the only authority anything "
        "downstream reads, and an inference is not a record.\n"
        "Nothing was drafted and nothing was written. The move is the operator's: name the "
        "backlog this sprint amends when you start the next one -\n"
        "  supskill-state init <next-id> --archive --backlog <path> "
        "(carrying this sprint's --branch and --slug)\n"
        "This guard checks that a target was authorized, not that a writeback would be "
        "correct. A wrong-but-recorded backlog path passes it."
    )
