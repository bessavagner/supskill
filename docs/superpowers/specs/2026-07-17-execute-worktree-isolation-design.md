# Design: auto-isolate EXECUTE into a worktree instead of blocking on branch

## Problem

The EXECUTE stage's branch check (`skills/supskill/SKILL.md`, "Before the first
dispatch — four checks, in this order", check 1) derives the repository's
default branch and refuses to dispatch anything if the current branch IS the
default branch, or if `HEAD` is detached. Today it just stops and reports:

> "EXECUTE writes commits and will not write them to the default branch" —
> naming `git switch -c <branch>` as the operator's move, and explicitly
> refusing to create/switch/delete a branch itself ("the same restraint that
> keeps `--archive` out of your hands").

Observed live: an operator ran `/supskill run B4`, reached EXECUTE with both
gates already approved and 8 tasks loaded, and the run halted purely because
the current branch happened to be `main`. The fix was a one-line manual
`git switch -c` before re-invoking — a real interruption in what is meant to
be a mostly-autonomous conductor, and one the backlog had already anticipated
(`docs/plans/sprints/backlog-01/backlog.md:172`, `SK-092: Git worktree
isolation per sprint`, parked earlier for lack of evidence — this incident is
that evidence).

A second, non-obvious wrinkle: by the time EXECUTE starts, the sprint doc and
dev plan are **uncommitted** files sitting on the current branch — PLAN's
dispatched agent is explicitly instructed never to commit
(`plan-prompt.md`), and nothing else in SCOPE/REFINE/PLAN runs `git commit`
either. A naive `git worktree add` checks out a *commit*, not working-tree
state, so it would silently lose both artifacts unless something carries them
forward.

## Goals

- Eliminate the manual-branch-switch interruption for the one case that
  triggers it today (current branch is default, or detached HEAD).
- Preserve the existing "conductor never creates/switches/deletes a branch
  the operator is sitting on" restraint — a worktree is purely additive (a
  new directory, a new branch, elsewhere) and never touches the operator's
  actual checkout.
- Leave the already-working case (dispatching on a normal feature branch)
  completely unchanged.
- Reuse `superpowers:using-git-worktrees`'s conventions (`.worktrees/`
  location, gitignore verification) rather than inventing new ones.

## Non-goals

- Always running EXECUTE in a worktree, even off a safe feature branch
  (rejected — bigger blast radius than the reported problem needs).
- Committing the sprint doc / dev plan to the operator's current branch as a
  "checkpoint" before branching off it (rejected — the conductor has never
  committed anything on the operator's behalf, and copying the two files
  achieves the same result without introducing a new autonomous commit).
- An opt-out flag — the new behavior strictly improves on today's hard
  block, so there is nothing to opt out of.
- Auto-merging, auto-PR'ing, or auto-cleaning the worktree once EXECUTE
  finishes — that is the operator's call, exactly like every other
  branch-lifecycle decision in this codebase.
- Any `state.json` schema change — the worktree's location is always
  *derived* (never persisted), so no migration story is needed.

## Design

### A. Trigger condition & naming

The existing branch-check ladder — derive the default branch (`origin/HEAD`,
falling back to `init.defaultBranch`, falling back to whichever of
`origin/main`/`origin/master` resolves) — is unchanged. Only the outcome
changes:

- Current branch is *not* the default branch and not detached → proceed
  exactly as today. No worktree, no new script call, dispatch happens in the
  repo root.
- Current branch *is* the default branch, or `HEAD` is detached → compute a
  target branch name (`sprint.branch` from `show --json` if the operator set
  one at `init --branch`, else the normalized sprint id, e.g. `s15`) and
  isolate into a worktree at `.worktrees/<branch-name>` — reusing
  `using-git-worktrees`'s own default location convention rather than a new
  one. Detached HEAD gets the same treatment as being on the default branch:
  committing there risks unreachable, garbage-collectable commits regardless
  of any restraint policy.

### B. The new script — `supskill-state worktree`

A new verb: `supskill-state worktree --branch <name> --artifact <path>
[--artifact <path> ...]`, run from the original repo root (same cwd
convention as every other verb). Behavior:

1. Ensure `.worktrees/` is listed in `.gitignore` — append if missing, write
   the file directly. Never commits it: a local, uncommitted edit is
   sufficient for git to respect it immediately.
