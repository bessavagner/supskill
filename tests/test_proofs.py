"""SK-022: the proof grammar is a parseable fact fixed in E3 - SK-033 adds the verb, never a parser."""

from pathlib import Path

import pytest

from supskill_state.errors import StateError
from supskill_state.proofs import GRAMMAR_LINE, ProofLine, parse_proof_lines

SPRINT_03 = (
    Path(__file__).resolve().parent.parent
    / "docs" / "plans" / "sprints" / "backlog-01" / "sprint-03-scope-refine-gate1.md"
)

GOOD = """## Stories

### SK-001 — a story · 3 · M
- **proof:** seam=unit · impact=local · provable=offline
"""


def test_dogfood_this_sprints_own_doc_parses():
    # the sprint spec classifies its own five stories; the parser must agree with it verbatim
    proofs = parse_proof_lines(SPRINT_03.read_text(encoding="utf-8"))
    assert proofs == [
        ProofLine("SK-020", "app-level", "cross-surface", "operator"),
        ProofLine("SK-021", "app-level", "journey", "operator"),
        ProofLine("SK-022", "unit", "cross-surface", "offline"),
        ProofLine("SK-023", "app-level", "journey", "operator"),
        ProofLine("SK-024", "unit", "local", "offline"),
    ]


def test_trailing_annotation_after_the_three_tokens_is_allowed():
    # SK-020's real proof line carries a parenthetical after provable=operator
    doc = GOOD.replace("provable=offline", "provable=offline *(the CLI half is seam=unit)*")
    assert parse_proof_lines(doc)[0].provable == "offline"


def test_unknown_tokens_are_rejected_naming_story_field_and_token():
    with pytest.raises(StateError, match="SK-001.*unknown seam token 'vibes'"):
        parse_proof_lines(GOOD.replace("seam=unit", "seam=vibes"))
    with pytest.raises(StateError, match="unknown impact token"):
        parse_proof_lines(GOOD.replace("impact=local", "impact=huge"))
    with pytest.raises(StateError, match="unknown provable token"):
        parse_proof_lines(GOOD.replace("provable=offline", "provable=maybe"))


def test_duplicate_proof_line_for_one_story_rejected():
    with pytest.raises(StateError, match="SK-001.*duplicate"):
        parse_proof_lines(GOOD + "- **proof:** seam=unit · impact=local · provable=offline\n")


def test_story_in_the_stories_section_without_a_proof_line_rejected():
    with pytest.raises(StateError, match="SK-002.*no proof line"):
        parse_proof_lines(GOOD + "\n### SK-002 — another story · 2 · M\n\nprose only\n")


def test_sk_headings_outside_the_stories_section_do_not_require_proof_lines():
    doc = GOOD + "\n## Deferred\n\n### SK-099 — parked, mentioned in an appendix\n"
    assert len(parse_proof_lines(doc)) == 1


def test_proof_line_before_any_story_heading_rejected():
    with pytest.raises(StateError, match="before any"):
        parse_proof_lines("- **proof:** seam=unit · impact=local · provable=offline\n")


def test_all_violations_are_reported_at_once():
    doc = GOOD.replace("seam=unit", "seam=vibes") + "\n### SK-002 — missing · 2 · M\n"
    with pytest.raises(StateError) as excinfo:
        parse_proof_lines(doc)
    assert "vibes" in str(excinfo.value) and "SK-002" in str(excinfo.value)


def test_grammar_line_constant_is_the_documented_grammar():
    assert GRAMMAR_LINE == (
        "- **proof:** seam=unit|integration|app-level|e2e"
        " · impact=none|local|cross-surface|journey"
        " · provable=offline|operator"
    )


def test_custom_story_prefix_is_honored():
    doc = """## Stories

### BLK-103 — a story · 3 · M
- **proof:** seam=unit · impact=local · provable=offline
"""
    assert parse_proof_lines(doc, story_prefix="BLK") == [
        ProofLine("BLK-103", "unit", "local", "offline")
    ]


def test_a_heading_that_does_not_match_the_configured_prefix_is_not_a_story_heading():
    # SK-001 does not match story_prefix="BLK" - this is a prefix mismatch (SK-101),
    # a more precise diagnosis than the old generic "before any" symptom.
    doc = """## Stories

### SK-001 — a story · 3 · M
- **proof:** seam=unit · impact=local · provable=offline
"""
    with pytest.raises(StateError, match="prefix mismatch"):
        parse_proof_lines(doc, story_prefix="BLK")


def test_the_missing_heading_violation_names_the_configured_prefix():
    with pytest.raises(StateError, match=r"before any ### BLK-xxx heading"):
        parse_proof_lines(
            "- **proof:** seam=unit · impact=local · provable=offline\n", story_prefix="BLK"
        )


def test_a_stories_section_with_a_foreign_prefix_is_refused():
    doc = GOOD.replace("SK-001", "PLS-001")
    with pytest.raises(StateError, match="prefix mismatch"):
        parse_proof_lines(doc, story_prefix="SK")


def test_the_mismatch_message_names_both_prefixes_and_the_config_command():
    doc = GOOD.replace("SK-001", "PLS-009")
    with pytest.raises(StateError) as exc:
        parse_proof_lines(doc, story_prefix="SK")
    message = str(exc.value)
    assert "PLS" in message and "SK" in message
    assert "supskill config --story-id-prefix PLS" in message


def test_a_matching_configured_prefix_still_parses():
    doc = GOOD.replace("SK-001", "PLS-001")
    assert parse_proof_lines(doc, story_prefix="PLS")[0].story == "PLS-001"


def test_a_stories_section_with_no_story_headings_is_not_a_mismatch():
    # narrow rule: refuse a MISMATCH, not mere emptiness
    doc = "## Stories\n\nprose only, no story headings yet\n"
    assert parse_proof_lines(doc, story_prefix="SK") == []
