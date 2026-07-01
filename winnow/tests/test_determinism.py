import json

import pytest

from winnow import scoring, trimmer
from winnow.tests import fixtures


@pytest.mark.parametrize("fixture_fn", [
    fixtures.short_chat, fixtures.long_prose_chat, fixtures.json_tool_chat,
    fixtures.code_chat, fixtures.single_message_chat,
])
def test_trim_is_byte_identical_across_runs(fixture_fn):
    body = fixture_fn()
    out1 = trimmer.trim(fixture_fn())
    out2 = trimmer.trim(fixture_fn())
    assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)
    # sanity: trim didn't mutate the caller's original object
    assert fixture_fn() == body


def test_hybrid_score_is_bit_identical_across_many_calls():
    query = "Can you show an example of a decorator that logs function calls?"
    candidate = "A Python decorator wraps a function to add logging around every call it makes."
    corpus = [candidate, "Carbonara is made with eggs and pecorino cheese."]
    results = {scoring.hybrid_score(query, candidate, corpus=corpus) for _ in range(20)}
    assert len(results) == 1
