# VC 피드백 대응 — CEO 내부 보고

---

## 문제 4 (지표 0) — 해결: 측정 시작

서버에 4개 핵심 이벤트 로깅 추가:

| 이벤트 | 의미 | 확인 방법 |
|---|---|---|
| `page_views` | 사람들이 오는가? | Render 로그 |
| `scans_started` | URL을 넣는가? | Render 로그 |
| `scans_completed` | 끝까지 기다리는가? | Render 로그 |
| `fix_copies` | 가치를 느끼는가? | Render 로그 |
| `install_clicks` | 재방문 의사? | Render 로그 |

실시간 대시보드: `vibesafe.onrender.com/api/metrics`

글 게시 완료:
- dev.to: https://dev.to/keuntaepark/my-cursor-generated-app-had-security-issues-it-scored-0-out-of-100-3pn4
- OKKY: https://okky.kr/articles/1553987

1주일 후 숫자로 판단.

---

## 문제 3 (TAM 모름) — 해결: 데이터 확보

### AI 코딩 시장 (검증된 데이터)
- **전체 시장:** $12.8B (2026), CAGR 26.6%
- **개발자 채택율:** 84%가 사용 중 또는 계획, 51%가 매일 사용
- **GitHub Copilot:** 2,000만+ 사용자
- **GitHub 커밋의 51%+가 AI 생성/보조** (2026 Q1)

### VibeSafe TAM 계산
```
전체 개발자: ~28M (GitHub 기준)
AI 코딩 도구 사용: 84% → ~23.5M
GitHub 사용: ~28M (거의 전부)
보안에 신경 씀: 추정 30% → ~7M
무료 도구 사용 의향: 추정 50% → ~3.5M

즉각적 TAM: 약 350만 명
```

---

## 문제 1 (비즈니스 모델) — 설계

### 제1원칙: 돈은 어디서 나오나?

무료 사용자 → 유료 사용자 전환. 어떤 가치에 돈을 내나?

MECE 분류:

| 무료 (현재) | 유료 (미래) |
|---|---|
| 웹 스캔 (light mode, public repos) | **Private repo 스캔** |
| GitHub Action (기본 룰) | **팀 대시보드 (히스토리, 트렌드)** |
| 8 custom rules | **500+ 전체 룰 웹 스캔** |
| 결과 1회성 | **연속 모니터링 + 알림** |
| AI Fix Prompt (텍스트) | **자동 Fix PR 생성** |

### Semgrep 모델 참고
- Semgrep OSS: 무료 → Semgrep Pro: $40/개발자/월
- 전환 트리거: "팀에서 쓰고 싶을 때" (관리 기능 필요)

### VibeSafe 모델 (안)
```
Free: 웹 스캔 (public, light) + GitHub Action (기본)
Pro ($9/월): private repo 웹 스캔 + full 500+ rules + 히스토리
Team ($29/월/좌석): 대시보드 + 자동 Fix PR + Slack 알림
```

**지금 실행하지 않음.** 무료 사용자 1,000명 → Pro 전환 실험 순서.

---

## 문제 2 (Moat 없음) — 장기 전략

### "왜 Semgrep이 직접 안 하나?"에 대한 답:

**Semgrep은 개발자를 판다. 우리는 비개발자를 판다.**

Semgrep의 고객: DevSecOps 팀, 시니어 엔지니어, CISO.
VibeSafe의 고객: Cursor로 앱 만드는 비개발자.

Semgrep이 "URL 넣으면 30초 결과 + AI Fix Prompt 복붙" 제품을 만들 가능성:
**낮다.** Semgrep은 엔터프라이즈 ($40/dev/월)에 집중. 무료 웹 스캐너는 그들의 비즈니스 모델과 충돌.

### Moat 구축 경로 (시간순)
1. **데이터** — 스캔 결과 축적 → "AI가 가장 많이 만드는 취약점 Top 10" 리포트 → 권위
2. **커뮤니티** — 바이브 코더 커뮤니티에서 "보안=VibeSafe" 인식 → 브랜드
3. **네트워크** — 스캔 결과 공유/비교 기능 → "내 앱 몇 점" 바이럴
4. **통합** — Lovable/Bolt/Cursor에 내장 파트너십 → 유통 채널 독점

지금 할 수 있는 것: **1번 (데이터)만.** 스캔 결과를 익명 집계.

---

## 실행 우선순위

| 순서 | 할 것 | 목적 |
|---|---|---|
| ✅ 완료 | 측정 로깅 추가 | VC 문제 4 |
| ✅ 완료 | 글 게시 (dev.to, OKKY) | 트래픽 시작 |
| ✅ 완료 | TAM 데이터 정리 | VC 문제 3 |
| ✅ 완료 | 비즈니스 모델 설계 | VC 문제 1 |
| ✅ 완료 | Moat 전략 정리 | VC 문제 2 |
| ⏳ 1주 후 | 지표 확인 → 다음 판단 | 증명 |
