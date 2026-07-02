---
tags: [mlx, fallback, reliability, local-model-router]
related: []
influences: []
---

# 0012. MLX Fallback Contract

**Status:** Accepted

## Context

The user turns the local MLX server off to save battery. Any current or future feature that calls out to it (e.g. `local-model-router`) must never block, error, or surface a failure to the user when it's unreachable — it must fail open, silently, back to the harness's normal path (Sonnet).

This isn't a new problem: `local-model-router` (`~/.claude/skills/local-model-router/SKILL.md`) already implements the correct pattern — a short-timeout liveness check (`curl -s -m 2 http://localhost:8080/v1/models`) before routing, and fail-open on any error, timeout (30s), or malformed output, never blocking or surfacing the failure. A live crash was observed during this session's work: after a model download completed, the MLX server failed to load with `ValueError: Model type gemma4_unified not supported.` — a real instance of exactly the failure mode this contract exists to handle.

What's missing isn't the pattern — it's that the pattern exists in exactly one place and isn't written down as a requirement for anything built after it. Without a documented contract, a future MLX-dependent feature could easily skip the liveness check or let an exception propagate, and there would be no written standard to catch that against.

## Decision

Any feature that depends on the MLX server must implement the following fail-open contract:

1. **Liveness-check first, short timeout.** Before any real work is sent to the MLX server, probe it with a timeout in the low single-digit seconds (2s in the reference implementation). Never assume it's up.
2. **Fail open on every failure mode** — connection refused, timeout, non-2xx response, malformed/unparseable output, or a slow response that exceeds a generous ceiling (30s in the reference implementation). All of these mean: silently fall back to the harness's default path. None of them mean: retry indefinitely, block, or show the user an error.
3. **Never surface MLX-unavailability to the user** as an error state. The user turning the server off is a normal, expected condition, not a fault.

`local-model-router` is cited directly as the reference implementation — this ADR formalizes what it already does correctly, it does not introduce new code.

## Alternatives Considered

- **A shared fallback utility/library** other features import. Rejected for now: there's exactly one consumer of this pattern today (`local-model-router`); extracting a shared abstraction for a single caller is premature. Revisit if/when a second MLX-dependent feature is actually built — the ADR's existence is what obligates that second feature to follow the same contract, a shared utility is an optional implementation detail at that point, not a requirement of this decision.
- **A health-check daemon** that polls MLX server status continuously and caches liveness. Rejected: adds a persistent background process for a check that's already cheap (2s timeout) to do per-call, and introduces a staleness window (cached "down" could miss the server coming back up).

## Consequences

Single-file ADR write plus one line added to `docs/decisions/README.md`. No code changes — `local-model-router` already conforms; this just makes the requirement explicit and citable for anything built after it.

## Affects

- `docs/decisions/README.md` — new index line added
