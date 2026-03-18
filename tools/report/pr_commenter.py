from __future__ import annotations

"""VibeSafe PR Comment — GitHub Actions 환경에서 PR에 스캔 결과를 코멘트한다."""

import json
import os
import sys
import urllib.request


SEVERITY_EMOJI = {
    "CRITICAL": "\U0001f534",
    "HIGH": "\U0001f7e0",
    "MEDIUM": "\U0001f7e1",
    "LOW": "\U0001f7e2",
    "INFO": "\u2139\ufe0f",
}
SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
SEVERITY_MAP = {"ERROR": "HIGH", "WARNING": "MEDIUM", "NOTE": "LOW", "NONE": "INFO"}
MAX_FINDINGS = 20  # PR 코멘트 길이 제한 방지

# 프레임워크 충돌 맵: key 프레임워크가 감지되면 value의 rule prefix를 오탐으로 제거
FRAMEWORK_CONFLICTS: dict[str, list[str]] = {
    "flask": ["python.django."],
    "django": ["python.flask."],
    "fastapi": ["python.django.", "python.flask."],
    "express": ["python.django.", "python.flask."],
}


def load_sarif_findings(sarif_path: str, detected_stack: list[str] | None = None) -> list[dict]:
    """SARIF 파일에서 개별 취약점 목록을 추출한다."""
    if not os.path.exists(sarif_path):
        return []
    with open(sarif_path) as f:
        data = json.load(f)

    # 프레임워크 충돌 필터: 감지된 스택 기반으로 제외할 rule prefix 목록
    exclude_prefixes: list[str] = []
    for framework in (detected_stack or []):
        exclude_prefixes.extend(FRAMEWORK_CONFLICTS.get(framework, []))

    findings: list[dict] = []
    for run in data.get("runs", []):
        # rule ID → severity, message 매핑
        rule_meta: dict[str, dict] = {}
        for rule in run.get("tool", {}).get("driver", {}).get("rules", []):
            level = rule.get("defaultConfiguration", {}).get("level", "").upper()
            # rule의 help/message 텍스트 (수정 가이드 포함)
            desc = (
                rule.get("help", {}).get("text", "")
                or rule.get("shortDescription", {}).get("text", "")
                or rule.get("fullDescription", {}).get("text", "")
            )
            rule_meta[rule["id"]] = {"level": level, "description": desc}

        for result in run.get("results", []):
            rule_id = result.get("ruleId", "unknown")

            # 프레임워크 충돌 오탐 필터링
            if any(rule_id.startswith(prefix) for prefix in exclude_prefixes):
                continue

            meta = rule_meta.get(rule_id, {})

            # severity 결정
            level = result.get("level", "").upper()
            if not level or level == "NONE":
                level = meta.get("level", "NOTE")
            severity = SEVERITY_MAP.get(level, level)
            if severity not in SEVERITY_ORDER:
                severity = "INFO"

            # 위치 정보
            locations = result.get("locations", [])
            if locations:
                phys = locations[0].get("physicalLocation", {})
                file_path = phys.get("artifactLocation", {}).get("uri", "")
                start_line = phys.get("region", {}).get("startLine", 0)
                snippet = phys.get("region", {}).get("snippet", {}).get("text", "").strip()
            else:
                file_path = ""
                start_line = 0
                snippet = ""

            # 메시지 (Semgrep message > rule description)
            message = result.get("message", {}).get("text", "") or meta.get("description", "")

            findings.append({
                "severity": severity,
                "rule_id": rule_id,
                "file": file_path,
                "line": start_line,
                "snippet": snippet,
                "message": message,
            })

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 99), f["file"], f["line"]))
    return findings


def load_secret_findings(secrets_path: str) -> list[dict]:
    """시크릿 스캔 결과를 findings 형식으로 변환한다."""
    if not os.path.exists(secrets_path):
        return []
    with open(secrets_path) as f:
        data = json.load(f)

    findings: list[dict] = []
    for s in data.get("secrets", []):
        findings.append({
            "severity": "CRITICAL",
            "rule_id": s.get("type", "hardcoded_secret"),
            "file": s.get("file", ""),
            "line": s.get("line", 0),
            "snippet": s.get("match", ""),
            "message": f"하드코딩된 시크릿 ({s.get('name', s.get('type', 'secret'))}) — 환경 변수나 시크릿 매니저로 이동하세요",
        })
    return findings


def group_findings(findings: list[dict]) -> list[dict]:
    """같은 file:line의 findings를 그룹핑한다. 최고 severity 대표 1건 + related count."""
    groups: dict[str, list[dict]] = {}
    for f in findings:
        key = f"{f['file']}:{f['line']}" if f["file"] else f["rule_id"]
        groups.setdefault(key, []).append(f)

    grouped: list[dict] = []
    for _key, group in groups.items():
        # severity 순 정렬, 최고 severity가 대표
        group.sort(key=lambda x: SEVERITY_ORDER.get(x["severity"], 99))
        primary = dict(group[0])
        related = len(group) - 1
        if related > 0:
            primary["related_count"] = related
        grouped.append(primary)

    grouped.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 99), f["file"], f["line"]))
    return grouped


