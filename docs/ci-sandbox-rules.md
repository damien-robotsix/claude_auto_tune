# CI sandbox — Bash command rules

When running inside `anthropics/claude-code-action@v1` (the claude.yml,
claude-code-review.yml, auto-improve-discover.yml, and auto-improve-verify.yml workflows), Bash tool calls are
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
- **Workflow files are effectively read-only.** The GitHub App token this
  agent runs under does not carry the `workflows` permission, so pushes
  that touch `.github/workflows/**` are rejected at the remote. If a fix
  needs a workflow change, surface it as a recommendation with a diff
  rather than editing the file.
