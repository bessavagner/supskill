# `.supskill/` state - schema v1

`supskill-state` (in `scripts/`) is the **only** permitted mutator of these
files (invariant 3). Layout:

    .supskill/
      state.json              # authoritative; the only file the conductor reads to resume
      gates.jsonl             # every gate decision + the operator's verbatim response (append-only)
      runs/<normalized-id>/
        blockers.jsonl        # every blocker record raised during execution (append-only)
        costs.jsonl           # every subagent dispatch's token/tool/duration usage (append-only)
        archive-<n>/          # a prior run's state.json + gates.jsonl, moved by `init --archive`

## Conventions

- **Datetime**: every timestamp anywhere in these files is timezone-aware UTC,
  ISO-8601 (e.g. `2026-07-12T18:00:00+00:00`). Naive or non-UTC timestamps are
  a validation error.
- **Atomicity**: `state.json` is written via same-directory temp + rename; the
  `.jsonl` logs are opened append-only and never truncated or rewritten.
- **Write order**: where one verb writes a log and `state.json`, the log is
  written first. A crash between the writes leaves the audit trail *ahead of*
  state, never behind.

## `state.json` fields

- `schema` (int): always `1`. Any other value refuses on load - no silent
  migration.
- `backlog` (string|null): path to the backlog driving this sprint.
- `sprint.id` (string): as the operator typed it (e.g. `S10`).
- `sprint.slug` (string|null), `sprint.branch` (string|null).
- `sprint.entry` (string): `SCOPE | PLAN | EXECUTE` (D7). Preconditions attach
  to *transitions taken*, not stages - a sprint entering at EXECUTE never
  crosses the G2 check.
- `sprint.scratch` (string): **derived** from the id, never typed:
  `.superpowers/sdd/<normalized-id>/` where normalization is lowercase and only
  `[a-z0-9-]` is accepted (anything else refuses; D8).
- `stage` (string): `SCOPE | PLAN | EXECUTE | REVIEW`. Sprint
  completion is a **G3 decision, not a sixth stage**.
- `artifacts`: exactly `sprint_doc` and `dev_plan`, each a path or null.
- `gates`: exactly `G1_sprint_doc`, `G2_plan`, `G3_review`; each
  `null | "approved" | "rejected"` (last decision wins; full history lives in
  `gates.jsonl`).
- `tasks[]`: `{id, seam, provable, status}`. `seam` and `provable` use D9's
  taxonomy (`unit|integration|app-level|e2e`; `offline|operator`) and are
  stored as free strings in v1.
- `blockers[]`: `{task, kind, found, options[], recommend}` (D5). Options are
  labeled `(a) ...`; `recommend` starts with one of those labels.

## Task status

`PENDING -> DONE | DONE_WITH_CONCERNS | BLOCKED | PARKED`.
The terminal set `{DONE, DONE_WITH_CONCERNS, BLOCKED, PARKED}` is exported as
`supskill_state.model.TERMINAL_STATUSES`; consume it, never redefine it.

**`NEEDS_CONTEXT` is not a state** (for E5): SDD implementers may report it,
but its defined handling is "controller supplies missing info, re-dispatches
the same subagent" - a loop signal. Resolve it in-loop; if it cannot be
resolved, the task becomes `BLOCKED` plus a blocker record. `supskill-state`
rejects `NEEDS_CONTEXT` as a status value.

## Gates

CLI ids map one-to-one onto state keys:

| CLI id | state key      | guards transition    |
|--------|----------------|----------------------|
| `G1`   | `G1_sprint_doc`| `advance --to PLAN`   |
| `G2`   | `G2_plan`      | `advance --to EXECUTE`|
| `G3`   | `G3_review`    | (E6's replan verbs)   |

`gates.jsonl` records `{gate, decision, response, at}` per decision, where
`gate` is the CLI id, `decision` is `approved|rejected`, `response` is the
operator's verbatim words (an **empty response is accepted and recorded** -
the audit trail's job is to make a fabricated approval readable, F-4), and
`at` is aware-UTC ISO-8601.

## Costs

`costs.jsonl` records `{stage, label, tokens, tool_uses, duration_ms, at}` per
subagent dispatch, where `stage` is one of `SCOPE | PLAN | EXECUTE |
REVIEW`, `label` is a free-text name for the dispatch within that stage (e.g.
`implementer`, `task-reviewer`, `fix`, `reviewer-a`) or `null` when the stage
dispatches only one agent, `tokens` is that dispatch's reported
`subagent_tokens`, `tool_uses` and `duration_ms` are its reported counterparts
(nullable - not every caller has them), and `at` is aware-UTC ISO-8601. This
verb never touches `state.json`: it is pure telemetry, recorded so questions
like PAR's doubled review cost or whether a SCOPE pass earns its keep get
answered from real numbers instead of estimation.
