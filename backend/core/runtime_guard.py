"""Runtime guard: block LLM/network calls while executing approved artifacts."""
from __future__ import annotations

import contextlib
import os
import sys
import urllib.request
from typing import Iterator


class RuntimeAICallBlocked(RuntimeError):
    """Raised when code attempts an AI/network call during artifact runtime."""


def _blocked(*args, **kwargs):
    raise RuntimeAICallBlocked("Runtime 阶段禁止调用 AI / 外部网络")


@contextlib.contextmanager
def no_ai_runtime() -> Iterator[None]:
    """Temporarily block common AI/network entrypoints."""
    original_urlopen = urllib.request.urlopen
    urllib.request.urlopen = _blocked

    requests_mod = sys.modules.get("requests")
    original_requests_post = getattr(requests_mod, "post", None) if requests_mod else None
    if requests_mod is not None:
        requests_mod.post = _blocked

    ai_call_mod = sys.modules.get("core.ai_call")
    original_ai_urlopen = getattr(ai_call_mod, "urlopen", None) if ai_call_mod else None
    original_ai_chat = getattr(ai_call_mod, "chat", None) if ai_call_mod else None
    if ai_call_mod is not None:
        ai_call_mod.urlopen = _blocked
        ai_call_mod.chat = _blocked

    try:
        yield
    finally:
        urllib.request.urlopen = original_urlopen
        if requests_mod is not None and original_requests_post is not None:
            requests_mod.post = original_requests_post
        if ai_call_mod is not None:
            if original_ai_urlopen is not None:
                ai_call_mod.urlopen = original_ai_urlopen
            if original_ai_chat is not None:
                ai_call_mod.chat = original_ai_chat


def activate_if_configured() -> None:
    """Permanently activate guard in CI/runtime when requested by env."""
    if os.environ.get("ZF_RUNTIME_NO_AI") != "1":
        return
    urllib.request.urlopen = _blocked
    requests_mod = sys.modules.get("requests")
    if requests_mod is not None:
        requests_mod.post = _blocked
    ai_call_mod = sys.modules.get("core.ai_call")
    if ai_call_mod is not None:
        ai_call_mod.urlopen = _blocked
        ai_call_mod.chat = _blocked


activate_if_configured()
