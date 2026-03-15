# VibeSafe Security Scan · GitHub Action

> PR마다 자동으로 보안을 검사하고, 결과를 코멘트로 달아줍니다.

바이브 코딩(AI 생성 코드)에서 자주 나타나는 SQL Injection, XSS, 하드코딩된 API 키 등을 PR 단계에서 잡아냅니다.

---

## 실제 PR 코멘트 예시

```
🔐 VibeSafe 보안 스캔 결과

🟢 100/100 (등급 A) ✅ Certified

> 취약점 미발견

| 심각도      | 건수 |
|-------------|------|
| 🔴 Critical |  0   |
| 🟠 High     |  0   |
| 🟡 Medium   |  0   |
| 🟢 Low      |  0   |

도메인: `platform` · 총 0건
```

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
    timeout-minutes: 15

    steps:
      - uses: actions/checkout@v4

      - name: Run VibeSafe scan
        id: vibesafe
        uses: vibesafeio/vibesafe-action@master
        with:
          domain: auto

      - name: Post PR comment
        uses: actions/github-script@v7
        env:
          VIBESAFE_SCORE: ${{ steps.vibesafe.outputs.score }}
          VIBESAFE_GRADE: ${{ steps.vibesafe.outputs.grade }}
          VIBESAFE_DOMAIN: ${{ steps.vibesafe.outputs.domain }}
          VIBESAFE_CERTIFIED: ${{ steps.vibesafe.outputs.certified }}
          VIBESAFE_CRITICAL: ${{ steps.vibesafe.outputs.critical }}
          VIBESAFE_HIGH: ${{ steps.vibesafe.outputs.high }}
          VIBESAFE_MEDIUM: ${{ steps.vibesafe.outputs.medium }}
          VIBESAFE_LOW: ${{ steps.vibesafe.outputs.low }}
          VIBESAFE_TOTAL: ${{ steps.vibesafe.outputs.total }}
          VIBESAFE_BLOCK_REASON: ${{ steps.vibesafe.outputs.certified_block_reason }}
        with:
          script: |
            const points    = parseInt(process.env.VIBESAFE_SCORE, 10);
            const grade     = process.env.VIBESAFE_GRADE;
            const domain    = process.env.VIBESAFE_DOMAIN;
            const certified = process.env.VIBESAFE_CERTIFIED === 'true';
            const critical  = parseInt(process.env.VIBESAFE_CRITICAL, 10);
            const high      = parseInt(process.env.VIBESAFE_HIGH, 10);
            const medium    = parseInt(process.env.VIBESAFE_MEDIUM, 10);
            const low       = parseInt(process.env.VIBESAFE_LOW, 10);
            const total     = parseInt(process.env.VIBESAFE_TOTAL, 10);
            const blockReason = process.env.VIBESAFE_BLOCK_REASON || '';
            const gradeEmoji = {A:'🟢',B:'🟡',C:'🟠',D:'🔴',F:'🔴'}[grade]||'⚪';
            const certBadge = certified ? ' ✅ **Certified**' : '';
            const certBlock = blockReason ? `\n> 인증 불가: ${blockReason}` : '';
            let summary = '';
            if (critical > 0)    summary = `Critical 취약점 ${critical}개 발견 — 즉시 수정 필요`;
            else if (high > 0)   summary = `High 취약점 ${high}개 발견 — 머지 전 수정 권장`;
            else if (medium > 0) summary = `Medium 취약점 ${medium}개 발견`;
            else if (low > 0)    summary = `Low 취약점 ${low}개`;
            else                 summary = `취약점 미발견`;
            const body = [
              `## 🔐 VibeSafe 보안 스캔 결과`,``,
              `${gradeEmoji} **${points}/100** (등급 ${grade})${certBadge}`,
              certBlock,``,`> ${summary}`,``,
              `| 심각도 | 건수 |`,`|--------|------|`,
              `| 🔴 Critical | ${critical} |`,`| 🟠 High | ${high} |`,
              `| 🟡 Medium | ${medium} |`,`| 🟢 Low | ${low} |`,``,
              `도메인: \`${domain}\` · 총 ${total}건`,``,
              `<sub>Powered by [VibeSafe](https://vibesafe.dev)</sub>`,
            ].join('\n');
            const {data:comments} = await github.rest.issues.listComments({
              owner:context.repo.owner, repo:context.repo.repo, issue_number:context.issue.number
            });
            const existing = comments.find(c =>
              c.user.login==='github-actions[bot]' && c.body.includes('VibeSafe 보안 스캔 결과')
            );
            if (existing) {
              await github.rest.issues.updateComment({
                owner:context.repo.owner, repo:context.repo.repo, comment_id:existing.id, body
              });
            } else {
              await github.rest.issues.createComment({
                owner:context.repo.owner, repo:context.repo.repo, issue_number:context.issue.number, body
              });
            }
```

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

## 머지 차단 설정 (선택)

Critical 취약점이 있으면 머지를 막으려면:

`Settings → Branches → Branch protection rules → Require status checks`
→ **`VibeSafe Security Scan / Security Scan`** 추가

---

## FAQ

**코드가 외부로 나가나요?**
아니요. 모든 스캔은 GitHub Actions runner 안에서 실행됩니다. 코드가 VibeSafe 서버로 전송되지 않습니다.

**비용이 드나요?**
GitHub Actions 실행 시간만 소비합니다. 스캔 1회 약 20초. Public 레포는 무제한 무료입니다.

**어떤 언어를 지원하나요?**
Semgrep이 지원하는 모든 언어 — JavaScript/TypeScript, Python, Java, Go, Ruby, PHP, Kotlin.

---

<sub>Powered by [VibeSafe](https://vibesafe.dev) · Built with [Semgrep](https://semgrep.dev)</sub>
