from __future__ import annotations
#!/usr/bin/env python3
"""
tools/report/pdf_generator.py
스캔 결과를 바이브 코더가 이해할 수 있는 보안 리포트로 변환한다.
HTML, PDF, JSON 형식을 지원한다.
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# ─── 등급별 색상 ─────────────────────────────────────────
GRADE_COLORS = {"A": "#22c55e", "B": "#84cc16", "C": "#eab308", "D": "#f97316", "F": "#ef4444"}
SEVERITY_COLORS = {"critical": "#7f1d1d", "high": "#ef4444", "medium": "#f97316", "low": "#eab308", "info": "#6b7280"}
SEVERITY_LABELS_KO = {"critical": "치명적", "high": "높음", "medium": "보통", "low": "낮음", "info": "정보"}


def format_regulation_status(compliance_data: dict) -> str:
    """규제 준수 현황을 HTML로 렌더링한다."""
    if not compliance_data:
        return "<p>규제 정보 없음</p>"

    sections = []
    for reg_name, reg_info in compliance_data.get("results", {}).items():
        status_badge = "✅ 준수" if reg_info["compliant"] else "❌ 미준수"
        color = "#22c55e" if reg_info["compliant"] else "#ef4444"

        req_rows = ""
        for req in reg_info.get("requirements", []):
            req_status = "✅" if req["compliant"] else "❌"
            penalty_html = f'<span style="color:#ef4444;font-size:12px">{req["penalty"]}</span>' if req.get("penalty") else ""
            req_rows += f"""
            <tr>
                <td>{req_status} {req['id']}</td>
                <td>{req['name']}</td>
                <td>{penalty_html}</td>
            </tr>"""

        sections.append(f"""
        <div class="regulation-card">
            <div class="regulation-header">
                <span class="regulation-name">{reg_name}</span>
                <span class="regulation-status" style="color:{color}">{status_badge}</span>
                <span class="regulation-pass-rate">{reg_info['pass_rate']}</span>
            </div>
            <table class="requirement-table">
                <thead><tr><th>요구사항 ID</th><th>내용</th><th>미준수 시 결과</th></tr></thead>
                <tbody>{req_rows}</tbody>
            </table>
        </div>""")

    return "\n".join(sections)


def format_vulnerability_list(vulnerabilities: list[dict], patches: list[dict]) -> str:
    """취약점 목록을 HTML로 렌더링한다."""
    if not vulnerabilities:
        return "<p style='color:#22c55e'>✅ 발견된 취약점이 없습니다.</p>"

    patch_map = {p.get("vuln_id"): p for p in patches}
    sections = []

    for vuln in vulnerabilities:
        severity = vuln.get("severity", "info").lower()
        color = SEVERITY_COLORS.get(severity, "#6b7280")
        label = SEVERITY_LABELS_KO.get(severity, severity)
        vuln_id = vuln.get("vuln_id", "")
        patch = patch_map.get(vuln_id, {})

        patch_button = ""
        if patch.get("patch_available"):
            patch_button = f'<button class="patch-btn" data-vuln-id="{vuln_id}">🔧 원클릭 수정</button>'

        ai_button = ""
        if patch.get("ai_prompt"):
            ai_button = f'<button class="ai-btn" onclick="copyToClipboard(\'{vuln_id}\')">🤖 AI 프롬프트 복사</button>'
            ai_button += f'<textarea id="prompt-{vuln_id}" style="display:none">{patch["ai_prompt"]}</textarea>'

        sections.append(f"""
        <div class="vuln-card" style="border-left: 4px solid {color}">
            <div class="vuln-header">
                <span class="severity-badge" style="background:{color}">{label}</span>
                <span class="vuln-title">{vuln.get('name', vuln.get('type', '알 수 없는 취약점'))}</span>
                <span class="vuln-location">{vuln.get('file', '')}:{vuln.get('line', '')}</span>
            </div>
            <p class="vuln-simple">{vuln.get('description_simple', vuln.get('description', ''))}</p>
            <details>
                <summary>기술적 상세 보기</summary>
                <p class="vuln-technical">{vuln.get('description', '')}</p>
            </details>
            <div class="vuln-actions">
                {patch_button}
                {ai_button}
            </div>
        </div>""")

    return "\n".join(sections)


def generate_html_report(
    scan_id: str,
    score_data: dict,
    compliance_data: dict,
    vulnerabilities: list[dict],
    patches: list[dict],
    language: str = "ko",
) -> str:
    """전체 HTML 리포트를 생성한다."""
    grade = score_data.get("grade", "F")
    score = score_data.get("score", 0)
    grade_color = GRADE_COLORS.get(grade, "#ef4444")

    generated_at = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")

    return f"""<!DOCTYPE html>
