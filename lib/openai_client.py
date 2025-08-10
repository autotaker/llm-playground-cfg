from __future__ import annotations

import os
import time
import random
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openai import APIStatusError, APIConnectionError, RateLimitError


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")


def _get_client() -> OpenAI:
    # The OpenAI SDK reads OPENAI_API_KEY from env automatically.
    return OpenAI()


def _retryable(exc: Exception) -> bool:
    return isinstance(exc, (APIConnectionError, RateLimitError, APIStatusError))


def _backoff_sleep(attempt: int, base: float = 0.5, cap: float = 8.0) -> None:
    # Exponential backoff with jitter
    sleep = min(cap, base * (2 ** attempt))
    time.sleep(sleep * (0.5 + random.random() / 2))


def responses_create(
    *,
    input: str,
    model: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    max_retries: int = 3,
) -> Any:
    client = _get_client()
    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return client.responses.create(
                model=model or DEFAULT_MODEL,
                input=input,
                tools=tools,
            )
        except Exception as e:  # noqa: BLE001
            last_err = e
            if not _retryable(e) or attempt == max_retries:
                raise
            _backoff_sleep(attempt)
    # Should not reach here
    if last_err:
        raise last_err


def output_text(resp: Any) -> str:
    return getattr(resp, "output_text", None) or getattr(resp, "output", None) or str(resp)


def extract_usage(resp: Any) -> tuple[Optional[int], Optional[int]]:
    """Return (input_tokens, output_tokens) if available, else (None, None)."""
    u = getattr(resp, "usage", None)
    if u is None and isinstance(resp, dict):
        u = resp.get("usage")

    def _get(obj: Any, key: str) -> Optional[int]:
        if obj is None:
            return None
        if hasattr(obj, key):
            val = getattr(obj, key)
        elif isinstance(obj, dict):
            val = obj.get(key)
        else:
            val = None
        try:
            return int(val) if val is not None else None
        except Exception:
            return None

    return _get(u, "input_tokens"), _get(u, "output_tokens")
