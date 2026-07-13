# Sprint 04 — PLAN + Gate 2

**Epic:** E4 · **Points:** 14 committed (was 10 — see [DoR findings](#dor-findings-refined-at-pull-time)) · **Milestone:** the conductor turns a G1-approved sprint doc into a dev plan `writing-plans` actually produced, refuses to let that plan agent execute anything, records the operator's verbatim Gate 2 decision, and loads `tasks[]` so E5 has something to drain.
**Depends on:** S3 — SCOPE, REFINE and Gate 1 landed in full (commits `f798f45…aa81d4d`): the stage pattern (dispatch a template → verify mechanically → record via `supskill-state` → advance), the proof-line grammar and its parser, the citation audit, and the conductor's refusal to treat silence as consent. This sprint replaces the PLAN stub (`skills/supskill/SKILL.md:93`) with the real thing. · **Unblocks:** E5 — and more than the backlog thought. `tasks[]` is empty until this sprint (`commands.py:77`), and `record_blocker` refuses a task it cannot find (`commands.py:250`), so **E5 cannot block, park, or map a single SDD status until SK-033 lands.** E6's G3 reuses the gate pattern a third time.
**Reference:** [backlog-01](backlog.md) — F-2 (SDD's status vocabulary is adopted verbatim), F-4, invariants 2/3/5 · [design decisions](../../../.ai/reports/2026-07-12-supskill-design-decisions.md) — **D1** (compose, never reinvent — this sprint is the purest test of it), **D4** (escalation is out-of-band), **D5** (the SDD status contract) · [contexts/04](../../../.ai/reports/contexts/04-composed-skill-contracts.md) — `writing-plans`' contract and impedance mismatch #2 · [sprint-03](sprint-03-scope-refine-gate1.md) — the stage pattern and the Gate 1 UX this sprint copies.

## Sprint goal (one line)

> `/supskill run s5` drives PLAN → Gate 2 end to end: a `writing-plans` subagent writes a real dev plan at a path the conductor supplies, the conductor proves the agent planned rather than *executed*, `supskill-audit` checks the plan's citations, the operator's verbatim approval lands in `gates.jsonl`, and `tasks[]` is populated so `advance --to EXECUTE` becomes reachable for the first time.

## Why this sprint

The backlog calls E4 "thin — mostly wiring `writing-plans` and intercepting its terminal question." The wiring is thin. The interception is not, and refinement against the live skill found why.

`writing-plans` does not merely *end by asking* which execution mode to use — it ends by **routing into execution**. Its Execution Handoff (writing-plans SKILL.md:156–175) offers Subagent-Driven or Inline, and each branch names a REQUIRED SUB-SKILL the agent is expected to invoke next. A dispatched subagent cannot ask anyone anything (invariant 2 / D4): in headless the question auto-resolves empty, and an agent holding an empty answer and two "REQUIRED SUB-SKILL" instructions is one plausible step from **executing the entire sprint inside the PLAN stage** — before the operator ever sees the plan, and without `advance --to EXECUTE` ever running its `G2_plan` precondition (`transitions.py:32-34`). The gate would not be *skipped*; it would be *bypassed*, with `state.json` still reading `PLAN` while the branch carried a sprint's worth of commits. That is the exact failure class this product exists to prevent, and SK-031 is where it gets stopped — pre-answered in the template, and caught mechanically by the conductor if the prompt fails to hold.

The second finding is quieter and worse. `advance --to REVIEW` refuses while any task is non-terminal (`transitions.py:36-41`) — but with `tasks[]` empty, that check **passes vacuously**. Today a sprint can reach REVIEW having executed nothing at all, and the strongest precondition in the state spine would raise no objection. SK-033 was scoped as a convenience verb ("nothing populates `tasks[]`"); it is really the load-bearing half of E5's enforcement, and it grows to carry the two preconditions that make an empty task list refuse instead of shrug.

So E4 is thin in code and sharp in consequence. It is also the last stage that composes a *skill* rather than driving one: after this, E5 hands off to SDD and the conductor's job is to survive what comes back.

## Capacity & sequencing

Working capacity ~**34 pts**; ~18% buffer → ~**28 pts committable** (same model as S1–S3). Committed: **14 pts** — deliberately the smallest sprint since S2. Do **not** pull E5 stories forward to "fill" it: E5's drain-then-halt is the hardest story in the backlog and it wants a whole sprint's attention, not a leftover 14 points.

- **Critical path:** SK-033 (tasks + preconditions — pure Python, blocks nothing but unblocks everything) → SK-030 (PLAN dispatch) → SK-031 (the no-execution guard, wraps the dispatch) → SK-032 (Gate 2, consumes the plan).
- **Wave A (parallel, pure offline Python):** SK-033 in full; SK-031's HEAD-guard helper.
- **Wave B (prose, after wave A):** SK-030's template + SKILL.md rows, SK-031's template clauses, SK-032.

SK-033 first is not arbitrary: SK-030's SKILL.md row ends by calling the tasks verb, so writing the prose before the verb exists invites a stub the reviewer has to catch.

## Stories

### SK-030 — PLAN stage: dispatch `writing-plans`, record the dev plan · 4 · M · **(3 → 4 at pull time)**

- **As** the stage that turns an approved spec into executable steps, **I want** `writing-plans` dispatched against the refined sprint doc and its output recorded, **so that** EXECUTE has a plan at an authoritative path and Gate 2 has something to read.
- **proof:** seam=app-level · impact=cross-surface · provable=operator

- **Context.** Unlike `sprint-plan` — which had no output convention at all (S3 DoR finding 3) — `writing-plans` *has* one: `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`, explicitly overridable by user preference (writing-plans SKILL.md:18-19). supskill overrides it, for one reason: the date is not derivable by the conductor without trusting a model to know today's date, and a plan written to the wrong date is a plan the resume path cannot find. The conductor supplies `docs/superpowers/plans/<YYYY-MM-DD>-sprint-<id>-<slug>.md` using the date it reads from the environment, and — as always — `artifacts.dev_plan` is the only authority anything downstream reads. The state spine already supports it: `dev_plan` is a known artifact key (`model.py:63`), the CLI already accepts it (`cli.py:74`), and `record_artifact` refuses a path that does not exist (`commands.py:184-185`). **No CLI work in this story** — the artifact half of E4 was built in S1 and has been waiting.

- **Accept:**
  - `skills/supskill/references/plan-prompt.md`: the dispatch template, same shape as `scope-prompt.md`. Placeholders: `{SPRINT_DOC_PATH}` (the G1-approved doc — the spec), `{OUTPUT_PATH}`, `{REPO_ROOT}`, `{EXEMPLAR_PLAN}` (an existing dev plan under `docs/superpowers/plans/`, or `none`). It instructs the agent to invoke `superpowers:writing-plans` with the sprint doc as the spec, states verbatim that the agent **cannot ask anyone anything** (D4) and **must not run `supskill-state`** or touch `.supskill/` (invariant 3) — both clauses linted by the existing template tests (`tests/test_prompt_templates.py:26`).
  - **Every plan task heading names the story it serves** — `### Task N: <what> (SK-0xx)` — or the literal `(process)` for tasks that serve no backlog story (the demo checklist, the backlog-delta task). This is not cosmetic: it is the join key SK-033 validates and E5's `SK-043` maps SDD statuses through. The hand-authored plans already do this by habit (S2's and S3's plan tasks all carry their story ids); this sprint makes the habit a requirement the template states and a script checks.
  - SKILL.md's PLAN row replaces the E4 stub: dispatch → confirm the file exists at the output path → run `supskill-audit <plan>` (citations only, no `--proofs` — a dev plan carries no proof lines) → `artifact --set dev_plan --path <path>` → load tasks (SK-033) → Gate 2. On a missing file, report the agent's output verbatim and stop.
  - **Resume idempotence** (SCOPE's rule, verbatim): re-invoked at stage PLAN with `artifacts.dev_plan` recorded and existing → skip the dispatch, continue at Gate 2. A crash between `artifact` and the gate must not re-spend a plan run.
  - The citation audit on the plan is a hard failure, not advisory, and the template says why: cite `file:line` only for code that **exists today**; a task that creates a file names the path without a line number (the audit's regex requires `:digits`, so `Create: \`scripts/foo.py\`` never resolves as a citation).

### SK-031 — The interception: `writing-plans` must plan, not execute · 3 · M · **(2 → 3 at pull time)**

- **As** Gate 2, **I want** the plan agent structurally unable to route itself into execution, **so that** a headless run cannot implement an entire sprint before its plan is approved.
- **proof:** seam=app-level · impact=journey · provable=operator

- **Context.** The backlog framed this as "it ends by asking the user; an unattended conductor stalls otherwise. Answer: subagent-driven, always." Refinement against the live skill says the stall is the *benign* failure. Execution Handoff (writing-plans SKILL.md:156-175) does not just ask — it names a REQUIRED SUB-SKILL per branch, and the plan header it mandates (writing-plans SKILL.md:61) repeats the instruction inside the plan document itself. A subagent whose `AskUserQuestion` auto-resolves empty (D4) has a plausible path straight into `subagent-driven-development`, which is explicitly built to run **without pausing between tasks**. The blast radius is a fully-implemented sprint sitting on the branch while `state.json` reads `PLAN` and `G2_plan` reads `null`.

  Two layers, because prose alone is not enforcement (F-4's shape — loud and auditable, not impossible):

- **Accept:**
  - **Layer 1 — pre-answer, in the template.** `plan-prompt.md` states: the execution question is already answered, **subagent-driven, always**; write the plan, save it, report the path, and **stop**. Do not invoke `subagent-driven-development` or `executing-plans`; do not implement, test, or commit anything. Naming the answer up front is exactly how `scope-prompt.md` defuses `sprint-plan`'s roster-and-PTO capacity checklist — same technique, higher stakes. The plan document's own mandated header may keep naming SDD as the execution sub-skill: that instruction is for **the conductor at E5**, and it is correct.
  - **Layer 2 — the HEAD guard, mechanical.** The conductor records `git rev-parse HEAD` **before** the PLAN dispatch and compares **after**. If HEAD moved, the plan agent committed — it executed. The conductor does **not** advance, does **not** call `gate`; it reports both SHAs, names the commits, and stops for the operator. Offline-testable as a pure function (`plan_guard.py`: `head_moved(before, after)` plus the shell-out at the call site), and the refusal text names what it means: *the plan stage produced commits; a plan is a document, and this run is stopped for you to inspect them.*
  - The guard is honest about its ceiling in its own message and here: an agent that edits files **without committing** slips past it, exactly as F-4 predicts. It catches the realistic failure (SDD commits per task, by design) and makes the unrealistic one no quieter than it was. It is not sold as a sandbox.
  - Reviewer check (standing, extended): no template instructs an agent to run `supskill-state`; **and no template instructs an agent to invoke `subagent-driven-development` or `executing-plans`.** Add the second assertion beside the first in `tests/test_prompt_templates.py`.

### SK-032 — Gate 2: the operator reads the plan · 2 · M

- **As** the operator, **I want** one real question once the dev plan exists, with my verbatim words in the trail, **so that** EXECUTE is unreachable without a recorded human decision.
- **proof:** seam=app-level · impact=journey · provable=operator

- **Context.** Enforcement exists already: `advance --to EXECUTE` refuses without `G2_plan == approved` and a recorded, existing `dev_plan` (`transitions.py:32-34`), built at S1. This story is the gate's UX, and it is a **deliberate copy** of Gate 1's section — the empty-answer refusal included. The CLI still records empty responses by design (`commands.py:203`); the refusal to treat silence as consent lives in the conductor and nowhere else (S3 DoR finding 5). If a third repetition of this block starts to itch at E6, that is the signal to extract a shared `references/gate.md` — **not now**: two instances is a coincidence, three is a pattern, and E6 is the epic that will know which parts actually vary.

- **Accept:**
  - SKILL.md's Gate 2 section: ask via real `AskUserQuestion` — approve / reject the dev plan at its recorded path, free text welcome, path named in the question.
  - **An empty or auto-resolved answer is not a decision:** no `gate` call, report that Gate 2 requires an interactive operator, stop.
  - Non-empty → `gate --id G2 --decision <approved|rejected> --response "<verbatim>"`. `approved` → `advance --to EXECUTE` → the EXECUTE row (E5's honest stub) reports and stops. `rejected` → recorded, reported, stop; the rework loop is Gate 1's, verbatim: the operator edits the plan or asks for a fresh PLAN pass, then re-invokes and re-gates. Last decision wins in state; every attempt stays in the trail (`commands.py:206-208`).

### SK-033 — Load `tasks[]`, and make an empty one refuse · 5 · M · **(3 → 5 at pull time)**

- **As** E5's drain-then-halt loop, **I want** `tasks[]` populated from the refined sprint doc and an empty task list treated as an error rather than a vacuous pass, **so that** blockers can attach, statuses can map, and no sprint reaches REVIEW having executed nothing.
- **proof:** seam=unit · impact=cross-surface · provable=offline

- **Context.** Proposed at S2 DoR as plumbing: `init` writes `tasks=[]` (`commands.py:77`), no verb adds tasks, and `record_blocker` refuses a task it cannot find (`commands.py:250`) — so E5 can neither block nor park. True, and incomplete. `advance --to REVIEW` refuses while any task is non-terminal (`transitions.py:36-41`); over an **empty** list that condition is trivially satisfied, so today a sprint can walk EXECUTE → REVIEW with nothing done and the spine's strongest precondition raises nothing. The verb is not a convenience — it is the input that makes the precondition mean anything.

  The parser is already in the package: `parse_proof_lines` (`proofs.py:50`) returns one `ProofLine` per story from the sprint doc. `Task` stores `id`, `seam`, `provable`, `status` (`model.py:76-80`) — `impact` is parsed and dropped, deliberately: nothing downstream branches on it, and the vocabulary owner stays single (`proofs.py`). Tasks are **story-shaped** (`SK-0xx`), not plan-task-shaped, which is why SK-030 requires plan task headings to name their story: that heading is the only join between what SDD reports (Task N) and what state tracks (SK-0xx), and E5's `SK-043` mapping is guesswork without it.

- **Accept:**
  - `supskill-state tasks --from <doc>`: parses the doc's proof lines via `parse_proof_lines` — **never a second parser** — and writes `tasks[]` as `{id, seam, provable, status: PENDING}`, in document order. Refuses a doc with no proof lines. **Idempotent and non-destructive:** re-running with tasks already present and statuses beyond `PENDING` refuses rather than resetting progress (`--force` is not in scope; an operator who wants a reload has `--archive`). Offline, TDD'd, fixture-doc tested — including against **this sprint doc**, which classifies its own four stories.
  - **Coverage validation, at load time.** Given `--plan <dev-plan>` as well, every story in `tasks[]` must be named by at least one `### Task N …` heading in the plan, and every plan task heading must name a known `SK-0xx` or the literal `(process)`. Violations are listed and the load refuses. This is where a plan that silently drops a story gets caught — before the operator approves it at Gate 2, and long before E5 tries to drain a task no plan task implements.
  - **Two preconditions** (`transitions.py`, TDD'd both directions):
    - `advance --to EXECUTE` refuses when `tasks[]` is empty — *a sprint with no tasks has nothing to execute; run `tasks --from <sprint doc>` first.*
    - `advance --to REVIEW` refuses when `tasks[]` is empty — closing the vacuous pass. The existing non-terminal check is unchanged; this adds the case it never covered.
    - An `entry: EXECUTE` sprint never crosses `→ EXECUTE`, so the REVIEW guard is the one that covers it. Both are tested with an entry-EXECUTE fixture, not only a SCOPE-entry one.
  - The conductor calls `tasks --from <sprint doc> --plan <dev plan>` in the PLAN row **after** recording `dev_plan` and **before** Gate 2 — so a plan that fails coverage never reaches the operator.

## DoR findings (refined at pull time)

Fourth sprint refined against live source. Sprint goes **10 → 14 pts** (SK-030 3 → 4, SK-031 2 → 3, SK-033 3 → 5).

1. **`writing-plans` does not stall — it routes into execution** (grew SK-031). Execution Handoff (writing-plans SKILL.md:156-175) names a REQUIRED SUB-SKILL per branch, and `subagent-driven-development` is built to run every task **without pausing** (its "Continuous execution" section). A dispatched agent whose `AskUserQuestion` auto-resolves empty (D4) can therefore implement the whole sprint inside the PLAN stage, leaving `state.json` at `PLAN` and `G2_plan` at `null` while the branch carries the commits — Gate 2 bypassed rather than skipped, `advance --to EXECUTE`'s precondition (`transitions.py:32-34`) never consulted. The backlog's one-liner ("it ends by asking the user; an unattended conductor stalls otherwise") named the benign half of this. Resolution: pre-answer in the template **and** a HEAD-moved guard in the conductor.

2. **`advance --to REVIEW` passes vacuously on an empty `tasks[]`** (grew SK-033). `failed_preconditions` checks that no task is non-terminal (`transitions.py:36-41`); over an empty list, nothing is non-terminal. Combined with `init` always writing `tasks=[]` (`commands.py:77`) and no verb to fill it, a sprint can reach REVIEW having executed nothing while the spine's strongest precondition raises no objection. SK-033 stops being plumbing and becomes enforcement: it adds the empty-list refusals on `→ EXECUTE` and `→ REVIEW`.

3. **Story ids vs plan tasks: the join key was never specified** (grew SK-030 and SK-033). `tasks[]` is story-shaped — `parse_proof_lines` (`proofs.py:50`) keys on `SK-0xx` and `Task` stores `id`/`seam`/`provable` (`model.py:76-80`). SDD reports per **plan task** (`Task N`), and S3's plan had 9 plan tasks for 5 stories. Nothing joins them, so E5's `SK-043` ("map SDD's statuses onto task status") would have had nothing to map through. The hand-authored plans already name story ids in their task headings (S2's and S3's plans, every task); this sprint promotes that habit to a template requirement and a load-time coverage check. Caught here, it costs a validator; caught at E5, it would have been a re-plan.

4. **`writing-plans` has an output convention and we still override it.** It writes to `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`, overridable by user preference (writing-plans SKILL.md:18-19) — a real contract, unlike `sprint-plan`'s "Save as markdown" (S3 DoR finding 3). We still supply the path: the date is not derivable by the conductor without trusting a model's sense of today, and a plan saved to the wrong date is one the resume path cannot find. Same rule as S3: prose supplies the convention, `artifacts.dev_plan` supplies the truth. **No CLI work needed** — `dev_plan` has been a valid artifact key since S1 (`model.py:63`, `cli.py:74`).

5. **The Gate 2 block is a deliberate copy of Gate 1's, and stays one.** Same `AskUserQuestion`, same empty-answer refusal, same rework loop. The temptation to factor out a shared gate reference is real and is **explicitly deferred to E6**, which adds the third instance and will know what actually varies. Recorded so nobody "cleans this up" mid-sprint and so E6 inherits the decision rather than re-arguing it.

6. **The HEAD guard's ceiling, stated before anyone oversells it.** It catches an agent that *commits* — which is precisely what SDD does, per task, by design. An agent that edits the working tree without committing walks past it. That is F-4's ceiling again (loud and auditable, not impossible), and the refusal message says so. Do not let a reviewer accept "the guard makes execution impossible"; it does not, and the story does not claim it.

**Deliberately NOT in scope**, though tempting: dispatching SDD (E5 — SK-040's `OUTFILE` override is its own problem), drain-then-halt (SK-041), the SDD status mapping (SK-043 — it consumes the join key this sprint establishes, and nothing more of it belongs here), a shared gate reference (finding 5, deferred to E6), PAR at PLAN (E6 owns PAR; the plan gets the citation audit and the operator, same floor as REFINE), and any sandbox that would make plan-stage execution truly impossible (finding 6 — a claim this sprint declines to make).

**Gate 1 data point #4** (open question §7.2): refinement against live source grew scope +4 pts, and — for the fourth consecutive sprint — the sharpest finding was structural rather than cosmetic: a headless PLAN stage could have executed the entire sprint before its own approval gate (finding 1), and an empty `tasks[]` made the spine's strongest precondition a no-op (finding 2). Neither is visible from a backlog one-liner. Four sprints, four data points, same direction. The open question — *is Gate 1 always worth stopping for?* — now has enough evidence to answer at E6: **yes, and the reason is not the gate, it is the refinement that precedes it.**

## Skills for executors

Standing skills apply (author↔review separation, verify-before-claim, no self-approval, TDD, `karpathy-guidelines`, no AI attribution in commits). Domain additions:

- **SK-033 / SK-031 (guard helper)** — `fullstack-dev-skills:python-pro` + `superpowers:test-driven-development`; the suite stays pure offline — no LLM, no subagent, no network.
- **SK-030 / SK-031 (prose)** — `superpowers:writing-skills` for `plan-prompt.md`. Read the live `writing-plans` SKILL.md before writing the template; its Execution Handoff is the thing being defused and its exact wording matters.
- **SK-032** — copy S3's Gate 1 section deliberately. If it feels like duplication, it is — and it is the right call this sprint (finding 5).
- **Review pass** — `oh-my-claudecode:code-reviewer` → `oh-my-claudecode:verifier`. The standing invariant-3 prose check over `skills/supskill/references/*.md` now carries a second assertion: **no template may instruct its agent to invoke `subagent-driven-development` or `executing-plans`.**

## Risks & mitigations

| Risk | Owner | Trigger / signal | Mitigation |
|------|-------|------------------|------------|
| **The plan agent executes the sprint** (finding 1 — the sprint's headline risk) | executor (031) | HEAD moved across the PLAN dispatch; commits on the branch while `state.json` reads `PLAN` | Template pre-answers the handoff and forbids the two execution sub-skills; the HEAD guard stops the run and reports the SHAs; the template lint asserts the clause |
| **The guard is oversold as a sandbox** | reviewer | anyone says "execution is impossible now" | Uncommitted edits slip past, stated in the refusal message, the story, and finding 6. F-4's ceiling, not a bug |
| **A plan drops a story silently** | executor (033) | a story in `tasks[]` no plan task names | Load-time coverage validation refuses *before* Gate 2 — the operator never approves a plan with a hole in it |
| **`writing-plans` writes to its own dated path** and the conductor cannot find the file | executor (030) | the output path does not exist after dispatch | The path is supplied in the template as an explicit override (the skill honors user preference); on a miss, report the agent's output verbatim and stop — never guess a path |
| **Plan citations fail the audit on to-be-created files** | executor (030) | `supskill-audit` fails on a `Create:` line | The regex needs `:digits`; the template says cite lines only for code that exists today. If a legitimate failure still appears, it is a template bug, not an audit bug — fix the template |
| **Gate 2 duplication rots** into two divergent gate flows | executor (032) / E6 | G1 and G2 blocks drift in wording | Copy verbatim this sprint; E6's third instance is the named trigger to extract the shared reference (finding 5) |

## Exit criteria

- [ ] **SK-030:** `plan-prompt.md` exists with the D4 and invariant-3 clauses and the story-id heading requirement; the PLAN row dispatches, audits, records `dev_plan`, loads tasks, and resumes idempotently.
- [ ] **SK-031:** the template forbids both execution sub-skills (asserted by the template lint); the HEAD guard is TDD'd offline and stops the run with both SHAs named; its ceiling is stated in its own refusal text.
- [ ] **SK-032:** Gate 2 asks for real, refuses an empty answer without calling `gate`, and records the operator's verbatim words; `advance --to EXECUTE` succeeds only after it.
- [ ] **SK-033:** `tasks --from` loads this very sprint doc's four proof lines in its fixture test; coverage validation refuses a plan that drops a story; `→ EXECUTE` and `→ REVIEW` both refuse an empty `tasks[]`, tested with SCOPE-entry and EXECUTE-entry fixtures.
- [ ] Full suite still pure offline and fast; every Python story TDD'd with failing-test-first evidence in the sprint scratch.
- [ ] **The sprint demo (operator-run, real tokens):** in this repo — `/supskill run s5 --backlog docs/plans/sprints/backlog-01/backlog.md --slug execute-drain` → SCOPE + REFINE + Gate 1 (S3's stages, now load-bearing for a stage they did not build) → PLAN dispatches `writing-plans` against the S5 sprint doc → the plan lands at the supplied path, HEAD has **not** moved, `supskill-audit` passes, `tasks[]` loads with coverage clean → **`/clear`** → re-invoke lands on Gate 2 from disk alone (invariant 5) → the operator's verbatim words land in `gates.jsonl` → approved advances to EXECUTE's honest E5 stub and stops. The artifact is a real dev plan for S5, which the operator needed anyway.

> **Honest scope note:** this sprint's offline-provable core is its largest yet relative to size — the tasks verb, the coverage validator, two preconditions, and the HEAD-guard predicate are all real unit-testable Python (SK-033 + half of SK-031, 6 of 14 pts). What remains unprovable offline is the same thing that always remains: whether a dispatched agent *obeys* a template. The HEAD guard is the first mechanism in this product that catches a disobedient agent rather than trusting a prompt — and it catches exactly one failure mode. Claiming E4 done because the suite is green would mean claiming the plan agent stayed in its lane, which only the demo can show.

## Backlog deltas — proposed (not yet applied)

To be applied to [backlog.md](backlog.md) once the operator accepts this doc:

1. **SK-030 re-pointed 3 → 4:** grows the plan-path override, the plan-doc citation audit before Gate 2, resume idempotence, and the story-id heading requirement that gives E5 its join key.
2. **SK-031 re-pointed 2 → 3, and its description corrected.** `writing-plans` does not merely end by asking — its Execution Handoff routes into a REQUIRED SUB-SKILL, so a headless plan agent can execute the whole sprint before Gate 2, bypassing `advance --to EXECUTE`'s `G2_plan` precondition entirely. Resolution: pre-answer subagent-driven in the template **and** a HEAD-moved guard in the conductor (which catches a committing agent, not an editing one — F-4's ceiling, stated).
3. **SK-033 re-pointed 3 → 5, and re-classified from plumbing to enforcement.** `advance --to REVIEW` passes vacuously over an empty `tasks[]` (`transitions.py:36-41`), so the verb also adds empty-list refusals on `→ EXECUTE` and `→ REVIEW`, plus load-time coverage validation joining plan tasks to story ids.
4. **SK-043 note (E5, points unchanged):** the SDD-status mapping joins through the `SK-0xx` id in each plan task's heading, established by SK-030 and validated by SK-033. E5 adds no parser and invents no second id scheme.
5. **E4 total 10 → 14; Summary table and 124-pt grand total → 128.**
6. **Gate 1 data point #4 recorded (open question §7.2):** live-source refinement grew scope +4 pts and found two structural defects invisible from the backlog — a PLAN stage that could execute the sprint it was planning, and an empty task list that made the spine's strongest precondition a no-op. Four sprints, four data points, same direction; §7.2 can be closed at E6 with the answer *the gate earns its keep because the refinement does*.
