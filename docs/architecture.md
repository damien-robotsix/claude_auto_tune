---
title: Architecture
layout: default
---

# Architecture

The workspace is intentionally small. Everything you need to understand it fits in a handful of files.

## Repo layout

```
.claude/settings.json     # Shared Claude Code settings (tracked in git)
.github/workflows/        # CI workflows (11): claude, claude-agent, claude-code-review, auto-improve-discover, auto-improve-verify, hub-daily-sweep, hub-sync, hub-adopt, clean-branches, docs-sync, config-sanity
CLAUDE.md                 # Agent instructions read by Claude Code
Dockerfile                # Container image used for local runs
docker-compose.yml        # Build/orchestration for the local image
run.sh                    # Entry point for local sessions
auto_tune_config.yml      # Workspace configuration (models, auto-improve, issue tracking)
fork-workspace.sh         # Create a customized fork of this workspace (interactive)
scripts/                  # Parsers, agent prompts, hub helpers, stale-branch cleanup
docs/                     # This documentation, published to GitHub Pages
```

## Local vs CI

- **Local** runs go through `run.sh` → `docker compose build` → `docker run` with the repo mounted at `/workspace` and `.claude-home/` providing persistent Claude/`gh` state.
- **CI** runs go through `.github/workflows/*.yml`, which call `anthropics/claude-code-action@v1` with the API key from the `ANTHROPIC_API_KEY` secret.

Both paths share the same `CLAUDE.md`, `.claude/settings.json`, and `auto_tune_config.yml`, so behaviour stays consistent.

## Self-improvement loop

The self-improvement loop is split into two workflows so that problem **discovery** and fix **verification** stay independent:

1. **Discover** (`auto-improve-discover.yml`, driven by `scripts/auto-improve-discover-prompt.md`) — collects recent run history (workflow logs in full; session transcripts capped by `auto_improve.default_conversation_limit`), compacts it through the deterministic `scripts/parse-*.py` helpers, and delegates clustering to the `workflow-insights-extractor` subagent (`.claude/agents/workflow-insights-extractor.md`) via the Task tool. It reconciles findings against a long-term issue tracker (one persistent GitHub issue per improvement subject, carrying an `auto-improve:<state>` label), captures a frozen `## Baseline (before fix)` section on every newly created issue, and ships focused fix PRs that reference the issue via `Refs #<num>` so GitHub never auto-closes.
2. **Verify** (`auto-improve-verify.yml`, driven by `scripts/auto-improve-verify-prompt.md`) — runs per-issue, either on its own daily cron or on demand with an `issue_number` input. For each target issue it resolves a `WINDOW_START` timestamp (the linked PR's merge time, falling back to the issue creation time) and invokes the extractor subagent with that window as a **hard filter**, so the subagent only reads workflow logs and session transcripts from runs created after the fix landed — pre-fix conversations can never enter the "after" snapshot. The subagent is also scoped to the issue's fingerprint key so it returns only signals that match the problem. Verify then appends a `## Verification history` entry comparing the in-window counts to the frozen baseline and — uniquely — owns the transitions to `auto-improve:merged`, `auto-improve:solved` (closed), and regression reopens. There is no configurable verification window to tune: a single clean verify run with zero in-window matches is sufficient to close.

The split guarantees that a fix is only considered "done" once a dedicated per-issue run has actually compared the world before and after the fix, rather than being closed automatically the moment a PR merges.

Both discover and verify use two additive **triage flags** alongside the state labels: `auto-improve:needs-human` (issue cannot be auto-fixed) and `auto-improve:waiting-data` (not enough post-fix runs to decide). These flags coexist with exactly one state label and are removed when they no longer apply. The verify workflow also filters reliability-category issues to **controllable** errors only — network/auth failures are excluded from the before/after comparison.

A second, narrower loop — the daily **docs-sync** agent defined by `scripts/docs-sync-prompt.md` — keeps pages under `docs/` aligned with recent `main` commits via the routing rules in [`docs/.docsrules`](https://github.com/damien-robotsix/claude_auto_tune/blob/main/docs/.docsrules). It never touches code.

## Cross-workspace hub

Beyond the local self-improvement loop, a set of hub workflows share improvements across independent workspace forks via the shared [`claude-auto-tune-hub`](https://github.com/damien-robotsix/claude-auto-tune-hub) repo (configured under the `hub:` config key — see [Configuration](configuration.md)):

- **Hub daily sweep** (`hub-daily-sweep.yml`, `scripts/hub-daily-sweep-prompt.md`) — scans recent `main` commits, creates proposal issues in the hub for changes that could benefit other workspaces.
- **Hub sync** (`hub-sync.yml`, `scripts/hub-sync-prompt.md`) — Phase 2: reviews open hub proposals, posts a structured verdict comment (`adopt` / `reject` / `defer`), and labels them.
- **Hub adopt** (`hub-adopt.yml`, `scripts/hub-adopt-prompt.md`) — Phase 3: for proposals labelled `adopt`, creates a PR that adapts the proposed change to the local workspace.

## Other automation

- **`claude-agent.yml`** — autonomous agent workflow triggered by `@claude` mentions in issues, with a confidence gate.
- **`clean-branches.yml`** / `scripts/clean-stale-branches.py` — automated cleanup of remote branches with no associated open PR.
- **`fork-workspace.sh`** — interactive script to create a customized copy of this workspace as a new repo.

Keeping each loop narrow and the surface area small is deliberate: it makes each improvement easy to review and easy to revert.
