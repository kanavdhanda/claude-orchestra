"""FastAPI reverse proxy. Only POST /v1/messages goes through the trimmer;
every other path/method is a byte-for-byte passthrough. The fail-open
boundary (req 4) lives here: any error while parsing/trimming the body falls
back to forwarding the untouched original bytes — trimming must never be
able to break a real request.
"""
import json

import httpx
from fastapi import FastAPI, Request, Response

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


def _trim_and_log(raw: bytes) -> bytes:
    """Parse, trim, log. Any failure here (bad JSON, scoring error, DB error)
    means: return the original raw bytes, unmodified."""
    body = json.loads(raw)
    trimmed = trimmer.trim(body)
    before = tokencount.estimate(body)
    after = tokencount.estimate(trimmed)
    out = json.dumps(trimmed).encode("utf-8") if trimmed is not body else raw
    try:
        stats = trimmer.diff_stats(body, trimmed)
        store.log_request(tokens_before=before, tokens_after=after, mode=config.mode(), **stats)
    except Exception:
        pass  # observability must never block a real request
    return out


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
            out_bytes = _trim_and_log(raw)
        except Exception:
            out_bytes = raw  # fail open: forward the original request untouched

    target = f"{config.upstream().rstrip('/')}/{path}"
    if request.url.query:
        target += f"?{request.url.query}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _STRIP_REQUEST_HEADERS}

    upstream = await _forward(request.method, target, headers, out_bytes)
    response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _STRIP_RESPONSE_HEADERS}
    return Response(content=upstream.content, status_code=upstream.status_code, headers=response_headers)
