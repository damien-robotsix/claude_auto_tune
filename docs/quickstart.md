---
title: Quick start
layout: default
---

# Quick start

There are two ways to use this workspace: locally through Docker, or in CI via the Claude GitHub App.

## Local (Docker)

```bash
./run.sh
```

This builds and runs Claude in a Docker container with `--dangerously-skip-permissions` for autonomous operation. Auth state persists in `.claude-home/` on the host, so you only need to authenticate once.

What `run.sh` does:

1. Builds the `claude_auto_tune-claude` image from the repo `Dockerfile` (via `docker compose build`).
2. Ensures the host-side bind-mount directories exist under `.claude-home/`.
3. Runs the container interactively with the workspace mounted at `/workspace`.

You can pass extra flags straight through to the Claude CLI:

```bash
./run.sh --help
```

## CI (GitHub Actions)

First, authenticate with GitHub using the required scopes:

```bash
gh auth login -h github.com -s repo,workflow
```

Then, from inside the Claude Code CLI:

```
/install-github-app
```

This installs the Claude GitHub App and configures the `ANTHROPIC_API_KEY` secret in the repo. Once installed, mention `@claude` in any issue or PR comment to trigger a run.

## Requirements

- Docker (for local runs)
- `gh` CLI (for the GitHub App setup step)
- A valid Anthropic API key, stored as the `ANTHROPIC_API_KEY` repo secret for CI runs
