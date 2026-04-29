import json
import socket
import sys
from pathlib import Path
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from core import ai_call


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return self.payload


def test_chat_retries_connection_error_once(monkeypatch):
    calls = {"count": 0}

    def fake_urlopen(_req, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise URLError("temporary down")
        return _Response(json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode())

    monkeypatch.setattr(ai_call, "urlopen", fake_urlopen)

    result = ai_call.chat("zhipu", "key", "https://example.test", "model", [{"role": "user", "content": "hi"}])

    assert result == {"ok": True, "content": "ok"}
    assert calls["count"] == 2


def test_chat_classifies_timeout(monkeypatch):
    monkeypatch.setattr(
        ai_call,
        "urlopen",
        lambda _req, timeout: (_ for _ in ()).throw(URLError(socket.timeout("timed out"))),
    )

    result = ai_call.chat("zhipu", "key", "https://example.test", "model", [], timeout=1)

    assert result["ok"] is False
    assert result["error_code"] == "AI_TIMEOUT"
    assert result["error_category"] == "timeout"


def test_chat_classifies_bad_response_json(monkeypatch):
    monkeypatch.setattr(ai_call, "urlopen", lambda _req, timeout: _Response(b"not-json"))

    result = ai_call.chat("zhipu", "key", "https://example.test", "model", [])

    assert result["ok"] is False
    assert result["error_code"] == "AI_RESPONSE_JSON_INVALID"
    assert result["error_category"] == "parse"


def test_chat_writes_audit_log_on_success(monkeypatch):
    records = []
    monkeypatch.setattr(ai_call, "_write_ai_call_log", lambda **kwargs: records.append(kwargs))
    monkeypatch.setattr(
        ai_call,
        "urlopen",
        lambda _req, timeout: _Response(json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()),
    )

    result = ai_call.chat("zhipu", "key", "https://example.test", "model", [{"role": "user", "content": "hi"}])

    assert result["ok"] is True
    assert records[0]["provider"] == "zhipu"
    assert records[0]["model"] == "model"
    assert records[0]["status"] == "success"
    assert records[0]["request_size"] > 0
    assert records[0]["response_size"] > 0
    assert records[0]["error_code"] is None


def test_chat_writes_audit_log_on_failure(monkeypatch):
    records = []
    monkeypatch.setattr(ai_call, "_write_ai_call_log", lambda **kwargs: records.append(kwargs))
    monkeypatch.setattr(
        ai_call,
        "urlopen",
        lambda _req, timeout: (_ for _ in ()).throw(URLError(socket.timeout("timed out"))),
    )

    result = ai_call.chat("zhipu", "key", "https://example.test", "model", [], timeout=1)

    assert result["ok"] is False
    assert records[-1]["status"] == "failed"
    assert records[-1]["error_code"] == "AI_TIMEOUT"
