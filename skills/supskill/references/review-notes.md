# PAR dispatch and aggregation (SK-050)

Referenced from **The REVIEW stage** in `SKILL.md`. This file is
conductor-facing: nothing here is sent to a subagent — that is
`review-prompt.md`'s job.

## Dispatch

Two fresh general-purpose subagents, `reviewer-a` and `reviewer-b`, each
dispatched from `references/review-prompt.md` filled once for its own
`{REVIEWER_LABEL}`, on the identical `{REVIEW_PACKAGE_PATH}` =
`<scratch>/review-final.diff` — EXECUTE's own last act before it halted
(`skills/supskill/SKILL.md:344-347`, `:472-475`). Dispatch both before
reading either's output; **neither reviewer sees the other's**, which is the
competitive frame's entire point (D9). Cost each dispatch as it completes:
`cost --stage REVIEW --label reviewer-a` / `cost --stage REVIEW --label
reviewer-b`.

## Matching

Which finding from `reviewer-a` corresponds to which from `reviewer-b` is
your judgment — a string comparison is not enough, and this doc does not
pretend otherwise. Match on what the finding actually points at (the same
location, the same mechanism), not on identical wording.

## Aggregation — fixed, no negotiation

Once matched:

| Reported by | confidence | severity |
|---|---|---|
| both, same severity | `high` | that severity |
| both, different severities | `high` | the worse of the two, always — `Critical > Important > Minor` |
| one reviewer only | `actionable` | that reviewer's severity |

`scripts/supskill_state/review.py`'s `aggregate()` is this table, as a pure
function of one already-matched finding's reported severities.

## Recording

One `review` call per finding, after both dispatches have returned:

    review --reviewer <reviewer-a|reviewer-b|both> \
      --severity <Critical|Important|Minor> \
      --confidence <high|actionable> \
      --finding "<description>" \
      --location "<file:line or path>"

`--reviewer both` is for a finding matched across both dispatches;
`--reviewer reviewer-a` or `--reviewer reviewer-b` for a finding only one of
them reported. The verb refuses an empty `--finding`/`--location` and an
unknown `--reviewer`/`--severity`/`--confidence` token, writing nothing on
any refusal — the same shape as `record_blocker`
(`scripts/supskill_state/commands.py:219-272`). Findings land in
`runs/<id>/review.jsonl`, append-only, before Gate 3 opens.
