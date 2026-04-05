# Proposal: track the Node.js 20 → 24 deprecation for GitHub Actions

**Category:** reliability
**Confidence:** medium — one high-priority Haiku insight, one workflow
log deprecation warning. Not urgent today, but has a fixed deadline.

## Evidence

The `Claude Code Review` workflow log for run `23990519154` contains:

> Node.js 20 actions (`checkout@v4`, `upload-artifact@v4`, `setup-bun`)
> will fail after **June 2, 2026**. Set
> `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` or update actions.

The Haiku parser flagged this high-priority. It affects all three
workflows in this repo (`.github/workflows/claude.yml`,
`.github/workflows/claude-code-review.yml`,
`.github/workflows/auto-improve.yml`).

## Recommendation

Wait for the upstream actions (`actions/checkout@v5`,
`actions/upload-artifact@v5`, `anthropics/claude-code-action@v2`,
`oven-sh/setup-bun@v2+`) to publish Node 24 builds, then bump. **Do
not** set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` as a workaround on
CI today — it changes the runtime under actions that were tested on
Node 20 and can produce hard-to-diagnose breakage. A calendar reminder
for early May 2026 is enough.

No file change is proposed right now — this file exists so the
deprecation is captured in the proposal set and the next auto-improve
run can see it was already logged.
