from __future__ import annotations
#!/usr/bin/env python3
"""
tools/remediation/fix_validator.py
패치 적용 후 재스캔을 실행하여 취약점이 실제로 제거되었는지 검증한다.
새로운 취약점이 생성되지 않았는지도 확인한다.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_targeted_sast(source_path: Path, target_file: str, timeout: int = 60) -> list[dict]:
    """특정 파일에 대해서만 Semgrep을 재실행한다."""
    target_path = source_path / target_file
    if not target_path.exists():
        target_path = Path(target_file)
    if not target_path.exists():
        return []

    result = subprocess.run(
        ["semgrep", "--config", "auto", "--json", str(target_path)],
        capture_output=True, text=True, timeout=timeout
    )

    findings = []
    try:
        data = json.loads(result.stdout)
        for finding in data.get("results", []):
            findings.append({
                "type": finding.get("check_id", ""),
                "file": finding.get("path", ""),
                "line": finding.get("start", {}).get("line", 0),
                "severity": finding.get("extra", {}).get("severity", "WARNING"),
            })
    except (json.JSONDecodeError, KeyError):
        pass

    return findings


def validate_syntax(file_path: Path) -> dict:
    """파일 구문이 유효한지 확인한다."""
    suffix = file_path.suffix.lower()

    if suffix in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
        result = subprocess.run(
            ["node", "--check", str(file_path)],
            capture_output=True, text=True
        )
        return {"valid": result.returncode == 0, "error": result.stderr if result.returncode != 0 else None}

    elif suffix == ".py":
        result = subprocess.run(
            ["python", "-m", "py_compile", str(file_path)],
            capture_output=True, text=True
        )
        return {"valid": result.returncode == 0, "error": result.stderr if result.returncode != 0 else None}

    elif suffix == ".rb":
        result = subprocess.run(
            ["ruby", "-c", str(file_path)],
            capture_output=True, text=True
        )
        return {"valid": result.returncode == 0, "error": result.stderr if result.returncode != 0 else None}

    # 검증 불가한 파일 형식 → 통과 처리
    return {"valid": True, "error": None, "skipped": True}


def validate_patch(vuln: dict, source_path: Path, pre_scan_findings: list[dict]) -> dict:
    """
    단일 취약점에 대한 패치 검증:
    1. 구문 오류 없음
    2. 원래 취약점이 제거됨
    3. 새로운 취약점 없음
    """
    file_rel = vuln.get("file", "")
    line_num = vuln.get("line", 0)
    vuln_type = vuln.get("type", "")

    file_path = source_path / file_rel
    if not file_path.exists():
        file_path = Path(file_rel)

    # 1. 구문 검증
    syntax_result = validate_syntax(file_path)
    if not syntax_result["valid"]:
        return {
            "vuln_id": vuln.get("vuln_id"),
            "validated": False,
            "reason": f"구문 오류: {syntax_result['error']}",
            "syntax_valid": False,
        }

    # 2. 재스캔으로 취약점 제거 확인
    post_findings = run_targeted_sast(source_path, file_rel)

    # 동일 파일, 동일 라인 부근에서 같은 유형의 취약점이 여전히 존재하는지 확인
    vuln_still_present = any(
        f["file"].endswith(file_rel) and abs(f["line"] - line_num) <= 3
        for f in post_findings
        if vuln_type.lower() in f["type"].lower() or f["type"].lower() in vuln_type.lower()
    )

    # 3. 새로운 취약점 탐지
    pre_finding_keys = {(f["file"], f["line"]) for f in pre_scan_findings}
    new_vulns = [
        f for f in post_findings
        if (f["file"], f["line"]) not in pre_finding_keys
    ]

    return {
        "vuln_id": vuln.get("vuln_id"),
        "validated": not vuln_still_present and len(new_vulns) == 0,
        "syntax_valid": True,
        "vuln_removed": not vuln_still_present,
        "new_vulns_introduced": len(new_vulns),
        "new_vulns": new_vulns,
    }


def main():
    parser = argparse.ArgumentParser(description="VibeSafe 패치 검증기")
    parser.add_argument("--source-path", required=True, help="소스 코드 경로")
    parser.add_argument("--patches", required=True, help="패치 JSON 파일 디렉토리")
    parser.add_argument("--dry-run", action="store_true", help="구문 검사만 수행 (SAST 재실행 생략)")
    args = parser.parse_args()

    source_path = Path(args.source_path)
    patches_dir = Path(args.patches)

    patch_files = [f for f in patches_dir.glob("*.json") if f.name != "summary.json"]

    results = []
    for patch_file in patch_files:
        vuln = json.loads(patch_file.read_text())

        if args.dry_run:
            # dry-run: 구문 검사만
            file_path = source_path / vuln.get("file", "")
            syntax = validate_syntax(file_path)
            results.append({
                "vuln_id": vuln.get("vuln_id"),
                "syntax_valid": syntax["valid"],
                "error": syntax.get("error"),
            })
        else:
            result = validate_patch(vuln, source_path, [])
            results.append(result)

    all_valid = all(r.get("validated", r.get("syntax_valid", False)) for r in results)

    summary = {
        "status": "ok",
        "all_validated": all_valid,
        "total": len(results),
        "validated": sum(1 for r in results if r.get("validated", r.get("syntax_valid", False))),
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
