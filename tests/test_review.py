"""SK-050: the review verb + PAR's aggregation rule.

Two slices, both offline: (1) the review verb - Critical|Important|Minor x
high|actionable, appended trail-first to runs/<id>/review.jsonl, exactly
like blockers.jsonl/tasks.jsonl/costs.jsonl (commands.py:256-269, :380-384,
:422-434) but with no state.json mirror - review has no schema field, the
same shape as cost; (2) the aggregation rule itself, review.aggregate(), a
pure function of an already-matched finding's reported severities. Matching
which finding from reviewer-a corresponds to which from reviewer-b is the
conductor's own judgment, done in prose - not this module's job, and not
tested here.
"""

import json

import pytest

from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_review_finding
from supskill_state.errors import StateError
from supskill_state.review import aggregate, worse_severity
from supskill_state.store import require_aware_utc_iso, runs_dir, state_path


def _reviews(tmp_path, sprint_dir="s6"):
    path = runs_dir(tmp_path) / sprint_dir / "review.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_records_one_line_and_touches_nothing_in_state_json(tmp_path):
    init_sprint("s6", backlog="backlog.md", root=tmp_path)
    before = state_path(tmp_path).read_bytes()

    record_review_finding(
        "reviewer-a", "Critical", "actionable",
        "auth_middleware is never called from the router", "src/auth.py:41",
        root=tmp_path,
    )

    assert state_path(tmp_path).read_bytes() == before  # pure telemetry, like cost
    lines = _reviews(tmp_path)
    assert len(lines) == 1
    require_aware_utc_iso(lines[0].pop("at"), "review.jsonl at")
    assert lines[0] == {
        "reviewer": "reviewer-a",
        "severity": "Critical",
        "confidence": "actionable",
        "finding": "auth_middleware is never called from the router",
        "location": "src/auth.py:41",
    }


@pytest.mark.parametrize(
    "overrides,match",
    [
        ({"reviewer": "reviewer-c"}, "unknown reviewer"),
        ({"severity": "Blocker"}, "unknown severity"),
        ({"confidence": "certain"}, "unknown confidence"),
        ({"finding": ""}, "non-empty --finding"),
        ({"finding": "   "}, "non-empty --finding"),
        ({"location": ""}, "non-empty --location"),
    ],
)
def test_the_vocabulary_and_the_two_required_fields_are_refused_with_nothing_written(tmp_path, overrides, match):
    init_sprint("s6", backlog="backlog.md", root=tmp_path)
    call = {
        "reviewer": "reviewer-a", "severity": "Critical", "confidence": "high",
        "finding": "a finding", "location": "src/x.py:1",
    }
    call.update(overrides)
    with pytest.raises(StateError, match=match):
        record_review_finding(
            call["reviewer"], call["severity"], call["confidence"], call["finding"], call["location"],
            root=tmp_path,
        )
    assert _reviews(tmp_path) == []


def test_both_is_a_legal_reviewer_value_for_a_finding_matched_across_both(tmp_path):
    init_sprint("s6", backlog="backlog.md", root=tmp_path)
    record_review_finding("both", "Important", "high", "matched by both reviewers", "src/y.py:9", root=tmp_path)
    assert _reviews(tmp_path)[0]["reviewer"] == "both"


def test_cli_records_and_refuses_with_the_right_exit_codes(tmp_path, monkeypatch, capsys):
    init_sprint("s6", backlog="backlog.md", root=tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main([
        "review", "--reviewer", "reviewer-b", "--severity", "Minor", "--confidence", "actionable",
        "--finding", "a nit", "--location", "src/z.py:3",
    ]) == 0
    assert "recorded review finding: reviewer-b Minor/actionable" in capsys.readouterr().out

    assert main([
        "review", "--reviewer", "nope", "--severity", "Minor", "--confidence", "actionable",
        "--finding", "x", "--location", "y",
    ]) == 1
    assert "unknown reviewer" in capsys.readouterr().err


# --- the aggregation rule: a pure function of an already-matched finding ---

def test_both_reviewers_agree_is_high_confidence_at_that_severity():
    assert aggregate("Important", "Important") == ("high", "Important")


def test_disagreement_always_takes_the_worse_severity_never_the_better():
    assert aggregate("Minor", "Critical") == ("high", "Critical")
    assert aggregate("Critical", "Minor") == ("high", "Critical")  # order never matters
    assert aggregate("Important", "Minor") == ("high", "Important")


def test_one_reviewer_only_is_actionable_at_that_reviewers_severity():
    assert aggregate("Important", None) == ("actionable", "Important")
    assert aggregate(None, "Minor") == ("actionable", "Minor")


def test_aggregate_refuses_a_finding_neither_reviewer_reported():
    with pytest.raises(StateError, match="at least one reviewer"):
        aggregate(None, None)


@pytest.mark.parametrize(
    "a,b,worse",
    [
        ("Critical", "Important", "Critical"),
        ("Important", "Minor", "Important"),
        ("Minor", "Minor", "Minor"),
        ("Critical", "Critical", "Critical"),
    ],
)
def test_worse_severity_ranks_critical_over_important_over_minor(a, b, worse):
    assert worse_severity(a, b) == worse
    assert worse_severity(b, a) == worse  # order never matters
