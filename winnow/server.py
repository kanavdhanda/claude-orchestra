"""FastAPI reverse proxy. Only POST /v1/messages goes through the trimmer;
every other path/method is a byte-for-byte passthrough. The fail-open
boundary (req 4) lives here: any error while parsing/trimming the body falls
back to forwarding the untouched original bytes — trimming must never be
able to break a real request.
"""
import json
import os

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

from winnow import config, store, tokencount, trimmer

app = FastAPI()

# Headers that describe the *wire* framing of the upstream response and must
# not be blindly replayed once we've already let httpx decode/rebuffer it.
_STRIP_RESPONSE_HEADERS = {"content-length", "content-encoding", "transfer-encoding", "connection"}
_STRIP_REQUEST_HEADERS = {"host", "content-length"}


async def _forward(method: str, url: str, headers: dict, content: bytes) -> httpx.Response:
    """Isolated so tests can monkeypatch it and inspect exactly what bytes
    would have gone out, without doing real network I/O."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        return await client.request(method, url, headers=headers, content=content)


def _make_sse_chunk(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8")


def _calculate_request_cost(model: str, tokens: int) -> float:
    # Default is Sonnet 5 pricing
    rate_cached = 0.30  # per Million tokens
    rate_uncached = 3.00 # per Million tokens
    
    m_lower = model.lower()
    if "opus" in m_lower:
        rate_cached = 0.50
        rate_uncached = 5.00
    elif "haiku" in m_lower:
        rate_cached = 0.03
        rate_uncached = 0.25
        
    effective_rate = (0.90 * rate_cached) + (0.10 * rate_uncached)
    return (tokens * effective_rate) / 1000000.0


async def sentinel_warning_stream(tokens: int, cost: float, limit: float, model: str):
    warning_text = (
        f"⚠️ [WINNOW SENTINEL WARNING]: This session has consumed approximately {tokens:,} tokens "
        f"on model '{model}' (est. cost ${cost:.4f} per turn), exceeding your safety budget cap of ${limit:.2f}.\n\n"
        f"To protect your wallet and Claude rate limits, Winnow intercepted this request.\n\n"
        f"To continue anyway, you can:\n"
        f"1. Start a fresh session (type '/clear' in Claude Code).\n"
        f"2. Increase your WINNOW_MAX_SESSION_COST environment variable (currently ${limit:.2f}).\n"
    )
    yield _make_sse_chunk("message_start", {
        "type": "message_start",
        "message": {
            "id": "msg_sentinel",
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": "claude-3-5-sonnet-20241022",
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0}
        }
    })
    yield _make_sse_chunk("content_block_start", {
        "type": "content_block_start",
        "index": 0,
        "content_block": {"type": "text", "text": ""}
    })
    yield _make_sse_chunk("content_block_delta", {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "text_delta", "text": warning_text}
    })
    yield _make_sse_chunk("content_block_stop", {
        "type": "content_block_stop",
        "index": 0
    })
    yield _make_sse_chunk("message_delta", {
        "type": "message_delta",
        "delta": {"stop_reason": "end_turn", "stop_sequence": None},
        "usage": {"output_tokens": 0}
    })
    yield _make_sse_chunk("message_stop", {
        "type": "message_stop"
    })


def _compress_git_diffs(body: dict) -> dict:
    messages = body.get("messages", [])
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    text = block.get("content")
                    if isinstance(text, str) and ("diff --git" in text or "git diff" in text):
                        lines = text.split("\n")
                        new_lines = []
                        skipping = False
                        for line in lines:
                            if line.startswith("diff --git"):
                                if any(x in line for x in ["package-lock.json", "yarn.lock", "pnpm-lock.yaml"]):
                                    skipping = True
                                else:
                                    skipping = False
                            if not skipping:
                                new_lines.append(line)
                        block["content"] = "\n".join(new_lines)
        elif isinstance(content, str) and ("diff --git" in content or "git diff" in content):
            lines = content.split("\n")
            new_lines = []
            skipping = False
            for line in lines:
                if line.startswith("diff --git"):
                    if any(x in line for x in ["package-lock.json", "yarn.lock", "pnpm-lock.yaml"]):
                        skipping = True
                    else:
                        skipping = False
                if not skipping:
                    new_lines.append(line)
            msg["content"] = "\n".join(new_lines)
    return body



def _strip_preloaded_file_contents(body: dict) -> dict:
    messages = body.get("messages", [])
    if not messages:
        return body
    
    first_msg = messages[0]
    content = first_msg.get("content")
    if not isinstance(content, str):
        return body
        
    if "### " in content and "```" in content:
        parts = content.split("```")
        new_parts = []
        for idx, part in enumerate(parts):
            if idx % 2 == 1:
                prev_part = parts[idx-1]
                if "### " in prev_part or "File contents:" in prev_part:
                    lang = ""
                    lines = part.split("\n")
                    if lines and not lines[0].strip().startswith("print") and len(lines[0]) < 15:
                        lang = lines[0] + "\n"
                    new_parts.append(f"{lang}[Winnow: File content stripped to save tokens. Use view_file to read if needed.]\n")
                else:
                    new_parts.append(part)
            else:
                new_parts.append(part)
        first_msg["content"] = "```".join(new_parts)
    return body



@app.get("/winnow/stats")
def stats():
    return {
        "enabled": config.enabled(),
        "mode": config.mode(),
        **store.aggregate_savings(),
        "recent": store.query_recent(20),
    }


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(path: str, request: Request):
    raw = await request.body()
    out_bytes = raw

    if config.enabled() and request.method == "POST" and path == "v1/messages":
        try:
            body = json.loads(raw)
            body = _strip_preloaded_file_contents(body)
            body = _compress_git_diffs(body)
            
            # 1. Check Dollar Cost Sentinel Safety Cap (opt-in, off by default)
            if config.sentinel_enabled():
                before = tokencount.estimate(body)
                model_name = body.get("model", "claude-3-5-sonnet")
                est_cost = _calculate_request_cost(model_name, before)
                limit = config.max_session_cost()
                if est_cost > limit:
                    return StreamingResponse(sentinel_warning_stream(before, est_cost, limit, model_name), media_type="text/event-stream")
            
            # 2. Regular SMWT Trimming
            trimmed = trimmer.trim(body)
            after = tokencount.estimate(trimmed)
            out_bytes = json.dumps(trimmed).encode("utf-8")
            
            try:
                stats_diff = trimmer.diff_stats(body, trimmed)
                store.log_request(tokens_before=before, tokens_after=after, mode=config.mode(), **stats_diff)
            except Exception:
                pass
        except Exception:
            out_bytes = raw  # fail open: forward original untouched bytes

    target = f"{config.upstream().rstrip('/')}/{path}"
    if request.url.query:
        target += f"?{request.url.query}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _STRIP_REQUEST_HEADERS}

    upstream = await _forward(request.method, target, headers, out_bytes)
    response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _STRIP_RESPONSE_HEADERS}
    return Response(content=upstream.content, status_code=upstream.status_code, headers=response_headers)
