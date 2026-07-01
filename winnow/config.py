"""Env-driven config. Read fresh where it matters (WINNOW_ENABLED) rather than
cached at import time, so the kill switch works without a restart."""
import os


def enabled() -> bool:
    return os.environ.get("WINNOW_ENABLED", "true").strip().lower() not in ("false", "0", "no")


def mode() -> str:
    return os.environ.get("WINNOW_MODE", "thorough").strip().lower()


def upstream() -> str:
    return os.environ.get("WINNOW_UPSTREAM", "https://api.anthropic.com")


def port() -> int:
    return int(os.environ.get("WINNOW_PORT", "8787"))


def keep_last_turns() -> int:
    return int(os.environ.get("WINNOW_KEEP_LAST_TURNS", "2"))


def relevance_threshold() -> float:
    return float(os.environ.get("WINNOW_RELEVANCE_THRESHOLD", "0.15"))


def json_keep_items() -> int:
    return int(os.environ.get("WINNOW_JSON_KEEP_ITEMS", "20"))


def db_path() -> str:
    return os.path.expanduser(os.environ.get("WINNOW_DB_PATH", "~/.winnow/winnow.db"))


def embedding_model() -> str:
    return os.environ.get("WINNOW_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
