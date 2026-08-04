# Design: the operator decides, the conductor acts

## Problem

supskill's stages are autonomous; its *seams* are not. Every point where the run
touches the operator today hands back a command to type by hand:

- the id-mismatch refusal (`skills/supskill/SKILL.md`, run checklist step 3) prints
  `init <id> --archive …` and stops, because the Conventions block says in as many
  words: **"Never pass `--archive`."**
- `artifact-guard` prints *"Stage and commit the paths above yourself, then re-run
  this stage"*, because "this skill never runs `git add`".
- a blocker's answer has no verb at all. `block` records `options[]` and
  `recommend`; nothing records which option was chosen. SK-103 shipped resolution
  as a *derivation* from `task --status DONE --note`, deliberately.
- the Shape-1 writeback is applied to the backlog and left uncommitted, by design.

None of these need the operator's *hands*. They need the operator's *decision*.
Not one of them requires elevated privilege, domain knowledge the conductor lacks,
or a judgment the conductor has not already made and recommended. They require
typing, which the conductor is fully capable of and prohibited from.

Observed live across ledgerus s8 and s9 (2026-08-01 → 2026-08-04): starting s9
took two invocations because the archive had to be hand-typed between them; the
sprint doc and dev plan sat untracked until `artifact-guard` refused at Gate 3 —
the *end* of the sprint — and needed a hand commit; the s9 writeback is still
uncommitted at the time of writing. The operator's summary: *"I find using
supskill great when Claude is performing the execution… but when it comes to my
action, it's confusing, and I am one of the developers — imagine how it'd be for
a user."*

## The friction is currently doing a job

This is why the fix is not simply "let the conductor run more commands."

**F-4** states the ceiling plainly: the script cannot prove a *human* answered a
gate; it makes skipping loud and auditable, not impossible. Today "type this
command yourself" is a genuine consent signal precisely because typing cannot
auto-resolve. **D4** records that `AskUserQuestion` is stripped from subagents and,
in headless runs, **auto-resolves with an empty answer in ~37ms**.

So the hazard is exact: today an empty answer costs a missing record. Under a
design where the conductor acts on chosen options, an empty answer would cost an
**executed action nobody chose**. Any version of this that does not carry that rule
explicitly silently collapses the gate model in every non-interactive run.

## Decisions taken

Three, settled with the operator before design:

1. **Scope is state verbs plus git — not merge, not push, not model invocation.**
   The conductor may run `.supskill/` verbs and `git add`/`git commit`. It may not
   merge a branch, push a remote, or start a sprint on its own initiative.
   `disable-model-invocation: true` stays; E7's recorded tension
   (`references/invocation-model.md`) stays open rather than being resolved here.
   Everything in scope is therefore local and reversible: a wrong commit is a
   `git reset`, never something published.
2. **Only gates and blockers interrupt.** Everything else executes and is reported.
3. **Batch acceptance is allowed and is marked as such in the trail.**

## Design

### 1. The classification table

Every stop the CLI can produce carries exactly one recorded label.

**Remediable** — the stop names a known, safe, specific action; the conductor takes
it and records it.

| Stop | Action |
|---|---|
| id-mismatch refusal, when the on-disk sprint's G3 **is** recorded | `init <id> --archive` with every operator flag carried forward |
| `artifact-guard` exit 1 | stage and commit the recorded artifacts |
| a Shape-1 writeback **this run just applied** | commit exactly the backlog path it wrote, and nothing else |

**Evidential** — acting on the stop would destroy the signal it exists to raise. It
still refuses and is still relayed verbatim.

| Stop | Why it must not be remediated |
|---|---|
| `review-guard` | SK-104: PAR handed a diff that is not this branch comes back *clean*. The refusal **is** the finding; regenerating the package hides it. |
| `plan-guard` | The plan agent produced commits. That is a misbehaving agent, not a fixable state. |
| `commit-scope-guard` | An agent swept foreign state (`.omc/`, `.supskill/`) into a commit. The commit is tainted. |
| `replan-guard --shape north-star-reset` | Invariant 7: a north-star reset is operator-authored, full stop. |
| `preflight` | A stage that cannot load the skill it dispatches improvises — the exact failure the project exists to prevent. |
| `tasks` coverage refusal | The plan dropped a story. That is a hole in the plan, not a chore. |
| `init --archive` over a sprint at REVIEW with **no** G3 (SK-115) | There is nothing to remediate: a decision has not been made yet. |

The same flag appears in both tables — `--archive` is remediable when a G3 decision
exists to preserve and evidential when it does not. That asymmetry is the
classification doing real work rather than restating a whitelist.

