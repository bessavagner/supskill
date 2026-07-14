---
name: supskill
description: Drives one development sprint from a markdown backlog, and resumes an in-progress sprint from its on-disk state. Use when the operator wants to start or return to a supskill-managed sprint in the current repository.
argument-hint: run <sprint-id>
disable-model-invocation: true
---

# supskill — sprint conductor

Drives one sprint from a markdown backlog. This skill is the conductor's UX;
all enforcement lives in the state CLI. The conductor is disposable: its only
memory is `.supskill/state.json`, and every re-invocation reconstructs
everything from that file. Never rely on anything a previous conversation knew.

## Conventions (read first, apply always)

- The state CLI is always invoked as
  `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state` — an absolute path, never via
  `PATH` (only `bin/` joins `PATH`; `scripts/` does not).
- Always run it from the **target repo's root**: `.supskill/` resolves from the
  current working directory. Nothing is ever read from or written under the
  plugin root — it is wiped on every plugin update.
- **Never edit anything under `.supskill/` yourself.** Every mutation goes
  through a `supskill-state` verb. If the CLI refuses, report its message
  verbatim and stop — never work around a refusal.
- **Never pass `--archive`.** Archiving a half-finished sprint is an operator
  decision. The only thing this skill does with that flag is name it in a
  refusal message and stop — matrix cell 3 or the SCOPE stage's backlog check
  below.
- **Stage agents never touch state.** Stages dispatch subagents from templates
  under `references/`; the conductor runs every `supskill-state` call itself,
  and no template instructs an agent to run one or to write under `.supskill/`.

## Arguments

`$ARGUMENTS` is `run <sprint-id>` (e.g. `run s2`), optionally followed by
flags that are forwarded to `init` if — and only if — init runs:
`--entry SCOPE|PLAN|EXECUTE`, `--backlog <path>`, `--branch <name>`,
`--slug <slug>`.

- First token is not `run`, or there is no sprint id AND no
  `.supskill/state.json` in the current directory → print exactly this usage
  line and stop. Ask nothing — subagents cannot ask, and the conductor must
  not build a habit the stages cannot share:

      usage: /supskill run <sprint-id> [--entry SCOPE|PLAN|EXECUTE] [--backlog <path>] [--branch <name>]

- No sprint id but `.supskill/state.json` exists → treat as a resume of the
  on-disk sprint: start the run checklist at step 1 and skip the id
  comparison in step 3.

## The run checklist

Copy this checklist into your response and check items off as you go.

1. **Read state.** Run:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state show --json`
   - Refused with "no state file" → go to step 2 (matrix cell 1: init).
   - Refused with anything else (unreadable or invalid state) → report the
     CLI's message verbatim and stop. **Never re-init over a state file that
     exists but cannot be read** — that is the operator's call.
   - Success → go to step 3 (matrix cells 2 and 3).
2. **Init (no state on disk).** Run:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state init <sprint-id>`
   appending only the flags the operator gave in the invocation. Then run
   `show --json` again and continue at step 4.
