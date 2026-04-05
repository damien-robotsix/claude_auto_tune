# Fix: `parse-workflow-log.py` fails in CI due to empty `ANTHROPIC_BASE_URL`

**Category:** `reliability` — **Priority:** high
**Evidence:** Directly observed in auto-improve run 23990412021 (2026-04-05). The
entire Haiku parsing step produced 20 consecutive `{"summary":"empty log",...}`
results in the first pass because `anthropic.Anthropic()` raised
`APIConnectionError` on every call.

## Root cause

In the Claude Code GitHub Action runner environment, the variable
`ANTHROPIC_BASE_URL` is exported as an **empty string** (not unset). The
`anthropic` Python SDK reads this env var verbatim and, when non-`None`, uses
it as the base URL. An empty string causes `httpx` to raise
`httpx.UnsupportedProtocol: Request URL is missing an 'http://' or 'https://'
protocol.`, surfaced by the SDK as `APIConnectionError: Connection error.`

The SDK does not fall back to `https://api.anthropic.com` when the env var is
empty-but-set.

## Fix

Update `scripts/parse-workflow-log.py` and `scripts/parse-claude-transcript.py`
to unset the problematic env vars before instantiating the client, or pass
`base_url` explicitly.

Minimal patch in `scripts/parse-workflow-log.py` around line 109:

```python
def parse_log(log_content: str) -> dict:
    # In Claude Code action environments, ANTHROPIC_BASE_URL may be set to
    # an empty string which breaks the SDK. Strip empty overrides.
    for var in ("ANTHROPIC_BASE_URL", "ANTHROPIC_BEDROCK_BASE_URL",
                "ANTHROPIC_VERTEX_BASE_URL", "ANTHROPIC_FOUNDRY_BASE_URL"):
        if os.environ.get(var) == "":
            os.environ.pop(var, None)
    client = anthropic.Anthropic()
    ...
```

Additionally, the auto-improve workflow script block should also prepend:

```bash
[ -z "$ANTHROPIC_BASE_URL" ] && unset ANTHROPIC_BASE_URL
```

before invoking the Python parsers, as a belt-and-suspenders measure.

## Why this matters

Without this fix, every run of the auto-improvement pipeline silently produces
empty insights (all logs look "empty" because the SDK error is caught by the
`if not log_content.strip()` fallback only if `parse_log` is never called — in
practice the exception propagates and the shell `||` branch writes the empty
placeholder). The pipeline appears to succeed while producing zero signal.
