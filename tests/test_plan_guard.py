"""SK-031 layer 2: the first mechanism in this product that catches a disobedient agent.

writing-plans' Execution Handoff names a REQUIRED SUB-SKILL per branch, and a
dispatched agent's AskUserQuestion auto-resolves empty (D4). If the template's
pre-answer fails to hold, the plan agent can implement the whole sprint inside
the PLAN stage - state.json still reading PLAN, G2_plan still null. HEAD moving
across the dispatch is the evidence.
"""

import pytest

from supskill_state.cli import main
from supskill_state.errors import StateError
from supskill_state.plan_guard import head_moved, refusal

BEFORE = "133da28f8f2b7c1a9e5d4c3b2a1908070605f4e3"
AFTER = "aa81d4d0e1f2a3b4c5d6e7f8091a2b3c4d5e6f70"


def test_an_unchanged_head_did_not_move():
    assert head_moved(BEFORE, BEFORE) is False


def test_a_changed_head_moved():
    assert head_moved(BEFORE, AFTER) is True


def test_surrounding_whitespace_is_stripped_before_comparing():
    # git rev-parse's output carries a trailing newline
    assert head_moved(f"{BEFORE}\n", f"  {BEFORE}  ") is False


def test_an_unreadable_head_is_never_a_silent_pass():
    for before, after in ((BEFORE, ""), ("", AFTER), ("", ""), (BEFORE, "   \n")):
        with pytest.raises(StateError, match="non-empty"):
            head_moved(before, after)


def test_the_refusal_names_both_shas_and_its_own_ceiling():
    text = refusal(BEFORE, AFTER)
    assert BEFORE in text and AFTER in text
    assert "a plan is a document" in text
    assert "without committing" in text  # the ceiling: an editing agent walks past this


def test_cli_exit_codes(capsys):
    assert main(["plan-guard", "--before", BEFORE, "--after", BEFORE]) == 0
    assert "HEAD unchanged" in capsys.readouterr().out

    assert main(["plan-guard", "--before", BEFORE, "--after", AFTER]) == 1
    err = capsys.readouterr().err
    assert BEFORE in err and AFTER in err

    assert main(["plan-guard", "--before", BEFORE, "--after", ""]) == 1
    assert "non-empty" in capsys.readouterr().err


def test_the_guard_needs_no_state_file(tmp_path, monkeypatch):
    # it is a query, not a verb: it must work before init and after a wipe
    monkeypatch.chdir(tmp_path)
    assert main(["plan-guard", "--before", BEFORE, "--after", BEFORE]) == 0
