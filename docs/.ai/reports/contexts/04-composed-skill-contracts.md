---
title: Composed skill contracts — sprint-plan, writing-plans, subagent-driven-development, executing-plans, brainstorming, writing-skills, verification-before-completion, requesting-code-review
date: 2026-07-12
---

## Scope and versions

All `superpowers:*` skills below are read from the **active installed version, 6.1.1**
(confirmed via `~/.claude/plugins/installed_plugins.json` →
`superpowers@claude-plugins-official` → `installPath:
/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1`,
gitCommitSha `a0b9ecce2b25aa7d703138f17650540c2e8b2cde`). Older cached versions
(6.1.0, 6.0.3, 5.1.0) also exist on disk under
`~/.claude/plugins/cache/claude-plugins-official/superpowers/<version>/skills/` but are
not what a live session invokes; ignore them unless we need to diff behavior across
versions later.

`pm-execution:sprint-plan` is read from the active installed version, 2.0.0
(`pm-execution@pm-skills` → `installPath:
/home/bessa/.claude/plugins/cache/pm-skills/pm-execution/2.0.0`).

---

## 1. `pm-execution:sprint-plan`

**File:** `/home/bessa/.claude/plugins/cache/pm-skills/pm-execution/2.0.0/skills/sprint-plan/SKILL.md` (68 lines, no supporting files — fully self-contained)

**Invocation name:** `pm-execution:sprint-plan`

**INPUT contract:**
- Takes `$ARGUMENTS` directly in the prompt — a free-text description of what's being planned. No required structure.
- "If the user provides files (backlogs, velocity data, team rosters, or previous sprint reports), read them first." — optional, unstructured, no fixed paths or naming convention expected.

**OUTPUT contract:**
- A markdown document following a fixed prose template (Sprint Goal / Duration / Team Capacity / Committed Stories / Buffer / Stories list / Risks).
- Literal instruction: **"Think step by step. Save as markdown."** — that is the *entire* output-location instruction. No path, no filename convention, no directory is specified anywhere in the file.
- This is the weakest contract of the eight: it does not say where to write, whether to commit, or what filename pattern to use.

**SCRATCH/state:** None. No working directory, no ledger, no intermediate files.

**BLOCKED behavior:** Not addressed at all. The skill has no concept of ambiguity handling, stopping, or escalation — it's a straight-line "estimate → select → map dependencies → identify risks → summarize" procedure with no gates.

**Subagent dispatch:** None. Single-pass, does not delegate.

**Commits to git:** No.

**Notable:** This is the shallowest of the eight skills — 68 lines, a five-step checklist, no state, no guardrails. It reads more like a prompt template than a discipline-enforcing skill (contrast with `superpowers:brainstorming`, which hard-gates on user approval before proceeding).

---

## 2. `superpowers:writing-plans`

**File:** `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/writing-plans/SKILL.md` (175 lines, self-contained, no supporting files referenced)

**Invocation name:** `superpowers:writing-plans`

**INPUT contract:**
- "Use when you have a spec or requirements for a multi-step task, before touching code." Expects a **spec** already exists (produced by `superpowers:brainstorming`, see §5) — the skill does not itself gather requirements.
- **Scope Check:** "If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans."
- Context note: "If working in an isolated worktree, it should have been created via the `superpowers:using-git-worktrees` skill at execution time."

**OUTPUT contract:**
- **Exact path pattern:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md` — quoted verbatim: *"Save plans to: `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`"*, with the caveat *"(User preferences for plan location override this default)"*.
- Confirmed in this repo: `/home/bessa/Documents/projetos/blinkebot/docs/superpowers/plans/2026-07-12-sprint-09b-public-slug-identity.md` exists and matches this exact convention — direct on-disk evidence this default is what actually gets used in practice, not just documented aspiration.
- **Mandatory document header** (quoted verbatim from the skill):
  ```markdown
  # [Feature Name] Implementation Plan

  > **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

  **Goal:** [One sentence describing what this builds]
  **Architecture:** [2-3 sentences about approach]
  **Tech Stack:** [Key technologies/libraries]

  ## Global Constraints
  [...]
  ---
  ```
  This header is itself a **composition seam**: it hardcodes a reference back to the two possible next skills, and the plan is unusable by an orchestrator that doesn't recognize that reference.
- Per-task structure is fixed: `### Task N: [Component Name]`, with `**Files:**` (Create/Modify/Test with exact paths+line ranges), `**Interfaces:**` (Consumes/Produces — exact signatures), then numbered `- [ ]` checkbox steps each with runnable code and exact verification commands + expected output.
- "No Placeholders" rule bans TBD/TODO/"similar to Task N"/vague steps — every step must be independently transcribable.

