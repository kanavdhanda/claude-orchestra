"""Env-driven config. Read fresh where it matters (WINNOW_ENABLED) rather than
cached at import time, so the kill switch works without a restart."""
import os


def enabled() -> bool:
    disabled_file = os.path.expanduser("~/.winnow/disabled")
    if os.path.exists(disabled_file):
        return False
    return os.environ.get("WINNOW_ENABLED", "true").strip().lower() not in ("false", "0", "no")


def active_model() -> str:
    env_model = os.environ.get("WINNOW_LOCAL_MODEL")
    if env_model:
        return env_model.strip()
    model_file = os.path.expanduser("~/.winnow/active_model")
    if os.path.exists(model_file):
        try:
            with open(model_file, "r") as f:
                return f.read().strip()
        except Exception:
            pass
    return "Qwen3.5-9B-TNG-PKD-Qwopus-Coder-Qwythos-qx86-hi-mlx"


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


def text_keep_chars() -> int:
    return int(os.environ.get("WINNOW_TEXT_KEEP_CHARS", "8000"))


def stub_old_tool_results() -> bool:
    return os.environ.get("WINNOW_STUB_OLD_TOOL_RESULTS", "true").strip().lower() not in ("false", "0", "no")


def trim_prose() -> bool:
    return os.environ.get("WINNOW_TRIM_PROSE", "false").strip().lower() not in ("false", "0", "no")


def db_path() -> str:
    return os.path.expanduser(os.environ.get("WINNOW_DB_PATH", "~/.winnow/winnow.db"))


def embedding_model() -> str:
    return os.environ.get("WINNOW_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def minify_system() -> bool:
    return os.environ.get("WINNOW_MINIFY_SYSTEM", "false").strip().lower() not in ("false", "0", "no")


def max_session_cost() -> float:
    return float(os.environ.get("WINNOW_MAX_SESSION_COST", "0.30"))



def omlx_url() -> str:
    return os.environ.get("WINNOW_OMLX_URL", "http://localhost:8081").rstrip("/")


def omlx_enabled() -> bool:
    return os.environ.get("WINNOW_OMLX_ENABLED", "true").strip().lower() not in ("false", "0", "no")



