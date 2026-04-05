---
title: Configuration
layout: default
---

# Configuration

Most workspace-level tuning lives in [`auto_tune_config.yml`](https://github.com/damien-robotsix/claude_auto_tune/blob/main/auto_tune_config.yml) at the repo root. Workflows and scripts read it to decide which model to use and how the auto-improve loop behaves.

## Models

The `models` section assigns a model family to each entry point:

```yaml
models:
  claude_code: "opus"          # main claude.yml workflow
  code_review: "opus"          # code-review workflow
  auto_improve: "opus"         # auto-improve discover workflow
  auto_improve_verify: "opus"  # per-issue auto-improve verify workflow
```

You can use a short alias (`haiku`, `sonnet`, `opus`) or pin a full model ID (for example `claude-sonnet-4-6`).

## Model aliases

The `model_aliases` section maps short names to specific model IDs. Update this section when new model versions are released:

```yaml
model_aliases:
  haiku:  "claude-haiku-4-5-20251001"
  sonnet: "claude-sonnet-4-6"
  opus:   "claude-opus-4-6"
```

Scripts fall back to built-in defaults if this section is missing.

## Auto-improve loop

```yaml
auto_improve:
  default_conversation_limit: 20
  schedule: "0 3 * * 0"

auto_improve_verify:
  schedule: "0 6 * * *"
```

- `auto_improve.default_conversation_limit` — maximum number of Claude Code session transcripts the discover workflow analyzes in a single pass. Workflow logs are always parsed in full (no cap).
- `auto_improve.schedule` — cron expression (UTC) used by the discover workflow trigger.
- `auto_improve_verify.schedule` — cron expression (UTC) used by the per-issue verify workflow trigger. The verify workflow can also be dispatched manually with an `issue_number` input.

## Issue tracking

The split auto-improve design has no tunable verification threshold. The
verify workflow filters signals to workflow runs created after the fix
PR merged (`WINDOW_START = pr.mergedAt`), which makes the per-issue
before/after comparison inherently strict: if zero in-window matches for
the fingerprint are found, the issue is closed on that single clean
verify run. Regressions after closure are caught by the daily verify
cron and automatically reopen the issue.

## Claude settings

Per-workspace Claude Code settings (tools, permissions, etc.) live in [`.claude/settings.json`](https://github.com/damien-robotsix/claude_auto_tune/blob/main/.claude/settings.json) and are tracked in git so they apply to every contributor and CI run.
