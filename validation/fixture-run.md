# Driving the fixture repo for real (SK-070)

**Status: operator-run and live** — a real, gated `supskill` run through both sprints of
`validation/fixture-repo`'s toy backlog. Deliberately **not** part of the offline `uv run pytest`
suite, the same split `evals/README.md` already uses for SK-061. The only offline artifact is the
fixture itself (`validation/fixture-repo/`) and its shape test (`tests/test_fixture_backlog.py`).

## What this proves

The design doc's own validation bar: "v1 is built by hand, then earns its keep by driving a real
sprint. If it cannot run one sprint the operator would have run anyway, it does not ship."
(`docs/.ai/reports/2026-07-12-supskill-design-decisions.md:345`.) SK-070 is the cheap, disposable
version of that bar — two tiny sprints, six points total, run against a project nobody actually
depends on — before SK-071 spends real effort on blinkebot.

## Set up an isolated copy

Never run this against `validation/fixture-repo/` in place — the run mutates it (`.supskill/`,
committed files, git history). Copy it to a scratch directory and `git init` there:

```bash
cp -r validation/fixture-repo /tmp/supskill-fixture-run
cd /tmp/supskill-fixture-run
git init -q
git add -A
git commit -q -m "fixture: initial state"
```

## Install the plugin

Install `supskill` from your marketplace into this scratch repo the same way any real project would
(this repo's own `README.md` Installation section) — not a symlink or clone into `.claude-plugin/`.

## Run both sprints

From `/tmp/supskill-fixture-run`, invoke the conductor per `skills/supskill/SKILL.md`'s entry point
for sprint `s1` (E1 — Greeting core), then again for `s2` (E2 — Greeting CLI) once `s1`'s Gate 3
proposes it. Follow every stage and gate exactly as the skill instructs — do not skip a gate because
the fixture is small; a skipped gate proves nothing about the real one.

## Record the result

Fill in `validation/report-template.md` (copy it to `validation/reports/fixture-run-<date>.md`) once
both sprints reach Gate 3. Name every gate decision, every blocker or parked task, and the total
tokens spent per stage (`.supskill/runs/<id>/costs.jsonl` in the scratch copy).

## What a pass looks like

Both sprints reach Gate 3 approved, `greet` and its CLI exist and satisfy every story's acceptance
criteria named in the backlog, and nothing in the run required stepping outside `supskill-state` to
make progress. Anything short of that is a finding for the report, not a reason to patch the fixture
until it passes.
