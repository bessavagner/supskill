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
