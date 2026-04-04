#!/usr/bin/env python3
"""
Parse a GitHub Actions workflow log using Claude Haiku.

Reads log text from stdin (or a file passed as argument), calls the Haiku
model to extract structured improvement insights, and prints JSON to stdout.

Usage:
    gh run view <run-id> --log | python3 scripts/parse-workflow-log.py
    python3 scripts/parse-workflow-log.py <log-file>
"""

import json
import sys
import os

try:
    import anthropic
except ImportError:
    sys.exit("anthropic package not found. Run: pip install anthropic")


SYSTEM_PROMPT = """You are an expert at analyzing Claude Code AI agent workflow logs.
Your job is to extract actionable improvement insights from GitHub Actions logs
where Claude Code was invoked.

Focus on:
1. Tasks that took many tool calls or a long time — potential for deterministic scripts
2. Repeated patterns across similar tasks — candidates for new workflows or skills
3. Expensive model usage — places where Haiku could replace Sonnet/Opus
4. Errors, retries, or failed approaches — reliability improvements
5. Missing capabilities that Claude had to work around manually

Be concise and specific. Each insight should be immediately actionable.
"""

EXTRACT_PROMPT = """Analyze this GitHub Actions workflow log from a Claude Code run.

Extract improvement opportunities as JSON with this exact structure:
{{
  "summary": "<one sentence summary of what this workflow run did>",
  "insights": [
    {{
      "category": "<one of: new_workflow | deterministic_script | subagent_skill | cost_reduction | reliability>",
      "title": "<short title>",
      "description": "<specific actionable description>",
      "priority": "<high | medium | low>"
    }}
  ]
}}

Only include insights with clear evidence from the log. Return valid JSON only.

Log:
---
{log_content}
---"""

# Truncate logs to avoid token limits — Haiku context window is 200k but we
# keep it lean to stay cheap. Middle sections of logs tend to be noise.
MAX_LOG_CHARS = 40_000


def truncate_log(log: str) -> str:
    if len(log) <= MAX_LOG_CHARS:
        return log
    half = MAX_LOG_CHARS // 2
    return (
        log[:half]
        + f"\n\n... [truncated {len(log) - MAX_LOG_CHARS} chars] ...\n\n"
        + log[-half:]
    )


def parse_log(log_content: str) -> dict:
    client = anthropic.Anthropic()

    truncated = truncate_log(log_content)
    prompt = EXTRACT_PROMPT.format(log_content=truncated)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(raw)


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", errors="replace") as f:
            log_content = f.read()
    else:
        log_content = sys.stdin.read()

    if not log_content.strip():
        print(json.dumps({"summary": "empty log", "insights": []}))
        return

    result = parse_log(log_content)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
