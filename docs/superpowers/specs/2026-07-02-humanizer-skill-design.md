# Humanizer Skill — Design Spec

This is a durable, git-tracked spec. Unlike the harness's own ephemeral
plan-mode file, this survives across sessions so a fresh session can find
and resume this work.

## Context

The user wants a skill that removes the tells that mark text as
AI-written, built from the complete Wikipedia "Signs of AI writing"
taxonomy — the only piece of the original four-skill ask (frontend/
Awwvards, critical-thinking, humanizer, skill-router) confirmed genuinely
novel enough to build rather than adopt from an existing community/
Anthropic option.

**Policy boundary, raised explicitly and acknowledged by the user
("both").** This skill is a general writing-quality tool, legitimate for
any writing context (emails, docs, blog posts, this repo's own prose) —
and separately, usable on text destined for academic submission. It must
NOT be engineered, marketed, or documented as a guaranteed detector-
evasion tool (Turnitin or otherwise). Whether the user submits humanized
output as coursework is the user's own responsibility, not something the
skill actively optimizes toward. Concretely: the skill's `description` and
body describe it as fixing AI writing tells for readability/authenticity,
never claim or imply detector-evasion guarantees, and never mention
Turnitin or similar tools by name.

## Decision

A single skill, `~/.claude/skills/humanizer/SKILL.md`, with two modes:

- **`scan`** — read the given text, report which taxonomy categories it
  triggers and where, without rewriting anything. For "is this text
  giving off AI tells" checks.
- **`fix`** — apply the taxonomy's fix guidance directly to the text and
  return the rewritten version.

The skill body is a distilled checklist from Wikipedia's "Signs of AI
writing" page, organized by category (each category: what the tell looks
like, why it reads as AI-generated, the concrete fix). No MLX dependency —
this is a pure prompting/checklist skill, Claude applies the checklist
itself; there's no local-model call to fail open around.

**Auto-activation.** Per the trigger phrasing convention already used by
other skills in this environment, the `description` field lists concrete
trigger phrases: "humanize," "sound human," "remove AI writing tells/
signs," "doesn't sound like ChatGPT," "de-AI this." This is enough for the
existing skill-discovery mechanism (`using-superpowers`) without a
separate router.

## Alternatives Considered

- **Two skills (scan-only and fix-only)** instead of one skill with two
  modes. Rejected: they share the entire taxonomy checklist; splitting
  them duplicates that content for no benefit, and a user asking to
  "humanize this" already implies fix mode by default with scan available
  as an explicit ask.
- **Bundling MLX-based style-transfer** (e.g., asking the local model to
  rewrite in a "more human" voice) as an optional acceleration path.
  Rejected: adds an MLX dependency (with its own fallback-contract
  obligation per [[2026-07-02-mlx-fallback-contract-design]]) for a task
  Claude can already do directly from a checklist — no capability gap it
  closes.

## Consequences

One new skill file. No code, no new dependency, no MLX integration. Given
it compiles the full Wikipedia taxonomy into a structured checklist (not a
one-line change), this gets a real implementation plan via `writing-plans`
rather than being treated as trivial — but the design itself is settled
here: single file, two modes, no MLX.

## Affects

New file `~/.claude/skills/humanizer/SKILL.md`.
