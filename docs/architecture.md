---
title: Architecture
layout: default
---

# Architecture

The workspace is intentionally small. Everything you need to understand it fits in a handful of files.

## Repo layout

```
.claude/settings.json     # Shared Claude Code settings (tracked in git)
.github/workflows/        # CI workflows: claude, claude-code-review, auto-improve
CLAUDE.md                 # Agent instructions read by Claude Code
Dockerfile                # Container image used for local runs
docker-compose.yml        # Build/orchestration for the local image
run.sh                    # Entry point for local sessions
auto_tune_config.yml      # Workspace configuration (models, auto-improve, issue tracking)
scripts/                  # Log/transcript parsing, auto-improve prompt, docs-sync prompt
docs/                     # This documentation, published to GitHub Pages
```

## Local vs CI

- **Local** runs go through `run.sh` → `docker compose build` → `docker run` with the repo mounted at `/workspace` and `.claude-home/` providing persistent Claude/`gh` state.
- **CI** runs go through `.github/workflows/*.yml`, which call `anthropics/claude-code-action@v1` with the API key from the `ANTHROPIC_API_KEY` secret.

Both paths share the same `CLAUDE.md`, `.claude/settings.json`, and `auto_tune_config.yml`, so behaviour stays consistent.

## Self-improvement loop

The `auto-improve` workflow is what makes this a *self-tuning* workspace:

1. Collect recent run history (workflow logs in full; session transcripts capped by `auto_improve.default_conversation_limit`).
2. Compact it through the **deterministic** `scripts/parse-*.py` helpers (regex/counters only; no LLM calls, no credentials).
3. Feed the result into Claude with `scripts/auto-improve-prompt.md`, which delegates the clustering/reasoning step to the `workflow-insights-extractor` subagent (`.claude/agents/workflow-insights-extractor.md`) via the Task tool. That subagent is the *only* component that reasons over the deterministic signals.
4. Reconcile findings against a long-term issue tracker (one persistent GitHub issue per improvement subject, carrying an `auto-improve:<state>` label) and, where possible, open a focused fix PR linked to its issue. Issues are only closed after `tracking.verify_runs` successive clean runs confirm the problem is gone.

A second, narrower loop — the daily **docs-sync** agent defined by `scripts/docs-sync-prompt.md` — keeps pages under `docs/` aligned with recent `main` commits via the routing rules in [`docs/.docsrules`](https://github.com/damien-robotsix/claude_auto_tune/blob/main/docs/.docsrules). It never touches code.

Keeping both loops narrow and the surface area small is deliberate: it makes each improvement easy to review and easy to revert.
