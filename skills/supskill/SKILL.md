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
- **Stage agents never touch state.** Stages dispatch subagents from templates
  under `references/`; the conductor runs every `supskill-state` call itself,
  and no template instructs an agent to run one or to write under `.supskill/`.

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

## Dispatch table

| `stage` | Action |
|---|---|
| `SCOPE` | Follow **The SCOPE stage** below. |
| `REFINE` | Report: "REFINE is not implemented yet — it lands with E3 (SCOPE + REFINE + Gate 1)." Stop. |
| `PLAN` | Report: "PLAN is not implemented yet — it lands with E4 (PLAN + Gate 2)." Add: the recorded `artifacts.sprint_doc` is the spec PLAN will hand to `superpowers:writing-plans`. Stop. |
| `EXECUTE` | Report: "EXECUTE is not implemented yet — it lands with E5 (drain-then-halt)." Add: the recorded `artifacts.dev_plan` is the plan EXECUTE will drive. Stop. |
| `REVIEW` | Report: "REVIEW is not implemented yet — it lands with E6 (PAR + Gate 3)." Stop. |

PLAN, EXECUTE, and REVIEW are honest stubs until their epics land — do not
improvise a stage. An implemented stage follows its section below exactly.

## The SCOPE stage

The stage pattern (E4–E6 copy this shape): dispatch a fresh-context subagent
from a template, verify its artifact mechanically, record it via
`supskill-state`, advance, fall through.

1. **Resume idempotence.** If `artifacts.sprint_doc` is recorded AND the file
   exists, SCOPE already ran — a crash between `artifact` and `advance` must
   not re-spend a run. Run `advance --to REFINE` and continue at the REFINE
   stage.
2. **Check the backlog.** If `backlog` is null (a pre-S3 state file; `init`
   now refuses to create this), report that a SCOPE sprint without a backlog
   has nothing to scope, name
   `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state init <sprint-id> --archive --backlog <path>`
   as the operator's way forward WITHOUT running it, and stop.
3. **Derive the output path** — a default the prompt supplies; the recorded
   artifact is the only authority anything downstream reads. The path is the
   backlog's own directory + `sprint-<id>-<slug>.md`, where `<id>` is the
   sprint id lowercased and `-<slug>` is dropped when `sprint.slug` is null.
   Example: backlog `docs/plans/sprints/backlog-01/backlog.md`, sprint `s4`,
   slug `plan-gate2` → `docs/plans/sprints/backlog-01/sprint-s4-plan-gate2.md`.
4. **Fill the template** [references/scope-prompt.md](references/scope-prompt.md)
   — every `{PLACEHOLDER}` it names. `{EXEMPLAR_DOCS}` is up to two existing
   `sprint-*.md` files in the backlog's directory (never the output path
   itself); if none exist, fill it with `none`.
5. **Dispatch** one general-purpose subagent whose entire prompt is the filled
   template.
6. **Verify mechanically.** The file must now exist at the derived output
   path. If it does not, report the agent's returned output verbatim and stop
   — no blocker verb is available before tasks exist, and the operator is one
   gate away.
7. **Record and advance.** Run
   `artifact --set sprint_doc --path <output path>`, then
   `advance --to REFINE`, then continue at the REFINE stage.

## Reference

- Why this skill is user-invoked only:
  [references/invocation-model.md](references/invocation-model.md)
