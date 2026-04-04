# Claude Auto Tune

A self-improving Claude Code workspace. Run Claude locally in Docker for safe autonomous operation, or through CI via the official `anthropics/claude-code-action@v1` GitHub Action.

## Quick start

### Local (Docker)

```bash
./run.sh
```

This builds and runs Claude in a Docker container with `--dangerously-skip-permissions` for autonomous operation. Auth state persists in `.claude-home/`.

### CI (GitHub Actions)

First, authenticate with GitHub:

```bash
gh auth login
```

Then, from inside Claude Code CLI:

```
/install-github-app
```

This installs the Claude GitHub App and configures the `ANTHROPIC_API_KEY` secret. Then mention `@claude` in any issue or PR comment.

## Structure

```
.claude/settings.json   # Shared Claude settings (tracked in git)
CLAUDE.md               # Agent instructions
Dockerfile              # Container for local runs
docker-compose.yml      # Docker orchestration
run.sh                  # Entry point for local sessions
```
