#!/usr/bin/env python3
"""
Parse a Claude Code session transcript (JSONL) using Claude Haiku.

Claude Code saves session transcripts as JSONL files under:
  ~/.claude/projects/<encoded-path>/<session-id>.jsonl

Each line is a JSON object representing one turn (user, assistant, or tool result).
This script reads that JSONL, extracts a tool-call summary, then sends it to
Haiku for structured insight extraction.

Usage:
    cat ~/.claude/projects/**/*.jsonl | python3 scripts/parse-claude-transcript.py
    python3 scripts/parse-claude-transcript.py <transcript-file.jsonl>
    python3 scripts/parse-claude-transcript.py <dir-of-jsonl-files/>
"""

import json
import sys
import os
import pathlib
from collections import Counter

try:
    import anthropic
except ImportError:
    sys.exit("anthropic package not found. Run: pip install anthropic")


def _build_anthropic_client() -> "anthropic.Anthropic":
    """Construct an Anthropic client that works inside claude-code-action.

    The claude-code-action GitHub Action exports ``ANTHROPIC_API_KEY=""`` and
    ``ANTHROPIC_BASE_URL=""`` (empty strings) so that the action's own harness
    uses OAuth via ``CLAUDE_CODE_OAUTH_TOKEN``. Those empty values break the
    Anthropic SDK, which treats an empty string as "no credentials" and an
    empty base URL as a malformed target. Fall back to the OAuth token when
    the API key is missing, and strip empty URL overrides so the SDK uses its
    default endpoint.
    """
    if os.environ.get("ANTHROPIC_BASE_URL", None) == "":
        os.environ.pop("ANTHROPIC_BASE_URL", None)

    api_key = os.environ.get("ANTHROPIC_API_KEY") or None
    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or None

    if api_key:
        return anthropic.Anthropic(api_key=api_key)
    if oauth_token:
        return anthropic.Anthropic(auth_token=oauth_token)
    return anthropic.Anthropic()

_DEFAULT_MODEL_ALIASES = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}


def _load_config() -> dict:
    """Load auto_tune_config.yml from the repo root (two levels up from scripts/)."""
    config_path = pathlib.Path(__file__).parent.parent / "auto_tune_config.yml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(config_path.read_text()) or {}
    except Exception:
        return {}


_CONFIG = _load_config()
_LOG_PARSER_CFG = _CONFIG.get("log_parser", {})


def _resolve_model(name: str) -> str:
    """Return the full model ID for a short alias, or the name as-is.

    Aliases are read from ``model_aliases`` in auto_tune_config.yml; the
    built-in defaults are used when that section is absent.
    """
    aliases = _CONFIG.get("model_aliases", _DEFAULT_MODEL_ALIASES)
    return aliases.get(name.lower(), name)


SYSTEM_PROMPT = """You are an expert at analyzing Claude Code AI agent session transcripts.
Your job is to identify patterns, inefficiencies, and improvement opportunities from
sequences of tool calls made by Claude Code during a task.

Focus on:
1. Repeated or redundant tool calls — could be cached or avoided
2. Long tool call chains to accomplish simple tasks — candidates for helper scripts
3. Failed tool calls or error-recovery loops — reliability improvements
4. Missing tools that Claude worked around — capability gaps
5. Expensive multi-step patterns that a single deterministic script could replace
"""

EXTRACT_PROMPT = """Analyze this Claude Code session tool-call summary.

The summary shows which tools were called, how many times, and any notable patterns
extracted from the JSONL transcript.

Extract improvement opportunities as JSON with this exact structure:
{{
  "summary": "<one sentence: what task this session accomplished>",
  "tool_call_count": <total number of tool calls>,
  "top_tools": [<list of top 5 tool names by call count>],
  "insights": [
    {{
      "category": "<one of: new_workflow | deterministic_script | subagent_skill | cost_reduction | reliability | capability_gap>",
      "title": "<short title>",
      "description": "<specific actionable description referencing the tool call patterns>",
      "priority": "<high | medium | low>"
    }}
  ]
}}

Only include insights with clear evidence from the transcript. Return valid JSON only.

Session tool-call summary:
---
{transcript_summary}
---"""

