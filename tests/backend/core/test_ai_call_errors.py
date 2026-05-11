import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from core import ai_call


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload.encode() if isinstance(payload, str) else payload
        self.status_code = status_code
        self.content = self.payload

    def json(self):
        return json.loads(self.payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code}",
                request=httpx.Request("POST", "https://test"),
                response=httpx.Response(self.status_code),
            )


class _FakeClient:
    def __init__(self, response_or_factory):
        self._resp = response_or_factory

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def post(self, *a, **kw):
        resp = self._resp() if callable(self._resp) else self._resp
        if isinstance(resp, Exception):
            raise resp
        return resp


def _make_client(response_or_factory):
    return lambda **kwargs: _FakeClient(response_or_factory)


def _ok_response():
    return _FakeResponse(json.dumps({"choices": [{"message": {"content": "ok"}}]}))


def test_chat_retries_connection_error_once(monkeypatch):
    calls = {"count": 0}

    def _flaky_post(*a, **kw):
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.ConnectError("temporary down")
        return _ok_response()

    monkeypatch.setattr("core.ai_call.httpx.Client", _make_client(_flaky_post))

    result = ai_call.chat("zhipu", "key", "https://example.test", "model", [{"role": "user", "content": "hi"}])

    assert result == {"ok": True, "content": "ok"}
    assert calls["count"] == 2


def test_chat_classifies_timeout(monkeypatch):
    def _timeout_post(*a, **kw):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("core.ai_call.httpx.Client", _make_client(_timeout_post))

    result = ai_call.chat("zhipu", "key", "https://example.test", "model", [], timeout=1)

    assert result["ok"] is False
    assert result["error_code"] == "AI_TIMEOUT"
    assert result["error_category"] == "timeout"


def test_chat_classifies_bad_response_json(monkeypatch):
    monkeypatch.setattr("core.ai_call.httpx.Client", _make_client(_FakeResponse(b"not-json")))

    result = ai_call.chat("zhipu", "key", "https://example.test", "model", [])

    assert result["ok"] is False
    assert result["error_code"] == "AI_RESPONSE_JSON_INVALID"
    assert result["error_category"] == "parse"


def test_chat_writes_audit_log_on_success(monkeypatch):
    records = []
    monkeypatch.setattr(ai_call, "_write_ai_call_log", lambda **kwargs: records.append(kwargs))
    monkeypatch.setattr("core.ai_call.httpx.Client", _make_client(_ok_response()))

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

    def _timeout_post(*a, **kw):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("core.ai_call.httpx.Client", _make_client(_timeout_post))

    result = ai_call.chat("zhipu", "key", "https://example.test", "model", [], timeout=1)

    assert result["ok"] is False
    assert records[-1]["status"] == "failed"
    assert records[-1]["error_code"] == "AI_TIMEOUT"
