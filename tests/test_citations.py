"""SK-024: a hallucinated or stale citation fails a script before it can impress an operator."""

from pathlib import Path

from supskill_state.citations import audit_citations, build_parser, main

REPO_ROOT = Path(__file__).resolve().parent.parent
SPRINT_03 = REPO_ROOT / "docs" / "plans" / "sprints" / "backlog-01" / "sprint-03-scope-refine-gate1.md"


def _tree(tmp_path):
    nested = tmp_path / "scripts" / "pkg"
    nested.mkdir(parents=True)
    (nested / "mod.py").write_text("\n".join(f"line {i}" for i in range(1, 51)) + "\n")


def test_resolvable_citations_pass_exact_suffix_and_range(tmp_path):
    _tree(tmp_path)
    text = "see `scripts/pkg/mod.py:50`, the bare `mod.py:7`, and the range `mod.py:1-10`"
    assert audit_citations(text, tmp_path) == []


def test_fabricated_file_fails_with_reason(tmp_path):
    _tree(tmp_path)
    failures = audit_citations("see `ghost.py:3`", tmp_path)
    assert len(failures) == 1 and "no file matching ghost.py" in failures[0]


def test_line_past_end_of_file_fails_with_reason(tmp_path):
    _tree(tmp_path)
    failures = audit_citations("see `mod.py:51`", tmp_path)
    assert len(failures) == 1 and "51" in failures[0] and "50 lines" in failures[0]


def test_range_end_is_checked_and_backwards_range_fails(tmp_path):
    _tree(tmp_path)
    assert "50 lines" in audit_citations("`mod.py:40-60`", tmp_path)[0]
    assert "backwards" in audit_citations("`mod.py:9-3`", tmp_path)[0]


def test_suffix_must_match_whole_path_segments(tmp_path):
    _tree(tmp_path)
    # "od.py" is a substring of mod.py's name but not a path suffix - must not resolve
    assert "no file matching" in audit_citations("`od.py:1`", tmp_path)[0]


def test_prose_placeholders_and_skill_names_are_not_citations(tmp_path):
    _tree(tmp_path)
    # no extension dot before the colon, or no numeric line -> not a citation token
    text = "cite `file:line` or `path:start-end`; invoke `pm-execution:sprint-plan`"
    assert audit_citations(text, tmp_path) == []


def test_repeated_citations_are_reported_once(tmp_path):
    _tree(tmp_path)
    assert len(audit_citations("`ghost.py:3` and again `ghost.py:3`", tmp_path)) == 1


def test_dogfood_every_citation_in_the_sprint_doc_resolves():
    # the sprint's own exit criterion: this doc's citations all resolve in this repo
    assert audit_citations(SPRINT_03.read_text(encoding="utf-8"), REPO_ROOT) == []


def test_help_states_the_resolve_not_truth_limit():
    assert "claims they support are true" in build_parser().format_help()


def test_cli_exit_codes_and_failure_output(tmp_path, monkeypatch, capsys):
    _tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "good.md").write_text("see `mod.py:5`\n")
    (tmp_path / "bad.md").write_text("see `ghost.py:3`\n")
    assert main(["good.md"]) == 0
    assert main(["bad.md"]) == 1
    assert "ghost.py" in capsys.readouterr().err
    assert main(["no-such-doc.md"]) == 1


def test_proofs_flag_also_validates_the_grammar(tmp_path, monkeypatch, capsys):
    _tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    doc = tmp_path / "doc.md"
    doc.write_text("## Stories\n\n### SK-001 — s · 1 · M\n- **proof:** seam=vibes · impact=local · provable=offline\n")
    assert main(["doc.md", "--proofs"]) == 1
    assert "vibes" in capsys.readouterr().err
    doc.write_text("## Stories\n\n### SK-001 — s · 1 · M\n- **proof:** seam=unit · impact=local · provable=offline\n")
    assert main(["doc.md", "--proofs"]) == 0
