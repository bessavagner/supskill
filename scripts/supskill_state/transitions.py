"""Stage transitions and their preconditions (D2).

Preconditions attach to *transitions taken*, not to stages: a sprint that
init's at EXECUTE never crosses the G2 check; a sprint entering at SCOPE
cannot reach EXECUTE without G1 and G2 approved. advance is strictly
one-step-forward; the replan shapes that move backwards are E6's explicit
verbs, never a loosened advance.
"""

from __future__ import annotations

from pathlib import Path

from .model import STAGE_ORDER, TERMINAL_STATUSES, Stage, State


def next_stage(current: Stage) -> Stage | None:
    index = STAGE_ORDER.index(current)
    if index + 1 == len(STAGE_ORDER):
        return None
    return STAGE_ORDER[index + 1]


def failed_preconditions(state: State, to: Stage, root: Path) -> list[str]:
    """Empty list means the transition may proceed. Gate failures are listed first."""
    failures: list[str] = []
    if to is Stage.PLAN:
        _check_gate(state, "G1_sprint_doc", failures)
        _check_artifact(state, "sprint_doc", root, failures)
    elif to is Stage.EXECUTE:
        _check_gate(state, "G2_plan", failures)
        _check_artifact(state, "dev_plan", root, failures)
    elif to is Stage.REVIEW:
        open_tasks = [task.id for task in state.tasks if task.status not in TERMINAL_STATUSES]
        if open_tasks:
            failures.append(
                "every task must be terminal (DONE|DONE_WITH_CONCERNS|BLOCKED|PARKED); "
                "still open: " + ", ".join(open_tasks)
            )
    return failures


def _check_gate(state: State, key: str, failures: list[str]) -> None:
    value = state.gates[key]
    if value != "approved":
        shown = value if value is not None else "null"
        failures.append(f"{key} must be approved (currently {shown})")


def _check_artifact(state: State, key: str, root: Path, failures: list[str]) -> None:
    value = state.artifacts[key]
    if not value:
        failures.append(f"artifacts.{key} is not recorded")
    elif not (root / value).exists():
        failures.append(f"artifacts.{key} points at a missing file: {value}")
