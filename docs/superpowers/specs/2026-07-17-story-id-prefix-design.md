# Design: configurable story-id prefix, and a citation carve-out for tooling findings

## Problem

supskill is a plugin: it's installed into other repos (e.g. `blinkebot`) and drives
their sprints against *their* backlogs. Two mechanisms hardcode assumptions that
only hold for supskill's own dogfooding:

1. **The story-id pattern is hardcoded to `SK-\d+`.** `proofs.py:38`'s `_STORY` and
   `plan_coverage.py:24`'s `_STORY_ID` both compile a literal `SK-\d+` regex. Any
   consuming project whose backlog uses a different prefix (`BLK-103`, `PROJ-7`,
   etc.) fails the REFINE proof-grammar check and the PLAN/story join-key check
   unconditionally — not because the doc is wrong, but because the tool can't see
   the project's own ID scheme.

2. **REFINE's citation rule has no sanctioned way to evidence a tooling finding.**
   `refine-prompt.md`'s citation clause requires every claim to carry a
   `path:line` citation that "resolves in `{REPO_ROOT}`'s working tree." A finding
   *about supskill's own mechanism* (e.g. "this validator hardcodes `SK-\d+`") is
   necessarily about code that lives in the plugin's install tree, not
   `{REPO_ROOT}`. The only citation style the prompt offers can never resolve for
   this class of finding, so a true, well-investigated finding fails the audit as
   if it were fabricated evidence.

Both surfaced together in one real run: `supskill:supskill run s15` against
blinkebot's `BLK-`-prefixed backlog. REFINE correctly identified the prefix
mismatch as a DoR finding, then cited the plugin's own `proofs.py`/
`plan_coverage.py` source as evidence — which does not resolve under
`blinkebot`'s working tree — and the run stalled at REFINE with no way to
proceed other than an operator decision.

## Goals

- Let a consuming project declare its own story-id prefix, once, per project.
- Zero behavior change for supskill's own repo and any project that hasn't
  opted in — default to today's `SK` scheme.
- Give REFINE (and PLAN) agents a sanctioned, audit-safe way to state a finding
  about supskill's own tooling, without inventing a second citable root.

## Non-goals

- Auto-detecting the prefix from `backlog.md`'s heading shapes.
- A full custom regex per project (only the prefix letters are configurable;
  the shape is always `PREFIX-\d+`).
- Changing `cli.py`'s illustrative `SK-041` / `(SK-0xx)` help text — these are
  examples, not enforced values.
- A second citable root (e.g. `{CLAUDE_PLUGIN_ROOT}`) in the citation auditor.
- Surfacing the active prefix in `supskill-state show`.

## Design

### A. Project-level config file

A new module, `scripts/supskill_state/config.py`, owns one setting:
`story_id_prefix`, persisted at `.supskill/config.json` — a sibling of
`state.json`, resolved the same way `store.py` resolves `.supskill/`
(`Path.cwd() / ".supskill"`, no upward search).

```json
{"story_id_prefix": "BLK"}
```

- `load_story_id_prefix(root: Path | None = None) -> str` — returns the
  configured prefix, or `"SK"` if no config file exists.
- `write_story_id_prefix(prefix: str, root: Path | None = None) -> None` —
  validates against `^[A-Z][A-Z0-9]*$` (rejects lowercase, digit-first, empty,
  punctuation) and writes/updates the file, preserving any other keys already
  present (future-proofing the file's schema for other config knobs).

`config.py` exposes only the prefix *string*, never a compiled pattern or raw
regex — `proofs.py` and `plan_coverage.py` stay the sole owners of their own
grammars, same as today, composing `re.escape(prefix) + r"-\d+"` into their own
anchored regex instead of a hardcoded literal.

This file is deliberately separate from `state.json`: the ID scheme is a
property of the *project*, not of one sprint run, so it survives
`init --archive` instead of resetting with each sprint.

### B. New CLI verb

`supskill-state config --story-id-prefix BLK` (`cli.py`'s `_add_config` /
`_cmd_config`) delegates to a new `commands.set_story_id_prefix(prefix, root=None)`,
which wraps `config.write_story_id_prefix`. Success prints
`set story id prefix: BLK (was: SK)`. An invalid prefix refuses via the same
`StateError` → `supskill-state: refused: ...` path every other verb uses.

There is no separate read verb — `load_story_id_prefix` is called internally
wherever the prefix is needed (see C). `supskill-state show` is unchanged.

### C. Threading the prefix through the parsers

- `proofs.py`: `parse_proof_lines(text: str, story_prefix: str = "SK")` compiles
  `_STORY` per call. Every existing call/test that omits the new argument keeps
  passing unchanged — the default reproduces today's hardcoded behavior exactly.
- `plan_coverage.py`: `validate_plan_coverage(plan_text, story_ids, story_prefix: str = "SK")`,
  same treatment for `_STORY_ID`.
- `commands.py`'s `load_tasks()`: loads the prefix once via
  `config.load_story_id_prefix(root)`, passes it to both `parse_proof_lines`
  and `validate_plan_coverage`.
- `citations.py`'s `main()` (the standalone `supskill-audit` CLI): when
  `--proofs` is passed, it also calls `config.load_story_id_prefix(Path.cwd())`
  before invoking `parse_proof_lines` — `supskill-audit` has no sprint/state
  context of its own, so it resolves the project's configured scheme directly
  from cwd, the same way `store.py` does.

No other call site touches these regexes.

### D. Prompt guidance carve-out for tooling findings

Add a short carve-out immediately after the existing citation clause in both:

- `refine-prompt.md` (item 1, the citation requirement)
- `plan-prompt.md` (item 3, the citation requirement)

> A finding about supskill's own tooling or mechanism — not `{REPO_ROOT}`'s
> code — is not evidenced by a citation into the plugin's installed source
> tree; it doesn't live under `{REPO_ROOT}` and no such citation can resolve.
> Evidence for a tooling finding is the reproduced symptom itself: quote the
> exact command and its verbatim output in prose, with no backtick
> `path:line` token, so the citation audit has nothing to (mis)resolve.

Pure prompt-text change, no code involved. It generalizes past this one
incident: any future tooling/mechanism finding an agent surfaces gets a
sanctioned, audit-safe way to be stated, instead of reaching for the one
citation style the prompt offers and failing the audit on a true claim.

## Testing plan

- `tests/test_config.py` (new): round-trip write/read of
  `.supskill/config.json`; default `"SK"` when no file exists; rejects invalid
  prefixes (lowercase, digit-first, empty, punctuation); `write_story_id_prefix`
  preserves unrelated keys already in the file.
- `tests/test_proofs.py`: add a `story_prefix="BLK"` case — proof-line parsing
  and the "no heading" violation message both honor a custom prefix.
- `tests/test_plan_coverage.py`: same, a custom-prefix case for the join-key
  validation.
- `tests/test_citations.py`: an integration-style case — a temp project with
  `.supskill/config.json` set to `BLK` and a doc using `### BLK-1` headings
  passes `--proofs`; the same doc fails without the config present (default
  `SK`), proving the fallback still gates correctly.
- CLI wiring for the new `config` subcommand gets a thin test alongside the
  existing CLI tests (likely `tests/test_init.py`, which already covers
  `init`'s CLI wiring) — writes via CLI, asserts the file contents.

## Open questions

None outstanding — all decision points were resolved during design (config
location, detection mechanism, pattern shape, `show` output, scope of the
citation-carve-out fix).
