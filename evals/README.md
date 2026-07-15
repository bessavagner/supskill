# supskill description eval (SK-061)

This measures whether the conductor's shipped `description`
(`skills/supskill/SKILL.md`) fires on prompts that should start or resume a
sprint and stays silent on the near-misses that should not. It is **operator-run
and live** — a real `claude -p` spend — and is deliberately **not** part of the
offline `uv run pytest` suite. The only offline artifact is the corpus
(`evals/description-corpus.json`) and its shape test (`tests/test_eval_corpus.py`).

## What runs it

We compose `skill-creator`'s real eval loop (invariant 1 — compose, never
reinvent), not a bespoke scorer. `skill-creator` is installed under the
`claude-plugins-official` marketplace:

```
~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator
```

Its `scripts/run_eval.py` registers the description as a command in a project's
`.claude/commands/`, then runs `claude -p <query>` three times per query and
reports a per-query trigger rate. `scripts/run_loop.py` adds a description-
improvement loop with a train/test holdout.

`skill-creator` is an **author/eval-time tool only**. It is NOT a supskill
runtime dependency: it is absent from `pyproject.toml`, from
`.claude-plugin/plugin.json`'s `dependencies`, and from the conductor's
dispatched-skill set — guarded by
`tests/test_plugin_manifest.py::test_skill_creator_is_not_a_runtime_dependency`.

## The invocation

Set `SC` to the skill-creator skill directory above, `SUP` to this repo's root,
and `MODEL` to the model you are budgeting for. A single scoring pass:

```bash
SC=~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator
SUP=<absolute path to this repo>
cd "$SC"
python -m scripts.run_eval \
  --eval-set "$SUP/evals/description-corpus.json" \
  --skill-path "$SUP/skills/supskill" \
  --model "$MODEL" \
  --runs-per-query 3 \
  --verbose
```

`run_eval.py` reads the description straight from `skills/supskill/SKILL.md`; do
not pass `--description` unless you are testing an alternative. For the
description-improvement loop instead of a single pass, use `python -m
scripts.run_loop` with the same `--eval-set` / `--skill-path` / `--model` and
its `--holdout` default.

> **Open wiring detail, stated so the operator confirms it at run time.**
> `run_eval.py` discovers its project root by walking up from the working
> directory for a `.claude/` dir, and writes the synthetic command file there.
> Run from `$SC` (so its `from scripts...` imports resolve) it will use the
> nearest `.claude/` on that path. This does not change *what* is scored — the
> synthetic command carries the description under test — but confirm the run
> completes and reports rates before trusting the number. This is the smaller,
> reversible default; if the wiring misbehaves, run `run_eval.py` by absolute
> path with `$SC` on `PYTHONPATH` from `$SUP` instead.

## The token budget

Cost is `len(corpus) × runs-per-query` `claude -p` calls per pass (16 × 3 = 48
for the corpus as authored), times the number of loop iterations if you use
`run_loop.py`. **Set and record a bounded budget before running.** This is an
operator-gated spend, not an offline check.

## What the number means, and does not

The command-registration path above is **separate** from the conductor's own
`disable-model-invocation: true` frontmatter (`skills/supskill/SKILL.md`), which
stays untouched. So the hit rate is a **real trigger rate for a command-
registered copy of the shipped description** — a fair proxy for what auto-invoke
would do if that flag were ever relaxed, not a literal reading of the disabled
auto-invoke path, and not a prediction of live auto-invocation. Report it that
way. Relaxing the flag remains a separate, operator-owned call
(`skills/supskill/references/invocation-model.md:13-18`), with this hit rate as
evidence — not a packaging default.
