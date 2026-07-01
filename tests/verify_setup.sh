#!/usr/bin/env bash
set -uo pipefail
fail=0

check() { echo "[check] $1"; }
ok()    { echo "  OK: $1"; }
bad()   { echo "  FAIL: $1"; fail=1; }

check "serena registered exactly once, github/ast-grep connected, headroom absent"
mcp_out="$(claude mcp list 2>&1)"
grep -q '^serena:' <<<"$mcp_out" && bad "duplicate standalone serena still present" || ok "no duplicate serena"
grep -q 'plugin:serena:serena.*Connected' <<<"$mcp_out" && ok "serena plugin connected" || bad "serena plugin not connected"
grep -q 'plugin:github:github.*Connected' <<<"$mcp_out" && ok "github connected" || bad "github not connected (may need a session restart to pick up the new token)"
grep -q '^ast-grep:.*Connected' <<<"$mcp_out" && ok "ast-grep MCP connected" || bad "ast-grep MCP not connected"
grep -qi '^headroom' <<<"$mcp_out" && bad "headroom MCP still registered" || ok "headroom MCP absent"

check "no leftover headroom references in global config"
if grep -qi headroom "$HOME/.claude/CLAUDE.md" "$HOME/.claude/settings.json" 2>/dev/null; then
  bad "headroom reference still present in CLAUDE.md or settings.json"
else
  ok "no headroom references in CLAUDE.md/settings.json"
fi

check "CLI tools installed"
for bin in ast-grep fd tree-sitter; do
  command -v "$bin" >/dev/null && ok "$bin found" || bad "$bin missing"
done

check "cross-domain-brainstorm skill exists with frontmatter"
skill="$HOME/.claude/skills/cross-domain-brainstorm/SKILL.md"
if [[ -f "$skill" ]] && grep -q '^name:' "$skill" && grep -q '^description:' "$skill"; then
  ok "skill present with name/description"
else
  bad "skill missing or malformed"
fi

exit $fail
