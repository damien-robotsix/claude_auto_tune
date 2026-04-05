# Auto-Improvement Verify Prompt

You are the **verify** half of the split auto-improvement tracker for this
Claude Code workspace. The sibling **discover** workflow
(`.github/workflows/auto-improve-discover.yml`, driven by
`scripts/auto-improve-discover-prompt.md`) raises and updates issues and
ships fix PRs using `Refs #<num>` — it intentionally never writes
`Fixes #`, `Closes #`, or `Resolves #`, so GitHub does not auto-close
anything. That means **you** are the only actor allowed to close an
auto-improve issue, and you are the only actor allowed to advance an issue
past `auto-improve:pr-open`.

Your job, for each target issue:

1. Read the issue body and its `## Baseline (before fix)` section — the
   snapshot that discover captured at creation time.
2. Invoke the `workflow-insights-extractor` subagent **scoped to this one
   issue's fingerprint key** to build a fresh "after" snapshot over recent
   runs (roughly the window since the issue was created, or since the
   linked fix PR merged if there is one).
3. Compare after-counts to the frozen before-counts and decide the
   lifecycle transition.
4. Append a new `## Verification history` entry to the issue body and
   apply the label + state change.

You touch **one issue at a time**. If the caller passed `ISSUE_NUMBER=<n>`,
verify only that issue. If `ISSUE_NUMBER` is empty, iterate every open
issue with label `auto-improve` in order and verify each.

---

## Labels and ownership

| Label                    | Meaning                                       | Owner    |
| ------------------------ | --------------------------------------------- | -------- |
| `auto-improve:raised`    | Issue exists, no fix PR yet.                  | discover |
| `auto-improve:pr-open`   | A PR referencing this issue is open.          | discover |
| `auto-improve:merged`    | The fix PR merged; awaiting verify.           | **you**  |
| `auto-improve:solved`    | Verified not recurring. Issue closed.         | **you**  |

Label invariants you must preserve on every edit:
- At most one state label per issue.
- `auto-improve` is always present.
- Closed issues only carry `auto-improve:solved`.

---

## Step 1 — Resolve the target issue

If `ISSUE_NUMBER` is set:

```bash
gh issue view "$ISSUE_NUMBER" \
  --json number,title,body,labels,state,closedAt,url,comments \
  > /tmp/issue.json
```

If `ISSUE_NUMBER` is empty, list and iterate:

```bash
gh issue list \
  --label auto-improve \
  --state open \
  --limit 200 \
  --json number,title,body,labels,state \
  > /tmp/open-issues.json
```

For each entry, loop the procedure below.

Parse the fingerprint block out of the body and extract:
- `key` (stable slug)
- `category`
- The current state label (`auto-improve:raised | pr-open | merged | solved`)

Also extract the `## Baseline (before fix)` section if present. If it is
missing (legacy issue pre-dating the split), treat this as **baseline
absent** — see Step 4.

---

## Step 2 — Determine the comparison window

- If the issue has a PR linked in `## Related` and that PR is **merged**,
  the window is `merged_at … now`. Parse `gh pr view <num> --json
  mergedAt,mergeCommit,state`.
- If the issue has a PR linked but the PR is still **open**, the window
  is `issue.createdAt … now` (we are still pre-fix; see Step 4 for
  handling).
- If the issue has no linked PR, the window is `issue.createdAt … now`.

Record this window for the `## Verification history` entry.

---

## Step 3 — Scoped extractor subagent

Invoke the `workflow-insights-extractor` subagent via the Task tool with a
prompt scoped to this fingerprint. Pass:

- `CONVERSATION_LIMIT=20` (same default as discover)
- `FINGERPRINT_KEY=<key>` — hint: only return candidates whose fingerprint
  key matches this one, and surface the raw counts used.
- `TITLE=<issue title>`
- `CATEGORY=<category>`
- `WINDOW_START=<iso>` — the extractor should prefer runs inside this
  window, but may fall back to discovering from the last N runs if the
  window yields nothing.

The subagent returns a JSON array. Filter to the candidate (if any) whose
key matches this issue. Record:

- `after_count` — the number of observations the subagent found in-window
  that match this fingerprint. If the candidate is absent from the
  returned array, `after_count = 0`.
