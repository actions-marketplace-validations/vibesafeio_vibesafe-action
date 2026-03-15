# Workflow: 자동 수정 제안 생성 (auto_remediation)

## 목표
스캔 결과에서 발견된 취약점 각각에 대해 바이브 코더가 이해할 수 있는 수준의 수정 코드와 설명을 생성한다.

## 근본 전제
바이브 코더는 코드를 직접 작성하지 않았으므로 **수정 코드도 직접 작성할 수 없다.**
따라서 수정 제안은 두 가지 형태로 제공해야 한다:
1. **원클릭 자동 패치**: 사용자가 "적용" 버튼만 누르면 수정이 반영되는 패치 파일
2. **AI 프롬프트 제안**: 사용자가 자신의 바이브 코딩 도구(Cursor, v0, Replit 등)에 복사-붙여넣기할 수 있는 수정 지시문

## 필수 입력값
| 필드 | 타입 | 설명 |
|------|------|------|
| scan_id | string | 스캔 고유 ID |
| vulnerabilities | SARIF[] | 스캔에서 발견된 취약점 목록 |
| source_files | path | 원본 소스 코드 경로 |
| domain_type | enum | 서비스 도메인 |
| detected_stack | string[] | 탐지된 기술 스택 |

## 실행 순서

### Step 1: 취약점 우선순위 정렬
**기준**: CVSS 점수 × 도메인 가중치
- 이커머스 도메인에서 SQL Injection → 가중치 2.0 (결제 데이터 직접 위험)
- 게임 도메인에서 XSS → 가중치 1.2 (채팅 통해 전파 가능)
- 헬스케어에서 암호화 미적용 → 가중치 3.0 (HIPAA 위반 즉시 과징금)

### Step 2: 수정 코드 생성
**도구**: `tools/remediation/auto_fix_generator.py`
```bash
python tools/remediation/auto_fix_generator.py \
  --scan-id <scan_id> \
  --vuln-file .tmp/scan_<scan_id>/vulnerabilities.json \
  --source-path .tmp/scan_<scan_id>/source/ \
  --output .tmp/scan_<scan_id>/patches/
```

**생성물 (취약점당)**:
```json
{
  "vuln_id": "VULN-001",
  "type": "sql_injection",
  "severity": "critical",
  "file": "src/api/products.ts",
  "line": 42,
  "description_ko": "사용자 입력값이 검증 없이 SQL 쿼리에 직접 삽입됩니다. 공격자가 데이터베이스 전체를 탈취할 수 있습니다.",
  "description_simple": "사용자가 입력한 값이 바로 데이터베이스 명령어에 들어가서, 해커가 모든 데이터를 훔칠 수 있어요.",
  "patch": "--- a/src/api/products.ts\n+++ b/src/api/products.ts\n@@ -42 +42 @@\n-const result = await db.query(`SELECT * FROM products WHERE id = ${req.params.id}`);\n+const result = await db.query('SELECT * FROM products WHERE id = $1', [req.params.id]);",
  "ai_prompt": "내 코드에서 SQL 쿼리를 파라미터화된 쿼리로 변경해줘. products.ts 42번째 줄에서 template literal 대신 $1 파라미터 바인딩을 사용하도록 수정해줘.",
  "references": ["https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"]
}
```

### Step 3: 패치 유효성 검증
**도구**: `tools/remediation/fix_validator.py`
```bash
python tools/remediation/fix_validator.py \
  --source-path .tmp/scan_<scan_id>/source/ \
  --patches .tmp/scan_<scan_id>/patches/ \
  --dry-run
```
**검증 항목**:
- 패치 적용 후 구문 오류 없음 (AST 파싱 성공)
- 패치가 원래 취약점을 제거했는지 재스캔
- 패치가 새로운 취약점을 생성하지 않았는지 확인

### Step 4: 결과 저장
DB에 수정 제안 저장 → 사용자 대시보드에 표시

## 예외 처리
| 상황 | 대응 |
|------|------|
| 수정 코드 생성 실패 (난독화 코드 등) | 수동 검토 큐에 추가 + 사용자에게 "이 취약점은 자동 수정이 불가합니다" 표시 |
| 패치 적용 시 구문 오류 발생 | 패치 폐기 + AI 프롬프트 제안만 제공 |
| 동일 파일에 다수 패치 충돌 | 통합 패치 생성 시도, 실패 시 우선순위 높은 패치만 제공 |

## 학습 기록
- [2025-03-15] 초기 작성
