# fixture-repo — Backlog 01: greeter

**Date:** 2026-07-17 · Legend: points = Fibonacci · pri = MoSCoW (M/S/C/W) · status ☐ todo / ☑ done

A throwaway two-epic backlog for supskill's own end-to-end validation (SK-070). It has no other
purpose: every story is deliberately tiny so a real, gated `supskill` run through both sprints stays
cheap.

## Summary — epics, in recommended build order

| # | Epic | Pts | Pri |
|---|------|-----|-----|
| **E1** | Greeting core | 3 | M |
| **E2** | Greeting CLI | 3 | M |

**Total: 6 pts.**

## E1 — Greeting core (3 pts)

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-001 | `greet(name: str) -> str` returns `"Hello, <name>!"`; raises `ValueError` on an empty or whitespace-only name. | 2 | M | ☐ |
| SK-002 | `greet` strips surrounding whitespace from `name` before formatting. | 1 | M | ☐ |

## E2 — Greeting CLI (3 pts)

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-003 | A `greet` CLI script takes one positional `name` argument and prints `greet(name)` to stdout. | 2 | M | ☐ |
| SK-004 | The CLI exits 1 and prints a usage error to stderr when `name` is missing. | 1 | M | ☐ |

## Recommended first sprint

**S1 — Greeting core (E1, 3 pts).** E2 depends on it: the CLI wraps `greet`.
