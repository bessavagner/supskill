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
