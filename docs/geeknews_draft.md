# 바이브 코딩으로 만든 앱, 보안 점수 매겨봤더니 0점이었습니다

AI에게 "쇼핑몰 만들어줘"라고 하면 30분 만에 동작하는 앱이 나옵니다. 그런데 그 앱에 SQL Injection, 하드코딩된 API 키, Command Injection이 들어있으면 어떻게 될까요?

실제로 테스트해봤습니다. AI가 생성한 Flask 앱을 보안 스캐너에 돌렸더니 **0/100 F등급**, 총 10건의 취약점(Critical 1 + High 7 + Medium 2)이 나왔습니다. eval(), subprocess.run(shell=True), f-string SQL 쿼리가 그대로 들어있었습니다.

이건 제 앱만의 문제가 아닙니다.

---

## 숫자로 보는 바이브 코딩의 보안 현실

- **Tenzai (2025.12)**: 5개 주요 바이브 코딩 도구를 테스트, 15개 앱에서 69개 취약점 발견. 절반 이상이 High/Critical.
- **Escape**: 5,600개 공개 바이브 코딩 앱 분석, 2,000개 이상의 취약점, 400개 이상의 노출된 시크릿, 175건의 개인정보 노출.
- **CodeRabbit**: AI가 공동 작성한 코드는 인간 코드보다 보안 취약점이 **2.74배** 높음.
- **Moltbook 사건**: 바이브 코딩으로 만든 앱에서 150만 인증 토큰 + 35,000 이메일 유출.
- **Lovable 앱**: 한 앱이 18,000명의 사용자 데이터를 노출.

코드가 동작한다고 안전한 게 아닙니다. AI는 기능은 잘 만들지만, 보안은 신경 쓰지 않습니다.

---

## Dependabot이 있지 않나요?

Dependabot은 의존성 버전만 봅니다. AI가 직접 작성한 코드의 SQL Injection이나 하드코딩된 시크릿은 못 잡습니다.

Snyk는 연 $35K부터 시작하고 설정에 30분이 걸립니다. CodeQL은 언어별 빌드 설정이 필요합니다. 바이브 코더에게 보안팀은 없습니다.

---

## VibeSafe: 24줄 YAML, 30초 설치

GitHub Action 하나 추가하면, 모든 PR에서 자동으로:

1. **기술 스택 자동 탐지** — import문, package.json, requirements.txt 분석
2. **도메인별 규칙 선택** — 이커머스면 PCI DSS, 핀테크면 AML 규칙 강화
3. **SAST + 시크릿 스캔** — Semgrep 기반 정적 분석 + API 키/토큰 탐지
4. **PR 코멘트로 결과 전달** — 파일명, 줄 번호, 취약한 코드, 수정 가이드까지

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

무료, 오픈소스, 코드가 외부로 나가지 않습니다 (GitHub Actions runner 안에서 실행).

---

## 실제 결과 예시

![VibeSafe PR 코멘트](스크린샷 URL)

- SQL Injection: `admin_api.py:24` — f-string으로 구성된 SQL 쿼리 탐지
- Command Injection: `admin_api.py:67` — subprocess.run(shell=True) 탐지
- 하드코딩된 시크릿: `admin_api.py:12` — OpenAI API 키 탐지

같은 위치의 중복 탐지는 자동으로 그룹핑하고, Flask 앱에 Django 룰이 발화하는 오탐은 프레임워크 감지로 필터링합니다.

---

## 써보기

GitHub: https://github.com/vibesafeio/vibesafe-action

30초만 투자하면, 다음 PR부터 보안 검사가 자동으로 돌아갑니다.

바이브 코딩의 속도를 유지하면서, 배포 전에 최소한의 안전망을 거는 겁니다. 내 코드가 안전한지, 확인하는 데 30초면 됩니다.
