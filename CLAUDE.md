# CLAUDE.md

This file provides guidance to Claude Code when working in this workspace.

## Purpose

This is a self-improving Claude Code workspace. Claude can be invoked locally (via Docker for safe autonomous operation) or through CI. The workspace will grow incrementally — start simple, add tooling as patterns emerge.

## Working on tasks

- Always `Read` a file before calling `Write` or `Edit` on it — the tools reject calls on files that have not been read in the current session, and skipping this wastes a round-trip
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
- **Do NOT issue parallel `gh pr *` or `gh api` Bash calls.** When multiple parallel `gh` Bash calls are dispatched in one assistant turn, the first failure cancels all siblings — wasting every queued call. Always gather PR context with a single `scripts/collect-pr-review-context.py` call. If you must use `gh` directly, issue calls sequentially, never in parallel.
- **Do NOT spawn `Agent` subagents for simple lookups.** Use `Read`, `Grep`, or `Glob` directly — they are faster and cheaper. Each `Agent` subagent adds ~5k tokens of overhead. Specifically:
  - To read a file or check its contents → `Read`
  - To find files by name/pattern → `Glob`
  - To search code for a string or regex → `Grep`
  - To check a function signature or class definition → `Grep` or `Read`
  - **Only** use `Agent` when the task genuinely requires multi-step exploration across many files where you cannot predict the search path in advance (e.g., tracing a complex call chain through 5+ files). A sequence of 2+ consecutive `Agent` calls is almost always wrong — use direct tools instead.

## Safety rules

- Never commit secrets, API keys, credentials, or private keys
- Never modify `.env`, `*.key`, `*.pem`, or `credentials.*` files
- Never force-push or rewrite published history
- Never skip CI checks or pre-commit hooks

## Key conventions

- When something fails or needs rework, capture the lesson so the pattern is not repeated
- Prefer simple, direct solutions over abstractions until a pattern repeats
- The auto-improve system is split in two: `auto-improve-discover.yml` raises/updates tracked issues and ships fix PRs using `Refs #<num>` (never `Fixes #`/`Closes #`/`Resolves #`), and `auto-improve-verify.yml` owns all per-issue before/after comparison and is the only workflow allowed to close an `auto-improve` issue.
- The `Read` tool caps file content at 10k tokens and rejects unbounded calls on larger files with `File content (N tokens) exceeds maximum allowed tokens (10000). Use offset and limit parameters...`. For files you expect to be large (workflow logs, JSON bundles from `scripts/collect-pr-review-context.py`, long markdown prompts under `scripts/`, parser output, transcripts), do one of: (a) `Grep` first and then `Read` with a targeted `offset`/`limit` window, (b) start with `Read(..., limit=200)` and paginate only as needed, or (c) pipe the file through a `python3 -c` filter via `Bash`. Do not issue an unbounded `Read` on a file whose size you have not checked.

<!--
CI-sandbox Bash rules (allowlist, no multi-op pipes, no /tmp redirection,
no 2>&1, literal gh args, read-only workflow files) live in
docs/ci-sandbox-rules.md and are appended to this file at runtime by the
CI workflows (.github/workflows/claude*.yml, auto-improve-*.yml). They are
intentionally not inlined here so local runs stay free of CI-only
guardrails.
-->


# CI sandbox — Bash command rules

When running inside `anthropics/claude-code-action@v1` (the claude.yml,
claude-code-review.yml, claude-agent.yml, auto-improve-discover.yml,
auto-improve-verify.yml, hub-daily-sweep.yml, and hub-sync.yml workflows), Bash tool calls are
restricted to the `--allowed-tools` list in the workflow and are further
filtered by a sandbox. To avoid wasting tool calls on rejected commands,
follow these rules:

- **One operation per `Bash` call.** Shell pipes (`|`), command chains
  (`&&`, `;`), command substitution (`$(...)`, backticks), and process
  substitution each count as separate operations. Each sub-command must
  *individually* match the allowlist, or the whole call is rejected with
  `This Bash command contains multiple operations. The following part
  requires approval: ...`. If you need to post-process output, pipe it
  through a single `python3 -c '...'` instead, or split into sequential
  calls.
- **Do not redirect output outside the working directory.** Writing to
  `/tmp/*` or any absolute path outside
  `/home/runner/work/<repo>/<repo>` is blocked with `Output redirection
  to '...' was blocked`. Use `Write` for files in the repo; for scratch
  data, use a path under the working directory (e.g. `./.scratch/…`) and
  clean up afterward.
- **`2>&1` counts as redirection.** Omit it; tool results already include
  stderr.
- **`gh` arguments must be literal values, not URL paths.** `gh pr view
  owner/repo/pull/7` is read as a branch name and fails with
  `no pull requests found for branch "owner/repo/pull/7"`. Pass the PR
  number alone (`gh pr view 7`) and use `--repo owner/repo` if you need
  a non-default target.
- **Never issue parallel `gh` Bash calls.** When multiple `gh pr *` or
  `gh api` calls are dispatched in the same assistant turn, the first
  failure cancels all siblings — every queued call is wasted. Use
  `scripts/collect-pr-review-context.py` for PR context, or issue `gh`
  calls one at a time, sequentially.
- **Workflow files are effectively read-only.** The GitHub App token this
  agent runs under does not carry the `workflows` permission, so pushes
  that touch `.github/workflows/**` are rejected at the remote. If a fix
  needs a workflow change, surface it as a recommendation with a diff
  rather than editing the file.
