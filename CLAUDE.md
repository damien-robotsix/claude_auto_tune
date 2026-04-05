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
- To gather PR context, use `python3 scripts/collect-pr-review-context.py <pr-number>` instead of issuing multiple `gh api` / `gh pr view` Bash calls. It returns PR metadata, diff, linked issues, comments, and check-run status as a single JSON bundle.

## Safety rules

- Never commit secrets, API keys, credentials, or private keys
- Never modify `.env`, `*.key`, `*.pem`, or `credentials.*` files
- Never force-push or rewrite published history
- Never skip CI checks or pre-commit hooks

## Key conventions

- When something fails or needs rework, capture the lesson so the pattern is not repeated
- Prefer simple, direct solutions over abstractions until a pattern repeats

<!--
CI-sandbox Bash rules (allowlist, no multi-op pipes, no /tmp redirection,
no 2>&1, literal gh args, read-only workflow files) live in
docs/ci-sandbox-rules.md and are appended to this file at runtime by the
CI workflows (.github/workflows/claude*.yml, auto-improve.yml). They are
intentionally not inlined here so local runs stay free of CI-only
guardrails.
-->
