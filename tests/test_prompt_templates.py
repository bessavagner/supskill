"""E3 prose surfaces: templates exist, quote the single-authority grammar, state D4 + invariant 3.

The authoritative invariant-3 check is the reviewer reading every template;
the tests here are tripwires for the obvious regressions only.
"""

from pathlib import Path

REFERENCES = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "references"
SCOPE = REFERENCES / "scope-prompt.md"
REFINE = REFERENCES / "refine-prompt.md"


def test_scope_template_names_its_placeholders():
    text = SCOPE.read_text(encoding="utf-8")
    for placeholder in ("{SPRINT_ID}", "{BACKLOG_PATH}", "{OUTPUT_PATH}", "{EXEMPLAR_DOCS}"):
        assert placeholder in text, placeholder


def test_scope_template_states_the_two_constraints():
    text = SCOPE.read_text(encoding="utf-8")
    assert "cannot ask anyone anything" in text  # D4 / invariant 2
    assert "must not run `supskill-state`" in text  # invariant 3, third surface


def test_no_dispatch_template_line_instructs_running_the_state_cli():
    for template in (SCOPE, REFINE):
        for line in template.read_text(encoding="utf-8").splitlines():
            if "supskill-state" in line:
                assert "not" in line.lower(), f"{template.name}: {line!r}"


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
