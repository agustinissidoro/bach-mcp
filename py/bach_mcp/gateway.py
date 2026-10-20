"""
gateway.py
----------
The small HTTP app that stands between the llama.cpp web chat and the model,
on the chat's port. With either backend it puts each request in its mode
(/score or /algo: that mode's part of the skill and its tools, see modes.py)
and adds the instrument docs to the messages that name an instrument (see
docs.py).

With the llama backend (`create_llama_gateway_app`) it is a plain proxy:
every request goes to llama-server unchanged, except that the chat requests
get the docs.

With the Ollama backend (`create_gateway_app`), which runs MLX models on
Apple Silicon, it also replaces llama-server's API:

    - answers /props and /v1/models itself, from bach.toml;
    - translates /v1/chat/completions to Ollama's native /api/chat and streams
      the reply back in the OpenAI format the chat expects (text, reasoning,
      tool calls, timings);
    - forwards every other GET (the chat's own HTML/JS) to a llama-server that
      runs without a model, only to serve those files.

Ollama's native API is used rather than its OpenAI-compatible one because only
the native one accepts the context size and the thinking switch per request.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from .config import BachConfig
from .docs import DocLibrary
from .modes import apply_mode, split_prefix

_THINK_LEVELS = ("low", "medium", "high", "xhigh")
_CHAT_PATHS = ("/v1/chat/completions", "/chat/completions")
# Hop-by-hop headers and the ones the proxy recomputes.
_SKIP_REQUEST_HEADERS = ("host", "content-length", "connection")
_SKIP_RESPONSE_HEADERS = ("content-length", "transfer-encoding", "connection")


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": {"message": message, "type": "server_error", "code": status}}, status_code=status)


def with_docs(body: Dict[str, Any], library: Optional[DocLibrary]) -> Dict[str, Any]:
    """Return the chat request with the instrument docs added to its user messages."""
    messages = body.get("messages")
    if library is None or not isinstance(messages, list):
        return body
    augmented, added = library.augment(messages)
    if added and messages and messages[-1].get("role") == "user":
        print(f"  docs      {', '.join(added)}", flush=True)
    return {**body, "messages": augmented}


class ModeSwitch:
    """Puts chat requests in their mode. The skill is read once, when the chat is set up with it."""

    def __init__(self, config: BachConfig) -> None:
        self.full = config.system_prompt()
        self.raw = config.skill_source()

    def __call__(self, body: Dict[str, Any]) -> Dict[str, Any]:
        messages = body.get("messages")
        moded, mode = apply_mode(body, self.full, self.raw)
        if isinstance(messages, list) and messages and messages[-1].get("role") == "user":
            content = messages[-1].get("content")
            text = content if isinstance(content, str) else ""
            if isinstance(content, list):
                text = next((str(p.get("text", "")) for p in content if isinstance(p, dict) and p.get("type") == "text"), "")
            if split_prefix(text)[0]:
                print(f"  mode      {mode}", flush=True)
        return moded


def to_ollama_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert OpenAI chat messages to Ollama's native message format."""
    out: List[Dict[str, Any]] = []
    call_names: Dict[str, str] = {}
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content")
        images: List[str] = []
        if isinstance(content, list):
            texts = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "text":
                    texts.append(str(part.get("text", "")))
                elif part.get("type") == "image_url":
                    url = (part.get("image_url") or {}).get("url", "")
                    if url.startswith("data:") and "," in url:
                        images.append(url.split(",", 1)[1])
            content = "\n".join(texts)
        msg: Dict[str, Any] = {"role": role, "content": content or ""}
        if images:
            msg["images"] = images
        if role == "assistant" and m.get("tool_calls"):
            calls = []
            for tc in m["tool_calls"]:
                fn = tc.get("function") or {}
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args) if args.strip() else {}
                    except json.JSONDecodeError:
                        args = {}
                call_names[str(tc.get("id", ""))] = fn.get("name", "")
                calls.append({"id": tc.get("id"), "function": {"name": fn.get("name", ""), "arguments": args}})
            msg["tool_calls"] = calls
        if role == "tool":
            name = call_names.get(str(m.get("tool_call_id", "")))
            if name:
                msg["tool_name"] = name
        out.append(msg)
    return out


