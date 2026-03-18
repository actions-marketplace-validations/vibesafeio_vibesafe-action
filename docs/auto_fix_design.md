# VibeSafe Auto-Fix 설계 문서

## 목표
취약점을 발견하면 수정 PR을 자동 생성한다. 바이브 코더의 AI 에이전트가 이해할 수 있는 형태로 제공.

## 왜 필요한가
- Gap 3 (Actionability)의 최종 단계: "뭘 고쳐야 하는지 알려줬다" → "고쳐놨다"
- GitHub Copilot Autofix가 이미 "탐지 + 수정 제안" 하고 있음
- VibeSafe 차별점: 바이브 코더의 AI 에이전트(Cursor, Claude Code)가 소비할 수 있는 구조화된 출력

## 아키텍처

```
SARIF findings
    ↓
auto_fix_generator.py (새 도구)
    ↓
fix_instructions.json (구조화된 수정 지침)
    ↓
(Option A) 수정 PR 자동 생성
(Option B) PR 코멘트에 수정 지침 첨부 (바이브 코더가 AI에게 "이거 고쳐줘" 할 수 있도록)
```

## fix_instructions.json 스키마

```json
{
  "findings": [
    {
      "id": "finding-1",
      "severity": "HIGH",
      "rule_id": "python.flask.security.injection.tainted-sql-string",
      "file": "admin_api.py",
      "line": 24,
      "current_code": "sql = f\"SELECT * FROM customers WHERE name LIKE '%{query}%'\"",
      "fix_type": "parameterized_query",
      "fix_description": "f-string SQL을 파라미터화된 쿼리로 교체",
      "suggested_code": "sql = \"SELECT * FROM customers WHERE name LIKE ?\"\ncursor.execute(sql, (f'%{query}%',))",
      "confidence": "high",
      "references": ["https://owasp.org/Top10/A03_2021-Injection/"]
    }
  ]
}
```

## 수정 패턴 매핑 (Phase 1 — 룰 기반)

| Semgrep rule pattern | fix_type | 변환 |
|---|---|---|
| `tainted-sql-string` | parameterized_query | f-string → placeholder + params |
| `subprocess-injection` | safe_subprocess | shell=True → shlex.split + shell=False |
| `user-eval` | remove_eval | eval() → ast.literal_eval() 또는 제거 |
| `hardcoded_secret` | env_variable | 리터럴 → os.environ.get() |
| `path-traversal-open` | path_validation | open(user_input) → pathlib 검증 추가 |
| `debug-enabled` | remove_debug | debug=True → 제거 또는 환경변수 분기 |

## 구현 단계

### Phase 1: 룰 기반 수정 제안 (PR 코멘트)
- SARIF rule_id → fix 패턴 매핑 테이블
- suggested_code는 정적 템플릿 (AST 분석 없이)
- PR 코멘트 하단에 "수정 제안" 섹션 추가
- 구현 난이도: 중 / 가치: 높음

### Phase 2: AST 기반 자동 수정 (수정 PR 생성)
- Python ast 모듈로 코드 파싱 → 취약 패턴 치환
- JS는 esprima/acorn 필요 → Docker 이미지 사이즈 증가
- git branch 생성 → 수정 적용 → PR 생성
- 구현 난이도: 높음 / 가치: 매우 높음

### Phase 3: LLM 기반 수정 (AI 에이전트 연동)
- fix_instructions.json을 Claude/GPT에 전달
- 컨텍스트 포함 수정 (주변 코드 이해)
- 구현 난이도: 중 (API 호출) / 가치: 매우 높음 / 비용: API 비용 발생

## 우선순위 결정
Phase 1부터 시작. 룰 기반 제안만으로도 "뭘 어쩌라고" 갭의 90%를 해결.
Phase 3는 비용 구조 확정 후. Phase 2는 ROI 대비 구현 비용이 높아 후순위.

## 의존성
- 새 외부 패키지 없음 (Phase 1은 순수 Python 템플릿)
- 기존 SARIF 파싱 로직 재사용 (pr_commenter.py의 load_sarif_findings)
