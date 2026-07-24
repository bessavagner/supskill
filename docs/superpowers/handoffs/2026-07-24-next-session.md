# Handoff — supskill, 2026-07-24

For the next session (a fresh Claude Code on this repo). High-signal state + what to do next.
Supersedes `2026-07-23-next-session.md`.

## Where things stand

- **Branch/remote:** `main` **pushed** to `origin/main`, working tree clean. No open branches.
- **Released: `v0.5.0`** (commit `6f376eb`, tag pushed). Carries SK-111 and SK-112. All three version files agree; `uv run pytest` → **431 passed in 1.74s** (re-verified 2026-07-24).
- **The local install is now `0.5.0`** — `~/.claude/plugins/cache/supskill/supskill/0.5.0/` exists. The previous handoff's "needs updating" item is **closed**. The release ritual and the plugin-update procedure live in [`docs/runbook.md`](../../runbook.md); don't re-type them into the next handoff.
- **A dogfood run is live right now.** `~/Documents/projetos/ledgerus` is at **sprint s7, stage PLAN**, G1 approved, `backlog: docs/sprints/backlog-01/backlog.md`. It began on 0.4.0 (the s7-refusal transcript shows the `0.4.0/scripts/supskill-state` path) and 0.5.0 has since been installed, so **s7 may straddle two versions** — worth knowing if it produces a finding that looks like a regression.

## Done this session

- **SK-111 + SK-112** implemented from `plans/2026-07-23-sk111-sk112-worktree-state-and-reviewer-handoff.md` and merged (`82be4df`). Rows marked ☑ (`a7c2ff9`). Details in the feature commits (`4dccf8f`, `ca7fc64`).
- **Backlog:** SK-114..116 filed from the **ledgerus** runs (`7136e41`) — first non-playset evidence in E9. E9 total 42 → 49 pts; header, doc total, and row sum all verified consistent at **49**.
- **`docs/runbook.md` created**, pointed to from the README quickstart. README's stale `314 passing` corrected to `431`.
- **E9 corrected from the ledgerus evidence:** SK-114 re-filed against what was observed (see below), SK-117 filed, SK-108 amended with its third instance, and the stale `35 points` intro prose fixed. E9 49 → **51 pts**; header, doc total, intro prose and row sum all verified equal.

## Three things the plan got wrong (worth knowing before executing the next one)

1. **The idiom count was 10; it was 12.** `commands.py` also repeated it in `record_review_finding` and `advance_stage`. The plan's own grep-to-zero check caught it. Count with `grep -c` before trusting a plan's number.
2. **`test_skill_frontmatter.py` is not frontmatter-only** — it also pins `body <= N lines`, and the SKILL.md body sat at *exactly* the 500 cap, so **any** prose addition failed a test the plan declared unaffected. Cap is now 515 (operator decision, recorded in that test's docstring). **Body is at 511 — 4 lines of headroom** (re-verified: file 517 lines, 6 of frontmatter). SK-113 is a one-line fix and fits; anything larger needs the cap raised again or moved to `references/`.
3. **The plan said to branch off `main`, and the repo agrees** (SK-100/101/105/106 all used feature branches + `--no-ff`). Not optional.

## SK-114 was filed wrong and has been re-filed — don't re-derive this

**The original row was falsified by the run it was drawn from**, and the corrected row is now in the backlog. Recorded here so the next session doesn't re-investigate it.

The original claimed a Gate 3 Shape 1 writeback is "unreachable" when `state.backlog` is null. ledgerus s6 reached it: the writeback **completed** — 63 insertions, 0 deletions, one hunk — because the conductor inferred the target from `artifacts.sprint_doc`'s parent directory. Nothing was blocked, and the null has since self-corrected (s7's init carried `--backlog`).

The real defect is narrower and more interesting: **`replan-guard` takes `--shape` and nothing else** (`cli.py:224-242`) — it reads no state at all, so it is structurally incapable of checking that an amending shape has a target. It returned exit 0 on a writeback with no authorized destination. The re-filed row asks for two things: give `replan-guard` the state and refuse the three amending shapes when `state.backlog` is null; and stop the step-3 refusal template (`SKILL.md:74-79`) dropping the operator's `--backlog`/`--branch`/`--slug` from the command it tells them to run (SK-118, folded in — same root cause, the target is deduced rather than authorized).

## The through-line — read this before grouping E9 into sprints

E9 is not fifteen unrelated defects. **Six are the same failure: a guard validates the *shape* of a thing and never its *preconditions*, and an agent's judgment quietly patched the hole.**

| Row | The mechanism passed | Judgment caught it |
|---|---|---|
| SK-101 | `supskill-audit --proofs` passed vacuously on a prefix mismatch | the REFINE agent noticed |
| SK-104 | nothing checked `review-final.diff` was current | conductor regenerated it |
| SK-112 | reviewer returned `Done.` / `.` as its findings | conductor resumed the agent |
| SK-113 | `advance --to REVIEW` succeeded with an open blocker | conductor rationalized, correctly |
| SK-114 | `replan-guard` exit 0 with `backlog: null` | conductor inferred the target |
| SK-118 | refusal template dropped the operator's `--backlog` | conductor re-added it |

