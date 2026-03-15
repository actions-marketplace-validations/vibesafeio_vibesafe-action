#!/usr/bin/env python3
from __future__ import annotations
"""
tools/scanner/sast_runner.py
Semgrep 기반 정적 분석(SAST) 실행기.
--detect-stack 모드: 기술 스택 자동 탐지
기본 모드: 지정 규칙셋으로 스캔 → SARIF 결과 파일 저장
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

STACK_MARKERS = {
    "nextjs":      ["next.config.js", "next.config.ts", "next.config.mjs"],
    "react":       ["package.json"],   # devDependencies 내 react 확인
    "vue":         ["vue.config.js"],
    "nuxt":        ["nuxt.config.js", "nuxt.config.ts"],
    "express":     ["package.json"],
    "fastapi":     ["requirements.txt", "pyproject.toml"],
    "django":      ["manage.py", "settings.py"],
    "flask":       ["requirements.txt"],
    "spring":      ["pom.xml", "build.gradle"],
    "laravel":     ["artisan"],
    "rails":       ["Gemfile"],
    "flutter":     ["pubspec.yaml"],
    "supabase":    ["package.json"],
    "prisma":      ["schema.prisma"],
    "stripe":      ["package.json"],
}

PACKAGE_SIGNALS = {
    "react":    ["react", "react-dom"],
    "nextjs":   ["next"],
    "express":  ["express"],
    "fastapi":  ["fastapi"],
    "flask":    ["flask"],
    "django":   ["django"],
    "supabase": ["@supabase/supabase-js", "supabase"],
    "prisma":   ["prisma", "@prisma/client"],
    "stripe":   ["stripe", "@stripe/stripe-js"],
    "socket.io": ["socket.io", "socket.io-client"],
}


def detect_stack(source_path: Path) -> dict:
    """파일 구조와 의존성 파일을 분석하여 기술 스택을 탐지한다."""
    detected = set()
    languages = set()

    # 언어 탐지
    for f in source_path.rglob("*"):
        if f.is_file():
            suffix = f.suffix.lower()
            if suffix in (".ts", ".tsx"):
                languages.add("typescript")
            elif suffix in (".js", ".jsx", ".mjs", ".cjs"):
                languages.add("javascript")
            elif suffix == ".py":
                languages.add("python")
            elif suffix in (".java", ".kt"):
                languages.add("java")
            elif suffix == ".go":
                languages.add("go")
            elif suffix == ".rb":
                languages.add("ruby")
            elif suffix == ".dart":
                languages.add("dart")
            elif suffix in (".css", ".scss", ".sass"):
                languages.add("css")

    # package.json 분석
    for pkg_file in source_path.rglob("package.json"):
        try:
            data = json.loads(pkg_file.read_text())
            all_deps = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }
            for tech, signals in PACKAGE_SIGNALS.items():
                if any(sig in all_deps for sig in signals):
                    detected.add(tech)
        except (json.JSONDecodeError, OSError):
            pass

    # requirements.txt 분석
    for req_file in source_path.rglob("requirements.txt"):
        try:
            content = req_file.read_text().lower()
            for line in content.splitlines():
                pkg = line.split("==")[0].split(">=")[0].strip()
                if pkg == "fastapi":
                    detected.add("fastapi")
                elif pkg == "flask":
                    detected.add("flask")
                elif pkg == "django":
                    detected.add("django")
        except OSError:
            pass

    # 특수 파일 존재 여부
    if (source_path / "schema.prisma").exists() or list(source_path.rglob("schema.prisma")):
        detected.add("prisma")
    if list(source_path.rglob("pubspec.yaml")):
        detected.add("flutter")
    if list(source_path.rglob("go.mod")):
        detected.add("go_modules")
        languages.add("go")

    return {
        "detected_stack": sorted(detected),
        "languages": sorted(languages),
    }


def run_semgrep(source_path: Path, rule_ids: list[str], output_file: Path, timeout: int = 180) -> dict:
    """Semgrep을 실행하고 SARIF 결과를 저장한다."""
    configs = rule_ids if rule_ids else ["auto"]
    cmd = ["semgrep"]
    for config in configs:
        cmd += ["--config", config]
    cmd += [
        "--sarif",
        "--output", str(output_file),
        "--timeout", str(timeout),
        "--max-memory", "2048",
        str(source_path),
    ]

    # stderr=STDOUT: Semgrep이 stderr를 pipe로 받으면 원격 규칙셋 로드에 실패(exit 7).
    # stderr를 stdout에 합쳐서 캡처하면 이 문제가 없다.
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout + 30,
    )

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stdout,   # merged; callers use stderr for error details
        "output_file": str(output_file),
    }


def parse_sarif_summary(sarif_file: Path) -> dict:
    """SARIF 결과 파일에서 발견된 취약점 수를 요약한다."""
    if not sarif_file.exists():
        return {"total": 0, "by_severity": {}}

    data = json.loads(sarif_file.read_text())
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}

    for run in data.get("runs", []):
        for result in run.get("results", []):
            level = result.get("level", "note").upper()
            severity_map = {"ERROR": "HIGH", "WARNING": "MEDIUM", "NOTE": "LOW", "NONE": "INFO"}
            severity = severity_map.get(level, "INFO")
            counts[severity] = counts.get(severity, 0) + 1

    return {
        "total": sum(counts.values()),
        "by_severity": counts,
    }


def main():
    parser = argparse.ArgumentParser(description="VibeSafe SAST 실행기")
    parser.add_argument("--path", required=True, help="스캔 대상 소스 코드 경로")
    parser.add_argument("--detect-stack", action="store_true", help="기술 스택 탐지 모드")
    parser.add_argument("--rules", help="적용할 Semgrep 규칙 ID (쉼표 구분)")
    parser.add_argument("--output", default=None, help="SARIF 결과 파일 경로")
    parser.add_argument("--timeout", type=int, default=180, help="스캔 타임아웃 (초)")
    args = parser.parse_args()

    source_path = Path(args.path)
    if not source_path.exists():
        print(json.dumps({"error": f"경로를 찾을 수 없습니다: {args.path}"}))
        sys.exit(1)

    if args.detect_stack:
        result = detect_stack(source_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # SAST 스캔 실행
    output_file = Path(args.output) if args.output else source_path.parent / "sast.sarif"
    rule_ids = [r.strip() for r in args.rules.split(",")] if args.rules else []

    scan_result = run_semgrep(source_path, rule_ids, output_file, args.timeout)

    if scan_result["exit_code"] not in (0, 1):  # semgrep: 0=clean, 1=findings, other=error
        print(json.dumps({"error": "Semgrep 실행 실패", "details": scan_result["stderr"]}))
        sys.exit(1)

    summary = parse_sarif_summary(output_file)
    result = {
        "status": "ok",
        "output_file": str(output_file),
        "summary": summary,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
