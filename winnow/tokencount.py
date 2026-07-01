"""Token count estimate for the monotonic-reduction guard and observability.

NOTE: this is an approximation (cl100k_base tokenization of a JSON/text
serialization) — it is NOT billing-accurate for Claude models, which use a
different tokenizer. It exists only so trimmer.py can compare "before" vs
"after" sizes consistently; do not use it for cost accounting.
"""
import json
from functools import lru_cache

import tiktoken


@lru_cache(maxsize=1)
def _encoding():
    return tiktoken.get_encoding("cl100k_base")


def estimate(obj) -> int:
    """Estimate token count of a JSON-serializable object (or a str)."""
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return len(_encoding().encode(text))
