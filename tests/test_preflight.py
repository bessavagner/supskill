"""SK-106: refuse at run start when a still-to-run stage would dispatch a
`superpowers` skill that did not resolve at runtime, rather than improvise."""

from pathlib import Path

import pytest

from supskill_state.cli import main
from supskill_state.errors import StateError
from supskill_state.preflight import (
    SKILL_ARTIFACTS,
    refusal,
    required_skills,
    unresolved,
)


def test_required_skills_accumulate_from_the_stage_onward():
    assert required_skills("SCOPE") == ("writing-plans", "subagent-driven-development")
    assert required_skills("PLAN") == ("writing-plans", "subagent-driven-development")
    assert required_skills("EXECUTE") == ("subagent-driven-development",)
    assert required_skills("REVIEW") == ()


def test_an_unknown_stage_raises():
    with pytest.raises(StateError, match="unknown stage"):
        required_skills("BOGUS")


def test_a_required_skill_not_passed_reads_as_unresolvable():
    problems = unresolved("EXECUTE", {})
    assert [skill for skill, _ in problems] == ["subagent-driven-development"]
    assert "could not be resolved" in problems[0][1]


def _plant_skill(base: Path, skill: str) -> Path:
    d = base / skill
    for rel in SKILL_ARTIFACTS[skill]:
        target = d / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")
    return d


def test_a_fully_present_skill_is_resolved(tmp_path):
    sdd = _plant_skill(tmp_path, "subagent-driven-development")
    assert unresolved("EXECUTE", {"subagent-driven-development": str(sdd)}) == []


def test_a_resolved_skill_missing_a_script_is_unresolvable(tmp_path):
    sdd = tmp_path / "sdd"
    (sdd).mkdir()
    (sdd / "SKILL.md").write_text("x", encoding="utf-8")  # present, but no scripts/
    problems = unresolved("EXECUTE", {"subagent-driven-development": str(sdd)})
    assert len(problems) == 1
    assert "task-brief" in problems[0][1]


def test_writing_plans_needs_only_its_skill_md(tmp_path):
    wp = tmp_path / "wp"
    wp.mkdir()
    (wp / "SKILL.md").write_text("x", encoding="utf-8")
    sdd = _plant_skill(tmp_path, "subagent-driven-development")
    resolved = {
        "writing-plans": str(wp),
        "subagent-driven-development": str(sdd),
    }
    assert unresolved("PLAN", resolved) == []


def test_the_refusal_names_the_skill_and_the_install_remedy():
    text = refusal("EXECUTE", [("subagent-driven-development", "could not be resolved")])
    assert "subagent-driven-development" in text
    assert "superpowers" in text
    assert "install" in text.lower()


def test_the_refusal_on_no_problems_raises():
    with pytest.raises(StateError, match="nothing to refuse"):
        refusal("EXECUTE", [])


def test_cli_passes_when_every_required_skill_resolves(tmp_path, capsys):
    sdd = _plant_skill(tmp_path, "subagent-driven-development")
    code = main(["preflight", "--stage", "EXECUTE", "--skill", f"subagent-driven-development={sdd}"])
    assert code == 0
    assert "resolves" in capsys.readouterr().out


def test_cli_refuses_a_required_skill_that_was_not_resolved(capsys):
    # --stage EXECUTE requires SDD; passing no --skill means the conductor could not resolve it
    code = main(["preflight", "--stage", "EXECUTE"])
    assert code == 1
    err = capsys.readouterr().err
    assert "subagent-driven-development" in err
    assert "superpowers" in err


def test_cli_rejects_a_malformed_skill_argument(capsys):
    code = main(["preflight", "--stage", "EXECUTE", "--skill", "no-equals-sign"])
    assert code == 1
    assert "NAME=DIR" in capsys.readouterr().err


def test_cli_preflight_needs_no_state_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["preflight", "--stage", "REVIEW"]) == 0  # REVIEW dispatches no external skill


def test_the_run_checklist_preflights_before_the_dispatch_table():
    skill = (Path(__file__).resolve().parent.parent / "skills" / "supskill" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "supskill-state preflight --stage" in skill
    # the refusal must be reached BEFORE the conductor dispatches on stage
    assert skill.index("preflight --stage") < skill.index("## Dispatch table")
