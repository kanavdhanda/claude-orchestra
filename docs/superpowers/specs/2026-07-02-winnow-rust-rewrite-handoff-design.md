# Winnow Rust Rewrite — Handoff Doc Design Spec

This is a durable, git-tracked spec. Unlike the harness's own ephemeral
plan-mode file, this survives across sessions so a fresh session can find
and resume this work.

## Context

Sequenced explicitly last, per the user's instruction: write the upfront
TODO/handoff doc *before* any rewrite work starts, so a fresh session can
pick this up cold. This subproject's deliverable is the handoff doc
itself — not Rust code, not a rewrite plan to be executed this mandate.

Grounded by reading `winnow/server.py` and `winnow/requirements.txt`
directly this session rather than assuming: the stack is FastAPI +
uvicorn + httpx (async HTTP proxy), `rank-bm25` for BM25 scoring, and —
confirmed by reading `scoring.py` — a default scoring mode (`mode:
str = "thorough"`) that is a 50/50 blend of BM25 and a local
`sentence-transformers` embedding cosine similarity, not BM25 alone. That
last point matters: it means the rewrite carries a real PyTorch-model
dependency, not just a set of straightforward crate swaps.

## Decision

Write a single handoff doc at `docs/winnow-rust-rewrite.md`, containing:

1. **Module mapping**, grounded in what was actually read this session:
   FastAPI/uvicorn/httpx → `axum` + `tokio` + `reqwest`; `rank-bm25` →
   hand-rolled (BM25 is small enough that a dependency isn't worth it);
   `tiktoken` → `tiktoken-rs`; sqlite (`store.py`) → `rusqlite`.
2. **The embedding-model question, stated as the #1 open decision, not
   pre-answered.** Four real options, each with its trade-off, and no
   pick made here:
   - (a) run the same embedding model natively via `candle` (Hugging
     Face's Rust ML framework).
   - (b) call out to a small local embedding server over HTTP/IPC.
   - (c) drop embedding mode, ship BM25-only in Rust — a real quality
     regression in trim decisions, requires explicit sign-off from
     whoever picks this up.
   - (d) hybrid: only the HTTP shell + BM25 + orchestration move to Rust;
     embedding scoring stays a small Python sidecar the Rust binary calls
     locally.
   The doc states these four options and their trade-offs; it does not
   choose one. That decision belongs to whoever picks up the rewrite,
   made with fresh eyes on how much the embedding half is actually
   earning its 50% weight in real trimming decisions by that point.
3. **Validation strategy.** The existing test suite
   (`test_determinism.py`, `test_failopen.py`, `test_monotonic.py`,
   `test_scoring.py`, plus the new cache-breakpoint tests from
   [[2026-07-02-winnow-cache-fix-design]]) encodes Winnow's real
   invariants. The Rust rewrite is only real once it passes equivalent
   tests; the doc specifies running Python and Rust in shadow mode (same
   input, diff outputs) before ever pointing launchd at the Rust binary.
4. **A "done / in-flight / next / open questions" scaffold** — empty at
   write time, structured so a cold session updates it incrementally
   instead of re-deriving state from git log each time it picks this back
   up.

## Alternatives Considered

- **Start the rewrite now, alongside the doc.** Rejected directly by the
  user's own sequencing instruction — the doc comes first, and this
  mandate's scope for subproject 5 is the doc only.
- **Pre-decide the embedding-model approach now** rather than leaving it
  open. Rejected: deciding it requires knowing, in practice, how much the
  embedding half of scoring actually changes trim outcomes versus BM25
  alone — that's an empirical question best answered by whoever starts
  the rewrite with real trimmer logs to look at, not guessed at now.

## Consequences

One doc-only deliverable, no code. Scoped tightly enough (a single
document, no further code decisions this mandate) to skip the full
worktree/multi-review ceremony — one implementer subagent writes the
final handoff doc from this spec.

## Affects

New file `docs/winnow-rust-rewrite.md`. Not an ADR: `docs/decisions/`
holds settled decisions, and this doc's central point (the embedding-model
approach) is explicitly left open — the wrong format for that content.
