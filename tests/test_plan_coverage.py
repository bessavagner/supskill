"""SK-033: the plan-task <-> story join key, validated at load time.

Every story in tasks[] must be named by at least one '### Task N: ... (SK-0xx)'
heading; every plan task heading must name a known story or the literal (process).
"""

from supskill_state.plan_coverage import PROCESS_MARKER, plan_task_headings, validate_plan_coverage

STORIES = ["SK-030", "SK-031"]

PLAN = """# A plan

### Task 1: the verb (SK-030)

prose

### Task 2: the guard (SK-031)

### Task 3: the demo checklist (process)
"""


def test_a_clean_plan_reports_no_violations():
    assert validate_plan_coverage(PLAN, STORIES) == []


def test_headings_are_extracted_in_document_order():
    assert [h.split(":")[0] for h in plan_task_headings(PLAN)] == ["### Task 1", "### Task 2", "### Task 3"]


def test_a_plan_that_drops_a_story_is_refused_naming_the_story():
    failures = validate_plan_coverage(PLAN.replace("### Task 2: the guard (SK-031)", "### Task 2: x (SK-030)"), STORIES)
    assert len(failures) == 1 and "SK-031" in failures[0] and "drops" in failures[0]


def test_a_heading_naming_no_story_and_not_marked_process_is_refused():
    failures = validate_plan_coverage(PLAN + "\n### Task 4: mystery work\n", STORIES)
    assert len(failures) == 1 and PROCESS_MARKER in failures[0]


def test_a_heading_naming_an_unknown_story_is_refused():
    failures = validate_plan_coverage(PLAN + "\n### Task 4: from another sprint (SK-099)\n", STORIES)
    assert len(failures) == 1 and "SK-099" in failures[0] and "unknown" in failures[0]


def test_one_heading_may_serve_two_stories():
    plan = "### Task 1: the template (SK-030, SK-031)\n"
    assert validate_plan_coverage(plan, STORIES) == []


def test_a_plan_with_no_task_headings_at_all_is_refused():
    failures = validate_plan_coverage("# a plan with prose only\n", STORIES)
    assert len(failures) == 1 and "no `### Task N" in failures[0]


def test_every_violation_is_reported_at_once():
    failures = validate_plan_coverage("### Task 1: mystery\n### Task 2: ghost (SK-099)\n", STORIES)
    assert len(failures) == 4  # unmarked heading, unknown story, and both stories dropped


# SK-033 code-fence awareness (S4 review finding, Critical): dev plans routinely quote
# example task briefs verbatim inside fenced code blocks. A heading matcher blind to
# fences either false-accepts (an unrelated fenced example happens to mention a real
# story, masking a genuine drop) or false-refuses (a fenced example heading that names
# no real story, or names one that isn't a task in this plan).


def test_a_heading_inside_a_fenced_code_block_is_not_a_real_heading():
    plan = "### Task 1: the verb (SK-030)\n```\n### Task 2: fenced example (SK-031)\n```\n"
    assert plan_task_headings(plan) == ["### Task 1: the verb (SK-030)"]


def test_false_accept_a_story_named_only_inside_a_fence_is_still_reported_dropped():
    # STORIES = ["SK-030", "SK-031"]; only SK-030 is a real heading. SK-031 appears only
    # inside a fenced example - it must not count as covering the story.
    plan = (
        "### Task 1: the verb (SK-030)\n"
        "\n"
        "```\n"
        "### Task 2: an unrelated fenced example (SK-031)\n"
        "```\n"
    )
    failures = validate_plan_coverage(plan, STORIES)
    assert len(failures) == 1 and "SK-031" in failures[0] and "drops" in failures[0]


def test_a_fenced_example_heading_naming_no_story_produces_no_violation():
    plan = (
        "### Task 1: the verb (SK-030)\n"
        "### Task 2: the guard (SK-031)\n"
        "```\n"
        "### Task 4: mystery work\n"
        "```\n"
    )
    assert validate_plan_coverage(plan, STORIES) == []


def test_a_fenced_example_heading_marked_process_produces_no_violation():
    plan = (
        "### Task 1: the verb (SK-030)\n"
        "### Task 2: the guard (SK-031)\n"
        "```\n"
        "### Task 4: the demo checklist (process)\n"
        "```\n"
    )
    assert validate_plan_coverage(plan, STORIES) == []


def test_a_language_tagged_fence_still_toggles():
    plan = "### Task 1: the verb (SK-030)\n```python\n### Task 2: fenced example (SK-031)\n```\nprose after\n"
    assert plan_task_headings(plan) == ["### Task 1: the verb (SK-030)"]
    failures = validate_plan_coverage(plan, STORIES)
    assert len(failures) == 1 and "SK-031" in failures[0] and "drops" in failures[0]


# SK-033 CommonMark fence tracking (S4 review, task-2 findings 1-4): the naive
# ``` toggle from 144fd77 doesn't implement CommonMark fence rules, which reopens
# false-accepts and introduces a new false-refuse.


def test_a_heading_inside_a_tilde_fence_is_not_a_real_heading_finding_1():
    # ~~~ is a valid CommonMark fence delimiter, just like ```. A toggle blind to
    # tildes lets a heading inside a ~~~ fence count as real - the exact false-accept
    # the original fix existed to close.
    plan = "### Task 1: the verb (SK-030)\n~~~\n### Task 2: fenced example (SK-031)\n~~~\n"
    failures = validate_plan_coverage(plan, STORIES)
    assert len(failures) == 1 and "SK-031" in failures[0] and "drops" in failures[0]


def test_a_self_closing_backtick_span_does_not_poison_fence_state_finding_2():
    # A line like ```inline``` at line start is not a real opening fence: per
    # CommonMark, a backtick fence's info string may not itself contain a backtick.
    # A toggle that doesn't know this rule flips into "in fence" and never flips
    # back, swallowing every real heading that follows.
    plan = "### Task 1: the verb (SK-030)\n```inline```\n### Task 2: the guard (SK-031)\n"
    assert plan_task_headings(plan) == [
        "### Task 1: the verb (SK-030)",
        "### Task 2: the guard (SK-031)",
    ]
    assert validate_plan_coverage(plan, STORIES) == []


def test_nested_fence_with_shorter_inner_run_does_not_close_the_outer_fence_finding_3():
    # CommonMark: a closing fence must be at least as long as its opener and use the
    # same character. A 4-backtick outer fence containing a 3-backtick inner example
    # must not be closed by the shorter inner run.
    plan = (
        "### Task 1: the verb (SK-030)\n"
        "````\n"
        "Example of a fenced block:\n"
        "```\n"
        "### Task 2: fenced inner example (SK-031)\n"
        "```\n"
        "end of outer example\n"
        "````\n"
    )
    assert plan_task_headings(plan) == ["### Task 1: the verb (SK-030)"]


def test_an_unclosed_fence_at_eof_swallows_trailing_real_headings_by_design_finding_4():
    # Fails safe (over-refuses) rather than guessing where an unterminated fence ends.
    # This is deliberate, documented behavior, not an accident - this test pins it.
    plan = "### Task 1: the verb (SK-030)\n```\nprose\n### Task 2: swallowed by unclosed fence (SK-031)\n"
    assert plan_task_headings(plan) == ["### Task 1: the verb (SK-030)"]
