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
  verbatim and stop — never work around a refusal.
- **Never pass `--archive`.** Archiving a half-finished sprint is an operator
  decision. The only thing this skill does with that flag is name it in the
  refusal message of matrix cell 3 below.

## Arguments

`$ARGUMENTS` is `run <sprint-id>` (e.g. `run s2`), optionally followed by
flags that are forwarded to `init` if — and only if — init runs:
`--entry SCOPE|PLAN|EXECUTE`, `--backlog <path>`, `--branch <name>`,
`--slug <slug>`.

- First token is not `run`, or there is no sprint id AND no
  `.supskill/state.json` in the current directory → print exactly this usage
  line and stop. Ask nothing — subagents cannot ask, and the conductor must
  not build a habit the stages cannot share:

      usage: /supskill run <sprint-id> [--entry SCOPE|PLAN|EXECUTE] [--backlog <path>] [--branch <name>]

- No sprint id but `.supskill/state.json` exists → treat as a resume of the
  on-disk sprint: start the run checklist at step 1 and skip the id
  comparison in step 3.

## The run checklist

Copy this checklist into your response and check items off as you go.

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
   - Different → refuse and stop. The refusal must name both ids and the
     operator's way forward, verbatim:

         A different sprint is already on disk: state.json holds <sprint.id>,
         you asked for <requested-id>. A half-finished sprint is never
         archived automatically. If you mean to close it out and start fresh,
         run: ${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state init <requested-id> --archive

     Do not run that command. Stop here.
4. **Report the resume surface.** From the same `show --json` output, report:
   the sprint id and slug, current `stage`, `sprint.entry`, each gate's
   decision (`null` = pending), each recorded artifact path, the `backlog`
   path, task counts by status, and open blockers. This report must come from
   the JSON alone — consult no memory of any prior conversation.
5. **Dispatch on `stage`.** Look up `stage` in the table below and do exactly
   what it says. `stage` from `show --json` is the dispatch's only input.

## Dispatch table (v-E2: every stage is an honest stub)

| `stage` | Action |
|---|---|
| `SCOPE` | Report: "SCOPE is not implemented yet — it lands with E3 (SCOPE + REFINE + Gate 1)." Stop. |
| `REFINE` | Report: "REFINE is not implemented yet — it lands with E3 (SCOPE + REFINE + Gate 1)." Stop. |
| `PLAN` | Report: "PLAN is not implemented yet — it lands with E4 (PLAN + Gate 2)." Add: the recorded `artifacts.sprint_doc` is the spec PLAN will hand to `superpowers:writing-plans`. Stop. |
| `EXECUTE` | Report: "EXECUTE is not implemented yet — it lands with E5 (drain-then-halt)." Add: the recorded `artifacts.dev_plan` is the plan EXECUTE will drive. Stop. |
| `REVIEW` | Report: "REVIEW is not implemented yet — it lands with E6 (PAR + Gate 3)." Stop. |

A stub that init's, resumes, and honestly says "not implemented yet; here is
the state" is the correct v-E2 behavior — do not improvise a stage.

## Reference

- Why this skill is user-invoked only:
  [references/invocation-model.md](references/invocation-model.md)