3. **Compare ids.** Lowercase both the requested sprint id and `sprint.id`
   from the JSON.
   - Equal → this is a resume. Mutate nothing; continue at step 4.
   - Different → refuse and stop. The refusal must name both ids and the
     operator's way forward, verbatim:

         A different sprint is already on disk: state.json holds <sprint.id>,
         you asked for <requested-id>. A half-finished sprint is never
         archived automatically. If you mean to close it out and start fresh,
         run: ${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state init <requested-id> --archive

     Do not run that command. Stop here.
4. **Report the resume surface.** From the same `show --json` output, report:
   the sprint id and slug, current `stage`, `sprint.entry`, each gate's
   decision (`null` = pending), each recorded artifact path, the `backlog`
   path, task counts by status, and open blockers. This report must come from
   the JSON alone — consult no memory of any prior conversation.
5. **Dispatch on `stage`.** Look up `stage` in the table below and do exactly
   what it says. `stage` from `show --json` is the dispatch's only input.

## Dispatch table

| `stage` | Action |
|---|---|
| `SCOPE` | Follow **The SCOPE stage** below. |
| `REFINE` | Follow **The REFINE stage** below. |
| `PLAN` | Follow **The PLAN stage** below. |
| `EXECUTE` | Follow **The EXECUTE stage** below. |
| `REVIEW` | Report: "REVIEW is not implemented yet — it lands with E6 (PAR + Gate 3)." Stop. |

REVIEW is a stub until E6 lands — do not improvise it. An implemented stage
follows its section below exactly.

## The SCOPE stage

The stage pattern (E4–E6 copy this shape): dispatch a fresh-context subagent
from a template, verify its artifact mechanically, record it via
`supskill-state`, advance, fall through.

1. **Resume idempotence.** If `artifacts.sprint_doc` is recorded AND the file
   exists, SCOPE already ran — a crash between `artifact` and `advance` must
   not re-spend a run. Run `advance --to REFINE` and continue at the REFINE
   stage.
2. **Check the backlog.** If `backlog` is null (a pre-S3 state file; `init`
   now refuses to create this), report that a SCOPE sprint without a backlog
   has nothing to scope, name
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state init <sprint-id> --archive --backlog <path>`
   as the operator's way forward WITHOUT running it, and stop.
3. **Derive the output path** — a default the prompt supplies; the recorded
   artifact is the only authority anything downstream reads. The path is the
   backlog's own directory + `sprint-<id>-<slug>.md`, where `<id>` is the
   sprint id lowercased and `-<slug>` is dropped when `sprint.slug` is null.
   Example: backlog `docs/plans/sprints/backlog-01/backlog.md`, sprint `s4`,
   slug `plan-gate2` → `docs/plans/sprints/backlog-01/sprint-s4-plan-gate2.md`.
4. **Fill the template** [references/scope-prompt.md](references/scope-prompt.md)
   — every `{PLACEHOLDER}` it names. `{EXEMPLAR_DOCS}` is up to two existing
   `sprint-*.md` files in the backlog's directory (never the output path
   itself); if none exist, fill it with `none`.
5. **Dispatch** one general-purpose subagent whose entire prompt is the filled
   template.
6. **Verify mechanically.** The file must now exist at the derived output
   path. If it does not, report the agent's returned output verbatim and stop
   — no blocker verb is available before tasks exist, and the operator is one
   gate away.
7. **Record and advance.** Run
   `artifact --set sprint_doc --path <output path>`, then
   `advance --to REFINE`, then continue at the REFINE stage.

## The REFINE stage

Re-invoked at stage REFINE, always re-dispatch on the doc's current content.
Worst case an already-refined doc is refined again — acceptable, because
Gate 1 still guards the result. Detecting "already refined" would mean parsing
prose for state, which is exactly the coupling the resume contract refuses.

1. **Locate the doc:** `artifacts.sprint_doc` from `show --json`. If the file
   is missing from disk, report that and stop.
2. **Fill the template**
   [references/refine-prompt.md](references/refine-prompt.md):
   `{SPRINT_DOC_PATH}`, `{BACKLOG_PATH}`, `{REPO_ROOT}` (the repo root the
   conductor runs from), `{EXEMPLAR_DOC}` (an existing refined sprint doc in
   the backlog's directory, or `none`), `{AUDIT_FAILURES}` = `none`. Dispatch
   one general-purpose subagent with the filled template.
3. **Audit mechanically.** From the repo root, run:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-audit --proofs <doc path>`
   - Exit 0 → continue at **Gate 1** (next section).
   - Exit 1 → re-dispatch **once**: the same filled template with
     `{AUDIT_FAILURES}` set to the audit's failure output, quoted verbatim.
     Run the audit again. A second failure → report the failures verbatim and
     stop. Never dispatch a third time — there is no retry loop.

## Gate 1 — the operator reads the refined doc

The CLI records empty gate responses BY DESIGN — a fabricated approval must
leave a readable empty quote in the trail. So the refusal to treat silence as
consent lives here, in the conductor, and nowhere else.

1. **Ask for real.** Use the `AskUserQuestion` tool: approve / reject the
   refined sprint doc at its recorded path, free text welcome. Name the doc
   path in the question so the operator knows what they are approving.
2. **An empty or auto-resolved answer is not a decision.** In headless runs
   the question tool resolves instantly with an empty answer. If the answer
   comes back empty, do NOT call `gate`. Report that Gate 1 requires an
   interactive operator, and stop.
3. **Record verbatim.** A non-empty answer — the selected label plus any free
   text, unedited — goes to:
   `gate --id G1 --decision <approved|rejected> --response "<verbatim>"`
4. `approved` → `advance --to PLAN` → continue at **The PLAN stage** (below).
5. `rejected` → the decision is recorded and final for this pass; report it
   and stop, naming the rework loop: the operator edits the doc directly or
   asks for a fresh REFINE pass, then re-invokes `/supskill run <sprint-id>`
   and re-gates. The last decision wins in state while every attempt stays in
   the trail.

## The PLAN stage

Same pattern as SCOPE (dispatch → verify → record → advance), plus one thing no
earlier stage needed. The plan agent is the first dispatched agent whose own
skill tries to route it into *executing* what it just planned: `writing-plans`
ends by naming a REQUIRED SUB-SKILL per execution mode, and a subagent's
question tool auto-resolves empty. The template pre-answers that (layer 1). Step
6 catches it if the prompt fails to hold (layer 2).

1. **Resume idempotence.** If `artifacts.dev_plan` is recorded AND the file
   exists, the plan was already written: skip the dispatch and the HEAD guard
   entirely — do not re-dispatch, do not re-spend a plan run. Instead, from the
   repo root, run:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-audit <plan path>` — citations only,
   **no `--proofs`**: a dev plan carries no proof lines. Exit 1 → report the
   failures verbatim and stop; this is a hard failure, not advisory, so a
   hand-edited plan is checked before it ever reaches the operator. Exit 0 →
   run `artifact --set dev_plan --path <plan path>`, then
   `tasks --from <sprint doc path> --plan <plan path>` — the crash may have
   happened before tasks were loaded, and `tasks[]` must be populated before
   the gate — then continue at **Gate 2**.
2. **Locate the spec:** `artifacts.sprint_doc` from `show --json` — the doc the
   operator approved at Gate 1. Missing from disk → report that and stop.
3. **Derive the output path:**
   `docs/superpowers/plans/<YYYY-MM-DD>-sprint-<id>-<slug>.md`, where
   `<YYYY-MM-DD>` is today's date as the environment reports it, `<id>` is the
   sprint id lowercased, and `-<slug>` is dropped when `sprint.slug` is null.
   `writing-plans` has a dated-path convention of its own and honors an explicit
   override — supply this path and nothing else. Before dispatching, the
   conductor runs `mkdir -p` on the output path's parent directory. As always:
   `artifacts.dev_plan` is the only authority anything downstream reads.
4. **Record HEAD.** Run `git rev-parse HEAD` from the repo root and keep the SHA.
5. **Fill the template**
   [references/plan-prompt.md](references/plan-prompt.md) — `{SPRINT_DOC_PATH}`,
   `{OUTPUT_PATH}`, `{REPO_ROOT}`, `{EXEMPLAR_PLAN}` (an existing plan under
   `docs/superpowers/plans/`, or `none`) — and dispatch one general-purpose
   subagent whose entire prompt is the filled template.
6. **The HEAD guard.** Run `git rev-parse HEAD` again, then:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state plan-guard --before <before> --after <after>`
   - Exit 0 → continue.
   - Exit 1 → **stop here.** Do not record the artifact, do not load tasks, do
     not advance, do not call `gate`. Report the guard's message verbatim,
     followed by the output of `git log --oneline <before>..<after>` so the
     operator can see exactly what the plan agent committed. The plan stage
     produced commits; a plan is a document, and this run is stopped for you to
     inspect them.
7. **Verify and audit the plan.** The file must now exist at the derived output
   path. If it does not, report the agent's returned output verbatim and stop —
   never guess a path the agent may have used instead. Then, from the repo root:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-audit <plan path>` — citations only,
   **no `--proofs`**: a dev plan carries no proof lines. Exit 1 → report the
   failures verbatim and stop. This is a hard failure, not advisory; there is no
   re-dispatch loop at PLAN.
8. **Record and load tasks.** Run
   `artifact --set dev_plan --path <plan path>`, then
   `tasks --from <sprint doc path> --plan <plan path>`. The second call is where
   a plan that silently dropped a story is caught: every story in the sprint doc
   must be named by a `### Task N … (SK-0xx)` heading, and every task heading
   must name a known story or the literal `(process)`. On a refusal, report it
   verbatim and stop — the operator never approves a plan with a hole in it.
9. Continue at **Gate 2** (next section).

## Gate 2 — the operator reads the dev plan

The same shape as Gate 1, deliberately. The CLI records empty gate responses BY
DESIGN — a fabricated approval must leave a readable empty quote in the trail.
So the refusal to treat silence as consent lives here, in the conductor, and
nowhere else.

1. **Ask for real.** Use the `AskUserQuestion` tool: approve / reject the dev
   plan at its recorded path, free text welcome. Name the plan path in the
   question so the operator knows what they are approving.
2. **An empty or auto-resolved answer is not a decision.** In headless runs the
   question tool resolves instantly with an empty answer. If the answer comes
   back empty, do NOT call `gate`. Report that Gate 2 requires an interactive
   operator, and stop.
3. **Record verbatim.** A non-empty answer — the selected label plus any free
   text, unedited — goes to:
   `gate --id G2 --decision <approved|rejected> --response "<verbatim>"`
4. `approved` → `advance --to EXECUTE` → continue at **The EXECUTE stage**
   (below). That transition also re-checks that `tasks[]` is non-empty; a
   refusal there is reported verbatim and stops the run.
5. `rejected` → the decision is recorded and final for this pass; report it and
   stop, naming the rework loop: PLAN's resume idempotence means re-invoking
   `/supskill run <sprint-id>` with the rejected plan still recorded and still
   on disk skips the dispatch and re-gates on the same file. So the operator
   edits the recorded plan **at its path** directly, then re-invokes — the
   conductor re-reads the edited file from disk and re-gates it. To force a
   genuinely fresh PLAN run instead, the operator removes the recorded plan
   file first, so the "recorded AND the file exists" condition fails and PLAN
   dispatches again — that is the operator's call to make, never the
   conductor's: the conductor never deletes an artifact. The last decision
   wins in state while every attempt stays in the trail.

## The EXECUTE stage

**You are the controller.** Invoke `superpowers:subagent-driven-development` in
**your own session** and run its loop yourself — that is the same-session mode
SDD's own decision tree names. Do not hand the loop to a subagent: the loop is
where every status, blocker and concern appears, and a subagent can neither run
`supskill-state` (invariant 3) nor ask the operator anything (D4). The
fresh-context boundary is still there — SDD puts it per *task*, which is where
it belongs.

Compose SDD verbatim (D1): its implementer prompt, its task-reviewer prompt, its
review loop, its fix loop, its model selection. supskill re-implements none of
it and adds no prompt template of its own. What supskill adds is the discipline
below. **Read SDD's SKILL.md and its three `scripts/` before the first
dispatch** — Model Selection, Handling Implementer Status, File Handoffs,
Durable Progress and Red Flags are the contract you are composing.

### Before the first dispatch — four checks, in this order

1. **The branch check.** Run `git rev-parse --abbrev-ref HEAD`. If it is the
   repo's default branch, **stop before dispatching anything**: report that
   EXECUTE writes commits and will not write them to the default branch, and name
   `git switch -c <branch>` as the operator's move. Do not create, switch, or
   delete a branch yourself — the same restraint that keeps `--archive` out of
   your hands. (SDD forbids implementing on main without explicit consent, and a
   subagent cannot give it.)
2. **Prepare the scratch.** Run SDD's `sdd-workspace` script once — it creates
   `.superpowers/sdd/` and writes the self-ignoring `.gitignore` that keeps every
   sprint's scratch out of `git status`. Then `mkdir -p <scratch>`, where
   `<scratch>` is `sprint.scratch` from `show --json`. **Neither is optional.**
   `task-brief` writes its `OUTFILE` with a plain shell redirect and never
   creates the parent, so the first brief dies on a missing directory; and
   passing `OUTFILE` is exactly what skips `sdd-workspace`'s own call, so a
   target repo that does not already ignore `.superpowers/` will let an
   implementer's `git add -A` commit this sprint's briefs and diffs.
3. **Read the plan.** `artifacts.dev_plan` from `show --json` is the plan, and
   the only authority for it. Missing from disk → report that and stop.
4. **SDD's pre-flight plan review.** Scan the plan once for conflicts, as SDD
   requires. SDD batches them into one question to a human; you have none. Every
   conflict becomes a blocker on the task it affects — with real options, per the
   blocker rules below — and that task is parked. If the scan blocks every task,
   the drain runs nothing and the halt is immediate. That is correct, and it is
   not a crash.

### The dispatch discipline — every task, no exceptions

- **Every scratch path is passed explicitly, and derived, never typed**
  (invariant 4). `<scratch>` is `sprint.scratch` from `show --json`:
  - brief: `task-brief <dev_plan> <N> <scratch>/task-<N>-brief.md`
  - report: `<scratch>/task-<N>-report.md` — named after the brief, per SDD's
    File Handoffs rule, so re-reading a task's outcome is one `Read`, never a
    re-dispatch
  - review package: `review-package <BASE> HEAD <scratch>/review-<N>.diff`
- **`BASE` is recorded, never derived.** Before each implementer dispatch, run
  `git rev-parse HEAD` and keep that SHA as the task's `BASE`. **Never `HEAD~1`**
  — SDD says in as many words that it silently drops all but the last commit of a
  multi-commit task. The final whole-branch review gets its own package:
  `review-package $(git merge-base <default-branch> HEAD) HEAD <scratch>/review-final.diff`.
  `sprint.branch` is optional at init and is not the authority here — `git` is.
- **Every dispatch names its model explicitly.** An omitted model silently
  inherits this session's — usually the most capable and most expensive one.
  *Which* model per role is SDD's Model Selection section's call, not this
  skill's; do not restate it, follow it.
- **The ledger is `state.json`.** Do not read or write `.superpowers/sdd/progress.md`.
  It is keyed by task number, task numbers restart every sprint, and its
  contract is "listed complete = do not re-dispatch" — so a ledger left by one
  sprint tells the next that its Task 1 is already finished. `tasks[]` is the ledger:
  sprint-scoped by construction, and the file you resume from (invariant 5). A
  stale `progress.md` on disk is ignored and named once in the halt report, so
  the operator can delete it.
- **No dispatched agent runs `supskill-state`** or touches `.supskill/`
  (invariant 3). SDD's implementers commit code; you record every status, every
  blocker and every advance yourself — **after** the task review, never on an
  implementer's word alone. An implementer that can write state can mark its own
  work done.

The drain that uses all of this is the next subsection.

## Reference

- Why this skill is user-invoked only:
  [references/invocation-model.md](references/invocation-model.md)
