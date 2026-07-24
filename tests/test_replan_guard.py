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
    lacks_backlog_target,
    refusal,
    target_refusal,
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

def test_cli_exit_codes_for_replan_guard(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    commands.init_sprint("s1", backlog="docs/backlog.md", root=tmp_path)

    assert main(["replan-guard", "--shape", "generative-writeback"]) == 0
    assert "is an amending shape" in capsys.readouterr().out

    assert main(["replan-guard", "--shape", "north-star-reset"]) == 1
    err = capsys.readouterr().err
    assert "operator's alone" in err
    assert "author the new backlog by hand" in err


def test_the_supersede_shape_still_needs_no_state_file(tmp_path, monkeypatch, capsys):
    # shape 4 is refused for what it IS, before any state is read: it must still
    # work before init and after a wipe, like plan-guard
    monkeypatch.chdir(tmp_path)
    assert main(["replan-guard", "--shape", "north-star-reset"]) == 1
    assert "operator's alone" in capsys.readouterr().err


# --- SK-114: the precondition the shape check never had ---

@pytest.mark.parametrize("shape", AMENDING_SHAPES)
def test_an_amending_shape_with_no_recorded_backlog_lacks_a_target(shape):
    assert lacks_backlog_target(shape, None) is True
    assert lacks_backlog_target(shape, "") is True
    assert lacks_backlog_target(shape, "   ") is True


@pytest.mark.parametrize("shape", AMENDING_SHAPES)
def test_an_amending_shape_with_a_recorded_backlog_has_its_target(shape):
    assert lacks_backlog_target(shape, "docs/plans/sprints/backlog-01/backlog.md") is False


def test_the_supersede_shape_is_never_judged_on_its_target():
    # shape 4 is refused for what it is; a backlog it could write to is beside the point
    assert lacks_backlog_target("north-star-reset", None) is False


def test_an_unknown_shape_still_raises_here_too():
    with pytest.raises(StateError, match="unknown replan shape"):
        lacks_backlog_target("some other reading", None)


def test_the_target_refusal_names_the_sprint_the_null_and_the_operators_move():
    text = target_refusal("generative-writeback", "s6")
    assert "s6" in text
    assert "backlog: null" in text
    assert "--backlog" in text
    assert "inferred" in text  # names the guess it exists to stop


def test_target_refusal_refuses_to_run_on_the_supersede_shape():
    with pytest.raises(StateError, match="its own refusal"):
        target_refusal("north-star-reset", "s6")


def test_cli_refuses_a_writeback_with_no_authorized_destination(tmp_path, monkeypatch, capsys):
    # the ledgerus s6 case, exactly: --entry EXECUTE carries backlog: null to Gate 3
    monkeypatch.chdir(tmp_path)
    commands.init_sprint("s6", entry="EXECUTE", root=tmp_path)
    assert main(["replan-guard", "--shape", "generative-writeback"]) == 1
    err = capsys.readouterr().err
    assert "s6" in err and "backlog: null" in err


def test_cli_reads_state_from_an_explicit_dir(tmp_path, capsys):
    commands.init_sprint("s6", entry="EXECUTE", root=tmp_path)
    assert main(["replan-guard", "--shape", "park-at-boundary", "--dir", str(tmp_path)]) == 1
    assert "s6" in capsys.readouterr().err
