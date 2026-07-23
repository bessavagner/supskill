# PLAN dispatch template

The conductor fills every `{PLACEHOLDER}` below and dispatches the result as
the complete prompt of one general-purpose subagent:

- `{SPRINT_DOC_PATH}` — the G1-approved sprint doc; it is the spec
- `{OUTPUT_PATH}` — where the dev plan must be written (derived by the conductor)
- `{REPO_ROOT}` — the repository the plan will be executed against
- `{EXEMPLAR_PLAN}` — an existing dev plan under `docs/superpowers/plans/`, or `none`

---

You are writing the implementation plan for the sprint specified at
{SPRINT_DOC_PATH}. Invoke the `superpowers:writing-plans` skill and follow it:
the sprint doc is the spec that skill asks for. Read it in full first, and read
the live source under {REPO_ROOT} for every file the plan will touch.

Three facts about your situation, stated up front because they are structural:

- **You cannot ask anyone anything.** You are a dispatched subagent: the
  question tool is unavailable to you, and in a headless run it would resolve
  instantly with an empty answer. Everything you need is in this prompt, in the
  sprint doc, and on disk. Where the spec leaves something open, make the
  smaller, reversible choice and say so in the plan — the operator reads this
  plan at a gate and can overrule you there.
- **You must not run `supskill-state`, and you must not read or write anything
  under `.supskill/`.** You produce one document; the conductor alone records it.
- **The execution question is already answered: subagent-driven, always.**
  `writing-plans` ends with an Execution Handoff that offers you two execution
  modes and names a REQUIRED SUB-SKILL for each. Do not answer it, and do not
  route into it. **Do not invoke `superpowers:subagent-driven-development` or
  `superpowers:executing-plans`.** Do not implement, test, or commit anything.
  Write the plan, save it, report the path, and stop. A plan is a document; the
  stage that executes it is a different stage, behind a gate you cannot see.
  Leave the plan's mandated header untouched: it will still name
  `superpowers:subagent-driven-development`, and that is not a command to you —
  it is `writing-plans`'s own text, meant for the conductor at a later stage,
  behind a gate you cannot see.

Your task:

1. Write the plan to {OUTPUT_PATH} — exactly that path, nowhere else. This
   overrides `writing-plans`' own dated-path default; the conductor supplies the
   path because the date is not derivable from a plan it has not read yet.
2. **Every task heading names the story it serves:**
   `### Task N: <what> ({STORY_ID_PREFIX}-0xx)` — or the literal `### Task N: <what> (process)`
   for a task that serves no backlog story (a demo checklist, a docs-only
   delta). This is a join key, not a decoration: a script checks that every
   story in the sprint doc is named by at least one task heading and that every
   task heading names a known story or `(process)`. A plan that drops a story is
   refused before the operator ever sees it. One heading may name two stories.
3. **Citations: cite `file:line` only for code that exists today.** A script
   resolves every backtick-wrapped `path:line` (and `path:start-end`) citation
   in your plan against the working tree and fails this stage on any that does
   not resolve. A task that CREATES a file names the path with no line number —
   `Create: \`scripts/foo.py\`` — because a line number for a file that does not
   exist yet cannot resolve and never will. Read the live source before citing
   it; the sprint doc was written earlier and its line numbers may have shifted.

   A finding about supskill's own tooling or mechanism — not {REPO_ROOT}'s
   code — is not evidenced by a citation into the plugin's installed source
   tree; it doesn't live under {REPO_ROOT} and no such citation can resolve.
   Evidence for a tooling finding is the reproduced symptom itself: quote the
   exact command and its verbatim output in prose, with no backtick
   `path:line` token, so the citation audit has nothing to (mis)resolve.

4. Shape target: {EXEMPLAR_PLAN}. Honor the sprint doc's own sequencing section
   if it has one — it was written by someone who knew what blocks what.

How to decompose the work into tasks is `writing-plans`' business and your
judgment; this prompt does not pretend to specify it.

Once the plan is written, **read it back** from disk and confirm it holds the
plan you meant to write, **before you reply**. If that read fails or the file is
empty, say exactly that in your reply instead of reporting a write you cannot
confirm.

Reply with one line and nothing else:

    WROTE {OUTPUT_PATH} — <n> tasks

Nothing parses your reply for content: the conductor reads the document. The
document is the deliverable, not your report.
