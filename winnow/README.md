# Winnow

A local, deterministic HTTP proxy that sits between Claude Code (or any
Anthropic-API client) and `api.anthropic.com`, trimming irrelevant older
conversation history before forwarding requests — to reduce per-request
token usage without ever *increasing* it.

## Why

This repo previously used **Headroom** and removed it (see
[`docs/decisions/0008-remove-headroom.md`](../docs/decisions/0008-remove-headroom.md)).
Any tool that sits in front of every API call and silently changes payload
size is dangerous if it isn't provably safe — Headroom wasn't. Winnow's
entire design is built around one hard guarantee instead: the forwarded
request is **never larger** than the original, and any internal failure
falls back to forwarding the original request byte-for-byte. See
`trimmer.trim()` for where that guarantee is enforced.

## Setup

```bash
pip install -r winnow/requirements.txt
python -m uvicorn winnow.server:app --port 8787
```

Point Claude Code (or any Anthropic SDK client) at the proxy instead of the
real API:

```bash
export ANTHROPIC_BASE_URL=http://localhost:8787
```

Requests to `/v1/messages` are trimmed (subject to the guarantees below);
every other path/method is forwarded unmodified. Your `ANTHROPIC_API_KEY` /
auth headers pass through untouched — Winnow never sees or needs its own key.

## Configuration

All env-driven, read fresh per request (no restart needed to toggle):

| Env var | Default | Meaning |
|---|---|---|
| `WINNOW_ENABLED` | `true` | Kill switch. `false` = byte-for-byte passthrough. |
| `WINNOW_MODE` | `thorough` | `thorough` (BM25 + local embeddings) or `fast` (BM25 only). |
| `WINNOW_UPSTREAM` | `https://api.anthropic.com` | Real API to forward to. |
| `WINNOW_PORT` | `8787` | Port for `uvicorn winnow.server:app`. |
| `WINNOW_KEEP_LAST_TURNS` | `2` | Most recent N messages always kept verbatim. |
| `WINNOW_RELEVANCE_THRESHOLD` | `0.15` | Prose blocks scoring below this (0-1) become a stub. |
| `WINNOW_JSON_KEEP_ITEMS` | `20` | Array items / dict keys kept before truncating a large JSON tool result. |
| `WINNOW_DB_PATH` | `~/.winnow/winnow.db` | sqlite3 log of every proxied request. |
| `WINNOW_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model for `thorough` mode. |

## Observability

```bash
curl http://localhost:8787/winnow/stats
python -m winnow.cli stats
python -m winnow.cli recent -n 20
```

## How trimming works

The system prompt and the last `WINNOW_KEEP_LAST_TURNS` messages are always
kept verbatim. Within older messages, each content block is classified:

- **Large JSON tool results** (parses as a list/dict above `WINNOW_JSON_KEEP_ITEMS`) — deterministically truncated: first N items/keys kept, plus a `"...K more omitted"` marker.
- **Code blocks** (contain a markdown code fence) — left verbatim. No compression in v1.
- **Plain prose** — scored against the newest user message with BM25 (+ local embeddings in `thorough` mode); below `WINNOW_RELEVANCE_THRESHOLD` it's replaced with a short deterministic stub, otherwise kept verbatim.

Everything runs through `trimmer.trim()`, a pure function with a runtime
guard: if the trimmed result is estimated (via `tiktoken`) to be equal or
larger than the original, or anything in the trimming path raises, it
returns the original request unmodified.

## Deferred (explicitly out of scope for v1)

- Adaptive/online learning — scoring is static and deterministic by design.
- Auth/TLS — localhost-only.
- Multi-user support.
- MCP-exposed stats (only HTTP + CLI for now).
- Full AST-based code compression — code blocks are left verbatim in v1.
