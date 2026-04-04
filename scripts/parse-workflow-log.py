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
import pathlib

try:
    import anthropic
except ImportError:
    sys.exit("anthropic package not found. Run: pip install anthropic")

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
{
  "summary": "<one sentence summary of what this workflow run did>",
  "insights": [
    {
      "category": "<one of: new_workflow | deterministic_script | subagent_skill | cost_reduction | reliability>",
      "title": "<short title>",
      "description": "<specific actionable description>",
      "priority": "<high | medium | low>"
    }
  ]
}

Only include insights with clear evidence from the log. Return valid JSON only.

Log:
---
{log_content}
---"""

# Truncate logs to avoid token limits — Haiku context window is 200k but we
# keep it lean to stay cheap. Middle sections of logs tend to be noise.
MAX_LOG_CHARS = int(_LOG_PARSER_CFG.get("max_log_chars", 40_000))


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
