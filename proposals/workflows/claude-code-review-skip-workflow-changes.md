# Proposal: skip `Claude Code Review` on PRs that only touch workflow files

**Category:** reliability
**Evidence:** run `23990312075` (PR "feat: add auto_tune_config.yml with
model alias support") failed with:

```
App token exchange failed: 401 Unauthorized - Workflow validation failed.
The workflow file must exist and have identical content to the version on
the repository's default branch. [...] this is normal and you should
ignore this error.
```

GitHub deliberately blocks app-token exchange on PRs that modify
`.github/workflows/**` until the workflow is merged to `main`. The error
message itself says to ignore it, but the failure still turns the PR red
and wastes a run.

## Proposed change

Add a `paths-ignore` filter to the `pull_request` trigger in
`.github/workflows/claude-code-review.yml`, so the review is simply
skipped when the PR only touches workflow files:

```yaml
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]
    paths-ignore:
      - '.github/workflows/**'
```

If a workflow-touching PR also changes code that should be reviewed,
contributors can still request a review manually via `@claude` in a
comment, which runs through `claude.yml` and is not affected by the
token-exchange issue.

## Alternative (if review of workflow changes is desired)

Add a `continue-on-error: true` on the `Run Claude Code Review` step and
a preceding guard job that detects the token-exchange failure and exits 0
with an explanatory annotation — but this is strictly more complex and
the `paths-ignore` approach is what GitHub itself recommends.
