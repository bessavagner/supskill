# supskill validation (E8)

Two gated, operator-run, live validations — deliberately **not** part of the offline `uv run pytest`
suite, the same split `evals/README.md` uses for SK-061's eval loop. What's offline here is the
harness: a disposable fixture repo and the runbooks/report template below. The runs themselves cost
real tokens and real time and are never automated by a subagent.

| Story | Runbook | What it proves |
|---|---|---|
| SK-070 | [fixture-run.md](fixture-run.md) | A real, cheap, two-sprint run against a throwaway toy backlog (`fixture-repo/`) — the harness works at all. |
| SK-071 | [blinkebot-run.md](blinkebot-run.md) | A real sprint against blinkebot, a project the operator actually depends on — the design doc's own validation bar. |

Both write their result into a copy of [report-template.md](report-template.md) under
`validation/reports/` (gitignored except for `.gitkeep` — reports document a point-in-time run, not a
tracked source file).

## This directory's own limits

Building this harness is not the same as clearing E8. The backlog rows for SK-070 and SK-071, and
`README.md`'s E8 status row, stay unchecked / `⬜ backlog` until an operator has actually run both
validations and filed a passing report — flip them by hand, in a `docs:` commit, at that time; no
task in this plan does it for you.