def format_findings_section(findings: list[dict]) -> str:
    """취약점 상세 목록을 마크다운으로 포맷한다. 같은 위치의 중복 탐지는 그룹핑."""
    if not findings:
        return ""

    grouped = group_findings(findings)
    shown = grouped[:MAX_FINDINGS]
    remaining = len(grouped) - len(shown)

    lines = ["", "### 발견된 취약점", ""]
    for f in shown:
        emoji = SEVERITY_EMOJI.get(f["severity"], "\u26aa")
        location = ""
        if f["file"]:
            location = f"  `{f['file']}"
            if f["line"]:
                location += f":{f['line']}"
            location += "`"

        # 관련 탐지 수
        related = f.get("related_count", 0)
        related_tag = f" (+{related}건 관련 탐지)" if related > 0 else ""

        # 첫 줄: severity + rule ID + 위치 + related
        lines.append(f"**{emoji} {f['severity']}** — `{f['rule_id']}`{location}{related_tag}")

        # 메시지 (한 줄로 축약, 200자 제한)
        msg = f["message"].replace("\n", " ").strip()
        if len(msg) > 200:
            msg = msg[:197] + "..."
        if msg:
            lines.append(f"> {msg}")

        # 코드 스니펫 (있으면)
        if f["snippet"]:
            snippet_line = f["snippet"].split("\n")[0][:120]
            lines.append(f"> ```\n> {snippet_line}\n> ```")

        lines.append("")

    if remaining > 0:
        lines.append(f"<sub>외 {remaining}건 생략</sub>")
        lines.append("")

    return "\n".join(lines)


def build_comment_body(score: dict, sarif_path: str = "/tmp/sast.sarif",
                       secrets_path: str = "/tmp/secrets.json",
                       stack_path: str = "/tmp/stack.json") -> str:
    points = score["score"]
    grade = score["grade"]
    domain = score["domain"]
    certified = score.get("certified", False)
    block_reason = score.get("certified_block_reason") or ""

    # 스택 정보 로드 (프레임워크 충돌 필터링용)
    detected_stack: list[str] = []
    if os.path.exists(stack_path):
        try:
            with open(stack_path) as f:
                detected_stack = json.load(f).get("detected_stack", [])
        except (json.JSONDecodeError, OSError):
            pass

    # 필터링된 findings에서 실제 카운트 산출 (raw score.json 대신)
    all_findings = load_secret_findings(secrets_path) + load_sarif_findings(sarif_path, detected_stack)
    all_findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 99), f["file"], f["line"]))

    filtered_counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for finding in all_findings:
        sev = finding["severity"]
        if sev in filtered_counts:
            filtered_counts[sev] += 1
    critical = filtered_counts["CRITICAL"]
    high = filtered_counts["HIGH"]
    medium = filtered_counts["MEDIUM"]
    low = filtered_counts["LOW"]
    total = sum(filtered_counts.values())

    grade_emoji = {"A": "\U0001f7e2", "B": "\U0001f7e1", "C": "\U0001f7e0", "D": "\U0001f534", "F": "\U0001f534"}.get(grade, "\u26aa")
    cert_badge = " \u2705 **Certified**" if certified else ""
    cert_block = f"\n> 인증 불가: {block_reason}" if block_reason else ""

    if critical > 0:
        summary = f"Critical 취약점 {critical}개 발견 — 즉시 수정 필요"
    elif high > 0:
        summary = f"High 취약점 {high}개 발견 — 머지 전 수정 권장"
    elif medium > 0:
        summary = f"Medium 취약점 {medium}개 발견"
    elif low > 0:
        summary = f"Low 취약점 {low}개"
    else:
        summary = "취약점 미발견"

    lines = [
        "## \U0001f510 VibeSafe 보안 스캔 결과",
        "",
        f"{grade_emoji} **{points}/100** (등급 {grade}){cert_badge}",
        cert_block,
        "",
        f"> {summary}",
        "",
        "| 심각도 | 건수 |",
        "|--------|------|",
        f"| \U0001f534 Critical | {critical} |",
        f"| \U0001f7e0 High     | {high} |",
        f"| \U0001f7e1 Medium   | {medium} |",
        f"| \U0001f7e2 Low      | {low} |",
        "",
        f"도메인: `{domain}` · 총 {total}건",
    ]
    details = format_findings_section(all_findings)
    if details:
        lines.append(details)

    lines.extend([
        "",
        "<sub>Powered by [VibeSafe](https://vibesafe.dev)</sub>",
    ])
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

    sarif_path = os.environ.get("VIBESAFE_SARIF", "/tmp/sast.sarif")
    secrets_path = os.environ.get("VIBESAFE_SECRETS", "/tmp/secrets.json")
    body = build_comment_body(score, sarif_path, secrets_path)
    post_or_update_comment(token, repo, pr_number, body)


if __name__ == "__main__":
    main()
