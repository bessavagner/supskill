# Auto-isolating EXECUTE into a worktree

Extracted from **The EXECUTE stage**'s branch check to keep `SKILL.md` under
its line cap. Referenced from step 1 (the branch check) and from **The halt**.

## When this fires

Only when `git rev-parse --abbrev-ref HEAD` names the repo's default branch
(from the same derivation ladder step 1 already runs), or the literal `HEAD`
(detached). Any other branch is unchanged: the dispatch root is the repo
root, no worktree, no script call — this file has nothing to say about that
case.

## Computing the branch name

`sprint.branch` from `show --json`, if the operator set one at `init
--branch`. Otherwise the normalized sprint id: lowercase `sprint.id`, the
same normalization `sprint.scratch` already carries (e.g. `S15` → `s15`) —
never invent a different rule.

## The script call

    ${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state worktree --branch <branch-name> \
      --artifact <sprint_doc> --artifact <dev_plan>

`<sprint_doc>` / `<dev_plan>` are `artifacts.sprint_doc` / `artifacts.dev_plan`
from `show --json`, whichever are non-null. Both are **uncommitted**
working-tree files at this point — PLAN's dispatched agent never commits — so
the script copies them into the worktree itself. A plain `git worktree add`
checks out a *commit*, not working-tree state, and would silently lose both
otherwise.

The script:
1. Ensures `.worktrees/` is gitignored (appends if missing; never commits the
   edit).
2. Reuses an already-registered worktree at `.worktrees/<branch>` if its
   directory is still on disk; refuses with a `StateError` if git knows about
   it but the directory is gone (never silently recreates over lost state).
3. Otherwise creates one — attaching to the branch if it already exists (an
   operator who ran a manual `git switch -c`/`branch` before this landed),
   else creating both branch and worktree fresh, from current HEAD.
4. (Re-)copies every `--artifact` on every call, including reuse, so the two
   documents stay fresh across a `/clear`-and-resume.
5. Prints exactly one line: `worktree ready at <path> (created|reused)`.

If the script raises, report its refusal verbatim and stop — the same rule as
every other CLI refusal in this skill. There is no silent fallback to
dispatching on the default branch.

## The dispatch root, for the rest of this run

`<path>` from that one line **is the dispatch root** until this EXECUTE run
ends. Everything that writes code or scratch state runs against it:

- every SDD dispatch's `Work from:` line names it, never an assumed repo root
- `sdd-workspace` and `mkdir -p <scratch>` (step 2) run there
- `task-brief` reads `<dev_plan>` from its synced copy there
- `git rev-parse HEAD` (recording `BASE`) and `review-package` (per-task and
  final) run as `git -C <dispatch-root> ...`

**What never moves:** `.supskill/state.json` and every `supskill-state` /
`supskill-audit` call stay anchored at the **original repo root**, worktree or
not, for the sprint's entire lifecycle. Only the code-writing was ever the
thing needing isolation.

## At the halt

Name the worktree's path and branch explicitly in the halt report, so the
operator can apply the same merge/PR/keep/discard choice — and worktree
cleanup — they would use for any other branch. EXECUTE never auto-merges,
auto-PRs, or auto-cleans a worktree it created; that decision is the
operator's alone, exactly like every other branch-lifecycle call in this
codebase.
