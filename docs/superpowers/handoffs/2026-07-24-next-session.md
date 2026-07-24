# Handoff — supskill, 2026-07-24

For the next session (a fresh Claude Code on this repo). High-signal state + what to do next.
Supersedes `2026-07-23-next-session.md`.

## Where things stand

- **Branch/remote:** `main` **pushed** to `origin/main`, working tree clean. No open branches.
- **Released: `v0.5.0`** (commit `6f376eb`, tag pushed). Carries SK-111 and SK-112. All three version files agree and 431 tests pass.
- **The local install is 0.4.0** (`gitCommitSha 1f1a6da`, updated 2026-07-23). It needs updating to 0.5.0 before the next dogfood run, or that run exercises code without these fixes. **The release ritual and the plugin-update procedure now live in [`docs/runbook.md`](../../runbook.md)** — they were re-typed into the last two handoffs; don't re-type them into the next one.

## Done this session

- **SK-111 + SK-112** implemented from `plans/2026-07-23-sk111-sk112-worktree-state-and-reviewer-handoff.md` and merged (`82be4df`). Backlog rows marked ☑ (`a7c2ff9`). Details are in the two feature commits (`4dccf8f`, `ca7fc64`) and the release commit — not repeated here.
- **Backlog:** SK-114..116 filed from the **ledgerus** runs (`7136e41`) — the first non-playset evidence in E9. Total 42 → 49 pts.
- **`docs/runbook.md` created**, pointed to from the README quickstart. The README's stale `314 passing` was corrected to `431`.

## Three things the plan got wrong (worth knowing before executing the next one)

1. **The idiom count was 10; it was 12.** `commands.py` also repeated it in `record_review_finding` and `advance_stage`. The plan's own grep-to-zero check caught it. Count with `grep -c` before trusting a plan's number.
2. **`test_skill_frontmatter.py` is not frontmatter-only** — it also pins `body <= N lines`, and the SKILL.md body sat at *exactly* the 500 cap, so **any** prose addition to SKILL.md failed a test the plan had declared unaffected. The cap is now 515 (operator decision, recorded in that test's docstring). **The body is at 511: there are 4 lines of headroom.** SK-113 is a one-line prose fix and fits; anything larger needs the cap raised again or moved to `references/`.
3. **The plan said to branch off `main`, and the repo agrees** (SK-100/101/105/106 all used feature branches + `--no-ff`). The prior handoff says this explicitly; it is not optional.

## What to do next

**Nothing is planned.** Pick from open E9 and write a plan. The two rows with the strongest claim:

- **SK-114 (3 pts, M) — the only row blocking a run already in progress.** An `--entry EXECUTE` sprint is legally created with `backlog: null` (`commands.py:60` conditions the `--backlog` requirement on the entry stage), then reaches Gate 3, whose Shape 1 appends to a backlog it does not have. **ledgerus s6 is sitting at REVIEW in exactly that state right now.** The backlog is a REVIEW-stage dependency being guarded at SCOPE.
- **SK-113 (1 pt, C) — cheapest close on the board**, one line of halt prose naming `BLOCKED`/`PARKED` as terminal states that legitimately reach REVIEW. Fits the remaining SKILL.md line budget. Good pairing with a larger row.

Also open: SK-102, SK-103, SK-104, SK-107 (M); SK-108 (S); SK-109, SK-110, SK-115, SK-116 (C). Full rows in `docs/plans/sprints/backlog-01/backlog.md`, epic E9.

## Suggested skills

- `superpowers:brainstorming` **first** if the next move is not already a filed backlog row — before any plan, before plan mode.
- `superpowers:writing-plans` to turn the chosen row into a plan under `docs/superpowers/plans/`.
- `superpowers:subagent-driven-development` to execute it (a fresh subagent per task, review between). `superpowers:executing-plans` is the inline fallback — that is what this session used, and it worked, but it puts every task in one context.
- `superpowers:finishing-a-development-branch` at the end; it presents merge/PR/keep/discard rather than guessing.
- **Do not** invoke the `handoff` skill for the next handoff doc — it writes to the OS temp dir. This repo's handoffs are committed here, in this format.

## Conventions that bit or matter here

- **No AI attribution** in commits/PRs (global rule). **No mypy** (older plans mention it; not installed). Lint `uv run ruff check .` (100 cols); tests `uv run pytest` (offline).
- Guard modules follow one shape: pure check + `refusal()` string + thin `cli.py` verb + dedicated test + one SKILL.md sentence (`plan_guard.py`/`replan_guard.py` are the templates).
- Dispatched subagents' **final chat messages routinely collapse to a placeholder** — hand work over as files and read the file back. SK-112 just did this for EXECUTE's task review; apply it to any dispatch you make.
- `Agent` subagent type names here are `oh-my-claudecode:executor` / `oh-my-claudecode:code-reviewer` (plain `executor` fails).
- Backlog bookkeeping is its own commit (`docs(backlog): …`), separate from the code that closes the row. Filing and marking-done are separate commits too.
- **A backlog row records the finding as filed, not as fixed.** SK-112's row names `review-findings-<N>.md`; what shipped is `task-<N>-review-findings.md`. Don't rewrite rows to match the implementation — note the divergence in the mark-done commit.
