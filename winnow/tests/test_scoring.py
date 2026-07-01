from winnow import scoring

QUERY = "Can you show an example of a decorator that logs function calls?"
RELEVANT = "A Python decorator wraps a function to add logging around every call it makes."
IRRELEVANT = "Carbonara is made with eggs, pecorino cheese, guanciale, and black pepper."
# ponytail: BM25 IDF is mathematically degenerate (== 0) for a 2-document
# corpus where a term appears in exactly one of the two; a few filler docs
# keep the corpus realistic enough for IDF to differentiate terms at all.
FILLER = [
    "Lisbon in October is generally mild with occasional rain showers.",
    "The train departs from platform nine at half past six each morning.",
]


def test_bm25_relevant_scores_higher_than_irrelevant():
    corpus = [RELEVANT, IRRELEVANT] + FILLER
    r = scoring.bm25_score(QUERY, RELEVANT, corpus=corpus)
    i = scoring.bm25_score(QUERY, IRRELEVANT, corpus=corpus)
    assert r > i


def test_hybrid_relevant_scores_higher_than_irrelevant():
    corpus = [RELEVANT, IRRELEVANT] + FILLER
    r = scoring.hybrid_score(QUERY, RELEVANT, corpus=corpus)
    i = scoring.hybrid_score(QUERY, IRRELEVANT, corpus=corpus)
    assert r > i


def test_scores_are_bounded_0_to_1():
    corpus = [RELEVANT, IRRELEVANT] + FILLER
    for text in corpus[:2]:
        h = scoring.hybrid_score(QUERY, text, corpus=corpus)
        b = scoring.bm25_score(QUERY, text, corpus=corpus)
        assert 0.0 <= h <= 1.0
        assert 0.0 <= b <= 1.0


def test_mode_dispatch():
    corpus = [RELEVANT, IRRELEVANT]
    assert scoring.score(QUERY, RELEVANT, corpus, mode="fast") == scoring.bm25_score(QUERY, RELEVANT, corpus)
    assert scoring.score(QUERY, RELEVANT, corpus, mode="thorough") == scoring.hybrid_score(QUERY, RELEVANT, corpus)
