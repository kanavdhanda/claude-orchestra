#!/bin/bash
set -e

# Claude Orchestra Setup & Migration Bootstrapper
echo "==========================================="
echo "  Claude Orchestra macOS Migration & Setup"
echo "==========================================="

# 1. OS verification
if [[ "$OSTYPE" != "darwin"* ]]; then
  echo "Error: This Winnow setup requires macOS (LaunchAgents and PyObjC/rumps are Mac-specific)."
  exit 1
fi

REPO_DIR=$(pwd)
PYTHON_PATH=$(which python3)
USER_HOME=$HOME
USER_ID=$(id -u)

echo "Detected repository path: $REPO_DIR"
echo "Using Python executable: $PYTHON_PATH"

# 2. Install required Python packages
echo "Installing required Python dependencies..."
"$PYTHON_PATH" -m pip install --user fastapi uvicorn httpx rumps pyobjc markitdown

# 3. Create configuration folders
echo "Creating global config directories..."
mkdir -p "$USER_HOME/.claude"
mkdir -p "$USER_HOME/.winnow"

# 4. Copy CLAUDE.md and Claude Code settings
echo "Configuring Claude Code custom instructions..."
if [ -f "$REPO_DIR/dotfiles/claude/CLAUDE.md" ]; then
  cp "$REPO_DIR/dotfiles/claude/CLAUDE.md" "$USER_HOME/.claude/CLAUDE.md"
  echo "Copied CLAUDE.md to ~/.claude/CLAUDE.md"
fi

if [ -f "$REPO_DIR/dotfiles/claude/settings.json" ]; then
  cp "$REPO_DIR/dotfiles/claude/settings.json" "$USER_HOME/.claude/settings.json"
  echo "Copied settings.json to ~/.claude/settings.json"
fi

# Copy active skill if present
if [ -d "$REPO_DIR/dotfiles/claude/skills/local-model-router" ]; then
  mkdir -p "$USER_HOME/.claude/skills/local-model-router"
  cp "$REPO_DIR/dotfiles/claude/skills/local-model-router/SKILL.md" "$USER_HOME/.claude/skills/local-model-router/SKILL.md"
  echo "Copied local-model-router skill to ~/.claude/skills/"
fi

# 5. Create LaunchAgent for Winnow proxy server
echo "Generating Winnow LaunchAgent plist..."
LAUNCH_AGENT_DIR="$USER_HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENT_DIR"

PROXY_PLIST="$LAUNCH_AGENT_DIR/com.claude-orchestra.winnow.plist"
cat <<EOF > "$PROXY_PLIST"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>com.claude-orchestra.winnow</string>
	<key>ProgramArguments</key>
	<array>
		<string>$PYTHON_PATH</string>
		<string>-m</string>
		<string>uvicorn</string>
		<string>winnow.server:app</string>
		<string>--port</string>
		<string>8787</string>
	</array>
	<key>WorkingDirectory</key>
	<string>$REPO_DIR</string>
	<key>RunAtLoad</key>
	<true/>
	<key>KeepAlive</key>
	<true/>
	<key>StandardOutPath</key>
	<string>$USER_HOME/Library/Logs/winnow.log</string>
	<key>StandardErrorPath</key>
	<string>$USER_HOME/Library/Logs/winnow.error.log</string>
</dict>
</plist>
EOF
echo "Created $PROXY_PLIST"

# 6. Create LaunchAgent for Winnow Menu Bar Application
echo "Generating Winnow Menu App LaunchAgent plist..."
MENU_PLIST="$LAUNCH_AGENT_DIR/com.claude-orchestra.winnow-menu.plist"
cat <<EOF > "$MENU_PLIST"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>com.claude-orchestra.winnow-menu</string>
	<key>ProgramArguments</key>
	<array>
		<string>$PYTHON_PATH</string>
		<string>$REPO_DIR/winnow/menu_bar.py</string>
	</array>
	<key>WorkingDirectory</key>
	<string>$REPO_DIR</string>
	<key>RunAtLoad</key>
	<true/>
	<key>KeepAlive</key>
	<true/>
	<key>StandardOutPath</key>
	<string>$USER_HOME/Library/Logs/winnow-menu.log</string>
	<key>StandardErrorPath</key>
	<string>$USER_HOME/Library/Logs/winnow-menu.error.log</string>
</dict>
</plist>
EOF
echo "Created $MENU_PLIST"

# 7. Unload and reload LaunchAgents
echo "Bootstrapping background services..."
launchctl bootout gui/"$USER_ID" "$PROXY_PLIST" 2>/dev/null || true
launchctl bootout gui/"$USER_ID" "$MENU_PLIST" 2>/dev/null || true

launchctl bootstrap gui/"$USER_ID" "$PROXY_PLIST"
launchctl bootstrap gui/"$USER_ID" "$MENU_PLIST"

echo "==========================================="
echo "  Migration Setup Completed Successfully!"
echo "  - Winnow Proxy active on port 8787"
echo "  - Winnow Menu Bar App running (💸 icon)"
echo "  - Claude Code settings & CLAUDE.md active"
echo "==========================================="
