# Winnow Cache-Invalidation Fix — Design Spec

This is a durable, git-tracked spec. Unlike the harness's own ephemeral
plan-mode file, this survives across sessions so a fresh session can find
and resume this work.

## Context

Winnow (`claude-orchestra/winnow/`) is a deterministic, fail-open HTTP
proxy sitting between Claude Code and `api.anthropic.com`
(`ANTHROPIC_BASE_URL`), trimming irrelevant older messages out of long
conversation histories before forwarding. Confirmed by direct grep this
session (`grep -rn "cache_control" winnow/` — zero matches anywhere,
including `tests/fixtures.py` and `config.py`): Winnow has **no** existing
concept of Anthropic's `cache_control` breakpoints.

The concrete bug: `trimmer.py`'s `_trim_inner` re-scores the "head" portion
of message history against `_newest_user_text(messages)` — the *current*
turn's query — on every single request, via BM25 (and, per `scoring.py`,
by default a 50/50 blend of BM25 and local sentence-transformer embedding
similarity). A message classified relevant/kept for turn N can be stubbed
for turn N+1's different query. Anthropic's prompt cache requires a
byte-identical prefix up to any `cache_control` breakpoint; Winnow's
re-scoring routinely rewrites content inside that prefix, busting the
cache on nearly every turn. This is a total gap, not a partial one — there
is nothing to build on, only something to add from scratch.

## Decision

**Approach A — breakpoint-aware freezing.** Before BM25/embedding scoring
runs, `_trim_inner` locates the last message carrying a `cache_control`
marker: `i = max(idx where messages[idx] contains a cache_control block)`.
The message array splits into `frozen = messages[:i+1]` and
`scorable = messages[i+1:]`. `frozen` is passed through byte-identical —
never re-scored, never stubbed, never touched in any way. Today's existing
head/tail scoring logic runs only on `scorable`. If no `cache_control`
marker exists anywhere in the request (e.g. very early turns before
Claude Code sets one), the whole array falls back to today's existing
full-history scoring behavior — no regression for that case.

This is mechanically correct by construction: Winnow cannot invalidate a
cache prefix it never touches. It does shrink Winnow's prunable region to
"content after the last cache breakpoint" — but that's the right trade,
not a loss, since Anthropic-cached content is already fast and cheap; not
fighting the cache isn't giving anything up.

## Approaches Considered and Rejected

- **B — Frozen classification / memoization.** Cache each message's keep/
  stub decision (content-hash keyed) in Winnow's existing sqlite store the
  first time it drops out of the tail/`keep_last_turns()` window; never
  revisit. Rejected: doesn't actually guarantee alignment with where the
  real `cache_control` breakpoint sits — could still bust cache on
  pre-breakpoint content freeze doesn't cover, or over-freeze content that
  was actually safe to trim. Also introduces relevance staleness (a
  message that becomes newly relevant later stays stubbed forever) for a
  guarantee it doesn't deliver.
- **C — Disable trimming entirely whenever any `cache_control` marker is
  present anywhere in the request.** Simplest possible change. Rejected:
  Claude Code sets `cache_control` on essentially every real conversation
  by default, so this quietly disables Winnow for the majority of its
  actual traffic — discards its core function for the exact case it
  exists to help.

## Validation Strategy

The existing test suite encodes Winnow's real invariants —
`test_determinism.py` (same input → same output), `test_failopen.py`
(any internal error → forward untouched), `test_monotonic.py` (trimming
never increases token count), `test_scoring.py` (BM25/embedding scoring
correctness). The fix adds new fixtures to `tests/fixtures.py` carrying
`cache_control` markers at varying positions (none, early, late,
multi-block) and a new test module verifying: content at/before the last
breakpoint is always byte-identical pre/post-trim, and existing invariants
still hold for the post-breakpoint scorable region.

## Consequences

A real code change to `winnow/trimmer.py` (new breakpoint-location step
inside `_trim_inner`, before the existing scoring call) plus new test
fixtures and a new test module. Touches correctness-critical, already-
tested logic — this gets a full implementation plan via `writing-plans`
and the implementer→reviewer loop, not a trivial single-file dispatch.

## Affects

`winnow/trimmer.py`; `winnow/tests/fixtures.py`; new test module under
`winnow/tests/`.
