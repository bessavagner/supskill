"""E3 prose surfaces: templates exist, quote the single-authority grammar, state D4 + invariant 3.

The authoritative invariant-3 check is the reviewer reading every template;
the tests here are tripwires for the obvious regressions only.
"""

from pathlib import Path

REFERENCES = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "references"
SCOPE = REFERENCES / "scope-prompt.md"
PLAN = REFERENCES / "plan-prompt.md"
REVIEW = REFERENCES / "review-prompt.md"

# SK-100 collapsed SCOPE and REFINE into one dispatch. refine-prompt.md is gone;
# the SCOPE template now both scopes from the backlog and refines against live
# source, so REFINE's contract (citations, the proof grammar, the DoR-findings
# section) lives here and is asserted against SCOPE below.
TEMPLATES = (SCOPE, PLAN, REVIEW)
EXECUTION_SUB_SKILLS = ("subagent-driven-development", "executing-plans")

# Every dispatch's deliverable is a file at a conductor-chosen path, never the
# subagent's chat reply. Measured across three validation runs, ~10 of 29
# dispatches returned a placeholder final message while having genuinely done
# the work; REVIEW lost both reviewers' findings outright because it had no
# file to fall back on. The path placeholder each template must carry:
DELIVERABLE_PATH = {
    SCOPE: "{OUTPUT_PATH}",
    PLAN: "{OUTPUT_PATH}",
    REVIEW: "{FINDINGS_PATH}",
}


def test_scope_template_names_its_placeholders():
    text = SCOPE.read_text(encoding="utf-8")
    for placeholder in (
        "{SPRINT_ID}", "{BACKLOG_PATH}", "{OUTPUT_PATH}", "{REPO_ROOT}",
        "{EXEMPLAR_DOCS}", "{AUDIT_FAILURES}", "{STORY_ID_PREFIX}",
    ):
        assert placeholder in text, placeholder


def test_scope_template_states_the_two_constraints():
    text = SCOPE.read_text(encoding="utf-8")
    assert "cannot ask anyone anything" in text  # D4 / invariant 2
    assert "must not run `supskill-state`" in text  # invariant 3, third surface


def test_scope_template_absorbed_refine_the_contract_and_grammar():
    # SK-100: the merged stage carries what REFINE used to. The proof grammar is
    # pinned to proofs.py's single-authority constant; the field-list contract
    # and the in-place re-dispatch rule are both present.
    from supskill_state.proofs import GRAMMAR_LINE

    text = SCOPE.read_text(encoding="utf-8")
    assert GRAMMAR_LINE in text
    assert "DoR findings (refined at pull time)" in text
    assert "in place" in text
    assert "live source" in text.lower()


def test_scope_template_carves_out_tooling_findings_from_the_repo_root_citation_rule():
    text = SCOPE.read_text(encoding="utf-8")
    assert "supskill's own tooling or mechanism" in text
    assert "reproduced symptom" in text


def test_scope_template_dispatches_no_sprint_plan_and_invents_no_capacity():
    # SK-100: the pm-execution:sprint-plan dispatch and the fabricated capacity
    # model are both removed. Story selection is the backlog's job; there is no
    # velocity to plan against, so no capacity number is invented.
    text = SCOPE.read_text(encoding="utf-8")
    assert "sprint-plan" not in text
    assert "committable" not in text
    assert "working capacity" not in text


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
    for placeholder in (
        "{SPRINT_DOC_PATH}", "{OUTPUT_PATH}", "{REPO_ROOT}", "{EXEMPLAR_PLAN}",
        "{STORY_ID_PREFIX}",
    ):
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
    assert "({STORY_ID_PREFIX}-0xx)" in text and "(process)" in text  # the heading grammar SK-033 validates
    assert "exists today" in text  # cite lines only for code that exists today


def test_review_template_names_its_placeholders():
    text = REVIEW.read_text(encoding="utf-8")
    for placeholder in (
        "{REVIEWER_LABEL}", "{REVIEW_PACKAGE_PATH}", "{REPO_ROOT}", "{FINDINGS_PATH}",
    ):
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


def test_every_dispatch_template_names_a_conductor_chosen_deliverable_path():
    for template, placeholder in DELIVERABLE_PATH.items():
        assert placeholder in template.read_text(encoding="utf-8"), template.name


def test_every_dispatch_template_requires_a_read_back_before_replying():
    # the confirmation is what makes a lost write loud: an agent that cannot read
    # its own deliverable back says so instead of replying as if it had written it
    for template in TEMPLATES:
        text = template.read_text(encoding="utf-8").lower()
        assert "read it back" in text, template.name
        assert "before you reply" in text, template.name


def test_every_dispatch_template_makes_the_reply_a_status_line_nothing_parses():
    for template in TEMPLATES:
        text = template.read_text(encoding="utf-8")
        assert "WROTE " in text, template.name
        assert "nothing parses your reply for content" in text.lower(), template.name


def test_no_dispatch_template_makes_the_chat_reply_the_deliverable():
    # the finding this whole rule exists for: a template that consumes the final
    # message has no fallback when the harness returns a placeholder instead
    for template in TEMPLATES:
        text = template.read_text(encoding="utf-8").lower()
        assert "as your final message" not in text, template.name
        assert "nothing else consumes your output" not in text, template.name


def test_review_template_writes_its_findings_to_the_file_the_conductor_reads():
    text = REVIEW.read_text(encoding="utf-8")
    assert "{FINDINGS_PATH}" in text
    assert "one finding per line" in text  # the on-disk format, unchanged
    assert "final message" not in text.lower()


def test_plan_template_carves_out_tooling_findings_from_the_repo_root_citation_rule():
    text = PLAN.read_text(encoding="utf-8")
    assert "supskill's own tooling or mechanism" in text
    assert "reproduced symptom" in text


def test_no_reference_template_hardcodes_the_sk_prefix_example():
    # SK-101: the SK-0xx literal is what anchored the playset PLS run onto SK.
    # scope/plan carry {STORY_ID_PREFIX}; replan-shapes is prefix-neutral.
    for reference in (SCOPE, PLAN, REFERENCES / "replan-shapes.md"):
        assert "SK-0xx" not in reference.read_text(encoding="utf-8"), reference.name