def build_ollama_request(body: Dict[str, Any], config: BachConfig) -> Dict[str, Any]:
    """Build the /api/chat payload from a web-chat request and bach.toml."""
    g = config.generation
    options: Dict[str, Any] = {
        "num_ctx": config.model.context_size,
        "temperature": body.get("temperature", g.temperature),
        "top_p": body.get("top_p", g.top_p),
        "top_k": body.get("top_k", g.top_k),
    }
    max_tokens = body.get("max_tokens", g.max_tokens)
    if isinstance(max_tokens, (int, float)) and max_tokens > 0:
        options["num_predict"] = int(max_tokens)

    request: Dict[str, Any] = {
        "model": config.model.ollama_model,
        "messages": to_ollama_messages(body.get("messages") or []),
        "stream": True,
        "options": options,
        "keep_alive": config.ollama.keep_alive,
    }
    if body.get("tools"):
        request["tools"] = body["tools"]

    # The chat's own thinking switch decides; bach.toml supplies its default and the level.
    wanted = (body.get("chat_template_kwargs") or {}).get("enable_thinking")
    if wanted is None and g.reasoning != "auto":
        wanted = g.reasoning != "off"
    if wanted is not None:
        request["think"] = (g.reasoning if g.reasoning in _THINK_LEVELS else True) if wanted else False
    return request


