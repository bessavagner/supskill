# REFINE dispatch template

The conductor fills every `{PLACEHOLDER}` below and dispatches the result as
the complete prompt of one general-purpose subagent. On an audit failure the
conductor re-dispatches ONCE, with the audit's output filled into
`{AUDIT_FAILURES}`:

- `{SPRINT_DOC_PATH}` — the sprint doc to refine, in place
- `{BACKLOG_PATH}` — the backlog the doc was scoped from
- `{REPO_ROOT}` — the repository the stories will be executed against
- `{EXEMPLAR_DOC}` — a refined sprint doc whose shape is the target, or `none`
- `{AUDIT_FAILURES}` — `none` on the first dispatch; the audit's verbatim output on the second

---

You are refining the sprint document at {SPRINT_DOC_PATH} against the live
source under {REPO_ROOT}, at pull time. This pass exists because the backlog's
one-liners were written before the code moved beneath them; your job is to
surface what they could not know.

Two facts about your situation, stated up front because they are structural:

- **You cannot ask anyone anything.** You are a dispatched subagent: the
  question tool is unavailable to you, and in a headless run it would resolve
  instantly with an empty answer. Everything you need is in this prompt and on
  disk. Record open questions as numbered DoR findings with your recommended
  answer — the operator reads this doc at the very next gate.
- **You must not run `supskill-state`, and you must not read or write anything
  under `.supskill/`.** You edit one document; the conductor alone talks to
  state.

Duties, in order:

1. Read the doc, the backlog rows it commits, and then the live source those
   stories touch — the actual functions they will change, not just READMEs
   and docstrings. What counts as a gap worth surfacing is your judgment;
   this prompt does not pretend to specify it. What is NOT judgment: every
   claim you make about current behavior carries a backtick-wrapped
   `path:line` (or `path:start-end`) citation that resolves in {REPO_ROOT}'s
   working tree. A script audits every citation and fails this stage on any
   that does not resolve.

   A finding about supskill's own tooling or mechanism — not {REPO_ROOT}'s
   code — is not evidenced by a citation into the plugin's installed source
   tree; it doesn't live under {REPO_ROOT} and no such citation can resolve.
   Evidence for a tooling finding is the reproduced symptom itself: quote the
   exact command and its verbatim output in prose, with no backtick
   `path:line` token, so the citation audit has nothing to (mis)resolve.

2. Grow the doc until it carries ALL of the following (this list is the
   contract, item by item):
   - a **Context** paragraph per story, grounded in `file:line` citations;
   - exact acceptance criteria per story — testable statements, not themes;
   - named interfaces and exact paths for everything a story creates or edits;
   - a `## DoR findings (refined at pull time)` section with numbered findings;
   - point deltas recorded story-by-story, inline: `N → M at pull time`;
   - one proof line per story, directly under the story heading, in exactly
     this grammar (three tokens, one value each, middot-separated):

     - **proof:** seam=unit|integration|app-level|e2e · impact=none|local|cross-surface|journey · provable=offline|operator

     Typical mapping: unit/integration → offline; app-level/e2e → operator; a
     mixed story classifies by its least-provable seam. Whether a
     classification is honest is the operator's judgment at the gate — the
     script only checks the vocabulary.
3. Edit {SPRINT_DOC_PATH} **in place**. Do not write a second file, do not
   rename it: the recorded artifact path never changes.
4. Shape target: {EXEMPLAR_DOC}.

If this is a re-dispatch, fix every audit failure below before anything else:

{AUDIT_FAILURES}

Once the doc is edited, **read it back** from disk and confirm your edits are
actually in the file, **before you reply**. If that read fails, or the file is
empty, or an edit you made is not there, say exactly that in your reply instead
of reporting an edit you cannot confirm.

Reply with one line and nothing else:

    WROTE {SPRINT_DOC_PATH} — <n> DoR findings

Nothing parses your reply for content: the conductor reads the document. The
document is the deliverable, not your report — nobody trusts the report alone.
