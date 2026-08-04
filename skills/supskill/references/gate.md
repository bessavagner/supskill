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
   **Say so when the answer was a bulk acceptance.** Add `--batched` to that
   same `gate` call whenever one answer accepted several recommendations at
   once instead of ruling on each item on its own terms. Offer the operator
   that batch **only when every item in it carries a recommendation** — an item
   with nothing recommended cannot be bulk-accepted, and its presence means the
   question is answered item by item and the gate is not `--batched`. Gate 3's
   question carries every open blocker, parked task, `DONE_WITH_CONCERNS` note
   and high/actionable finding, so it is the gate this most often applies to;
   the same flag and the same condition are on `decide` for a single blocker's
   answer. Omit it and every row reads `batched: false`, and a ledger that
   cannot tell a bulk acceptance from a considered one is lying quietly
   (SK-109, SK-133). `show` prints it beside the gate's decision and
   `show --json` carries it under `derived.gates`, so the two stay tellable
   apart on disk after the conversation is gone.

What happens after the decision is recorded is each gate's own — see Gate 1,
Gate 2, or Gate 3 in `SKILL.md`.
