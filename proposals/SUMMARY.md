# Auto-improvement run summary — 2026-04-05

## Pipeline counts

- **Workflows parsed:** 20
- **Conversations analyzed:** 6

The other 14 workflow runs had no `claude-transcript` artifact — they
were `skipped`, had expired logs (failed conclusion with no body), or
were the currently-running `Auto-Improvement Agent` run itself.

## Insights aggregated by category

(Counts are raw insight counts from the two parsers; a single
proposal can cover multiple related insights.)

| Category              | Workflow-log insights | Transcript insights |
|-----------------------|-----------------------|---------------------|
| reliability           | 12                    | 5                   |
| cost_reduction        | 8                     | 6                   |
| new_workflow          | 7                     | 6                   |
| deterministic_script  | 7                     | 6                   |
| capability_gap        | 0                     | 4                   |

## Proposals in this PR

| # | Proposal                                                                                   | Category                         | Evidence strength |
|---|--------------------------------------------------------------------------------------------|----------------------------------|-------------------|
| 1 | [Downgrade code review to Haiku](./cost-reduction.md#1)                                    | cost_reduction                   | **very high** — 6 cross-run high-priority insights with per-run cost numbers |
| 2 | [Fix parser auth under claude-code-action](./scripts/parser-auth-fallback.md)              | reliability                      | **very high** — observed in THIS run + prior run |
| 3 | [`review-pr` skill: fetch PR context once, reduce fan-out](./skills/review-pr-shared-context.md) | deterministic_script + cost | **high** — ~107 redundant `gh` calls across 6 transcripts |
| 4 | [Skip code-review on workflow-file PRs](./workflows/claude-code-review-skip-workflow-changes.md) | reliability                 | high — 1 failure run + 2 Haiku insights |
| 5 | [Investigate 19–29 permission denials per review](./scripts/investigate-permission-denials.md) | reliability + cost_reduction  | high — 3 runs, all high priority |
| 6 | [Track Node 20 → 24 deprecation (no code change yet)](./workflows/node24-deprecation.md)    | reliability                      | medium — 1 high-priority warning |
| 7 | [CLAUDE.md: read from checkout, not `gh api contents`](./claude-md-update.md)              | deterministic_script / convention | high — 10 redundant `gh api contents` calls |

Proposals that only had a single weak signal (cache bun modules, extract
git-config into a composite action, pre-compute `yq` model alias at
build time, etc.) were **not** promoted to files in this PR — they
didn't meet the "2+ instances or 1 high-confidence" bar set in
`scripts/auto-improve-prompt.md`.
