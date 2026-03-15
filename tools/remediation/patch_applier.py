#!/usr/bin/env python3
"""
tools/remediation/patch_applier.py
생성된 unified diff 패치를 소스 코드에 적용한다.
적용 전 백업을 생성하고, 실패 시 자동 롤백한다.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def apply_patch(patch_content: str, source_path: Path, dry_run: bool = False) -> dict:
    """unified diff 패치를 적용한다."""
    if not patch_content or not patch_content.strip():
        return {"success": False, "reason": "패치 내용이 비어있습니다"}

    # 백업 생성
    backup_dir = source_path.parent / f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if not dry_run:
        shutil.copytree(source_path, backup_dir)

    # patch 명령어 실행
    cmd = ["patch", "--strip=1", "--directory", str(source_path)]
    if dry_run:
        cmd.append("--dry-run")

    result = subprocess.run(
        cmd,
        input=patch_content,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # 롤백
        if not dry_run and backup_dir.exists():
            shutil.rmtree(source_path)
            shutil.copytree(backup_dir, source_path)
            shutil.rmtree(backup_dir)
        return {
            "success": False,
            "reason": result.stderr,
            "stdout": result.stdout,
        }

    # 성공 시 백업 유지 (사용자가 수동 롤백 가능)
    return {
        "success": True,
        "dry_run": dry_run,
        "backup_path": str(backup_dir) if not dry_run else None,
        "output": result.stdout,
    }


def apply_patch_file(patch_json_path: Path, source_path: Path, dry_run: bool = False) -> dict:
    """패치 JSON 파일을 읽어 소스 코드에 적용한다."""
    patch_data = json.loads(patch_json_path.read_text())
    patch_content = patch_data.get("patch")

    if not patch_content:
        return {
            "vuln_id": patch_data.get("vuln_id"),
            "success": False,
            "reason": "이 취약점에 대한 자동 패치가 없습니다. AI 프롬프트를 사용하세요.",
            "ai_prompt": patch_data.get("ai_prompt"),
        }

    result = apply_patch(patch_content, source_path, dry_run)
    result["vuln_id"] = patch_data.get("vuln_id")
    result["type"] = patch_data.get("type")
    return result


def main():
    parser = argparse.ArgumentParser(description="VibeSafe 패치 적용기")
    parser.add_argument("--patches-dir", required=True, help="패치 JSON 파일들이 있는 디렉토리")
    parser.add_argument("--source-path", required=True, help="소스 코드 경로")
    parser.add_argument("--vuln-id", help="특정 취약점 ID만 적용 (생략 시 전체)")
    parser.add_argument("--dry-run", action="store_true", help="실제 적용 없이 가능 여부만 확인")
    args = parser.parse_args()

    patches_dir = Path(args.patches_dir)
    source_path = Path(args.source_path)

    if not patches_dir.exists():
        print(json.dumps({"error": f"패치 디렉토리를 찾을 수 없습니다: {args.patches_dir}"}))
        sys.exit(1)

    # 적용할 패치 파일 수집
    if args.vuln_id:
        patch_files = [patches_dir / f"{args.vuln_id}.json"]
    else:
        patch_files = [f for f in patches_dir.glob("*.json") if f.name != "summary.json"]

    results = []
    success_count = 0
    fail_count = 0

    for patch_file in patch_files:
        if not patch_file.exists():
            results.append({"file": str(patch_file), "success": False, "reason": "파일을 찾을 수 없습니다"})
            fail_count += 1
            continue

        result = apply_patch_file(patch_file, source_path, args.dry_run)
        results.append(result)
        if result["success"]:
            success_count += 1
        else:
            fail_count += 1

    summary = {
        "status": "ok",
        "dry_run": args.dry_run,
        "total": len(results),
        "success": success_count,
        "failed": fail_count,
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
