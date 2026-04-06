#!/usr/bin/env python3
"""Tests for scripts/parse-claude-transcript.py

Exercises the JSONL transcript parser with synthetic but realistic
Claude Code session data covering: tool calls, error detection,
repeated-sequence detection, token accounting, empty input,
stdin mode, file mode, and directory mode.
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate the script under test
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "parse-claude-transcript.py"

# Make the module importable so we can unit-test extract_tool_calls directly.
sys.path.insert(0, str(SCRIPT.parent))
# We import the module by exec'ing its path to avoid filename-with-hyphen issues.
import importlib.util

_spec = importlib.util.spec_from_file_location("parse_claude_transcript", SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
extract_tool_calls = _mod.extract_tool_calls
collect_jsonl_lines = _mod.collect_jsonl_lines


# ---------------------------------------------------------------------------
# Helpers to build realistic JSONL lines
# ---------------------------------------------------------------------------

def _assistant_tool_use(name: str, tool_input: dict | None = None) -> str:
    """Build an assistant message with a single tool_use block."""
    return json.dumps({
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_test",
                    "name": name,
                    "input": tool_input or {},
                }
            ],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        },
    })


def _tool_result(*, is_error: bool = False) -> str:
    """Build a user message carrying a tool_result block."""
    return json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_test",
                    "content": "ok" if not is_error else "Error: something broke",
                    "is_error": is_error,
                }
            ],
        },
    })


def _user_text(text: str = "hello") -> str:
    """Build a plain user text message (no tool results)."""
    return json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": text,
        },
    })


# ---------------------------------------------------------------------------
# Unit tests for extract_tool_calls()
# ---------------------------------------------------------------------------

class TestExtractToolCalls(unittest.TestCase):
    """Direct tests on the core extraction function."""

    def test_empty_input(self):
        result = extract_tool_calls([])
        self.assertEqual(result["tool_call_count"], 0)
        self.assertEqual(result["top_tools"], [])
        self.assertEqual(result["error_tools"], {})
        self.assertEqual(result["repeated_sequences"], [])
        self.assertEqual(result["tool_sequence_preview"], "")

    def test_blank_lines_skipped(self):
        result = extract_tool_calls(["", "  ", "\n"])
        self.assertEqual(result["tool_call_count"], 0)

    def test_malformed_json_skipped(self):
        lines = ["{bad json", _assistant_tool_use("Read")]
        result = extract_tool_calls(lines)
        self.assertEqual(result["tool_call_count"], 1)
        self.assertIn("Read", result["top_tools"])

    def test_single_tool_call(self):
        lines = [_assistant_tool_use("Bash")]
        result = extract_tool_calls(lines)
        self.assertEqual(result["tool_call_count"], 1)
        self.assertEqual(result["top_tools"], ["Bash"])
        self.assertEqual(result["tool_counts"], {"Bash": 1})

    def test_multiple_tool_calls_counted(self):
        lines = [
            _assistant_tool_use("Read"),
            _tool_result(),
            _assistant_tool_use("Edit"),
            _tool_result(),
            _assistant_tool_use("Read"),
            _tool_result(),
        ]
        result = extract_tool_calls(lines)
        self.assertEqual(result["tool_call_count"], 3)
        self.assertEqual(result["tool_counts"]["Read"], 2)
        self.assertEqual(result["tool_counts"]["Edit"], 1)
        # Read is most common so should appear first
        self.assertEqual(result["top_tools"][0], "Read")

    def test_error_tools_detected(self):
        lines = [
            _assistant_tool_use("Bash"),
            _tool_result(is_error=True),
            _assistant_tool_use("Write"),
            _tool_result(is_error=False),
            _assistant_tool_use("Bash"),
            _tool_result(is_error=True),
        ]
        result = extract_tool_calls(lines)
        self.assertEqual(result["error_tools"], {"Bash": 2})

    def test_error_without_prior_tool_is_safe(self):
        """A tool_result error before any tool_use should not crash."""
        lines = [_tool_result(is_error=True)]
        result = extract_tool_calls(lines)
        self.assertEqual(result["error_tools"], {})

    def test_repeated_sequences_detected(self):
        # 5 consecutive Bash calls should trigger repeated detection
        lines = [_assistant_tool_use("Bash") for _ in range(5)]
        result = extract_tool_calls(lines)
        self.assertEqual(len(result["repeated_sequences"]), 1)
        seq = result["repeated_sequences"][0]
        self.assertEqual(seq["tool"], "Bash")
        self.assertEqual(seq["run_length"], 5)
        self.assertEqual(seq["start_index"], 0)

    def test_short_repeat_not_flagged(self):
        # 2 consecutive calls should NOT be flagged (threshold is 3)
        lines = [_assistant_tool_use("Grep"), _assistant_tool_use("Grep")]
        result = extract_tool_calls(lines)
        self.assertEqual(result["repeated_sequences"], [])

    def test_multiple_repeated_runs(self):
        lines = (
            [_assistant_tool_use("Read")] * 4
            + [_assistant_tool_use("Edit")]
            + [_assistant_tool_use("Bash")] * 3
        )
        result = extract_tool_calls(lines)
        self.assertEqual(len(result["repeated_sequences"]), 2)
        self.assertEqual(result["repeated_sequences"][0]["tool"], "Read")
        self.assertEqual(result["repeated_sequences"][1]["tool"], "Bash")

    def test_token_usage_accumulated(self):
        lines = [
            _assistant_tool_use("Bash"),
            _assistant_tool_use("Read"),
        ]
        result = extract_tool_calls(lines)
        # Each assistant message contributes 100 input + 50 output
        self.assertEqual(result["token_usage"]["input_tokens"], 200)
        self.assertEqual(result["token_usage"]["output_tokens"], 100)

    def test_sequence_preview(self):
        lines = [
            _assistant_tool_use("Read"),
            _assistant_tool_use("Edit"),
            _assistant_tool_use("Bash"),
        ]
        result = extract_tool_calls(lines)
        self.assertEqual(result["tool_sequence_preview"], "Read \u2192 Edit \u2192 Bash")

    def test_string_content_handled(self):
        """Messages where content is a plain string (not a list)."""
        line = json.dumps({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": "I'll help you with that.",
            },
        })
        result = extract_tool_calls([line])
        self.assertEqual(result["tool_call_count"], 0)

    def test_older_format_top_level_role(self):
        """Older format: role/content at top level, no 'message' wrapper."""
        line = json.dumps({
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "t1", "name": "Glob", "input": {}},
            ],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        })
        result = extract_tool_calls([line])
        self.assertEqual(result["tool_call_count"], 1)
        self.assertIn("Glob", result["top_tools"])
        self.assertEqual(result["token_usage"]["input_tokens"], 10)


# ---------------------------------------------------------------------------
# Integration tests: run the script as a subprocess
# ---------------------------------------------------------------------------

class TestScriptCLI(unittest.TestCase):
    """Run the script end-to-end and verify JSON output."""

    def _run(self, *args, stdin_data: str | None = None) -> dict:
        cmd = [sys.executable, str(SCRIPT)] + list(args)
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        return json.loads(result.stdout)

    def test_empty_stdin(self):
        out = self._run(stdin_data="")
        self.assertEqual(out["tool_call_count"], 0)
        self.assertEqual(out["note"], "empty transcript")

    def test_stdin_parsing(self):
        lines = "\n".join([
            _assistant_tool_use("Read"),
            _tool_result(),
            _assistant_tool_use("Bash"),
            _tool_result(is_error=True),
        ])
        out = self._run(stdin_data=lines)
        self.assertEqual(out["tool_call_count"], 2)
        self.assertEqual(out["error_tools"], {"Bash": 1})

    def test_file_argument(self):
        lines = "\n".join([
            _assistant_tool_use("Grep"),
            _tool_result(),
        ])
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            f.write(lines)
            f.flush()
            try:
                out = self._run(f.name)
            finally:
                os.unlink(f.name)
        self.assertEqual(out["tool_call_count"], 1)
        self.assertIn("Grep", out["top_tools"])

    def test_directory_argument(self):
        lines_a = "\n".join([_assistant_tool_use("Read")] * 2)
        lines_b = "\n".join([_assistant_tool_use("Edit")])
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "session_a.jsonl").write_text(lines_a)
            (Path(td) / "session_b.jsonl").write_text(lines_b)
            out = self._run(td)
        self.assertEqual(out["tool_call_count"], 3)
        self.assertEqual(out["tool_counts"]["Read"], 2)
        self.assertEqual(out["tool_counts"]["Edit"], 1)

    def test_nested_directory_recursion(self):
        """Transcripts in subdirectories (like hub layout) are found."""
        with tempfile.TemporaryDirectory() as td:
            sub = Path(td) / "2026-04-06" / "abc123"
            sub.mkdir(parents=True)
            (sub / "session.jsonl").write_text(_assistant_tool_use("Bash"))
            out = self._run(td)
        self.assertEqual(out["tool_call_count"], 1)

    def test_mixed_valid_and_invalid_lines(self):
        lines = "\n".join([
            "not json at all",
            _assistant_tool_use("Read"),
            '{"incomplete": true',  # malformed
            _assistant_tool_use("Write"),
        ])
        out = self._run(stdin_data=lines)
        self.assertEqual(out["tool_call_count"], 2)


# ---------------------------------------------------------------------------
# Realistic session transcript test
# ---------------------------------------------------------------------------

class TestRealisticSession(unittest.TestCase):
    """Parse a more realistic multi-turn session transcript."""

    def test_realistic_conversation(self):
        """Simulate a short debugging session with mixed turns."""
        lines = [
            _user_text("Can you check why the tests are failing?"),
            _assistant_tool_use("Bash"),
            _tool_result(is_error=True),
            _assistant_tool_use("Read"),
            _tool_result(),
            _assistant_tool_use("Read"),
            _tool_result(),
            _assistant_tool_use("Edit"),
            _tool_result(),
            _assistant_tool_use("Bash"),
            _tool_result(),
            _user_text("Great, now commit this."),
            _assistant_tool_use("Bash"),
            _tool_result(),
        ]
        result = extract_tool_calls(lines)

        self.assertEqual(result["tool_call_count"], 6)
        self.assertEqual(result["tool_counts"]["Bash"], 3)
        self.assertEqual(result["tool_counts"]["Read"], 2)
        self.assertEqual(result["tool_counts"]["Edit"], 1)
        self.assertEqual(result["error_tools"], {"Bash": 1})
        self.assertEqual(result["repeated_sequences"], [])
        self.assertEqual(
            result["tool_sequence_preview"],
            "Bash \u2192 Read \u2192 Read \u2192 Edit \u2192 Bash \u2192 Bash",
        )
        # 6 assistant messages x 100 input tokens each
        self.assertEqual(result["token_usage"]["input_tokens"], 600)


if __name__ == "__main__":
    unittest.main()
