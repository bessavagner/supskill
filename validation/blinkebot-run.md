# Driving blinkebot for real (SK-071)

**Status: operator-run and live** — the actual bar E8 exists to clear: "drive a real sprint against
a project the operator actually depends on. If it cannot run one sprint the operator would have run
anyway, it does not ship." (`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:345`.)
Deliberately **not** part of the offline `uv run pytest` suite — the live run itself is the accept
criteria, not a test file.

## "S11" is a historical label, not a target

The backlog names this story "Drive blinkebot S11 for real," written 2026-07-12. blinkebot's own
backlog (`docs/plans/sprints/backlog-02/backlog.md:187-192` in that repo) now shows S11 **already shipped**
— a daemon and read-budget allocator landed under that sprint id before this story was ever picked up.
Do not chase the literal string "S11": read blinkebot's live state instead.

## Read the live state before doing anything

blinkebot may already have a `.supskill/` directory — a real conductor run against it may already be
in progress, not hypothetical:

```bash
cd /path/to/your/blinkebot/checkout
supskill-state show --json
```

If that command refuses, naming "no state file", there is no run in flight and you are starting one
fresh, per `skills/supskill/SKILL.md`'s entry point, against whatever sprint is next in blinkebot's
own current backlog. If it succeeds, it names the sprint id, stage, and recorded artifacts of a run
already under way — resume that, per the next section. Trust this command's live output over any
snapshot in this file; state moves.

## Resume, do not restart

If `show --json` reports an in-flight sprint, resume it exactly where `skills/supskill/SKILL.md`'s
entry point says a live `state.json` resumes — do **not** `init` over it. `init` over an existing run
refuses by design (`tests/test_run_matrix.py::test_cell_mismatch_init_refuses_and_names_archive_without_using_it`)
and `--archive` is never the conductor's call to make; if a fresh sprint really is warranted, that is
a decision for you, the operator, made explicitly outside this runbook.

## Follow the conductor to Gate 3

Continue the sprint through Gate 1 (approve or send back the refined sprint doc), PLAN + Gate 2,
EXECUTE's drain-then-halt, REVIEW's PAR, and Gate 3 — every gate a real `AskUserQuestion` answer, per
`skills/supskill/references/gate.md`. Let it run into whatever it actually finds; do not pre-decide
the outcome to make the validation look clean.

## Record the result

Fill in `validation/report-template.md` (copy it to `validation/reports/blinkebot-<sprint-id>-
<date>.md`) once the sprint closes at Gate 3. This is the artifact that answers the design doc's own
question — did it "run one sprint the operator would have run anyway"? A yes ships E8; a no is a real
finding, not a reason to rerun until it looks better.
