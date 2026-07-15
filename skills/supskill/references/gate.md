# The gate shape (shared by G1, G2, G3)

Extracted at E6 per a trigger named at S4: "two instances is a coincidence,
three is a pattern" (`docs/plans/sprints/backlog-01/sprint-04-plan-gate2.md:67`).
Referenced from each gate's own section in `SKILL.md`, which keeps its own
stage-specific routing — what happens after the decision — inline. Only the
three steps below are shared.

1. **Ask for real.** Use the `AskUserQuestion` tool: approve / reject the
   artifact this gate is reading, at its recorded path, free text welcome.
   Name the path in the question so the operator knows what they are
   approving.
2. **An empty or auto-resolved answer is not a decision.** In headless runs
   the question tool resolves instantly with an empty answer
   (`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:118-122`, D4).
   If the answer comes back empty, do NOT call `gate`. Report that this gate
   requires an interactive operator, and stop.
3. **Record verbatim.** A non-empty answer — the selected label plus any
   free text, unedited — goes to `gate --id <G1|G2|G3> --decision <value>
   --response "<verbatim>"`. The CLI records empty responses by design
   (`scripts/supskill_state/commands.py:196-213`) — a fabricated approval
   must leave a readable, empty quote in the trail (F-4) — which is exactly
   why step 2's refusal lives here, in the conductor, and nowhere else.

What happens after the decision is recorded is each gate's own — see Gate 1,
Gate 2, or Gate 3 in `SKILL.md`.
