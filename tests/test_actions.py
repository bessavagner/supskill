"""SK-131: what the conductor did on the operator's behalf, durable on disk.

Decision 2 of the design makes these actions silent. Invariant 5 says the
conductor is disposable with .supskill/ as its only memory, so a report in a
conversation /clear destroys is not a record.
"""

import json

import pytest

from supskill_state.commands import init_sprint, record_action
from supskill_state.errors import StateError
from supskill_state.store import require_aware_utc_iso, runs_dir, state_path


def _actions(tmp_path, sprint_dir="s10"):
    path = runs_dir(tmp_path) / sprint_dir / "actions.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_records_the_stop_its_reason_and_the_exact_command(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    record_action(
        "artifact-guard.untracked",
        "git add docs/a.md docs/b.md && git commit -m 'docs: track sprint artifacts'",
        operator_answered=True,
        sha="0173092",
        root=tmp_path,
    )

    rows = _actions(tmp_path)
    assert len(rows) == 1
    assert rows[0]["stop"] == "artifact-guard.untracked"
    assert rows[0]["command"].startswith("git add ")
    assert rows[0]["sha"] == "0173092"
    assert rows[0]["result"] == "ok"
    assert rows[0]["reason"]  # carried from the table's condition, never invented
    require_aware_utc_iso(rows[0]["at"], "actions.at")


def test_state_json_is_untouched(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)
    before = state_path(tmp_path).read_bytes()

    record_action("artifact-guard.untracked", "git add docs/a.md", operator_answered=True, root=tmp_path)

    assert state_path(tmp_path).read_bytes() == before


def test_refuses_an_evidential_stop_and_writes_nothing(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    with pytest.raises(StateError, match="evidential"):
        record_action("review-guard.stale", "git diff > pkg.diff", operator_answered=True, root=tmp_path)

    assert _actions(tmp_path) == []


def test_refuses_an_unknown_stop_id_and_writes_nothing(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    with pytest.raises(StateError):
        record_action("no-such-stop", "true", operator_answered=True, root=tmp_path)

    assert _actions(tmp_path) == []


def test_refuses_when_no_operator_answered_this_run(tmp_path):
    """SK-136: a run that cannot ask does not act on an operator's behalf."""
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    with pytest.raises(StateError, match="operator"):
        record_action(
            "artifact-guard.untracked", "git add a", operator_answered=False, root=tmp_path
        )

    assert _actions(tmp_path) == []


def test_records_the_operator_attestation_on_the_row(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    record_action("artifact-guard.untracked", "git add a", operator_answered=True, root=tmp_path)

    assert _actions(tmp_path)[0]["operator_answered"] is True


def test_operator_answered_is_required_not_defaulted(tmp_path):
    """No default: a caller that forgets it fails loudly rather than silently acting."""
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    with pytest.raises(TypeError):
        record_action("artifact-guard.untracked", "git add a", root=tmp_path)


def test_refuses_an_empty_command(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    with pytest.raises(StateError, match="--command"):
        record_action("artifact-guard.untracked", "", operator_answered=True, root=tmp_path)

    assert _actions(tmp_path) == []


def test_appends_rather_than_replaces(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    record_action("artifact-guard.untracked", "git add a", operator_answered=True, root=tmp_path)
    record_action(
        "init.archive.decided", "supskill-state init s11 --archive", operator_answered=True, root=tmp_path
    )

    assert [r["stop"] for r in _actions(tmp_path)] == [
        "artifact-guard.untracked",
        "init.archive.decided",
    ]


def test_cli_records_an_action(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    from supskill_state.cli import main

    exit_code = main([
        "action", "--stop", "artifact-guard.untracked", "--command", "git add a",
        "--sha", "abc1234", "--operator-answered",
    ])

    assert exit_code == 0
    assert "recorded action" in capsys.readouterr().out
    assert _actions(tmp_path)[0]["sha"] == "abc1234"


def test_cli_refuses_an_evidential_stop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    from supskill_state.cli import main

    assert main([
        "action", "--stop", "review-guard.stale", "--command", "true", "--operator-answered",
    ]) == 1


def test_cli_refuses_without_the_operator_attestation(tmp_path, monkeypatch):
    """SK-136: the flag is opt-in, so forgetting it fails loudly."""
    monkeypatch.chdir(tmp_path)
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    from supskill_state.cli import main

    assert main(["action", "--stop", "artifact-guard.untracked", "--command", "git add a"]) == 1
    assert _actions(tmp_path) == []


def test_the_consent_refusal_does_not_claim_the_action_was_not_executed(tmp_path):
    """I3: this check runs when the action is REPORTED, after both flows have acted.

    SKILL.md's step 3 archives then records; Gate 3 commits then records. "Nothing was
    executed" is therefore false on exactly the path this refusal exists for, and it
    would talk an operator out of looking for the unrecorded commit SK-131 exists to
    make findable.
    """
    init_sprint("s10", backlog="backlog.md", root=tmp_path)

    with pytest.raises(StateError) as refusal:
        record_action("artifact-guard.untracked", "git add a", operator_answered=False, root=tmp_path)

    text = str(refusal.value)
    assert "nothing was executed" not in text.lower()
    assert "unrecorded" in text
    assert _actions(tmp_path) == []
