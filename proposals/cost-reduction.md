# Cost-reduction notes — 2026-04-05

## 1. Downgrade `claude-code-review.yml` from Opus/Sonnet to Haiku

**Category:** cost_reduction
**Confidence:** very high — **6 separate high-priority insights** across
the parsed workflow logs recommended exactly this, with concrete per-run
cost and turn counts.

**Evidence from parsed runs:**

| Run         | Model used         | Turns | Wall time | Cost (from log) |
|-------------|--------------------|-------|-----------|-----------------|
| 23990519154 | claude-opus-4-6    | 13    | ~2.5 min  | $0.85           |
| 23990306838 | claude-opus-4-6    | 12    | ~4 min    | $2.82           |
| 23990303471 | claude-sonnet-4-6  | 14    | 162 s     | $0.387          |
| 23990363053 | claude-sonnet-4-6  | 9     | ~2 min    | $0.73           |

Across all four runs the task is the same: **read a PR diff, check
against CLAUDE.md, post comments**. The Haiku parser flagged this as
"deterministic, well-scoped, read-heavy, suitable for Haiku" in every
single workflow log it analyzed.

**Proposed change:** set the default `code_review` model in
`auto_tune_config.yml` to `haiku`. The workflow already resolves the
model through `yq` and the alias map, so this is a one-line config
change:

```yaml
# auto_tune_config.yml
models:
  log_parser: haiku
  code_review: haiku   # was: opus / sonnet
```

Keep `opus` reachable via the alias map so individual PRs can still
opt-in to a deeper review by overriding the workflow input.

**Expected savings:** Haiku is roughly 1/12 the input-token price of
Opus and 1/5 of Sonnet. On the observed mix, that is the difference
between ~$3/review and ~$0.25/review.

## 2. Prefer `Read` on the checkout over `gh api repos/.../contents/...`

**Category:** cost_reduction + deterministic_script
**Evidence:** 10 of the 17 `gh api` calls across the 6 parsed Claude
Code session transcripts fetched the file
`repos/damien-robotsix/claude_auto_tune/contents/scripts/parse-workflow-log.py`
— a file already present in the checkout. The Haiku parser for two of
the transcripts independently flagged the same "Read-Bash" alternation
pattern, recommending consolidation.

**Recommendation:** add the convention to `CLAUDE.md` — see
`proposals/claude-md-update.md`.

## 3. Collapse duplicated "second review" sub-agents

**Category:** cost_reduction + deterministic_script
**Evidence:** `general-purpose` Agents were launched 31 times across 6
runs. Sub-agent prompts show clear **"Review X"** / **"Independent
second review of X"** pairs for both CLAUDE.md compliance and bug
scanning, plus in one run "7 consecutive Agent calls near session
end." The Haiku parser flagged this in three separate transcripts as
"reduce Agent delegation frequency" / "evaluate whether delegations
represent legitimate parallel work."

**Recommendation:** keep a single reviewer per pass unless the diff
exceeds a size threshold (e.g. >500 changed lines or >10 files). See
`proposals/skills/review-pr-shared-context.md` for the full skill
proposal that bundles this with the shared-context optimization.

## 4. Log parser model is already correct — no change

`auto_tune_config.yml` already routes the `log_parser` alias to
`haiku`, and the parser truncates each log to 40 000 characters. The
Haiku parser's own analysis of the auto-improve run flagged no cheaper
alternative for this step. No change recommended.
