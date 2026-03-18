# VibeSafe 경쟁사 분석 (2026-03-19)

## 직접 경쟁사: "Vibe Coding Security" 카테고리

### 1. SecureVibes (anshumanbh/securevibes)
- **방식:** Claude 멀티 에이전트 (5개 AI 에이전트가 협업)
- **강점:** 11언어 지원, DAST 포함, threat modeling, exploit chain 분석, diff 기반 PR 리뷰
- **약점:** Claude API 비용 발생, 설정 복잡 (pip install + API 키 필요)
- **Stars:** ~200+
- **VibeSafe 대비:** SecureVibes는 "AI가 분석"하는 도구, VibeSafe는 "규칙이 분석"하는 도구. SecureVibes가 더 깊지만 비용/설정이 장벽. VibeSafe는 무료+24줄 YAML.

### 2. VibeSecurity (abenstirling/VibeSecurity)
- **방식:** 웹 기반 스캐너 (Go 구현)
- **강점:** 웹 UI, 프리미엄 티어
- **약점:** GitHub Action이 아님 — CI/CD 통합 없음
- **VibeSafe 대비:** 완전히 다른 접근. VibeSafe는 PR 워크플로 내장.

### 3. VibePenTester (firetix/vibe-coding-penetration-tester)
- **방식:** AI 펜테스터 (동적 분석)
- **Stars:** 159
- **약점:** DAST 중심 — 코드 레벨 정적 분석 아님
- **VibeSafe 대비:** 보완적. SAST(VibeSafe) + DAST(VibePenTester) 조합 가능.

### 4. ZeriFlow
- **방식:** 상용 보안 스캐너
- **약점:** 가격 정보 불명, 클로즈드 소스
- **VibeSafe 대비:** VibeSafe는 무료 오픈소스.

### 5. vibe-security-skill (raroque)
- **방식:** Claude Code 스킬 (MCP 기반)
- **Stars:** 201
- **VibeSafe 대비:** 스킬은 IDE 내 실시간 검사. VibeSafe의 MCP 서버 계획과 직접 경쟁.

## 인접 경쟁사: 범용 SAST

### Semgrep (직접 GitHub Action)
- 무료 (10인까지), PR 코멘트 지원
- **VibeSafe 대비:** VibeSafe는 Semgrep을 내부에서 사용. 차별점은 도메인별 규칙 자동 선택 + 수정 제안 + 프레임워크 필터링.

### Codacy
- 무료 티어 있음, PR 코멘트 지원
- **VibeSafe 대비:** Codacy는 코드 품질 중심. VibeSafe는 보안 전문.

### CodeQL (GitHub Advanced Security)
- 공개 레포 무료
- **VibeSafe 대비:** CodeQL은 빌드 설정 필요 (15분+). VibeSafe는 30초.

## VibeSafe의 실제 차별점

| 차별점 | 경쟁사 상황 |
|--------|------------|
| **24줄 YAML, 30초 설치** | SecureVibes: pip + API 키. CodeQL: 빌드 설정. Semgrep: 계정 필요 |
| **도메인별 규칙 자동 선택** | 없음 — 모든 경쟁사가 범용 스캔 |
| **프레임워크 오탐 필터링** | 없음 — Flask/Django 충돌 등은 모든 Semgrep 기반 도구에서 발생 |
| **Fix 수정 제안 (32패턴)** | SecureVibes: AI 기반 (비용). Semgrep: 메시지만. CodeQL: 없음 |
| **무료, 비용 0** | SecureVibes: API 비용. Snyk: $35K+. ZeriFlow: 유료 |

## 위협

1. **SecureVibes가 GitHub Action 출시하면** — 직접 경쟁. 단, AI 비용이 장벽.
2. **Semgrep이 도메인 규칙/Fix 제안 추가하면** — 차별점 소멸. 하지만 Semgrep은 엔터프라이즈 포커스.
3. **GitHub Copilot Autofix 확대** — 무료화되면 Fix 제안 차별점 사라짐.

## 기회

1. **MCP 서버** — vibe-security-skill (201 stars)이 수요 증명. VibeSafe MCP 서버 출시하면 IDE 시장 진입.
2. **pre-commit hook** — 경쟁사 중 제공하는 곳 없음. 코딩 시점 보안 = 독점 영역.
3. **한국 시장** — 한국어 지원하는 vibe coding 보안 도구 없음.
