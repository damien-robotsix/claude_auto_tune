# Proposal: investigate the 19–29 permission denials per code-review run

**Category:** reliability + cost_reduction
**Confidence:** high — three separate workflow logs surfaced the same
number in their structured result, and all three were flagged
high-priority by the Haiku parser.

## Evidence

| Run         | `permission_denials_count` | Model             |
|-------------|----------------------------|-------------------|
| 23990306838 | 29                         | claude-opus-4-6   |
| 23990519154 | 19                         | claude-opus-4-6   |
| 23990303471 | 19 (≈)                     | claude-sonnet-4-6 |

Each denial is a Claude tool call that the harness refused — the model
spent tokens planning and then the action didn't go through. The
current `claude_args` in `.github/workflows/claude.yml` only allows a
restricted set of `Bash(...)` patterns (`gh api:*`, `gh run:*`,
`git *`, `pip install*`, `python3 *`, `mkdir *`, `cat *`, `echo *`,
`unzip *`, `wc *`, `ls *`, `head *`, `find *`, `rm *`), plus
`Read, Write, Edit, Glob`. Denials likely come from the code-review
plugin trying things like `gh pr diff`, `gh pr view`, `sed`, `awk`,
etc. that are not in that list.

## Proposed change — debug step, not a blanket allowlist expansion

Add a post-run step that extracts the denied tool-call names from the
transcript and surfaces them as a step summary, so the next review
cycle can decide exactly which patterns to allow. Something like:

```yaml
- name: Summarize permission denials
  if: always()
  run: |
    python3 scripts/summarize-permission-denials.py \
      ~/.claude/projects/**/*.jsonl \
      >> "$GITHUB_STEP_SUMMARY"
```

A thin helper script (to land under `scripts/` once the pattern is
agreed) would walk the transcript JSONL looking for
`permission_denied` events and group them by tool name + input
prefix. That turns a number into a list of concrete allowlist
candidates, which is what's missing today — one of the Haiku
insights explicitly noted: _"execution summary shows 19 permission
denials but provides no detail about which operations failed."_

**Do not** blanket-expand `allowed_tools`: the denials might be
evidence that the code-review plugin is attempting work it shouldn't
need to do (see `proposals/skills/review-pr-shared-context.md`
— e.g. re-fetching the diff via `gh` when it's already on disk).
Fixing the redundancy is a better outcome than papering over it.
