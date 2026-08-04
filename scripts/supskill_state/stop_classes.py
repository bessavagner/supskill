"""SK-130: which stops the conductor may remediate, and which must stay refusals.

Every seam where supskill stops carries exactly one class. `remediable` means the
stop names a known, safe, specific action and the conductor takes it. `evidential`
means acting on the stop would destroy the signal it exists to raise - a
regenerated review package comes back clean, which is precisely what SK-104 was
built to prevent. `no_stop` is a verb that cannot refuse in a way an operator has
to act on.

The table is total over the CLI's verbs, and tests/test_stop_classes.py enforces
that. Without the test this decays into per-run prose judgment, which is SK-108's
failure mode: open across four runs and three contradictory readings.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import StateError

REMEDIABLE = "remediable"
EVIDENTIAL = "evidential"
NO_STOP = "no_stop"


@dataclass(frozen=True)
class Stop:
    id: str
    verb: str
    condition: str
    stop_class: str
    action: str | None = None


STOPS: tuple[Stop, ...] = (
    Stop(
        id="init.archive.decided",
        verb="init",
        condition="a different sprint is on disk and its G3 decision IS recorded",
        stop_class=REMEDIABLE,
        action="run init <id> --archive, carrying every operator flag forward verbatim",
    ),
    Stop(
        id="init.archive.undecided",
        verb="init",
        condition="the sprint on disk rests at REVIEW with no G3 decision (SK-115)",
        stop_class=EVIDENTIAL,
    ),
    Stop(
        id="artifact-guard.untracked",
        verb="artifact-guard",
        condition="a recorded artifact is untracked by git",
        stop_class=REMEDIABLE,
        action="stage and commit exactly the recorded artifact paths",
    ),
    Stop(
        id="review-guard.stale",
        verb="review-guard",
        condition="HEAD moved past the recorded package, or none was recorded",
        stop_class=EVIDENTIAL,
    ),
    Stop(
        id="plan-guard.commits",
        verb="plan-guard",
        condition="the plan agent produced commits",
        stop_class=EVIDENTIAL,
    ),
    Stop(
        id="commit-scope-guard.foreign",
        verb="commit-scope-guard",
        condition="a commit range swept foreign harness state in",
        stop_class=EVIDENTIAL,
    ),
    Stop(
        id="replan-guard.north-star",
        verb="replan-guard",
        condition="the shape reads as a north-star reset (invariant 7)",
        stop_class=EVIDENTIAL,
    ),
    Stop(
        id="preflight.unresolvable",
        verb="preflight",
        condition="a skill a later stage dispatches will not resolve",
        stop_class=EVIDENTIAL,
    ),
    Stop(
        id="tasks.coverage",
        verb="tasks",
        condition="the dev plan does not cover the sprint doc's stories",
        stop_class=EVIDENTIAL,
    ),
    Stop(id="show.none", verb="show", condition="reads only", stop_class=NO_STOP),
    Stop(id="config.none", verb="config", condition="reads or sets config", stop_class=NO_STOP),
    Stop(id="artifact.none", verb="artifact", condition="records a path", stop_class=NO_STOP),
    Stop(id="gate.none", verb="gate", condition="records a decision", stop_class=NO_STOP),
    Stop(id="block.none", verb="block", condition="records a blocker", stop_class=NO_STOP),
    Stop(id="task.none", verb="task", condition="records a status", stop_class=NO_STOP),
    Stop(id="advance.none", verb="advance", condition="validates a transition", stop_class=NO_STOP),
    Stop(id="package.none", verb="package", condition="records a package", stop_class=NO_STOP),
    Stop(id="worktree.none", verb="worktree", condition="creates the dispatch root", stop_class=NO_STOP),
    Stop(id="cost.none", verb="cost", condition="records telemetry", stop_class=NO_STOP),
    Stop(id="review.none", verb="review", condition="records a finding", stop_class=NO_STOP),
    Stop(id="action.none", verb="action", condition="records an action", stop_class=NO_STOP),
)


def classify(stop_id: str) -> Stop:
    for stop in STOPS:
        if stop.id == stop_id:
            return stop
    raise StateError(f"unknown stop id {stop_id!r}; expected one of {sorted(s.id for s in STOPS)}")


def verbs_covered() -> set[str]:
    return {stop.verb for stop in STOPS}
