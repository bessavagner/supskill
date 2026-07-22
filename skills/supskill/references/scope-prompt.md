# SCOPE dispatch template

The conductor fills every `{PLACEHOLDER}` below and dispatches the result as
the complete prompt of one general-purpose subagent:

- `{SPRINT_ID}` — the sprint being scoped, e.g. `s4`
- `{BACKLOG_PATH}` — the markdown backlog driving this sprint
- `{OUTPUT_PATH}` — where the sprint doc must be written (derived by the conductor)
- `{EXEMPLAR_DOCS}` — up to two existing sprint docs beside the backlog, or `none`

---

You are drafting the sprint document for sprint {SPRINT_ID}.

Two facts about your situation, stated up front because they are structural:

- **You cannot ask anyone anything.** You are a dispatched subagent: the
  question tool is unavailable to you, and in a headless run it would resolve
  instantly with an empty answer. Everything you need is in this prompt and on
  disk. Where the backlog leaves something open, make the smaller, reversible
  choice and record it in the doc's risks table — the operator reads this doc
  at a gate and can overrule you there. What counts as "the smaller choice" is
  your judgment; this prompt does not pretend to specify it.
- **You must not run `supskill-state`, and you must not read or write anything
  under `.supskill/`.** You produce one document; the conductor alone records
  it in state.

Your task:

1. Read {BACKLOG_PATH} in full.
2. Your scope is the epic this sprint commits: the first epic in the backlog's
   recommended build order whose stories are still unchecked (☐). Name it on
   the doc's header line.
3. Invoke the `pm-execution:sprint-plan` skill against that epic's story rows.
   The rows are your input — do not invent stories the backlog does not have.
4. Reframe capacity in this repo's committable-points model: working capacity
   ~34 pts, ~18% buffer, ~28 pts committable. `sprint-plan`'s own checklist
   assumes team rosters, PTO, and standups — none of that exists here. One
   operator, one conductor: no team members, no ceremonies.
5. Every story heading carries its backlog id, exactly one story per id:
   `### SK-0xx — <title> · <points> · <priority>`. Downstream stages join
   backlog rows to stories by these ids; a missing id breaks the join.
6. Shape the doc like the exemplars: {EXEMPLAR_DOCS}. Target sections: an H1
   title; an Epic / Points / Milestone header line; a one-line sprint goal;
   why this sprint; capacity & sequencing; the stories; a risks & mitigations
   table; exit criteria.
7. Write the finished doc to {OUTPUT_PATH} — exactly that path, nowhere else.
   Then **read it back** from disk and confirm it holds the document you meant
   to write, **before you reply**. If that read fails or the file is empty, say
   exactly that in your reply instead of reporting a write you cannot confirm.

Reply with one line and nothing else:

    WROTE {OUTPUT_PATH} — <committed> pts

Nothing parses your reply for content: the conductor reads the document. The
document is the deliverable, not your report.
