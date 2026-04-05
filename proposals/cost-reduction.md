# Cost reduction: switch PR code review to Haiku

**Category:** `cost_reduction` — **Priority:** high
**Evidence:** Observed across 4 of the 20 analysed runs (runs 23990303471,
23990283750, 23990241024, plus insight in 23990361966).

## Observations

| Run ID      | Task         | Model               | Turns | Duration | Cost   |
|-------------|--------------|---------------------|-------|----------|--------|
| 23990303471 | Code review  | claude-sonnet-4-6   | 14    | 162.5 s  | $0.39  |
| 23990283750 | Code review  | claude-sonnet-4-6   | 9     | 162 s    | $0.73  |
| 23990241024 | Code review  | claude-sonnet-4-6   | 5     | 33 s     | $0.094 |

Code review over a bounded PR diff is a well-scoped, non-speculative task that
rarely requires deep reasoning. Three independent Haiku-generated insights
flagged this exact cluster as a Sonnet → Haiku swap candidate.

## Recommendation

1. Update `.github/workflows/claude-code-review.yml` to pass
   `claude_args: --model claude-haiku-4-5-20251001` for the code-review step.
2. Keep Sonnet / Opus reserved for the `claude.yml` interactive workflow where
   reasoning depth matters.
3. Add a rollback plan: re-enable Sonnet on the specific repo if review quality
   drops (track via review-acceptance rate over the next ~20 PRs).

Expected savings: ~70–80% on the per-review cost line, based on the current
sample. At $0.40 average × ~40 reviews/month, that is ~$12 → ~$3 per month on
this repo alone, and scales linearly with PR volume if rolled out to other
repositories.

## Risk

Haiku may miss subtle logic bugs that Sonnet catches. Mitigate by keeping a
nightly Sonnet-powered deep-review on `main` (separate scheduled workflow) and
letting Haiku handle the fast PR-gate review.
