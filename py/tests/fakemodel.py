"""A stand-in for the model server, for the tests: scripted replies in the OpenAI stream format."""

import json

from bach_mcp.model.client import read_stream


def chunk(delta=None, finish=None, usage=None):
    out = {"choices": [{"index": 0, "delta": delta or {}, "finish_reason": finish}]}
    if usage:
        out["usage"] = usage
    return out


def text_reply(text, finish="stop", thinking=""):
    chunks = [chunk({"reasoning_content": thinking})] if thinking else []
    words = text.split(" ")
    chunks += [chunk({"content": w + (" " if i < len(words) - 1 else "")}) for i, w in enumerate(words)]
    return chunks + [chunk(finish=finish, usage={"prompt_tokens": 100, "completion_tokens": 7})]


def tool_reply(name, arguments, text="", call_id="call_1"):
    raw = json.dumps(arguments) if not isinstance(arguments, str) else arguments
    half = len(raw) // 2
    chunks = [chunk({"content": text})] if text else []
    chunks += [chunk({"tool_calls": [{"index": 0, "id": call_id, "function": {"name": name, "arguments": raw[:half]}}]}),
               chunk({"tool_calls": [{"index": 0, "function": {"arguments": raw[half:]}}]}),
               chunk(finish="tool_calls", usage={"prompt_tokens": 100, "completion_tokens": 30})]
    return chunks


def sse_lines(chunks):
    return [f"data: {json.dumps(c)}" for c in chunks] + ["data: [DONE]"]


class FakeClient:
    """Answers each request with the next scripted reply, and keeps every request."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests = []
        self.cancelled = 0

    def stream(self, messages, tools, max_tokens=None):
        self.requests.append({"messages": [dict(m) for m in messages], "tools": tools, "max_tokens": max_tokens})
        if not self.replies:
            raise RuntimeError("no scripted reply left")
        yield from read_stream(sse_lines(self.replies.pop(0)))

    def cancel(self):
        self.cancelled += 1
