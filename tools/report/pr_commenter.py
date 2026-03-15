from __future__ import annotations

"""VibeSafe PR Comment — GitHub Actions 환경에서 PR에 스캔 결과를 코멘트한다."""

import json
import os
import sys
import urllib.request


def build_comment_body(score: dict) -> str:
    points = score["score"]
    grade = score["grade"]
    domain = score["domain"]
    certified = score.get("certified", False)
    critical = score.get("critical", 0)
    high = score.get("high", 0)
    medium = score.get("medium", 0)
    low = score.get("low", 0)
    total = score.get("total_vulnerabilities", 0)
    block_reason = score.get("certified_block_reason") or ""

    grade_emoji = {"A": "\U0001f7e2", "B": "\U0001f7e1", "C": "\U0001f7e0", "D": "\U0001f534", "F": "\U0001f534"}.get(grade, "\u26aa")
    cert_badge = " \u2705 **Certified**" if certified else ""
    cert_block = f"\n> \uc778\uc99d \ubd88\uac00: {block_reason}" if block_reason else ""

    if critical > 0:
        summary = f"Critical \ucde8\uc57d\uc810 {critical}\uac1c \ubc1c\uacac \u2014 \uc989\uc2dc \uc218\uc815 \ud544\uc694"
    elif high > 0:
        summary = f"High \ucde8\uc57d\uc810 {high}\uac1c \ubc1c\uacac \u2014 \uba38\uc9c0 \uc804 \uc218\uc815 \uad8c\uc7a5"
    elif medium > 0:
        summary = f"Medium \ucde8\uc57d\uc810 {medium}\uac1c \ubc1c\uacac"
    elif low > 0:
        summary = f"Low \ucde8\uc57d\uc810 {low}\uac1c"
    else:
        summary = "\ucde8\uc57d\uc810 \ubbf8\ubc1c\uacac"

    lines = [
        "## \U0001f510 VibeSafe \ubcf4\uc548 \uc2a4\uce94 \uacb0\uacfc",
        "",
        f"{grade_emoji} **{points}/100** (\ub4f1\uae09 {grade}){cert_badge}",
        cert_block,
        "",
        f"> {summary}",
        "",
        "| \uc2ec\uac01\ub3c4 | \uac74\uc218 |",
        "|--------|------|",
        f"| \U0001f534 Critical | {critical} |",
        f"| \U0001f7e0 High     | {high} |",
        f"| \U0001f7e1 Medium   | {medium} |",
        f"| \U0001f7e2 Low      | {low} |",
        "",
        f"\ub3c4\uba54\uc778: `{domain}` \u00b7 \ucd1d {total}\uac74",
        "",
        "<sub>Powered by [VibeSafe](https://vibesafe.dev)</sub>",
    ]
    return "\n".join(lines)


MARKER = "VibeSafe \ubcf4\uc548 \uc2a4\uce94 \uacb0\uacfc"


def github_api(method: str, url: str, token: str, data: dict | None = None) -> dict:
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def post_or_update_comment(token: str, repo: str, pr_number: int, body: str) -> None:
    api = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"

    comments = github_api("GET", api, token)
    existing = None
    for c in comments:
        if c.get("user", {}).get("login") == "github-actions[bot]" and MARKER in c.get("body", ""):
            existing = c
            break

    if existing:
        github_api("PATCH", existing["url"], token, {"body": body})
        print(f"Updated existing comment #{existing['id']}")
    else:
        result = github_api("POST", api, token, {"body": body})
        print(f"Created comment #{result['id']}")


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("No GitHub token provided, skipping PR comment.")
        return

    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path or not os.path.exists(event_path):
        print("Not running in GitHub Actions, skipping PR comment.")
        return

    with open(event_path) as f:
        event = json.load(f)

    pr_number = event.get("pull_request", {}).get("number")
    if not pr_number:
        print("Not a pull_request event, skipping PR comment.")
        return

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        print("GITHUB_REPOSITORY not set, skipping PR comment.")
        return

    score_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/score.json"
    with open(score_path) as f:
        score = json.load(f)

    body = build_comment_body(score)
    post_or_update_comment(token, repo, pr_number, body)


if __name__ == "__main__":
    main()
