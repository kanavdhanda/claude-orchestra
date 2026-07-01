"""Requirement 9: content-type-aware trimming. Each content type gets its
own treatment inside the trimmable ("head") portion of the conversation.
"""
from winnow import trimmer
from winnow.tests import fixtures


def test_large_json_tool_result_is_truncated_in_place():
    out = trimmer.trim(fixtures.json_tool_chat())
    tool_result = out["messages"][2]["content"][0]
    assert tool_result["type"] == "tool_result"
    import json
    parsed = json.loads(tool_result["content"])
    assert len(parsed) == 21  # 20 kept + 1 marker
    assert parsed[-1] == "...30 more omitted"


def test_code_fenced_block_left_verbatim_even_when_old(monkeypatch):
    # Force a very high threshold so every prose block would be stubbed if it
    # were treated as prose - the code block must survive anyway.
    monkeypatch.setenv("WINNOW_RELEVANCE_THRESHOLD", "0.99")
    body = fixtures.code_chat()
    out = trimmer.trim(fixtures.code_chat())
    assert out["messages"][1]["content"] == body["messages"][1]["content"]
    assert "```" in out["messages"][1]["content"]


def test_low_relevance_prose_is_replaced_with_stub(monkeypatch):
    # With an artificially high threshold, older prose that isn't verbatim
    # code or JSON must be replaced by a deterministic stub explaining why.
    monkeypatch.setenv("WINNOW_RELEVANCE_THRESHOLD", "0.99")
    out = trimmer.trim(fixtures.long_prose_chat())
    first_reply = out["messages"][1]["content"]
    assert first_reply == "[winnow: older message omitted, low relevance to current topic]"
