"""Deterministic structural JSON truncation for large tool-result blocks.

Pure function, no I/O. Keeps the first N array items / dict keys (insertion
order, which is stable in Python/JSON) and appends a marker describing how
much was omitted. Recurses into kept children so nested large structures are
also bounded.
"""


def truncate_json(value, keep_items: int = 20):
    if isinstance(value, list):
        kept = [truncate_json(v, keep_items) for v in value[:keep_items]]
        omitted = len(value) - keep_items
        if omitted > 0:
            kept.append(f"...{omitted} more omitted")
        return kept
    if isinstance(value, dict):
        keys = list(value.keys())
        result = {k: truncate_json(value[k], keep_items) for k in keys[:keep_items]}
        omitted = len(keys) - keep_items
        if omitted > 0:
            result[f"...{omitted} more omitted"] = True
        return result
    return value


def needs_truncation(value, keep_items: int = 20) -> bool:
    """Only truncate above the size threshold (> keep_items at the top level)."""
    if isinstance(value, (list, dict)):
        return len(value) > keep_items
    return False
