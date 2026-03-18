#!/usr/bin/env python3
from __future__ import annotations
"""
tools/mcp_server.py
VibeSafe MCP Server — Claude Code / Cursor에서 실시간 보안 검증.

설치:
  claude mcp add vibesafe -- python /path/to/vibesafe/tools/mcp_server.py

  # Cursor (.cursor/mcp.json)
  {"mcpServers": {"vibesafe": {"command": "python", "args": ["/path/to/vibesafe/tools/mcp_server.py"]}}}
"""

import json
import sys
from pathlib import Path

# MCP SDK가 없으면 fallback 모드로 동작 (테스트용)
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

# VibeSafe 도구 import (같은 프로젝트 내)
TOOLS_DIR = Path(__file__).parent
sys.path.insert(0, str(TOOLS_DIR.parent))

from tools.scanner.secret_scanner import scan_file, scan_text
from tools.scanner.sast_runner import detect_stack


def check_secret(text: str) -> dict:
    """텍스트에서 시크릿 패턴을 검사한다."""
    findings = scan_text(text)
    return {
        "has_secrets": len(findings) > 0,
        "count": len(findings),
        "findings": [
            {
                "type": f["type"],
                "name": f["name"],
                "line": f.get("line", 0),
                "severity": "critical",
                "fix": f"Remove this {f['name']} from code. Use environment variables or a secret manager.",
            }
            for f in findings
        ],
    }


def scan_file_security(file_path: str, content: str | None = None) -> dict:
    """단일 파일의 보안 취약점을 스캔한다."""
    path = Path(file_path)

    # Secret scan
    if content:
        secret_findings = scan_text(content)
    elif path.exists():
        secret_findings = scan_file(path)
    else:
        secret_findings = []

    findings = []
    for f in secret_findings:
        findings.append({
            "severity": "CRITICAL",
            "type": "hardcoded_secret",
            "name": f["name"],
            "line": f.get("line", 0),
            "fix": f"Remove this {f['name']}. Use `os.environ.get()` or a secret manager.",
        })

    return {
        "file": file_path,
        "findings": findings,
        "total": len(findings),
        "summary": f"{len(findings)} issues found" if findings else "No issues found",
    }


if HAS_MCP:
    server = Server("vibesafe")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="vibesafe_check_secret",
                description="Check text for hardcoded secrets (API keys, tokens, passwords). Use this before writing code that contains credentials.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to check for secrets"},
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="vibesafe_scan_file",
                description="Scan a file for security vulnerabilities (hardcoded secrets, API keys). Returns findings with line numbers and fix suggestions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file to scan"},
                        "content": {"type": "string", "description": "File content (optional, reads from disk if omitted)"},
                    },
                    "required": ["file_path"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "vibesafe_check_secret":
            result = check_secret(arguments["text"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        elif name == "vibesafe_scan_file":
            result = scan_file_security(
                arguments["file_path"],
                arguments.get("content"),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    if __name__ == "__main__":
        import asyncio
        asyncio.run(main())

else:
    # Fallback: CLI 모드 (MCP SDK 없을 때 테스트용)
    if __name__ == "__main__":
        import argparse
        parser = argparse.ArgumentParser(description="VibeSafe MCP Server (CLI fallback)")
        parser.add_argument("--check-secret", help="Check text for secrets")
        parser.add_argument("--scan-file", help="Scan a file for vulnerabilities")
        args = parser.parse_args()

        if args.check_secret:
            print(json.dumps(check_secret(args.check_secret), indent=2))
        elif args.scan_file:
            print(json.dumps(scan_file_security(args.scan_file), indent=2))
        else:
            print("VibeSafe MCP Server")
            print("MCP SDK not installed. Install with: pip install mcp")
            print("CLI mode available: --check-secret TEXT or --scan-file PATH")
