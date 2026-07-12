"""Shared builders: a valid schema-v1 state, small enough to tweak per test."""

import pytest

from supskill_state.model import SprintInfo, Stage, State


@pytest.fixture
def make_state():
    def _make(**overrides):
        state = State(
            schema=1,
            backlog="docs/plans/sprints/backlog-02/backlog.md",
            sprint=SprintInfo(
                id="S10",
                slug="alerting-spine",
                entry=Stage.SCOPE,
                branch="feat/e10-alerting-spine",
                scratch=".superpowers/sdd/s10/",
            ),
            stage=Stage.SCOPE,
            artifacts={"sprint_doc": None, "dev_plan": None},
            gates={"G1_sprint_doc": None, "G2_plan": None, "G3_review": None},
            tasks=[],
            blockers=[],
        )
        for key, value in overrides.items():
            setattr(state, key, value)
        return state

    return _make
