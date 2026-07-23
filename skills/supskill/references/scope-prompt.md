# SCOPE dispatch template

The conductor fills every `{PLACEHOLDER}` below and dispatches the result as
the complete prompt of one general-purpose subagent. This one stage both scopes
the sprint from the backlog and refines it against live source — there is no
separate refine pass. On a citation-audit failure the conductor re-dispatches
ONCE, with the audit's output filled into `{AUDIT_FAILURES}`:

- `{SPRINT_ID}` — the sprint being scoped, e.g. `s4`
- `{BACKLOG_PATH}` — the markdown backlog driving this sprint
- `{OUTPUT_PATH}` — where the sprint doc must be written (derived by the conductor)
- `{REPO_ROOT}` — the repository the stories will be executed against
- `{EXEMPLAR_DOCS}` — up to two existing sprint docs beside the backlog, or `none`
- `{AUDIT_FAILURES}` — `none` on the first dispatch; the audit's verbatim output on the second

---

You are producing the sprint document for sprint {SPRINT_ID}, at {OUTPUT_PATH}.
This single pass does two things: it scopes the sprint from the backlog, and it
refines that scope against the live source under {REPO_ROOT} at pull time. The
refinement is the point — the backlog's one-liners were written before the code
moved beneath them, and your job is to surface what they could not know.

Two facts about your situation, stated up front because they are structural:

- **You cannot ask anyone anything.** You are a dispatched subagent: the
  question tool is unavailable to you, and in a headless run it would resolve
  instantly with an empty answer. Everything you need is in this prompt and on
  disk. Where the backlog leaves something open, make the smaller, reversible
  choice and record it as a numbered DoR finding with your recommended answer —
  the operator reads this doc at the very next gate and can overrule you there.
- **You must not run `supskill-state`, and you must not read or write anything
  under `.supskill/`.** You produce one document; the conductor alone records
  it in state.

Duties, in order:

1. **Scope.** Read {BACKLOG_PATH} in full. Your scope is the epic this sprint
   commits: the first epic in the backlog's recommended build order whose
   stories are still unchecked (☐). Name it on the doc's header line. The
   epic's story rows are your input — do not invent stories the backlog does
   not have, and do not import stories from another epic.

2. **Read the live source.** For each story in scope, read the actual functions
   it will change under {REPO_ROOT} — the real code, not just READMEs and
   docstrings. What counts as a gap worth surfacing is your judgment; this
   prompt does not pretend to specify it. What is NOT judgment: every claim you
   make about current behavior carries a backtick-wrapped `path:line` (or
   `path:start-end`) citation that resolves in {REPO_ROOT}'s working tree. A
   script audits every citation and fails this stage on any that does not
   resolve.

   A finding about supskill's own tooling or mechanism — not {REPO_ROOT}'s code
   — is not evidenced by a citation into the plugin's installed source tree; it
   doesn't live under {REPO_ROOT} and no such citation can resolve. Evidence for
   a tooling finding is the reproduced symptom itself: quote the exact command
   and its verbatim output in prose, with no backtick `path:line` token, so the
   citation audit has nothing to (mis)resolve.

3. **Write the doc** so that it carries ALL of the following (this list is the
   contract, item by item):
   - an H1 title; an Epic / Points / Milestone header line; a one-line sprint
     goal; a *why this sprint* paragraph; a sequencing note; the stories; a
     risks & mitigations table; exit criteria;
   - every story heading carries its backlog id, exactly one story per id:
     `### SK-0xx — <title> · <points> · <priority>` (use the backlog's own
     story-id prefix). Downstream stages join backlog rows to stories by these
     ids; a missing id breaks the join;
   - a **Context** paragraph per story, grounded in `file:line` citations;
   - exact acceptance criteria per story — testable statements, not themes;
   - named interfaces and exact paths for everything a story creates or edits;
   - a `## DoR findings (refined at pull time)` section with numbered findings,
     each carrying your recommended answer;
   - point deltas recorded story-by-story, inline: `N → M at pull time`;
   - one proof line per story, directly under the story heading, in exactly
     this grammar (three tokens, one value each, middot-separated):

     - **proof:** seam=unit|integration|app-level|e2e · impact=none|local|cross-surface|journey · provable=offline|operator

     Typical mapping: unit/integration → offline; app-level/e2e → operator; a
     mixed story classifies by its least-provable seam. Whether a
     classification is honest is the operator's judgment at the gate — the
     script only checks the vocabulary.

   There is no team here: no roster, no velocity, no PTO, no ceremonies. Do not
   invent a capacity number to plan against — commit the points the stories
   actually carry after refinement, and let the operator judge the total at the
   gate.

4. Shape the doc like the exemplars: {EXEMPLAR_DOCS}. Write it to {OUTPUT_PATH}
   — exactly that path, nowhere else. If this is a re-dispatch, edit that same
   file in place; do not write a second file and do not rename it, because the
   recorded artifact path never changes.

If this is a re-dispatch, fix every audit failure below before anything else:

{AUDIT_FAILURES}

Once the doc is written, **read it back** from disk and confirm it holds the
document you meant to write, **before you reply**. If that read fails, or the
file is empty, or something you wrote is not there, say exactly that in your
reply instead of reporting a write you cannot confirm.

Reply with one line and nothing else:

    WROTE {OUTPUT_PATH} — <committed> pts, <n> DoR findings

Nothing parses your reply for content: the conductor reads the document. The
document is the deliverable, not your report — nobody trusts the report alone.
