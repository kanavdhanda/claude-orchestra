# Model/Subagent Routing Discipline — Design Spec

This is a durable, git-tracked spec. Unlike the harness's own ephemeral
plan-mode file, this survives across sessions so a fresh session can find
and resume this work.

## Context

The user's mandate asked for agent/model usage to be maximally efficient —
not defaulting to Sonnet for everything, routing heavy/judgment work to
Sonnet/Opus, fast/mechanical work to Haiku, and local-eligible work to the
already-running local model — plus giving subagents only the context they
need for their specific task, not a dump of the whole conversation.

Most of this already exists. The global `~/.claude/CLAUDE.md`
`retrieval-tool-discipline` block already states the heavy/fast/local
three-way split and already routes local-eligible work to the
`local-model-router` skill rather than conflating it with the Agent tool's
`model` parameter (which only accepts Claude-family models). Confirmed by
reading that block directly — no design work needed there.

Two real gaps remain, both raised explicitly by the user when asked what's
actually missing given the above is already written down:

1. **Context over-sharing.** Nothing stops a subagent dispatch from handing
   over the full conversation/repo context instead of only what the
   subtask needs. The Agent tool's own description nudges toward scoping
   ("brief the agent like a smart colleague... hand over the exact
   command"), but that's advisory per-call guidance, not a standing rule
   the main session checks against every time.
2. **Enforcement drift.** The routing rule exists in writing but isn't
   reliably followed in practice — Sonnet/Opus still gets reached for on
   work that should have gone to Haiku or the local model.

## Decision

Sharpen the existing `retrieval-tool-discipline` block in
`~/.claude/CLAUDE.md` (global config — not this project's local
`CLAUDE.md`, per the user's explicit correction) with a concrete two-item
pre-flight checklist, rather than inventing a new mechanism:

> Before every Agent/Task dispatch, run this pre-flight check:
> 1. **Model fit** — does the task weight match the model? Mechanical/fast/
>    single-shot → haiku. Default judgment work → sonnet (inherited).
>    Architecture, hard debugging, high-stakes irreversible decisions →
>    opus. Local-model-eligible (per `local-model-router`'s own criteria)
>    → route there instead of Agent, not in addition to it.
> 2. **Context scope** — does the prompt contain only what this specific
>    subtask needs (relevant file paths, the exact question, prior
>    findings that inform it), not the full conversation history or
>    unrelated project context? If you're about to paste in "everything
>    so far," stop and extract only the load-bearing parts.

This lives inside the existing block (same file, same section) so it
inherits that block's placement and precedence — no new file, no new
section, no hook, no mechanical enforcement layer.

## Alternatives Considered

- **A PreToolUse hook on the Agent tool** that inspects prompt length/
  content and warns on apparent over-sharing. Rejected: "too much
  context" has no reliable mechanical signal — a long prompt can be
  legitimately necessary, a short one can still leak the wrong things.
  High false-positive risk for a discipline problem that a sharper written
  rule already addresses without that risk.
- **Leaving the Agent tool's own description as the only guidance.**
  Rejected: it already exists today and is evidently insufficient, which
  is why the user flagged this as a gap in the first place.

## Consequences

Single-file, single-block text edit to `~/.claude/CLAUDE.md`. No code, no
new skill, no hook. Trivial enough to skip the full worktree/multi-review
implementation ceremony — one implementer subagent applies the edit.

## Affects

`~/.claude/CLAUDE.md` (global) — `retrieval-tool-discipline` block.
