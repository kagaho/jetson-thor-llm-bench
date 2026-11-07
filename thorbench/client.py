"""Minimal, dependency-free client for a vLLM OpenAI-compatible API."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class APIError(Exception):
    """An API connection, protocol, or server error."""


@dataclass
class Sample:
    """Timing and token information from a single request (no prompt text)."""

    elapsed_s: float
    ttft_s: float | None
    ttfc_s: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    reasoning_tokens: int | None
    finish_reason: str | None
    content: str
    streamed: bool

    def metrics(self) -> dict[str, Any]:
        completion = self.completion_tokens
        reasoning = self.reasoning_tokens
        decode_s = self.elapsed_s - self.ttft_s if self.ttft_s is not None else None
        return {
            "elapsed_s": round(self.elapsed_s, 4),
            "ttft_s": round(self.ttft_s, 4) if self.ttft_s is not None else None,
            "ttfc_s": round(self.ttfc_s, 4) if self.ttfc_s is not None else None,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": completion,
            "reasoning_tokens": reasoning,
            "visible_tokens": completion - reasoning if completion is not None and reasoning is not None else None,
            "effective_tokens_s": round(completion / self.elapsed_s, 3) if completion is not None and self.elapsed_s > 0 else None,
            "decode_tokens_s": round((completion - 1) / decode_s, 3)
            if completion is not None and completion > 1 and decode_s and decode_s > 0 else None,
            "finish_reason": self.finish_reason,
            "streamed": self.streamed,
        }


def _usage(payload: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    usage = payload.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return usage.get("prompt_tokens"), usage.get("completion_tokens"), details.get("reasoning_tokens")


class VLLMClient:
    def __init__(self, base_url: str, model: str, timeout: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.api_key = os.environ.get("THOR_BENCH_API_KEY", "")
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")

    def _request(self, path: str, payload: dict | None = None):
        raw = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json"}
        if raw is not None:
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = Request(self.base_url + path, data=raw, headers=headers, method="POST" if raw is not None else "GET")
        try:
            return urlopen(req, timeout=self.timeout)
        except HTTPError as exc:
            # Avoid logging server response bodies, which can contain prompts or credentials.
            raise APIError(f"HTTP {exc.code} from {path}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise APIError(f"Connection failure for {path}: {type(exc).__name__}") from exc

    def health(self) -> bool:
        with self._request("/health") as response:
            return response.status == 200

    def models(self) -> list[dict[str, Any]]:
        with self._request("/v1/models") as response:
            return json.load(response).get("data", [])

    def chat(self, payload: dict[str, Any], streaming: bool = True) -> Sample:
        req = {"model": self.model, **payload, "stream": streaming}
        if streaming:
            req["stream_options"] = {"include_usage": True}
            return self._stream(req)
        return self._nonstream(req)

    def _nonstream(self, request: dict[str, Any]) -> Sample:
        start = time.monotonic()
        with self._request("/v1/chat/completions", request) as response:
            data = json.load(response)
        elapsed = time.monotonic() - start
        choices = data.get("choices") or []
        if not choices:
            raise APIError("Chat response contained no choices")
        first = choices[0]
        p, c, r = _usage(data)
        return Sample(elapsed, None, None, p, c, r, first.get("finish_reason"), first.get("message", {}).get("content") or "", False)

    def _stream(self, request: dict[str, Any]) -> Sample:
        start = time.monotonic()
        first_token_at = None
        first_content_at = None
        content_parts = []
        finish_reason = None
        p = c = r = None
        with self._request("/v1/chat/completions", request) as response:
            # Each SSE data event may be split across multiple data: lines.
            data_lines: list[str] = []
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
                    continue
                if line and not line.startswith(":"):
                    continue
                if not data_lines:
                    continue
                event = "\n".join(data_lines)
                data_lines.clear()
                if event == "[DONE]":
                    break
                try:
                    chunk = json.loads(event)
                except json.JSONDecodeError:
                    raise APIError("Invalid streaming JSON event") from None
                if chunk.get("error"):
                    raise APIError("Streaming API returned an error")
                if chunk.get("usage"):
                    p, c, r = _usage(chunk)
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    reasoning = delta.get("reasoning") or delta.get("reasoning_content") or ""
                    content = delta.get("content") or ""
                    if (reasoning or content) and first_token_at is None:
                        first_token_at = time.monotonic()
                    if content:
                        if first_content_at is None:
                            first_content_at = time.monotonic()
                        content_parts.append(content)
                    if choice.get("finish_reason") is not None:
                        finish_reason = choice["finish_reason"]
            # Some servers may finish without the terminating blank SSE line.
        elapsed = time.monotonic() - start
        return Sample(
            elapsed_s=elapsed,
            ttft_s=first_token_at - start if first_token_at is not None else None,
            ttfc_s=first_content_at - start if first_content_at is not None else None,
            prompt_tokens=p,
            completion_tokens=c,
            reasoning_tokens=r,
            finish_reason=finish_reason,
            content="".join(content_parts),
            streamed=True,
        )
