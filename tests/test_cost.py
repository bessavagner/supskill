"""record_cost is pure telemetry: state.json never changes, only runs/<id>/costs.jsonl grows.

Exists to answer supskill's own open cost questions (docs/.ai/reports/2026-07-12-supskill-design-
decisions.md open question #3: "PAR cost... worth measuring") from real per-dispatch numbers
instead of estimation.
"""

import json

import pytest

from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_cost
from supskill_state.errors import StateError
from supskill_state.store import require_aware_utc_iso, runs_dir, state_path


def _costs(tmp_path, sprint_dir="s10"):
    path = runs_dir(tmp_path) / sprint_dir / "costs.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_records_one_line_and_touches_nothing_in_state_json(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)
    before = state_path(tmp_path).read_bytes()

    record_cost("SCOPE", 71053, label="scope-agent", tool_uses=13, duration_ms=187319, root=tmp_path)

    assert state_path(tmp_path).read_bytes() == before  # pure telemetry: no state mutation
    lines = _costs(tmp_path)
    assert len(lines) == 1
    require_aware_utc_iso(lines[0].pop("at"), "costs.jsonl at")
    assert lines[0] == {
        "stage": "SCOPE",
        "label": "scope-agent",
        "tokens": 71053,
        "tool_uses": 13,
        "duration_ms": 187319,
    }


def test_label_tool_uses_and_duration_are_all_optional(tmp_path):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)
    record_cost("PLAN", 5000, root=tmp_path)
    line = _costs(tmp_path)[0]
    assert line["label"] is None
    assert line["tool_uses"] is None
    assert line["duration_ms"] is None
    assert line["tokens"] == 5000


def test_repeated_dispatches_within_a_stage_all_land_in_the_trail(tmp_path):
    # EXECUTE dispatches several subagents per task - implementer, task-reviewer, fix
    init_sprint("s10", entry="EXECUTE", root=tmp_path)
    record_cost("EXECUTE", 20000, label="T1-implementer", root=tmp_path)
    record_cost("EXECUTE", 8000, label="T1-task-reviewer", root=tmp_path)
    record_cost("EXECUTE", 4000, label="T1-fix", root=tmp_path)
    assert [line["label"] for line in _costs(tmp_path)] == [
        "T1-implementer",
        "T1-task-reviewer",
        "T1-fix",
    ]


@pytest.mark.parametrize(
    "stage,match",
    [
        ("SCOPING", "unknown stage"),
        ("scope", "unknown stage"),
        ("", "unknown stage"),
    ],
)
def test_unknown_stage_is_refused_and_writes_nothing(tmp_path, stage, match):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)
    before = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match=match):
        record_cost(stage, 100, root=tmp_path)
    assert _costs(tmp_path) == []
    assert state_path(tmp_path).read_bytes() == before


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"tokens": -1}, "--tokens must not be negative"),
        ({"tokens": 100, "tool_uses": -1}, "--tool-uses must not be negative"),
        ({"tokens": 100, "duration_ms": -1}, "--duration-ms must not be negative"),
    ],
)
def test_negative_numbers_are_refused(tmp_path, kwargs, match):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)
    tokens = kwargs.pop("tokens")
    with pytest.raises(StateError, match=match):
        record_cost("SCOPE", tokens, root=tmp_path, **kwargs)
    assert _costs(tmp_path) == []


def test_cli_records_with_the_right_exit_code(tmp_path, monkeypatch, capsys):
    init_sprint("s10", backlog="backlog.md", root=tmp_path)
    monkeypatch.chdir(tmp_path)
    assert (
        main(
            [
                "cost", "--stage", "REFINE", "--label", "refine-agent",
                "--tokens", "12345", "--tool-uses", "7", "--duration-ms", "9000",
            ]
        )
        == 0
    )
    assert "recorded cost: REFINE/refine-agent tokens=12345" in capsys.readouterr().out
    assert _costs(tmp_path)[0]["stage"] == "REFINE"

    assert main(["cost", "--stage", "BOGUS", "--tokens", "1"]) == 1
    assert "unknown stage" in capsys.readouterr().err