<html lang="{language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VibeSafe 보안 리포트 — {scan_id}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; line-height: 1.6; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 32px 16px; }}
        .header {{ text-align: center; margin-bottom: 48px; }}
        .score-circle {{ width: 160px; height: 160px; border-radius: 50%; border: 8px solid {grade_color}; display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 0 auto 16px; }}
        .score-number {{ font-size: 48px; font-weight: 900; color: {grade_color}; }}
        .score-grade {{ font-size: 20px; color: {grade_color}; }}
        .score-summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 32px 0; }}
        .score-card {{ background: #1e293b; border-radius: 12px; padding: 16px; text-align: center; }}
        .score-card .count {{ font-size: 32px; font-weight: 700; }}
        .score-card .label {{ font-size: 12px; color: #94a3b8; margin-top: 4px; }}
        .section {{ margin: 48px 0; }}
        .section h2 {{ font-size: 20px; font-weight: 700; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #334155; }}
        .regulation-card {{ background: #1e293b; border-radius: 12px; padding: 16px; margin: 12px 0; }}
        .regulation-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; font-weight: 600; }}
        .regulation-pass-rate {{ margin-left: auto; color: #94a3b8; font-size: 14px; }}
        .requirement-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        .requirement-table th {{ text-align: left; padding: 8px; background: #0f172a; color: #94a3b8; }}
        .requirement-table td {{ padding: 8px; border-top: 1px solid #334155; }}
        .vuln-card {{ background: #1e293b; border-radius: 12px; padding: 16px; margin: 12px 0; }}
        .vuln-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }}
        .severity-badge {{ padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; color: white; }}
        .vuln-title {{ font-weight: 600; }}
        .vuln-location {{ margin-left: auto; color: #94a3b8; font-size: 12px; font-family: monospace; }}
        .vuln-simple {{ color: #cbd5e1; margin-bottom: 8px; }}
        .vuln-technical {{ color: #94a3b8; font-size: 13px; margin-top: 8px; }}
        details summary {{ cursor: pointer; color: #60a5fa; font-size: 13px; margin: 4px 0; }}
        .vuln-actions {{ margin-top: 12px; display: flex; gap: 8px; }}
        .patch-btn {{ background: #3b82f6; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }}
        .ai-btn {{ background: #8b5cf6; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }}
        .footer {{ text-align: center; color: #475569; font-size: 12px; margin-top: 64px; padding-top: 16px; border-top: 1px solid #334155; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="font-size:28px;font-weight:900;margin-bottom:8px">🛡️ VibeSafe 보안 리포트</h1>
            <p style="color:#94a3b8">스캔 ID: {scan_id} | {generated_at}</p>
            <div class="score-circle">
                <div class="score-number">{score}</div>
                <div class="score-grade">등급 {grade}</div>
            </div>
        </div>

        <div class="score-summary">
            <div class="score-card">
                <div class="count" style="color:#7f1d1d">{score_data.get('critical', 0)}</div>
                <div class="label">치명적</div>
            </div>
            <div class="score-card">
                <div class="count" style="color:#ef4444">{score_data.get('high', 0)}</div>
                <div class="label">높음</div>
            </div>
            <div class="score-card">
                <div class="count" style="color:#f97316">{score_data.get('medium', 0)}</div>
                <div class="label">보통</div>
            </div>
            <div class="score-card">
                <div class="count" style="color:#eab308">{score_data.get('low', 0)}</div>
                <div class="label">낮음</div>
            </div>
        </div>

        <div class="section">
            <h2>📋 규제 준수 현황</h2>
            {format_regulation_status(compliance_data)}
        </div>

        <div class="section">
            <h2>🔍 취약점 목록 (우선순위순)</h2>
            {format_vulnerability_list(vulnerabilities, patches)}
        </div>

        <div class="footer">
            <p>VibeSafe — 바이브 코더를 위한 보안 스캐닝 서비스 | 이 리포트는 자동 생성되었으며 전문 보안 감사를 대체하지 않습니다.</p>
        </div>
    </div>

    <script>
        function copyToClipboard(vulnId) {{
            const textarea = document.getElementById('prompt-' + vulnId);
            if (textarea) {{
                navigator.clipboard.writeText(textarea.value).then(() => alert('AI 프롬프트가 복사되었습니다! Cursor, v0, Replit에 붙여넣기 하세요.'));
            }}
        }}
    </script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="VibeSafe 리포트 생성기")
    parser.add_argument("--scan-id", required=True)
    parser.add_argument("--format", choices=["html", "pdf", "json"], default="html")
    parser.add_argument("--language", default="ko")
    parser.add_argument("--output", required=True, help="출력 파일 경로")
    parser.add_argument("--score-file", help="점수 JSON 파일")
    parser.add_argument("--compliance-file", help="규제 준수 JSON 파일")
    parser.add_argument("--vulns-file", help="취약점 JSON 파일")
    parser.add_argument("--patches-file", help="패치 JSON 파일")
    args = parser.parse_args()

    # 데이터 로드
    score_data = json.loads(Path(args.score_file).read_text()) if args.score_file and Path(args.score_file).exists() else {}
    compliance_data = json.loads(Path(args.compliance_file).read_text()) if args.compliance_file and Path(args.compliance_file).exists() else {}
    vulns_data = json.loads(Path(args.vulns_file).read_text()) if args.vulns_file and Path(args.vulns_file).exists() else {}
    patches_data = json.loads(Path(args.patches_file).read_text()) if args.patches_file and Path(args.patches_file).exists() else {}

    vulnerabilities = vulns_data.get("vulnerabilities", []) if isinstance(vulns_data, dict) else vulns_data
    patches = patches_data.get("patches", []) if isinstance(patches_data, dict) else patches_data

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format in ("html", "pdf"):
        html = generate_html_report(
            scan_id=args.scan_id,
            score_data=score_data,
            compliance_data=compliance_data,
            vulnerabilities=vulnerabilities,
            patches=patches,
            language=args.language,
        )
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html, encoding="utf-8")

        if args.format == "pdf":
            try:
                import subprocess
                subprocess.run(
                    ["chromium", "--headless", "--disable-gpu", f"--print-to-pdf={output_path}", str(html_path)],
                    check=True, capture_output=True
                )
            except (FileNotFoundError, subprocess.CalledProcessError):
                # Chromium 없으면 HTML만 저장
                print(json.dumps({"warning": "Chromium이 없어 HTML 형식으로 저장되었습니다", "output": str(html_path)}))
                sys.exit(0)

    elif args.format == "json":
        combined = {
            "scan_id": args.scan_id,
            "score": score_data,
            "compliance": compliance_data,
            "vulnerabilities": vulnerabilities,
            "patches": patches,
        }
        output_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2))

    print(json.dumps({"status": "ok", "output": str(output_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
