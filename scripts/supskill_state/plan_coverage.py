"""The plan-task <-> story join key (SK-033, S4 DoR finding 3).

tasks[] is story-shaped (SK-0xx): parse_proof_lines keys on the story id and
Task stores id/seam/provable. SDD reports per PLAN TASK ("Task 3 DONE"). Nothing
joins the two vocabularies, so E5's status mapping would have had nothing to map
through - unless every plan task heading names the story it serves:

    ### Task N: <what> (SK-0xx)          # serves a backlog story
    ### Task N: <what> (process)         # serves none (the demo checklist, the backlog deltas)

This module enforces exactly that, in both directions, and nothing else. Whether
a plan task actually IMPLEMENTS the story it names is judgment - the reviewer's
and the operator's at Gate 2 - and this validator does not pretend otherwise
(F-4's shape: loud and auditable, not impossible).
"""

from __future__ import annotations

import re

PROCESS_MARKER = "(process)"

_TASK_HEADING = re.compile(r"^###\s+Task\s+\d+\b.*$")
_STORY_ID = re.compile(r"SK-\d+")
_FENCE = re.compile(r"^\s*```")


def plan_task_headings(text: str) -> list[str]:
    """Every '### Task N ...' heading line, in document order.

    Skips lines inside fenced code blocks (```` ``` ```` or ```` ```lang ````): dev plans
    routinely quote example task briefs - including their test-fixture code - verbatim
    inside fences, and a quoted example is not a real task.
    """
    headings: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence and _TASK_HEADING.match(line):
            headings.append(line.rstrip())
    return headings


def validate_plan_coverage(plan_text: str, story_ids: list[str]) -> list[str]:
    """One message per violation; an empty list means the join is clean both ways."""
    headings = plan_task_headings(plan_text)
    if not headings:
        return ["the plan has no `### Task N: ...` headings - there is nothing to join the stories through"]

    known = set(story_ids)
    named: set[str] = set()
    failures: list[str] = []
    for heading in headings:
        found = _STORY_ID.findall(heading)
        if not found:
            if PROCESS_MARKER not in heading:
                failures.append(f"plan task names no story and is not marked {PROCESS_MARKER}: {heading}")
            continue
        for story in found:
            if story in known:
                named.add(story)
            else:
                failures.append(f"plan task names an unknown story {story}: {heading}")

    for story in story_ids:
        if story not in named:
            failures.append(f"{story}: no plan task heading names it - the plan drops this story")
    return failures
