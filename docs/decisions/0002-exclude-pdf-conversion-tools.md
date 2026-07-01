# 0002. Exclude Docling, Marker, MinerU, Nougat

**Status:** Accepted

## Context
Docling, Marker, MinerU, and Nougat were considered for PDF-to-text/markdown conversion.

## Decision
Excluded. Claude reads PDFs natively with no special step, making all four redundant. Nougat is additionally unmaintained since ~2023 and was superseded in practice by Marker/Docling/MinerU.

## Consequences
No gap — native PDF reading covers the need.

## Affects
N/A
