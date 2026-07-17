"""E8's runbooks state their own gated, operator-run status - tripwires for a runbook that quietly
loses the "not in the offline suite" framing SK-070/SK-071 depend on. Asserted the same way
tests/test_review_prose.py asserts SKILL.md's own prose, and mirrors evals/README.md's framing.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATION = REPO_ROOT / "validation"


def test_the_fixture_runbook_exists_and_states_it_is_gated():
    text = (VALIDATION / "fixture-run.md").read_text(encoding="utf-8")
    assert "operator-run and live" in text


def test_the_fixture_runbook_names_both_toy_sprints():
    text = (VALIDATION / "fixture-run.md").read_text(encoding="utf-8")
    assert "s1" in text.lower() and "s2" in text.lower()


def test_the_fixture_runbook_warns_against_running_in_place():
    text = (VALIDATION / "fixture-run.md").read_text(encoding="utf-8")
    assert "git init" in text
    assert "scratch" in text.lower()


def test_the_blinkebot_runbook_exists_and_states_it_is_gated():
    text = (VALIDATION / "blinkebot-run.md").read_text(encoding="utf-8")
    assert "operator-run and live" in text


def test_the_blinkebot_runbook_warns_the_s11_label_is_historical():
    text = (VALIDATION / "blinkebot-run.md").read_text(encoding="utf-8")
    assert "already shipped" in text
    assert "supskill-state show --json" in text


def test_the_blinkebot_runbook_forbids_init_over_a_live_run():
    text = (VALIDATION / "blinkebot-run.md").read_text(encoding="utf-8")
    assert "do **not** `init` over it" in text


def test_the_report_template_exists_and_names_every_required_section():
    text = (VALIDATION / "report-template.md").read_text(encoding="utf-8")
    for heading in ("## Run identity", "## Gate decisions", "## Cost", "## Findings", "## Verdict"):
        assert heading in text


def test_the_report_template_points_at_the_designs_own_validation_bar():
    text = (VALIDATION / "report-template.md").read_text(encoding="utf-8")
    assert "docs/.ai/reports/2026-07-12-supskill-design-decisions.md:345" in text


def test_both_runbooks_point_at_the_shared_report_template():
    fixture = (VALIDATION / "fixture-run.md").read_text(encoding="utf-8")
    blinkebot = (VALIDATION / "blinkebot-run.md").read_text(encoding="utf-8")
    assert "report-template.md" in fixture
    assert "report-template.md" in blinkebot


def test_the_validation_readme_lists_both_stories_and_their_runbooks():
    text = (VALIDATION / "README.md").read_text(encoding="utf-8")
    assert "SK-070" in text and "fixture-run.md" in text
    assert "SK-071" in text and "blinkebot-run.md" in text


def test_the_validation_readme_states_the_backlog_flip_is_not_automatic():
    text = (VALIDATION / "README.md").read_text(encoding="utf-8")
    assert "no task in this plan does it for you" in text.lower() or "by hand" in text.lower()
