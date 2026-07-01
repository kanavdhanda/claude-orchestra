# 0004. Exclude Semantic Scholar MCP and OpenAlex MCP

**Status:** Accepted

## Context
Semantic Scholar MCP and OpenAlex MCP were considered for non-arXiv literature search. Both underlying APIs are real and live.

## Decision
Skip both — neither has an official MCP server, only unmaintained single-maintainer community forks. Rely on the working arxiv-mcp-server plus WebSearch/Firecrawl for non-arXiv literature instead, to avoid depending on unmaintained third-party MCP code.

## Consequences
No dedicated structured-search tool for Semantic Scholar/OpenAlex; covered via WebSearch/Firecrawl as a fallback.

## Affects
N/A
