from winnow import trimmer
from winnow.tests import fixtures


def test_last_cache_breakpoint_index_finds_a_single_marker():
    body = fixtures.cache_early_chat()
    assert trimmer._last_cache_breakpoint_index(body["messages"]) == 1


def test_last_cache_breakpoint_index_finds_a_late_marker():
    body = fixtures.cache_late_chat()
    assert trimmer._last_cache_breakpoint_index(body["messages"]) == 5


def test_last_cache_breakpoint_index_returns_the_highest_of_several_markers():
    body = fixtures.cache_multi_breakpoint_chat()
    assert trimmer._last_cache_breakpoint_index(body["messages"]) == 5


def test_last_cache_breakpoint_index_returns_negative_one_when_absent():
    body = fixtures.long_prose_chat()
    assert trimmer._last_cache_breakpoint_index(body["messages"]) == -1


def test_last_cache_breakpoint_index_ignores_plain_string_content():
    # A plain string `content` value can never carry a cache_control block —
    # only the list-of-blocks form can. This must not raise or false-positive.
    body = fixtures.short_chat()
    assert trimmer._last_cache_breakpoint_index(body["messages"]) == -1
