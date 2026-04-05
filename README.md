# Claude Auto Tune

A self-improving [Claude Code](https://claude.com/claude-code) workspace. Run Claude locally in Docker for safe autonomous operation, or through CI via the official `anthropics/claude-code-action@v1` GitHub Action.

## Quick start

Local (Docker):

```bash
./run.sh
```

CI (GitHub Actions):

```bash
gh auth login -h github.com -s repo,workflow
# then, inside Claude Code CLI:
/install-github-app
```

Then mention `@claude` in any issue or PR comment.

## Documentation

Full documentation is published to GitHub Pages:

**https://damien-robotsix.github.io/claude_auto_tune/**

Source lives in [`docs/`](docs/):

- [Quick start](docs/quickstart.md)
- [Configuration](docs/configuration.md)
- [Workflows](docs/workflows.md)
- [Architecture](docs/architecture.md)
