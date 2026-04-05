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
auto_tune_config.yml      # Workspace configuration (models, auto-improve, log parser)
scripts/                  # Log/transcript parsing + auto-improve prompt
docs/                     # This documentation, published to GitHub Pages
```

## Local vs CI

- **Local** runs go through `run.sh` → `docker compose build` → `docker run` with the repo mounted at `/workspace` and `.claude-home/` providing persistent Claude/`gh` state.
- **CI** runs go through `.github/workflows/*.yml`, which call `anthropics/claude-code-action@v1` with the API key from the `ANTHROPIC_API_KEY` secret.

Both paths share the same `CLAUDE.md`, `.claude/settings.json`, and `auto_tune_config.yml`, so behaviour stays consistent.

## Self-improvement loop

The `auto-improve` workflow is what makes this a *self-tuning* workspace:

1. Collect recent run history (logs, transcripts).
2. Compact it through the `scripts/parse-*.py` helpers, bounded by `log_parser` limits.
3. Feed the result into Claude with `scripts/auto-improve-prompt.md`.
4. Open PRs that tweak prompts, configuration, or tooling based on what was learned.

Keeping the loop narrow and the surface area small is deliberate: it makes each improvement easy to review and easy to revert.
