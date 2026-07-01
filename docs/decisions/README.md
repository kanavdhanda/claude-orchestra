# Architecture Decision Records

- [0001. Exclude Task Master](0001-exclude-task-master.md) — redundant with native Task* tools
- [0002. Exclude Docling, Marker, MinerU, Nougat](0002-exclude-pdf-conversion-tools.md) — redundant with native PDF reading
- [0003. Exclude Crawl4AI](0003-exclude-crawl4ai.md) — redundant with Firecrawl
- [0004. Exclude Semantic Scholar MCP and OpenAlex MCP](0004-exclude-semantic-scholar-openalex-mcp.md) — no official MCP server for either
- [0005. Exclude Papers with Code MCP](0005-exclude-papers-with-code-mcp.md) — underlying service shut down
- [0006. No Hard Token Governor](0006-no-hard-token-governor.md) — no hook/API exists to enforce it
- [0007. No Automatic PDF-Ingestion Hook](0007-no-automatic-pdf-ingestion-hook.md) — redundant with native PDF reading
- [0008. Remove Headroom (Office-doc reading via markitdown)](0008-remove-headroom.md) — removed at user's request
- [0009. No Speculative Scaffold Directories](0009-no-speculative-scaffold-directories.md) — YAGNI
- [0010. Use Official ast-grep MCP Instead of Building a Custom One](0010-use-official-ast-grep-mcp.md) — official server already exists
- [0011. No MCP Wrappers for fd and tree-sitter](0011-no-fd-tree-sitter-mcp-wrappers.md) — plain Bash invocation is sufficient
