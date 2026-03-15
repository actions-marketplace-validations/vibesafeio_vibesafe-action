#!/usr/bin/env python3
"""
tools/infra/sandbox_manager.py
DAST용 Docker 샌드박스 생성 및 폐기를 관리한다.
네트워크 격리, 리소스 제한이 적용된 안전한 실행 환경을 제공한다.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time

SANDBOX_NETWORK = "vibesafe_sandbox_net"
SANDBOX_CPU_LIMIT = "1.0"
SANDBOX_MEMORY_LIMIT = "512m"
SCAN_TIMEOUT_SECONDS = 300
BASE_PORT = 13000  # sandbox-<scan_id>:3000 → 호스트 포트 13xxx


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def ensure_network():
    """격리 Docker 네트워크가 없으면 생성한다."""
    result = run_cmd(["docker", "network", "ls", "--filter", f"name={SANDBOX_NETWORK}", "--format", "{{.Name}}"], check=False)
    if SANDBOX_NETWORK not in result.stdout:
        run_cmd(["docker", "network", "create", "--internal", SANDBOX_NETWORK])


def create_sandbox(scan_id: str, source_path: str) -> dict:
    """
    소스 경로를 마운트하여 격리된 샌드박스 컨테이너를 생성한다.
    앱이 :3000에서 실행된다고 가정한다.
    """
    ensure_network()

    container_name = f"sandbox-{scan_id}"
    host_port = BASE_PORT + (int(scan_id[-4:], 16) % 1000 if len(scan_id) >= 4 else 0)

    cmd = [
        "docker", "run",
        "--detach",
        "--name", container_name,
        "--network", SANDBOX_NETWORK,
        "--cpus", SANDBOX_CPU_LIMIT,
        "--memory", SANDBOX_MEMORY_LIMIT,
        "--read-only",                          # 파일 시스템 읽기 전용
        "--no-new-privileges",                  # 권한 상승 차단
        "--security-opt", "no-new-privileges",
        "--tmpfs", "/tmp:size=64m",             # 임시 쓰기 영역만 허용
        "--volume", f"{source_path}:/app:ro",   # 소스 코드 읽기 전용 마운트
        "--publish", f"127.0.0.1:{host_port}:3000",
        "--label", f"vibesafe.scan_id={scan_id}",
        "node:20-alpine",
        "sh", "-c", "cd /app && npm install --production && npm start"
    ]

    result = run_cmd(cmd, check=False)
    if result.returncode != 0:
        return {"error": result.stderr, "container_name": container_name}

    # 앱 기동 대기 (최대 30초)
    for _ in range(30):
        health = run_cmd(
            ["docker", "inspect", "--format", "{{.State.Running}}", container_name],
            check=False
        )
        if health.stdout.strip() == "true":
            break
        time.sleep(1)

    return {
        "status": "created",
        "container_name": container_name,
        "target_url": f"http://127.0.0.1:{host_port}",
        "network": SANDBOX_NETWORK,
    }


def destroy_sandbox(scan_id: str) -> dict:
    """샌드박스 컨테이너를 강제 종료 및 삭제한다."""
    container_name = f"sandbox-{scan_id}"
    run_cmd(["docker", "rm", "--force", container_name], check=False)
    return {"status": "destroyed", "container_name": container_name}


def list_sandboxes() -> list[dict]:
    result = run_cmd(
        ["docker", "ps", "--filter", "label=vibesafe.scan_id", "--format", "{{.Names}}\t{{.Status}}\t{{.Labels}}"],
        check=False
    )
    sandboxes = []
    for line in result.stdout.strip().splitlines():
        if line:
            parts = line.split("\t")
            sandboxes.append({"name": parts[0], "status": parts[1] if len(parts) > 1 else "unknown"})
    return sandboxes


def main():
    parser = argparse.ArgumentParser(description="VibeSafe 샌드박스 관리자")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create", action="store_true", help="샌드박스 생성")
    group.add_argument("--destroy", action="store_true", help="샌드박스 삭제")
    group.add_argument("--list", action="store_true", help="실행 중인 샌드박스 목록")
    parser.add_argument("--scan-id", help="스캔 ID (create/destroy 시 필수)")
    parser.add_argument("--source-path", help="소스 코드 경로 (create 시 필수)")
    args = parser.parse_args()

    if args.create:
        if not args.scan_id or not args.source_path:
            print(json.dumps({"error": "--scan-id 와 --source-path 가 필요합니다"}))
            sys.exit(1)
        result = create_sandbox(args.scan_id, args.source_path)
    elif args.destroy:
        if not args.scan_id:
            print(json.dumps({"error": "--scan-id 가 필요합니다"}))
            sys.exit(1)
        result = destroy_sandbox(args.scan_id)
    else:
        result = list_sandboxes()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
