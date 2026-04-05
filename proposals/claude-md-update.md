# Proposal: add a "read from checkout, not from the API" rule to CLAUDE.md

**Category:** deterministic_script / cost_reduction
**Evidence:** see `proposals/cost-reduction.md` — 10 of 17 `gh api`
calls across the last 6 Claude Code sessions fetched a file that was
already in the working copy.

## Suggested addition to `CLAUDE.md` (under **Key conventions**)

```markdown
- When a file is already in the current checkout, read it with the `Read`
  tool. Do not refetch it via `gh api repos/<owner>/<repo>/contents/...`
  — that endpoint is slower, returns base64 that must be decoded, and
  counts against the REST rate limit.
```

This is a one-line convention; no tooling change is required.
