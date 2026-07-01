# 0007. No Automatic PDF-Ingestion Hook

**Status:** Accepted

## Context
An automatic PDF-ingestion hook ("detect PDF → convert → index → cache") was considered.

## Decision
Not built. Redundant — PDFs already work with zero special handling; there is nothing to trigger a pipeline for in the common case.

## Consequences
No gap — native PDF reading covers the need.

## Affects
N/A
