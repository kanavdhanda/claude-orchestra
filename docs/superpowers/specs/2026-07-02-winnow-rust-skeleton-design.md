# Winnow Rust Rewrite — Skeleton + BM25 — Design Spec

This is the first concrete slice of the rewrite scoped in
`docs/winnow-rust-rewrite.md`. That doc lays out the full module mapping and
the four embedding-model options (a/b/c/d) as an explicitly open decision;
this spec covers only the slice that doesn't depend on that decision.

## Context

The Python Winnow proxy is 588 lines across 8 modules: `server.py` (FastAPI
reverse proxy, fail-open), `trimmer.py` (pure orchestration — cache-breakpoint
freeze, corpus build, classify/score/truncate), `scoring.py` (BM25 +
embedding hybrid), `json_truncate.py` (pure structural truncation),
`tokencount.py` (tiktoken estimate), `store.py` (sqlite3 observability),
`config.py` (env-driven config), `cli.py` (thin stats CLI).

Before starting, real usage data was checked per the handoff doc's own
decision guidance: of 673 real proxied requests logged in
`~/.winnow/winnow.db`, **zero have ever dropped or truncated anything**
(`dropped=0, truncated=0` on every row). Tracing why: `_trim_inner` freezes
everything up to the last `cache_control` breakpoint (merged same day as this
spec), and Claude Code's own traffic keeps that breakpoint close to the
current turn, so `scorable`/`head` end up empty on real conversations. The
embedding-scoring half of `hybrid_score` has never actually been exercised in
production.

That doesn't prove embedding is worthless — a longer conversation without
recent cache breakpoints could still hit it — but it means there is currently
zero evidence the embedding half changes a real drop decision. Building the
full BM25 rewrite now and deferring the embedding decision until there's
actual evidence it matters is the correct call, not a shortcut.

## Scope

**In scope:** `config.rs`, `json_truncate.rs`, `tokencount.rs`, `store.rs`,
`scoring.rs` (BM25 only), `trimmer.rs`, `main.rs`/`server.rs`.

**Out of scope:** the embedding model (Open Decision #1 in the handoff doc
stays open), a Python/Rust shadow-mode diffing harness, launchd wiring,
`cli.rs`.

## Module Mapping

One Rust module per Python file, same responsibility boundary:

- **`config.rs`** — same env vars (`WINNOW_ENABLED`, `WINNOW_MODE`,
  `WINNOW_UPSTREAM`, `WINNOW_PORT`, `WINNOW_KEEP_LAST_TURNS`,
  `WINNOW_RELEVANCE_THRESHOLD`, `WINNOW_JSON_KEEP_ITEMS`, `WINNOW_DB_PATH`,
  `WINNOW_EMBEDDING_MODEL`), same defaults, read fresh (not cached) so
  `WINNOW_ENABLED` works as a live kill switch.
- **`json_truncate.rs`** — pure recursion over `serde_json::Value`: keep
  first N array items / dict keys (insertion order), append an
  omitted-count marker, recurse into kept children.
- **`tokencount.rs`** — `tiktoken-rs`, `cl100k_base` encoding, estimate only
  (not billing-accurate, matches the Python docstring's own caveat).
- **`scoring.rs`** — hand-rolled BM25Okapi (raw score → `raw/(raw+1)`
  saturating squash, deliberately not batch-max-normalized — see the
  `ponytail:` comment in `scoring.py` for why). `hybrid_score`/embedding path
  is not implemented; `score(mode)` dispatches `"fast"` to BM25 and
  `"thorough"` also to BM25 for now, logging a one-time startup warning that
  embedding scoring isn't implemented in this build.
- **`store.rs`** — `rusqlite` (bundled feature, no system libsqlite3
  dependency), same `requests` table schema, same `log_request` /
  `query_recent` / `aggregate_savings` queries.
- **`trimmer.rs`** — the core correctness surface, ported faithfully:
  `_last_cache_breakpoint_index` freeze, `_build_prose_corpus`,
  `_classify_and_process` (json/code/prose/skip), `diff_stats`, and the
  guarded `trim()` entrypoint that discards the trimmed result and returns
  the original body untouched if the trimmed estimate isn't strictly
  smaller, or if anything panics/errors.
- **`main.rs`/`server.rs`** — `axum` + `tokio`, `reqwest` upstream client
  (300s timeout, matching `server.py`'s `httpx.AsyncClient(timeout=300.0)`),
  catch-all route forwarding every method/path, `POST /v1/messages` is the
  only path that goes through `_trim_and_log`, same header strip sets
  (`content-length`/`content-encoding`/`transfer-encoding`/`connection` on
  the response; `host`/`content-length` on the request), `GET /winnow/stats`
  returns the same JSON shape as the Python version.

## Dependencies

`axum`, `tokio` (full), `reqwest`, `serde` + `serde_json`, `rusqlite`
(bundled), `tiktoken-rs`. No ML/candle crate this session.

## Error Handling

Fail-open is preserved exactly: `trim()` never panics out to the caller
(catch with `std::panic::catch_unwind` or, preferably, structure it so
scoring/truncation return `Result` and every error path falls back to the
original body — matching Python's broad `except Exception`). The proxy
handler's outer boundary also falls back to forwarding the raw original
bytes on any trim/log failure, same as `server.py`.

## Testing

Each Rust module gets unit tests ported from its matching `test_*.py`:
`test_json_truncate.py`, `test_scoring.py` (BM25 ranges/ordering only —
embedding assertions don't apply), `test_trimmer.py`, `test_determinism.py`,
`test_monotonic.py`, `test_cache_breakpoint.py`, `test_failopen.py`. No
shadow-mode automation this session — the ported test fixtures are the
correctness gate. `server.rs`/`main.rs` gets a manual smoke test (start it,
hit `/winnow/stats`, proxy one real request) rather than a formal
integration-test suite, since `_forward` isolation for mocking would be new
surface not justified yet.

## Execution Plan

Five leaf modules have no interdependencies and are dispatched in parallel;
`trimmer.rs` depends on all of them; `main.rs`/`server.rs` depends on
`trimmer` + `store` + `config`.

- **Wave 1 (parallel):** `config.rs`, `json_truncate.rs`, `tokencount.rs`,
  `store.rs`, `scoring.rs` — each with its ported unit tests.
- **Wave 2 (sequential):** `trimmer.rs`, against `test_trimmer.py`,
  `test_determinism.py`, `test_monotonic.py`, `test_cache_breakpoint.py`.
- **Wave 3 (sequential):** `main.rs`/`server.rs`, wired into a real
  `Cargo.toml`, manually smoke-tested.

## Open Questions Carried Forward

Unchanged from `docs/winnow-rust-rewrite.md`: which embedding option
(a/b/c/d), p99 latency budget, startup-time budget if embedding is bundled,
whether the cache strategy needs simplification. This spec adds one data
point to that decision: **real usage as of 2026-07-02 shows the embedding
path has never been exercised** (0/673 requests dropped or truncated
anything) — worth re-checking after this Rust version has run for a while,
since it changes nothing structurally but is strong evidence for leaning
toward option (c) BM25-only, or at minimum deprioritizing (a)/(d)'s
complexity.
