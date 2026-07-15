"""E6's prose surfaces: the REVIEW stage exists, PAR's dispatch discipline is
named, and nothing still calls REVIEW a stub.

The authoritative check is the reviewer reading every section; these are
tripwires for the regressions that would silently ship a stage nobody can
reach, or a reviewer that can see the other reviewer's output (F-5, D9).
"""

from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "supskill"
SKILL = SKILL_DIR / "SKILL.md"
REFERENCES = SKILL_DIR / "references"


def _section(heading: str, next_marker: str = "\n## ") -> str:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index(heading)
    rest = text.index(next_marker, start + 1)
    return text[start:rest]


def review_section() -> str:
    return _section("## The REVIEW stage")


def test_the_dispatch_table_routes_into_the_real_review_stage():
    text = SKILL.read_text(encoding="utf-8")
    assert "| `REVIEW` | Follow **The REVIEW stage** below. |" in text
    assert "## The REVIEW stage" in text


def test_no_review_stub_language_survives_anywhere():
    for path in sorted(SKILL_DIR.rglob("*.md")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            assert "REVIEW is not implemented yet" not in line, f"{path.name}:{number}: {line!r}"
            assert "REVIEW is a stub" not in line, f"{path.name}:{number}: {line!r}"


def test_the_review_stage_names_the_dispatch_and_forbids_state_access():
    section = review_section()
    assert "reviewer-a" in section and "reviewer-b" in section
    assert "review-final.diff" in section
    assert "No dispatched reviewer runs `supskill-state`" in section


def test_the_review_stage_costs_each_dispatch_and_points_at_gate_3():
    section = review_section()
    assert "cost --stage REVIEW --label reviewer-a|reviewer-b" in section
    assert "Gate 3" in section


def test_review_notes_exist_and_state_no_cross_visibility():
    text = (REFERENCES / "review-notes.md").read_text(encoding="utf-8")
    assert "neither reviewer sees the other's" in text.lower()


def test_review_notes_state_the_aggregation_rule_and_the_verbs_exact_flags():
    text = (REFERENCES / "review-notes.md").read_text(encoding="utf-8")
    assert "confidence=high" in text.lower() or "`high`" in text
    assert "confidence=actionable" in text.lower() or "`actionable`" in text
    assert "Critical > Important > Minor" in text
    assert "--reviewer" in text and "--severity" in text and "--confidence" in text
    assert "--finding" in text and "--location" in text
