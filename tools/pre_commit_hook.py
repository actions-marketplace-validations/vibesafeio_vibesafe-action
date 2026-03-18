#!/usr/bin/env python3
from __future__ import annotations
"""
tools/pre_commit_hook.py
VibeSafe pre-commit hook — git commit 전에 로컬에서 보안 스캔을 실행한다.

설치:
  cp tools/pre_commit_hook.py .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit

또는 vibesafe CLI로:
  vibesafe install-hook

변경된 파일만 스캔하여 빠르게 피드백한다.
Critical/High 취약점이 있으면 commit을 차단한다.
"""

import json
import subprocess
import sys
from pathlib import Path


def get_staged_files() -> list[str]:
    """git에 staged된 파일 목록을 반환한다."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True,
    )
    return [f for f in result.stdout.strip().split("\n") if f]


def filter_scannable(files: list[str]) -> list[str]:
    """스캔 가능한 파일만 필터링한다."""
    scannable_ext = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".php", ".kt"}
    return [f for f in files if Path(f).suffix.lower() in scannable_ext]


def run_secret_scan(files: list[str]) -> list[dict]:
    """변경된 파일에서 시크릿을 스캔한다."""
    findings = []
    try:
        # vibesafe의 secret_scanner를 직접 import
        from tools.scanner.secret_scanner import scan_file
        for f in files:
            path = Path(f)
            if path.exists():
                results = scan_file(path)
                for r in results:
                    findings.append({
                        "severity": "CRITICAL",
                        "file": f,
                        "line": r.get("line", 0),
                        "message": f"하드코딩된 시크릿: {r.get('name', r.get('type', 'secret'))}",
                    })
    except ImportError:
        # standalone 모드: secret_scanner가 없으면 스킵
        pass
    return findings


def run_semgrep_scan(files: list[str]) -> list[dict]:
    """변경된 파일에 대해 Semgrep을 실행한다."""
    findings = []

    # semgrep이 설치되어 있는지 확인
    try:
        subprocess.run(["semgrep", "--version"], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("[VibeSafe] semgrep not installed, skipping SAST scan")
        return findings

    # 변경된 파일만 대상으로 스캔
    cmd = [
        "semgrep",
        "--config", "p/owasp-top-ten",
        "--json",
        "--quiet",
        "--timeout", "30",
    ] + files

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60,
        )
        if result.stdout:
            data = json.loads(result.stdout)
            severity_map = {"ERROR": "HIGH", "WARNING": "MEDIUM", "INFO": "LOW"}
            for r in data.get("results", []):
                sev = severity_map.get(r.get("extra", {}).get("severity", "").upper(), "MEDIUM")
                findings.append({
                    "severity": sev,
                    "file": r.get("path", ""),
                    "line": r.get("start", {}).get("line", 0),
                    "message": r.get("extra", {}).get("message", r.get("check_id", "")),
                })
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        print("[VibeSafe] semgrep scan timed out or failed")

    return findings


def main() -> int:
    staged = get_staged_files()
    scannable = filter_scannable(staged)

    if not scannable:
        return 0  # 스캔할 파일 없음

    print(f"[VibeSafe] 보안 스캔 중... ({len(scannable)} files)")

    all_findings: list[dict] = []
    all_findings.extend(run_secret_scan(scannable))
    all_findings.extend(run_semgrep_scan(scannable))

    if not all_findings:
        print("[VibeSafe] ✅ 보안 이슈 없음")
        return 0

    # 결과 출력
    critical_high = [f for f in all_findings if f["severity"] in ("CRITICAL", "HIGH")]
    medium_low = [f for f in all_findings if f["severity"] not in ("CRITICAL", "HIGH")]

    print(f"\n[VibeSafe] 🔍 {len(all_findings)}건 발견")
    for f in all_findings:
        emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(f["severity"], "⚪")
        loc = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
        msg = f["message"][:100]
        print(f"  {emoji} {f['severity']}: {loc}")
        print(f"     {msg}")

    if critical_high:
        print(f"\n[VibeSafe] ❌ Critical/High {len(critical_high)}건 — commit 차단")
        print("[VibeSafe] 수정 후 다시 시도하세요. 강제 커밋: git commit --no-verify")
        return 1
    else:
        print(f"\n[VibeSafe] ⚠️ Medium/Low {len(medium_low)}건 — commit 허용 (수정 권장)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
