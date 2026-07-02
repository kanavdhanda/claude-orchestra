---
tags: [fd, tree-sitter, cli-sufficient]
related: []
influences: []
---

# 0011. No MCP Wrappers for fd and tree-sitter

**Status:** Accepted

## Context
MCP wrappers for the `fd` and `tree-sitter` CLI utilities were considered.

## Decision
Not built. Both are simple, single-purpose CLI utilities with no meaningful benefit from a structured-tool-call interface; plain Bash invocation is sufficient.

## Consequences
No gap — plain Bash invocation covers the need.

## Affects
N/A
