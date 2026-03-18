# VibeSafe MCP Server 설계

## 목표
Claude Code, Cursor 등 AI 코딩 에이전트에서 코드 작성 중 실시간 보안 검증.
PR 시점이 아닌 **코딩 시점**에 취약점을 잡는다 (Gap 4: 타이밍).

## MCP (Model Context Protocol) 개요
- Anthropic이 정의한 AI 에이전트 ↔ 외부 도구 연결 프로토콜
- Claude Code, Cursor 등에서 MCP 서버를 등록하면 AI가 도구로 호출 가능
- JSON-RPC 기반, stdio 또는 HTTP 전송

## 제공할 Tools

### 1. `vibesafe_scan_file`
단일 파일 보안 스캔. 에이전트가 코드 생성 후 즉시 호출.

```json
{
  "name": "vibesafe_scan_file",
  "description": "파일의 보안 취약점을 스캔합니다",
  "inputSchema": {
    "type": "object",
    "properties": {
      "file_path": {"type": "string", "description": "스캔할 파일 경로"},
      "content": {"type": "string", "description": "파일 내용 (선택, 없으면 디스크에서 읽음)"}
    },
    "required": ["file_path"]
  }
}
```

응답:
```json
{
  "findings": [
    {
      "severity": "HIGH",
      "line": 24,
      "rule": "sql-injection",
      "message": "f-string SQL 쿼리 사용",
      "fix": "파라미터화된 쿼리를 사용하세요"
    }
  ],
  "score": 45,
  "summary": "HIGH 2건, MEDIUM 1건 발견"
}
```

### 2. `vibesafe_scan_diff`
staged/unstaged 변경분만 스캔. commit 전 빠른 검증.

```json
{
  "name": "vibesafe_scan_diff",
  "description": "git diff의 변경된 코드만 보안 스캔합니다",
  "inputSchema": {
    "type": "object",
    "properties": {
      "staged_only": {"type": "boolean", "default": true}
    }
  }
}
```

### 3. `vibesafe_check_secret`
텍스트에서 시크릿 패턴을 검사. 에이전트가 코드에 시크릿을 넣으려 할 때 사전 차단.

```json
{
  "name": "vibesafe_check_secret",
  "description": "텍스트에 하드코딩된 시크릿이 있는지 검사합니다",
  "inputSchema": {
    "type": "object",
    "properties": {
      "text": {"type": "string", "description": "검사할 텍스트"}
    },
    "required": ["text"]
  }
}
```

## 아키텍처

```
AI Agent (Claude Code / Cursor)
    ↕ MCP Protocol (stdio)
vibesafe-mcp-server (Python)
    ↓
tools/scanner/secret_scanner.py   (시크릿)
tools/scanner/sast_runner.py      (SAST — semgrep 필요)
tools/report/score_calculator.py  (점수)
```

## 구현 방식
- Python + `mcp` SDK (`pip install mcp`)
- stdio 전송 (프로세스 기반, 설치 가장 간단)
- 의존성: mcp SDK + 기존 VibeSafe 도구

## 설치 (사용자 관점)

```bash
# Claude Code
claude mcp add vibesafe -- python /path/to/vibesafe/tools/mcp_server.py

# Cursor (.cursor/mcp.json)
{
  "mcpServers": {
    "vibesafe": {
      "command": "python",
      "args": ["/path/to/vibesafe/tools/mcp_server.py"]
    }
  }
}
```

## 사용 시나리오

1. **코드 생성 후 자동 검증**: AI가 코드를 작성한 직후 `vibesafe_scan_file` 호출 → 취약점 있으면 즉시 수정
2. **커밋 전 검증**: 사용자가 "커밋해줘" → AI가 `vibesafe_scan_diff` 호출 → Critical 있으면 경고
3. **시크릿 사전 차단**: AI가 환경변수 대신 리터럴 값을 넣으려 할 때 `vibesafe_check_secret`이 차단

## 구현 우선순위
1. `vibesafe_check_secret` — 가장 간단, 외부 의존성 없음
2. `vibesafe_scan_file` — semgrep 필요하지만 핵심 가치
3. `vibesafe_scan_diff` — git 연동 필요

## 차별점
- GitGuardian MCP: 시크릿 탐지 중심
- VibeSafe MCP: 시크릿 + SAST + 도메인별 규칙 + 점수 + 수정 제안
