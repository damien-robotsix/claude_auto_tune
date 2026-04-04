# Auto-Improvement Agent Prompt

You are the auto-improvement agent for this Claude Code workspace. Your goal is
to analyze recent workflow runs — including both the CI logs and the detailed
Claude Code session transcripts — identify patterns and inefficiencies, and
create a PR with concrete improvement proposals.

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

## Step 3 — Fetch and parse Claude Code session transcripts

Claude Code saves detailed session transcripts (tool calls, inputs, outputs) as
JSONL files. These are uploaded as artifacts by workflows that include the
transcript-upload step (see **Workflow Setup** below).

For each run ID, download the `claude-transcript` artifact and parse it:

```bash
for RUN_ID in $RUN_IDS; do
  echo "=== Fetching transcript for run $RUN_ID ==="
  ARTIFACT_ID=$(gh api repos/$GITHUB_REPOSITORY/actions/runs/$RUN_ID/artifacts \
    --jq '.artifacts[] | select(.name == "claude-transcript") | .id' 2>/dev/null | head -1)

  if [ -n "$ARTIFACT_ID" ]; then
    mkdir -p /tmp/transcripts/$RUN_ID
    gh api repos/$GITHUB_REPOSITORY/actions/artifacts/$ARTIFACT_ID/zip \
      > /tmp/transcripts/$RUN_ID/transcript.zip 2>/dev/null
    unzip -q /tmp/transcripts/$RUN_ID/transcript.zip \
      -d /tmp/transcripts/$RUN_ID/ 2>/dev/null || true

    python3 scripts/parse-claude-transcript.py /tmp/transcripts/$RUN_ID/ \
      >> /tmp/all-transcript-insights.jsonl \
      || echo '{"summary":"parse failed","tool_call_count":0,"top_tools":[],"insights":[]}' \
         >> /tmp/all-transcript-insights.jsonl
  else
    echo "No transcript artifact for run $RUN_ID (workflow may predate transcript upload step)"
  fi
done
```

Each line in `/tmp/all-transcript-insights.jsonl` is the JSON output for one
Claude Code session.

### Workflow Setup

For transcripts to be available, the workflow that invokes the Claude Code
action must include an upload step immediately after the action step:

```yaml
- name: Upload Claude session transcript
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: claude-transcript
    # Claude Code stores transcripts under ~/.claude/projects/
    path: ~/.claude/projects/**/*.jsonl
    if-no-files-found: ignore
    retention-days: 30
```

If this step is missing from the active workflows, add a proposal for it under
`proposals/workflows/` and note it in the PR body.

## Step 4 — Synthesize insights

Read all insights from both `/tmp/all-insights.jsonl` (workflow logs) and
`/tmp/all-transcript-insights.jsonl` (Claude session transcripts) and group
them by category. For each category with 2+ similar insights, it represents a
real pattern worth addressing.

Categories:
- `new_workflow` — tasks that should be automated as a scheduled GitHub Actions workflow
- `deterministic_script` — tasks Claude repeated identically; a shell/Python script would be faster and cheaper
- `subagent_skill` — reusable capabilities that should become a Claude Code skill or subagent prompt
- `cost_reduction` — places where Haiku or a simpler approach replaces Sonnet/Opus
- `reliability` — recurring errors or fragile steps
- `capability_gap` — tools or APIs Claude had to work around; a new MCP tool or skill would help

When synthesizing, prefer cross-source corroboration: an insight that appears
in both the workflow log and the session transcript carries higher confidence.

## Step 5 — Create improvement proposals

For each high-priority insight (or cluster of medium ones), create a concrete
file change. Examples:

- A new workflow in `proposals/workflows/<name>.yml`
- A new script in `proposals/scripts/<name>.sh`
- A new skill prompt in `proposals/skills/<name>.md`
- An update to `CLAUDE.md` with a new convention or rule
- A note in `proposals/cost-reduction.md` with a specific model-swap recommendation

Put all proposals under `proposals/` so they can be reviewed before merging into
their final location.

## Step 6 — Summarize and open a PR

Create a branch `auto-improve/<date>`, commit the proposals, and open a PR with:
- Title: `chore: auto-improvement proposals <date>`
- Body: a table listing each proposal, its category, and the evidence from logs
- Reference this issue (#2) in the PR body
- Note whether transcript data was available and how many sessions were analyzed

Keep the PR focused: include only proposals backed by at least 2 observed instances
or 1 high-confidence instance with strong evidence.
