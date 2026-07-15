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


def gate3_section() -> str:
    return _section("## Gate 3")


def test_gate_1_and_gate_2_still_route_correctly_after_the_extraction():
    # the exact substrings tests/test_execute_prose.py already asserts must survive
    text = SKILL.read_text(encoding="utf-8")
    assert "`approved` → `advance --to PLAN` → continue at **The PLAN stage**" in text
    assert "`approved` → `advance --to EXECUTE` → continue at **The EXECUTE stage**" in text


def test_all_three_gates_point_at_the_shared_gate_doc():
    text = SKILL.read_text(encoding="utf-8")
    assert text.count("references/gate.md") >= 3  # Gate 1, Gate 2, Gate 3


def test_gate_md_states_the_three_shared_steps():
    text = (REFERENCES / "gate.md").read_text(encoding="utf-8")
    assert "Ask for real" in text
    assert "empty" in text.lower() and "not a decision" in text.lower()
    assert "Record verbatim" in text
    assert "gate --id <G1|G2|G3> --decision" in text or "gate --id" in text


def test_gate_3_batches_every_source_the_sprint_produced():
    section = gate3_section()
    assert "blocker" in section.lower()
    assert "parked" in section.lower()
    assert "DONE_WITH_CONCERNS" in section
    assert "review.jsonl" in section
    assert "confidence=high" in section and "confidence=actionable" in section


def test_gate_3_decision_routing_is_exact_for_all_three_outcomes():
    section = gate3_section()
    assert '`gate --id G3 --decision approved --response "<verbatim>"`' in section
    assert '`gate --id G3 --decision replan --response' in section
    assert "replan-shapes.md" in section
    assert "Refusing a north-star supersede" in section


def test_gate_3_never_records_a_decision_for_a_shape_4_reading():
    # SK-052's own accept criteria: Shape 4 is never a `gate` call at all
    section = gate3_section()
    assert "**no** `gate` call" in section


def test_replan_shapes_doc_names_all_four_and_marks_the_fourth_out_of_scope():
    text = (REFERENCES / "replan-shapes.md").read_text(encoding="utf-8")
    for shape in ("generative writeback", "park at a live boundary", "fork on live evidence",
                  "north-star reset"):
        assert shape in text.lower()
    assert "out of scope" in text.lower()


def test_shape_1_matches_the_existing_backlog_row_format_and_only_appends():
    text = (REFERENCES / "replan-shapes.md").read_text(encoding="utf-8")
    assert "| ID | Story | Pts | Pri | Status |" in text
    assert "Only append" in text or "only append" in text.lower()


def test_shape_2_uses_the_task_status_verb_that_already_exists():
    text = (REFERENCES / "replan-shapes.md").read_text(encoding="utf-8")
    assert '`task --id <SK-0xx> --status PARKED --note' in text
    assert "not** advanced past" in text.lower() or "not advanced past" in text.lower()


def test_shape_3_names_the_fork_verb_and_never_runs_a_branch_rename():
    text = (REFERENCES / "replan-shapes.md").read_text(encoding="utf-8")
    assert "`init`" in text
    assert "Name the rename" in text or "name the rename" in text.lower()
    assert "do not" in text.lower() and "run it" in text.lower()


def test_shape_4_points_at_the_refusal_and_adds_no_mutator():
    text = (REFERENCES / "replan-shapes.md").read_text(encoding="utf-8")
    assert "Refusing a north-star supersede" in text
    assert "never a new mutator" in text.lower() or "no new mutator" in text.lower()


def test_gate_3_section_wires_in_the_refusal_subsection_right_after_it():
    section = gate3_section()
    assert "### Refusing a north-star supersede" in section


def test_the_refusal_subsection_matches_the_guard_functions_own_language():
    section = gate3_section()
    assert "backlog.md" in section and "North star" in section
    assert "state.json.backlog" in section
    assert "operator's alone" in section
    assert "author the new backlog by hand" in section


def propose_section() -> str:
    return _section("## Propose the next sprint, then stop", next_marker="\n## Reference")


def test_propose_section_exists_and_names_the_backlog_build_order_rule():
    section = propose_section()
    assert "build order" in section
    assert "D6" in section


def test_propose_section_forbids_every_further_state_mutating_call():
    section = propose_section()
    for verb in ("`advance`", "`gate`", "`task`", "`block`", "`cost`", "`init`"):
        assert verb in section, verb
    assert "subagent dispatch" in section


def test_propose_section_applies_regardless_of_which_shape_closed_the_sprint():
    section = propose_section()
    assert "fork" in section.lower() or "Shape 3" in section
    assert "refus" in section.lower()
