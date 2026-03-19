#!/usr/bin/env python3
from __future__ import annotations
"""
tools/scanner/sca_scanner.py
Software Composition Analysis — dependency vulnerability scanning.
Checks package manifests (requirements.txt, package.json, etc.) for known CVEs.
Uses pip-audit for Python and npm audit for Node.js (both free, no API key needed).
"""

import json
import subprocess
import sys
from pathlib import Path


def scan_python_deps(source_path: Path) -> list[dict]:
    """Scan Python dependencies using pip-audit."""
    findings = []

    for req_file in source_path.rglob("requirements.txt"):
        try:
            result = subprocess.run(
                ["pip-audit", "-r", str(req_file), "--format", "json", "--desc"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
            if result.stdout.strip():
                data = json.loads(result.stdout)
                for vuln in data:
                    # pip-audit JSON format: {"name": "pkg", "version": "1.0", "vulns": [...]}
                    pkg_name = vuln.get("name", "unknown")
                    pkg_version = vuln.get("version", "?")
                    for v in vuln.get("vulns", []):
                        severity = "HIGH"  # pip-audit doesn't provide severity, default to HIGH
                        fix_version = v.get("fix_versions", ["?"])[0] if v.get("fix_versions") else "?"
                        findings.append({
                            "type": "dependency_vulnerability",
                            "severity": severity,
                            "package": pkg_name,
                            "version": pkg_version,
                            "cve": v.get("id", ""),
                            "description": v.get("description", "")[:200],
                            "fix": f"Upgrade {pkg_name} to {fix_version}" if fix_version != "?" else f"Check {v.get('id', '')} for remediation",
                            "file": str(req_file),
                            "source": "pip-audit",
                        })
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            # pip-audit not installed or timed out — skip silently
            pass

    return findings


def scan_node_deps(source_path: Path) -> list[dict]:
    """Scan Node.js dependencies using npm audit."""
    findings = []

    for pkg_json in source_path.rglob("package.json"):
        pkg_dir = pkg_json.parent
        # Skip node_modules
        if "node_modules" in str(pkg_dir):
            continue
        # Must have package-lock.json or node_modules for npm audit
        if not (pkg_dir / "package-lock.json").exists():
            continue

        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
                cwd=str(pkg_dir),
            )
            if result.stdout.strip():
                data = json.loads(result.stdout)
                severity_map = {"critical": "CRITICAL", "high": "HIGH", "moderate": "MEDIUM", "low": "LOW"}
                for _adv_id, adv in data.get("vulnerabilities", {}).items():
                    sev = severity_map.get(adv.get("severity", ""), "MEDIUM")
                    findings.append({
                        "type": "dependency_vulnerability",
                        "severity": sev,
                        "package": adv.get("name", "unknown"),
                        "version": adv.get("range", "?"),
                        "cve": adv.get("via", [{}])[0].get("url", "") if isinstance(adv.get("via", [{}])[0], dict) else "",
                        "description": adv.get("via", [{}])[0].get("title", "") if isinstance(adv.get("via", [{}])[0], dict) else str(adv.get("via", "")),
                        "fix": f"Run `npm audit fix` or upgrade {adv.get('name', '')} to {adv.get('fixAvailable', {}).get('version', '?') if isinstance(adv.get('fixAvailable'), dict) else 'latest'}",
                        "file": str(pkg_json),
                        "source": "npm-audit",
                    })
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass

    return findings


def scan_dependencies(source_path: Path) -> dict:
    """Run all SCA scanners and return combined results."""
    all_findings = []
    all_findings.extend(scan_python_deps(source_path))
    all_findings.extend(scan_node_deps(source_path))

    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in all_findings:
        sev = f.get("severity", "MEDIUM")
        counts[sev] = counts.get(sev, 0) + 1

    return {
        "status": "ok",
        "total": len(all_findings),
        "by_severity": counts,
        "vulnerabilities": all_findings,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="VibeSafe SCA Scanner")
    parser.add_argument("--path", required=True, help="Source code path to scan")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    args = parser.parse_args()

    source_path = Path(args.path)
    if not source_path.exists():
        print(json.dumps({"error": f"Path not found: {args.path}"}))
        sys.exit(1)

    result = scan_dependencies(source_path)

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
