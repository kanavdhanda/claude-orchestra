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
import re

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
        return "[winnow: older message omitted, low relevance to current topic]"
    return text


def _process_content(content, is_old_turn: bool, query: str = None, mode: str = None,
                     threshold: float = None, keep_items: int = 20, corpus: list = None):
    if isinstance(content, str):
        if config.trim_prose() and is_old_turn:
            new_text = _classify_and_process(content, query, mode, threshold, keep_items, corpus)
            return new_text
        return content

    if not isinstance(content, list):
        return content

    any_changed = False
    new_blocks = []
    for block in content:
        if not isinstance(block, dict):
            new_blocks.append(block)
            continue

        btype = block.get("type")
        if btype == "tool_result":
            nb = dict(block)
            cache_ctrl = nb.get("cache_control")
            
            # Determine truncation parameters based on age
            is_stub_turn = is_old_turn and config.stub_old_tool_results()
            max_chars = 3000 if is_stub_turn else config.text_keep_chars()
            keep_edge = 1500 if is_stub_turn else None
            
            inner = block.get("content")
            if isinstance(inner, str):
                kind, parsed = _classify_kind(inner)
                if kind == "json":
                    if json_truncate.needs_truncation(parsed, keep_items):
                        nb["content"] = json.dumps(json_truncate.truncate_json(parsed, keep_items))
                        any_changed = True
                else:
                    if len(inner) > max_chars:
                        if keep_edge is not None:
                            nb["content"] = inner[:keep_edge] + f"\n\n... [winnow: {len(inner) - (keep_edge * 2)} characters omitted from old tool result for cache stability] ...\n\n" + inner[-keep_edge:]
                        else:
                            nb["content"] = inner[:max_chars] + f"\n\n... [{len(inner) - max_chars} characters omitted by winnow] ..."
                        any_changed = True
            elif isinstance(inner, list):
                new_inner = []
                inner_changed = False
                for sub in inner:
                    if isinstance(sub, dict) and sub.get("type") == "text" and isinstance(sub.get("text"), str):
                        nsub = dict(sub)
                        sub_text = sub["text"]
                        kind, parsed = _classify_kind(sub_text)
                        sub_changed = False
                        if kind == "json":
                            if json_truncate.needs_truncation(parsed, keep_items):
                                nsub["text"] = json.dumps(json_truncate.truncate_json(parsed, keep_items))
                                sub_changed = True
                        else:
                            if len(sub_text) > max_chars:
                                if keep_edge is not None:
                                    nsub["text"] = sub_text[:keep_edge] + f"\n\n... [winnow: {len(sub_text) - (keep_edge * 2)} characters omitted from old tool result for cache stability] ...\n\n" + sub_text[-keep_edge:]
                                else:
                                    nsub["text"] = sub_text[:max_chars] + f"\n\n... [{len(sub_text) - max_chars} characters omitted by winnow] ..."
                                sub_changed = True
                        
                        if sub_changed:
                            inner_changed = True
                        new_inner.append(nsub)
                    else:
                        new_inner.append(sub)
                if inner_changed:
                    nb["content"] = new_inner
                    any_changed = True
            
            if cache_ctrl:
                nb["cache_control"] = cache_ctrl
            new_blocks.append(nb)
            
        elif btype == "text" and isinstance(block.get("text"), str):
            nb = dict(block)
            if config.trim_prose() and is_old_turn:
                new_text = _classify_and_process(block["text"], query, mode, threshold, keep_items, corpus)
                if new_text is not block["text"]:
                    nb["text"] = new_text
                    any_changed = True
            new_blocks.append(nb)
            
        else:
            new_blocks.append(block)
            
    if any_changed:
        return new_blocks
    return content


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


def _minify_system_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    
    # Strip Ponytail block: from "#+ Ponytail, lazy senior dev" until next "# " or end of string
    text = re.sub(
        r"#+ Ponytail, lazy senior dev mode.*?(?=\n#+ |\Z)",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Strip Superpowers bootstrap: from "#+ using-superpowers" or "IMPORTANT: The using-superpowers"
    # until next "# " or end of string
    text = re.sub(
        r"(?:#+ using-superpowers|IMPORTANT: The using-superpowers skill content).*?(?=\n#+ |\Z)",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Clean up double newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _minify_system_prompt(system):
    if isinstance(system, str):
        return _minify_system_text(system)
    elif isinstance(system, list):
        new_system = []
        for block in system:
            if isinstance(block, dict) and block.get("type") == "text":
                nb = dict(block)
                nb["text"] = _minify_system_text(block["text"])
                new_system.append(nb)
            else:
                new_system.append(block)
        return new_system
    return system


def _trim_inner(body: dict) -> dict:
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        return body

    keep_n = config.keep_last_turns()
    total_len = len(messages)

    query = ""
    mode = "fast"
    threshold = 0.15
    keep_items = config.json_keep_items()
    corpus = []
    
    if config.trim_prose():
        query = _newest_user_text(messages)
        mode = config.mode()
        threshold = config.relevance_threshold()
        head_messages = messages[: max(0, total_len - keep_n)]
        corpus = _build_prose_corpus(head_messages)

    any_changed = False
    new_messages = []
    for i, m in enumerate(messages):
        is_old_turn = (i < total_len - keep_n)
        orig_content = m.get("content")
        new_content = _process_content(
            orig_content,
            is_old_turn=is_old_turn,
            query=query,
            mode=mode,
            threshold=threshold,
            keep_items=keep_items,
            corpus=corpus
        )
        if new_content is not orig_content:
            any_changed = True
        
        nm = dict(m)
        nm["content"] = new_content
        new_messages.append(nm)

    if any_changed:
        new_body = dict(body)
        new_body["messages"] = new_messages
        return new_body
    return body


_STUB_PREFIX = "[winnow:"


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
        new_body = dict(body)
        if "system" in new_body and config.minify_system():
            new_body["system"] = _minify_system_prompt(new_body["system"])
            
        original_size = tokencount.estimate(new_body)
        trimmed = _trim_inner(new_body)
        if tokencount.estimate(trimmed) >= original_size:
            return new_body
        return trimmed
    except Exception:
        return body
