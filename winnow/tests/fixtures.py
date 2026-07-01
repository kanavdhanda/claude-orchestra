"""Fixed (not random) sample conversation bodies, shaped like real Anthropic
Messages API request payloads. Each function returns a fresh dict so tests
can mutate their own copy without cross-test contamination.
"""
import copy
import json

_SHORT_CHAT = {
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "system": "You are a helpful assistant.",
    "messages": [
        {"role": "user", "content": "Hi, what's 2+2?"},
        {"role": "assistant", "content": "4."},
        {"role": "user", "content": "Great, thanks!"},
    ],
}

_LONG_PROSE_CHAT = {
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "system": "You are a helpful coding assistant.",
    "messages": [
        {"role": "user", "content": "Can you explain what a Python decorator is?"},
        {"role": "assistant", "content": (
            "A Python decorator is a function that wraps another function to extend its "
            "behavior without modifying its source code, using the @decorator syntax."
        )},
        {"role": "user", "content": "What's a good recipe for pasta carbonara?"},
        {"role": "assistant", "content": (
            "Carbonara is made with eggs, pecorino cheese, guanciale, and black pepper, "
            "tossed with hot pasta off the heat so the eggs form a creamy sauce instead of scrambling."
        )},
        {"role": "user", "content": "What's the weather usually like in Lisbon in October?"},
        {"role": "assistant", "content": (
            "Lisbon in October is generally mild, with average highs around 22C and "
            "occasional rain showers as autumn sets in."
        )},
        {"role": "user", "content": "Can you show an example of a decorator that logs function calls?"},
        {"role": "assistant", "content": (
            "Sure, here's a logging decorator: it wraps a function, prints the function "
            "name and arguments before calling it, and returns the wrapped result."
        )},
        {"role": "user", "content": "Now, going back to decorators - can they take arguments themselves?"},
    ],
}

_JSON_TOOL_CHAT = {
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "system": "You are a helpful assistant with tool access.",
    "messages": [
        {"role": "user", "content": "List all open issues in the repo."},
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "toolu_01", "name": "list_issues", "input": {"repo": "acme/widgets"}},
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_01",
                    "content": json.dumps(
                        [{"id": i, "title": f"Issue number {i}", "state": "open"} for i in range(50)]
                    ),
                }
            ],
        },
        {"role": "assistant", "content": "There are 50 open issues, mostly minor."},
        {"role": "user", "content": "Now summarize the 3 most recent ones for me."},
    ],
}

_CODE_CHAT = {
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "system": "You are a helpful coding assistant.",
    "messages": [
        {"role": "user", "content": "Write a function to compute the fibonacci sequence."},
        {"role": "assistant", "content": (
            "```python\n"
            "def fib(n):\n"
            "    a, b = 0, 1\n"
            "    for _ in range(n):\n"
            "        a, b = b, a + b\n"
            "    return a\n"
            "```"
        )},
        {"role": "user", "content": "Now write one for factorial."},
        {"role": "assistant", "content": (
            "```python\n"
            "def factorial(n):\n"
            "    return 1 if n <= 1 else n * factorial(n - 1)\n"
            "```"
        )},
        {"role": "user", "content": "Can you combine both into one module?"},
    ],
}

_SINGLE_MESSAGE_CHAT = {
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "Hello there!"},
    ],
}


def short_chat():
    return copy.deepcopy(_SHORT_CHAT)


def long_prose_chat():
    return copy.deepcopy(_LONG_PROSE_CHAT)


def json_tool_chat():
    return copy.deepcopy(_JSON_TOOL_CHAT)


def code_chat():
    return copy.deepcopy(_CODE_CHAT)


def single_message_chat():
    return copy.deepcopy(_SINGLE_MESSAGE_CHAT)


def all_fixtures():
    return [short_chat(), long_prose_chat(), json_tool_chat(), code_chat(), single_message_chat()]
