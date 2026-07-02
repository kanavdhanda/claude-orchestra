"""Core trimming orchestration. PURE FUNCTION — no network/DB calls — so reqs
1 (deterministic), 3 (monotonic) and 4 (fail-open) are unit-testable without
a server.

Only `messages` are ever touched; `system` and every other top-level field of
the request body pass through untouched. Within the trimmable portion, only
`text` blocks and `tool_result` blocks are classified/modified — every other
block type (tool_use, image, thinking, ...) is left verbatim, since those
often carry API-required fields (ids, signatures) that must not be altered.
"""
import json

from winnow import config, json_truncate, scoring, tokencount

# ponytail: markdown code-fence sniffing is a naive heuristic ("```" present
# => treat as code, skip trimming). Full AST-aware code detection is a v2 item.
_CODE_FENCE = "```"


def _classify_kind(text):
    """("json", parsed) | ("code", None) | ("prose", None) | ("skip", None)."""
    if not isinstance(text, str) or not text:
        return "skip", None
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        parsed = None
    if isinstance(parsed, (list, dict)):
        return "json", parsed
    if _CODE_FENCE in text:
        return "code", None
    return "prose", None


def _each_text_leaf(content):
    """Yield every classifiable text leaf in a message's `content` (top-level
    string, `text` blocks, and `tool_result` inner text). Read-only walk;
    used both to build the BM25 corpus and (by _process_content) mirrored to
    write results back.
    """
    if isinstance(content, str):
        yield content
        return
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text" and isinstance(block.get("text"), str):
            yield block["text"]
        elif btype == "tool_result":
            inner = block.get("content")
            if isinstance(inner, str):
                yield inner
            elif isinstance(inner, list):
                for sub in inner:
                    if isinstance(sub, dict) and sub.get("type") == "text" and isinstance(sub.get("text"), str):
                        yield sub["text"]


def _classify_and_process(text: str, query: str, mode: str, threshold: float, keep_items: int, corpus: list) -> str:
    kind, parsed = _classify_kind(text)
    if kind in ("skip", "code"):
        return text

    if kind == "json":
        if json_truncate.needs_truncation(parsed, keep_items):
            return json.dumps(json_truncate.truncate_json(parsed, keep_items))
        return text

    # prose: BM25 needs a real multi-document corpus for its IDF term-weighting
    # to be meaningful (a 1-document corpus makes every term's IDF an identical
    # degenerate constant) — so score against the other sibling prose blocks in
    # this same request, not against the candidate alone.
    s = scoring.score(query, text, corpus=corpus, mode=mode)
    if s < threshold:
        # ponytail: deliberately no embedded floats here — digits tokenize
        # inefficiently in BPE and a verbose stub can erase the savings it's
        # supposed to create. Exact scores are still logged to sqlite
        # (store.py) for observability; this text only needs to explain why.
        return "[winnow: older message omitted, low relevance to current topic]"
    return text


def _process_content(content, query: str, mode: str, threshold: float, keep_items: int, corpus: list):
    if isinstance(content, str):
        return _classify_and_process(content, query, mode, threshold, keep_items, corpus)

    if not isinstance(content, list):
        return content

    new_blocks = []
    for block in content:
        if not isinstance(block, dict):
            new_blocks.append(block)
            continue

        btype = block.get("type")
        if btype == "text" and isinstance(block.get("text"), str):
            nb = dict(block)
            nb["text"] = _classify_and_process(block["text"], query, mode, threshold, keep_items, corpus)
            new_blocks.append(nb)
        elif btype == "tool_result":
            nb = dict(block)
            inner = block.get("content")
            if isinstance(inner, str):
                nb["content"] = _classify_and_process(inner, query, mode, threshold, keep_items, corpus)
            elif isinstance(inner, list):
                new_inner = []
                for sub in inner:
                    if isinstance(sub, dict) and sub.get("type") == "text" and isinstance(sub.get("text"), str):
                        nsub = dict(sub)
                        nsub["text"] = _classify_and_process(sub["text"], query, mode, threshold, keep_items, corpus)
                        new_inner.append(nsub)
                    else:
                        new_inner.append(sub)
                nb["content"] = new_inner
            new_blocks.append(nb)
        else:
            new_blocks.append(block)
    return new_blocks


def _newest_user_text(messages: list) -> str:
    for m in reversed(messages):
        if m.get("role") != "user":
            continue
        content = m.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
            if parts:
                return "\n".join(parts)
    return ""


def _build_prose_corpus(head: list) -> list:
    corpus = []
    for m in head:
        for text in _each_text_leaf(m.get("content")):
            if _classify_kind(text)[0] == "prose":
                corpus.append(text)
    return corpus


def _has_cache_control(message: dict) -> bool:
    content = message.get("content")
    if not isinstance(content, list):
        return False
    return any(isinstance(block, dict) and block.get("cache_control") is not None for block in content)


def _last_cache_breakpoint_index(messages: list) -> int:
    """Highest index of a message carrying a cache_control marker, or -1 if
    none exists. Anthropic's prompt cache requires a byte-identical prefix up
    to this point, so everything at or before it must never be rescored."""
    idx = -1
    for i, m in enumerate(messages):
        if isinstance(m, dict) and _has_cache_control(m):
            idx = i
    return idx


def _trim_inner(body: dict) -> dict:
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        return body

    keep_n = config.keep_last_turns()
    tail = messages[-keep_n:] if keep_n > 0 else []
    head = messages[: len(messages) - len(tail)]
    if not head:
        return body  # everything is within the "keep verbatim" window

    mode = config.mode()
    threshold = config.relevance_threshold()
    keep_items = config.json_keep_items()
    query = _newest_user_text(messages)
    corpus = _build_prose_corpus(head)

    new_head = []
    for m in head:
        nm = dict(m)
        nm["content"] = _process_content(m.get("content"), query, mode, threshold, keep_items, corpus)
        new_head.append(nm)

    new_body = dict(body)
    new_body["messages"] = new_head + tail
    return new_body


_STUB_PREFIX = "[winnow: older message omitted"


def diff_stats(original: dict, trimmed: dict) -> dict:
    """Count what happened to each text leaf, for observability logging
    (req 6). Not part of the guarded trim() path — purely descriptive."""
    orig_msgs = original.get("messages") or []
    trim_msgs = trimmed.get("messages") or []
    kept = truncated = dropped = 0
    for om, tm in zip(orig_msgs, trim_msgs):
        o_leaves = list(_each_text_leaf(om.get("content")))
        t_leaves = list(_each_text_leaf(tm.get("content")))
        for o, t in zip(o_leaves, t_leaves):
            if o == t:
                kept += 1
            elif isinstance(t, str) and t.startswith(_STUB_PREFIX):
                dropped += 1
            else:
                truncated += 1
    return {"kept": kept, "truncated": truncated, "dropped": dropped}


def trim(body: dict) -> dict:
    """Guarded entrypoint: deterministic, never raises, never returns a
    payload estimated larger than the input (reqs 1/3/4 all enforced here).
    """
    try:
        original_size = tokencount.estimate(body)
        trimmed = _trim_inner(body)
        if tokencount.estimate(trimmed) >= original_size:
            return body
        return trimmed
    except Exception:
        return body
