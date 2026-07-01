# 0008. Remove Headroom (Office-doc reading via markitdown)

**Status:** Accepted

## Context
Headroom's markitdown integration provided Office-document (.docx/.doc/.pptx/.ppt/.xlsx/.xls) reading.

## Decision
Fully removed at the user's request (no longer used). The `headroom:markitdown_office` block was deleted from `~/.claude/CLAUDE.md`, its `permissions.allow` entry removed from `~/.claude/settings.json`, and the broken `headroom` MCP registration removed from `~/.claude.json`.

## Consequences
Office documents (.docx/.doc/.pptx/.ppt/.xlsx/.xls) can no longer be read directly through Claude Code; only PDFs continue to work natively. Revisit if Office-doc reading is needed again later.

## Affects
`~/.claude/CLAUDE.md`, `~/.claude/settings.json#permissions.allow`, `~/.claude.json#mcpServers`
