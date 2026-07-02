---
name: local-model-router
description: >
  Routes genuinely low-complexity, single-shot text or research tasks to a local model
  running on oMLX (or Claude Haiku as fallback) instead of Claude Sonnet, to reduce cost
  and API usage. Applies to: explaining code, repository Q&A, refactoring suggestions,
  generating unit tests, docstrings, regex, shell commands, git logs, formatting,
  summarizing papers/text, and cross-domain brainstorming. Does NOT apply to architecture/planning,
  multi-file edits, complex debugging, agentic workflows, or large feature
  implementation.
---

# Local Model Router

Claude has tool access, file access, and judgment. The local model (served via oMLX at `http://localhost:8081`) or the fallback Haiku model has none of that — they are single text-in/text-out exchanges with no memory, no tools, and no files. They can only answer a prompt you construct and paste back.

Routing to them trades latency for massive token savings. The user has explicitly accepted that tradeoff.

## Step 1 — Classify the task (deterministic, not vibes)

**Route to the local model (or Haiku)** if the task is ONE of:
1. **Code Explanation**: Explaining a file, class, or function.
2. **Documentation**: Writing docstrings, JSDoc, README files, or markdown guides.
3. **Unit Test Generation**: Creating tests (pytest, jest, etc.) for a specific function or module.
4. **Refactoring Suggestions**: Recommending cleaner code patterns (pure text suggestion, not applying a multi-file edit).
5. **Regex & Command Generation**: Generating regex expressions or shell commands.
6. **Commit Messages & PR Descriptions**: Drafting git logs from diff outputs.
7. **Formatting & Style Compliance**: Fixing formatting, lint errors, or JSON/YAML/Markdown layout.
8. **Research Summarization & Abstract Synthesis**: Summarizing ArXiv papers, extracting metrics, or drafting comparative study outlines.
9. **Cross-Domain Brainstorming**: Finding analogies or connections between separate disciplines (e.g. EEG signals and signal processing pipelines).

**Keep with Claude Sonnet** — do NOT route — if the task involves ANY of:
- Architecture or planning
- Multi-file edits
- Complex debugging
- Agentic workflows (multiple tool calls, iterative exploration)
- Large feature implementation
- Anything requiring real judgment, codebase-wide context, or tool use beyond a single text-in/text-out exchange

If a task doesn't cleanly match a routable bullet above, keep it with Sonnet. When in doubt, don't route.

## Step 2 — Battery & Liveness Check (fail-open, always)

1. **Battery Check**: Local models consume substantial battery on Apple Silicon. If you are drawing from battery power, skip the local model to conserve power, unless overridden by `OMLX_FORCE=true`.
2. **Liveness Check**: Verify oMLX is active.

Run this check in a shell:

```bash
# Skip local model on battery unless OMLX_FORCE is true
if [ "$OMLX_FORCE" != "true" ] && pmset -g batt | grep -q "Battery Power"; then
  exit 1
fi

# Verify oMLX is listening
curl -s -m 2 http://localhost:8081/v1/models > /dev/null || exit 1
```

If the check returns a non-zero exit code:
* **Haiku Fallback**: Instead of falling open to Sonnet 3.5, **spawn a subagent via the native Agent/Task tool using the `claude-3-5-haiku` model** to execute the task. This keeps your costs extremely low.
* If Haiku is unavailable or errors, do the task with Claude Sonnet directly.

## Step 3 — Call the local model

Discover the model ID dynamically from the oMLX models list (it will automatically target whatever model is currently active/pinned on the server) and call the completions endpoint:

```bash
# 1. Discover active model ID dynamically
MODEL_ID=$(curl -s http://localhost:8081/v1/models | jq -r '.data[0].id // empty')
if [ -z "$MODEL_ID" ]; then
  MODEL_ID="mlx-community/gemma-4-12b-coder-fable5-composer2.5-8bit" # Fallback
fi

# 2. Call the chat completions endpoint with your custom prompt
curl -s -m 30 http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$MODEL_ID\", \"messages\": [{\"role\": \"system\", \"content\": \"You are a senior developer. Respond extremely concisely, providing direct answers and code snippets without conversational filler or apologies.\"}, {\"role\": \"user\", \"content\": \"<task-specific prompt>\"}], \"max_tokens\": 2000}"
```

Extract `choices[0].message.content` from the JSON response and present it as the answer.

## Step 4 — Fail-open on error too

If the request errors, times out (30s), or returns malformed/empty output:
silently fallback and execute the task using a Haiku subagent, or with Sonnet directly if needed. Never block the user.

## Monitoring

- Liveness: `curl -s http://localhost:8081/v1/models`
- Logs: `/Users/kanavdhanda/Library/Application Support/oMLX/logs/server.log`
