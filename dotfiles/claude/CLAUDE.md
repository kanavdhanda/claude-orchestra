# Antigravity Rules
- **4-Tier Models**: Tier 0: Opus 4.8 (Safety/Loop Blockers); Tier 1: Sonnet 5 (Default/Workhorse); Tier 2: Haiku (Medium/Fallback); Tier 3: Local oMLX Qwen (Low/Single-shot, e.g. explain, doc, test, regex).
- **Session Continuity**: Read only `docs/SESSION_LOG.md` on resume. Do not preload files. Use local `rg` to find old tasks; do not open files blindly. Keep logs < 50 lines.
- **Git Rules**: Messages < 10-20 words. Commit/stash changes before starting a session to avoid startup pre-loading token bloat (~110k+).
- **Discipline**: Serena first for symbols, then `rg`/`ast-grep`. On initializing new projects, verify `.serena/project.yml` is created and contains `languages: ["python"]` so Serena indexes automatically.
- **Knowledge Memory**: Extract load-bearing math/structures into `docs/decisions/` or `docs/research/` via templates on read. Run memory audits on session end.
- **Failure Learning**: Record resolved bugs in a `## Lessons Learned` section.
