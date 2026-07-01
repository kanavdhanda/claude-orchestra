"""Relevance scoring: BM25 (fast) and BM25+embedding hybrid (thorough).

Pure functions only — no network/DB calls. The embedding model is a
lazily-loaded process-local singleton (loading it eagerly at import time
would slow down every process that imports this module, including tests
that never need it).
"""
import re
from functools import lru_cache

from rank_bm25 import BM25Okapi

from winnow import config

_TOKEN_RE = re.compile(r"\w+")


def _tokenize(text: str):
    return _TOKEN_RE.findall(text.lower())


@lru_cache(maxsize=1)
def _embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(config.embedding_model())


def _corpus_with_candidate(candidate: str, corpus):
    docs = list(corpus) if corpus else []
    if candidate not in docs:
        docs = docs + [candidate]
    return docs


def bm25_scores_batch(query: str, candidates: list) -> list:
    """BM25 relevance of `query` against each of `candidates`, squashed to
    [0, 1) via a saturating raw/(raw+1) transform.

    ponytail: deliberately NOT normalized by dividing by the batch's own max
    score — that collapses to a useless constant 1.0 whenever the batch has
    just one candidate (our real call pattern, see trimmer.py), and BM25 IDF
    is itself degenerate (== 0) for very small corpora. The saturating
    transform is stable and monotonic regardless of corpus size.
    """
    if not candidates:
        return []
    tokenized = [_tokenize(c) for c in candidates]
    bm25 = BM25Okapi(tokenized)
    raw = bm25.get_scores(_tokenize(query))
    return [float(s) / (float(s) + 1.0) for s in raw]


def embedding_scores_batch(query: str, candidates: list) -> list:
    """Cosine similarity of `query` against each of `candidates`, mapped from
    [-1, 1] to [0, 1]."""
    if not candidates:
        return []
    model = _embedding_model()
    vectors = model.encode([query] + list(candidates), normalize_embeddings=True)
    q = vectors[0]
    return [float((q @ v + 1.0) / 2.0) for v in vectors[1:]]


def bm25_score(query: str, candidate: str, corpus: list = None) -> float:
    """Fast-mode score: BM25 only, for a single candidate against a query.
    `corpus` (sibling candidates from the same conversation) supplies IDF
    context; defaults to just the candidate itself."""
    docs = _corpus_with_candidate(candidate, corpus)
    scores = bm25_scores_batch(query, docs)
    return scores[docs.index(candidate)]


def hybrid_score(query: str, candidate: str, corpus: list = None) -> float:
    """Thorough-mode score: 50/50 blend of BM25 and local embedding cosine
    similarity for a single candidate against a query."""
    docs = _corpus_with_candidate(candidate, corpus)
    bm25 = bm25_scores_batch(query, docs)[docs.index(candidate)]
    emb = embedding_scores_batch(query, [candidate])[0]
    return round(0.5 * bm25 + 0.5 * emb, 12)


def score(query: str, candidate: str, corpus: list = None, mode: str = "thorough") -> float:
    """Single entrypoint trimmer.py uses; dispatches on mode."""
    if mode == "fast":
        return bm25_score(query, candidate, corpus)
    return hybrid_score(query, candidate, corpus)
