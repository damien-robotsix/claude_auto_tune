#!/usr/bin/env python3
"""
PROPOSAL: Fix KeyError in parse-workflow-log.py caused by JSON curly braces
in EXTRACT_PROMPT conflicting with Python str.format().

Evidence: 7 of 20 workflow runs (runs with non-empty logs) crashed with:
  KeyError: '\n  "summary"'
at scripts/parse-workflow-log.py:79 in parse_log().

Root cause: The EXTRACT_PROMPT template contains literal JSON braces like
  {"summary": "...", "insights": [...]}
Python's str.format() interprets these as {<variable>} placeholders and
raises KeyError when it can't find them.

Fix: Escape all literal braces in the JSON example with double braces {{ }},
so str.format() treats them as literal characters.

Apply this diff to scripts/parse-workflow-log.py:
"""

# --- BEFORE (lines 38-57 of scripts/parse-workflow-log.py) ---
BEFORE = r"""
EXTRACT_PROMPT = \"\"\"Analyze this GitHub Actions workflow log from a Claude Code run.

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
---\"\"\"
"""

# --- AFTER: escape all literal braces except {log_content} ---
AFTER = r"""
EXTRACT_PROMPT = \"\"\"Analyze this GitHub Actions workflow log from a Claude Code run.

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
---\"\"\"
"""

# Note: parse-claude-transcript.py already has this fix applied (uses {{ }}).
# The fix should be applied to parse-workflow-log.py to match.
