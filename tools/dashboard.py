#!/usr/bin/env python3
from __future__ import annotations
"""
tools/dashboard.py
VibeSafe Status Dashboard — 프로덕트 + KPI + 시스템 상태 한눈에.

Usage:
  python3 tools/dashboard.py                  # GitHub token from env
  GITHUB_TOKEN=ghp_xxx python3 tools/dashboard.py
  python3 tools/dashboard.py --no-github      # local only (skip API)
"""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "vibesafeio/vibesafe-action"


def github_api(endpoint: str) -> dict | list:
    if not TOKEN:
        return {}
    url = f"https://api.github.com/{endpoint}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return {}


def section(title: str):
    print(f"\n{'━' * 50}")
    print(f"  {title}")
    print(f"{'━' * 50}")


def main():
    skip_github = "--no-github" in sys.argv
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"🔐 VibeSafe Dashboard — {now}")

    # ── 1. KPI Metrics ──
    section("📊 Phase 1 KPIs")
    if not skip_github and TOKEN:
        repo = github_api(f"repos/{REPO}")
        views = github_api(f"repos/{REPO}/traffic/views")
        clones = github_api(f"repos/{REPO}/traffic/clones")
        stars = repo.get("stargazers_count", "?")
        forks = repo.get("forks_count", "?")
        issues = repo.get("open_issues_count", "?")
        view_count = views.get("count", "?")
        view_unique = views.get("uniques", "?")
        clone_count = clones.get("count", "?")
        clone_unique = clones.get("uniques", "?")

        print(f"  Stars:        {stars} / 100 target")
        print(f"  Forks:        {forks}")
        print(f"  Open issues:  {issues}")
        print(f"  Views (14d):  {view_count} total, {view_unique} unique")
        print(f"  Clones (14d): {clone_count} total, {clone_unique} unique")
    else:
        print("  (GitHub API skipped — set GITHUB_TOKEN or remove --no-github)")

    # ── 2. Harness Status ──
    section("🧪 Harness Status")
    log_file = PROJECT_DIR / "test" / "harness_log.json"
    if log_file.exists():
        logs = json.loads(log_file.read_text())
        if logs:
            last = logs[-1]
            status_emoji = "✅" if last["status"] == "pass" else "❌"
            print(f"  Last run:     {status_emoji} {last['status'].upper()} ({last['timestamp']})")
            print(f"  Commit:       {last['commit']}")
            if last.get("failures"):
                print(f"  Failures:     {last['failures']}")
            # Show last 5 runs
            recent = logs[-5:]
            streak = "".join("✅" if r["status"] == "pass" else "❌" for r in recent)
            print(f"  Last 5 runs:  {streak}")
        else:
            print("  No harness runs recorded")
    else:
        print("  No harness log found")

    # ── 3. Feature Status ──
    section("🛡️ Security Stack")
    features = [
        ("SAST (Semgrep + custom rules)", True),
        ("Secret Detection (15 patterns)", True),
        ("SCA Dependencies (pip-audit + npm)", True),
        ("Config: Supabase RLS check", True),
        ("Config: Firebase Rules check", True),
        ("Fix Suggestions (38 patterns)", True),
        ("Framework false positive filter", True),
        ("Merge blocking (fail-on)", True),
        ("PR Comments (English)", True),
        ("Pre-commit hook", True),
        ("MCP Server (Claude Code/Cursor)", True),
        ("Custom rules input", True),
        ("Diff-only scanning", False),  # Semgrep Pro only
        ("Dynamic badge endpoint", True),
        ("Share page (vibesafe.dev)", False),
    ]
    for name, done in features:
        emoji = "✅" if done else "⬜"
        print(f"  {emoji} {name}")

    # ── 4. Git Status ──
    section("📦 Git Status")
    try:
        branch = subprocess.run(["git", "branch", "--show-current"],
                                capture_output=True, text=True, cwd=str(PROJECT_DIR)).stdout.strip()
        status = subprocess.run(["git", "status", "--short"],
                                capture_output=True, text=True, cwd=str(PROJECT_DIR)).stdout.strip()
        last_commit = subprocess.run(["git", "log", "--oneline", "-1"],
                                     capture_output=True, text=True, cwd=str(PROJECT_DIR)).stdout.strip()
        ahead = subprocess.run(["git", "rev-list", "--count", "origin/master..HEAD"],
                               capture_output=True, text=True, cwd=str(PROJECT_DIR)).stdout.strip()
        print(f"  Branch:       {branch}")
        print(f"  Last commit:  {last_commit}")
        print(f"  Ahead:        {ahead} commits")
        if status:
            print(f"  Uncommitted:  {len(status.splitlines())} files")
        else:
            print(f"  Working tree: clean")
    except Exception:
        print("  (git not available)")

    # ── 5. Marketing Channels ──
    section("📣 Distribution Channels")
    channels = [
        ("OKKY", "Published", "https://okky.kr/articles/1553873"),
        ("DEV.to", "Published", "dev.to/keuntaepark/..."),
        ("GitHub Marketplace", "Published", "v0.1.0 release"),
        ("GeekNews", "Waiting", "Publish after 2026-03-26"),
        ("Reddit r/webdev", "Not posted", ""),
        ("Hacker News", "Not posted", ""),
        ("Product Hunt", "Not launched", ""),
    ]
    for name, status, note in channels:
        emoji = "🟢" if "Published" in status else "🟡" if "Waiting" in status else "⚪"
        line = f"  {emoji} {name}: {status}"
        if note:
            line += f" — {note}"
        print(line)

    # ── 6. Docker Image ──
    section("🐳 Docker Image")
    if not skip_github and TOKEN:
        runs = github_api(f"repos/{REPO}/actions/workflows/publish-action.yml/runs?per_page=1")
        if runs and runs.get("workflow_runs"):
            last_run = runs["workflow_runs"][0]
            emoji = "✅" if last_run["conclusion"] == "success" else "❌"
            print(f"  Last build:   {emoji} {last_run['conclusion']} ({last_run['created_at'][:16]})")
            print(f"  Commit:       {last_run['head_sha'][:7]}")
        else:
            print("  No build data")
    else:
        print("  (skipped)")

    print(f"\n{'━' * 50}")
    print(f"  Dashboard generated at {now}")
    print(f"{'━' * 50}\n")


if __name__ == "__main__":
    main()
