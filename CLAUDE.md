# CLAUDE.md

This file provides guidance to Claude Code when working in this workspace.

## Purpose

This is a self-improving Claude Code workspace. Claude can be invoked locally (via Docker for safe autonomous operation) or through CI. The workspace will grow incrementally — start simple, add tooling as patterns emerge.

## Working on tasks

- Read the full task description and all available context before starting
- Follow existing code patterns and conventions
- Write clear, focused commit messages explaining the "why"
- Keep changes scoped to one task — avoid unrelated modifications
- Run the test suite if one exists before finalizing changes

## Code review

- Focus on correctness, readability, and security
- Flag potential bugs, edge cases, and missing error handling
- Suggest improvements only when they meaningfully improve the code
- Be specific — reference exact lines and propose concrete fixes

## Safety rules

- Never commit secrets, API keys, credentials, or private keys
- Never modify `.env`, `*.key`, `*.pem`, or `credentials.*` files
- Never force-push or rewrite published history
- Never skip CI checks or pre-commit hooks

## Key conventions

- When something fails or needs rework, capture the lesson so the pattern is not repeated
- Prefer simple, direct solutions over abstractions until a pattern repeats

## CI sandbox — Bash command rules

When running inside `anthropics/claude-code-action@v1` (the claude.yml,
claude-code-review.yml, and auto-improve.yml workflows), Bash tool calls
are restricted by an allowlist and a sandbox. Before issuing non-trivial
Bash commands in CI, read [`docs/ci-sandbox-rules.md`](docs/ci-sandbox-rules.md)
— it documents the exact harness error strings and the concrete
workarounds for each failure mode (multi-operation pipelines, output
redirection, `2>&1`, `gh` URL-style arguments, and workflow-file pushes).
