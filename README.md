# claude-orchestra

The config/tooling layer behind this user's Claude Code setup: a local proxy
that trims context before it hits the API, a lightweight per-project memory
system, a router that offloads simple tasks to a local model, and a
shareable copy of the global `~/.claude/` config. This repo documents what's
actually built and running, not a wishlist — see `docs/decisions/` for what
was deliberately left out and why.

## Winnow

`winnow/` is a local, deterministic HTTP proxy that sits between Claude Code
and `api.anthropic.com`, trimming irrelevant older conversation history out
of each request before forwarding it — it never makes a request *larger*
than the original, and falls back to forwarding it byte-for-byte on any
internal failure. It's now wired in via `ANTHROPIC_BASE_URL` in
`~/.claude/settings.json`, pointing at Winnow's local port. See
[`winnow/README.md`](winnow/README.md) for configuration, the trimming
algorithm, and observability (`/winnow/stats`, `python -m winnow.cli`).

## Project memory graph

A per-project memory system using plain markdown: `docs/SESSION_LOG.md`
(reverse-chronological session notes), `docs/research.md` (a research log),
and ADR-style decision records in `docs/decisions/`, all cross-referenced
with `[[wikilinks]]` and queried with a single `rg` call — no database, no
MCP server, no background process. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full picture of what
this setup is built from and why.

## Local model router

`~/.claude/skills/local-model-router/` routes genuinely low-complexity,
single-shot tasks — explaining functions, repo Q&A, refactor suggestions,
unit tests, docs, regex, shell commands, commit messages, small
Markdown/YAML/JSON edits — to a local Gemma model served via `mlx-lm`,
instead of spending a Claude API request on them. It fails open: if the
local server isn't running or the request errors, the task is just done
with Claude directly, no interruption. Architecture/planning, multi-file
edits, debugging, and anything needing tool access stay with Claude.

## `dotfiles/claude/`

A scrubbed, shareable copy of the meaningful parts of this user's
`~/.claude/` config (`CLAUDE.md`, skills, `settings.json`, status line) with
secrets removed, so the setup can be copied onto a fresh machine.

## Status

- **Live now:** Winnow runs as a launchd service (`RunAtLoad` +
  `KeepAlive`), autostarting on login; logs at `~/Library/Logs/winnow.log`.
- **Requires a session restart:** `ANTHROPIC_BASE_URL` was just added to
  `~/.claude/settings.json` — Claude Code only reads it at session start, so
  the current session is still talking directly to `api.anthropic.com`
  until restarted.
- **Not yet running:** the local Gemma model server (`mlx-lm`) that
  `local-model-router` depends on — setting up that launchd service is a
  separate task. The skill fails open until it exists.
