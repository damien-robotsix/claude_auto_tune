#!/usr/bin/env python3
"""
Aggregate daily token usage from hub transcripts into per-day JSON reports.

Walks ``transcripts/<workspace-slug>/<date>/`` in a local hub clone,
extracts model and token usage from each JSONL transcript, and writes
a structured report to ``usage/<date>.json``.  Also maintains
``usage/index.json`` (sorted list of available dates) for the dashboard.

No LLM calls, no network calls.  Operates purely on local files.

Usage
-----
::

    python3 scripts/hub/aggregate-usage.py --hub-dir .scratch/hub
    python3 scripts/hub/aggregate-usage.py --hub-dir .scratch/hub --date 2026-04-05

Exit codes
----------
0  on success (including "nothing to aggregate").
1  on fatal errors (missing hub dir, etc.).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def _empty_bucket() -> dict[str, int]:
    return {f: 0 for f in TOKEN_FIELDS}


def _add_bucket(dst: dict[str, int], src: dict[str, int]) -> None:
    for f in TOKEN_FIELDS:
        dst[f] += src.get(f, 0)


def load_workflow_from_meta(meta_path: Path) -> str:
    """Return workflow name from .meta.json, or ``local`` for local sessions."""
    if not meta_path.exists():
        return "unknown"
    try:
        meta = json.loads(meta_path.read_text())
    except (json.JSONDecodeError, OSError):
        return "unknown"
    if meta.get("source") == "local":
        return "local"
    return meta.get("workflow") or "unknown"


def extract_usage(jsonl_path: Path) -> dict[str, dict[str, int]]:
    """Parse a transcript JSONL and return ``{model: {token_field: count}}``."""
    by_model: dict[str, dict[str, int]] = {}
    try:
        text = jsonl_path.read_text(errors="replace")
    except OSError:
        return by_model
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        msg = entry.get("message", entry)
        role = msg.get("role", entry.get("type", ""))
        if role != "assistant":
            continue
        model = msg.get("model", "unknown")
        usage = msg.get("usage") or entry.get("usage")
        if not usage:
            continue
        if model not in by_model:
            by_model[model] = _empty_bucket()
        _add_bucket(by_model[model], usage)
    return by_model


def aggregate_date(hub_dir: Path, date: str) -> dict | None:
    """Aggregate all transcripts for *date* across all workspaces.

    Returns the full report dict, or ``None`` if no transcripts found.
    """
    transcripts_root = hub_dir / "transcripts"
    if not transcripts_root.is_dir():
        return None

    workspaces: dict[str, dict] = {}
    grand_total = _empty_bucket()
    grand_sessions = 0

    # Walk transcripts/<owner>/<repo>/<date>/ — slug has two path components
    for owner_dir in sorted(transcripts_root.iterdir()):
        if not owner_dir.is_dir():
            continue
        for repo_dir in sorted(owner_dir.iterdir()):
            if not repo_dir.is_dir():
                continue
            slug = f"{owner_dir.name}/{repo_dir.name}"
            date_dir = repo_dir / date
            if not date_dir.is_dir():
                continue
            jsonl_files = sorted(date_dir.glob("*.jsonl"))
            if not jsonl_files:
                continue

            ws_workflows: dict[str, dict] = {}
            ws_total = _empty_bucket()
            ws_sessions = 0

            for jsonl_path in jsonl_files:
                meta_path = jsonl_path.with_suffix(".meta.json")
                workflow = load_workflow_from_meta(meta_path)
                by_model = extract_usage(jsonl_path)
                if not by_model:
                    continue

                ws_sessions += 1
                grand_sessions += 1

                if workflow not in ws_workflows:
                    ws_workflows[workflow] = {
                        "sessions": 0,
                        "models": {},
                        "total": _empty_bucket(),
                    }
                wf = ws_workflows[workflow]
                wf["sessions"] += 1
                for model, tokens in by_model.items():
                    if model not in wf["models"]:
                        wf["models"][model] = _empty_bucket()
                    _add_bucket(wf["models"][model], tokens)
                    _add_bucket(wf["total"], tokens)
                    _add_bucket(ws_total, tokens)
                    _add_bucket(grand_total, tokens)

            if ws_sessions > 0:
                workspaces[slug] = {
                    "workflows": ws_workflows,
                    "total": {**ws_total, "sessions": ws_sessions},
                }

    if not workspaces:
        return None

    return {
        "date": date,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(
            timespec="seconds"
        ),
        "workspaces": workspaces,
        "grand_total": {**grand_total, "sessions": grand_sessions},
    }


def update_index(usage_dir: Path) -> None:
    """Rebuild ``usage/index.json`` from the set of ``<date>.json`` files."""
    dates = sorted(
        (p.stem for p in usage_dir.glob("*.json") if p.stem != "index"),
        reverse=True,
    )
    index_path = usage_dir / "index.json"
    index_path.write_text(json.dumps({"dates": dates}, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate daily token usage from hub transcripts."
    )
    parser.add_argument(
        "--hub-dir",
        required=True,
        help="Path to the local hub repo clone.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help=(
            "Date to aggregate (YYYY-MM-DD). "
            "Defaults to yesterday (UTC)."
        ),
    )
    args = parser.parse_args()

    hub_dir = Path(args.hub_dir)
    if not hub_dir.is_dir():
        print(f"error: hub directory not found: {hub_dir}", file=sys.stderr)
        return 1

    date = args.date
    if not date:
        yesterday = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=1)
        date = yesterday.strftime("%Y-%m-%d")

    report = aggregate_date(hub_dir, date)
    if report is None:
        print(f"aggregate-usage: no transcripts found for {date}")
        return 0

    usage_dir = hub_dir / "usage"
    usage_dir.mkdir(parents=True, exist_ok=True)
    out_path = usage_dir / f"{date}.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    update_index(usage_dir)

    gt = report["grand_total"]
    print(
        f"aggregate-usage: {date} — "
        f"{gt['sessions']} session(s), "
        f"{gt['input_tokens']:,} input / {gt['output_tokens']:,} output tokens"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
