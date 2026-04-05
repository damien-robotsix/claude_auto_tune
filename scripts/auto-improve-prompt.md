# Auto-Improvement Agent Prompt

You are the auto-improvement agent for this Claude Code workspace. Your goal
is to analyze recent workflow runs — including both the CI logs and the
detailed Claude Code session transcripts — identify concrete, actionable
improvements, and deliver them as:

1. **One umbrella GitHub issue** containing the global report (summary of
   findings, metrics, and a list of every spawned PR with a one-line
   description).
2. **One focused PR per improvement subject**, each containing the actual
   code changes (not proposals) and a detailed explanation in the PR body.

Do **not** dump everything into a single bundled PR or place files under a
`proposals/` directory. Each improvement must stand on its own as a merge-ready
change.

## Step 1 — Fetch workflow run IDs

Fetch **all** recent workflow runs (no cap on workflows). Pagination is
enabled so the list is limited only by GitHub's retention window and the
default API window (typically the last several hundred runs is fine —
don't try to pull years of history).

```bash
gh api repos/$GITHUB_REPOSITORY/actions/runs \
  --paginate \
  --jq '.workflow_runs[] | {id: .id, name: .name, created_at: .created_at, conclusion: .conclusion}' \
  > /tmp/runs.jsonl
echo ">>> Total runs discovered: $(wc -l < /tmp/runs.jsonl)"
```

Collect all run IDs into a list (`$RUN_IDS`). There is **no upper limit**
for workflow log parsing — all discovered runs are analyzed in Step 2.

The separate `$CONVERSATION_LIMIT` (provided to you in the task invocation,
default 20) only caps how many **Claude Code session transcripts** are
downloaded in Step 3.

## Step 2 — Parse every run log with the log parser

Iterate over **all** discovered run IDs — no slicing.

```bash
pip install -q anthropic pyyaml
WORKFLOWS_PARSED=0
for RUN_ID in $RUN_IDS; do
  echo "=== Parsing run $RUN_ID ==="
  gh run view "$RUN_ID" --log 2>/dev/null \
    | python3 scripts/parse-workflow-log.py \
    >> /tmp/all-insights.jsonl || echo '{"summary":"fetch failed","insights":[]}' >> /tmp/all-insights.jsonl
  WORKFLOWS_PARSED=$((WORKFLOWS_PARSED + 1))
done
echo ">>> Workflows parsed: $WORKFLOWS_PARSED"
```

## Step 3 — Fetch and parse Claude Code session transcripts (cap: $CONVERSATION_LIMIT)

Walk the run list in order (newest first, as returned by the API) and
download the `claude-transcript` artifact where available. **Stop as soon
as `$CONVERSATION_LIMIT` transcripts have been successfully analyzed.**
Runs without a transcript artifact don't count toward the cap — keep
going until you either hit the limit or exhaust the run list.

```bash
CONVERSATIONS_ANALYZED=0
for RUN_ID in $RUN_IDS; do
  if [ "$CONVERSATIONS_ANALYZED" -ge "$CONVERSATION_LIMIT" ]; then
    echo ">>> Reached conversation cap ($CONVERSATION_LIMIT); stopping transcript collection."
    break
  fi

  ARTIFACT_ID=$(gh api repos/$GITHUB_REPOSITORY/actions/runs/$RUN_ID/artifacts \
    --jq '.artifacts[] | select(.name == "claude-transcript") | .id' 2>/dev/null | head -1)

  if [ -z "$ARTIFACT_ID" ]; then
    continue  # no transcript for this run — not counted against the cap
  fi

  echo "=== Fetching transcript for run $RUN_ID ==="
  mkdir -p /tmp/transcripts/$RUN_ID
  gh api repos/$GITHUB_REPOSITORY/actions/artifacts/$ARTIFACT_ID/zip \
    > /tmp/transcripts/$RUN_ID/transcript.zip 2>/dev/null
  unzip -q /tmp/transcripts/$RUN_ID/transcript.zip \
    -d /tmp/transcripts/$RUN_ID/ 2>/dev/null || true

  python3 scripts/parse-claude-transcript.py /tmp/transcripts/$RUN_ID/ \
    >> /tmp/all-transcript-insights.jsonl \
    || echo '{"summary":"parse failed","tool_call_count":0,"top_tools":[],"insights":[]}' \
       >> /tmp/all-transcript-insights.jsonl
  CONVERSATIONS_ANALYZED=$((CONVERSATIONS_ANALYZED + 1))
done
echo ">>> Conversations analyzed: $CONVERSATIONS_ANALYZED (cap: $CONVERSATION_LIMIT)"
```

### Workflow Setup (sanity check)

For transcripts to be available, every workflow invoking `claude-code-action`
must end with an upload step like:

```yaml
- name: Upload Claude session transcript
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: claude-transcript
    path: ~/.claude/projects/**/*.jsonl
    if-no-files-found: ignore
    retention-days: 30
```

If any active workflow is missing it, that alone becomes one of your
improvement subjects (see Step 5).

## Step 4 — Synthesize and cluster into improvement subjects

Read all insights from both `/tmp/all-insights.jsonl` (workflow logs) and
`/tmp/all-transcript-insights.jsonl` (Claude session transcripts). Group them
into **improvement subjects** where each subject is:

- A single, focused change that can be shipped as one PR.
- Supported by **at least 2 observed instances** or **1 high-confidence
  instance** with strong evidence.
- Scoped narrowly enough that a reviewer can understand it in a few minutes.

Suggested categories (a subject can fit more than one):

- `reliability` — recurring errors, flaky steps, missing tool permissions
- `cost_reduction` — swap a cheaper model where quality is unaffected
- `new_workflow` — repeated manual work worth automating
- `deterministic_script` — Claude repeating the same steps; a script is faster
- `subagent_skill` — capability worth extracting into a skill/subagent
- `capability_gap` — a missing tool or API causing workarounds
- `docs_convention` — a rule or convention that should live in `CLAUDE.md`

Prefer insights that are corroborated by **both** log and transcript sources.

Aim for **3–7 improvement subjects** total. If you find more, pick the
highest-impact ones and mention the rest in the umbrella issue as "deferred".

## Step 5 — Ship each subject as its own PR

For **each** improvement subject, in order:

1. `git checkout main && git pull`
2. Create a branch: `auto-improve/<date>-<short-slug>` (e.g.
   `auto-improve/2026-04-05-add-gh-pr-allowed-tool`).
3. Make the **actual** edits — modify the real files (`.github/workflows/*`,
   `scripts/*`, `CLAUDE.md`, etc.). Do not place anything under a `proposals/`
   directory.
4. Keep the change minimal and self-contained. If two subjects would touch
   the same lines, merge them into one subject instead.
5. Commit with a clear message explaining the *why*.
6. Push the branch and open a PR with:
   - **Title**: concise, imperative (`fix:`, `feat:`, `chore:` prefix).
   - **Body** (required sections):
     - `## Problem` — what the logs/transcripts showed, with run IDs or
       excerpts as evidence.
     - `## Change` — what this PR modifies and why.
     - `## Files` — bulleted list of modified files.
     - `## Evidence` — number of observed instances, sources (log vs.
       transcript), and confidence level (low / medium / high).
   - Do **not** reference the umbrella issue yet — you'll link it after the
     issue is created in Step 6.

Record each opened PR's number and title in a local variable so Step 6 can
reference them.

If a subject cannot be implemented as a code change (e.g. it's purely a
recommendation or needs human judgment), do **not** open an empty PR. Instead,
list it in the umbrella issue under a "Recommendations (no PR)" section.

## Step 6 — Open the umbrella issue with the global report

After all PRs are opened, create **one** GitHub issue titled
`Auto-improvement report <date>` with this structure:

```markdown
## Summary
<2–4 sentences describing the scan: how many runs analyzed, overall health,
biggest themes>

## Pipeline metrics
- Workflows parsed: <N>
- Conversations analyzed: <N>
- Improvement subjects identified: <N>
- PRs opened: <N>

## Proposed changes
| PR | Category | One-line description |
| -- | -------- | -------------------- |
| #<num> | reliability | Add missing `gh pr:*` to auto-improve allowed-tools |
| #<num> | cost_reduction | Switch log parser default to haiku |
| ...    | ...          | ...                                               |

## Recommendations (no PR)
<optional — subjects that need human judgment>

## Deferred
<optional — lower-priority subjects not shipped this run>

---
Generated by the Auto-Improvement Agent.
```

Use `gh issue create` to open it, then **edit each PR body** (via
`gh pr edit <num> --body`) to append a line `Part of #<issue-num>` so the
links go both ways.

## Step 7 — Exit criteria and guardrails

- If both `WORKFLOWS_PARSED` and `CONVERSATIONS_ANALYZED` are 0, **stop**.
  Open a single issue titled `Auto-improvement report <date> — no data` with
  a brief explanation of why nothing was analyzed. Do not open any PRs.
- Never modify `.env`, `*.key`, `*.pem`, `credentials.*`, or anything in
  `.github/workflows/` without a concrete, evidence-backed reason.
- Never force-push. Never rewrite `main`. Each PR targets `main` from its own
  branch.
- If a PR would touch more than ~5 files, reconsider whether it's really one
  subject — split it or narrow the scope.
