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

```yaml
tracking:
  verify_runs: 1
```

- `verify_runs` — number of successive clean per-issue verify runs required before the verify workflow closes an issue as `auto-improve:solved`. Default is `1` for the split design: because the verify workflow does a targeted before/after comparison against the frozen `## Baseline (before fix)` snapshot, a single clean run is enough evidence to close. Raise this value if you want a stricter verification window.

## Claude settings

Per-workspace Claude Code settings (tools, permissions, etc.) live in [`.claude/settings.json`](https://github.com/damien-robotsix/claude_auto_tune/blob/main/.claude/settings.json) and are tracked in git so they apply to every contributor and CI run.
