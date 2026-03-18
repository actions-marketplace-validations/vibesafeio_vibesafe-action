# [오픈소스] 바이브 코딩 보안 스캐너 VibeSafe 소개

안녕하세요. AI로 코딩하시는 분들께 공유드립니다.

## 문제

요즘 Cursor, Copilot, Claude로 코드 생성하시는 분 많으실 텐데요. AI가 만든 코드가 기능적으로는 잘 동작하지만 보안은 다른 문제입니다.

- CodeRabbit 분석: AI 공동 작성 코드는 인간 코드보다 보안 취약점이 **2.74배** 높음
- Escape 조사: 5,600개 공개 바이브 코딩 앱에서 2,000개 취약점 + 400개 노출된 시크릿 발견
- 실제 피해: Moltbook (150만 토큰 유출), Lovable 앱 (18,000명 데이터 노출)

SQL Injection, 하드코딩된 API 키, Command Injection 같은 취약점이 AI 생성 코드에 자주 들어갑니다.

## VibeSafe

GitHub Action 하나 추가하면 모든 PR에서 자동으로 보안 검사합니다.

**특징:**
- 24줄 YAML, 30초 설치 — Snyk(30분+, 유료)이나 CodeQL(빌드 설정 필요) 대비 진입장벽 최소
- PR 코멘트로 결과 전달 — 파일명, 줄 번호, 취약한 코드 스니펫, 수정 가이드까지
- 같은 위치 중복 탐지 자동 그룹핑
- Flask/Django/FastAPI 프레임워크 자동 감지 → 오탐 필터링
- 무료, 오픈소스, 코드가 외부로 나가지 않음

**설치:**

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
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: vibesafeio/vibesafe-action@v0
        with:
          domain: auto
```

**OWASP Juice Shop 벤치마크:** 36건 탐지, 0/100 F등급

GitHub: https://github.com/vibesafeio/vibesafe-action

피드백이나 개선 제안 환영합니다. 이슈나 PR 남겨주세요.
