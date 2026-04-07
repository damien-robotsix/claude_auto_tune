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

## Avoiding tool-call errors

Every failed tool call wastes a round-trip and tokens. Follow these rules to
keep the error rate low:

### Prefer dedicated tools over Bash
- **Read files** → use `Read`, not `cat` / `head` / `tail` / `sed`
- **Search file contents** → use `Grep`, not `grep` / `rg`
- **Find files by name** → use `Glob`, not `find` / `ls`
- **Edit files** → use `Edit`, not `sed` / `awk`
- **Create files** → use `Write`, not `echo` / `cat <<EOF`
- Reserve `Bash` for commands that genuinely require shell execution (git, gh, python3, npm, etc.)

### Guard against Edit / Write failures
- **Always `Read` before `Edit` or `Write`** — the tools reject calls on unread files
- **Verify the file exists** before editing — use `Glob` or `Read` first if you are unsure about the path
- **Ensure `old_string` is unique** in the file — if it isn't, include more surrounding context or use `replace_all`

### Guard against Bash failures
- **Check that commands and paths exist** before running them — a quick `which <cmd>` or `ls <dir>` avoids "command not found" / "No such file" errors
- **Do not assume tools are installed** — the Docker image and CI runner have a fixed set of packages; if unsure, verify first
- **Avoid complex shell pipelines** when a single Python one-liner (`python3 -c '...'`) is clearer and less error-prone

## Gathering GitHub context efficiently

These rules apply to **all agents** (review, hub-daily-sweep, hub-local,
auto-improve, general), not just code review sessions.

- **Hard limit: never make more than 4 consecutive Bash calls.** After
  every 3–4 Bash calls, interleave a non-Bash tool (Read, Write, Grep,
  Glob) — even if just to inspect the output of the previous call. If
  you are about to issue a 5th consecutive Bash call, stop and
  restructure: batch the remaining work into a single `python3 -c`
  script, or use a deterministic script from `scripts/` or
  `scripts/hub/`.
- **For PR context** (metadata, diff, linked issues, comments, check-run
  status), use `python3 scripts/collect-pr-review-context.py <pr-number>`
  instead of issuing multiple `gh api` / `gh pr view` / `gh pr diff` Bash
  calls. It returns everything in a single JSON bundle.
- **For hub operations**, use the scripts under `scripts/hub/*.py`
  (`list-recent-commits.py`, `hub-search.py`, `hub-open-proposal.py`,
  etc.) instead of ad-hoc `gh api` / `gh issue` calls. These scripts
  exist specifically to avoid long Bash chains.
- **Never issue parallel `gh` Bash calls.** When multiple `gh pr *` or
  `gh api` calls are dispatched in one assistant turn, the first failure
  cancels all siblings — wasting every queued call. If you must use `gh`
  directly, issue calls one at a time, sequentially.
- **Avoid long consecutive `gh` Bash chains.** If you find yourself making
  5+ sequential `gh` calls (e.g., polling `gh run view`, looping over
  `gh issue view`, or calling `gh api` repeatedly), stop and consider:
  - Can `scripts/collect-pr-review-context.py` provide this in one call?
  - Can a `scripts/hub/*.py` script handle this operation?
  - Can a single `gh api` call with GraphQL replace multiple REST calls?
  - Can a `python3 -c` script batch the work into one process?
- **Do NOT spawn `Agent` subagents for simple lookups.** Use `Read`, `Grep`,
  or `Glob` directly — they are faster and cheaper. Each `Agent` subagent
  adds ~5k tokens of overhead. Specifically:
  - To read a file or check its contents → `Read`
  - To find files by name/pattern → `Glob`
  - To search code for a string or regex → `Grep`
  - To check a function signature or class definition → `Grep` or `Read`
  - **Only** use `Agent` when the task genuinely requires multi-step
    exploration across many files where you cannot predict the search path
    in advance (e.g., tracing a complex call chain through 5+ files). A
    sequence of 2+ consecutive `Agent` calls is almost always wrong — use
    direct tools instead.

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
- The auto-improve system is split in two: `auto-improve-discover.yml` raises/updates tracked issues and ships fix PRs using `Refs #<num>` (never `Fixes #`/`Closes #`/`Resolves #`), and `auto-improve-verify.yml` owns all per-issue before/after comparison and is the only workflow allowed to close an `auto-improve` issue.
- The `Read` tool caps file content at 10k tokens and rejects unbounded calls on larger files with `File content (N tokens) exceeds maximum allowed tokens (10000). Use offset and limit parameters...`. For files you expect to be large (workflow logs, JSON bundles from `scripts/collect-pr-review-context.py`, long markdown prompts under `scripts/`, parser output, transcripts), do one of: (a) `Grep` first and then `Read` with a targeted `offset`/`limit` window, (b) start with `Read(..., limit=200)` and paginate only as needed, or (c) pipe the file through a `python3 -c` filter via `Bash`. Do not issue an unbounded `Read` on a file whose size you have not checked.

# CI sandbox — Bash command rules

When running inside `anthropics/claude-code-action@v1` (the
claude-agent.yml, claude-code-review.yml, auto-improve-discover.yml,
auto-improve-verify.yml, hub-daily-sweep.yml, hub-sync.yml, and hub-adopt.yml workflows), Bash tool calls are
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
- **Limit consecutive Bash calls to 4.** After 3–4 Bash calls,
  interleave a non-Bash tool (Read, Write, Grep, Glob). If you need
  more Bash calls, batch them into a single `python3 -c` script or use
  a deterministic script from `scripts/` or `scripts/hub/`.
- **Workflow files are effectively read-only.** The GitHub App token this
  agent runs under does not carry the `workflows` permission, so pushes
  that touch `.github/workflows/**` are rejected at the remote. If a fix
  needs a workflow change, surface it as a recommendation with a diff
  rather than editing the file.
- **`.claude/agents/` is writable.** Agent definition files under
  `.claude/agents/` are regular repo files — you may read, edit, and
  commit changes to them like any other source file. Do not self-restrict
  writes to this directory.

## Common CI sandbox mistakes (avoid these)

These patterns cause the majority of Bash/Edit errors in CI runs:

| Mistake | Example | Fix |
|---------|---------|-----|
| Pipe through unapproved command | `gh pr view 5 \| jq .title` | Split into two calls or use `python3 -c` |
| Redirect stderr | `git status 2>&1` | Omit `2>&1` — stderr is captured automatically |
| Write to `/tmp` | `echo x > /tmp/foo` | Use `./.scratch/foo` or `Write` tool |
| Edit unread file | `Edit(file="new.md", ...)` | `Read("new.md")` first |
| `cat` / `head` / `grep` via Bash | `cat README.md` | Use the `Read` / `Grep` dedicated tools |
| Chain commands with `&&` | `mkdir -p dir && echo done` | Use two separate Bash calls or a single `python3 -c` |
| 5+ consecutive Bash calls | `gh api ...` x20 in a row | Interleave Read/Write/Grep, or batch into `python3 -c` |
