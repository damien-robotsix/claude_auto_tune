# Proposal: make parser scripts survive the Claude-Code-Action env

**Category:** reliability
**Severity:** high — directly observed and worked around in **this run** and
in the previous `auto-improve` run (`23990412021`).

## Evidence

Under the `anthropics/claude-code-action@v1` harness, the Anthropic SDK
fails to initialize in two distinct ways:

1. `ANTHROPIC_API_KEY` is set but **empty**; the SDK raises
   `TypeError: Could not resolve authentication method`.
2. `ANTHROPIC_BASE_URL` is set but **empty**; if `1` is worked around
   by also setting the key, the client then raises
   `httpx.UnsupportedProtocol: Request URL is missing an 'http://' or
   'https://' protocol`.

The transcript for run `23990412021` shows the previous auto-improve
Claude discovering this the same way (several probe commands, including
`echo "BASE_URL=$ANTHROPIC_BASE_URL"; …`) and eventually landing on the
workaround:

```bash
unset ANTHROPIC_BASE_URL
export ANTHROPIC_API_KEY=$CLAUDE_CODE_OAUTH_TOKEN
```

which makes `api.anthropic.com` accept the OAuth token as if it were an
API key for the Haiku calls the parser makes. That work had to be
rediscovered from scratch in the current run (`23993817915`) — on the
first parser pass all 20 logs came back as `{"summary": "empty log",
"insights": []}` because the SDK traceback was swallowed by
`2>/dev/null` and replaced by the fallback `echo` line.

## Proposed fix — bake the workaround into the parser scripts

Add a tiny shim to the top of both `scripts/parse-workflow-log.py` and
`scripts/parse-claude-transcript.py`, before `import anthropic`:

```python
import os

# The anthropics/claude-code-action harness sets ANTHROPIC_BASE_URL and
# ANTHROPIC_API_KEY to empty strings, which break the SDK. If we detect
# that shape, fall back to the Claude Code OAuth token and clear the
# empty base URL so the default (api.anthropic.com) is used.
if not os.environ.get("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_BASE_URL", None)
if not os.environ.get("ANTHROPIC_API_KEY"):
    oauth = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if oauth:
        os.environ["ANTHROPIC_API_KEY"] = oauth
```

This removes the need for every future auto-improve run to rediscover
the workaround, and — more importantly — removes the dependency on the
calling shell remembering to `unset ANTHROPIC_BASE_URL` before every
invocation. The scripts stay usable from a plain developer shell with a
real `ANTHROPIC_API_KEY` because the first `if` only clears the
variable when it is empty or unset.

## Also: stop hiding parser errors

In `scripts/auto-improve-prompt.md`, the example pipeline uses
`2>/dev/null` on `gh run view` and `|| echo '{...}'` on the parser call.
That combination silently converted a traceback into a "looks like a
successful empty insight" entry for an entire run. Recommended change:

- Keep the `gh run view` stderr suppression (a missing log is expected).
- **Remove** the fallback `echo` on the parser call, or change it to
  write to `/tmp/parse-errors.log` **and** exit the outer loop with a
  loud message. The pipeline-summary step already checks the line
  count; making the parser failure loud is cheap and prevents opening
  an empty PR.
