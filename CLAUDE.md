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

**Scope:** these rules only apply when running inside
`anthropics/claude-code-action@v1` (the claude.yml, claude-code-review.yml,
and auto-improve.yml workflows), where Bash tool calls are restricted by
an allowlist and a further sandbox. Local runs (Docker or any invocation
that skips permissions) are unaffected and may ignore this section. In
CI, follow these rules on **every** Bash call — they are the largest
single source of failed tool calls in this workspace. Full details with
exact harness error strings live in
[`docs/ci-sandbox-rules.md`](docs/ci-sandbox-rules.md).

- **One operation per `Bash` call.** Shell pipes (`|`), command chains
  (`&&`, `;`), command substitution (`$(...)`, backticks), and process
  substitution each count as separate operations and each sub-command
  must individually match the allowlist. Rejected with
  `This Bash command contains multiple operations. The following part
  requires approval: ...`. Split into sequential calls, or pipe through
  a single `python3 -c '...'` post-processor.
- **Do not redirect output outside the working directory.** Writing to
  `/tmp/*` or any absolute path outside `/home/runner/work/<repo>/<repo>`
  is blocked with `Output redirection to '...' was blocked`. For scratch
  data, write under `./.scratch/` inside the repo and clean up afterward;
  for real files use the `Write` tool.
- **`2>&1` counts as redirection.** Omit it; tool results already include
  stderr.
- **`gh` arguments must be literal values, not URL paths.**
  `gh pr view owner/repo/pull/7` is parsed as a branch name and fails
  with `no pull requests found for branch "owner/repo/pull/7"`. Use the
  numeric PR id alone: `gh pr view 7` (add `--repo owner/repo` only when
  the target is not the current repository).
- **`.github/workflows/**` is effectively read-only.** The GitHub App
  token this agent runs under does not carry the `workflows` permission,
  so pushes that touch workflow files are rejected at the remote. If a
  fix needs a workflow change, raise/update the tracked issue with a
  diff for the human maintainer instead of editing the file.
