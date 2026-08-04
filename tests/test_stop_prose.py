"""SK-135: the conductor's prose matches the classification table it describes."""

import pathlib
import re

from supskill_state import stop_classes

SKILL = pathlib.Path("skills/supskill/SKILL.md")
REFERENCE = pathlib.Path("skills/supskill/references/stop-classes.md")


def test_the_reference_names_every_stop():
    text = REFERENCE.read_text(encoding="utf-8")
    for stop in stop_classes.STOPS:
        if stop.stop_class != stop_classes.NO_STOP:
            assert stop.id in text, f"{stop.id} is missing from stop-classes.md"


def test_skill_no_longer_forbids_archive_outright():
    text = SKILL.read_text(encoding="utf-8")
    assert "**Never pass `--archive`.**" not in text


def test_skill_links_the_stop_classes_reference():
    assert "references/stop-classes.md" in SKILL.read_text(encoding="utf-8")


def test_skill_still_refuses_a_north_star_supersede():
    text = SKILL.read_text(encoding="utf-8")
    assert "north-star-reset" in text
    assert "operator's alone" in text or "operator-authored" in text


def test_remediable_actions_pass_operator_answered():
    # every `action --stop ... --command "..."` invocation written into the prose
    # must carry the SK-136 attestation, or it is describing a command the CLI
    # refuses. Whitespace is flattened first so hand-wrapped prose lines don't
    # split a single invocation across two lines and dodge the check.
    for path in (SKILL, REFERENCE):
        flat = " ".join(path.read_text(encoding="utf-8").split())
        occurrences = list(re.finditer(r'action --stop \S+ --command "[^"]*"', flat))
        assert occurrences, f"no `action --stop ... --command` invocation found in {path.name}"
        for match in occurrences:
            window = flat[match.start() : match.end() + 60]
            assert "--operator-answered" in window, f"{path.name}: {match.group(0)!r}"


def test_reference_opens_with_the_conductor_facing_framing():
    text = REFERENCE.read_text(encoding="utf-8")
    assert "conductor-facing" in text.lower()
    assert "nothing here is sent to a subagent" in text.lower() or "nothing in it is sent to a subagent" in text.lower()
    assert "stop_classes.py" in text


def test_evidential_stops_are_still_named_as_refusals():
    text = REFERENCE.read_text(encoding="utf-8")
    for stop in stop_classes.STOPS:
        if stop.stop_class == stop_classes.EVIDENTIAL:
            assert stop.id in text, f"{stop.id} is missing from stop-classes.md"


def test_skill_still_refuses_review_guard_stale_and_plan_guard_commits():
    # both are evidential: acting on either destroys the signal it exists to raise
    text = SKILL.read_text(encoding="utf-8")
    assert "review-guard" in text
    assert "Relay the refusal verbatim and stop" in text
    assert "plan-guard" in text
