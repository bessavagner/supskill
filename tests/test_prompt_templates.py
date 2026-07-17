"""E3 prose surfaces: templates exist, quote the single-authority grammar, state D4 + invariant 3.

The authoritative invariant-3 check is the reviewer reading every template;
the tests here are tripwires for the obvious regressions only.
"""

from pathlib import Path

REFERENCES = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "references"
SCOPE = REFERENCES / "scope-prompt.md"
REFINE = REFERENCES / "refine-prompt.md"
PLAN = REFERENCES / "plan-prompt.md"
REVIEW = REFERENCES / "review-prompt.md"

TEMPLATES = (SCOPE, REFINE, PLAN, REVIEW)
EXECUTION_SUB_SKILLS = ("subagent-driven-development", "executing-plans")


def test_scope_template_names_its_placeholders():
    text = SCOPE.read_text(encoding="utf-8")
    for placeholder in ("{SPRINT_ID}", "{BACKLOG_PATH}", "{OUTPUT_PATH}", "{EXEMPLAR_DOCS}"):
        assert placeholder in text, placeholder


def test_scope_template_states_the_two_constraints():
    text = SCOPE.read_text(encoding="utf-8")
    assert "cannot ask anyone anything" in text  # D4 / invariant 2
    assert "must not run `supskill-state`" in text  # invariant 3, third surface


def test_no_dispatch_template_line_instructs_running_the_state_cli():
    for template in TEMPLATES:
        for line in template.read_text(encoding="utf-8").splitlines():
            if "supskill-state" in line:
                assert "not" in line.lower(), f"{template.name}: {line!r}"


def test_no_dispatch_template_line_instructs_an_execution_sub_skill():
    # SK-031: writing-plans' Execution Handoff names a REQUIRED SUB-SKILL per branch. No
    # template may route its agent into one - a plan agent that executes bypasses Gate 2
    # entirely (state.json still reads PLAN while the branch carries the commits).
    for template in TEMPLATES:
        for line in template.read_text(encoding="utf-8").splitlines():
            if any(skill in line for skill in EXECUTION_SUB_SKILLS):
                assert "not" in line.lower(), f"{template.name}: {line!r}"


def test_plan_template_names_its_placeholders():
    text = PLAN.read_text(encoding="utf-8")
    for placeholder in ("{SPRINT_DOC_PATH}", "{OUTPUT_PATH}", "{REPO_ROOT}", "{EXEMPLAR_PLAN}"):
        assert placeholder in text, placeholder


def test_plan_template_states_the_two_standing_constraints():
    text = PLAN.read_text(encoding="utf-8")
    assert "cannot ask anyone anything" in text  # D4 / invariant 2
    assert "must not run `supskill-state`" in text  # invariant 3, third surface


def test_plan_template_pre_answers_the_execution_handoff_and_stops():
    text = PLAN.read_text(encoding="utf-8")
    assert "subagent-driven, always" in text  # the question is already answered
    assert "superpowers:writing-plans" in text  # the skill it must actually invoke
    assert "do not implement, test, or commit anything" in text.lower()


def test_plan_template_states_the_join_key_and_the_citation_rule():
    text = PLAN.read_text(encoding="utf-8")
    assert "(SK-0xx)" in text and "(process)" in text  # the heading grammar SK-033 validates
    assert "exists today" in text  # cite lines only for code that exists today


def test_refine_template_names_its_placeholders():
    text = REFINE.read_text(encoding="utf-8")
    for placeholder in (
        "{SPRINT_DOC_PATH}", "{BACKLOG_PATH}", "{REPO_ROOT}", "{EXEMPLAR_DOC}", "{AUDIT_FAILURES}",
    ):
        assert placeholder in text, placeholder


def test_refine_template_quotes_the_grammar_verbatim():
    # grammar-drift risk from the sprint risks table: proofs.py is the single
    # authority; the quote in the prompt is pinned to the parser's own constant
    from supskill_state.proofs import GRAMMAR_LINE

    assert GRAMMAR_LINE in REFINE.read_text(encoding="utf-8")


def test_refine_template_states_the_two_constraints_and_the_field_list():
    text = REFINE.read_text(encoding="utf-8")
    assert "cannot ask anyone anything" in text
    assert "must not run `supskill-state`" in text
    # the spec-shaped definition appears as a concrete field list, not as the word "spec-shaped"
    assert "DoR findings (refined at pull time)" in text
    assert "in place" in text


def test_review_template_names_its_placeholders():
    text = REVIEW.read_text(encoding="utf-8")
    for placeholder in ("{REVIEWER_LABEL}", "{REVIEW_PACKAGE_PATH}", "{REPO_ROOT}"):
        assert placeholder in text, placeholder


def test_review_template_states_the_two_standing_constraints():
    text = REVIEW.read_text(encoding="utf-8")
    assert "cannot ask anyone anything" in text  # D4 / invariant 2
    assert "must not run `supskill-state`" in text  # invariant 3, fourth surface


def test_review_template_states_the_competitive_frame_and_no_cross_visibility():
    text = REVIEW.read_text(encoding="utf-8")
    assert "false positives are worse than misses" in text  # D9's own framing
    assert "no other agent's" in text.lower()  # no cross-visibility between the two dispatches


def test_review_template_asks_for_severity_and_a_defensible_location():
    text = REVIEW.read_text(encoding="utf-8")
    assert "Critical" in text and "Important" in text and "Minor" in text
    assert "location" in text.lower()


def test_refine_template_carves_out_tooling_findings_from_the_repo_root_citation_rule():
    text = REFINE.read_text(encoding="utf-8")
    assert "supskill's own tooling or mechanism" in text
    assert "reproduced symptom" in text


def test_plan_template_carves_out_tooling_findings_from_the_repo_root_citation_rule():
    text = PLAN.read_text(encoding="utf-8")
    assert "supskill's own tooling or mechanism" in text
    assert "reproduced symptom" in text
