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

Runs on the cron schedule defined in `auto_improve.schedule` (and can be dispatched manually). It inspects recent runs, parses logs via the scripts in `scripts/`, and proposes improvements to prompts, configuration, or tooling.

The goal is to let the workspace grow incrementally: when a pattern of failure or friction repeats, the loop captures the lesson rather than repeating the mistake.

## Scripts

Supporting scripts live in [`scripts/`](https://github.com/damien-robotsix/claude_auto_tune/tree/main/scripts):

- `auto-improve-prompt.md` — the prompt used by the auto-improve workflow.
- `parse-claude-transcript.py` — parses Claude transcripts into a compact summary.
- `parse-workflow-log.py` — parses raw workflow logs into a compact summary.

Both parsing scripts honour the `log_parser` limits from `auto_tune_config.yml`.
