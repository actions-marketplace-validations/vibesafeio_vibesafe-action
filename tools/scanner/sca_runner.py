#!/usr/bin/env python3
"""
tools/scanner/sca_runner.py
의존성 취약점 스캐너 (SCA).
npm audit (Node.js), pip-audit (Python), bundle-audit (Ruby) 등을 실행하여
취약 패키지와 CVE 정보를 수집한다.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_npm_audit(project_path: Path) -> list[dict]:
    """package.json이 있는 디렉토리에서 npm audit을 실행한다."""
    pkg_files = list(project_path.rglob("package.json"))
    findings = []

    for pkg_file in pkg_files:
        if "node_modules" in pkg_file.parts:
            continue
        work_dir = pkg_file.parent
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True, text=True, cwd=work_dir
        )
        try:
            data = json.loads(result.stdout)
            vulns = data.get("vulnerabilities", {})
            for pkg_name, info in vulns.items():
                for via in info.get("via", []):
                    if isinstance(via, dict):
                        findings.append({
                            "package": pkg_name,
                            "ecosystem": "npm",
                            "severity": info.get("severity", "unknown"),
                            "cve": via.get("source", ""),
                            "title": via.get("title", ""),
                            "url": via.get("url", ""),
                            "installed_version": info.get("nodes", [""])[0],
                            "fixed_version": via.get("fixAvailable", {}).get("version") if isinstance(via.get("fixAvailable"), dict) else None,
                            "source_file": str(pkg_file),
                        })
        except (json.JSONDecodeError, KeyError):
            pass

    return findings


def run_pip_audit(project_path: Path) -> list[dict]:
    """requirements.txt 또는 pyproject.toml에서 pip-audit을 실행한다."""
    findings = []
    req_files = list(project_path.rglob("requirements.txt"))

    for req_file in req_files:
        result = subprocess.run(
            ["pip-audit", "--requirement", str(req_file), "--format", "json"],
            capture_output=True, text=True
        )
        try:
            data = json.loads(result.stdout)
            for dep in data.get("dependencies", []):
                for vuln in dep.get("vulns", []):
                    findings.append({
                        "package": dep.get("name"),
                        "ecosystem": "pypi",
                        "severity": vuln.get("fix_versions", ["unknown"])[0] if vuln.get("fix_versions") else "unknown",
                        "cve": vuln.get("id", ""),
                        "title": vuln.get("description", ""),
                        "url": f"https://osv.dev/vulnerability/{vuln.get('id', '')}",
                        "installed_version": dep.get("version"),
                        "fixed_version": vuln.get("fix_versions", [None])[0] if vuln.get("fix_versions") else None,
                        "source_file": str(req_file),
                    })
        except (json.JSONDecodeError, KeyError):
            pass

    return findings


def run_bundle_audit(project_path: Path) -> list[dict]:
    """Gemfile.lock에서 bundle-audit을 실행한다."""
    findings = []
    gemfiles = list(project_path.rglob("Gemfile.lock"))

    for gemfile in gemfiles:
        result = subprocess.run(
            ["bundle-audit", "check", "--format", "json"],
            capture_output=True, text=True, cwd=gemfile.parent
        )
        try:
            data = json.loads(result.stdout)
            for vuln in data.get("results", []):
                findings.append({
                    "package": vuln.get("gem", {}).get("name"),
                    "ecosystem": "rubygems",
                    "severity": vuln.get("criticality", "unknown"),
                    "cve": vuln.get("advisory", {}).get("cve", ""),
                    "title": vuln.get("advisory", {}).get("title", ""),
                    "url": vuln.get("advisory", {}).get("url", ""),
                    "installed_version": vuln.get("gem", {}).get("version"),
                    "fixed_version": vuln.get("advisory", {}).get("patched_versions", [None])[0],
                    "source_file": str(gemfile),
                })
        except (json.JSONDecodeError, KeyError):
            pass

    return findings


def calculate_cvss_from_severity(severity: str) -> float:
    """심각도 문자열에서 CVSS 점수 범위를 반환한다."""
    mapping = {"critical": 9.5, "high": 8.0, "moderate": 5.5, "medium": 5.5, "low": 2.0, "info": 0.0}
    return mapping.get(severity.lower(), 5.0)


def main():
    parser = argparse.ArgumentParser(description="VibeSafe SCA 스캐너")
    parser.add_argument("--path", required=True, help="스캔 대상 소스 코드 경로")
    parser.add_argument("--output", default=None, help="결과 JSON 파일 저장 경로")
    args = parser.parse_args()

    source_path = Path(args.path)
    if not source_path.exists():
        print(json.dumps({"error": f"경로를 찾을 수 없습니다: {args.path}"}))
        sys.exit(1)

    all_findings = []
    ecosystem_status = {}

    # npm audit
    try:
        npm_findings = run_npm_audit(source_path)
        all_findings.extend(npm_findings)
        ecosystem_status["npm"] = {"scanned": True, "count": len(npm_findings)}
    except FileNotFoundError:
        ecosystem_status["npm"] = {"scanned": False, "reason": "npm not installed"}

    # pip-audit
    try:
        pip_findings = run_pip_audit(source_path)
        all_findings.extend(pip_findings)
        ecosystem_status["pypi"] = {"scanned": True, "count": len(pip_findings)}
    except FileNotFoundError:
        ecosystem_status["pypi"] = {"scanned": False, "reason": "pip-audit not installed"}

    # bundle-audit
    try:
        ruby_findings = run_bundle_audit(source_path)
        all_findings.extend(ruby_findings)
        ecosystem_status["rubygems"] = {"scanned": True, "count": len(ruby_findings)}
    except FileNotFoundError:
        ecosystem_status["rubygems"] = {"scanned": False, "reason": "bundle-audit not installed"}

    # CVSS 점수 보강
    for finding in all_findings:
        if "cvss_score" not in finding:
            finding["cvss_score"] = calculate_cvss_from_severity(finding.get("severity", "medium"))

    result = {
        "status": "ok",
        "total_vulnerabilities": len(all_findings),
        "ecosystem_status": ecosystem_status,
        "vulnerabilities": all_findings,
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
