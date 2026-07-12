---
title: Claude Code Context Mechanics — Verified Facts for Bounded-Context Orchestration
date: 2026-07-12
sources_count: 9
status: draft
---

# Claude Code context mechanics

Research for **supskill**, a Claude Code plugin whose purpose is context boundary management
across a long multi-sprint development pipeline. All facts below are sourced primarily from
official Anthropic docs (`code.claude.com/docs/en/*`, which is where `docs.claude.com` 301-redirects
for Claude Code pages) and the `anthropics/claude-code` GitHub issue tracker. Docs were fetched
live on 2026-07-12; version numbers embedded in quotes (e.g. "as of v2.1.198") are the docs' own
version annotations, not my inference.

---

## Verified facts

### 1. Subagent context isolation

**Isolation is real and by design.** A subagent does not inherit the parent's conversation:

> "Each subagent starts with a fresh, isolated context window. It doesn't see your conversation
> history, the skills you've already invoked, or the files Claude has already read. Claude
> composes a delegation message that summarizes the task, and the subagent works from there."
> — [Subagents](https://code.claude.com/docs/en/sub-agents), "Manage subagent context › What loads at startup"

The one exception is a **fork** (see §5 below), which inherits the full parent conversation instead
of starting fresh.

**What a non-fork subagent's initial context actually contains** (exact list from the docs):

- System prompt: the agent's own prompt + environment details Claude Code appends — **not** the
  full Claude Code system prompt.
- Task message: the delegation prompt Claude writes when handing off work.
- CLAUDE.md and memory: every level of the memory hierarchy the main conversation loads
  (`~/.claude/CLAUDE.md`, project rules, `CLAUDE.local.md`, managed policy files) — **except**
  the built-in `Explore` and `Plan` agents, which skip this.
- Git status: a snapshot taken at the start of the parent session (skipped if not a git repo, if
  `includeGitInstructions` is `false`, or by Explore/Plan).
- Preloaded skills: full content of any skill named in the agent's `skills` frontmatter field.

Source: [Subagents § Manage subagent context](https://code.claude.com/docs/en/sub-agents#manage-subagent-context)

**What returns to the parent — only the final result, plus a small metadata trailer:**

> "Only the subagent's final text response comes back to your context, plus a small metadata
> trailer with token counts and duration. The subagent read 6,100 tokens of files. You got a
> 420-token result. That's the context savings."
> — [Explore the context window](https://code.claude.com/docs/en/context-window)

Subagent transcripts persist independently and are unaffected by main-conversation compaction:

> "Main conversation compaction: when the main conversation compacts, subagent transcripts are
> unaffected. They're stored in separate files."
> — [Subagents § Resume subagents](https://code.claude.com/docs/en/sub-agents#resume-subagents)

**Subagents DO see CLAUDE.md, skills, and MCP tools** (except Explore/Plan skip CLAUDE.md/git):

> "Subagents inherit the internal tools and MCP tools available in the main conversation by
> default." — [Subagents § Available tools](https://code.claude.com/docs/en/sub-agents#available-tools)

But four tools are withheld from subagents regardless of what `tools:` frontmatter lists, because
they depend on main-session UI/state:

> "The following tools depend on the main conversation's UI or session state and aren't available
> to subagents, even when listed in the `tools` field: `AskUserQuestion`, `EnterPlanMode`,
> `ExitPlanMode` (unless the subagent's permissionMode is `plan`), `ScheduleWakeup`,
> `WaitForMcpServers`."
> — [Subagents § Available tools](https://code.claude.com/docs/en/sub-agents#available-tools)

**No message from any agent counts as user approval**, and no agent can rewrite a subagent's own
permission config — a hard boundary worth building on:

> "Two limits still hold regardless of who sent the message: no message from any agent counts as
> your approval for a pending permission prompt, and no agent message can change a subagent's
> permission settings, CLAUDE.md, or configuration. Only the permission system or your own
> messages can grant approval."
> — [Subagents § Resume subagents](https://code.claude.com/docs/en/sub-agents#resume-subagents)

### 2. Nested subagents — RESOLVED, contradicts the stale GitHub issue

**Current status (docs, v2.1.172+): nested subagent spawning is supported**, with a fixed,
non-configurable depth cap of 5:

> "As of Claude Code v2.1.172, a subagent can spawn its own subagents. Use this when a delegated
> task itself splits into parallel subtasks... Only the top-level subagent's summary returns to
> you... Depth is counted as the number of subagent levels below the main conversation, regardless
> of whether each level runs in the foreground or background. A subagent at depth five doesn't
> receive the Agent tool and can't spawn further. The limit is fixed and not configurable."
> — [Subagents § Spawn nested subagents](https://code.claude.com/docs/en/sub-agents#spawn-nested-subagents)

Background-subagent depth is pinned at spawn time and does not change on resume:

> "As of Claude Code v2.1.187, a background subagent's depth is fixed when it is first spawned,
> and resuming it later doesn't change that depth."
> — same section

To prevent a specific subagent from spawning children: omit `Agent` from its `tools` list or add
it to `disallowedTools`.

**GitHub issue #60763** ("[FEATURE] Subagents have no Agent/Task tool — recursive/nested subagent
dispatch impossible") is still **open**, filed **2026-05-20**, labeled `stale`, with **no
maintainer comment** confirming a fix — it predates the v2.1.172 change documented above and
is now stale/superseded by the docs.
Source: [github.com/anthropics/claude-code/issues/60763](https://github.com/anthropics/claude-code/issues/60763)

I could not verify (not checked) issues #4182, #19077, #61993, or the SDK-side issues #189/#172
mentioned by other search hits — treat those as unverified until read directly if they matter to
supskill's design.

### 3. Headless mode (`claude -p`)

**Fresh context per invocation, unless you explicitly resume.** Each `claude -p` call without
`--continue`/`--resume` starts a new session. With those flags it appends to or resumes an
existing session transcript (see §7).

**User-invoked skills and slash commands DO work in `-p` mode** — confirmed directly:

> "User-invoked skills and custom commands work in `-p` mode: include `/skill-name` in the prompt
> string and Claude Code expands it before running. Built-in commands that only run in the
> terminal interface, such as `/login`, aren't available in `-p` mode. `/model`, `/effort`,
> `/fast`, `/color`, and `/rename` accept the value as an argument... and `/mcp` with no argument
> prints a text summary of server status."
> — [Run Claude Code programmatically](https://code.claude.com/docs/en/headless)

**`--bare`**: skips auto-discovery of hooks, skills, plugins, MCP servers, auto memory, and
CLAUDE.md; loads only what you pass explicitly via flags. Recommended for CI/scripts, becoming
the default for `-p` in a future release. Also skips OAuth/keychain — needs `ANTHROPIC_API_KEY`
or `apiKeyHelper`. Quote:

> "Add `--bare` to reduce startup time by skipping auto-discovery of hooks, skills, plugins, MCP
> servers, auto memory, and CLAUDE.md. Without it, `claude -p` loads the same context an
> interactive session would."

**`--allowedTools`**: auto-approves listed tools (permission-rule syntax, e.g.
`"Bash(git diff *)"`). **`--permission-mode`**: sets a baseline (`dontAsk`, `acceptEdits`, etc.)
for the whole run instead of listing individual tools.

**`--output-format`**: `text` (default) / `json` (structured, includes `session_id`,
`total_cost_usd`, per-model cost breakdown, optional `structured_output` when paired with
`--json-schema`) / `stream-json` (newline-delimited streaming events).

**`--append-system-prompt`**: adds instructions on top of the default system prompt (vs.
`--system-prompt` which fully replaces it).

**`--resume` / `--continue` / `--fork-session`**: `--continue` resumes the most recent session in
the current directory; `--resume <id>` resumes a specific one; `--fork-session` (combined with
`--continue`/`--resume`) copies history into a **new** session ID, leaving the original untouched
— this is how `/branch` works under the hood.

**Background-task gotchas, exact wording:**

> "If Claude starts a background Bash task during a `claude -p` run... that shell is terminated
> about five seconds after Claude has returned its final result and stdin has closed... Before
> v2.1.163, a never-exiting background process would hold the `claude -p` invocation open
> indefinitely."
>
> "Background subagents and workflows are exempt from the five-second grace because their result
> is part of the final output, so `claude -p` waits for them to complete. From v2.1.182, that wait
> is capped at ten minutes by default so a stuck background agent cannot hold the process open
> indefinitely. Adjust the cap with `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`, or set it to `0` to
> wait without a limit."
> — [Run Claude Code programmatically § Background tasks at exit](https://code.claude.com/docs/en/headless#background-tasks-at-exit)

Other gotchas confirmed in the same doc: piped stdin capped at 10MB (v2.1.128+, exits non-zero if
exceeded); an invalid `--json-schema` now errors loudly (v2.1.205+, previously silently ignored).

### 4. Auto-compaction

**Trigger condition** — not a single fixed percentage; it depends on model and session type:

> "When `CLAUDE_CODE_AUTO_COMPACT_WINDOW` is set, in cloud sessions, and on Sonnet 4.6 and Opus
> 4.6 without extended context, [compaction happens] at the 200K boundary by default. On Sonnet 5,
> proactive compaction applies at the model's default threshold. In other cases, such as a local
> session on Opus 4.8, auto-compaction triggers when the conversation reaches the model's context
> limit."
> — [Environment variables](https://code.claude.com/docs/en/env-vars), `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` entry

`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (1–100) can only **lower** the threshold to compact earlier — it
cannot raise it or disable compaction. Applies to both main conversations and subagents.

**What survives compaction — exact table** from
[Explore the context window § What survives compaction](https://code.claude.com/docs/en/context-window#what-survives-compaction):

| Mechanism | After compaction |
|---|---|
| System prompt and output style | Unchanged; not part of message history |
| Project-root CLAUDE.md and unscoped rules | Re-injected from disk |
| Auto memory | Re-injected from disk |
| Rules with `paths:` frontmatter | Lost until a matching file is read again |
| Nested CLAUDE.md in subdirectories | Lost until a file in that subdirectory is read again |
| Invoked skill bodies | Re-injected, capped at 5,000 tokens/skill and 25,000 tokens total; oldest dropped first |
| Hooks | Not applicable; hooks run as code, not context |
| **Skill descriptions listing** (the index Claude uses to decide what it *could* invoke) | **NOT re-injected** — "Only skills you actually invoked are preserved." |

General mechanism, plain language:

> "It clears older tool outputs first, then summarizes the conversation if needed. Your requests
> and key code snippets are preserved; detailed instructions from early in the conversation may
> be lost."
> — [How Claude Code works § When context fills up](https://code.claude.com/docs/en/how-claude-code-works#when-context-fills-up)

**Compaction cannot be fully disabled** — I found no documented flag to turn it off entirely; the
only lever is `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, which only moves the threshold earlier. If a
single file/output is so large that context refills immediately after each summary attempt,
Claude Code **stops** auto-compacting after a few tries and surfaces a "thrashing" error instead
of looping forever (see [troubleshooting doc](https://code.claude.com/docs/en/troubleshooting#auto-compaction-stops-with-a-thrashing-error), not independently fetched but referenced by the how-claude-code-works page).

**Why compaction is an inferior substitute for a real context boundary** (synthesis, not a quote):
compaction is lossy and content-priority-based, not scope-based — it keeps "your requests and key
code snippets" by heuristic, and explicitly drops path-scoped rules, nested CLAUDE.md, and the
skill-description index. A subagent boundary, by contrast, is a clean room: nothing crosses except
what the parent explicitly summarized into the delegation prompt and what the child explicitly
returns. Compaction is "the same conversation, smaller"; a subagent is "a new conversation,
scoped."

### 5. `/clear` vs. new process vs. subagent — what actually differs

> "`/clear`: start fresh with an empty context. The previous conversation is saved and resumable."
> — [Manage sessions § Manage context within a session](https://code.claude.com/docs/en/sessions#manage-context-within-a-session)

- **`/clear`**: same session storage lineage is discarded from *active* context but the prior
  transcript remains on disk and resumable via `/resume`; you get a genuinely empty context window
  for the next turn, in the same terminal/process.
- **A new process** (`claude` invoked fresh in the same directory): also starts empty, but is a
  wholly separate OS process with its own session ID from the start — no relationship to a prior
  session unless you explicitly `--continue`/`--resume`.
- **A subagent**: does NOT clear or replace the parent's context — the parent conversation keeps
  accumulating in parallel. The subagent gets its own separate context window that exists only for
  the duration of that delegation (unless resumed later, see §1), and only its final result is
  merged back into the parent's still-intact context.

Also relevant — a **fork** is a fourth option not covered by the "3 vs 1" framing:

> "A fork is a subagent that inherits the entire conversation so far instead of starting fresh...
> The fork's own tool calls still stay out of your conversation and only its final result comes
> back, so your main context window stays clean."
> — [Subagents § Fork the current conversation](https://code.claude.com/docs/en/sub-agents#fork-the-current-conversation)

A fork requires `CLAUDE_CODE_FORK_SUBAGENT=1` (or the `/fork` command, enabled by default since
v2.1.161) and **cannot spawn further forks** (though it can spawn other subagent types).

### 6. Can a subagent or headless session ask the user a question? — NO, confirmed two ways

**(a) Subagents are explicitly denied the `AskUserQuestion` tool**, regardless of `tools:`
frontmatter (quoted in full in §1 above) — this is documented, current behavior, not a bug report.

**(b) In headless/no-TTY mode, `AskUserQuestion` does not block for input — it auto-resolves with
empty answers.** This is confirmed by a **closed-as-not-planned** GitHub issue, meaning Anthropic
reviewed it and declined to change it (i.e., this is intentional/expected, not a defect awaiting a
fix):

> Issue #50728, "AskUserQuestion auto-resolves with empty answers in headless/no-TTY mode (Python
> Agent SDK)" — **Closed: not planned**, opened 2026-04-19.
> "When using the Python Agent SDK... in a headless/no-TTY environment..., `AskUserQuestion`
> auto-resolves immediately with empty answers: 'User has answered your questions: . You can now
> continue with the user's answers in mind.' The tool completes in ~37ms without any opportunity
> for the integration to collect answers from the user, even when a `can_use_tool` callback or
> `PreToolUse` hook is registered."
> — [github.com/anthropics/claude-code/issues/50728](https://github.com/anthropics/claude-code/issues/50728)

The only documented workaround is a `PreToolUse` hook that denies the `AskUserQuestion` call
outright (`permissionDecision: "deny"`) so it never resolves silently — but the issue reporter
notes this loses conversational continuity: "the answer arrives as a fresh prompt rather than a
tool result."

**(c) Interactive-mode nuance** (not headless, but relevant to escalation design): even in a live
terminal session, `AskUserQuestion` now has an idle auto-continue timeout as of v2.1.198/2.1.200 —
by default there's no timeout, but `askUserQuestionTimeout` can be set to `60s`/`5m`/`10m`, after
which "the dialog closes on its own: it submits any options you'd already selected and tells
Claude you may be away from your keyboard, so Claude proceeds on its own judgment." Permission
prompts (including plan approval) are explicitly exempt from this auto-resolve behavior. Source:
[Tools reference, `AskUserQuestion` row](https://code.claude.com/docs/en/tools-reference).

**Design implication**: there is no supported HITL channel from inside a subagent, a background
teammate, or a headless run. Any escalation-to-human design for supskill must either (1) run the
escalating step as the interactive main session (not a subagent/headless run), or (2) implement
its own out-of-band notification (e.g., write a file/exit with a specific status the orchestrating
human or wrapper script polls for), not rely on `AskUserQuestion` surviving a headless boundary.

### 7. Session resume — scope rules

> "Sessions created with `claude -p` or the Agent SDK do not appear in the session picker, but you
> can still resume one by passing its session ID to `claude --resume <session-id>`. Run this from
> the directory the session was started in: session ID lookup is scoped to the current project
> directory and its git worktrees, so a session created elsewhere reports 'No conversation found
> with session ID: <session-id>'."
> — [Manage sessions § Resume a session](https://code.claude.com/docs/en/sessions#resume-a-session)

- `claude --continue`: resumes most recent session in current directory.
- `claude --resume`: opens interactive picker (scoped to current worktree by default; `Ctrl+W`
  widens to all worktrees of the repo, `Ctrl+A` to all projects on the machine).
- `claude --resume <name-or-id>`: resumes directly on exact match; ambiguous name opens the
  picker pre-filled (CLI) or errors (the in-session `/resume <name>` slash form).
- Transcripts stored at `~/.claude/projects/<project>/<session-id>.jsonl` (path-derived from
  working directory), 30-day retention by default (`cleanupPeriodDays`), configurable location via
  `CLAUDE_CONFIG_DIR`.
- Resuming a resumed/failed/completed **subagent** via `SendMessage` re-marks it as running under
  the *same agent ID* (as of v2.1.205; earlier versions kept showing stale status).
- v2.1.199+: `SendMessage` verifies a name still points to the agent you reached earlier in *this*
  conversation, refusing to deliver to a same-named agent that has since been replaced; this check
  resets on `/clear`.

### 8. Agent teams — the closest thing to a "Workflow tool" for bounded-context orchestration

There is no separate "Workflow tool" documented by that name for end users; the relevant primitive
is **agent teams** (experimental, opt-in via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`). Key facts
for supskill's design:

> "Unlike subagents, which run within a single session and can only report back to the main agent,
> you can also interact with individual teammates directly without going through the lead."
> — [Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams)

- Each teammate is "a full, independent Claude Code session" with its own context window; **the
  lead's conversation history does NOT carry over** to a spawned teammate (same isolation
  guarantee as subagents) — only the spawn prompt does.
- Communication is via a **mailbox** (`SendMessage`) and a **shared task list** with file-locked
  claiming; the lead does not need to poll.
- **No nested teams**: "teammates cannot spawn their own teammates. Only the lead can manage the
  team." This is a harder limit than the subagent depth-5 cap — it's depth-1, fixed.
- **No background subagents from in-process teammates**: a teammate's own subagents run in the
  foreground only, "because a teammate's background work can't outlive the lead's process."
- **Permission bubbling and consent boundary, explicit and load-bearing**: "A teammate cannot
  approve a permission prompt or supply consent on your behalf, and a teammate that was denied an
  action cannot relay it to another teammate to bypass the check." Teammate permission prompts
  always bubble up to the lead session for a human (or the lead's own judgment) to resolve.
- **One team per session, lead is fixed for the session's lifetime** — no promotion, no transfer.
- Token cost: "significantly more" than subagents; roughly linear per active teammate, and ~7x a
  standard session when teammates run in plan mode (per the [costs page](https://code.claude.com/docs/en/costs#agent-team-token-costs)).
- Session-resumption limitation: `/resume`/`/rewind` do **not** restore in-process teammates —
  the lead may try to message teammates that no longer exist after a resume.

---

## Contested / stale claims

| Claim | Verdict | Why |
|---|---|---|
| "Subagents cannot spawn nested subagents" (GitHub issue #60763, blog posts referencing it, and search-result summaries of issues #19077/#61993) | **Stale as of docs dated for v2.1.172+** | The official [Subagents doc](https://code.claude.com/docs/en/sub-agents#spawn-nested-subagents) explicitly documents nested spawning with a fixed depth-5 cap, dated to v2.1.172. Issue #60763 remains open and labeled `stale` with zero maintainer confirmation of a fix, so it looks like the docs shipped the feature without the tracking issue being closed — trust the docs over the open issue. |
| "`claude -p` skills/slash commands don't work in headless mode" (a plausible-sounding assumption, not something I found asserted anywhere, but worth flagging since it's a common misconception) | **False** | Directly contradicted by the headless doc: "User-invoked skills and custom commands work in `-p` mode... Claude Code expands it before running." Only *terminal-only* built-ins like `/login` are excluded. |
| "AskUserQuestion just times out silently and Claude waits" in headless mode | **Wrong framing** | It does not wait/time out — it resolves **immediately** (~37ms per the reporter) with empty answers, and Anthropic closed the report "not planned," i.e., confirmed as intended. Don't design around it eventually blocking; design around it firing instantly with nothing. |
| Blog-sourced numbering like "Claude Code Nested Sub-Agents: 5 Levels Deep" (ofox.ai) | **Directionally correct, unverified as primary source** | The "5 levels" figure matches the official doc's depth-5 cap, so the blog's headline number is corroborated, but I did not independently vet the rest of that post's claims (token math, "3 pitfalls") — treat only the depth number as confirmed, not the rest of the article. |
| A dedicated "Workflow tool" exists as a named, documented primitive | **Not found** | I searched for this and found no `code.claude.com` page or tool named "Workflow." The closest matches are **agent teams** (multi-session, mailbox-based) and the `Agent`/Task tool for subagents. If the team-lead has a specific "Workflow tool" reference in mind (e.g., an internal/beta feature, or the generic `TaskCreate`/`TaskList`/`TaskUpdate` todo-list tools visible in this very session's deferred-tool list), it should clarify — I did not find public docs for anything called exactly "Workflow tool." |

---

## Implications for supskill

1. **Treat subagents as the real context-boundary primitive, not `/clear` or compaction.**
   Compaction is lossy-by-heuristic and keeps skill-description index entries out on purpose;
   `/clear` still lives in the same process/session lineage. A subagent (or fork, if inheritance is
   wanted) is the only mechanism with a documented, enumerable "what crosses the boundary" contract
   (delegation prompt in, final text + metadata trailer out).

2. **Design sprint boundaries as subagent (or headless `-p`) invocations with explicit
   hand-off prompts**, not as `/compact` checkpoints. Since path-scoped rules and nested CLAUDE.md
   don't survive compaction but do reload on file-read, and skill-description listings never
   reload post-compact, any pipeline that leans on compaction to "start a new sprint" will silently
   lose skill discoverability and scoped rules — a correctness risk supskill should design away from,
   not paper over.

3. **The nested-subagent depth-5 cap is real and fixed (not configurable)** — any supskill
   orchestration pattern that plans on recursive divide-and-conquer must budget for at most 5
   levels below the main conversation, and depth is pinned at spawn time even across resume. Build
   the "fan-out" primitive to flatten work rather than assuming arbitrary recursion.

4. **There is no supported HITL channel inside a subagent, background teammate, or headless run.**
   `AskUserQuestion` is stripped from subagents outright and auto-resolves empty in headless mode
   (confirmed via a "closed: not planned" issue, i.e., intentional). Any supskill escalation design
   needs an out-of-band signal — e.g., a sentinel file, a specific exit code/status field in
   `--output-format json`, or keeping the escalating turn on the interactive main session — rather
   than assuming a prompt can "wait for the human" from inside delegated work.

5. **`--bare` is the correct default for reproducible, scripted supskill pipeline stages.** It skips
   hooks/skills/plugins/MCP/auto-memory/CLAUDE.md discovery so a teammate's local config can't leak
   into a CI run; pass only what's needed via `--append-system-prompt`, `--settings`, `--mcp-config`,
   `--agents`. Anthropic is moving toward `--bare` as the `-p` default, so opting in early is future-proof.

6. **Background subagent/workflow waits in headless mode are capped at 10 minutes by default**
   (`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`, v2.1.182+). Any supskill stage that spawns a long-running
   background subagent from a `claude -p` invocation must either raise this ceiling explicitly or
   design the stage to poll/resume rather than block a single `-p` call past 10 minutes.

7. **Session-ID resume is scoped to project directory + its git worktrees** — a `claude -p`
   session started in one directory cannot be resumed by ID from an unrelated directory. If
   supskill's sprint pipeline moves between worktrees, it must track (worktree, session-id) pairs
   explicitly rather than assuming a global session namespace.

8. **Agent teams add a second, heavier isolation primitive with a stricter no-nesting rule and
   built-in consent boundary** (teammates literally cannot relay approval). If supskill needs
   peer-to-peer coordination between sprint workers (not just fan-out/fan-back), agent teams are
   the right primitive — but budget ~7x token cost in plan-mode-heavy configurations, and don't
   rely on `/resume` to restore in-process teammates after interruption.

9. **A "fork" (`CLAUDE_CODE_FORK_SUBAGENT=1` or `/fork`) is a distinct fourth primitive** worth
   naming explicitly in supskill's design vocabulary — it inherits full context (cheap via shared
   prompt cache) but forfeits isolation, and cannot itself spawn further forks. Useful for "try N
   variations from the same checkpoint," not for boundary enforcement.

10. **`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` cannot disable compaction, only move it earlier** — supskill
    cannot rely on an environment variable to prevent an in-flight stage from being silently
    summarized. If a stage's correctness depends on verbatim history, that stage must be sized
    to fit comfortably under the model's context limit or split into subagent-delegated chunks,
    not exempted from compaction.

---

## Open questions / not independently verified

- Whether teammates (agent-team members) are also denied `AskUserQuestion` — the agent-teams doc
  didn't state this explicitly; only the subagents doc did. Worth a follow-up fetch of
  `tools-reference` filtered for team-specific restrictions if this matters to the design.
- The exact content of GitHub issues #4182, #19077, #61993, and the SDK issues #189/#172 — only
  read via search-result summaries, not fetched directly.
- Whether there is an internal/beta "Workflow tool" the team lead may have encountered elsewhere
  (e.g., a private preview) — I found no public doc page for it under that name.
