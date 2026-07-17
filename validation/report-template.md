# E8 validation report — <fixture-run | blinkebot-<sprint-id>> — <date>

Copy this file to `validation/reports/<name>-<date>.md` and fill in every section before treating
the run as evidence. An incomplete report is not a pass.

## Run identity

- Target: `<validation/fixture-repo scratch copy at PATH | blinkebot at PATH>`
- Sprint id(s) driven: `<>`
- Conductor / plugin version: `<supskill vX.Y.Z, from .claude-plugin/plugin.json>`
- Date range: `<start>` – `<end>`

## Gate decisions

| Gate | Sprint | Decision | Operator's verbatim response (or a pointer to `gates.jsonl`) |
|---|---|---|---|
| G1 | | | |
| G2 | | | |
| G3 | | | |

## Cost

Pull from `.supskill/runs/<id>/costs.jsonl` in the run's own working tree.

| Stage | Label | Tokens | Tool uses |
|---|---|---|---|
| | | | |

## Findings

- Blockers recorded (`blockers.jsonl`): `<>`
- Tasks parked, and why: `<>`
- PAR review findings at `confidence=high` or `confidence=actionable`: `<>`
- Anything that required stepping outside `supskill-state` to make progress: `<>`

## Verdict

Did this run one sprint the operator would have run anyway — the design doc's own bar
(`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:345`)? **Yes / No**, and why, in your own
words — not a restatement of the checklist above.
