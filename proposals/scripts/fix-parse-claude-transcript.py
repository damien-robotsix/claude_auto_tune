#!/usr/bin/env python3
"""
PROPOSAL: Fix JSONL format mismatch in parse-claude-transcript.py

Evidence: All 3 analyzed transcripts returned "no tool calls found" despite
containing tool calls. Direct inspection of a transcript file confirmed 16
tool_use blocks in message.content of run 23980452961.

Root cause: The script checks entry.get("role") at the top level, but
Claude Code's JSONL format uses entry["type"] at the top level and nests
the actual message as entry["message"]["role"] / entry["message"]["content"].

Current (broken) logic in extract_tool_calls():
    role = entry.get("role", "")          # always "" in real transcripts
    content = entry.get("content", [])    # always [] in real transcripts

    if role == "assistant":               # never matches
        for block in content:             # never iterates

Actual JSONL structure (from live transcript):
    {
      "type": "assistant",
      "message": {
        "role": "assistant",
        "content": [{"type": "tool_use", "name": "Bash", ...}, ...]
      },
      "uuid": "...",
      "timestamp": "..."
    }

Fix: Read role and content from entry["message"] rather than the top level.

Apply this diff to scripts/parse-claude-transcript.py (lines 81-116):
"""

# --- BEFORE ---
BEFORE = """
        role = entry.get("role", "")
        content = entry.get("content", [])

        if isinstance(content, str):
            content = [{"type": "text", "text": content}]

        # Extract usage from assistant messages
        usage = entry.get("usage") or entry.get("message", {}).get("usage", {})
        if usage:
            total_input_tokens += usage.get("input_tokens", 0)
            total_output_tokens += usage.get("output_tokens", 0)

        if role == "assistant":
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    name = block.get("name", "unknown")
                    tool_counter[name] += 1
                    tool_sequences.append(name)

        elif role == "tool":
            # Detect tool errors
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    if block.get("is_error"):
                        if tool_sequences:
                            error_tools.append(tool_sequences[-1])
"""

# --- AFTER ---
AFTER = """
        # Claude Code JSONL wraps messages: {"type": "assistant", "message": {...}}
        # Fall back to top-level role/content for older formats.
        msg = entry.get("message", entry)
        role = msg.get("role", entry.get("type", ""))
        content = msg.get("content", [])

        if isinstance(content, str):
            content = [{"type": "text", "text": content}]

        # Extract usage from assistant messages
        usage = msg.get("usage") or entry.get("usage", {})
        if usage:
            total_input_tokens += usage.get("input_tokens", 0)
            total_output_tokens += usage.get("output_tokens", 0)

        if role == "assistant":
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    name = block.get("name", "unknown")
                    tool_counter[name] += 1
                    tool_sequences.append(name)

        elif role == "tool":
            # Detect tool errors
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    if block.get("is_error"):
                        if tool_sequences:
                            error_tools.append(tool_sequences[-1])
"""