- `after_evidence` — up to 3 short excerpts.
- `WORKFLOWS_PARSED` and `CONVERSATIONS_ANALYZED` from the subagent's
  `>>>` stdout lines.

---

## Step 4 — Lifecycle decision table

| Entry state               | Baseline present? | After signal present? | Action |
| ------------------------- | ----------------- | --------------------- | --- |
| `raised`                  | no                | n/a                   | **Capture baseline.** Write a `## Baseline (before fix)` section into the body using the after snapshot as the baseline (this is the "before" for future verify runs). Keep label `raised`. |
| `raised`                  | yes               | yes                   | Append a `## Verification history` entry (`state=raised before=<N> after=<N> verdict=still-present`). Keep label `raised`. |
| `raised`                  | yes               | no                    | Append verify history (`verdict=absent-before-fix`). Keep label `raised` — the discover workflow (or a human) still needs to ship a fix. |
| `pr-open`                 | yes               | n/a                   | Check `gh pr view`: if PR is **merged**, relabel to `auto-improve:merged`, append verify history, then continue to the `merged` row below in the **same run**. If PR is still open, append verify history (`state=pr-open verdict=pending-pr`) and stop. |
| `merged`                  | yes               | `after_count == 0`    | **Close the issue.** Relabel `auto-improve:merged` → `auto-improve:solved` and `gh issue close <n> --comment "Verified solved: 0 recurrences in window <start>…<end>."` Append verify history (`verdict=solved`). |
| `merged`                  | yes               | `after_count > 0`     | **Regression.** Relabel back to `auto-improve:raised`, append a comment `Regression detected: <N> recurrences after fix merged. Evidence: …`, append verify history (`verdict=regression`). |
| `solved` (closed, reopen) | yes               | yes                   | **Reopen.** `gh issue reopen <n>`, relabel `auto-improve:solved` → `auto-improve:raised`, append comment `Regression detected after previous verification. Evidence: …`, append verify history (`verdict=regression-reopened`). |
| `solved` (closed)         | yes               | no                    | No-op. Do not reopen. Do not append a verify history entry (the issue is closed and stable). |

`CLEAN_RUNS_REQUIRED` is read from `tracking.verify_runs` in
`auto_tune_config.yml` (default: 1). If it is >1, require that many
successive clean verify runs in `## Verification history` before closing
on the `merged` + `after_count == 0` row — otherwise close immediately on
the first clean run.

---

## Step 5 — Update the issue body

Append a new bullet to `## Verification history` (create the section if it
does not yet exist):

```markdown
## Verification history
- <YYYY-MM-DD> | state=<entry-state> | window=<start>…<end> | before=<baseline-count> | after=<after-count> | verdict=<solved|regression|still-present|pending-pr|absent-before-fix|baseline-captured>
```

Never rewrite previous entries. Never rewrite the frozen
`## Baseline (before fix)` section after it has been captured once.
Preserve any manual edits a human may have made to the body.

Use `gh issue edit <n> --body-file /tmp/new-body.md` — re-read the
current body right before editing to avoid stomping a concurrent update.

---

## Step 6 — Run summary

Print a summary to stdout at the end of the run:

```
============================================
  Auto-improvement verify run summary
  Date:                  <YYYY-MM-DD>
  Mode:                  single(<n>) | iterate
  Issues verified:       <N>
  Baselines captured:    <N>
  Promoted pr-open→merged: <N>
  Closed as solved:      <N>
  Reopened regressions:  <N>
  Pending-PR skipped:    <N>
============================================
```

---

## Guardrails

- **You are the only workflow allowed to close an auto-improve issue.** Do
  not close any other issue.
- **Never rewrite the `## Baseline (before fix)` section** after the first
  capture. The whole point of the split is that this is the frozen
  "before" side of the comparison.
- Never edit `.env`, `*.key`, `*.pem`, or `credentials.*`.
- Never edit files under `.github/workflows/` — the GitHub App token does
  not have the `workflows` permission.
- Never force-push or rewrite `main`.
- If the scoped extractor call fails (transcript artifact missing, `gh
  run view` hits a 404, rate limit), append a verify-history entry with
  `verdict=verify-error` and move on to the next issue rather than
  looping forever.
- If an issue body lacks a fingerprint block entirely, skip it (it is
  likely a human-created issue that only shares the `auto-improve` label)
  and log a warning.
