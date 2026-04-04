#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Build if needed
docker compose build

# Ensure host dirs/files exist for bind mounts
mkdir -p "$SCRIPT_DIR/.claude-home/.claude" "$SCRIPT_DIR/.claude-home/.config/gh"
[ -f "$SCRIPT_DIR/.claude-home/.claude.json" ] || touch "$SCRIPT_DIR/.claude-home/.claude.json"

# Run with explicit interactive TTY allocation
docker run -it --rm \
    -v "$SCRIPT_DIR:/workspace" \
    -v "$SCRIPT_DIR/.claude-home/.claude:/home/claude/.claude" \
    -v "$SCRIPT_DIR/.claude-home/.claude.json:/home/claude/.claude.json" \
    -v "$SCRIPT_DIR/.claude-home/.config/gh:/home/claude/.config/gh" \
    -w /workspace \
    claude_auto_tune-claude \
    --dangerously-skip-permissions "$@"
