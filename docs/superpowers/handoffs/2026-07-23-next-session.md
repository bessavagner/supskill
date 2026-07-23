# Handoff — supskill, 2026-07-23

For the next session (a fresh Claude Code on this repo). High-signal state + what to do next.

## Where things stand

- **Branch/remote:** `main` **pushed** to `origin/main`, working tree clean.
- **Released: `v0.4.0`** (commit `00b9dd2`, tag pushed to origin). Carries SK-101, SK-105, SK-106. Both manifests and `uv.lock` are at 0.4.0 and the version-consistency test passes.
- **The local install is still 0.3.0.** `~/.claude/plugins/cache/supskill/supskill/` holds `0.1.0…0.3.0`; a new cache dir appears only after a plugin update pulls the new tag. Until the operator updates the plugin, `/supskill run` (and the playset) still execute 0.3.0 code without these fixes. Update with `claude plugin update supskill@supskill` (or the `/plugin` UI), then confirm `…/cache/supskill/supskill/0.4.0/` exists.

## Done this session (all on `main`, pushed)

- **SK-101** finished (Task 3: `{STORY_ID_PREFIX}` templates + SKILL.md fill wiring) and merged (`d8f71af`). Parsers + audit + templates now honor a configured story-id prefix end to end.
- **SK-105** `commit-scope-guard` and **SK-106** `preflight` — implemented via full subagent-driven development, per-task + whole-branch reviews clean, merged (`7c22ca4`). New modules `scripts/supskill_state/commit_scope.py`, `preflight.py`; new CLI verbs `commit-scope-guard`, `preflight`; wired into SKILL.md (EXECUTE dispatch discipline + run checklist). 424 tests green.
- **Backlog updated** (`64a3317`) from the **playset s5** dogfood run: filed **SK-111**, **SK-112**, **SK-113**; re-pointed **SK-107** C→M (s5 reproduced it). E9 total 36→42 pts.

## The next dev plan (ready to execute)

**`docs/superpowers/plans/2026-07-23-sk111-sk112-worktree-state-and-reviewer-handoff.md`** — covers **SK-111 + SK-112** (chosen as the top-priority s5 EXECUTE-boundary findings). Two independent tasks:

- **Task 1 (SK-111, code):** `store.resolve_root()` redirects state lookups to the main worktree root when cwd is a git *linked* worktree (fixes `supskill-state` being refused from a `.worktrees/<id>` cwd during EXECUTE). Centralizes the repeated `root = Path.cwd()` idiom across `commands.py` (a DRY win). Narrow rule: only a linked worktree redirects; main worktree / subdir / non-repo cwd unchanged.
- **Task 2 (SK-112, prose):** the EXECUTE drain's task-review dispatch writes findings to `<scratch>/task-<N>-review-findings.md` and returns one status line — "read the file, never the reply", the same discipline `7dfb0f9` gave supskill's own dispatches.

**To execute it:** branch off `main` (never implement on `main`), then run `superpowers:subagent-driven-development` against the plan — a fresh subagent per task, review between, merge with `--no-ff`, delete the branch, mark the rows `☑`, push. That is exactly the flow SK-105/106 used this session; the plan's Execution Handoff section restates the options.

## Open threads (not started)

1. **Release — done for 0.4.0; the local install still needs updating.** The release ritual is: bump `pyproject.toml` + `.claude-plugin/plugin.json` to the same version (a `test_plugin_version_matches_pyproject` guard ties them), run `uv lock` so `uv.lock` follows (it silently drifted after 0.3.0 and needed a repair commit), `chore: release X.Y.Z — <headline>`, `git tag -a vX.Y.Z`, push both `main` and the tag. **Remaining step:** update the installed plugin to 0.4.0 so the next playset run exercises the fixes rather than 0.3.0 code. Repeat the ritual after SK-111/112 land.
2. **Remaining E9 (open, M-priority):** SK-102 (blocker cancels unrun headings → make observable), SK-103 (`block` inverse / resolve), SK-104 (stale `review-final.diff` detection), SK-107 (now M — PLAN template must prove a novel test harness runnable; s5 gave a second instance). Lower: SK-108 (S), SK-109 (C), SK-110 (C — `cost --label refine` still live at `SKILL.md:128/136`, cosmetic), SK-113 (C — one-line halt-prose clarification).
3. **Playset s5 itself** (separate repo `~/Documents/projetos/playset`) is halted at REVIEW: PLS-020/021 done, PLS-022 blocked on an httpx `ASGITransport` SSE-test hang (operator must pick option a/b/c — a: switch to `starlette.TestClient`, recommended), PLS-023 parked. That's the playset operator's call, not supskill work — it was the *source* of this session's findings.

## Conventions that bit or matter here

- **No AI attribution** in commits/PRs (global rule). **No mypy** in this project (older plans mention it; it isn't installed). Lint is `uv run ruff check .` (100 cols); tests `uv run pytest` (offline).
- Guard modules follow one shape: pure check + `refusal()` string + thin `cli.py` verb + dedicated test + one SKILL.md sentence (`plan_guard.py`/`replan_guard.py` are the templates).
- Dispatched subagents' **final chat messages routinely collapse to a placeholder** — always hand work over as files and read the file back (this is literally what SK-112 fixes for EXECUTE; apply it to any dispatch you make).
- `Agent` subagent type names here are `oh-my-claudecode:executor` / `oh-my-claudecode:code-reviewer` (plain `executor` fails).
