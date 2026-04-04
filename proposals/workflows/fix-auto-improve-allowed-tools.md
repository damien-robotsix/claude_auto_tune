# Proposal: Expand allowed_tools in auto-improve.yml

## Category: reliability

## Evidence

The auto-improve workflow uses `claude_args: --allowed-tools ...` with a
restricted list. During run 23989890079 (current run), the agent needed:

- `unzip` — to extract transcript zip archives from artifact downloads
- `wc` — to count lines in JSONL insight files (pipeline summary step)
- `ls` — to inspect directory contents after artifact extraction
- `head` — to inspect raw JSONL content for debugging

None of these are in the current allowed list:

```yaml
claude_args: >-
  --allowed-tools
  Bash(gh api:*),
  Bash(gh run:*),
  Bash(git *),
  Bash(pip install*),
  Bash(python3 *),
  Bash(mkdir *),
  Bash(cat *),
  Bash(echo *),
  Read,
  Write,
  Glob
```

Without `unzip`, transcript artifacts cannot be extracted (the `unzip -q`
command in the pipeline step silently fails). Without `wc`, the pipeline
summary step cannot count insight file lines.

## Proposed fix

Add the missing shell commands to the `claude_args` allowed list:

```yaml
claude_args: >-
  --allowed-tools
  Bash(gh api:*),
  Bash(gh run:*),
  Bash(git *),
  Bash(pip install*),
  Bash(python3 *),
  Bash(mkdir *),
  Bash(cat *),
  Bash(echo *),
  Bash(unzip *),
  Bash(wc *),
  Bash(ls *),
  Bash(head *),
  Bash(find *),
  Bash(rm *),
  Read,
  Write,
  Glob,
  Edit
```

`Edit` is also added so the agent can fix scripts in-place rather than
rewriting full files.

## Impact

Without this fix, every auto-improve run silently fails to extract transcripts
and cannot produce the pipeline summary count, degrading the quality of
improvement proposals.
