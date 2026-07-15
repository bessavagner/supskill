# The four replan shapes (SK-052)

Referenced from Gate 3 in `SKILL.md`. Pulled verbatim from the design's own
table (`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:244-254`):
the first three amend the backlog; the fourth replaces it and is refused —
see `SKILL.md`'s "Refusing a north-star supersede".

## Shape 1 — generative writeback

Append new rows to `backlog.md` under the relevant epic (or a new epic, if
none fits), in the existing row format — `| ID | Story | Pts | Pri | Status |` (`docs/plans/sprints/backlog-01/backlog.md:84`), status `☐` — each citing
the PAR finding or blocker that motivated it. Only append: never edit an
existing row's points or status here — that is a backlog-delta ritual owned
by the sprint that actually implements the change, per every prior sprint's
own "Backlog deltas — proposed" section. This is a direct edit to
`backlog.md`, outside `supskill-state` — invariant 3 binds `state.json`
specifically (`docs/plans/sprints/backlog-01/backlog.md:29-30`); `backlog.md`
was never inside that boundary, and every prior sprint's delta pass has
already edited it this way, by hand, in a `docs:` commit.

## Shape 2 — park at a live boundary

`task --id <SK-0xx> --status PARKED --note "<the blocker that parked it>"` —
the verb that already exists (`scripts/supskill_state/commands.py:331-387`).
The sprint itself is **not** advanced past `REVIEW`; name which live boundary
stopped it in the report.

## Shape 3 — fork on live evidence

Draft a forked sprint id, and a branch-rename recommendation where
warranted, but do not execute either unasked — the operator rules on the
fork's process weight first. A fork's `init` is the verb that already exists
(`scripts/supskill_state/commands.py:39-90`); a branch rename is not a verb
at all and this shape does not add one — the same restraint EXECUTE's own
branch check already states: "Do not create, switch, or delete a branch
yourself" (`skills/supskill/SKILL.md:312-313`). Name the rename; do not
run it.

## Shape 4 — north-star reset

Out of scope by construction: no verb reachable from any shape above
supersedes `backlog.md` wholesale. See `SKILL.md`'s "Refusing a north-star
supersede".

---

Every shape above is recorded through a verb that already exists — a
`backlog.md` edit, `task --status PARKED`, a fresh `init` — never a new mutator.
