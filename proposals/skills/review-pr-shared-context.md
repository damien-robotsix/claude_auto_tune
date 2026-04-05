# Proposal: `review-pr` skill that fetches PR context **once** and shares it

**Category:** deterministic_script + cost_reduction
**Evidence source:** Claude Code session transcripts for runs
`23990283750`, `23990303471`, `23990306838`, `23990363053`, `23990412021`,
`23990519154`.

## Observed pattern

The `code-review` plugin invoked by `.github/workflows/claude-code-review.yml`
fans out 4–6 `general-purpose` sub-agents per PR (eligibility check,
CLAUDE.md-file listing, PR summarization, CLAUDE.md compliance review,
independent second review, bug scan, independent second bug scan). Each
sub-agent then re-fetches the same PR diff from scratch with `gh pr
diff`, often trying several flag variants before finding one that works.

Aggregated `Bash` tool-use counts across the 6 parsed transcripts:

| Command signature                                      | Invocations |
|--------------------------------------------------------|-------------|
| `gh pr diff damien-robotsix/claude_auto_tune/pull/9`   | 11          |
| `gh pr diff 9 --repo damien-robotsix/claude_auto_tune` | 8           |
| `gh pr diff 10 --repo damien-robotsix/claude_auto_tune`| 5           |
| `gh pr diff damien-robotsix/claude_auto_tune#10`       | 4           |
| `gh pr diff 7 --repo damien-robotsix/claude_auto_tune` | 3           |
| `gh api .../contents/scripts/parse-workflow-log.py`    | 10          |

Overall, **107 of 157 Bash calls** across 6 runs were `gh` invocations,
and the overwhelming majority were redundant fetches of the **same**
diff or file for the **same** PR. `Read` was used only 14 times even
though the PR working copy is already checked out at `$GITHUB_WORKSPACE`.

**Cross-source corroboration:** the Haiku transcript parser
independently flagged this in multiple runs as _"Reduce Agent
delegation frequency — 7 Agent calls with 4 consecutive calls suggest
unnecessary delegation"_ and _"Long bash command chains should be
consolidated into shell scripts — Bash was called 47 times (62% of
all tool calls) with sequences of 5–13 consecutive bash calls."_

## Proposed skill: `review-pr`

Create `proposals/skills/review-pr.md` (final location:
`~/.claude/skills/review-pr/SKILL.md`). The skill description should
trigger on "review PR" / "code review" prompts and enforce:

1. **Fetch diff and metadata exactly once**, into
   `/tmp/pr-context/<pr-number>/`:
   - `diff.patch` — `gh pr diff <N> --repo <repo>`
   - `meta.json` — `gh pr view <N> --repo <repo> --json
     title,body,files,baseRefName,headRefName`
2. **Pass the cached paths** (not the PR number) to every sub-agent.
   Sub-agents must `Read` from the cache, never re-invoke `gh`.
3. **Read modified files from the checkout**, not from
   `gh api repos/.../contents/…`. The working copy is already at
   `$GITHUB_WORKSPACE`; the `gh api contents` endpoint is slower, rate
   limited, and returns base64 that has to be decoded.
4. **Limit sub-agent fan-out** to what is actually independent. Two
   "independent second review" / "second bug scan" agents per PR
   duplicate context without producing materially different feedback —
   collapse to one review agent + one bug-scan agent unless the PR is
   over a size threshold (e.g. >500 changed lines).

## Expected savings

On the 6 transcripts parsed, this would eliminate roughly **80 of ~107
`gh` invocations** and shave one full Haiku/Sonnet round-trip per
duplicated sub-agent — call it 30–50 % of the end-to-end review cost.
