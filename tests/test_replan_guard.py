"""SK-053: refuse a north-star supersede, structurally.

Two kinds of proof: (1) the guard function itself, TDD'd purely offline -
the same shape as plan_guard.py's head_moved predicate, a pure check plus a
call site (Task 8) that reports and stops; (2) regression tests that the
structural claim it relies on still holds - state.backlog assigned nowhere
but init_sprint, and every trail file commands.py writes ends .jsonl, never
.md (the only way a verb could ever touch backlog.md).
"""

import re
from pathlib import Path

import pytest

from supskill_state import commands
from supskill_state.cli import main
from supskill_state.errors import StateError
from supskill_state.replan_guard import (
    AMENDING_SHAPES,
    REPLAN_SHAPES,
    is_supersede,
    refusal,
)


def test_replan_shapes_names_exactly_the_designs_own_four():
    # docs/.ai/reports/2026-07-12-supskill-design-decisions.md:244-254
    assert REPLAN_SHAPES == (
        "generative-writeback",
        "park-at-boundary",
        "fork-on-live-evidence",
        "north-star-reset",
    )
    assert AMENDING_SHAPES == REPLAN_SHAPES[:3]


@pytest.mark.parametrize("shape", AMENDING_SHAPES)
def test_the_first_three_shapes_amend_and_are_never_supersede(shape):
    assert is_supersede(shape) is False


def test_the_fourth_shape_is_the_one_that_is_always_refused():
    assert is_supersede("north-star-reset") is True


def test_an_unclassified_shape_is_refused_loudly_not_silently():
    with pytest.raises(StateError, match="unknown replan shape"):
        is_supersede("some other reading")


def test_the_refusal_names_the_operators_own_move_and_never_offers_to_help():
    text = refusal("north-star-reset")
    assert "operator's alone" in text
    assert "author the new backlog by hand" in text
    assert "not offered here for convenience" in text


def test_refusal_refuses_to_run_on_an_amending_shape():
    with pytest.raises(StateError, match="not the supersede shape"):
        refusal("generative-writeback")


# --- the structural regression: still true today, by construction ---

def test_state_backlog_is_constructed_nowhere_outside_init_sprint():
    source = Path(commands.__file__).read_text(encoding="utf-8")
    functions = re.split(r"\ndef ", source)
    offenders = [
        chunk.split("(", 1)[0]
        for chunk in functions[1:]
        if re.search(r"backlog\s*=", chunk) and not chunk.startswith("init_sprint")
    ]
    assert offenders == []


def test_every_trail_file_this_module_writes_is_jsonl_never_markdown():
    # the only way a verb could ever touch backlog.md is by naming it in a store
    # write call; every trail file commands.py builds names itself here, and every
    # one of those names must end .jsonl - backlog.md edits are a person's, by hand
    source = Path(commands.__file__).read_text(encoding="utf-8")
    names = re.findall(
        r'runs_dir\(root\)\s*/\s*normalize_sprint_id\(state\.sprint\.id\)\s*/\s*"([^"]+)"',
        source,
    )
    assert len(names) >= 4  # blockers, tasks, costs, review - grows, never shrinks silently
    assert all(name.endswith(".jsonl") for name in names)


# --- the CLI call site: SK-056 ---

def test_cli_exit_codes_for_replan_guard(capsys):
    assert main(["replan-guard", "--shape", "generative-writeback"]) == 0
    assert "is an amending shape" in capsys.readouterr().out

    assert main(["replan-guard", "--shape", "north-star-reset"]) == 1
    err = capsys.readouterr().err
    assert "operator's alone" in err
    assert "author the new backlog by hand" in err


def test_replan_guard_needs_no_state_file(tmp_path, monkeypatch):
    # it is a query, not a verb: it must work before init and after a wipe, like plan-guard
    monkeypatch.chdir(tmp_path)
    assert main(["replan-guard", "--shape", "park-at-boundary"]) == 0
