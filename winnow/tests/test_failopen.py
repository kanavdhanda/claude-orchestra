import httpx
from fastapi.testclient import TestClient

from winnow import scoring, server, trimmer
from winnow.tests import fixtures


def test_scoring_error_falls_back_to_original(monkeypatch):
    monkeypatch.setenv("WINNOW_TRIM_PROSE", "true")
    def boom(*args, **kwargs):
        raise RuntimeError("scoring exploded")

    monkeypatch.setattr(scoring, "score", boom)
    body = fixtures.long_prose_chat()
    out = trimmer.trim(fixtures.long_prose_chat())
    assert out == body  # unmodified, and trim() must not raise


def test_truncation_error_falls_back_to_original(monkeypatch):
    monkeypatch.setenv("WINNOW_STUB_OLD_TOOL_RESULTS", "false")
    def boom(*args, **kwargs):
        raise RuntimeError("truncation exploded")

    monkeypatch.setattr("winnow.json_truncate.truncate_json", boom)
    body = fixtures.json_tool_chat()
    out = trimmer.trim(fixtures.json_tool_chat())
    assert out == body


def test_malformed_json_passes_through_raw_bytes_at_server_layer(monkeypatch):
    captured = {}

    async def fake_forward(method, url, headers, content):
        captured["content"] = content
        return httpx.Response(200, content=b'{"ok": true}', headers={"content-type": "application/json"})

    monkeypatch.setattr(server, "_forward", fake_forward)
    monkeypatch.setenv("WINNOW_ENABLED", "true")

    client = TestClient(server.app)
    raw = b'{"messages": [this is not valid json'
    resp = client.post("/v1/messages", content=raw, headers={"content-type": "application/json"})

    assert resp.status_code == 200
    assert captured["content"] == raw
