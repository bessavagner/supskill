# Sprint 03 — SCOPE + REFINE + Gate 1 (the heart)

**Epic:** E3 · **Points:** 23 committed (was 19 — see [DoR findings](#dor-findings-refined-at-pull-time)) · **Milestone:** the conductor drives its first real stages — a `sprint-plan` subagent writes the sprint doc, a refine subagent grows it against live source with citations a script can audit, and the operator's verbatim Gate 1 decision lands in `gates.jsonl` before PLAN becomes reachable.
**Depends on:** S2 — the conductor skeleton landed in full (commits `b9746cc…b0c6e85`): valid plugin layout, the init-or-resume-or-refuse matrix, the `show --json` read contract, and honest stubs for every stage. This sprint replaces the SCOPE and REFINE stubs with the real thing. · **Unblocks:** E4 (PLAN consumes the G1-approved, spec-shaped sprint doc), E5 (the `provable` classification is drain-then-halt's only principled basis — backlog: *"E5 cannot drain-then-halt without this"*), SK-033 (parses the proof grammar fixed here), and E6 (G2/G3 reuse the gate UX pattern SK-023 establishes).
**Reference:** [backlog-01](backlog.md) — F-1, F-5, invariants 2/3/4 · [design decisions](../../../.ai/reports/2026-07-12-supskill-design-decisions.md) — **D3** (refine-at-pull-time is the heart), **D4** (escalation is out-of-band; `AskUserQuestion` auto-resolves empty in headless), **D9** (the seam/impact taxonomy) · [contexts/04](../../../.ai/reports/contexts/04-composed-skill-contracts.md) — §1 (`sprint-plan`'s contract, the weakest of the eight) and impedance mismatches #1–#2 (the bridge this epic builds) · [contexts/05](../../../.ai/reports/contexts/05-empirical-workflow-blinkebot.md) — pattern 1 (the DoR pass is institutionalized, not an escape hatch) · [contexts/01](../../../.ai/reports/contexts/01-claude-code-context-mechanics.md) — `AskUserQuestion` mechanics.

## Sprint goal (one line)

> `/supskill run s4` in this repo drives SCOPE → REFINE → Gate 1 end to end: the sprint doc appears at a derived path, grows a cited DoR-findings section that `supskill-audit` verifies against the working tree, and `advance --to PLAN` succeeds only after the operator's verbatim approval is on disk.

## Why this sprint

F-1 says the chain does not compose: `sprint-plan` emits stories/points/risks with no output-path contract at all — its entire location instruction is *"Save as markdown"* (its SKILL.md:61) — while `writing-plans` expects a *spec* and assumes `brainstorming` produced it. The bridge that works in practice is the undocumented DoR pass, present in every blinkebot sprint doc and responsible for scope growing every single sprint (10→16, 14→16, 18→23 — contexts/05 pattern 1). This epic makes that bridge a first-class, dispatched, audited stage (**D3**). It is the heart of the product; everything before it was harness.

It is also the sprint where the conductor stops being a skeleton. The stage pattern established here — dispatch a fresh-context subagent from a prompt template, verify its artifact mechanically, record it via `supskill-state artifact`, `advance`, gate — is the pattern E4–E6 copy verbatim. Getting the pattern right once is most of those epics' risk retired.

Two constraints dominate:

1. **Dispatched agents can never ask anyone anything** (invariant 2 / D4). `AskUserQuestion` is stripped from subagents and auto-resolves empty in headless. Every prompt template written this sprint states this fact and gives the agent its full input up front; the only question in the whole flow is Gate 1 itself, asked by the *conductor* in the interactive session.
2. **Invariant 3 grows a third surface.** S1 enforced "the script is the only mutator" in code, S2 in SKILL.md prose. From this sprint on it also holds for **subagent prompt templates**: no template may instruct its agent to run `supskill-state` or touch `.supskill/`. Stage agents produce documents; the conductor alone records them. The reviewer's standing invariant-3 check now covers `skills/supskill/references/*.md`.

One thing this sprint is **not**: PLAN. When G1 approves, the conductor advances and lands on the E4 stub, which honestly reports that PLAN lands with E4 and stops. Resist wiring `writing-plans` "since we're here" — E4 is thin but has its own trap (intercepting the terminal question, SK-031) and its own gate.

## Capacity & sequencing

Working capacity ~**34 pts**; ~18% buffer → ~**28 pts committable** (same model as S1/S2). Committed: **23 pts** — the largest sprint yet, but 8 of it (SK-020's CLI half, SK-022, SK-024) is pure offline Python in S1's mold. **Do not fill the remaining 5 pts**; the prompt-shaped stories carry the real uncertainty here.

- **Critical path:** SK-020 (SCOPE stage — establishes the dispatch pattern and the doc path) → SK-021 (REFINE — the heart, and the story most likely to underdeliver) → SK-023 (Gate 1 — consumes REFINE's output).
- **Wave A (parallel, pure Python, offline):** SK-020's CLI preconditions, SK-022's grammar + parser, SK-024's citation audit. All three are independent of each other and of any prose.
- **Wave B (prose, after wave A):** SK-020's prompt template + SKILL.md row, SK-021 (consumes SK-022's grammar and SK-024's audit in its acceptance), SK-023.

## Stories

### SK-020 — SCOPE stage: dispatch `sprint-plan`, record the doc · 4 · M · **(3 → 4 at pull time)**

- **As** the pipeline's first stage, **I want** the backlog turned into a sprint doc at a path everything downstream can find, **so that** REFINE has something to refine and `artifacts.sprint_doc` is authoritative from the first minute.
- **proof:** seam=app-level · impact=cross-surface · provable=operator *(its two CLI sub-criteria are seam=unit · provable=offline; a mixed story classifies by its least-provable seam)*

- **Context.** `sprint-plan` is the weakest contract of the eight (contexts/04 §1): free-text input, a fixed prose template out, and *"Save as markdown"* as the entire location instruction. supskill supplies the convention (impedance mismatch #1): default path `<backlog-dir>/sprint-<normalized-id>-<slug>.md`, e.g. `sprint-s4-plan-gate2.md`. This deviates slightly from the hand-authored `sprint-01-…`/`sprint-02-…` names beside it — deliberately: zero-padding cannot be derived from ids like `s9a`, and a derivable rule beats a prettier one (invariant 4's lesson). The convention is a *default* in the dispatch prompt; the **authority** is `artifacts.sprint_doc`, recorded via `artifact --set sprint_doc` (which refuses a missing file, `commands.py:178`) and re-verified by the `→ PLAN` precondition (`transitions.py:50-55`). Nothing downstream ever re-derives the path from prose.

- **Accept:**
  - **CLI half (offline, TDD'd, the +1 pt — DoR findings 1–2):** `init` with entry SCOPE (including the default) refuses without `--backlog` — today `backlog` is simply optional (`commands.py:40`, `cli.py:35`) and a SCOPE sprint with `backlog: null` has nothing to scope and no verb to fix it. And `advance --to REFINE` gains a precondition: `artifacts.sprint_doc` recorded and existing — today `failed_preconditions` (`transitions.py:24-40`) has no REFINE branch at all, so a doc-less REFINE dispatch is currently legal. Both directions tested offline; entry=PLAN/EXECUTE sprints are unaffected (preconditions attach to transitions *taken*).
  - `skills/supskill/references/scope-prompt.md`: the dispatch template. Placeholders for backlog path, epic/sprint id, output path, and exemplar docs (`sprint-01-state-spine.md`, `sprint-02-conductor-skeleton.md`, named as the target shape). It instructs the agent to invoke `pm-execution:sprint-plan` against the named epic's rows, reframes "team capacity" as this repo's committable-points model (~34/~28 — `sprint-plan`'s own checklist assumes rosters and PTO), requires story headings to carry backlog ids (`SK-0xx`) so REFINE and later SK-033 can join rows to stories, and states verbatim that the agent cannot ask anyone anything (D4) and must not run `supskill-state` (invariant 3, constraint 2 above).
  - SKILL.md's SCOPE row becomes real: dispatch → confirm the file exists → `artifact --set sprint_doc --path <path>` → `advance --to REFINE` → fall through to the REFINE row. If the subagent returns without producing the file, report its output verbatim and stop — no blocker verb is available before tasks exist (DoR finding 7), and the operator is one gate away regardless.
  - **Resume idempotence:** re-invoked at stage SCOPE with `artifacts.sprint_doc` already recorded and existing → skip the dispatch, advance, continue. A crash between `artifact` and `advance` must not re-spend a SCOPE run.

### SK-021 — REFINE stage: the bridge, against live source · 8 · M

- **As** the stage the whole product exists for, **I want** a fresh-context agent to read the live source, cite `file:line`, surface what the backlog's one-liners could not know, and grow the doc until it is spec-shaped, **so that** `writing-plans` receives what it actually expects (F-1) and Gate 1 has something worth an operator's read.
- **proof:** seam=app-level · impact=journey · provable=operator

- **Context.** The output contract is concrete, not vibes — "spec-shaped enough for `writing-plans`" means (contexts/04 mismatch #2): per-story **Context** paragraphs grounded in `file:line` citations, exact acceptance criteria, named interfaces and paths, a "DoR findings (refined at pull time)" section with numbered findings, and point deltas recorded story-by-story. The S2 doc is the golden exemplar and the prompt names it as such. REFINE edits the sprint doc **in place**: `ARTIFACT_KEYS` has a single `sprint_doc` key (`model.py:63`), deliberately — one doc that gains a DoR section is exactly blinkebot practice (contexts/05 pattern 1), and the recorded artifact path never changes.

- **Accept:**
  - `skills/supskill/references/refine-prompt.md`: inputs are the sprint doc path, the backlog path, and the repo root. Duties: read the live source the stories touch; every claim about *current* behavior carries a backtick-wrapped `file:line` citation; add the DoR-findings section; adjust points with deltas noted inline (`N → M at pull time`); add one proof line per story in SK-022's exact grammar; write the doc back in place. States the D4 fact and the no-`supskill-state` rule like SK-020's template. Its report back to the conductor is a short summary of deltas — the *doc* is the deliverable, not the report (F-5: never trust the report alone).
  - Conductor wiring in the REFINE row: after the agent returns, run `supskill-audit` (SK-024) and the proof-grammar validator (SK-022) against the doc. On failure, re-dispatch **once** with the failure list quoted verbatim; a second failure → report verbatim and stop. No unbounded retry loop.
  - **Resume rule (stated, not clever):** re-invoked at stage REFINE, the conductor re-dispatches REFINE on the doc's current content. Worst case it refines an already-refined doc — acceptable, because G1 still guards the result; detecting "already refined" would mean parsing prose for state, which is the coupling SK-012 refused.
  - Reviewer checks: the template contains no state-mutation instruction; the spec-shaped definition above appears in the template as a concrete field list, not as the word "spec-shaped".

### SK-022 — Proof-seam classification: grammar + validator · 5 · M

- **As** E5's drain-then-halt split and E4's task loader, **I want** every story classified in a machine-findable grammar fixed now, **so that** `provable: offline | operator` is a parseable fact, not prose SK-033 will have to guess at.
- **proof:** seam=unit · impact=cross-surface · provable=offline

- **Context.** Vocabulary is D9's stolen taxonomy. The grammar must be fixed in E3 because SK-033 (E4) loads `tasks[]` from the refined doc — if the format is improvised per-sprint, E4 inherits a parsing guess. The `Task` model already stores `seam` and `provable` as free strings (`model.py:76-80`), so the validator is the only vocabulary owner. One exact line per story, directly under the story's heading:

      - **proof:** seam=unit|integration|app-level|e2e · impact=none|local|cross-surface|journey · provable=offline|operator

- **Accept:**
  - `scripts/supskill_state/proofs.py`: `parse_proof_lines(text)` associates each proof line with the nearest preceding `### SK-xxx` heading; rejects unknown tokens, duplicate lines per story, and stories in the Stories section that lack one. Pure Python, offline tests including a fixture doc. It lands in the package **now** so SK-033 only adds the verb, not the parser.
  - The validator enforces vocabulary only. Whether `seam=e2e · provable=offline` is a *lie* is judgment — the refine reviewer's and the operator's at G1 — and the validator does not pretend otherwise (typical mapping, stated in the module docstring: unit/integration → offline; app-level/e2e → operator).
  - `refine-prompt.md` quotes the grammar verbatim; the reviewer diff-checks the quote against `proofs.py`'s accepted tokens (drift risk is named in the risks table).
  - Dogfood: this sprint doc classifies its own five stories with the grammar (done — see the proof lines above), and the parser's fixture test parses *this file*.

### SK-023 — Gate 1: the operator reads the refined doc · 3 · M

- **As** the operator, **I want** one real question at the moment the refined doc exists, with my verbatim words in the audit trail, **so that** approval is a recorded decision and PLAN is unreachable without it.
- **proof:** seam=app-level · impact=journey · provable=operator

- **Context.** Enforcement already exists: `advance --to PLAN` refuses without `G1 == approved` and a recorded, existing sprint doc (`transitions.py:27-29`) — S1 built that. This story is the gate's UX in the conductor, plus one sharp edge from DoR finding 5: in headless, `AskUserQuestion` auto-resolves in ~37ms with an **empty** answer (contexts/01), and the `gate` verb records empty responses **by design** (F-4's loud-trail rationale, `commands.py:197`). So the refusal to treat silence as consent must live in the conductor.

- **Accept:**
  - SKILL.md's REFINE-row tail: after both audits pass, ask via real `AskUserQuestion` — approve / reject, free-text welcome. The verbatim response (selected label plus any free text) goes to `gate --id G1 --decision <d> --response "<verbatim>"`.
  - **An empty or auto-resolved answer is not a decision.** The conductor does not call `gate`, reports that Gate 1 requires an interactive operator, and stops. The demo asserts the recorded `gates.jsonl` line carries non-empty verbatim words.
  - `approved` → `advance --to PLAN` → the PLAN row (still E4's honest stub) reports and stops. `rejected` → recorded, reported, stop; the rework loop is documented: the operator edits the doc or asks for a fresh REFINE pass, then re-gates — last decision wins in state while every attempt stays in the trail (`commands.py:201`).

### SK-024 — Citation audit: the mechanical floor under REFINE · 3 · M · **(new at pull time)**

- **As** the check F-5 says a reviewer alone cannot be, **I want** every `file:line` citation in the doc verified to resolve against the working tree, **so that** a hallucinated or stale refinement fails a script before it can impress an operator.
- **proof:** seam=unit · impact=local · provable=offline

- **Accept:**
  - `scripts/supskill-audit <doc>`: extracts backtick-wrapped `path:line` and `path:start-end` tokens, checks the file exists under the cwd and has at least that many lines; prints every unresolved citation with the reason; exit 1 on any. Same self-bootstrapping shim pattern as `scripts/supskill-state` (its `sys.path` insert at line 7); logic in `scripts/supskill_state/citations.py`, tested offline with good/bad fixture docs.
  - **Honesty stated in `--help` and here:** the audit proves citations *resolve*, not that the claims they support are true. Truth stays with the reviewer and the operator; the script only removes the cheapest way to fake depth (F-4's shape: loud and auditable, not impossible).
  - Conductor wiring is SK-021's re-dispatch-once loop; this story is just the tool and its tests.

## DoR findings (refined at pull time)

Third sprint refined against live source. Sprint goes **19 → 23 pts** (SK-020 3 → 4, SK-024 new at 3).

1. **`advance --to REFINE` is unguarded** (grew SK-020). `failed_preconditions` (`transitions.py:24-40`) branches on PLAN, EXECUTE, and REVIEW only — nothing stops a REFINE dispatch with no sprint doc recorded. The story that makes SCOPE real also adds the precondition that makes skipping SCOPE's artifact loud.

2. **A SCOPE-entry sprint can have no backlog** (grew SK-020). `init` treats `--backlog` as optional (`commands.py:40`, `cli.py:35`) and no verb sets it afterward — so a defaulted `init s4` yields a SCOPE stage with `backlog: null`, nothing to scope, and archive-and-reinit as the only exit. Structural fix at init time, matching the project's ethos: refuse SCOPE entry without a backlog.

3. **`sprint-plan` really has no output contract, so the convention is ours — but authority stays in state.** Its entire location instruction is *"Save as markdown"* (SKILL.md:61; contexts/04 mismatch #1). Decision: the derived default `<backlog-dir>/sprint-<normalized-id>-<slug>.md` (derivable for every id, including blinkebot-style `s9a` — unlike the zero-padded hand-authored names) lives in the dispatch prompt as a default, and `artifacts.sprint_doc` — existence-checked at record time (`commands.py:178`) and re-checked at `→ PLAN` (`transitions.py:50-55`) — is the only path anything downstream reads. Prose supplies a convention; state supplies the truth. (Invariant 4's spirit, applied to a doc path where the collision cost is one overwritten file, not a cross-sprint scratch smash.)

4. **F-5 needs a mechanical floor, and the backlog's "consider PAR here too" gets a decision** (new SK-024). "Read the source and find the gaps" is exactly what an agent does shallowly and reports confidently. Rather than doubling REFINE's token cost with PAR now, the floor is structural: a citation audit script that fails unresolvable `file:line` cites before the doc reaches G1, plus the operator's own read *at* G1 — which is a human review of the very artifact PAR would review. **PAR at REFINE is deferred, with a named revisit trigger:** if S3's demo shows a shallow refinement passing both the audit and the operator, E6's PAR story extends to REFINE. Recorded so E6 inherits the question with evidence instead of re-arguing it.

5. **Gate 1 has a headless failure mode, and the CLI cannot be the one to catch it.** `AskUserQuestion` auto-resolves empty in ~37ms headless (contexts/01; D4), and `record_gate` accepts an empty `--response` **by design** — F-4 wants fabricated approvals to leave a readable empty quote in the trail (`commands.py:197`). If the conductor piped an auto-resolved answer into `gate`, a headless run would silently self-approve. Resolution in SK-023: an empty answer is not a decision — no `gate` call, report, stop. The CLI stays permissive (the trail is the point); the conductor owns the refusal.

6. **SK-022's grammar must be fixed now because E4 parses it.** SK-033 loads `tasks[]` from the refined doc; `Task` stores `seam`/`provable` as free strings (`model.py:76-80`), so nothing downstream re-validates vocabulary. The parser (`proofs.py`) lands in the package this sprint with the grammar; SK-033 adds only the verb. SK-033's points are unchanged — this is scope clarity, not scope transfer.

7. **E3's stages cannot raise blocker records — and must not fake them.** `record_blocker` requires the task to exist in `state.tasks` (`commands.py:242-244`), and `tasks[]` is empty until SK-033 (E4). So SCOPE/REFINE failures escalate by report-verbatim-and-stop, not by blocker record. Acceptable: the operator is one gate away throughout this epic. Named here so nobody "fixes" it by inventing placeholder tasks.

8. **Stage agents are prompt templates in `references/`, not plugin `agents/` definitions.** The SCOPE agent must *invoke a skill* (`pm-execution:sprint-plan`), which a general-purpose subagent dispatch keeps simple; SDD's own `implementer-prompt.md` is the precedent for template-shaped dispatch. `agents/` (empty, reserved at SK-010) stays reserved — if E6's PAR reviewers want tool-restricted agent definitions, that is the epic to spend the mechanism on. Invariant 3 for subagents is enforced the same way everything prompt-shaped is here: stated in the template, checked by the reviewer, verified mechanically where possible (the conductor, not the agent, runs every `supskill-state` call).

**Deliberately NOT in scope**, though tempting: the PLAN stage and `writing-plans` interception (E4 — including its terminal-question trap, SK-031), the tasks-loading verb (SK-033, E4), PAR at REFINE (deferred with a trigger, finding 4), any "auto-approve" or `--yes` affordance at G1 (silence is not consent — finding 5 is the whole point), and relaxing `disable-model-invocation` (E7's decision, with evals).

**Gate 1 data point #3** (open question §7.2): refinement against live source grew scope +4 pts, and the sharpest finding was again structural — a headless run would have silently self-approved its own gate (finding 5), which no backlog one-liner mentioned. Three sprints, three data points, same direction.

## Skills for executors

Standing skills apply (author↔review separation, verify-before-claim, no self-approval, TDD, `karpathy-guidelines`, no AI attribution in commits). Domain additions:

- **SK-020 (CLI half) / SK-022 / SK-024** — `fullstack-dev-skills:python-pro` + `superpowers:test-driven-development`; the suite stays pure offline — no LLM, no subagent, no network.
- **SK-020 (prose) / SK-021** — `superpowers:writing-skills` for the templates; degrees-of-freedom framing (exact CLI invocations and the proof grammar = low freedom; "what counts as a gap worth surfacing" = judgment, and the template says so rather than pretending to specify it).
- **SK-023** — contexts/01 is the local authority on `AskUserQuestion` mechanics; do not re-derive its behavior from memory.
- **Review pass** — `oh-my-claudecode:code-reviewer` → `oh-my-claudecode:verifier`. The standing invariant-3 prose check extends to `skills/supskill/references/*.md`: no template may instruct an agent to run `supskill-state` or edit `.supskill/`. This check repeats every sprint from now on.

## Risks & mitigations

| Risk | Owner | Trigger / signal | Mitigation |
|------|-------|------------------|------------|
| **REFINE is shallow and confident** (F-5, the backlog's own named risk) | executor (021) | DoR section restates the backlog; citations cluster on READMEs and docstrings | `supskill-audit` is the mechanical floor; the operator reads the doc *at G1*; PAR deferral carries a named revisit trigger (finding 4) |
| **A headless or drifting run self-approves G1** | executor (023) | a `gates.jsonl` line with an empty `response` | Empty answer → no `gate` call, stop (SK-023); the CLI keeps recording empties so any bypass stays loud in the trail (F-4) |
| **`sprint-plan` emits team-shaped boilerplate** (rosters, PTO, standups) | executor (020) | capacity section talks about team members | scope-prompt reframes capacity as the repo's committable model and names the S1/S2 exemplars; REFINE exists to fix the residue; a weak SCOPE doc is REFINE's input, not the product |
| **Grammar drift** between `refine-prompt.md`'s quoted grammar and `proofs.py` | executor (022) | prompt and parser accept different tokens | the parser is the single authority; tokens pinned by test; reviewer diff-checks the quote |
| **SKILL.md outgrows its 500-line cap** (SK-011's own acceptance) | executor (021/023) | line count | stage detail lives one reference-hop deep in `references/*.md`; the frontmatter lint already in the suite keeps failing loudly if the body balloons |
| **The dogfood demo disappoints** — the S4 doc is rejected at G1 | operator | G1: rejected in `gates.jsonl` | a rejection is the gate *working*, and either verdict is the F-5 data the PAR deferral needs; record it as data point material, not demo failure |

## Exit criteria

- [ ] **SK-020:** `init` (entry SCOPE) refuses without `--backlog`; `advance --to REFINE` refuses without a recorded, existing `sprint_doc` — both TDD'd offline; `scope-prompt.md` exists with the D4 and invariant-3 statements; the SCOPE row dispatches, records, advances, and resumes idempotently.
- [ ] **SK-021:** `refine-prompt.md` exists with the concrete spec-shaped field list and the grammar quote; the conductor's audit → re-dispatch-once → stop loop is in the REFINE row; reviewer confirms no template mutates state.
- [ ] **SK-022:** `proofs.py` parses this very sprint doc's five proof lines in its fixture test; unknown tokens, duplicates, and missing lines all rejected offline.
- [ ] **SK-024:** `supskill-audit` resolves every citation in this doc and fails a fixture doc with a fabricated cite; its help text states the resolve-not-truth limit.
- [ ] Full suite still pure offline and fast; every Python story TDD'd with failing-test-first evidence in the sprint scratch.
- [ ] **The sprint demo (the heart in anger, operator-run, real tokens):** in this repo — `/supskill run s4 --backlog docs/plans/sprints/backlog-01/backlog.md --slug plan-gate2` → SCOPE writes `sprint-s4-plan-gate2.md` beside this file and records it → **`/clear`** mid-sprint → re-invoke lands on REFINE (invariant 5, now with real stages) → REFINE grows the doc, `supskill-audit` and the grammar validator pass → Gate 1 asks for real → the operator's verbatim words land in `gates.jsonl` → approved advances to PLAN's honest E4 stub and stops; rejected stops with the rework loop named. Either verdict on the S4 doc's quality is recorded as the F-5 / PAR-deferral data point.

> **Honest scope note:** the offline-provable core is real but small — two preconditions, a parser, an audit script. The product of this sprint is prompt-shaped: two templates and a gate flow the suite cannot execute. Those are proven only by the operator-run demo, and the demo is doubly load-bearing here because its output is a *real* sprint doc for S4 — the refinement quality question (F-5) gets its first honest answer from an artifact the operator was going to need anyway. Claiming E3 done on green tests alone would be exactly the self-certification this product exists to prevent.

## Backlog deltas — proposed (not yet applied)

To be applied to [backlog.md](backlog.md) once the operator accepts this doc:

1. **SK-020 re-pointed 3 → 4:** grows the two structural preconditions — `init` refuses SCOPE entry without `--backlog`; `advance --to REFINE` requires a recorded, existing `sprint_doc` (`transitions.py` today has no REFINE branch).
2. **New story SK-024 (3 pts, E3): citation audit.** `scripts/supskill-audit` verifies every backtick-wrapped `file:line` citation in a sprint doc resolves against the working tree; the conductor runs it before Gate 1. The mechanical floor under F-5; PAR at REFINE deferred with a named revisit trigger (S3 demo evidence).
3. **SK-022 note:** the proof-line grammar and its parser (`proofs.py`) land in E3; SK-033 (E4) only adds the state-loading verb. SK-033's points unchanged.
4. **E3 total 19 → 23; Summary table and 120-pt grand total → 124.**
5. **Gate 1 data point #3 recorded (open question §7.2):** live-source refinement grew scope +4 pts and found that a headless conductor would silently self-approve its own gate (`AskUserQuestion` empty auto-resolve × `gate`'s by-design acceptance of empty responses). Three sprints, three data points, same direction.
