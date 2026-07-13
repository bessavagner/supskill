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
