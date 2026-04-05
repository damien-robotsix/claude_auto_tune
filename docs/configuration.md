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
  claude_code: "opus"   # main claude.yml workflow
  code_review: "opus"   # code-review workflow
  auto_improve: "opus"  # auto-improve workflow
  log_parser: "haiku"   # log/transcript parsing scripts (cheaper, fast)
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
```

- `default_conversation_limit` — maximum number of Claude Code session transcripts the auto-improve workflow analyzes in a single pass. Workflow logs are always parsed in full (no cap).
- `schedule` — cron expression (UTC) used by the scheduled workflow trigger.

## Issue tracking

```yaml
tracking:
  verify_runs: 2
```

- `verify_runs` — number of successive clean runs (no recurrence) required after a fix PR merges before the auto-improve tracker closes an issue as `auto-improve:solved`.

## Claude settings

Per-workspace Claude Code settings (tools, permissions, etc.) live in [`.claude/settings.json`](https://github.com/damien-robotsix/claude_auto_tune/blob/main/.claude/settings.json) and are tracked in git so they apply to every contributor and CI run.
