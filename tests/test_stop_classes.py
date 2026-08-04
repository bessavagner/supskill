"""SK-130: every stop the CLI can produce carries exactly one recorded class."""

import pytest

from supskill_state import stop_classes
from supskill_state.cli import build_parser
from supskill_state.errors import StateError


def _cli_verbs() -> set[str]:
    parser = build_parser()
    actions = [a for a in parser._actions if hasattr(a, "choices") and a.choices]
    return set(actions[0].choices)


def test_every_cli_verb_is_classified():
    missing = _cli_verbs() - stop_classes.verbs_covered()
    assert missing == set(), f"unclassified verbs: {sorted(missing)}"


def test_no_stop_names_a_verb_the_cli_does_not_have():
    extra = stop_classes.verbs_covered() - _cli_verbs()
    assert extra == set(), f"table names verbs the CLI lacks: {sorted(extra)}"


def test_stop_ids_are_unique():
    ids = [stop.id for stop in stop_classes.STOPS]
    assert len(ids) == len(set(ids))


def test_every_remediable_stop_names_its_action():
    for stop in stop_classes.STOPS:
        if stop.stop_class == stop_classes.REMEDIABLE:
            assert stop.action, f"{stop.id} is remediable but names no action"


def test_no_evidential_stop_names_an_action():
    for stop in stop_classes.STOPS:
        if stop.stop_class == stop_classes.EVIDENTIAL:
            assert stop.action is None, f"{stop.id} is evidential but names an action"


def test_archive_is_classified_both_ways_on_whether_a_decision_exists():
    archive = [s for s in stop_classes.STOPS if s.verb == "init" and "archive" in s.id]
    classes = {s.stop_class for s in archive}
    assert classes == {stop_classes.REMEDIABLE, stop_classes.EVIDENTIAL}


def test_the_seven_evidential_stops_are_present():
    evidential_verbs = {
        s.verb for s in stop_classes.STOPS if s.stop_class == stop_classes.EVIDENTIAL
    }
    assert {
        "review-guard",
        "plan-guard",
        "commit-scope-guard",
        "replan-guard",
        "preflight",
        "tasks",
        "init",
    } <= evidential_verbs


def test_classify_refuses_an_unknown_stop_id():
    with pytest.raises(StateError):
        stop_classes.classify("no-such-stop")
