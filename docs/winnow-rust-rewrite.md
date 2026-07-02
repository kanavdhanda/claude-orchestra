# Winnow Rust Rewrite — Handoff and TODO

**Not an ADR.** This doc is a sequenced handoff for a future Rust rewrite of the Winnow proxy (currently Python). Its purpose is to capture the scope and open decisions upfront so a fresh session can pick up the actual rewrite work cold, without re-deriving the technical trade-offs from git history.

The embedding-model approach — Winnow's highest-uncertainty decision — is deliberately left open here. That choice belongs to whoever picks up the rewrite, made with fresh eyes on real trimmer logs and real data on how much the embedding half is earning its 50% weight in practice.

## Module Mapping

The current Python stack is FastAPI + uvicorn for the HTTP server, httpx for the upstream proxy client, rank-bm25 for BM25 scoring, sentence-transformers for embedding-based scoring, and tiktoken for token counting.

Rust equivalents:
- **HTTP server**: FastAPI/uvicorn → `axum` + `tokio`
- **HTTP client**: httpx → `reqwest`
- **BM25 scoring**: `rank-bm25` → hand-rolled implementation (BM25 is a straightforward algorithm; the crate's size doesn't justify a dependency)
- **Embedding scoring**: sentence-transformers → **[open decision, see below]**
- **Token counting**: `tiktoken` → `tiktoken-rs`
- **SQLite storage**: store.py → `rusqlite`

The server.py architecture (fail-open on any error, strip and replay headers correctly, monkeypatching hook for tests) carries over directly.

## The Embedding-Model Question (Open Decision #1)

Winnow's current "thorough" scoring mode is a 50/50 blend of BM25 and local embedding-model cosine similarity. The rewrite must decide how to handle this embedding component. **This doc lays out the four options and their trade-offs; it does not choose one.**

### Option (a): Native Port via Candle
Run the same embedding model natively in Rust using Hugging Face's `candle` ML framework.

- **Pro**: Single-binary deployment, full control over model loading/caching, no inter-process overhead.
- **Con**: Candle is less mature than PyTorch; model support may lag; adds substantial complexity to the Rust codebase.

### Option (b): Local Embedding Server
Spin a small Python or Go embedding server (or call out to an existing one like ollama-rs), communicate over HTTP or IPC.

- **Pro**: Clear separation of concerns, allows switching embedding backends without touching Rust code, proven stability.
- **Con**: Adds operational complexity (another process to manage, health-check, restart); network/IPC latency on every score call; harder to bundle cleanly in launchd.

### Option (c): BM25-Only, Drop Embedding Mode
Ship the Rust rewrite with only BM25 scoring; eliminate the embedding mode entirely.

- **Pro**: Simplest implementation, single-path scoring, no new dependencies.
- **Con**: **Real quality regression.** Requires explicit sign-off from whoever picks this up. Must verify that BM25 alone still meets trimmer accuracy targets in practice.

### Option (d): Hybrid — Rust Shell + Python Sidecar
Only the HTTP reverse-proxy shell, BM25 scoring, and orchestration move to Rust; embedding scoring stays a small Python subprocess the Rust binary spawns and manages.

- **Pro**: No PyTorch/candle dependency in Rust; embedding model path unchanged and proven; minimal rewrite scope.
- **Con**: Still managing a Python subprocess; some latency overhead; conceptual hybrid (defeats some of the appeal of a Rust rewrite).

### Decision Guidance

This decision should be made when the rewrite work picks up, not now. At that time, check:
- Real Winnow usage logs: how often does "thorough" mode activate vs. "fast"?
- Trim-quality samples: does BM25 alone meet the bar, or does the embedding half actually move decisions?
- Deployment constraints: what operational friction (process management, startup time, launchd integration) is acceptable?

## Validation Strategy

Winnow's correctness invariants are encoded in the existing test suite:
- `test_determinism.py`: scoring and trimming produce consistent output across runs.
- `test_failopen.py`: any error (JSON, DB, model, network) results in an unmodified request forwarded upstream.
- `test_monotonic.py`: removal of any message strictly decreases token count.
- `test_scoring.py`: BM25 and embedding scores follow expected ranges and relative ordering.
- Cache-breakpoint tests: [from [[2026-07-02-winnow-cache-fix-design]]] ensure cache invalidation is correct.

**Validation workflow**:

1. Build a Rust binary that implements the chosen embedding strategy (a/b/c/d).
2. Run the Python and Rust implementations in **shadow mode**: same input stream, capture their outputs, and diff. Any divergence in scoring, trimming decisions, or statistics is a bug.
3. Ensure the existing test suite passes on the Rust binary (either by porting the tests or by running them against the Rust server).
4. Only after shadow-mode validation passes and tests succeed should launchd be pointed at the Rust binary.

The Python implementation remains the ground truth for correctness. Any deviation is a rewrite bug, not a design change.

## Done / In-flight / Next / Open Questions

### Done
- (nothing yet)

### In-flight
- Skeleton + BM25 rewrite (config, json_truncate, tokencount, store, scoring,
  trimmer, server — everything except the embedding model) — see
  [[2026-07-02-winnow-rust-skeleton-design]] for the full spec and rationale.

### Next
- Embed option (a/b/c/d) chosen in this section once the skeleton + BM25
  slice lands and there's real usage data on the Rust version.
- (remaining tasks to be filled in as work progresses)

### Open Questions
- **Which embedding option?** (a/b/c/d as detailed above). Real usage data
  as of 2026-07-02 (checked before starting the skeleton slice): 0 of 673
  logged requests have ever dropped or truncated anything, because the
  cache-breakpoint freeze + `keep_last_turns` absorb all real Claude Code
  traffic so far — the embedding path has never actually been exercised in
  production. Leans toward (c) BM25-only or deprioritizing (a)/(d), but
  isn't proof it stays that way on longer conversations.
- **Performance target**: What is the p99 latency budget for a score call in the Rust version? Does embedding server overhead violate it?
- **Startup time**: If embedding is bundled (option a/d), what is acceptable model-load time for launchd restarts?
- **Cache strategy**: Does the Rust version need the same cache-busting logic, or can we simplify?
- (new questions to be added as rewrite progresses)
