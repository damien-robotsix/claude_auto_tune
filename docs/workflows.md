---
title: Workflows
layout: default
---

# Workflows

The repo ships three GitHub Actions workflows under `.github/workflows/`. All of them read model assignments from [`auto_tune_config.yml`](configuration.md).

## `claude.yml` — interactive agent

Triggered when `@claude` is mentioned in an issue or PR comment, or when an issue is assigned/labelled accordingly. Runs the `anthropics/claude-code-action@v1` action with the model configured as `models.claude_code`.

Use it to ask Claude to answer questions, review changes, or implement small-to-medium tasks directly from GitHub.

## `claude-code-review.yml` — automated review

Runs on pull requests and asks Claude (using `models.code_review`) to review the diff. The review focuses on correctness, readability, and security, as laid out in [`CLAUDE.md`](https://github.com/damien-robotsix/claude_auto_tune/blob/main/CLAUDE.md).

## `auto-improve.yml` — self-tuning loop

Runs on the cron schedule defined in `auto_improve.schedule` (and can be dispatched manually). It inspects recent workflow runs and Claude Code session transcripts, parses them via the scripts in `scripts/`, and maintains a long-term **issue tracker** for each improvement subject.

Every recurring problem becomes one persistent GitHub issue carrying the `auto-improve` label and a lifecycle label that moves through `auto-improve:raised` → `auto-improve:pr-open` → `auto-improve:merged` → `auto-improve:solved`. When the tracker can fix a problem automatically, it opens a focused PR linking back to the issue via `Fixes #<num>`; otherwise the issue stays in `raised` for human follow-up. Fixes are only closed as `solved` after `tracking.verify_runs` successive clean runs (see [Configuration](configuration.md#issue-tracking)).

Session transcripts analyzed per run are capped by `auto_improve.default_conversation_limit`; workflow logs are always parsed in full.

The goal is to let the workspace grow incrementally: when a pattern of failure or friction repeats, the loop captures the lesson rather than repeating the mistake.

## Docs-sync agent

A daily docs-sync agent keeps pages under `docs/` aligned with what landed on `main` in the last 24 hours. It is deliberately narrow: it only edits `docs/`, never proposes code changes, and uses [`docs/.docsrules`](https://github.com/damien-robotsix/claude_auto_tune/blob/main/docs/.docsrules) to route changed source files to the doc page most likely to need updating. Its full instructions live in [`scripts/docs-sync-prompt.md`](https://github.com/damien-robotsix/claude_auto_tune/blob/main/scripts/docs-sync-prompt.md).

## Scripts

Supporting scripts live in [`scripts/`](https://github.com/damien-robotsix/claude_auto_tune/tree/main/scripts):

- `auto-improve-prompt.md` — the prompt used by the auto-improve tracker.
- `docs-sync-prompt.md` — the prompt used by the daily docs-sync agent.
- `collect-doc-relevant-diff.sh` — emits the commit list and unified diff the docs-sync agent consumes from `.scratch/`.
- `parse-claude-transcript.py` — **deterministic** aggregator over Claude Code session JSONL files. Emits tool-call counts, error tools, repeated consecutive runs, token usage, and a sequence preview. No LLM calls.
- `parse-workflow-log.py` — **deterministic** regex-based signal extractor over raw GitHub Actions logs. Emits counts and samples for errors, tool denials, workflow-permission rejections, HTTP errors, non-zero exits, retries, timeouts, and rate limits. No LLM calls.
- All LLM-side reasoning over the output of these two scripts is handled by the `workflow-insights-extractor` subagent at [`.claude/agents/workflow-insights-extractor.md`](https://github.com/damien-robotsix/claude_auto_tune/blob/main/.claude/agents/workflow-insights-extractor.md), which the auto-improve tracker invokes via the Task tool.
