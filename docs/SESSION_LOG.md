# Session Log

Thin index, newest first. One line per session file — filename + a short
summary, no inline content. Full detail lives in `docs/sessions/<date>.md`;
open that file only if the one-liner isn't enough. This index must stay
short forever: it only ever gains one line per session.

- [[2026-07-02]] — ADRs split into `docs/decisions/`, Winnow proxy built, project memory graph added, Winnow cache-breakpoint bug fixed and merged, auto-compact context-spike bug root-caused and fixed (ponytail/superpowers hook matchers). Proxy redesigned to Stable Moving-Window Trimming (SMWT) to achieve actual token savings with prompt cache compatibility; minified system prompt + CLAUDE.md to save 3,400+ tokens per turn.
