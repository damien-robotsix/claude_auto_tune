# Migrate GitHub Actions to Node.js 24 before 2026-06-02

**Category:** `reliability` — **Priority:** high
**Evidence:** Deprecation warning appeared in 4 parsed workflow logs
(23990303471, 23990283750, 23990241024, 23990361966). GitHub will force
`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` on 2026-06-02, ~8 weeks from today.

## Affected actions across workflows

`grep -l` hits all three workflows in `.github/workflows/`:

- `auto-improve.yml`
- `claude-code-review.yml`
- `claude.yml`

Problematic pins:
- `actions/checkout@v4`           → should become `actions/checkout@v5`
- `actions/upload-artifact@v4`    → should become `actions/upload-artifact@v5`
- `oven-sh/setup-bun@v1` (or similar) — check for Node 24 compatible tag

## Plan

1. Update all three workflow files to use `@v5` of the official `actions/*`.
2. For `oven-sh/setup-bun`, pin to the latest release confirmed to ship a
   Node.js 24 runtime (or temporarily set
   `env: FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` at job level as a bridge).
3. Trigger each workflow once after the bump to confirm green runs before the
   2026-06-02 deadline.

## Why bundled

All three workflows share the identical set of actions. A single PR touching
all three avoids the churn of three separate migration PRs and lets CI prove
the new pins all at once.