That is a thesis violation, not a bug list — supskill exists to *remove the situation in which guessing is the only move left*, and in six recorded cases the run survived because an agent guessed well. Worth saying in E9's own prose, and it is what makes the sprint groupings below coherent rather than arbitrary.

## Also filed this session (no action needed, context only)

- **SK-117 (2, M)** — the sprint doc and dev plan are **never staged**. playset flagged it at s1 *and* s2 ("the plan a branch implements is not in the branch"); ledgerus needed a hand commit (`a3433df` there). Three occurrences, two projects. The row specifies **report, don't stage**: supskill never runs git for the operator (it will not create, switch or delete a branch), so an auto-`git add` breaks that posture — a Gate 3 check naming any recorded artifact untracked by git fits the guard-module shape instead.
- **SK-118** — the refusal-template flag drop, **folded into SK-114** rather than filed separately; same root cause.
- **SK-108 amended** with its third instance: ledgerus s6's writeback was strictly append-only (63 insertions, 0 deletions, single hunk) *and* the conductor declined to tick two boxes an earlier sprint had closed, documenting the restraint instead of acting. Three runs, three readings — s1 (0 deletions, stale total), s2 (3 deletions, total corrected), s6 (0 deletions, restraint recorded). **This row is now decidable rather than carryable** — s6 is the cleanest instance and argues for strict append-only with the roll-up total as a named exception.

## What to do next

**Nothing is planned.** E9 stands at 51 pts — 24 closed, **27 open across 12 rows**. Suggested sequencing, grouped by seam (the four groups sum to exactly 27):

1. **Sprint boundaries — SK-114, SK-115, SK-116, SK-117 (9 pts).** All four are ledgerus-sourced and share one seam: `init` and the guards decide what a sprint may touch, and none of them check. Lands in `commands.py` + one guard module, following the established shape. SK-115's open design call: refuse `--archive` when the outgoing sprint rests at REVIEW with `G3_review: null` (no schema change — recommended) vs. adding an `abandoned` gate decision (`gate --decision` currently allows three values).
2. **What Gate 3 reads and can't trust — SK-102, SK-103, SK-104, SK-109 (11 pts).** Cancelled headings vanish, settled blockers read as live, the diff may be stale, costs mix measured with estimated. Individually minor; together the highest-stakes screen in the product is assembled from partly-untrustworthy inputs. Sequence 103 → 102 (shared terminal-status semantics) before 104 and 109.
3. **SK-107 (3 pts)** — riskiest row on the board; it changes the PLAN template's contract so a novel test harness must be *proven runnable*, not described. Two instances (playset s1, s5). Give it a critic pass over the written plan before execution.
4. **Sweep — SK-110, SK-113, SK-108 (4 pts).** SK-113 is the cheapest close on the board and fits the remaining SKILL.md line budget; good pairing with any larger row.

**Open rows and their real priorities** (the previous handoff mis-sorted SK-115): SK-102, SK-103, SK-104, SK-107, SK-114, **SK-115**, SK-117 — M. SK-108 — S. SK-109, SK-110, SK-113, SK-116 — C. Full rows in `docs/plans/sprints/backlog-01/backlog.md`, epic E9.

## Suggested skills

- `superpowers:brainstorming` **first** if the next move is not already a filed backlog row — before any plan, before plan mode.
- `superpowers:writing-plans` to turn the chosen row into a plan under `docs/superpowers/plans/`.
- `superpowers:subagent-driven-development` to execute it (a fresh subagent per task, review between). `superpowers:executing-plans` is the inline fallback — it worked last session, but it puts every task in one context.
- `superpowers:finishing-a-development-branch` at the end; it presents merge/PR/keep/discard rather than guessing.
- **Do not** invoke the `handoff` skill for the next handoff doc — it writes to the OS temp dir. This repo's handoffs are committed here, in this format.

## Conventions that bit or matter here

- **No AI attribution** in commits/PRs (global rule). **No mypy** (older plans mention it; not installed). Lint `uv run ruff check .` (100 cols); tests `uv run pytest` (offline).
- Guard modules follow one shape: pure check + `refusal()` string + thin `cli.py` verb + dedicated test + one SKILL.md sentence (`plan_guard.py`/`replan_guard.py` are the templates).
- Dispatched subagents' **final chat messages routinely collapse to a placeholder** — hand work over as files and read the file back. SK-112 just did this for EXECUTE's task review; apply it to any dispatch you make.
- `Agent` subagent type names here are `oh-my-claudecode:executor` / `oh-my-claudecode:code-reviewer` (plain `executor` fails).
- Backlog bookkeeping is its own commit (`docs(backlog): …`), separate from the code that closes the row. Filing and marking-done are separate commits too.
- **A backlog row records the finding as filed, not as fixed.** SK-112's row names `review-findings-<N>.md`; what shipped is `task-<N>-review-findings.md`. Don't rewrite rows to match the implementation — note the divergence in the mark-done commit.
- **A row can also be filed *wrong*.** SK-114 is the first case: filed from a predicted failure that the run then contradicted. When a dogfood run disproves a row, re-file it against what was observed — the correction is the finding.
