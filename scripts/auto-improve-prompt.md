# Auto-Improvement Agent Prompt

You are the auto-improvement agent for this Claude Code workspace. Your goal is
to analyze recent workflow runs, identify patterns and inefficiencies, and create
a PR with concrete improvement proposals.

## Step 1 — Fetch the last 20 workflow run IDs

```bash
gh api repos/$GITHUB_REPOSITORY/actions/runs \
  --paginate \
  --jq '.workflow_runs[:20] | .[] | {id: .id, name: .name, created_at: .created_at, conclusion: .conclusion}' \
  | head -20
```

Collect all run IDs into a list.

## Step 2 — Parse each run log with Haiku

For each run ID, fetch its logs and pipe through the Haiku parser:

```bash
pip install -q anthropic
for RUN_ID in $RUN_IDS; do
  echo "=== Parsing run $RUN_ID ==="
  gh run view "$RUN_ID" --log 2>/dev/null \
    | python3 scripts/parse-workflow-log.py \
    >> /tmp/all-insights.jsonl || echo '{"summary":"fetch failed","insights":[]}' >> /tmp/all-insights.jsonl
done
```

Each line in `/tmp/all-insights.jsonl` is the JSON output for one run.

## Step 3 — Synthesize insights

Read all insights and group them by category. For each category with 2+ similar
insights, it represents a real pattern worth addressing.

Categories:
- `new_workflow` — tasks that should be automated as a scheduled GitHub Actions workflow
- `deterministic_script` — tasks Claude repeated identically; a shell/Python script would be faster and cheaper
- `subagent_skill` — reusable capabilities that should become a Claude Code skill or subagent prompt
- `cost_reduction` — places where Haiku or a simpler approach replaces Sonnet/Opus
- `reliability` — recurring errors or fragile steps

## Step 4 — Create improvement proposals

For each high-priority insight (or cluster of medium ones), create a concrete
file change. Examples:

- A new workflow in `proposals/workflows/<name>.yml`
- A new script in `proposals/scripts/<name>.sh`
- A new skill prompt in `proposals/skills/<name>.md`
- An update to `CLAUDE.md` with a new convention or rule
- A note in `proposals/cost-reduction.md` with a specific model-swap recommendation

Put all proposals under `proposals/` so they can be reviewed before merging into
their final location.

## Step 5 — Summarize and open a PR

Create a branch `auto-improve/<date>`, commit the proposals, and open a PR with:
- Title: `chore: auto-improvement proposals <date>`
- Body: a table listing each proposal, its category, and the evidence from logs
- Reference this issue (#2) in the PR body

Keep the PR focused: include only proposals backed by at least 2 observed instances
or 1 high-confidence instance with strong evidence.
