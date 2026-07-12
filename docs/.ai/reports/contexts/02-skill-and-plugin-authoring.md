---
title: Skill and plugin authoring for Claude Code — official reference
date: 2026-07-12
sources:
  - https://code.claude.com/docs/en/skills
  - https://code.claude.com/docs/en/plugins-reference
  - https://code.claude.com/docs/en/plugin-marketplaces
  - https://code.claude.com/docs/en/sub-agents
  - https://code.claude.com/docs/en/hooks
  - https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
  - https://github.com/anthropics/skills
  - https://github.com/anthropics/claude-plugins-official
  - https://paddo.dev/blog/claude-skills-controllability-problem/
---

# Skill and plugin authoring for Claude Code

Research for supskill (Claude Code plugin: skill + agents + driver script, distributed via a
GitHub marketplace). All facts below are sourced from official Anthropic docs unless marked
otherwise; the controllability section draws on a third-party critique (paddo.dev), flagged as
opinion, not spec.

## 1. SKILL.md anatomy

**Required/validated frontmatter** (from the platform best-practices page, which states the
actual validation rules — the Claude Code skills page calls both fields technically optional
but `description` "recommended"):

> "`name`: Maximum 64 characters. Must contain only lowercase letters, numbers, and hyphens.
> Cannot contain XML tags. Cannot contain reserved words: 'anthropic', 'claude'."
> "`description`: Must be non-empty. Maximum 1024 characters. Cannot contain XML tags. Should
> describe what the Skill does and when to use it."
> — [platform.claude.com best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

Claude Code's own reference is more permissive at the frontmatter-parsing level ("All fields are
optional. Only `description` is recommended so Claude knows when to use the skill") but layers a
**hard 1,536-character cap** on the combined `description` + `when_to_use` text as rendered in
the skill listing:

> "Put the key use case first: the combined `description` and `when_to_use` text is truncated at
> 1,536 characters in the skill listing to reduce context usage."
> — [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)

If `description` is omitted, Claude Code falls back to the first paragraph of the markdown body.
If the frontmatter YAML is malformed, the skill still loads (so `/skill-name` still works) but
with **no** description, so Claude never auto-triggers it — this fails silently; only `--debug`
surfaces the parse error.

**Full Claude Code frontmatter field table** (all optional beyond `description`):

| Field | Purpose |
|---|---|
| `name` | Display name in listings; only sets the *invocation* name for a plugin-root `SKILL.md` (see §5) |
| `description` | Discovery trigger text (see below) |
| `when_to_use` | Extra trigger phrases, appended to `description`, counts toward the same 1,536-char cap |
| `argument-hint` | Autocomplete hint, e.g. `[issue-number]` |
| `arguments` | Named positional args for `$name` substitution |
| `disable-model-invocation` | `true` → only the user can invoke it (`/name`); hides it from Claude's context and from subagent preloading |
| `user-invocable` | `false` → hides from the `/` menu; only Claude can invoke it |
| `allowed-tools` | Tools pre-approved (no permission prompt) while the skill is active |
| `disallowed-tools` | Tools removed from the pool while active (clears on next message) |
| `model` | Override model for the turn |
| `effort` | Override effort level for the turn |
| `context: fork` | Run the skill body as the prompt for a forked subagent |
| `agent` | Which subagent type to fork into (`Explore`, `Plan`, `general-purpose`, or custom) |
| `hooks` | Hooks scoped to this skill's lifecycle |
| `paths` | Glob patterns gating auto-activation to matching files |
| `shell` | `bash` (default) or `powershell` for inline `!command` execution |

### Description quality — Anthropic's own good/bad examples

> "Always write in third person. The description is injected into the system prompt, and
> inconsistent point-of-view can cause discovery problems.
> **Good:** 'Processes Excel files and generates reports'
> **Avoid:** 'I can help you process Excel files' / 'You can use this to process Excel files'"

> "Effective examples: `description: Extract text and tables from PDF files, fill forms, merge
> documents. Use when working with PDF files or when the user mentions PDFs, forms, or document
> extraction.`"

> "Avoid vague descriptions like these: `description: Helps with documents` / `description:
> Processes data` / `description: Does stuff with files`"
> — best-practices page

Mechanically, discovery is **not** algorithmic keyword matching — it is the model reading the
full listing of names+descriptions (pre-loaded into every session's context) and deciding by
semantic judgment whether the current request matches. This is the crux of the controllability
debate in §8.

Naming convention guidance: prefer gerund form (`processing-pdfs`, `analyzing-spreadsheets`)
over vague (`helper`, `utils`) or generic (`documents`, `data`) names.

## 2. Progressive disclosure

Three-tier loading model, explicit in both docs:

1. **Metadata tier (always-on):** only `name` + `description` (+ `when_to_use`) for *every*
   installed skill are pre-loaded into the system prompt at session start. This is the
   `skillListingBudgetFraction`-bounded cost (~1% of the context window by default).
2. **Body tier (on invoke):** the full `SKILL.md` markdown body loads only when the skill is
   actually invoked (by the user or by Claude), and then **persists in context for the rest of
   the session** — it is not re-read per turn.
3. **Reference tier (on demand):** supporting files (`reference.md`, `scripts/*.py`, etc.) are
   read only when `SKILL.md` explicitly points Claude at them, or executed (scripts) without ever
   entering context (only their stdout does).

> "Not every token in your Skill has an immediate cost. At startup, only the metadata (name and
> description) from all Skills is pre-loaded. Claude reads SKILL.md only when the Skill becomes
> relevant, and reads additional files only as needed."
> — best-practices page

Structuring guidance for large skills (best-practices page):
- **Keep `SKILL.md` under 500 lines**; split overflow into separate files (Claude Code doc
  repeats this as a hard tip: "Keep SKILL.md under 500 lines. Move detailed reference material to
  separate files.")
- **One level deep only** — reference files must link directly from `SKILL.md`. Nested references
  (`SKILL.md` → `advanced.md` → `details.md`) are an anti-pattern: "Claude may partially read
  files when they're referenced from other referenced files... might use commands like `head
  -100` to preview content rather than reading entire files, resulting in incomplete information."
- **Table of contents** at the top of any reference file over 100 lines, so a partial/preview read
  still shows the full scope.
- **Domain-partitioned reference files** (e.g. `reference/finance.md`, `reference/sales.md`)
  rather than generic `doc1.md`, `doc2.md` — keeps unrelated context off the read path entirely.
- Match **degrees of freedom** to task fragility: high-freedom prose for judgment calls, medium
  (parameterized pseudocode) for "preferred pattern, some variation OK," low (exact script
  invocation, "do not modify") for fragile/must-be-consistent operations like DB migrations.

Claude Code-specific mechanics on top of the spec:
- Re-invoking a skill whose rendered content is byte-identical to what's already in context adds
  only a short "already loaded" note, not a duplicate copy (as of v2.1.202+).
- Auto-compaction re-attaches the most-recently-invoked copy of each skill (first 5,000 tokens,
  shared 25,000-token budget across all re-attached skills) after a summary — older/less-recently
  invoked skills can be dropped entirely.
- `claude plugin details <name>` reports both "always-on" (listing) and "on-invoke" (full body)
  projected token costs per component — useful for supskill to self-audit before publishing.

## 3. Plugin structure

`.claude-plugin/plugin.json` is **optional**. If omitted, Claude Code auto-discovers components
from default directory names and derives the plugin name from the install directory. The only
directory rule that matters structurally:

> "The `.claude-plugin/` directory contains the `plugin.json` file. All other directories
> (commands/, agents/, skills/, output-styles/, themes/, monitors/, hooks/) must be at the plugin
> root, not inside `.claude-plugin/`."
> — plugins-reference

### Full `plugin.json` schema

```json
{
  "name": "plugin-name",
  "displayName": "Plugin Name",
  "version": "1.2.0",
  "description": "Brief plugin description",
  "author": { "name": "Author Name", "email": "author@example.com", "url": "https://github.com/author" },
  "homepage": "https://docs.example.com/plugin",
  "repository": "https://github.com/author/plugin",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"],
  "skills": "./custom/skills/",
  "commands": ["./custom/commands/special.md"],
  "agents": ["./custom/agents/reviewer.md"],
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "outputStyles": "./styles/",
  "lspServers": "./.lsp.json",
  "experimental": { "themes": "./themes/", "monitors": "./monitors.json" },
  "dependencies": ["helper-lib", { "name": "secrets-vault", "version": "~2.1.0" }]
}
```

- **Only `name` is required** (kebab-case, no spaces). It drives component namespacing:
  `plugin-dev:agent-creator` for agent `agent-creator` in plugin `plugin-dev`.
- Claude Code **ignores unrecognized top-level fields** (so `plugin.json` can double as an
  npm `package.json` / VS Code extension manifest / MCPB bundle manifest). Wrong-*type* fields
  still fail to load. `claude plugin validate --strict` turns unrecognized-field warnings into
  errors — useful in supskill's CI.
- `defaultEnabled: false` ships the plugin installed-but-off (requires opt-in via
  `claude plugin enable`); useful if supskill's driver script has cost/scope implications.

### Directory layout (default locations)

| Component | Default location |
|---|---|
| Manifest | `.claude-plugin/plugin.json` |
| Skills | `skills/<name>/SKILL.md` |
| Commands (flat, legacy) | `commands/*.md` |
| Agents | `agents/*.md` |
| Output styles | `output-styles/` |
| Hooks | `hooks/hooks.json` |
| MCP servers | `.mcp.json` |
| LSP servers | `.lsp.json` |
| Monitors | `monitors/monitors.json` |
| Executables (added to Bash `PATH`) | `bin/` |
| Default settings | `settings.json` (only `agent` and `subagentStatusLine` keys supported) |

Single-skill shorthand relevant to supskill: **"If a plugin has no `skills/` directory and no
`skills` manifest field, a `SKILL.md` at the plugin root is loaded as a single skill."** In that
layout the frontmatter `name` field is what controls the invocation name — without it, Claude
Code falls back to the install directory name, which for marketplace installs "is a version
string that changes on every update." **Action item: if supskill ships one skill at plugin root,
set `name` explicitly in its frontmatter.**

Path field behavior: `commands`, `agents`, `outputStyles` **replace** the default directory scan
when set; `skills` **adds to** the default `skills/` scan (except the marketplace-root exception
in §4). All custom paths must start with `./` and stay inside the plugin root — **path traversal
(`../shared-utils`) silently fails after install** because only the plugin directory is copied
into the local cache (`~/.claude/plugins/cache`). Cross-plugin file sharing within one
marketplace requires symlinks (dereferenced into the cache at publish time; symlinks pointing
outside the marketplace are dropped for security).

Two path variables matter for a driver script:
- `${CLAUDE_PLUGIN_ROOT}` — absolute path to the plugin's *current* install dir. Changes on every
  update; do not persist state here (old version dir is GC'd ~7 days post-update).
- `${CLAUDE_PLUGIN_DATA}` — persistent dir (`~/.claude/plugins/data/{id}/`) that survives updates;
  correct place for installed deps, caches, or driver-script state. Recommended pattern: diff a
  copy of the bundled manifest (`package.json`, `requirements.txt`, etc.) against the one in
  `CLAUDE_PLUGIN_DATA` on `SessionStart`, reinstalling deps only when they differ.

### `.mcp.json` — standard MCP config format, e.g.:

```json
{
  "mcpServers": {
    "plugin-database": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": { "DB_PATH": "${CLAUDE_PLUGIN_DATA}/data" }
    }
  }
}
```
Not required unless the plugin bundles an MCP server; a skill + agents + driver-script plugin can
skip it entirely.

## 4. Marketplace

`.claude-plugin/marketplace.json` at the marketplace repo root.

### Required schema

```json
{
  "name": "company-tools",
  "owner": { "name": "DevTools Team", "email": "devtools@example.com" },
  "plugins": [
    { "name": "code-formatter", "source": "./plugins/formatter", "description": "...", "version": "2.1.0" },
    { "name": "deployment-tools", "source": { "source": "github", "repo": "company/deploy-plugin" }, "description": "..." }
  ]
}
```

- `name` (marketplace, kebab-case), `owner.name`, `plugins[]` are required.
- Each plugin entry needs `name` + `source` at minimum; `source` is either a relative path
  string (`"./plugins/foo"`, resolved from the marketplace root, must start with `./`, no `..`)
  or an object: `github {repo, ref?, sha?}`, `url {url, ref?, sha?}`,
  `git-subdir {url, path, ref?, sha?}` (sparse clone for monorepos), or
  `npm {package, version?, registry?}`.
- **Reserved marketplace names** (blocked for third parties): `claude-code-marketplace`,
  `claude-code-plugins`, `claude-plugins-official`, `claude-plugins-community`,
  `claude-community`, `anthropic-marketplace`, `anthropic-plugins`, `agent-skills`,
  `anthropic-agent-skills`, `knowledge-work-plugins`, `life-sciences`, `claude-for-legal`,
  `claude-for-financial-services`, `financial-services-plugins`, `first-party-plugins`,
  `healthcare`, plus anything that "impersonates" official names (e.g.
  `official-claude-plugins`). Checked on every load, not just registration.

### User flow

```
/plugin marketplace add owner/repo        # or a git URL, or a local path
/plugin install plugin-name@marketplace-name
```
CLI equivalents: `claude plugin marketplace add <source>`, `claude plugin install <plugin>
[-s user|project|local]`. Scope determines which settings file gets the `enabledPlugins` entry
(`~/.claude/settings.json` for user / `.claude/settings.json` for project, shared via VCS /
`.claude/settings.local.json` for local, gitignored).

### Versioning and the immutable-slug rule

Version resolution order: `plugin.json` `version` → marketplace-entry `version` → git commit SHA
(git-hosted sources only) → `"unknown"` (npm/non-git local). **Whichever value is used becomes
the cache key** that decides whether `/plugin update` has anything to do.

> "If you set `version` in `plugin.json`, you must bump it every time you want users to receive
> changes. Pushing new commits alone is not enough, because Claude Code sees the same version
> string and keeps the cached copy."

The "immutable slug" is the plugin's `name`: it is the stable identifier used in
`enabledPlugins`, `pluginConfigs`, and every `/plugin install` invocation. Changing `name` breaks
every existing install unless the marketplace also declares a top-level `renames` map
(`{"old-name": "new-name-or-null"}`, v2.1.193+) so Claude Code migrates users automatically and
shows a one-line notice. To just relabel the UI without breaking installs, set `displayName`
instead and leave `name` untouched.

### Auto-update patterns

- Users refresh with `/plugin marketplace update [name]` (omit name = all).
- Background auto-update at startup needs git credentials in env (`GITHUB_TOKEN`/`GH_TOKEN`,
  `GITLAB_TOKEN`/`GL_TOKEN`, `BITBUCKET_TOKEN`) since interactive prompts would block startup.
- Release-channel pattern: two marketplace entries pointing at different `ref`/branch of the same
  repo (e.g. `stable` vs `latest`), assigned to different user groups via
  `extraKnownMarketplaces` in managed settings.
- `strict` field on a plugin entry (default `true`) controls whether `plugin.json` is the
  authority for components (merged with marketplace-entry extras) or, if `false`, whether the
  marketplace entry is the *entire* definition (plugin ships raw files only).

## 5. Agent definition files (`agents/*.md`)

Frontmatter — **only `name` and `description` are required**:

| Field | Notes |
|---|---|
| `name` | lowercase+hyphens; what hooks receive as `agent_type` |
| `description` | drives auto-delegation (see below) |
| `tools` | allowlist; omit → inherits everything. `Agent(type1, type2)` restricts which subagents *it* can spawn |
| `disallowedTools` | denylist; applied before `tools` is resolved |
| `model` | `sonnet`/`opus`/`haiku`/`fable`/full ID/`inherit` (default) |
| `permissionMode` | `default`/`acceptEdits`/`auto`/`dontAsk`/`bypassPermissions`/`plan` |
| `maxTurns`, `effort`, `skills` (preload), `mcpServers`, `hooks`, `memory`, `background`, `isolation: worktree`, `color`, `initialPrompt` | see sub-agents doc for each |

> "Claude uses each subagent's description to decide when to delegate tasks... To encourage
> proactive delegation, include phrases like 'use proactively' in your subagent's description
> field."
> — sub-agents doc

**Plugin-shipped agents are restricted for security**: they support `name`, `description`,
`model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills`, `memory`, `background`, and
`isolation` (worktree only) — but **`hooks`, `mcpServers`, and `permissionMode` are silently
ignored** when the agent ships inside a plugin. This directly matters for supskill's agents/*.md:
if any agent needs a `PreToolUse` guard or a scoped MCP server, that config must live in the
plugin's top-level `hooks/hooks.json` / `.mcp.json` instead of the agent's own frontmatter.

Dispatch: Claude compares the task at hand (and the user's phrasing) against every registered
agent's `description`, the same semantic-match mechanism as skill discovery — not a keyword
router. Plugin agents appear in the `@`-mention typeahead under `plugin-name:agent-name`.

## 6. Hooks

Full event catalog (31 events; the plugins-reference table below is the authoritative
Claude-Code-plugin-relevant subset, cross-checked against the dedicated hooks page):

| Event | Fires | Can block? |
|---|---|---|
| `SessionStart` / `Setup` / `SessionEnd` | session lifecycle | no |
| `UserPromptSubmit` / `UserPromptExpansion` | before Claude sees the prompt / before a command expands | yes (exit 2) |
| `PreToolUse` | before a tool call executes | **yes** — 4-way decision (`allow`/`deny`/`ask`/`defer`) + can rewrite input via `updatedInput` |
| `PostToolUse` / `PostToolUseFailure` | after success/failure | no (can rewrite the *output* Claude sees via `updatedToolOutput`) |
| `PostToolBatch` | after a parallel batch resolves, before next model call | yes (exit 2) |
| `PermissionRequest` / `PermissionDenied` | permission dialog / auto-denial | yes / retry-only |
| `Stop` / `SubagentStop` | Claude (or a subagent) finishes responding | **yes — exit 2 prevents stopping and continues the conversation** |
| `StopFailure` | turn ends on API error | no (logging only) |
| `SubagentStart`, `TeammateIdle`, `TaskCreated`, `TaskCompleted` | team/task lifecycle | mixed, see full table in hooks doc |
| `PreCompact` / `PostCompact` | around context compaction | Pre: yes |
| `FileChanged`, `CwdChanged`, `WorktreeCreate`, `WorktreeRemove` | filesystem/env | mixed |
| `ConfigChange`, `InstructionsLoaded` | config/CLAUDE.md reload | Config: yes |
| `Elicitation`, `ElicitationResult` | MCP server requests user input | yes |
| `MessageDisplay`, `Notification` | display-only / side effects | no |

Hook types: `command` (shell), `http` (POST the event JSON), `mcp_tool`, `prompt` (LLM eval),
`agent` (agentic verifier). Plugin hooks configure identically to user hooks, in
`hooks/hooks.json` at the plugin root or inline in `plugin.json`, with `${CLAUDE_PLUGIN_ROOT}`
substituted for script paths.

**Can a hook block/redirect?** Yes, precisely and richly for `PreToolUse` (deny, ask, defer, or
silently rewrite the tool's arguments before it runs) — this is the correct mechanism for
supskill if the driver script needs to intercept or validate specific tool calls deterministically,
rather than relying on the model choosing to comply with prose instructions.

**Can a `Stop` hook chain work?** Yes, confirmed directly in the docs and cross-verified by a
third-party guide:

> "Prevents Claude from stopping, continues the conversation" — exit code 2 behavior on `Stop`.
> Example from the docs: `if [ "$tests_failed" = true ]; then echo "Tests must pass" >&2; exit 2;
> fi`

**Is that advisable for supskill?** The docs present it as a narrow, deterministic guard (e.g.
"don't stop until tests pass"), not a general orchestration primitive — it has no way to inject a
*new* task, only to force one more turn with `additionalContext` as feedback. Using `Stop` to
chain a whole multi-skill workflow would be an abuse of the mechanism: it can't select or invoke a
specific skill, it can only nudge the model to keep going and hope it does the right thing next —
which reintroduces exactly the non-determinism problem covered in §8. If supskill needs guaranteed
sequencing, `PreToolUse`/`PostToolUse` rewriting or an explicit driver-script orchestration layer
outside the hook system is the safer primitive; `Stop` is best reserved for verification gates
("did the required side effect happen"), not as a state machine driver.

## 7. Skill best-practice anti-patterns (Anthropic's own guidance)

From the best-practices page's explicit "Anti-patterns to avoid" section plus scattered
guidance:

- **Windows-style paths** (`scripts\helper.py`) — break cross-platform; always forward slashes.
- **Too many options presented without a default** — "You can use pypdf, or pdfplumber, or
  PyMuPDF..." confuses the model; give one default with an explicit escape hatch instead.
- **Punting error handling to Claude** in bundled scripts instead of handling it in code
  ("Solve, don't punt").
- **"Voodoo constants"** — unexplained magic numbers (`TIMEOUT = 47 # Why 47?`); justify every
  configured value in a comment.
- **Deeply nested references** (§2) — Claude may only partially read a chain of linked files.
- **Time-sensitive content** ("before August 2025, use...") that silently goes stale; put
  deprecated info in a collapsed "old patterns" section instead.
- **Inconsistent terminology** within one skill (mixing "API endpoint"/"URL"/"route").
- **Assuming a package/tool is installed** — state the `pip install` step explicitly; on the
  Claude API (vs. claude.ai) there is *no* runtime package installation or network access at all,
  so this is a hard constraint, not just tidiness.

Anthropic frames the skill body itself as **"a checklist/workflow, not an essay"** implicitly
through the "Use workflows for complex tasks" and "Implement feedback loops" sections: break
multi-step operations into a literal checklist Claude is told to copy into its response and
check off, and pair every fragile operation with a validate → fix → repeat loop. The "Solve,
don't punt" and "degrees of freedom" framing (§2) is the same idea applied to code: for anything
that must not vary (a DB migration, a release script), give an exact command and say "do not
modify"; for a judgment call, give principles and trust the model.

### Testing skills

Evaluation-driven development is the explicitly recommended process, in this order:

1. Run Claude on representative tasks **without** the skill; document the specific gaps.
2. Write 3+ evaluation scenarios that probe exactly those gaps (JSON format: `skills`, `query`,
   `files`, `expected_behavior[]`).
3. Baseline Claude's performance without the skill.
4. Write the minimum instructions that close the gaps and pass the evals.
5. Iterate using a two-Claude loop: "Claude A" (helps author/refine `SKILL.md`) vs. "Claude B" (a
   fresh instance that actually uses the skill on real tasks) — bring Claude B's observed
   failures back to Claude A rather than guessing at fixes.
6. **Test with every model tier you intend to support** — Haiku/Sonnet/Opus have different
   tolerances for terseness vs. explicit guidance.

Claude Code operationalizes step 2–5 as an installable plugin:

> "The `skill-creator` plugin automates the comparison loop inside Claude Code... Test cases:
> stores prompts, input files, and expected behavior in `evals/evals.json`... Isolated runs:
> spawns a subagent per test case... Grading... Benchmark: aggregates pass rate, time, and tokens
> for with-skill versus without-skill... Description tuning: generates should-trigger and
> should-not-trigger prompts, measures the hit rate, and proposes description edits when the
> skill activates on the wrong requests."
> — `/plugin install skill-creator@claude-plugins-official`,
> [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)

This is directly useful for supskill: it gives a concrete, official tool for tuning the skill's
`description` against false-positive/false-negative triggering before publishing — the exact
failure mode the controllability critique in §8 complains about.

### Guidance on skills that orchestrate other skills

There is **no dedicated Anthropic pattern or example for a skill whose job is to orchestrate
other skills**. The closest official mechanisms:

- **Skill stacking**: typing `/code-review /fix-issue 123` in one message loads both named skills
  and passes the trailing text as `$ARGUMENTS` to each (up to 6 total, stops at the first
  non-inline-invocable token). This is a *user-authored* multi-skill invocation, not one skill
  programmatically invoking another.
- **`context: fork` + `agent:`**: a skill can hand its own body off as the prompt for a forked
  subagent, optionally a *custom* subagent whose own markdown body could itself reference other
  skills by name in prose — but this is prose-level delegation, evaluated by the same semantic
  judgment as top-level discovery, not a guaranteed call.
- **The `Skill` tool** exists and can be permission-scoped (`Skill(name)` allow/deny rules), which
  means an agent *can* be given/denied the ability to invoke skills as a tool call — but nothing
  in the docs describes a skill's own markdown instructing Claude to "call the Skill tool with
  name=X" as a documented, reliable pattern. It would work the same way any tool-use instruction
  in a prompt works: probabilistically, subject to the model actually choosing to comply.

**Conclusion for supskill: there is no supported, deterministic "skill A invokes skill B"
primitive.** The only deterministic composition points are (a) hooks intercepting tool calls
around whatever skill/agent runs, and (b) a driver script that is itself invoked as a tool
(Bash/script execution) and does real orchestration outside the LLM's decision loop. Anything
that must reliably happen in sequence belongs in the driver script or in hook logic, not in
skill-to-skill prose delegation.

## 8. Reliability of skill invocation — the controllability critique

Question 8 asked for an honest read of paddo.dev's "Claude Skills: The Controllability Problem."
This is **not an Anthropic source** — treat it as one practitioner's opinion, cross-checked
against what the official docs actually confirm.

**The critique, in its own words:**

> "Claude decides using its own semantic understanding of your request - there's no algorithmic
> matching, it's LLM reasoning about whether your intent matches a skill description."

> "Can't force-invoke: You need architectural analysis right now, but Claude doesn't think your
> question matches the skill description... No visibility into decisions: Claude silently
> chooses when to load skill instructions."

> "The controllability problem is particularly acute for workflow orchestration: multi-step
> processes needing explicit sequencing (build → test → deploy). Semantic triggering works for
> context selection. Explicit controls matter for workflow orchestration."

> Verdict: "Skills work for large monorepos requiring progressive disclosure but are problematic
> for engineering workflows needing predictability... Treat Claude as a tool that needs explicit
> controls, not magic that guesses your intent."

**How much of this still holds, checked against the current official docs (2026-07-12):**

- **Largely still true and confirmed by Anthropic's own docs**: auto-invocation is genuinely
  semantic-judgment-based, not algorithmic ("Claude uses each subagent's/skill's description to
  decide"). There is no documented way to force Claude to select skill X with certainty short of
  the user typing `/skill-name` directly. Nothing in the docs contradicts "no algorithmic
  matching."
- **Partially addressed since the critique was written**: the critique's own "Later updates"
  note is accurate — Claude Code now ships explicit, deterministic controls the article was
  asking for: `disable-model-invocation: true` (user-only, hard block on model triggering),
  `user-invocable: false` (Claude-only), per-skill `Skill(name)` allow/deny permission rules, and
  `skillOverrides` (`"off"` fully hides a skill from Claude, `"name-only"` reduces its context
  footprint). These are real force/disable controls, contradicting the article's "you still can't
  force-invoke a skill or disable one for a session" as currently written — that line is now
  stale relative to the docs at hand.
  - Caveat: these controls are all **binary, author-set-in-advance** switches (in frontmatter, or
    a settings override the *user* toggles). They are not a **runtime, conditional "invoke skill
    X now, deterministically, based on this specific tool-call outcome"** mechanism. That gap —
    no deterministic *conditional* trigger — is real and unaddressed. The article's deeper
    architectural point (semantic triggering ≠ workflow orchestration) stands even where its
    specific "can't disable" claim is now outdated.
- **The one solid, load-bearing point for supskill**: skills and hooks solve different problems.
  Skills inject *judgment and context* (prose, reference material) subject to the model's
  discretion. Hooks (specifically `PreToolUse`/`PostToolUse`/`Stop` with exit codes) are the only
  Claude Code primitive that is actually deterministic — they run as real code before/after real
  tool calls, independent of whether the model "feels like" cooperating. A driver script invoked
  from an agent, or triggered by a hook, is likewise deterministic. **If supskill's workflow has a
  hard ordering requirement, put the ordering in the driver script or hooks, and use the skill
  only for the parts that genuinely benefit from LLM judgment** (this is consistent with, and
  reinforces, Anthropic's own "degrees of freedom" guidance in §7 — low-freedom, must-not-vary
  steps get an exact script; high-freedom steps get prose).

## Implications for supskill

1. **Frontmatter validation to build/test for**: `name` ≤ 64 chars, lowercase+hyphens only, no
   `anthropic`/`claude` substrings; `description` non-empty, ≤ 1024 chars, third person, states
   both *what* and *when*. Add a CI/lint step that checks these before every marketplace push.
2. **Decide the invocation model up front** for each skill: pure reference skill (default, both
   invoke) vs. side-effecting action (`disable-model-invocation: true`, user-only) vs. background
   knowledge (`user-invocable: false`). Don't leave supskill's driver-triggering skill on default
   auto-invoke if it has side effects users should control the timing of.
3. **Any ordering guarantee the driver script needs must live in the driver script or in
   `PreToolUse`/`PostToolUse` hooks — not in skill prose telling Claude to "then invoke skill Y."**
   There is no supported deterministic skill-to-skill call.
4. **Ship as a single-skill-plus-agents plugin without a `skills/` subdirectory only if you
   explicitly set `name` in the root `SKILL.md` frontmatter** — otherwise the invocation name
   drifts with every marketplace update (it falls back to the version-stamped cache directory
   name).
5. **Plugin-shipped agents cannot carry `hooks`, `mcpServers`, or `permissionMode`** — any
   PreToolUse guard the agents need must be declared at the plugin level
   (`hooks/hooks.json`), not in `agents/*.md` frontmatter.
6. **Use the `skill-creator` plugin (`claude-plugins-official`) during development** to build
   `evals/evals.json` test cases and get should-trigger/should-not-trigger hit-rate tuning on the
   `description` before publishing — this is Anthropic's own answer to the controllability
   critique, and it's directly installable now.
7. **Version supskill explicitly** (`plugin.json` `version`, semver) rather than relying on commit
   SHA versioning, since it's a public marketplace release with real users — but remember to bump
   it on every release or updates silently no-op.
8. **Reserve the marketplace name check** — confirm supskill's chosen marketplace `name` isn't in
   the reserved list (§4) and doesn't read as an official-sounding name.
9. **Keep `SKILL.md` under 500 lines, one reference-hop deep**, and put anything driver-script
   related in `scripts/` (executed, zero context cost) rather than inlined in the skill body.
10. **If the driver script needs persistent local state** (installed deps, caches), key it off
    `${CLAUDE_PLUGIN_DATA}`, not `${CLAUDE_PLUGIN_ROOT}` — the latter is wiped/rotated on every
    plugin update.
