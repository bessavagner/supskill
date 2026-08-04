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
  verbatim and stop — never work around a refusal, **except** where
  [references/stop-classes.md](references/stop-classes.md) classifies that stop
  as **remediable**. There, and only there, take exactly the action that file
  names for it, then record it with `action --stop <id> --command "<the exact
  command>" --operator-answered`. A stop the file does not list as remediable is
  evidential: relay it verbatim and stop, whatever it looks like you could fix.
  A remediable stop's refusal text is a report of what to do, not a hand-back.
- **Pass `--archive` only to close a sprint whose G3 decision is recorded** (`init.archive.decided`) — never over one still open. A sprint resting at `REVIEW` with no `G3` decision is `init.archive.undecided`, and `init --archive` itself still refuses over it: archiving it would keep the question and lose the answer (SK-115). Every stop's class — which the conductor now acts on, which still refuses — is [references/stop-classes.md](references/stop-classes.md).
- **Stage agents never touch state.** Stages dispatch subagents from templates
  under `references/`; the conductor runs every `supskill-state` call itself,
  and no template instructs an agent to run one or to write under `.supskill/`.
- **Every subagent dispatch is costed.** Right after it completes, run
  `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state cost --stage <stage> --tokens <subagent_tokens>` (add `--tool-uses`/`--duration-ms` when reported, `--label <name>` where a stage names one) — even if verification fails downstream.

## Arguments