**The table lives in one reference doc, and a test asserts that every guard and
refusal reachable from `cli.py` appears in it exactly once.** Without that test this
decays back into per-run prose judgment, which is SK-108's failure mode — open
across four runs and three contradictory readings.

### 2. `actions.jsonl`

A new per-run trail, `.supskill/runs/<id>/actions.jsonl`, with one append-only
record per conductor-executed action: the kind, the reason, the exact command, the
resulting SHA where there is one, and the outcome. A new `action` verb writes it;
like `cost`, only the conductor calls it.

This is not optional bookkeeping. Decision 2 makes these actions silent, and
**invariant 5** says the conductor is disposable with `.supskill/` as its only
memory. A report delivered in a conversation that `/clear` destroys is not a record.
The trail is what makes "what did it do to my repo?" answerable from disk after the
conversation is gone.

### 3. `decide` — the blocker's inverse

    supskill-state decide --task SK-0xx --option "(a)" --response "<verbatim>" [--batched]

Refuses an `--option` label absent from that blocker's recorded `options[]` (reusing
`_OPTION_LABEL`, `commands.py:411`), an empty `--response`, an unknown task, and a
blocker already decided. `show` derives resolution from the decision rather than
inferring it from task status.

SK-103 deliberately shipped resolution as a derivation with no new verb, reasoning
that `task --status DONE --note` already records how a blocker was settled and *"a
second mover could disagree with it."* That was correct while the answer was free
prose. It stops being correct once the answer is a chosen option: the chosen label
is a recorded fact, not an inference. SK-103's derivation remains as the fallback
for blockers settled the old way.

### 4. `--batched`

On `gate` and on `decide`. Exactly SK-109's shape and exactly its reason: a ledger
that cannot distinguish two provenances is lying quietly. `show` renders it, so a
batch-accepted G3 and an individually-reasoned one are tellable apart.

Batching is offered **only when every item in the batch carries a recommendation.**
A question with no recommended answer cannot be bulk-accepted.

### 5. A run that cannot ask cannot act

`record_gate` accepts an empty `--response` **by design** — `commands.py:402` carries
the comment `empty is accepted and recorded by design (F-4)`, so that a fabricated
approval leaves a readable empty quote in the trail. Enforcing the empty-answer rule
inside `gate` would destroy that mechanism.

So it is enforced one level up: **before its first silent action of a run, the
conductor establishes that an interactive operator exists**, extending the existing
preflight step of the run checklist. A run that cannot raise a gate does not get to
execute actions on the operator's behalf either.

This is the weakest part of the design and is recorded as such. It remains conductor
discipline backed by a precondition check, not a mechanism that makes the failure
impossible — which is F-4's ceiling restated, one level out.

### 6. `commit-scope-guard` covers the conductor

Today it guards an implementer's commits across a task's `BASE`..`HEAD`. Every
conductor-executed commit runs through the same guard, with the same refusal, before
it lands. The actor that gains the most reach under this design must not be the one
the guard exempts.

### 7. Prose

The run checklist's step-3 refusal template, the SCOPE backlog-null refusal, Gate 3's
`artifact-guard` paragraph, and the Conventions line `Never pass --archive` all change
to match. `--archive` becomes: pass it only to close a sprint whose G3 decision is
recorded, and record the action.

## What does not change

- Gates G1/G2/G3 still stop the run and still record the operator's words verbatim.
- The conductor still never acts on its own recommendation; a recommendation stays
  advice (**D4**).
- Invariant 7 holds: no north-star supersede, ever.
- Invariant 3 holds: no dispatched agent runs `supskill-state` or touches `.supskill/`.
  Everything here is the *conductor's* reach, not a subagent's.
- No merge, no push, no branch creation or deletion outside the worktree script.

## Testing

- Every guard and refusal reachable from `cli.py` appears exactly once in the
  classification table. This is the anti-drift test and the most important one here.
- `decide` refuses: an unknown option label, an empty response, an unknown task, and
  a re-decide of an already-decided blocker — writing nothing on any refusal.
- `--batched` round-trips through `show` and `show --json` on both verbs.
- `actions.jsonl` is append-only; a conductor commit that would sweep `.supskill/`
  or `.omc/` is refused by `commit-scope-guard`.
- The seven evidential stops still refuse and still write nothing.

## Sizing

Roughly 21 points: classification table and its test (3), `actions.jsonl` and the
`action` verb (3), `decide` (5), `--batched` (2), conductor-commit guard (3), the
SKILL.md prose changes (3), the interactive precondition (2). Filed as **E10**.
