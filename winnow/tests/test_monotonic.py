import pytest

from winnow import config, json_truncate, tokencount, trimmer
from winnow.tests import fixtures


@pytest.mark.parametrize("fixture_fn", [
    fixtures.short_chat, fixtures.long_prose_chat, fixtures.json_tool_chat,
    fixtures.code_chat, fixtures.single_message_chat,
])
def test_trim_never_grows_the_payload(fixture_fn):
    body = fixture_fn()
    trimmed = trimmer.trim(fixture_fn())
    assert tokencount.estimate(trimmed) <= tokencount.estimate(body)


def test_adversarial_bloat_falls_back_to_original(monkeypatch):
    # Pathologically inflate what truncate_json returns, simulating a bug in
    # the trimming path. The guard in trimmer.trim must catch the resulting
    # size increase and hand back the untouched original instead.
    def bloat(value, keep_items=20):
        return ["x" * 10_000] * 500

    monkeypatch.setattr(json_truncate, "truncate_json", bloat)

    body = fixtures.json_tool_chat()
    out = trimmer.trim(fixtures.json_tool_chat())
    assert out == body


def test_system_prompt_and_last_n_messages_kept_verbatim():
    body = fixtures.long_prose_chat()
    keep_n = config.keep_last_turns()
    trimmed = trimmer.trim(fixtures.long_prose_chat())

    assert trimmed.get("system") == body["system"]
    assert trimmed["messages"][-keep_n:] == body["messages"][-keep_n:]

