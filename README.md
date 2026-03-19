# VibeSafe Security Scan · GitHub Action

> PR마다 자동으로 보안을 검사하고, 결과를 코멘트로 달아줍니다.

바이브 코딩(AI 생성 코드)에서 자주 나타나는 SQL Injection, XSS, 하드코딩된 API 키 등을 PR 단계에서 잡아냅니다.

---

## 실제 PR 코멘트 예시

**취약점 없음 — A등급 Certified**

![Clean result](./docs/screenshot-clean.png)

**취약점 발견 — F등급**

![Vulnerable result](./docs/screenshot-vuln.png)

---

## 설치 (30초)

`.github/workflows/vibesafe-scan.yml` 파일 하나 추가하면 끝입니다.

```yaml
name: VibeSafe Security Scan

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  vibesafe:
    name: Security Scan
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - name: Run VibeSafe scan
        uses: vibesafeio/vibesafe-action@v0
        with:
          domain: auto
```

PR 코멘트는 action이 자동으로 달아줍니다. 별도 설정 불필요.

---

## Why VibeSafe?

| | VibeSafe | Snyk | CodeQL | Dependabot |
|---|---|---|---|---|
| 설치 시간 | **30초** (YAML 복사) | 30분+ (계정+API키+CLI) | 15분+ (빌드 설정) | 자동 (PR만) |
| 비용 | **무료** | $35K~$90K/년 | 무료 (공개 레포) | 무료 |
| PR 코멘트 | **파일+줄+코드+수정가이드** | 파일+줄 | ❌ | ❌ |
| 바이브 코딩 최적화 | **도메인별 규칙** | ❌ | ❌ | ❌ |
| 시크릿 스캔 | ✅ | ✅ (유료) | ❌ | ❌ |

VibeSafe는 바이브 코더를 위해 만들어졌습니다. 보안팀이 없어도, 24줄이면 충분합니다.

### 공인 벤치마크: OWASP Juice Shop

[OWASP Juice Shop](https://github.com/juice-shop/juice-shop)은 의도적으로 취약하게 만든 공인 테스트 앱입니다.

| 항목 | 결과 |
|------|------|
| 스택 탐지 | Express + Socket.io (JS/TS/Python) |
| SAST 취약점 | 18건 (High 7 + Medium 11) |
| 노출된 시크릿 | 18건 (JWT 토큰 9 + Supabase 키 9) |
| **총 탐지** | **36건** |
| **점수** | **0/100 F등급** |

---

## 무엇을 검사하나요

| 항목 | 내용 |
|------|------|
| **SAST** | SQL Injection, XSS, SSRF, IDOR, Command Injection 등 OWASP Top 10 |
| **시크릿 탐지** | API 키, GitHub 토큰, Stripe 키, AWS 자격증명 하드코딩 |
| **도메인별 규칙** | 서비스 유형에 맞는 보안 규칙 자동 선택 |

지원 언어: JavaScript · TypeScript · Python · Java · Go · Ruby · PHP · Kotlin

---

## 도메인 옵션

```yaml
domain: auto        # 코드를 분석해서 자동 분류 (기본값)
domain: ecommerce   # 결제/주문 — PCI DSS 룰 강화
domain: fintech     # 계좌/송금 — 전자금융거래법, AML
domain: healthcare  # 환자정보 — HIPAA, 개인정보보호법
domain: platform    # SaaS/멀티테넌트 — JWT, RBAC
domain: game        # 게임서버 — WebSocket, 클라이언트 조작
domain: education   # 학생정보 — FERPA, COPPA
```

---

## 점수 기준

| 등급 | 점수 | 의미 |
|------|------|------|
| 🟢 **A** + ✅ Certified | 85 ~ 100 | Critical · High 0개 |
| 🟢 **A** | 85 ~ 100 | 양호 |
| 🟡 **B** | 70 ~ 84 | 경미한 취약점 |
| 🟠 **C** | 50 ~ 69 | Medium 취약점 다수 |
| 🔴 **D / F** | 0 ~ 49 | Critical · High 존재 |

**✅ Certified** 배지는 Critical 0 + High 0 + 점수 85 이상일 때 발급됩니다.

---

## Outputs

다른 step에서 결과를 활용할 수 있습니다.

```yaml
- run: echo "Score: ${{ steps.vibesafe.outputs.score }}"
```

| output | 설명 | 예시 |
|--------|------|------|
| `score` | 보안 점수 | `82` |
| `grade` | 등급 | `B` |
| `domain` | 감지된 도메인 | `fintech` |
| `certified` | Certified 여부 | `true` |
| `critical` | Critical 취약점 수 | `0` |
| `high` | High 취약점 수 | `2` |
| `medium` | Medium 취약점 수 | `5` |
| `low` | Low 취약점 수 | `3` |
| `total` | 전체 취약점 수 | `10` |
| `certified_block_reason` | Certified 미발급 사유 | `high >= 1` |

---

## Merge Blocking

**By default, VibeSafe fails the check (exit 1) when critical vulnerabilities are found.** This means GitHub branch protection will block the merge automatically.

Configure the threshold with `fail-on`:

```yaml
- uses: vibesafeio/vibesafe-action@v0
  with:
    domain: auto
    fail-on: high     # Block on high or critical (default: critical)
    # fail-on: none   # Never block, comment only
```

| `fail-on` | Blocks merge when |
|-----------|-------------------|
| `critical` (default) | Critical >= 1 |
| `high` | High >= 1 or Critical >= 1 |
| `medium` | Medium >= 1 or above |
| `low` | Any finding |
| `none` | Never (comment only) |

To enable: `Settings → Branches → Branch protection rules → Require status checks` → add **`Security Scan`**

---

## Pre-commit Hook (선택)

커밋 전에 로컬에서 시크릿을 잡고 싶다면:

```bash
cp tools/pre_commit_hook.py .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

하드코딩된 API 키나 토큰이 staged 파일에 있으면 commit을 차단합니다. Semgrep이 설치되어 있으면 SAST도 함께 실행합니다.

강제 커밋: `git commit --no-verify`

---

## MCP Server — IDE 실시간 보안 검증 (선택)

Claude Code나 Cursor에서 코딩 중 실시간으로 시크릿을 감지합니다.

**Claude Code:**
```bash
claude mcp add vibesafe -- python /path/to/vibesafe/tools/mcp_server.py
```

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "vibesafe": {
      "command": "python",
      "args": ["/path/to/vibesafe/tools/mcp_server.py"]
    }
  }
}
```

AI 에이전트가 코드를 작성할 때 `vibesafe_check_secret`과 `vibesafe_scan_file` 도구를 사용하여 시크릿과 취약점을 즉시 감지합니다.

---

## FAQ

**Does my code leave my environment?**
No. All scanning runs inside the GitHub Actions runner. No code is sent to VibeSafe servers.

**How much does it cost?**
Free. Only consumes GitHub Actions minutes (~20 seconds per scan). Public repos have unlimited free minutes.

**What languages are supported?**
All languages supported by Semgrep — JavaScript/TypeScript, Python, Java, Go, Ruby, PHP, Kotlin, and more.

---

<sub>Powered by [VibeSafe](https://vibesafe.dev) · Built with [Semgrep](https://semgrep.dev)</sub>
