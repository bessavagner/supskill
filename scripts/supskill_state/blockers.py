"""SK-103: which recorded blockers are still live, derived from their tasks.

`block` mirrors a blocker into state.blockers and flips its task to BLOCKED, and
nothing ever took it back out. On playset s1 both blockers were resolved, both
tasks moved on, and `show` still reported "open blockers: 2" - so Gate 3, the one
irreversible decision in the product, presented two settled questions as live
ones and the operator reconstructed resolution from the tasks trail by hand.

Resolution is DERIVED here, never recorded. `task --id X --status DONE --note`
already writes how a blocker was settled to runs/<id>/tasks.jsonl; a second verb
that could move a blocker independently could also disagree with its task, and
then Gate 3 would have two answers and no rule for picking one.

The resolving set is DONE and DONE_WITH_CONCERNS - successful terminal statuses.
PARKED is terminal too, and deliberately excluded: a parked task is one that never
ran because it sat downstream of a blocker, which is the opposite of settled. The
backlog row says "terminal non-blocked status"; this is narrower on purpose, and
the divergence is recorded rather than the row rewritten.

The ceiling: this says a blocker's task moved on, not that the operator made a
good call. A task marked DONE with an empty note resolves its blocker here.
"""

from __future__ import annotations

from .model import Blocker, Task, TaskStatus

# Successful terminal statuses only. PARKED is terminal but means "never ran".
RESOLVING_STATUSES: frozenset[TaskStatus] = frozenset(
    (TaskStatus.DONE, TaskStatus.DONE_WITH_CONCERNS)
)


def resolving_status(blocker: Blocker, tasks: list[Task]) -> TaskStatus | None:
    """The status that settled this blocker, or None while it is still open.

    A blocker whose task is not in `tasks` at all stays open: missing evidence is
    never read as resolution.
    """
    task = next((t for t in tasks if t.id == blocker.task), None)
    if task is None or task.status not in RESOLVING_STATUSES:
        return None
    return task.status


def partition(blockers: list[Blocker], tasks: list[Task]) -> tuple[list[Blocker], list[Blocker]]:
    """`(open, resolved)`, each preserving the order the blockers were recorded in."""
    open_: list[Blocker] = []
    resolved: list[Blocker] = []
    for blocker in blockers:
        (resolved if resolving_status(blocker, tasks) else open_).append(blocker)
    return open_, resolved
