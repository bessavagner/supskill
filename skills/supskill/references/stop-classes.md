# The stop classes (SK-130 / SK-135)

Referenced from Conventions and from Gate 3 in `SKILL.md`. This file is
conductor-facing: nothing here is sent to a subagent — every stop below
fires inside the conductor's own run, never inside a dispatched agent's
prompt. `scripts/supskill_state/stop_classes.py` is the authority this
table describes, not the other way round: ids and conditions below are
copied verbatim from `stop_classes.STOPS`, and a test
(`tests/test_stop_prose.py`) pins that every non-`no_stop` id from that
table appears here.

Every seam where `supskill-state` stops carries exactly one class:

- **remediable** — the stop names a known, safe, specific action, and the
  conductor takes it, then records it: `action --stop <id> --command "<the
  exact command>" --operator-answered` (SK-131).
- **evidential** — acting on the stop would destroy the signal it exists to
  raise (a regenerated review package comes back clean, which is precisely
  what `review-guard` exists to prevent). The conductor relays the refusal
  verbatim and stops. Nothing is ever recorded for one of these.

`action --stop <id>` itself refuses for an evidential id — `record_action`
checks `stop.stop_class` before writing anything — and refuses for either
class without `--operator-answered`: a run that has not received a real,
non-empty answer from an operator does not act on their behalf (SK-136).
`AskUserQuestion` auto-resolves with an empty answer in headless runs, and
an empty answer is not consent. That refusal, too, is relayed verbatim like
any other stop.

## Remediable — the conductor acts, then records it

| id | condition | action | recording it |
|---|---|---|---|
| `init.archive.decided` | a different sprint is on disk and its G3 decision IS recorded | run `init <id> --archive`, carrying every operator flag forward verbatim | `action --stop init.archive.decided --command "<the exact init line>" --operator-answered` |
| `artifact-guard.untracked` | a recorded artifact is untracked by git | stage and commit exactly the recorded artifact paths | `action --stop artifact-guard.untracked --command "<the exact git line>" --sha <the resulting commit SHA> --operator-answered` |

### Checking a set of paths before the conductor commits

`artifact-guard.untracked`'s action is the one case where the conductor
stages files nobody has committed yet, so the foreign-state check has to
run before the commit rather than after it. `commit_scope.guard_conductor_commit`
is that check (SK-134): the same denylist `commit-scope-guard` already
refuses on — `.omc/`, `.superpowers/`, `.supskill/`, `.codegraph/` — applied
to the staged set of paths instead of a committed `BASE..HEAD` range. Run it
from the repo root:

    python3 -c "
    import sys
    sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
    from supskill_state.commit_scope import guard_conductor_commit
    print(guard_conductor_commit(sys.argv[1:]))
    " <untracked artifact path> [<untracked artifact path> ...]

An empty list back → the paths are clean: `git add <path> [<path> ...] &&
git commit -m "docs: track sprint artifacts"`, keep the SHA (`git rev-parse
HEAD`), then record the action above. A non-empty list is
`commit-scope-guard.foreign`'s shape reached through a different door:
relay which path and its prefix, and stop — that commit is not yours to
make, and nothing is recorded.

## Evidential — relayed verbatim, never acted on

| id | condition |
|---|---|
| `init.archive.undecided` | the sprint on disk rests at REVIEW with no G3 decision (SK-115) |
| `review-guard.stale` | HEAD moved past the recorded package, or none was recorded |
| `plan-guard.commits` | the plan agent produced commits |
| `commit-scope-guard.foreign` | a commit range swept foreign harness state in |
| `replan-guard.north-star` | the shape reads as a north-star reset (invariant 7) |
| `preflight.unresolvable` | a skill a later stage dispatches will not resolve |
| `tasks.coverage` | the dev plan does not cover the sprint doc's stories |

Every one of these seven is a refusal the conductor relays and stops on —
never a command it runs, never an `action` it records. Acting on any of
them would destroy the signal it exists to raise.
