"""
openai_compat.py
----------------
OpenAI-compatible chat-completions provider.

A single adapter for every backend that speaks the OpenAI
`/v1/chat/completions` API with tool calling. That includes:
    - Ollama       (http://localhost:11434/v1)
    - llama.cpp    (http://localhost:8080/v1)
    - vLLM         (http://localhost:8000/v1)
    - LM Studio, Groq, Together, OpenAI itself, ...

Because Ollama and llama.cpp both expose this endpoint, there is no separate
Ollama-specific provider — point `base_url` at whichever server you run.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional

import requests

from .provider import AssistantTurn, ToolCall, ToolSpec


def _log(msg: str) -> None:
    try:
        print(msg, file=sys.stderr)
    except Exception:
        pass


class OpenAICompatibleProvider:
    """Calls an OpenAI-compatible /chat/completions endpoint with tools."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: Optional[str] = None,
        temperature: float = 0.35,
        max_tokens: int = 2048,
        request_timeout_seconds: float = 300.0,
    ) -> None:
        # base_url should already include the version segment (e.g. ".../v1").
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.request_timeout_seconds = request_timeout_seconds

    @property
    def _endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    @staticmethod
    def _tool_payload(tools: List[ToolSpec]) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    def chat(self, messages: List[Dict[str, Any]], tools: List[ToolSpec]) -> AssistantTurn:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            payload["tools"] = self._tool_payload(tools)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            r = requests.post(
                self._endpoint,
                json=payload,
                headers=headers,
                timeout=self.request_timeout_seconds,
            )
            r.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                f"Cannot reach LLM server at {self.base_url}. "
                "Make sure it is running (e.g. `ollama serve`, or your llama.cpp/vLLM server)."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(
                f"LLM request timed out after {self.request_timeout_seconds}s "
                f"(model={self.model}). Try a smaller model or raise BACH_LLM_TIMEOUT."
            ) from exc
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            detail = ""
            if exc.response is not None:
                try:
                    detail = str(exc.response.json().get("error", "")).strip()
                except Exception:
                    detail = (exc.response.text or "").strip()
            msg = f"LLM HTTP error {status}"
            if detail:
                msg = f"{msg}: {detail}"
            raise RuntimeError(msg) from exc

        data = r.json()
        choices = data.get("choices") or [{}]
        message = (choices[0] or {}).get("message", {}) or {}
        content = message.get("content") or ""

        tool_calls: List[ToolCall] = []
        for i, tc in enumerate(message.get("tool_calls") or []):
            fn = tc.get("function", {}) or {}
            raw_args = fn.get("arguments", "")
            if isinstance(raw_args, dict):
                args = raw_args
            elif isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args) if raw_args.strip() else {}
                except json.JSONDecodeError:
                    _log(f"[OpenAICompatibleProvider] Could not parse tool args: {raw_args!r}")
                    args = {}
            else:
                args = {}
            tool_calls.append(
                ToolCall(
                    id=str(tc.get("id") or f"call_{i}"),
                    name=str(fn.get("name", "")),
                    arguments=args,
                )
            )

        return AssistantTurn(content=content, tool_calls=tool_calls)
