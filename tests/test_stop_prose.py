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


def test_the_reference_copies_every_condition_verbatim():
    """I6: ids matching is not the drift that bit this branch - conditions are.

    stop-classes.md says its conditions are "copied verbatim from stop_classes.STOPS".
    Asserting only the id lets either side be edited alone, which is the exact defect
    class divergence 6 had to repair mid-run (prose said "G3 is null", the code says
    "REVIEW and G3 is null").
    """
    text = REFERENCE.read_text(encoding="utf-8")
    for stop in stop_classes.STOPS:
        if stop.stop_class != stop_classes.NO_STOP:
            assert stop.condition in text, f"{stop.id}'s condition drifted from stop-classes.md"


def test_every_remediable_stop_has_a_prose_caller():
    """I6: the branch's dominant structural defect - surface nothing tells the conductor to use.

    A remediable stop with no `action --stop <id>` anywhere in the runtime prose is a
    stop that classifies as remediable and is never remediated, which is how SK-132 and
    SK-133 shipped unwired. `replan-guard.writeback-uncommitted` was added at the very
    end of the branch precisely because this gap was noticed by hand.
    """
    # stop-classes.md is excluded on purpose: its own table names every remediable
    # stop's recording command by construction, so including it would make this pass
    # for a stop no stage ever reaches. The caller has to be at a runtime site.
    prose = SKILL.read_text(encoding="utf-8")
    for path in sorted(REFERENCE.parent.glob("*.md")):
        if path != REFERENCE:
            prose += path.read_text(encoding="utf-8")
    for stop in stop_classes.STOPS:
        if stop.stop_class == stop_classes.REMEDIABLE:
            assert f"action --stop {stop.id}" in prose, f"{stop.id} is remediable but nothing runs it"


def test_skill_step_three_keys_on_stage_and_gate_the_way_the_code_does():
    """I6: `_undecided_review_refusal` fires only when stage is REVIEW AND G3 is null.

    Divergence 6: prose that keyed on the gate alone sent the conductor to "refuse and
    stop" in cases the CLI would have archived. Correct today, and unprotected until
    this test - the condition lives in two files and only one of them is executable.
    """
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("3. **Compare ids.**")
    step_three = text[start : text.index("\n4. **", start)]
    branches = step_three.split("\n   - ")[1:]
    keyed = [b for b in branches if "init.archive.decided" in b or "init.archive.undecided" in b]
    assert len(keyed) == 2, "step 3 should split the id mismatch into exactly two branches"
    for branch in keyed:
        # both sides of the split state both halves of the condition, or the split has
        # drifted back to keying on the gate alone
        assert "REVIEW" in branch, branch
        assert "gates.G3_review" in branch, branch
        assert "null" in branch, branch


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


def test_the_operator_answer_rule_is_written_down_because_it_cannot_be_remembered():
    """I4: "an operator answered THIS RUN" has no on-disk representation.

    Invariant 5 says the conductor is disposable, so knowledge with no disk
    representation is a bug by definition. It cannot be given one here (divergence 3
    rejected the trail-derived check: step 3's archive precedes G1), so the rule has
    to survive /clear in prose instead - including the ceiling, so the flag is not
    read as an observation.
    """
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("## The run checklist")
    preamble = text[start : text.index("\n1. **Read state.**", start)]
    assert "--operator-answered" in preamble
    assert "/clear" in preamble  # the resume path the rule has to survive
    assert "re-establishes" in preamble or "re-establish" in preamble
    assert "F-4" in preamble  # attested, not observed