def create_gateway_app(config: BachConfig, ui_origin: str, capabilities: Optional[List[str]] = None) -> Starlette:
    """Create the app that serves the web chat on top of Ollama.

    ui_origin: base URL of the model-less llama-server that serves the chat's files.
    capabilities: what Ollama reports for the model ("thinking", "vision", "tools", ...).
    """
    capabilities = capabilities or []
    alias = config.model.alias
    client = httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0))
    static_cache: Dict[str, Response] = {}
    library = DocLibrary() if config.chat.docs else None
    with_mode = ModeSwitch(config)

    async def props(request: Request) -> JSONResponse:
        g = config.generation
        return JSONResponse({
            "role": "model",
            "model_alias": alias,
            "model_path": config.model.ollama_model,
            "total_slots": 1,
            "default_generation_settings": {
                "n_ctx": config.model.context_size,
                "params": {"temperature": g.temperature, "top_p": g.top_p, "top_k": g.top_k,
                           "n_predict": g.max_tokens},
            },
            "modalities": {"vision": "vision" in capabilities, "audio": False},
            # The chat shows its thinking switch when the template mentions this variable.
            "chat_template": "{{ enable_thinking }}" if "thinking" in capabilities else "",
            "build_info": "bach-gateway (ollama)",
            "cors_proxy_enabled": False,
            "ui_settings": config.webui_settings(),
        })

    async def models(request: Request) -> JSONResponse:
        entry = {"id": alias, "object": "model", "created": int(time.time()), "owned_by": "ollama"}
        return JSONResponse({"object": "list", "data": [entry], "models": [{"name": alias, "model": alias}]})

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def slots(request: Request) -> JSONResponse:
        return JSONResponse([])

    async def chat(request: Request) -> Response:
        try:
            body = await request.json()
        except ValueError:
            return _error(400, "request body is not valid JSON")
        payload = build_ollama_request(with_docs(with_mode(body), library), config)
        upstream_request = client.build_request("POST", f"{config.ollama.url}/api/chat", json=payload)
        try:
            upstream = await client.send(upstream_request, stream=True)
        except httpx.HTTPError as exc:
            return _error(502, f"Cannot reach Ollama at {config.ollama.url} ({exc}). Is the Ollama app running?")
        if upstream.status_code != 200:
            detail = (await upstream.aread()).decode("utf-8", errors="replace")
            await upstream.aclose()
            try:
                detail = json.loads(detail).get("error", detail)
            except ValueError:
                pass
            return _error(upstream.status_code, f"Ollama: {detail}")

        completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())

        def chunk(delta: Dict[str, Any], finish: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
            return {"id": completion_id, "object": "chat.completion.chunk", "created": created, "model": alias,
                    "choices": [{"index": 0, "delta": delta, "finish_reason": finish}], **extra}

        async def events() -> AsyncIterator[Dict[str, Any]]:
            """Yield OpenAI-style chunks translated from Ollama's NDJSON stream."""
            called = False
            n_calls = 0
            yield chunk({"role": "assistant", "content": None})
            try:
                async for line in upstream.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    if data.get("error"):
                        yield {"error": {"message": f"Ollama: {data['error']}", "type": "server_error", "code": 500}}
                        return
                    message = data.get("message") or {}
                    if message.get("thinking"):
                        yield chunk({"reasoning_content": message["thinking"]})
                    if message.get("content"):
                        yield chunk({"content": message["content"]})
                    for tc in message.get("tool_calls") or []:
                        fn = tc.get("function") or {}
                        called = True
                        yield chunk({"tool_calls": [{
                            "index": n_calls,
                            "id": tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                            "type": "function",
                            "function": {"name": fn.get("name", ""),
                                         "arguments": json.dumps(fn.get("arguments") or {}, ensure_ascii=False)},
                        }]})
                        n_calls += 1
                    if data.get("done"):
                        prompt_n, predicted_n = data.get("prompt_eval_count", 0), data.get("eval_count", 0)
                        prompt_ms = data.get("prompt_eval_duration", 0) / 1e6
                        predicted_ms = data.get("eval_duration", 0) / 1e6
                        finish = "tool_calls" if called else ("length" if data.get("done_reason") == "length" else "stop")
                        yield chunk(
                            {}, finish,
                            usage={"prompt_tokens": prompt_n, "completion_tokens": predicted_n,
                                   "total_tokens": prompt_n + predicted_n},
                            timings={"prompt_n": prompt_n, "prompt_ms": prompt_ms,
                                     "predicted_n": predicted_n, "predicted_ms": predicted_ms,
                                     "predicted_per_second": predicted_n / (predicted_ms / 1000) if predicted_ms else 0,
                                     "prompt_per_second": prompt_n / (prompt_ms / 1000) if prompt_ms else 0},
                        )
            finally:
                await upstream.aclose()

        if body.get("stream", False):
            async def sse() -> AsyncIterator[bytes]:
                async for event in events():
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
                yield b"data: [DONE]\n\n"
            return StreamingResponse(sse(), media_type="text/event-stream",
                                     headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

        # Non-streaming: fold the chunks into one message.
        message: Dict[str, Any] = {"role": "assistant", "content": ""}
        finish, extra = "stop", {}
        async for event in events():
            if "error" in event:
                return JSONResponse(event, status_code=500)
            choice = event["choices"][0]
            delta = choice["delta"]
            if delta.get("content"):
                message["content"] += delta["content"]
            if delta.get("reasoning_content"):
                message["reasoning_content"] = message.get("reasoning_content", "") + delta["reasoning_content"]
            if delta.get("tool_calls"):
                message.setdefault("tool_calls", []).extend(
                    {k: v for k, v in tc.items() if k != "index"} for tc in delta["tool_calls"])
            if choice["finish_reason"]:
                finish = choice["finish_reason"]
                extra = {k: event[k] for k in ("usage", "timings") if k in event}
        return JSONResponse({"id": completion_id, "object": "chat.completion", "created": created, "model": alias,
                             "choices": [{"index": 0, "message": message, "finish_reason": finish}], **extra})

    async def static(request: Request) -> Response:
        """Serve the chat's own files from the model-less llama-server."""
        path = request.url.path
        if path in static_cache:
            return static_cache[path]
        try:
            upstream = await client.get(f"{ui_origin}{path}")
        except httpx.HTTPError as exc:
            return _error(502, f"web chat files are not available ({exc})")
        headers = {k: v for k, v in upstream.headers.items()
                   if k.lower() in ("content-type", "cache-control", "etag")}
        response = Response(upstream.content, status_code=upstream.status_code, headers=headers)
        if upstream.status_code == 200:
            static_cache[path] = response
        return response

    async def not_supported(request: Request) -> JSONResponse:
        return _error(404, "not available with the Ollama backend")

    app = Starlette(routes=[
        Route("/props", props),
        Route("/v1/models", models),
        Route("/models", models),
        Route("/health", health),
        Route("/v1/health", health),
        Route("/slots", slots),
        Route("/v1/chat/completions", chat, methods=["POST"]),
        Route("/v1/{rest:path}", not_supported, methods=["GET", "POST"]),
        Route("/{rest:path}", static, methods=["GET"]),
    ])
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    return app


def create_llama_gateway_app(config: BachConfig, llama_origin: str) -> Starlette:
    """Create the proxy that stands in front of llama-server (llama backend).

    llama_origin: base URL of llama-server, which runs the model on an internal port.
    Everything is forwarded as it is, byte for byte and streamed; only the chat
    requests are put in their mode and get the instrument docs.
    """
    client = httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0))
    library = DocLibrary() if config.chat.docs else None
    with_mode = ModeSwitch(config)

    async def proxy(request: Request) -> Response:
        content = await request.body()
        if request.method == "POST" and request.url.path in _CHAT_PATHS:
            try:
                body = json.loads(content)
            except ValueError:
                body = None
            if isinstance(body, dict):
                content = json.dumps(with_docs(with_mode(body), library), ensure_ascii=False).encode("utf-8")
        url = f"{llama_origin}{request.url.path}"
        if request.url.query:
            url += f"?{request.url.query}"
        headers = {k: v for k, v in request.headers.items() if k.lower() not in _SKIP_REQUEST_HEADERS}
        try:
            upstream = await client.send(
                client.build_request(request.method, url, headers=headers, content=content), stream=True)
        except httpx.HTTPError as exc:
            return _error(502, f"Cannot reach llama-server at {llama_origin} ({exc}). See logs/llama-server.log.")

        async def relay() -> AsyncIterator[bytes]:
            try:
                async for data in upstream.aiter_raw():
                    yield data
            finally:
                await upstream.aclose()

        headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _SKIP_RESPONSE_HEADERS}
        return StreamingResponse(relay(), status_code=upstream.status_code, headers=headers)

    methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
    return Starlette(routes=[Route("/{rest:path}", proxy, methods=methods)], on_shutdown=[client.aclose])
