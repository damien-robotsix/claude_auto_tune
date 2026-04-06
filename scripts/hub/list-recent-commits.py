#!/usr/bin/env python3
"""
Deterministic lister for recent commits on the default branch.

Lists commits pushed to the repository's default branch within a lookback
window and emits a single JSON array to stdout. One row per commit with:

- sha, short_sha, message, author, date, url
- files: list of changed file paths (with additions/deletions/status)
- diff: unified diff (truncated at DIFF_CHAR_CAP per commit)
- diff_truncated: bool

This is a pure orchestration of ``gh`` / ``git``. No LLM calls, no network
beyond what ``gh`` already does, no writes. It exists so that the
``hub-daily-sweep`` workflow's Claude agent can get a deterministic commit
bundle in one tool call instead of chaining many ``gh`` invocations.

Usage::

    python3 scripts/hub/list-recent-commits.py
    python3 scripts/hub/list-recent-commits.py --since 48h
    python3 scripts/hub/list-recent-commits.py --repo owner/name --since 24h
    python3 scripts/hub/list-recent-commits.py --since 24h -o /tmp/commits.json

Exit codes:
    0  success (even if zero commits matched)
    2  usage error
    3  ``gh`` CLI not installed or not authenticated
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

# Per-commit diff cap. Bigger diffs get truncated and flagged so the caller
# can fetch the specific files it needs via other tools.
DIFF_CHAR_CAP = 80_000

# Max commits we'll bundle in one call. The sweep workflow should never be
# asked to reason about hundreds of commits at once.
COMMIT_LIMIT = 50


def _run_gh(args: list[str]) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return 127, "", "gh CLI not found on PATH"
    return proc.returncode, proc.stdout, proc.stderr


def _gh_json(args: list[str]) -> tuple[Any, str | None]:
    rc, out, err = _run_gh(args)
    if rc != 0:
        return None, (err or out or f"gh exited with {rc}").strip()
    try:
        return json.loads(out), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON from gh: {exc}"


_DURATION_RE = re.compile(r"^\s*(\d+)\s*([hdw])\s*$", re.IGNORECASE)


def parse_since(value: str) -> timedelta:
    """Parse a lookback like ``24h``, ``3d``, ``1w`` into a timedelta."""
    m = _DURATION_RE.match(value)
    if not m:
        raise ValueError(
            f"invalid --since {value!r}; expected e.g. 24h, 3d, 1w"
        )
    n = int(m.group(1))
    unit = m.group(2).lower()
    if unit == "h":
        return timedelta(hours=n)
    if unit == "d":
        return timedelta(days=n)
    return timedelta(weeks=n)


def resolve_default_repo() -> str | None:
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env
    data, err = _gh_json(["repo", "view", "--json", "nameWithOwner"])
    if err or not data:
        return None
    return data.get("nameWithOwner")


def resolve_default_branch(repo: str) -> tuple[str | None, str | None]:
    data, err = _gh_json(
        ["repo", "view", repo, "--json", "defaultBranchRef"]
    )
    if err or not data:
        return None, err or "no repo data"
    ref = data.get("defaultBranchRef") or {}
    return ref.get("name"), None


def list_recent_commits(
    repo: str, branch: str, since: datetime
) -> tuple[list[dict], str | None]:
    """Fetch commits on ``branch`` since ``since`` via the GitHub API."""
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    data, err = _gh_json(
        [
            "api",
            f"repos/{repo}/commits",
            "--paginate",
            "-f", f"sha={branch}",
            "-f", f"since={since_iso}",
            "-f", f"per_page={COMMIT_LIMIT}",
        ]
    )
    if err:
        return [], err
    if not isinstance(data, list):
        return [], "unexpected response format from commits API"
    return data[:COMMIT_LIMIT], None


def fetch_commit_diff(repo: str, sha: str) -> tuple[str, bool, str | None]:
    """Fetch the diff for a single commit via gh api."""
    rc, stdout, err = _run_gh(
        [
            "api",
            f"repos/{repo}/commits/{sha}",
            "-H", "Accept: application/vnd.github.v3.diff",
        ]
    )
    if rc != 0:
        return "", False, (err or f"gh api exited with {rc}").strip()
    if len(stdout) > DIFF_CHAR_CAP:
        return stdout[:DIFF_CHAR_CAP], True, None
    return stdout, False, None


def fetch_commit_files(repo: str, sha: str) -> tuple[list[dict], str | None]:
    """Fetch the file list for a single commit via gh api."""
    data, err = _gh_json(
        [
            "api",
            f"repos/{repo}/commits/{sha}",
            "--jq", ".files",
        ]
    )
    if err:
        return [], err
    if not isinstance(data, list):
        return [], None
    return [
        {
            "path": f.get("filename"),
            "status": f.get("status"),
            "additions": f.get("additions"),
            "deletions": f.get("deletions"),
        }
        for f in data
    ], None


def build_row(repo: str, commit: dict) -> dict:
    sha = commit.get("sha", "")
    commit_data = commit.get("commit", {})
    author_data = commit_data.get("author", {})
    gh_author = commit.get("author") or {}

    files, _files_err = fetch_commit_files(repo, sha)
    diff, truncated, diff_err = fetch_commit_diff(repo, sha)

    row: dict[str, Any] = {
        "repo": repo,
        "sha": sha,
        "short_sha": sha[:7],
        "message": commit_data.get("message", ""),
        "author": gh_author.get("login") or author_data.get("name", ""),
        "date": author_data.get("date", ""),
        "url": commit.get("html_url", ""),
        "files": files,
        "diff": diff,
        "diff_truncated": truncated,
    }
    if diff_err:
        row["diff_error"] = diff_err
    return row


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "List commits on the default branch within a lookback "
            "window as a JSON array (used by the hub-daily-sweep "
            "workflow)."
        )
    )
    parser.add_argument(
        "--since",
        default="24h",
        help="lookback window: e.g. 24h, 3d, 1w (default: 24h)",
    )
    parser.add_argument(
        "--repo",
        help=(
            "owner/name slug (default: $GITHUB_REPOSITORY or gh default)"
        ),
    )
    parser.add_argument(
        "--branch",
        help=(
            "branch to list commits from (default: the repo's default "
            "branch)"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        help="write JSON array to this path instead of stdout",
    )
    args = parser.parse_args()

    if not shutil.which("gh"):
        print("error: gh CLI not found on PATH", file=sys.stderr)
        return 3

    try:
        window = parse_since(args.since)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    repo = args.repo or resolve_default_repo()
    if not repo:
        print(
            "error: could not determine repo; pass --repo owner/name",
            file=sys.stderr,
        )
        return 2

    branch = args.branch
    if not branch:
        branch, err = resolve_default_branch(repo)
        if not branch:
            print(
                f"error: could not resolve default branch: {err}",
                file=sys.stderr,
            )
            return 2

    since_dt = datetime.now(timezone.utc) - window
    commits, err = list_recent_commits(repo, branch, since_dt)
    if err:
        print(f"error: commits API failed: {err}", file=sys.stderr)
        return 3

    rows = [build_row(repo, c) for c in commits]
    text = json.dumps(rows, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
            f.write("\n")
    else:
        sys.stdout.write(text)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
