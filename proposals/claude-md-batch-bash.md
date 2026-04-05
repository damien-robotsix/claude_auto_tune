# CLAUDE.md addition: batch sequential bash commands

**Category:** `deterministic_script` — **Priority:** high
**Evidence:** 5 of 5 analysed session transcripts flagged long consecutive
Bash-call chains as the single biggest waste. Observed chain lengths:

| Run         | Tool calls | Longest consecutive Bash run |
|-------------|-----------:|-----------------------------:|
| 23990283750 | 76         | 22 in a row (plus 14, 10)    |
| 23990303471 | 56         | 13 in a row                  |
| 23990241024 | 23         | 4 + 4 (two clusters)         |
| 23990306838 | 15         | 12 in a row                  |
| unnamed     |  8         | 4 in a row                   |

## Proposed CLAUDE.md addition

Append to `CLAUDE.md` under **Key conventions**:

> - **Batch shell work.** When a task needs more than ~3 dependent bash
>   commands, write them as a single multi-line `bash` invocation (using
>   `&&` chains or a heredoc) rather than calling the `Bash` tool once per
>   command. Each `Bash` tool call costs a round-trip to the model; chains
>   of 10+ sequential calls appeared in 4 of our last 5 sessions and account
>   for the majority of wasted turns. If the same chain recurs across
>   sessions, promote it to a script under `scripts/`.

## Why this is load-bearing

Every consecutive `Bash` call consumes a full agent turn (prompt + tool
result round-trip). A 22-call chain is ~22× the token cost of the same logic
in one script invocation. This is the highest-signal, cheapest-to-fix pattern
across the observed sessions.
