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

_TASK_HEADING = re.compile(r"^ {0,3}###\s+Task\s+\d+\b.*$")
# A CommonMark fence line: 0-3 leading spaces, then a run of 3+ of the same
# fence character (backtick or tilde), then the rest of the line (info string
# on an opener, or the trailing-whitespace check on a closer).
_FENCE_LINE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def _story_id_pattern(story_prefix: str) -> re.Pattern[str]:
    return re.compile(rf"{re.escape(story_prefix)}-\d+")


def plan_task_headings(text: str) -> list[str]:
    """Every '### Task N ...' heading line, in document order.

    Skips lines inside fenced code blocks, per the CommonMark fence rules that
    matter here: dev plans routinely quote example task briefs - including their
    test-fixture code - verbatim inside fences, and a quoted example is not a
    real task.

    - Both backtick (```` ``` ````) and tilde (``~~~``) fences are recognized as
      openers.
    - A backtick opener's info string must not itself contain a backtick (a line
      like ```` ```inline``` ```` is therefore not an opener at all, so it cannot
      poison fence state for the rest of the document); a tilde opener's info
      string is unrestricted.
    - A closer must use the same character as its opener and a run at least as
      long (so a shorter nested run, e.g. a 3-backtick example inside a 4-backtick
      fence, does not close the outer fence) and nothing but whitespace after the
      run.
    - By design, an unclosed fence runs to end of file: every line after it,
      including real task headings, is treated as fenced and dropped. This fails
      safe (over-refuses) rather than guessing where an unterminated fence ends.
    """
    headings: list[str] = []
    fence_char: str | None = None
    fence_len = 0
    for line in text.splitlines():
        match = _FENCE_LINE.match(line)
        if fence_char is None:
            if match:
                run, info = match.group(1), match.group(2)
                char = run[0]
                if char == "`" and "`" in info:
                    pass  # not a valid opening fence - info string bars a backtick
                else:
                    fence_char, fence_len = char, len(run)
                    continue
            if _TASK_HEADING.match(line):
                headings.append(line.rstrip())
        elif match and match.group(1)[0] == fence_char and len(match.group(1)) >= fence_len:
            if not match.group(2).strip():
                fence_char, fence_len = None, 0
    return headings


def validate_plan_coverage(plan_text: str, story_ids: list[str], story_prefix: str = "SK") -> list[str]:
    """One message per violation; an empty list means the join is clean both ways."""
    headings = plan_task_headings(plan_text)
    if not headings:
        return ["the plan has no `### Task N: ...` headings - there is nothing to join the stories through"]

    story_id_re = _story_id_pattern(story_prefix)
    known = set(story_ids)
    named: set[str] = set()
    failures: list[str] = []
    for heading in headings:
        found = story_id_re.findall(heading)
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
