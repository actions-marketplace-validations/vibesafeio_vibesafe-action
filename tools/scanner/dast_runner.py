#!/usr/bin/env python3
"""
tools/scanner/dast_runner.py
OWASP ZAP 기반 동적 분석(DAST) 실행기.
Docker 샌드박스에서 실행 중인 앱을 대상으로 능동 스캔을 수행한다.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ZAP_DOCKER_IMAGE = "ghcr.io/zaproxy/zaproxy:stable"
DEFAULT_SCAN_TIMEOUT = 120  # 초


def wait_for_target(target_url: str, retries: int = 30, delay: int = 2) -> bool:
    """대상 URL이 응답할 때까지 대기한다."""
    import urllib.request
    import urllib.error
    for _ in range(retries):
        try:
            urllib.request.urlopen(target_url, timeout=3)
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(delay)
    return False


def run_zap_baseline_scan(target_url: str, output_file: Path, timeout: int = DEFAULT_SCAN_TIMEOUT) -> dict:
    """
    ZAP Baseline Scan — 수동 스파이더링 + 수동 규칙 검사.
    능동 공격 없이 빠르게 기초 취약점을 탐지한다.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "docker", "run", "--rm",
        "--network", "vibesafe_sandbox_net",
        "-v", f"{output_file.parent}:/zap/wrk:rw",
        ZAP_DOCKER_IMAGE,
        "zap-baseline.py",
        "-t", target_url,
        "-J", output_file.name,
        "-I",                   # 경고도 결과에 포함
        "-m", str(timeout // 60),  # 분 단위
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60)
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout[-2000:],  # 마지막 2KB만 보존
        "stderr": result.stderr[-1000:],
        "output_file": str(output_file),
    }


def run_zap_active_scan(target_url: str, output_file: Path, timeout: int = DEFAULT_SCAN_TIMEOUT) -> dict:
    """
    ZAP Full (Active) Scan — SQL Injection, XSS 등 능동 취약점 탐지.
    샌드박스 환경에서만 실행해야 한다.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "docker", "run", "--rm",
        "--network", "vibesafe_sandbox_net",
        "-v", f"{output_file.parent}:/zap/wrk:rw",
        ZAP_DOCKER_IMAGE,
        "zap-full-scan.py",
        "-t", target_url,
        "-J", output_file.name,
        "-I",
        "-m", str(timeout // 60),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 120)
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-1000:],
        "output_file": str(output_file),
    }


def parse_zap_json(output_file: Path) -> list[dict]:
    """ZAP JSON 결과를 표준 취약점 형식으로 파싱한다."""
    if not output_file.exists():
        return []

    data = json.loads(output_file.read_text())
    findings = []

    risk_map = {"High": "HIGH", "Medium": "MEDIUM", "Low": "LOW", "Informational": "INFO"}

    for alert in data.get("site", [{}])[0].get("alerts", []):
        severity = risk_map.get(alert.get("riskdesc", "").split(" ")[0], "INFO")
        for instance in alert.get("instances", [{}]):
            findings.append({
                "type": "dast_" + alert.get("alertRef", "unknown"),
                "name": alert.get("alert", "Unknown"),
                "severity": severity,
                "cvss_score": {"HIGH": 8.0, "MEDIUM": 5.5, "LOW": 2.0, "INFO": 0.0}.get(severity, 5.0),
                "url": instance.get("uri", ""),
                "method": instance.get("method", ""),
                "evidence": instance.get("evidence", "")[:200],
                "description": alert.get("desc", ""),
                "solution": alert.get("solution", ""),
                "reference": alert.get("reference", ""),
                "source": "dast",
            })

    return findings


def main():
    parser = argparse.ArgumentParser(description="VibeSafe DAST 실행기")
    parser.add_argument("--target", required=True, help="스캔 대상 URL (예: http://sandbox-xxx:3000)")
    parser.add_argument("--scan-type", choices=["baseline", "active"], default="baseline")
    parser.add_argument("--rules", help="도메인 규칙 ID (현재 미사용, 향후 ZAP 정책에 반영)")
    parser.add_argument("--output", required=True, help="결과 JSON 파일 저장 경로")
    parser.add_argument("--timeout", type=int, default=DEFAULT_SCAN_TIMEOUT)
    args = parser.parse_args()

    output_file = Path(args.output)

    # 대상 응답 대기
    print(f"대상 URL 응답 대기 중: {args.target}", file=sys.stderr)
    if not wait_for_target(args.target):
        print(json.dumps({"error": f"대상 URL에 접근할 수 없습니다: {args.target}"}))
        sys.exit(1)

    # ZAP 실행
    if args.scan_type == "active":
        scan_result = run_zap_active_scan(args.target, output_file, args.timeout)
    else:
        scan_result = run_zap_baseline_scan(args.target, output_file, args.timeout)

    # ZAP은 발견 시 exit code 2 반환
    if scan_result["exit_code"] not in (0, 2):
        print(json.dumps({"error": "ZAP 실행 실패", "details": scan_result["stderr"]}))
        sys.exit(1)

    findings = parse_zap_json(output_file)

    result = {
        "status": "ok",
        "scan_type": args.scan_type,
        "target": args.target,
        "total_findings": len(findings),
        "output_file": str(output_file),
        "vulnerabilities": findings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
