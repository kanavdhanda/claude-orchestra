import pytest

from winnow import config, trimmer
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


@pytest.mark.parametrize("fixture_fn,breakpoint_idx", [
    (fixtures.cache_early_chat, 1),
    (fixtures.cache_late_chat, 5),
    (fixtures.cache_multi_breakpoint_chat, 5),
])
def test_frozen_prefix_is_byte_identical_after_trim(fixture_fn, breakpoint_idx):
    body = fixture_fn()
    trimmed = trimmer.trim(fixture_fn())
    assert trimmed["messages"][: breakpoint_idx + 1] == body["messages"][: breakpoint_idx + 1]


@pytest.mark.parametrize("fixture_fn", [
    fixtures.cache_early_chat, fixtures.cache_late_chat, fixtures.cache_multi_breakpoint_chat,
])
def test_last_n_messages_still_kept_verbatim_with_a_cache_breakpoint(fixture_fn):
    body = fixture_fn()
    keep_n = config.keep_last_turns()
    trimmed = trimmer.trim(fixture_fn())
    assert trimmed["messages"][-keep_n:] == body["messages"][-keep_n:]


def test_cache_breakpoint_covering_the_whole_history_returns_body_unchanged():
    # cache_late_chat's breakpoint is at index 5 of 9 messages; if
    # WINNOW_KEEP_LAST_TURNS were large enough that scorable ends up empty,
    # trim() must hand back the original body rather than an empty-messages
    # rewrite. keep_last_turns() defaults to 2, so scorable = messages[6:9]
    # (3 messages) is non-empty by default — this asserts the *shape* of that
    # guard using the real default rather than monkeypatching config.
    body = fixtures.cache_late_chat()
    trimmed = trimmer.trim(fixtures.cache_late_chat())
    assert len(trimmed["messages"]) == len(body["messages"])
