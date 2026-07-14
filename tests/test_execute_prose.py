"""E5's prose surfaces: the EXECUTE stage exists, and nothing still calls it a stub.

The authoritative check is the reviewer reading the section; these are tripwires
for the regressions that would silently ship a stage nobody can reach (S5 DoR
finding 9) or an implementer that can mark its own work done (invariant 3, F-5).
"""

from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "supskill"
SKILL = SKILL_DIR / "SKILL.md"


def execute_section() -> str:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("## The EXECUTE stage")
    rest = text.index("\n## ", start + 1)
    return text[start:rest]


def test_the_dispatch_table_and_gate_2_both_route_into_the_real_stage():
    text = SKILL.read_text(encoding="utf-8")
    assert "| `EXECUTE` | Follow **The EXECUTE stage** below. |" in text
    assert "## The EXECUTE stage" in text
    # Gate 2's approval is the ONLY path that reaches EXECUTE (S5 DoR finding 9)
    assert "`approved` → `advance --to EXECUTE` → continue at **The EXECUTE stage**" in text


def test_gate_1_routes_into_the_plan_stage_that_shipped_in_s4():
    # the same defect one stage back, live on main until this sprint: Gate 1's approval is
    # the only path that reaches PLAN, and it still called PLAN an honest stub
    assert "`approved` → `advance --to PLAN` → continue at **The PLAN stage**" in SKILL.read_text(
        encoding="utf-8"
    )


def test_no_stub_language_survives_anywhere_except_for_review():
    for path in sorted(SKILL_DIR.rglob("*.md")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            assert "improvise EXECUTE" not in line, f"{path.name}:{number}: {line!r}"
            if "not implemented yet" in line or "honest stub" in line:
                assert "REVIEW" in line, f"{path.name}:{number}: {line!r}"


def test_the_execute_section_forbids_a_dispatched_agent_writing_state():
    # an implementer that can write state can mark its own work done (F-5)
    assert "No dispatched agent runs `supskill-state`" in execute_section()


def test_the_execute_section_refuses_sdds_progress_ledger():
    # keyed by task number; task numbers restart every sprint (S5 DoR finding 2)
    section = execute_section()
    assert "Do not read or write `.superpowers/sdd/progress.md`" in section
    assert "`tasks[]` is the ledger" in section


def test_the_execute_section_prepares_the_scratch_before_the_first_dispatch():
    # passing OUTFILE is exactly what skips sdd-workspace (S5 DoR finding 8)
    section = execute_section()
    assert "sdd-workspace" in section
    assert "mkdir -p <scratch>" in section


def test_the_execute_section_records_base_and_never_derives_it():
    section = execute_section()
    assert "Never `HEAD~1`" in section
    assert "git merge-base" in section  # the final whole-branch review gets its own package


def test_the_execute_section_names_a_model_on_every_dispatch():
    assert "Every dispatch names its model explicitly" in execute_section()


def test_the_execute_section_stops_before_dispatching_on_the_default_branch():
    section = execute_section()
    assert "git rev-parse --abbrev-ref HEAD" in section
    assert "git switch -c" in section


def test_supskill_contributes_no_fourth_prompt_template():
    # the implementer and reviewer prompts are SDD's; supskill has no opinion (D1)
    assert not (SKILL_DIR / "references" / "execute-prompt.md").exists()


def test_the_drain_maps_all_four_sdd_statuses_onto_a_verb():
    section = execute_section()
    assert "`task --id <SK-0xx> --status DONE`" in section
    assert "--status DONE_WITH_CONCERNS --note" in section
    assert "`block --task <SK-0xx>" in section
    assert "re-dispatch the same task **once**" in section  # NEEDS_CONTEXT is bounded


def test_the_drain_writes_each_status_before_the_next_dispatch():
    assert "before the next dispatch begins" in execute_section()


def test_the_drain_skips_terminal_tasks_and_resumes_from_state_alone():
    section = execute_section()
    assert "never re-dispatched" in section
    assert "the first `PENDING` task" in section


def test_downstream_is_discovered_not_predicted():
    section = execute_section()
    assert "same root cause" in section
    assert "--status PARKED" in section


def test_provable_gates_the_claim_and_not_the_run():
    section = execute_section()
    assert "**not proven** — verify by hand" in section
    assert "every task runs" in section


def test_the_halt_happens_exactly_once_and_advances_nothing():
    section = execute_section()
    assert "**exactly once**" in section
    assert "Do not advance to REVIEW" in section
    assert "A halt is the target shape, not an error" in section


def test_sdds_two_remaining_human_decisions_become_blockers_or_resolutions():
    section = execute_section()
    assert "plan-mandated" in section
    assert "cannot verify from diff" in section


def test_the_drain_never_guesses():
    section = execute_section()
    assert "do not invent a blocker's options" in section
    assert "without the task review" in section