MAX_SUMMARY_CHARS = int(_LOG_PARSER_CFG.get("max_summary_chars", 30_000))


def extract_tool_calls(lines: list[str]) -> dict:
    """Parse JSONL transcript lines and extract tool call statistics."""
    tool_counter: Counter = Counter()
    error_tools: list[str] = []
    tool_sequences: list[str] = []
    total_input_tokens = 0
    total_output_tokens = 0
    session_summary = ""

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue

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
                        # Map back to the tool name via the preceding sequence entry
                        if tool_sequences:
                            error_tools.append(tool_sequences[-1])

    # Build a readable summary for Haiku
    lines_out: list[str] = []

    if total_input_tokens or total_output_tokens:
        lines_out.append(
            f"Token usage: {total_input_tokens} input, {total_output_tokens} output"
        )

    lines_out.append(f"Total tool calls: {sum(tool_counter.values())}")

    if tool_counter:
        lines_out.append("\nTool call counts (descending):")
        for tool, count in tool_counter.most_common(20):
            lines_out.append(f"  {tool}: {count}")

    if error_tools:
        error_counts = Counter(error_tools)
        lines_out.append("\nFailed tool calls:")
        for tool, count in error_counts.most_common():
            lines_out.append(f"  {tool}: {count} error(s)")

    # Detect repeated sequences (runs of 3+ identical consecutive calls)
    repeated: list[str] = []
    i = 0
    while i < len(tool_sequences):
        j = i
        while j < len(tool_sequences) and tool_sequences[j] == tool_sequences[i]:
            j += 1
        run_len = j - i
        if run_len >= 3:
            repeated.append(f"  {tool_sequences[i]} called {run_len}x in a row")
        i = j
    if repeated:
        lines_out.append("\nRepeated consecutive calls:")
        lines_out.extend(repeated)

    # Truncate sequence to show first 100 tool calls
    if tool_sequences:
        seq_preview = " → ".join(tool_sequences[:100])
        if len(tool_sequences) > 100:
            seq_preview += f" ... (+{len(tool_sequences) - 100} more)"
        lines_out.append(f"\nTool call sequence (first 100):\n  {seq_preview}")

    return {
        "text": "\n".join(lines_out),
        "total_calls": sum(tool_counter.values()),
        "top_tools": [t for t, _ in tool_counter.most_common(5)],
    }


def parse_transcript(summary_text: str) -> dict:
    client = _build_anthropic_client()

    if len(summary_text) > MAX_SUMMARY_CHARS:
        summary_text = summary_text[:MAX_SUMMARY_CHARS] + "\n\n... [truncated] ..."

    prompt = EXTRACT_PROMPT.format(transcript_summary=summary_text)

    _alias = _CONFIG.get("models", {}).get("log_parser", "haiku")
    message = client.messages.create(
        model=_resolve_model(_alias),
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw_lines = raw.split("\n")
        raw = "\n".join(raw_lines[1:-1] if raw_lines[-1] == "```" else raw_lines[1:])

    return json.loads(raw)


def collect_jsonl_lines(source: str) -> list[str]:
    """Collect all JSONL lines from a file, directory, or stdin."""
    p = pathlib.Path(source)
    if p.is_dir():
        lines: list[str] = []
        for jf in sorted(p.rglob("*.jsonl")):
            lines.extend(jf.read_text(errors="replace").splitlines())
        return lines
    elif p.is_file():
        return p.read_text(errors="replace").splitlines()
    else:
        return []


def main():
    if len(sys.argv) > 1:
        all_lines: list[str] = []
        for arg in sys.argv[1:]:
            all_lines.extend(collect_jsonl_lines(arg))
    else:
        all_lines = sys.stdin.read().splitlines()

    if not any(line.strip() for line in all_lines):
        print(json.dumps({"summary": "empty transcript", "tool_call_count": 0, "top_tools": [], "insights": []}))
        return

    extracted = extract_tool_calls(all_lines)

    if extracted["total_calls"] == 0:
        print(json.dumps({"summary": "no tool calls found", "tool_call_count": 0, "top_tools": [], "insights": []}))
        return

    result = parse_transcript(extracted["text"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
