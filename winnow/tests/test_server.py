import json

import httpx
from fastapi.testclient import TestClient

from winnow import cli, config, server
from winnow.tests import fixtures


def _fake_forward_factory(captured):
    async def fake_forward(method, url, headers, content):
        captured["content"] = content
        return httpx.Response(200, content=b'{"ok": true}', headers={"content-type": "application/json"})

    return fake_forward


def test_kill_switch_disables_trimming(monkeypatch, tmp_path):
    monkeypatch.setenv("WINNOW_DB_PATH", str(tmp_path / "winnow.db"))
    monkeypatch.setenv("WINNOW_ENABLED", "false")
    captured = {}
    monkeypatch.setattr(server, "_forward", _fake_forward_factory(captured))

    client = TestClient(server.app)
    raw = json.dumps(fixtures.long_prose_chat()).encode()
    resp = client.post("/v1/messages", content=raw, headers={"content-type": "application/json"})

    assert resp.status_code == 200
    assert captured["content"] == raw  # byte-for-byte passthrough, nothing trimmed


def test_non_messages_paths_are_pure_passthrough(monkeypatch, tmp_path):
    monkeypatch.setenv("WINNOW_DB_PATH", str(tmp_path / "winnow.db"))
    monkeypatch.setenv("WINNOW_ENABLED", "true")
    captured = {}
    monkeypatch.setattr(server, "_forward", _fake_forward_factory(captured))

    client = TestClient(server.app)
    raw = json.dumps(fixtures.long_prose_chat()).encode()
    resp = client.post("/v1/other-endpoint", content=raw, headers={"content-type": "application/json"})

    assert resp.status_code == 200
    assert captured["content"] == raw


def test_stats_endpoint_and_cli_report_logged_requests(monkeypatch, tmp_path, capsys):
    db_path = str(tmp_path / "winnow.db")
    monkeypatch.setenv("WINNOW_DB_PATH", db_path)
    monkeypatch.setenv("WINNOW_ENABLED", "true")
    captured = {}
    monkeypatch.setattr(server, "_forward", _fake_forward_factory(captured))

    client = TestClient(server.app)
    raw = json.dumps(fixtures.long_prose_chat()).encode()
    client.post("/v1/messages", content=raw, headers={"content-type": "application/json"})

    resp = client.get("/winnow/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["requests"] == 1
    assert data["tokens_before_total"] > 0

    cli.main(["stats"])
    out = json.loads(capsys.readouterr().out)
    assert out["requests"] == 1


def test_default_mode_is_thorough(monkeypatch):
    monkeypatch.delenv("WINNOW_MODE", raising=False)
    assert config.mode() == "thorough"
