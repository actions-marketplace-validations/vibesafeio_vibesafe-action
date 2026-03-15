#!/usr/bin/env python3
"""
tools/infra/file_extractor.py
업로드된 파일(ZIP, TAR.GZ, 단일 소스파일)을 압축 해제하고 구조를 분석한다.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import tarfile
import zipfile
from pathlib import Path

MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500MB
MAX_FILE_COUNT = 10_000
DANGEROUS_EXTENSIONS = {".exe", ".sh", ".bat", ".ps1", ".com", ".scr"}


def validate_zip_bomb(path: Path) -> bool:
    """압축 해제 전 zip bomb 패턴 탐지."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            total_uncompressed = sum(info.file_size for info in zf.infolist())
            compressed_size = path.stat().st_size
            if compressed_size > 0 and total_uncompressed / compressed_size > 100:
                return False  # 100배 이상 팽창 = zip bomb 의심
    return True


def safe_extract_zip(zip_path: Path, output_dir: Path) -> list[str]:
    """경로 순회 공격(path traversal) 방지 ZIP 압축 해제."""
    extracted = []
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            member_path = output_dir / member.filename
            # 경로 순회 방지
            if not str(member_path.resolve()).startswith(str(output_dir.resolve())):
                raise ValueError(f"Path traversal detected: {member.filename}")
            # 심볼릭 링크 공격 방지
            if member.create_system == 3 and (member.external_attr >> 16) & 0xA000 == 0xA000:
                raise ValueError(f"Symlink detected: {member.filename}")
            zf.extract(member, output_dir)
            extracted.append(str(member_path))
    return extracted


def safe_extract_tar(tar_path: Path, output_dir: Path) -> list[str]:
    """경로 순회 공격 방지 TAR 압축 해제."""
    extracted = []
    with tarfile.open(tar_path) as tf:
        for member in tf.getmembers():
            member_path = output_dir / member.name
            if not str(member_path.resolve()).startswith(str(output_dir.resolve())):
                raise ValueError(f"Path traversal detected: {member.name}")
            if member.issym() or member.islnk():
                raise ValueError(f"Symlink detected: {member.name}")
            tf.extract(member, output_dir)
            extracted.append(str(member_path))
    return extracted


def analyze_structure(output_dir: Path) -> dict:
    """압축 해제된 디렉토리 구조를 분석하여 요약을 반환한다."""
    files = list(output_dir.rglob("*"))
    file_list = [f for f in files if f.is_file()]

    extensions = {}
    for f in file_list:
        ext = f.suffix.lower()
        extensions[ext] = extensions.get(ext, 0) + 1

    return {
        "total_files": len(file_list),
        "total_dirs": len([f for f in files if f.is_dir()]),
        "extension_counts": extensions,
        "top_level_entries": [e.name for e in output_dir.iterdir()],
    }


def compute_checksum(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="VibeSafe 파일 추출기")
    parser.add_argument("--input", required=True, help="업로드된 파일 경로")
    parser.add_argument("--output", required=True, help="압축 해제 대상 디렉토리")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    # --- 검증 ---
    if not input_path.exists():
        print(json.dumps({"error": f"파일을 찾을 수 없습니다: {args.input}"}))
        sys.exit(1)

    file_size = input_path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        print(json.dumps({"error": f"파일 크기 초과: {file_size / 1024 / 1024:.1f}MB (최대 500MB)"}))
        sys.exit(1)

    if not validate_zip_bomb(input_path):
        print(json.dumps({"error": "Zip bomb 패턴 감지. 처리를 중단합니다."}))
        sys.exit(1)

    output_path.mkdir(parents=True, exist_ok=True)

    # --- 압축 해제 ---
    try:
        suffix = input_path.suffix.lower()
        if suffix == ".zip":
            safe_extract_zip(input_path, output_path)
        elif suffix in (".gz", ".tgz") or input_path.name.endswith(".tar.gz"):
            safe_extract_tar(input_path, output_path)
        else:
            # 단일 소스 파일 → 그대로 복사
            import shutil
            shutil.copy2(input_path, output_path / input_path.name)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    # --- 파일 수 검증 ---
    structure = analyze_structure(output_path)
    if structure["total_files"] > MAX_FILE_COUNT:
        print(json.dumps({"error": f"파일 수 초과: {structure['total_files']}개 (최대 {MAX_FILE_COUNT}개)"}))
        sys.exit(1)

    result = {
        "status": "ok",
        "checksum": compute_checksum(input_path),
        "output_path": str(output_path),
        "structure": structure,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