2. Check `git worktree list --porcelain` for an existing worktree at
   `.worktrees/<branch>`.
   - Found, directory still exists on disk → reuse it (the resume case).
   - Found, directory missing (manually deleted) → refuse with a
     `StateError` rather than silently recreating over lost state.
   - Not found → create it: attach to the branch if it already exists
     (`git worktree add <path> <branch>` — handles an operator who already
     ran a manual `git switch -c`/`branch` before this landed), or create
     both fresh (`git worktree add <path> -b <branch>`) if it doesn't.
     Branches from current HEAD either way.
3. Copy each `--artifact` path (pulled from `show --json`'s `artifacts.*` —
   the sprint doc, the dev plan) from the original tree into the same
   relative path inside the worktree, creating parent directories as needed.
   Always re-copies, even on reuse, so the two "single authority" documents
   stay fresh across a `/clear`-and-resume.
4. Print one line: `worktree ready at <path> (created|reused)`.

This is the one script in the codebase that needs a real git-repository test
fixture rather than markdown/string parsing.

### C. Re-homing EXECUTE's dispatch machinery

Once the script reports a worktree path, everything EXECUTE does for that run
is rooted there instead of the repo root:

- **Prepare the scratch** (existing check 2) runs SDD's `sdd-workspace`
  inside the worktree — the implementers actually work there.
- **Every SDD dispatch's "Work from:"** line names the worktree path.
- **Every git command the conductor runs for EXECUTE bookkeeping** — the
  `BASE` recorded before each implementer, the final
  `review-package $(git merge-base <default-branch> HEAD) HEAD ...` —
  runs with `-C <worktree-path>` (or an equivalent subshell `cd`), never by
  changing the conductor's own session directory. `<default-branch>` is
  still resolved exactly as before — a ref visible from any worktree sharing
  the same `.git`.
- **`task-brief`** reads the dev plan from the worktree's synced copy, so a
  resume mid-drain reads the same file the running implementers have been
  committing alongside.

**What never moves:** `.supskill/state.json` and all `supskill-state` /
`supskill-audit` invocations stay anchored at the *original* repo root for
the sprint's entire lifecycle. The conductor's own bookkeeping was never the
thing needing isolation — only the code-writing was.

### D. Handoff at the end

EXECUTE's existing halt/handoff to REVIEW gets one addition: when a worktree
was used, the report names its path and branch explicitly, so the operator
can apply the same merge/PR/keep/discard choice (and worktree cleanup) they'd
use for any other branch. The conductor never auto-merges or auto-cleans it.

### E. Error handling & edge cases

- **Worktree creation fails** (sandbox denial, permission error): the script
  raises `StateError`; the conductor reports it verbatim and stops — no
  silent fallback to dispatching on the default branch.
- **Stale worktree registration** (git knows about it, directory is gone):
  `StateError`, surfaced for the operator to decide — never auto-healed.
- **Branch name collision** (a branch exists from an earlier manual attempt,
  no worktree attached): the script attaches to the existing branch instead
  of erroring.
- **Non-blocking case:** already on a safe feature branch → no worktree, no
  new script call, byte-for-byte identical to today.

## Testing plan

- `tests/test_worktree.py` (new): a real temp git repo fixture (`tmp_path` +
  `git init` + at least one commit). Cases: fresh creation (branch doesn't
  exist) → worktree created, artifacts copied, `.gitignore` updated; reuse
  (already registered and healthy) → no duplicate creation, artifacts
  re-copied; existing branch with no worktree → attaches rather than
  erroring; stale registration (directory deleted underneath) →
  `StateError`; `.gitignore` already containing `.worktrees/` → not
  duplicated.
- `SKILL.md`'s EXECUTE section gets prose-fidelity tripwires in the existing
  `test_execute_prose.py` style: the new script is named at the right point
  in the branch-check step; the "Work from:" / scratch-prep /
  review-package language references the resolved worktree path rather than
  an assumed repo root; the halt/handoff section names the worktree path
  when one was used.

## Open questions

None outstanding — all decision points (trigger scope, artifact
carry-forward mechanism, branch-naming convention, script-vs-prose
implementation shape) were resolved during design.