**SCRATCH/state:** None during writing. But the skill performs a **Self-Review** pass (spec coverage, placeholder scan, type consistency across tasks) before considering the plan done — this is inline, not a subagent dispatch.

**BLOCKED behavior:** Not explicit — writing-plans assumes the spec is already validated (that gate lives upstream in brainstorming). If spec coverage gaps are found during self-review, "add the task" (self-correct, don't ask).

**Subagent dispatch:** None.

**Commits to git:** Not stated explicitly for the plan file itself (contrast with brainstorming, which explicitly says "commit the design document to git" — writing-plans has no equivalent line). This is a gap: whether the plan file gets committed is left to whichever skill executes next, or to the orchestrator.

**Execution Handoff (critical seam):** After saving, the skill presents the user a **binary choice** and requires an explicit "Which approach?" answer:
1. **Subagent-Driven** (recommended) → `superpowers:subagent-driven-development`
2. **Inline Execution** → `superpowers:executing-plans`

This choice point is a **human-in-the-loop gate baked into the skill itself** — an orchestrator (supskill) that wants to run this unattended must supply this decision itself rather than let the skill prompt for it.

---

## 3. `superpowers:subagent-driven-development` — MOST IMPORTANT

**Files:**
- `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/subagent-driven-development/SKILL.md` (419 lines)
- `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/subagent-driven-development/implementer-prompt.md` (139 lines — the implementer dispatch template)
- `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/subagent-driven-development/task-reviewer-prompt.md` (189 lines — the per-task reviewer dispatch template)
- `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/subagent-driven-development/scripts/review-package` (executable bash, 45 lines)
- `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/subagent-driven-development/scripts/task-brief` (executable bash, 41 lines)
- `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/subagent-driven-development/scripts/sdd-workspace` (executable bash, 23 lines — the shared workspace resolver)

**Invocation name:** `superpowers:subagent-driven-development`

**INPUT contract:**
- Requires an implementation plan on disk in the format `superpowers:writing-plans` produces (task headings `### Task N: ...`, checkbox steps).
- Requires tasks to be "mostly independent" (see the skill's own decision flowchart — if tightly coupled, it says to fall back to manual execution or re-brainstorm, NOT to `executing-plans`).
- Must run "in this session" (not a separate/parallel session — that's `executing-plans`'s niche).
- **Pre-Flight Plan Review**: before dispatching Task 1, the controller scans the whole plan once for internal contradictions or plan-mandated defects, and must present all such findings as **one batched question** to the human before execution starts.

**OUTPUT contract / how it dispatches subagents (the core mechanism):**
- Per task, in order: **implementer subagent → task-reviewer subagent → (if issues) fix subagent → re-review → repeat until clean**, then mark the task complete, then move to next task. After ALL tasks: a **final whole-branch reviewer** (using `requesting-code-review`'s template, dispatched on the most capable model), then hand off to `superpowers:finishing-a-development-branch`.
- **Never dispatches multiple implementer subagents in parallel** — explicitly listed as a Red Flag ("conflicts"). This directly conflicts with any orchestration model that wants to parallelize independent tasks across subagents.
- **Model selection is mandatory and explicit per dispatch** — "An omitted model silently inherits the session's most expensive one." Cheap/mechanical tasks get a fast model; integration/judgment tasks get standard; architecture and the final whole-branch review get the most capable model.
- **Implementer status contract** (exactly 4 values, quoted from `implementer-prompt.md`):
  - `DONE` → controller runs `review-package`, dispatches task reviewer.
  - `DONE_WITH_CONCERNS` → controller reads concerns; addresses correctness/scope concerns before review, notes observational ones and proceeds.
  - `NEEDS_CONTEXT` → controller supplies missing info, re-dispatches same subagent.
  - `BLOCKED` → controller triages: more context (same model) → more capable model → break task smaller → escalate to human. **"Never ignore an escalation or force the same model to retry without changes."**
- **Task reviewer returns two verdicts, both required**: Spec Compliance (✅/❌/⚠️ "Cannot verify from diff") and Task Quality (Approved / Needs fixes), plus Strengths and Issues bucketed Critical/Important/Minor. `⚠️` items must be resolved by the *controller*, not the reviewer — the controller holds cross-task context the reviewer doesn't.

**SCRATCH/state — EXACT paths (this is the collision hazard the team lead flagged):**
- Workspace root, resolved by `scripts/sdd-workspace`: **`<repo-root>/.superpowers/sdd/`** (git-ignored via a self-writing `.gitignore: *` inside that dir — chosen specifically because Claude Code denies agent writes under `.git/`, so this can't live there).
- **Progress ledger:** `<repo-root>/.superpowers/sdd/progress.md` — one line per completed task, e.g. `Task N: complete (commits <base7>..<head7>, review clean)`. At skill start the controller runs `cat "$(git rev-parse --show-toplevel)/.superpowers/sdd/progress.md"` and **must not re-dispatch tasks already listed as complete**; resumes at the first incomplete task. This file is explicitly the recovery mechanism across context-compaction: *"the commits it names exist in git even when your context no longer remembers creating them."*
- **Task briefs:** `scripts/task-brief PLAN_FILE N [OUTFILE]` → default `<repo-root>/.superpowers/sdd/task-<N>-brief.md`. Extracted via an `awk` script that greps for a heading matching `^#+\s+Task\s+N(\D|$)` in the plan file (brace-fence aware) — **this is exactly the filename-collision hazard flagged**: task numbers are the only namespacing, reused verbatim across every plan/sprint run in the same repo. Two different plans both having a "Task 3" will silently overwrite each other's brief unless an explicit `OUTFILE` override is passed.
- **Review packages:** `scripts/review-package BASE HEAD [OUTFILE]` → default `<repo-root>/.superpowers/sdd/review-<base7>..<head7>.diff` — namespaced by the git SHA range, so this one is naturally collision-resistant (a re-review after fixes gets a fresh file since HEAD changes).
- **Reports:** implementer report file is named by convention off the brief (`…/task-N-brief.md` → `…/task-N-report.md`) but this is *not* generated by a script — the controller composes the path manually when writing the dispatch prompt. Same task-number collision risk as briefs.
- **Reuse vs. namespacing summary:** briefs and reports are **reused/overwritten across runs** (task-number keyed only, no run ID, no date, no plan-name in the filename); review packages are **naturally namespaced** by SHA range; the progress ledger is a **single shared file per repo**, not per-plan — if two plans are executed against the same repo without clearing `.superpowers/sdd/`, their progress lines interleave in one file with no plan identifier per line beyond "Task N," which is ambiguous across plans.

**BLOCKED behavior:** Explicit 4-state contract above. Additionally: **"Continuous execution: Do not pause to check in with your human partner between tasks... The only reasons to stop are: BLOCKED status you cannot resolve, ambiguity that genuinely prevents progress, or all tasks complete."** This is a strong autonomy directive — the skill actively discourages "should I continue?" checkpoints, which is favorable for an orchestrator wanting hands-off execution, but means the orchestrator must be the thing that resolves BLOCKED/plan-contradiction escalations, since the skill won't just wait quietly.

**Subagent dispatch:** Yes — this is the skill's entire mechanism. Dispatches (per task) an implementer, a task reviewer, optionally a fix subagent, and at the end one final whole-branch reviewer. **Important for supskill:** since subagents cannot themselves dispatch subagents, `subagent-driven-development` must be run by an agent that has dispatch authority (i.e., not itself invoked as a leaf subagent by another orchestrator layer that also wants to dispatch — it needs to be the dispatching layer, or nothing beneath it in the stack can fan out).

**Commits to git:** Yes, but indirectly — the *implementer subagent* commits its own work as part of its "Your Job" contract (step 4: "Commit your work"), and the controller records the resulting commit SHAs in the progress ledger. The skill's own Red Flag list explicitly forbids starting implementation on main/master without explicit user consent.

---

## 4. `superpowers:executing-plans` — the alternative executor

**File:** `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/executing-plans/SKILL.md` (71 lines, self-contained — much thinner than subagent-driven-development)

**Invocation name:** `superpowers:executing-plans`

**INPUT contract:** Same upstream artifact as subagent-driven-development — a plan file from `writing-plans`. Description: "Use when you have a written implementation plan to execute **in a separate session** with review checkpoints."

**How it actually differs (this is the part flagged as relevant):**
- It does **not** dispatch fresh subagents per task. It is a linear, single-agent, in-session loop: *Load plan → review critically → for each task: mark in_progress, follow steps exactly, run verifications, mark completed → finishing-a-development-branch.*
- "Separate session" in its description does not mean the skill spawns a session itself — it means the *human* is expected to run this skill in a **different conversation/session** than the one that wrote the plan (a manual context-switch), as opposed to subagent-driven-development which stays in the same session and gets its isolation from fresh subagents instead. The skill file itself contains no session-spawning mechanism — this is a workflow convention, not a technical feature.
- Explicitly recommends stepping *up* to subagent-driven-development when subagents are available: *"Superpowers works much better with access to subagents... If subagents are available, use superpowers:subagent-driven-development instead of this skill."* This reads as: `executing-plans` is the **fallback for platforms without subagent support**, not a peer alternative chosen for its own merits.
- Review checkpoints are much coarser: no per-task reviewer subagent, no spec/quality dual verdict, no review-package diffs. The only review discipline is "review plan critically" once at the start (Step 1) and the final `finishing-a-development-branch` handoff — no in-loop review between tasks at all.
- **STOP conditions are broader and vaguer** than subagent-driven-development's 4-state contract: "blocker (missing dependency, test fails, instruction unclear)", "plan has critical gaps", "you don't understand an instruction", "verification fails repeatedly" → all just "ask for clarification rather than guessing." There is no BLOCKED/NEEDS_CONTEXT/DONE_WITH_CONCERNS taxonomy — it's a single undifferentiated "stop and ask" behavior aimed at a human partner, not a controller.

**SCRATCH/state:** None. No `.superpowers/sdd/`-equivalent directory, no ledger, no brief/report file convention. Progress tracking is via the session's own todo list only — **this means executing-plans has no compaction-survival mechanism** the way subagent-driven-development's progress ledger does.

**BLOCKED behavior:** "Don't force through blockers - stop and ask." Same spirit as subagent-driven-development but coarser and explicitly framed around a human partner replying, not a controller triaging.

**Subagent dispatch:** **No** — this is the key structural difference from subagent-driven-development, more fundamental than the "separate session" framing. It's a same-agent linear executor.

**Commits to git:** Not explicit inside the loop itself (the plan's own task steps, per `writing-plans`'s Bite-Sized Task Granularity, include a "Commit" step, so commits happen as part of following the plan's steps exactly — but `executing-plans` itself states no independent commit policy beyond "follow plan steps exactly").

**Integration:** Same required workflow skills as subagent-driven-development (`using-git-worktrees`, `writing-plans`, `finishing-a-development-branch`) minus `requesting-code-review` (no per-task review dispatch to configure).

---

## 5. `superpowers:brainstorming`

**File:** `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/brainstorming/SKILL.md` (159 lines) + `visual-companion.md` referenced but not required (opt-in browser tool, not read here — orthogonal to the orchestration contract)

**Invocation name:** `superpowers:brainstorming`

**INPUT contract:** Free-form — a raw idea/request from the user. No file or structured input required. Explicitly triggered "before any creative work."

**HARD-GATE (quoted verbatim):**
> "Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity."

This is the single most orchestration-relevant line in the whole set: **brainstorming refuses to be non-interactive.** It structurally requires a human-approval round-trip (design proposal → user approval → write spec → user reviews spec file → only then proceeds). An orchestrator that wants to run brainstorming unattended is fighting the skill's explicit design, not working around a gap.

**OUTPUT contract:**
- **Exact path pattern:** `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` — quoted: *"Write the validated design (spec) to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`"*, again with *"(User preferences for spec location override this default)"*.
- **Explicitly commits:** "Commit the design document to git" — this is the one skill in the set with an unambiguous, stated commit obligation for its primary artifact.
- Runs its own inline **Spec Self-Review** (placeholder scan, internal consistency, scope check, ambiguity check) before the human review gate.
- **User Review Gate** (second human checkpoint, distinct from the design-approval gate): after self-review, the skill must literally say *"Spec written and committed to `<path>`. Please review it and let me know if you want to make any changes before we start writing out the implementation plan,"* and wait.

**SCRATCH/state:** None.

**BLOCKED behavior:** N/A in the BLOCKED/escalation sense — the skill's entire structure IS a blocking gate (two rounds of mandatory human approval: design approval, then spec-file approval) rather than something that can be blocked by an external condition.

**Subagent dispatch:** None described in-skill (it's a conversational, single-agent dialogue skill).

**Terminal state:** "The terminal state is invoking writing-plans. Do NOT invoke frontend-design, mcp-builder, or any other implementation skill." This closes the loop back to §2 — brainstorming's only allowed exit is into `writing-plans`.

---

## 6. `superpowers:writing-skills`

**File:** `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/writing-skills/SKILL.md` (690 lines — by far the longest of the eight) — supporting files present in the directory (`anthropic-best-practices.md`, `testing-skills-with-subagents.md`, `persuasion-principles.md`, `graphviz-conventions.dot`, `render-graphs.js`) referenced but not required reading for the contract itself.

**Invocation name:** `superpowers:writing-skills`

**Rules extracted for authoring `supskill` itself:**

1. **Frontmatter is load-bearing and size-capped.** Required fields: `name` (letters/numbers/hyphens only, no parens/special chars) and `description` (third person, max 1024 chars total for the whole frontmatter block, target under 500 chars).
2. **The description field must describe ONLY triggering conditions ("Use when...") and must NEVER summarize the skill's workflow.** The skill cites a concrete regression as justification: a description that said "code review between tasks" caused an agent to do one review instead of the two-stage review the skill's own flowchart specified, because the agent followed the description instead of reading the body. **Direct implication for supskill:** if supskill's own SKILL.md (or any skill it authors) has a description that summarizes its orchestration steps, agents may shortcut past the real procedure.
3. **Iron Law: "NO SKILL WITHOUT A FAILING TEST FIRST."** Applies to new skills AND edits to existing ones. The whole skill is TDD-for-documentation: RED (run a pressure scenario on a subagent *without* the skill, record verbatim rationalizations) → GREEN (write minimal skill addressing those specific failures) → REFACTOR (close loopholes found in re-testing).
4. **"Match the Form to the Failure"** table (this directly informs how supskill should write its own orchestration rules): prohibition + rationalization table only for pressure-driven rule violations; a positive recipe/contract for shape problems (bloated output, buried verdict); a structural required-field for omissions; a conditional keyed to an observable predicate for condition-dependent behavior. Explicitly: prohibitions **backfire** on shape problems — a documented head-to-head test found the prohibition-worded variant produced *more* of the unwanted content than a recipe-worded variant, and trended worse than no guidance at all.
5. **No nuance clauses, no exemption clauses that don't scope** — "don't X unless it matters" reopens negotiation; if part of output must be exempt, restructure the rule so it structurally can't reach that part.
6. **Cross-referencing convention:** use skill name only with explicit markers — `**REQUIRED SUB-SKILL:** Use superpowers:test-driven-development` or `**REQUIRED BACKGROUND:** You MUST understand superpowers:X`. Never `@`-link another skill file (force-loads it into context immediately, burning 200k+ tokens before it's needed) — this is exactly the mechanism `writing-plans`, `subagent-driven-development`, and `executing-plans` all use to reference each other, and it is the pattern supskill should follow when it references the skills it orchestrates.
7. **Token budget targets:** getting-started/frequently-loaded skills <150-200 words; other skills <500 words. (All eight skills documented here vary wildly against this — `sprint-plan` at ~450 words complies, `subagent-driven-development` at 419 lines/~3500+ words does not, presumably because it's deliberately not a frequently-preloaded skill.)
8. **Directory structure convention:** `skills/<skill-name>/SKILL.md` required; separate files only for heavy reference (100+ lines) or reusable tools/scripts — exactly the pattern `subagent-driven-development` follows with its `scripts/` directory and two `*-prompt.md` templates.

**SCRATCH/state:** None for the skill's own operation, but it prescribes that skill authors use pressure-scenario subagent runs during development (not persisted state, a testing methodology).

**BLOCKED behavior:** N/A — this is an authoring guide, not a runtime-execution skill.

**Subagent dispatch:** Describes dispatching subagents *as a testing technique* (pressure-scenario subagents to find rationalizations) but that's authorship methodology, not something `writing-skills` does when invoked as part of a live orchestration chain.

**Commits to git:** The Skill Creation Checklist's Deployment section says "Commit skill to git and push to your fork (if configured)."

---

## 7. `superpowers:verification-before-completion`

**File:** `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/verification-before-completion/SKILL.md` (139 lines, fully self-contained)

**Invocation name:** `superpowers:verification-before-completion`

**INPUT contract:** None — this is a pure discipline/gate skill, not a producer of artifacts from input. It activates on an *intent* ("about to claim work is complete, fixed, or passing") rather than on a file or data input.

**OUTPUT contract:** None — it produces no files. Its "output" is behavioral: a claim of completion must be preceded, in the same message, by having actually run the verification command and read its output. **Iron Law (quoted): "NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE."**

**SCRATCH/state:** None.

**BLOCKED behavior:** Inverted framing — this skill exists to make an agent BLOCK ITSELF from claiming success prematurely. Red flags list ("should", "probably", "seems to", "Great!"/"Perfect!"/"Done!" before verification, trusting agent success reports) are treated as violations requiring the agent to stop and go get evidence, not proceed.

**Subagent dispatch:** No dispatch of its own, but it explicitly governs how dispatch results from other skills must be treated: *"Agent delegation: ✅ Agent reports success → Check VCS diff → Verify changes → Report actual state / ❌ Trust agent report."* This is directly load-bearing for `subagent-driven-development`'s "Do Not Trust the Report" instruction in its task-reviewer-prompt.md (§3) — the same principle, restated as its own standalone skill.

**Commits to git:** No file-producing behavior at all; not applicable.

**Relevance to supskill:** This is a **cross-cutting constraint skill**, not a pipeline stage. It should probably be treated by supskill as an always-on invariant layered across every dispatch/verification point in the chain, rather than a step with its own input/output slot in a linear pipeline.

---

## 8. `superpowers:requesting-code-review`

**Files:**
- `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/requesting-code-review/SKILL.md` (103 lines)
- `/home/bessa/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/requesting-code-review/code-reviewer.md` (172 lines — the actual dispatch template)

**Invocation name:** `superpowers:requesting-code-review`

**INPUT contract:**
- Requires two git SHAs (`BASE_SHA`, `HEAD_SHA`) bounding the diff to review — the skill shows deriving these via `git rev-parse HEAD~1` / `git rev-parse HEAD` or by grepping `git log --oneline` for a marker commit message.
- Template placeholders that must be filled by the caller: `{DESCRIPTION}` (what was built), `{PLAN_OR_REQUIREMENTS}` (what it should do — plan file path, task text, or requirements), `{BASE_SHA}`, `{HEAD_SHA}`.

**OUTPUT contract:** Not a file — a **subagent report returned in the dispatching agent's context**, structured as: Strengths / Issues (Critical, Important, Minor, each with file:line + why + fix) / Recommendations / Assessment (`Ready to merge?` Yes/No/With fixes + 1-2 sentence reasoning).

**SCRATCH/state:** None of its own. Note this is the **generic/standalone** version of code review — it has the caller run `git diff` directly inside the dispatched subagent's prompt rather than pre-materializing a review-package file. This is a smaller-footprint alternative to `subagent-driven-development`'s `scripts/review-package`, which is used as this skill's own final-whole-branch-review template (see §3).

**BLOCKED behavior:** N/A (review is not a blocking-capable step itself) — but it does instruct the calling agent on how to react to review output: "Fix Critical issues immediately. Fix Important issues before proceeding. Note Minor issues for later. Push back if reviewer is wrong (with reasoning)." Red Flags explicitly forbid skipping review because "it's simple," ignoring Critical issues, or arguing with valid feedback without evidence.

**Subagent dispatch:** Yes — dispatches exactly one `general-purpose` subagent per invocation, filled from the `code-reviewer.md` template. Explicitly told to review **read-only**: "Do not mutate the working tree, the index, HEAD, or branch state in any way."

**Commits to git:** No — pure review, no write actions of its own.

**Relationship to subagent-driven-development's review:** `subagent-driven-development` does NOT use this skill's per-task review path (it has its own richer `task-reviewer-prompt.md` with dual spec/quality verdicts and diff-file handoff). It DOES use this skill's `code-reviewer.md` template specifically for the **final whole-branch review** at the end of all tasks. So `requesting-code-review` is simultaneously (a) a standalone skill usable anywhere, and (b) a required sub-component consumed by `subagent-driven-development`.

---

## Composition seams: sprint-plan → writing-plans → subagent-driven-development

| Handoff | What's actually passed | Is it a file, a path convention, or ad hoc? |
|---|---|---|
| **sprint-plan → writing-plans** | Nothing formal. `sprint-plan` produces prose ("Save as markdown") with no fixed path. `writing-plans` expects "a spec or requirements" — normally produced by `superpowers:brainstorming` at `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, NOT by `sprint-plan`. There is no documented handoff between these two skills at all; they were never designed to compose. |
| **writing-plans → subagent-driven-development** | A single markdown file at `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`, whose header text is the literal instruction that names the next skill (`REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development ... or superpowers:executing-plans`). The receiving skill reads this file directly with `scripts/task-brief PLAN_FILE N`, which greps for `^#+\s+Task\s+N` headings — so the handoff is contractually tight IF the plan's task headings exactly match `writing-plans`'s prescribed `### Task N: [Component Name]` format. Any deviation (e.g., a differently-formatted plan handed in by an orchestrator instead of by `writing-plans` itself) silently breaks `task-brief`'s awk parser (exits 3, "task N not found"). |
| **Execution-choice gate between writing-plans and its two executors** | Not a file at all — a **conversational question** ("Subagent-Driven vs Inline Execution — Which approach?") that `writing-plans` asks the human directly at the end of its own run. An orchestrator that wants to drive this pipeline unattended must intercept and answer this choice itself; neither executor skill exposes a flag or file-based way to pre-select itself. |

---

## Impedance mismatches supskill must bridge

1. **`sprint-plan` has no output-location or filename contract at all.** Every other skill in this chain (`writing-plans`, `brainstorming`) has an exact, quoted `docs/superpowers/{plans,specs}/YYYY-MM-DD-<name>.md` convention with an explicit "user preferences override this" escape hatch. `sprint-plan` just says "save as markdown." If supskill wants to chain `sprint-plan` output into `writing-plans` input, **supskill itself must invent and enforce a path convention** for sprint-plan's output — the skill provides nothing to hook into.

2. **`sprint-plan` and `writing-plans`/`brainstorming` are not the same lineage and don't share a spec format.** `sprint-plan` is a `pm-execution` (PM-toolkit marketplace) skill oriented around story-point capacity planning; `writing-plans` expects a **spec** (design doc) as its upstream artifact, which is `brainstorming`'s output, not `sprint-plan`'s. A sprint plan (stories + points + risks) is not a design spec (architecture + components + data flow). **Supskil cannot pipe sprint-plan's output directly into writing-plans and expect writing-plans's Scope Check or Task Right-Sizing logic to behave sensibly** — it needs a translation/synthesis step (e.g., "for each story in the sprint plan, brainstorm+spec it, then plan it") or must accept that `sprint-plan` composes at a coarser granularity (a sprint) than `writing-plans`/`subagent-driven-development` (a single plan's tasks).

3. **The task-numbering collision hazard is real and by design, not a bug.** `subagent-driven-development`'s own scratch files (`task-N-brief.md`, `task-N-report.md`) are namespaced ONLY by task number, inside a single repo-wide `.superpowers/sdd/` directory with no per-plan or per-run subdirectory. This matches the memory `[[sdd-scratch-dir-collides-across-sprints]]` already on file. If supskill orchestrates multiple plans/sprints against the same repo without clearing or namespacing `.superpowers/sdd/` between runs, task briefs and reports from an earlier plan will be silently overwritten or misread by a later plan that happens to reuse the same task numbers (which is nearly guaranteed, since task numbering restarts at 1 for every plan). **Supskil must either (a) wrap each `subagent-driven-development` run in its own worktree/directory, (b) namespace `.superpowers/sdd/` per plan itself via the `OUTFILE` overrides that `task-brief`/`review-package` both accept as an optional third argument, or (c) require the progress ledger and scratch dir to be swept between plan runs.**

4. **Two mandatory human-approval gates are load-bearing inside `brainstorming`, and a third choice-point is load-bearing inside `writing-plans`.** None of these are file-based or flag-based — they're literally "ask the user and wait for their reply" instructions baked into the skill prose (`<HARD-GATE>` in brainstorming; the design-approval loop; the spec-review loop; the Subagent-Driven vs Inline Execution question in writing-plans). An orchestrator running unattended must either (a) inject itself as the "user" answering these prompts with a pre-configured policy (e.g., "always choose Subagent-Driven"), or (b) accept that these skills cannot run fully autonomously as written and will stall waiting for input they were designed to require from a human.

5. **`subagent-driven-development` structurally cannot be nested inside another dispatching layer.** It works by having the *calling agent* dispatch implementer/reviewer/fix subagents directly. Since subagents cannot themselves dispatch subagents, if supskill's own orchestration model is "a top-level orchestrator dispatches a subagent to run subagent-driven-development," that inner subagent will be unable to fan out its own implementer/reviewer subagents. **`subagent-driven-development` must be invoked as (or by) supskill's top-level orchestrating agent itself, not as a leaf task it delegates to a sub-agent.**

6. **`subagent-driven-development` vs `executing-plans` is a false binary for supskill's needs — the two skills differ in dispatch capability, not merely "same session vs. separate session."** The `writing-plans` handoff presents them as a simple choice, but the actual axis that matters for automation is: does the executor have subagent-dispatch tooling available at all? `executing-plans`'s own SKILL.md says outright to prefer `subagent-driven-development` "if subagents are available" — meaning `executing-plans` exists as a **degraded-capability fallback**, not a first-class alternative. Supskil should treat the choice as capability-gated (can this execution context dispatch subagents? yes → subagent-driven-development; no → executing-plans), not as a stylistic preference to surface to the user.

7. **Review depth is inconsistent across the chain and none of it defers to `verification-before-completion` explicitly.** `subagent-driven-development`'s task-reviewer explicitly says "Do not re-run the suite to confirm their report" (trust the implementer's TDD evidence, verify by reading the diff) while `verification-before-completion` says "Trusting agent success reports" is a Red Flag requiring the *controller* to independently verify via VCS diff. These are not actually contradictory (task-reviewer avoids blind trust by reading the diff for evidence, not by re-running tests) but the two skills state their trust models independently rather than cross-referencing each other — an orchestrator author reading only one of the two could conclude the wrong thing about whether reports are ever independently verified. Supskil's documentation should make explicit that `verification-before-completion`'s discipline is satisfied, inside `subagent-driven-development`, by the diff-reading requirement in `task-reviewer-prompt.md`, not by an independent test re-run.

8. **Only `brainstorming` has an unambiguous git-commit obligation for its primary artifact.** `writing-plans` never says whether the plan file gets committed; `sprint-plan` never mentions git at all; `subagent-driven-development`'s commits happen only as a side effect of the implementer subagent's own task-level commit step. **Supskil needs its own explicit commit policy for spec/plan artifacts** rather than assuming skill-level consistency — right now, whether a plan file lands in git before execution starts depends on incidental behavior, not a stated contract.

### Does any skill support being told WHERE to write its output?

Partially, and inconsistently:
- `writing-plans` and `brainstorming` both state their default path AND explicitly say "(User preferences for plan/spec location override this default)" — i.e., they're overridable via instruction in the prompt/session, but there's no structured parameter; you'd override by telling the agent in prose before/during invocation.
- `sprint-plan` has no default path to override — genuinely unconfigurable, silent on the matter.
- `subagent-driven-development`'s scratch-file scripts (`task-brief`, `review-package`) DO accept an explicit `OUTFILE` third argument to override their default `.superpowers/sdd/...` path — this is the one skill in the set with an actual parameterized override mechanism, not just a documented default. This is the tool supskill should lean on for the namespacing fix in mismatch #3 above.