`$ARGUMENTS` is `run <sprint-id>` (e.g. `run s2`), optionally followed by
flags that are forwarded to `init` if — and only if — init runs:
`--entry SCOPE|PLAN|EXECUTE`, `--backlog <path>`, `--branch <name>`,
`--slug <slug>`, `--continues <sprint-id>` (the sprint a PLAN- or EXECUTE-entry
sprint resumes; `init` defaults it to the archived sprint's id).

- First token is not `run`, or there is no sprint id AND no
  `.supskill/state.json` in the current directory → print exactly this usage
  line and stop. Ask nothing — subagents cannot ask, and the conductor must
  not build a habit the stages cannot share:

      usage: /supskill run <sprint-id> [--entry SCOPE|PLAN|EXECUTE] [--backlog <path>] [--branch <name>]

- No sprint id but `.supskill/state.json` exists → treat as a resume of the
  on-disk sprint: start the run checklist at step 1 and skip the id
  comparison in step 3.

## The run checklist

Copy this checklist into your response and check items off as you go. A run that has not received a real, non-empty answer from an operator this run takes no remediable action below — `action` refuses without `--operator-answered`, and that refusal is relayed verbatim like any other stop.

**Where that answer comes from, and why this rule is written down rather than remembered.** A run may take a remediable action only after a real, non-empty answer has come back from an operator *in this run*: the `AskUserQuestion` answer at a gate or at a blocker question, or — at step 3, which precedes every gate — this invocation's own live request for a different sprint id. Nothing on disk records that a run reached an operator. `actions.jsonl` records the claim (`operator_answered`), never what made the claim true, so a conductor re-invoked after `/clear` cannot read the fact back and must not assume it: a resumed run has established nothing yet, whatever the trail shows, and re-establishes at the first gate or blocker question this checklist brings it to. Pass `--operator-answered` only for an answer you have just read yourself. Passing it on any other basis is a fabricated attestation — F-4's ceiling applies here exactly as it applies to a gate's recorded response: the CLI records what the conductor claims, not what a human did.

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
   - Different, and the on-disk sprint is **not** resting at `REVIEW` with `gates.G3_review` null — i.e. any other `stage`, or `stage` is `REVIEW` with `gates.G3_review` non-null — this is `init.archive.decided` ([references/stop-classes.md](references/stop-classes.md)): run `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state init <requested-id> --archive <every --entry/--backlog/--branch/--slug flag from this invocation, verbatim>` — never drop a flag the operator typed: an init that loses `--backlog` starts a sprint with `backlog: null`, which `replan-guard` refuses at Gate 3 — then `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state action --stop init.archive.decided --command "<the exact init line just run>" --operator-answered`. Then run `show --json` again and continue at step 4 — the JSON you read at step 1 described the sprint you just archived, and step 4 reports and step 6 dispatches on the sprint that exists **now** (invariant 5: never carry state across a mutation in your head).
   - Different, and `stage` **is** `REVIEW` **and** `gates.G3_review` is null (`init.archive.undecided`) → refuse and stop. The refusal must name both ids, the flags you gave this invocation, and the operator's way forward, verbatim:

         A different sprint is already on disk: state.json holds <sprint.id>,
         you asked for <requested-id>. A half-finished sprint is never
         archived automatically. If you mean to close it out and start fresh, run:
         ${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state init <requested-id> --archive <every --entry/--backlog/--branch/--slug flag from this invocation, verbatim>

     Never drop a flag the operator typed: an init that loses `--backlog` starts
     a sprint with `backlog: null`, which `replan-guard` refuses at Gate 3.
     Do not run that command. Stop here.
4. **Report the resume surface.** From the same `show --json` output, report:
   the sprint id and slug, current `stage`, `sprint.entry`, each gate's
   decision (`null` = pending), each recorded artifact path, the `backlog`
   path, task counts by status, and open blockers. This report must come from
   the JSON alone — consult no memory of any prior conversation.
5. **Preflight the skills the remaining stages dispatch.** Before dispatching,
   confirm every external skill a stage from the current `stage` onward will
   dispatch actually resolves — a declared dependency can still be missing,
   disabled, or its marketplace unreachable, and a stage that cannot load the
   skill it dispatches improvises. For each required skill (PLAN dispatches
   `superpowers:writing-plans`; EXECUTE dispatches `superpowers:subagent-driven-development`),
   resolve its base directory by loading the skill — its payload's first line
   is `Base directory for this skill: <abs path>`. A skill that will not load
   at all is already the refusal: report it and stop. Then run, passing each
   resolved skill as `name=<base-dir>`:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state preflight --stage <stage> --skill writing-plans=<dir> --skill subagent-driven-development=<dir>`
   (pass only the skills the remaining stages need; omit any you could not resolve —
   the guard refuses by omission). Exit 1 → report verbatim and stop; do not
   dispatch. Exit 0 → continue at step 6.
6. **Dispatch on `stage`.** Look up `stage` in the table below and do exactly
   what it says. `stage` from `show --json` is the dispatch's only input.

## Dispatch table

| `stage` | Action |
|---|---|
| `SCOPE` | Follow **The SCOPE stage** below. |
| `PLAN` | Follow **The PLAN stage** below. |
| `EXECUTE` | Follow **The EXECUTE stage** below. |
| `REVIEW` | Follow **The REVIEW stage** below. |

## The SCOPE stage

One stage scopes the sprint from the backlog **and** refines it against live
source, in a single dispatch — there is no separate REFINE stage (SK-100
collapsed the two: SCOPE's output was never gated on its own, so it produced an
ungated intermediate REFINE rewrote anyway). The stage pattern the later stages
copy: dispatch a fresh-context subagent from a template, verify its artifact
mechanically, audit it, record it via `supskill-state`, then Gate 1.

1. **Resume idempotence.** If `artifacts.sprint_doc` is recorded AND the file
   exists, the scope-and-refine pass already ran — do not re-dispatch (a crash
   between the dispatch and `artifact` leaves no recorded artifact, so this
   check only skips a genuinely finished pass). Continue at step 6 (audit).
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
   — every `{PLACEHOLDER}` it names. `{REPO_ROOT}` is the repo root the
   conductor runs from; `{EXEMPLAR_DOCS}` is up to two existing `sprint-*.md`
   files in the backlog's directory (never the output path itself), or `none`;
   `{AUDIT_FAILURES}` is `none` on the first dispatch. `{STORY_ID_PREFIX}` is
   this project's configured story-id prefix: read it once with
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state config --get` and fill it verbatim.
5. **Dispatch** one general-purpose subagent whose entire prompt is the filled
   template, then `cost --stage SCOPE --label refine`.
6. **Verify mechanically.** The file must now exist at the derived output
   path. If it does not, report the agent's returned output verbatim and stop
   — no blocker verb is available before tasks exist, and the operator is one
   gate away. Then record it: `artifact --set sprint_doc --path <output path>`.
7. **Audit mechanically.** From the repo root, run:
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-audit --proofs <doc path>`
   - Exit 0 → continue at **Gate 1** (next section).
   - Exit 1 → re-dispatch **once**: the same filled template with `{AUDIT_FAILURES}` set to the audit's failure output, quoted verbatim, then `cost --stage SCOPE --label refine-retry`. Run the audit again. A second failure → report the failures verbatim and stop. Never dispatch a third time — there is no retry loop.

## Gate 1 — the operator reads the refined doc

Ask for real, refuse an empty answer, record verbatim: [references/gate.md](references/gate.md).

4. `approved` → `advance --to PLAN` → continue at **The PLAN stage** (below).
5. `rejected` → recorded and final for this pass; report it and stop, naming the rework loop: edit the doc or ask for a fresh SCOPE pass, then re-invoke and re-gate. Last decision wins in state; every attempt stays in the trail.

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
   `docs/superpowers/plans/`, or `none`), and `{STORY_ID_PREFIX}` (read once with
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state config --get`) — dispatch one general-purpose
   subagent whose entire prompt is the filled template, then `cost --stage PLAN`.
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

Ask for real, refuse an empty answer, record verbatim - the same shape as Gate 1: [references/gate.md](references/gate.md).

4. `approved` → `advance --to EXECUTE` → continue at **The EXECUTE stage** (below). That transition also re-checks that `tasks[]` is non-empty; a refusal there is reported verbatim and stops the run.
5. `rejected` → recorded and final for this pass; report it and stop. PLAN's resume idempotence means re-invoking with the rejected plan still on disk skips the dispatch and re-gates the same file, so the operator edits the recorded plan **at its path** directly, then re-invokes. To force a fresh PLAN run, the operator removes the recorded plan file first - the conductor never deletes an artifact itself.

## The EXECUTE stage

**You are the controller.** Invoke `superpowers:subagent-driven-development` in **your
own session** and run its loop yourself — that is the same-session mode SDD's own
decision tree names. Do not hand the loop to a subagent: the loop is where every status,
blocker and concern appears, and a subagent can neither run `supskill-state`
(invariant 3) nor ask the operator anything (D4). The fresh-context boundary is still
there — SDD puts it per *task*, which is where it belongs.

Compose SDD verbatim (D1): its implementer prompt, its task-reviewer prompt, its review
loop, its fix loop, its model selection — everything except the final whole-branch
review, which is E6's; see **The halt**. supskill re-implements none of it and adds no
prompt template of its own. What supskill adds is the discipline below. **Read SDD's
SKILL.md and its three `scripts/` before the first dispatch** — Model Selection, Handling
Implementer Status, File Handoffs, Durable Progress and Red Flags are the contract you
are composing.

### Before the first dispatch — four checks, in this order

SDD's three scripts — `sdd-workspace`, `task-brief`, `review-package` — live in
the installed superpowers plugin: not on `PATH`, and **not** under
`${CLAUDE_PLUGIN_ROOT}` (that is *this* plugin). Resolve their directory once from the
loaded `subagent-driven-development` skill's own location — the skill payload's first
line, `Base directory for this skill: <abs path>`, is that location, so do not glob the
plugin cache — invoke each by absolute path, and **never re-implement one**: a
hand-rolled `task-brief` hands the implementer a brief that is not SDD's, which is
exactly the D1 violation this stage exists to avoid.

1. **The branch check.** Derive the default branch, never assume it: it is what
   `git symbolic-ref --short refs/remotes/origin/HEAD` names with `origin/` stripped.
   **If that command fails or prints nothing** — `origin/HEAD` is unset in any repo not
   created by `git clone` — use `git config --get init.defaultBranch`; if that is unset
   too, take whichever of `origin/main` / `origin/master`
   `git rev-parse --verify --quiet` resolves, and if neither or both resolve, that is a
   **blocker**: the ladder never ends in a `main` guess. Then run
   `git rev-parse --abbrev-ref HEAD`. Not the default branch, and not the literal `HEAD`
   (detached) → the **dispatch root** is the repo root; go to check 2. Otherwise → do not
   stop: isolate into a worktree and set the dispatch root to its path, per
   [references/worktree-notes.md](references/worktree-notes.md). Do not create, switch,
   or delete a branch yourself outside of that one script call — the same restraint that
   keeps `--archive` out of your hands.
2. **Prepare the scratch.** From the dispatch root, run SDD's `sdd-workspace` script
   once — it creates `.superpowers/sdd/` and writes the self-ignoring `.gitignore`
   that keeps every sprint's scratch out of `git status`. Then `mkdir -p <scratch>`,
   also at the dispatch root, where `<scratch>` is `sprint.scratch` from `show --json`.
   **Neither is optional.** `task-brief` writes its `OUTFILE` with a plain shell
   redirect and never creates the parent, so the first brief dies on a missing
   directory; and passing `OUTFILE` is exactly what skips `sdd-workspace`'s own call,
   so a target repo that does not already ignore `.superpowers/` will let an
   implementer's `git add -A` commit this sprint's briefs and diffs.
3. **Read the plan.** `artifacts.dev_plan` from `show --json` is the plan, and the
   only authority for it — read it from the dispatch root (its synced copy, when a
   worktree is in use). Missing from disk → report that and stop.
4. **SDD's pre-flight plan review.** Scan the plan once for conflicts, as SDD
   requires. SDD batches them into one question to a human; you have none. Every
   conflict becomes a blocker on the task it affects — with real options, per the
   blocker rules below — and that task is parked. If the scan blocks every task,
   the drain runs nothing and the halt is immediate. That is correct, and it is
   not a crash.

### The dispatch discipline — every task, no exceptions

- **Every scratch path is passed explicitly, and derived, never typed**
  (invariant 4), all of it relative to the dispatch root established in the branch
  check. `<scratch>` is `sprint.scratch` from `show --json`:
  - brief: `task-brief <dev_plan> <N> <scratch>/task-<N>-brief.md`, `<dev_plan>` read
    from the dispatch root's synced copy
  - report: `<scratch>/task-<N>-report.md` — named after the brief, per SDD's
    File Handoffs rule, so re-reading a task's outcome is one `Read`, never a
    re-dispatch
  - review package: `review-package <BASE> HEAD <scratch>/review-<N>.diff`
  - every implementer dispatch's `Work from:` line names the dispatch root, never an
    assumed repo root
- **`BASE` is recorded, never derived.** Before each implementer dispatch, run
  `git -C <dispatch-root> rev-parse HEAD` and keep that SHA as the task's `BASE`.
  **Never `HEAD~1`** — SDD says in as many words that it silently drops all but the
  last commit of a multi-commit task. EXECUTE also **produces** the final
  whole-branch review's package — an output it leaves for E6, never an input it
  consumes (see **The halt**):
  `review-package $(git -C <dispatch-root> merge-base <default-branch> HEAD) HEAD <scratch>/review-final.diff`,
  run from `<dispatch-root>`, with `<default-branch>` derived exactly as in the
  branch check.
  Then record what that package covers, so REVIEW can prove it is still the branch:
  `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state package --base <the merge-base you just used> --head $(git -C <dispatch-root> rev-parse HEAD) --path <scratch>/review-final.diff --dispatch-root <dispatch-root>`
  EXECUTE and REVIEW are different runs; a SHA you do not write down does not survive
  the gap (SK-104). Pass `--dispatch-root` always: the package is cut in
  `<dispatch-root>`, which is a worktree when EXECUTE isolated (check 1), and
  `review-guard` must rev-parse HEAD in that same repo, never the state root.
- **Every dispatch names its model explicitly.** An omitted model silently
  inherits this session's — usually the most capable and most expensive one.
  *Which* model per role is SDD's Model Selection section's call, not this
  skill's; do not restate it, follow it.
- **The ledger is `state.json`.** Do not read or write `.superpowers/sdd/progress.md`.
  It is keyed by task number, task numbers restart every sprint, and its
  contract is "listed complete = do not re-dispatch" — so a ledger left by one
  sprint tells the next that its Task 1 is already finished. `tasks[]` is the ledger:
  sprint-scoped by construction, and the file you resume from (invariant 5).
- **No dispatched agent runs `supskill-state`** or touches `.supskill/`
  (invariant 3). SDD's implementers commit code; you record every status, every
  blocker and every advance yourself — **after** the task review, never on an
  implementer's word alone. An implementer that can write state can mark its own
  work done.
- **Scope every task's commits to its own files.** After a task's implementer and
  fix dispatches have committed — before recording any status — run, from the
  dispatch root:
  `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state commit-scope-guard --before <BASE> --after $(git -C <dispatch-root> rev-parse HEAD) --dir <dispatch-root>`
  Exit 1 → **stop.** An implementer's `git add -A` swept a harness's state
  (`.omc/`) or the conductor's own (`.supskill/`) into the commit. Report the
  guard's message verbatim; do not record the task's status — its commit is
  tainted. The remedy is the reset the guard names; this run is stopped for the
  operator, the same restraint as the HEAD guard at PLAN.

### The drain

The unit of work is a **`### Task N` heading in the dev plan**, taken in the dev
plan's own task order — not `tasks[]` order, which comes from the sprint doc's
proof lines and can differ. Every artifact in the cycle below is keyed by that
`N`. `tasks[]` stays the **ledger** (invariant 5), not the loop. A heading may name
**several** stories, and one story may be served by **several** headings — S5's own
plan carries `### Task 1: … (SK-043)` and `### Task 3: … (SK-041, SK-043)`. So the
branch is over the heading's whole set of stories. For each heading, in plan order:

- it is marked `(process)` → run the cycle, and record **no** status: it serves no
  story, so `tasks[]` has no entry to write. The halt report names it as run;
- otherwise, **every** story it names is already terminal → skip it: a terminal
  story's plan tasks are **never re-dispatched**, SDD's ledger rule on our ledger;
- otherwise, it names at least one story that is not terminal → run the cycle, and
  record a status against **each** story the heading names — including one already
  recorded by an earlier heading, which is re-recorded here (step 3).

The cycle:

1. Record `BASE` (`git rev-parse HEAD`), write the brief, dispatch a fresh
   implementer, then the task reviewer, then a fix subagent on any Critical or
   Important finding. That is SDD's cycle, unchanged. Cost each dispatch as it
   completes, `--label <N>-implementer` / `<N>-task-reviewer` / `<N>-fix`
   (`<N>` = this heading's task number).

   **The task reviewer writes its findings to a file, never to its reply.** SDD's
   task-reviewer prompt returns its findings as its final chat message, and a
   dispatched agent's final message is exactly what collapses to a placeholder
   (the same failure `7dfb0f9` fixed for supskill's own dispatches). So when you
   dispatch the task reviewer, tell it — in addition to SDD's prompt — to write
   its full findings and its two verdicts (spec compliance, task quality) to
   `<scratch>/task-<N>-review-findings.md` and to return only a one-line status.
   You then **read that file** for the verdicts and act on them; you rely on the
   file, **never the reply**. A reviewer that cannot write the file says so in the
   one line it returns, which is loud — a lost finding read as an approval is not.
2. Map what SDD reported onto the spine, **before the next dispatch begins** — a
   `/clear` or a crash mid-drain then costs at most one task's work:

   | SDD reports | You run |
   |---|---|
   | `DONE` | `task --id <SK-0xx> --status DONE` — `--note` carries the task's Minor-findings roll-up, which E6's final whole-branch review reads. A roll-up nobody reads is a silent discard. |
   | `DONE_WITH_CONCERNS` | `task --id <SK-0xx> --status DONE_WITH_CONCERNS --note "<the concern, verbatim>"`. The drain continues; the concern surfaces in the halt batch. |
   | `BLOCKED` | `block --task <SK-0xx> --kind … --found … --option "(a) …" --option "(b) …" --recommend "(a) — because …"`, which flips the status itself. |
   | `NEEDS_CONTEXT` | Supply the missing context and re-dispatch the same task **once**. Still `NEEDS_CONTEXT` → `block`. It is a controller-loop signal, not a resting state, and there is no unbounded loop anywhere in this stage. |

3. **The join is the plan task's heading** — `### Task N: <what> (SK-0xx)`, the one
   required by PLAN and validated when `tasks` loaded. This stage adds no parser. Where
   several headings serve one story, the record stays **eager**: re-record the story as
   each of its headings lands, and record the roll-up so far — the story is `DONE` only
   when **all** of its headings are; any `DONE_WITH_CONCERNS` among them makes it
   `DONE_WITH_CONCERNS`; any blocker among them blocks it. Re-recording is what the verb
   is for: every attempt is appended to the trail and the **last** status wins in state,
   so the trail carries the history and state carries the roll-up. Never defer a story's
   record to its last heading.

**Resume is the loop's boundary, not a step in it.** Re-invoking
`/supskill run <sprint-id>` restarts the heading walk at the first heading whose stories
are not all terminal — the first `PENDING` task's heading — read from `state.json`
alone. But `PENDING` does not mean *untouched*: a task may already carry commits from a
dispatch that crashed after the implementer committed and before you recorded the
status. The trail records the status, not the SHA — a task's `BASE` and its commit list
live only in this conversation, and a `/clear` destroys them. So before re-dispatching a
`PENDING` task, check whether HEAD has moved since the last recorded status. That anchor
is on disk. Compare the newest commit's time with the `at` of the last record in
`.supskill/runs/<sprint-id>/tasks.jsonl`: both sides must be UTC, or the string compare is
not an instant compare. The trail's `at` is UTC by enforcement, and a bare `%cI` prints local
time, so read the commit's time with `TZ=UTC git log -1 --date=iso-strict-local --format=%cd`.
A commit newer than the last recorded status means that task is partially implemented, its
`BASE` is lost, and a re-dispatch would re-record `BASE` at the *current* HEAD, hand the
reviewer an **empty diff**, and mark unreviewed code `DONE`. That is a **blocker**, not a guess.

**Downstream is discovered, not predicted.** A blocker stops its chain, not the drain. A
later task that comes back `BLOCKED` for the **same root cause** — its report names the
already-blocked story, or the artifact that story was to produce — is recorded
`task --id <SK-0xx> --status PARKED --note "<the blocker that parked it>"`, not blocked
a second time. One blocker per root cause; the options are enumerated once. What counts
as the same root cause is your judgment, and this prose does not pretend otherwise.

**`provable` gates the claim, not the run:** every task runs — `provable` is not
a skip filter. It decides what the halt report may claim about a finished task:
an `offline` task is *proven*, with its test command and that command's output;
an `operator` task is *implemented and reviewed, **not proven** — verify by hand*.

**SDD's two remaining "ask the human" points become blockers, not guesses.**

- A reviewer finding labelled **plan-mandated** — or any finding that contradicts the
  plan's text — is the human's decision in SDD. Do not dismiss the finding because the
  plan mandates it, and do not dispatch a fix that contradicts the plan. Record a blocker
  whose `--found` is the finding beside the plan text that mandates it, and whose options
  are the two courses that actually exist: fix it against the plan, or keep the plan and
  carry the finding.
- A reviewer's "⚠️ cannot verify from diff" item is the opposite case: SDD requires the
  **controller** to resolve it, and you hold the plan and the cross-task context the
  reviewer lacks. Resolve it. If you genuinely cannot, block. An empty answer is never a
  decision.

**Never guess.** Do not skip a task because it looks hard; do not mark a task `DONE`
without the task review, on an implementer's word alone; do not re-dispatch a task with
unchanged input; and do not invent a blocker's options. A situation with no legal move is
a blocker — and a blocker halts the chain, never the drain.

### The halt

The drain ends when the plan's **last `### Task N` heading has been walked** — not
when no `PENDING` task remains: a plan's trailing `(process)` headings carry no
status and would be skipped by that test (S5's own plan ends with two). Then,
**exactly once**, report one batch:

- **per task:** its status, the commits you observed for it, and what its `provable`
  class does and does not claim (above). The trail carries no SHA, so for a task
  drained before a `/clear` the commits may be unrecoverable: say that, and never
  reconstruct them by guessing at `git log`;
- **every `(process)` task:** named as run — it carries no status by design;
- **every blocker:** its `found`, its `options[]`, and its `recommend`;
- **every parked task:** with the blocker that parked it;
- **every `DONE_WITH_CONCERNS` concern:** verbatim;
- **any stale `.superpowers/sdd/progress.md`** found on disk: named once, so the
  operator can delete it;
- **the dispatch root, if it was a worktree:** its path and branch, named explicitly
  — the operator's merge/PR/keep/discard/cleanup call, exactly like any other branch
  ([references/worktree-notes.md](references/worktree-notes.md)).

The final whole-branch review is **REVIEW's**, and EXECUTE dispatches nothing after
the last task. Your job is to leave `<scratch>/review-final.diff` and the `--note`
roll-ups **on disk** for REVIEW/PAR to read — that is where the roll-up is spent,
and that is why it is not a silent discard.

Then run `advance --to REVIEW` (the CLI itself refuses while any task is
non-terminal, so this is safe even after a halt that leaves blockers behind) and
stop. Do not continue into **The REVIEW stage** in this same run, do not open a
gate, and do not ask a question — REVIEW's own dispatch, with its real-token
reviewers, is the next `/supskill run` invocation's job, and the halt report above
is still this stage's deliverable.

**A halt is the target shape, not an error.** A sprint that drains 4 of 6 tasks
and halts with two blockers is a **successful** EXECUTE. Say so in those words.
Do not apologize for it, and do not try once more.

### The blocker rules

The CLI already refuses a blocker with fewer than two options, an unlabelled option, a
duplicate label, or a `--recommend` that names none of them. It cannot refuse three
phrasings of the same option. That part is yours.

- Options are **materially different courses of action** — do X / do Y / stop and
  change the plan — each labelled `(a) …`, `(b) …`, `(c) …`.
- **Never fabricate an option** to satisfy the two-option floor. If there is
  genuinely only one move, there is no decision to escalate, and the task was not
  blocked.
- `--found` is what was **observed**, never what was inferred from it.
- `--recommend` names one option and says why in the same breath.
- The recommendation is **advice, not a decision**. You never act on your own
  recommendation, at any point, for any reason — you halt (D4: escalation is
  out-of-band, always). A wrong recommendation must still leave the operator the
  right option: blinkebot's S9a blocker is on record as exactly that case — the
  recommended option was wrong and option (c) was right.

## The REVIEW stage

Before you dispatch either reviewer, run `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state review-guard`: exit 1 means HEAD has moved past the package EXECUTE recorded, or that EXECUTE never recorded one. Relay the refusal verbatim and stop — do not regenerate the diff yourself. PAR handed a diff that is not this branch comes back *clean*, which is why this refuses rather than repairs (SK-104).

PAR: two adversarial reviewers on the identical `<scratch>/review-final.diff` package, worse severity wins (D9). Each writes its findings to its own `<scratch>/review-findings-<label>.md`, and you read that file — a reviewer's chat reply is a liveness signal, never the findings. Dispatch discipline, the collection rule, the aggregation rule, and the `review` verb's exact flags: [references/review-notes.md](references/review-notes.md). No dispatched reviewer runs `supskill-state`; cost each as it completes, `cost --stage REVIEW --label reviewer-a|reviewer-b` — and add `--estimated` whenever you could not read that dispatch's reported usage, which is every reviewer dispatched as a mailbox teammate. A guessed number filed beside a measured one is the ledger lying quietly (SK-109). Then continue at **Gate 3**.
## Gate 3 — one decision, not two

Ask for real, refuse an empty answer, record verbatim — the same shape as Gate 1 and Gate 2: [references/gate.md](references/gate.md). The question batches every **open** blocker, every parked task, every `DONE_WITH_CONCERNS` note, and every `runs/<id>/review.jsonl` finding at `confidence=high` or `confidence=actionable` — nothing silently dropped. Take open from `show --json`'s `derived.blockers.open`: a blocker whose task reached `DONE` or `DONE_WITH_CONCERNS` is settled and belongs in `derived.blockers.resolved`, which you report as context and never re-ask (SK-103). Where a blocker's `plan_headings` is non-empty, name those headings too — a story the plan spends three headings on, blocked at the first, cancelled two the operator never saw (SK-102). Before you ask the question, run `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state artifact-guard`: exit 0 → continue to the question. Exit 1 means a recorded artifact — the sprint doc or the dev plan — is untracked by git, so the documents that authorize this sprint are not in the branch that implements it: this is `artifact-guard.untracked` ([references/stop-classes.md](references/stop-classes.md) has the exact commands). Check the untracked path(s) against `guard_conductor_commit`'s denylist there; clean → stage and commit exactly those paths, then `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state action --stop artifact-guard.untracked --command "<the exact git line>" --sha <the resulting commit SHA> --operator-answered`, then continue to the question. A foreign path → relay it and stop; that commit is not yours to make, and nothing is recorded.

Once the answer is in, record each blocker's own answer with its own verb **before** you record the gate. For every open blocker the question named, run `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state decide --task <story-id> --option "(x)" --response "<the operator's verbatim words>"`, adding `--batched` when the answer took the recommendations wholesale rather than ruling on that blocker on its own terms. `(x)` is the label the operator chose from that blocker's own recorded `options[]` — the CLI refuses a label it was never offered, and refuses a second decision on a blocker already decided. A blocker the answer did not name gets no `decide` row: an option you inferred is not an option they chose. `decide` records **which option was chosen**, never whether the blocker is settled — that stays the derivation from task status (SK-103), which is why `derived.blockers.*` carries `decision` beside `resolved_by`. Then record the gate:

4. Closes cleanly → `gate --id G3 --decision approved --response "<verbatim>"`. `REVIEW` is the last stage; nothing advances past it.
5. Resolves into Shape 1, 2 or 3 → `gate --id G3 --decision replan --response "<verbatim>"`, then run the shape's own verb: [references/replan-shapes.md](references/replan-shapes.md).
6. Reads as Shape 4 → **no** `gate` call — see **Refusing a north-star supersede**, next.

### Refusing a north-star supersede

No code path here can rewrite `backlog.md`'s North star or repoint `state.json.backlog` (true today by construction; a regression test guards it). Confirm your own classification against [references/replan-shapes.md](references/replan-shapes.md) with `replan-guard --shape <generative-writeback|park-at-boundary|fork-on-live-evidence|north-star-reset>`: on the first three shapes it exits 0 and you continue as that shape's row describes; on `north-star-reset` it exits 1 and prints the refusal verbatim on stderr - relay that text to the operator. A Shape-4 reading gets a report, never a `gate` call, a draft, or an edit - the move is the operator's alone: author the new backlog by hand, then start the next sprint against it. The guard also reads state: on an amending shape it refuses when `state.backlog` is null, because a writeback whose destination was never recorded is a path you inferred, not a path anything authorized (SK-114). Relay that refusal verbatim too.

## Propose the next sprint, then stop

Once a replan shape or the refusal above has resolved the sprint, name the first unchecked epic in the backlog's build order, its points, and why (D6) - that is next sprint's SCOPE stage, not this run's. Then stop: no `advance`, `gate`, `task`, `block`, `cost`, `init`, or subagent dispatch follows the proposal, fork (Shape 3) and refusal alike.

## Reference

- Why this skill is user-invoked only:
  [references/invocation-model.md](references/invocation-model.md)
