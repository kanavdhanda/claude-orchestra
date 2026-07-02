# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.
# >>> retrieval-tool-discipline >>>
## Retrieval & Tool Discipline
- Use Serena's symbol tools (find_symbol, find_referencing_symbols, get_symbols_overview) first; fall back to `rg`/`ast-grep`/`fd`.
- Query docs/APIs via Context7 (resolve-library-id → query-docs) instead of guessing.
- Use `arxiv-mcp-server` for papers; use WebSearch/Firecrawl for other literature.
- **Four-Tier Task Complexity Hierarchy**:
  - **Tier 0 (Claude Opus 4.8)**: High-risk/critical tasks—extreme debugging loops where Sonnet is stuck, core safety audits, or final architecture verification.
  - **Tier 1 (Claude Sonnet 5)**: Standard workhorse—complex logic, multi-file edits, codebase-wide searches, planning, and signal-processing math.
  - **Tier 2 (Claude Haiku 3.5)**: Medium-complexity tasks—single-file scripts, refactorings, or serving as fallback for Tier 3 when oMLX is down or on battery. Spawns via Agent/Task tool using `claude-3-5-haiku`.
  - **Tier 3 (Local oMLX)**: Genuinely low-complexity/single-shot text tasks—explanations, docstrings, unit tests, regex, shell commands, git logs, formatting, paper summaries, and cross-domain brainstorming. Called directly via `curl` shell call to `http://localhost:8081`.
  - **Fallback Mode**: If oMLX (Tier 3) is offline or your Mac is on battery, the hierarchy collapses to **Sonnet 5 (Tier 1)** and **Haiku (Tier 2)**.
- Pre-flight check: Verify model fit. Include only minimal, strictly required files/context in prompts.
# <<< retrieval-tool-discipline <<<
# >>> operating-mode >>>
## Operating Mode
- Caveman ultra-compression: Active session-wide. Exemptions: safety warnings, confirmations, user confusion, and subagent reports.
- Karpathy guidelines: Always active (avoid complexity, make surgical edits, define success, surface assumptions).
- Ponytail: Off in main session. Run ponytail ONLY inside implementer subagent prompts.
- Subagent SDD: Brainstorm/plan in main session, then dispatch tasks to implementers via reviewer loops. Main session only designs, coordinates, and reports.
- Decision-Aware Editing: Before proposing or making any architectural changes, refactorings, or modifications to core logic, search `docs/decisions/` and `docs/research/` (using `rg`) for related past decisions to prevent regressions or unintended domino effects. If related decisions exist, read them first.
- Git Commits: Git commit messages must be extremely concise and strictly no longer than 10-20 words.
- Git Hygiene: Commit or stash uncommitted changes before starting a new Claude Code session. Claude Code automatically pre-loads all uncommitted changes and diffs on startup, causing massive token bloat (~110k+ tokens). Keep the working directory clean.
- SCEMP (Concept Pinning): When reading research papers, complex code modules, or math formulas, immediately extract load-bearing structures/variables into a markdown node under `docs/decisions/` or `docs/research/` using `docs/templates/concept_pinning.md`. Do not re-read large papers; refer to these pinned nodes instead.
- Cross-Domain Analogies: For signal processing or EEG roadblocks, brainstorm analogies from mature domains (speech, acoustics, vision) using `docs/templates/cross_domain_analogy.md`.
- Memory Audit: On session end, verify if any files changed during this session conflict with existing decisions or research logs, and prune/update them accordingly to prevent memory drift.
- Failure Learning: Whenever the user corrects you, fixes a bug you introduced, or resolves a complex signal processing error, write a concise lesson learned under a new `## Lessons Learned` section in the project-root `CLAUDE.md` to prevent repeating the mistake in future chats.
- PDF Reading: If you need to read a local PDF research paper, do not attempt to read the binary. Execute `python3 winnow/pdf_to_md.py <pdf_path> <md_path>` to convert it to a clean Markdown text file in the same directory, and read the converted text instead.
# <<< operating-mode <<<
# >>> active-infrastructure >>>
## Active Infrastructure
- **local-model-router**: Routes simple tasks (explain, refactor, tests, regex, edits) to local Gemma.
- **Winnow**: Local proxy (`http://localhost:8787`) that trims old history.
# <<< active-infrastructure <<<
# >>> session-continuity >>>
## Session Continuity
- On session start: If starting in a new repository where project memory is missing, automatically initialize it by executing the `/project-memory` skill flow. Otherwise, check `docs/SESSION_LOG.md`, open plans, or git diffs to resume without asking.
- Task Resumption: Unless the user explicitly asks to start fresh or ignore past sessions, when they say "continue", "resume", or similar, immediately read the top line of `docs/SESSION_LOG.md` and open the referenced `docs/sessions/<date>.md` to discover exactly where the last session left off. Inspect the current `git status`, git diff, and active branch to pick up the implementation immediately from that state without asking the user for background info.
- On session end/pause: Write handoff details in `docs/sessions/YYYY-MM-DD.md`. Append the new session line to the top of `docs/SESSION_LOG.md` and **strictly keep only the newest 5 sessions** in the list, pruning any lines older than the top 5 to keep the log index compact.
# <<< session-continuity <<<
# >>> prefix-cache-protection >>>
## Prefix Cache Protection & Efficiency
- Do not request changes to the main tool configurations or add/remove MCP servers mid-session (this invalidates the prefix cache).
- Keep conversations focused and split large projects into isolated chat sessions.
- On-Demand Retrieval: Do not pre-load or paste large reference files/logs into the conversation. Query them on-demand using `rg` or `view_file` when needed; this keeps the prefix clean and leverages cached reads cheaply.
# <<< prefix-cache-protection <<<

