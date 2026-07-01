# Architecture

This repo documents the actual state of a global Claude Code configuration (`~/.claude/`) after auditing what already existed versus what a much larger original request asked for. Most of that request was already solved by existing plugins/MCP servers or by capabilities baked into the harness itself. This doc describes what's real, not what was originally proposed.

## What's installed and its role

| Component | Type | Role |
|---|---|---|
| Serena | MCP (plugin) | LSP-backed semantic code navigation — symbol find/rename/insert across 30+ languages, used instead of reading whole files. |
| Context7 | MCP (plugin) | Resolves a library name to current, version-specific docs — used before assuming an API's shape. |
| arxiv-mcp-server | MCP | Paper search/read against arXiv. The only research-paper MCP in this setup — see `DECISIONS.md` for why Semantic Scholar/OpenAlex/Papers-with-Code were not added. |
| Firecrawl | Skills (CLI-based, no MCP) | Web crawling/scraping. |
| chrome-devtools-mcp | MCP (plugin) | Browser automation/debugging. |
| github MCP | MCP (plugin) | GitHub operations over `api.githubcopilot.com`, authenticated via `GITHUB_PERSONAL_ACCESS_TOKEN` (reused from the existing `gh` CLI token) set in `~/.claude/settings.json`'s `env` key. |
| ast-grep | CLI (brew) + MCP (`ast-grep/ast-grep-mcp`, user-scope) | Structural/pattern-based code search and rewrite, available both as a Bash command and as first-class MCP tools. |
| fd, tree-sitter | CLI (brew) | Fast filename search and grammar-level parsing. No MCP wrapper — plain CLI usage is sufficient for both. |
| superpowers, ponytail, caveman | Skills/hooks (plugins) | Process discipline (brainstorming/planning/TDD/debugging gates), lazy/minimal implementation bias, terse communication mode. |
| Native `Task*` tools | Harness-native | AI-assisted task planning — makes a separate "Task Master" tool redundant. |
| `cross-domain-brainstorm` | Skill (this repo's addition) | See below. |

## How retrieval actually works

There is no custom "context retrieval engine." The harness's own system prompt already instructs spawning `Explore` subagents for broad codebase discovery instead of recursively reading files, and Serena provides symbol-level lookup for anything code-specific. `rg`, `ast-grep`, and `fd` fill in for text search, structural search, and filename search respectively. This is documented behavior, not new infrastructure — see the "Retrieval & Tool Discipline" block in `~/.claude/CLAUDE.md`.

## How model routing actually works

The only real, available lever is the `model` parameter on the Task/Agent tool when dispatching subagents (haiku for formatting/simple work, sonnet/opus for implementation/debugging/architecture). **The main session's own active model cannot be switched automatically mid-conversation** — there is no hook or API for a running session to reclassify a prompt and swap its own model. This is a hard platform limitation, not a gap left to close later.

## How cross-domain brainstorming fits in

`~/.claude/skills/cross-domain-brainstorm/SKILL.md` is a narrowly-scoped, deliberately-invoked technique (`/cross-domain-brainstorm` or an explicit ask for interdisciplinary/lateral brainstorming). It is *not* a replacement for `superpowers:brainstorming`'s mandatory, hard-gated design-approval workflow — it's an optional deep-dive step usable inside or before that flow (e.g. during "propose 2-3 approaches") that hands control back afterward rather than proceeding to specs or implementation itself.

## Token governance

There is no hard "token governor." No Claude Code hook or API exists today to programmatically cap or block tool calls based on a token budget. What exists is advisory guidance (the retrieval-discipline block in `CLAUDE.md`) plus the harness's own built-in nudges (e.g. preferring `Grep`/`Read` over `cat`, preferring `Explore` subagents over recursive reads). Treat this as a soft constraint enforced by convention, not code.

## What changed from the original ask

See `DECISIONS.md` for the full exclusion list and reasoning. In short: research-tool MCPs beyond arXiv, a document-conversion pipeline, Task Master, and a hard token governor were all either redundant with existing capabilities or not buildable with current platform primitives, and were deliberately not built.
