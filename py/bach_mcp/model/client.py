"""
client.py
---------
The one place that talks to the model: a streaming chat request with tools,
in the OpenAI format both backends speak (mlx_lm.server and llama-server).
Sampling, the reply limit and the thinking switch come from [generation] in
bachmcp.toml and travel with every request.

stream() yields the reply as it is written:

    ("thinking", text)   a piece of the model's reasoning (only with reasoning = "on")
    ("text", text)       a piece of the answer
    ("calling", {...})   a tool call being written: its name and length so far
                         (llama-server streams these; mlx_lm.server sends a call when it is whole)
    ("reply", Reply)     at the end: the whole answer, its tool calls, why it ended, token counts
"""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

import httpx

from ..config import GenerationConfig


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]
    error: str = ""  # set when the arguments are not valid JSON (e.g. a reply cut off by the token limit)


@dataclass
class Reply:
    text: str = ""
    thinking: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish: str = ""  # "stop", "tool_calls" or "length" (the reply limit was reached)
    usage: Dict[str, int] = field(default_factory=dict)


def read_stream(lines: Iterable[str]) -> Iterator[Tuple[str, Any]]:
    """The events of an OpenAI-style server-sent stream, given its lines."""
    reply = Reply()
    calls: Dict[int, Dict[str, str]] = {}
    for line in lines:
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        chunk = json.loads(data)
        if chunk.get("error"):
            error = chunk["error"]
            raise RuntimeError(error.get("message", str(error)) if isinstance(error, dict) else str(error))
        if chunk.get("usage"):
            reply.usage = {k: int(v) for k, v in chunk["usage"].items() if isinstance(v, (int, float))}
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            thinking = delta.get("reasoning_content") or delta.get("reasoning")  # llama-server | mlx_lm.server
            if thinking:
                reply.thinking += thinking
                yield "thinking", thinking
            if delta.get("content"):
                reply.text += delta["content"]
                yield "text", delta["content"]
            for tc in delta.get("tool_calls") or []:
                call = calls.setdefault(int(tc.get("index", len(calls))), {"id": "", "name": "", "arguments": ""})
                fn = tc.get("function") or {}
                call["id"] = tc.get("id") or call["id"]
                call["name"] += fn.get("name") or ""
                arguments = fn.get("arguments")
                call["arguments"] += arguments if isinstance(arguments, str) else json.dumps(arguments or {})
                yield "calling", {"name": call["name"], "chars": len(call["arguments"])}
            if choice.get("finish_reason"):
                reply.finish = choice["finish_reason"]
    for index in sorted(calls):
        call = calls[index]
        try:
            arguments = json.loads(call["arguments"]) if call["arguments"].strip() else {}
            error = "" if isinstance(arguments, dict) else "the arguments are not a JSON object"
        except json.JSONDecodeError as exc:
            arguments, error = {}, f"the arguments are not valid JSON ({exc.msg} at character {exc.pos})"
        reply.tool_calls.append(ToolCall(id=call["id"] or f"call_{index}", name=call["name"],
                                         arguments=arguments if isinstance(arguments, dict) else {}, error=error))
    if reply.tool_calls and reply.finish != "length":
        reply.finish = "tool_calls"
    yield "reply", reply


class ModelClient:
    """Sends a conversation to the model server and streams back its reply."""

    def __init__(self, base_url: str, generation: GenerationConfig, model: Optional[str] = None,
                 timeout_seconds: float = 1800.0) -> None:
        self.base_url = base_url.rstrip("/")  # ".../v1"
        self.generation = generation
        self.model = model
        self.timeout = httpx.Timeout(timeout_seconds, connect=10.0)
        self._response: Optional[httpx.Response] = None

    def request(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]],
                max_tokens: Optional[int] = None) -> Dict[str, Any]:
        g = self.generation
        body: Dict[str, Any] = {
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "max_tokens": max_tokens or g.max_tokens,
            "temperature": g.temperature,
            "top_p": g.top_p,
            "top_k": g.top_k,
            "presence_penalty": g.presence_penalty,
            "chat_template_kwargs": {"enable_thinking": g.reasoning == "on"},
        }
        if self.model:
            body["model"] = self.model
        if tools:
            body["tools"] = tools
        return body

    def stream(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]],
               max_tokens: Optional[int] = None) -> Iterator[Tuple[str, Any]]:
        body = self.request(messages, tools, max_tokens)
        with httpx.stream("POST", f"{self.base_url}/chat/completions", json=body, timeout=self.timeout) as response:
            if response.status_code != 200:
                detail = response.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"the model server answered {response.status_code}: {detail[:500]}")
            self._response = response
            try:
                yield from read_stream(response.iter_lines())
            finally:
                self._response = None

    def cancel(self) -> None:
        """Stop the reply being read, from another thread: its stream ends with an error at once.

        The socket is shut down rather than the response closed: closing waits for the
        reading thread, which may be blocked while the model writes a tool call in silence.
        """
        response = self._response
        stream = response.extensions.get("network_stream") if response is not None else None
        sock = stream.get_extra_info("socket") if stream is not None else None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


__all__ = ["ModelClient", "Reply", "ToolCall", "read_stream"]
