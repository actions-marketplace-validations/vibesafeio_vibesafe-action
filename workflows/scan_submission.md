# Workflow: 스캔 제출 처리 (scan_submission)

## 목표
사용자가 업로드한 실행 파일 + 도메인 유형을 받아 보안 스캔을 완료하고 결과를 반환한다.

## 트리거 조건
- 사용자가 웹 UI에서 파일 업로드 + 도메인 선택 후 "스캔 시작" 클릭
- API 엔드포인트 `POST /api/v1/scans`에 파일과 메타데이터 도착

## 필수 입력값
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| file | binary | Y | ZIP, TAR.GZ, 또는 단일 소스코드 파일 |
| domain_type | enum | Y | ecommerce, game, platform, healthcare, fintech, education |
| tech_stack | string[] | N | 사용자가 명시한 기술 스택 (예: ["nextjs", "supabase", "stripe"]) |
| scan_depth | enum | N | quick (SAST만), standard (SAST+SCA), deep (SAST+SCA+DAST). 기본값: standard |

## 실행 순서

### Step 1: 파일 수신 및 검증
**도구**: `tools/infra/file_extractor.py`
```bash
python tools/infra/file_extractor.py --input <uploaded_file> --output .tmp/scan_<scan_id>/
```
**검증 항목**:
- 파일 크기 ≤ 500MB
- 압축 해제 후 총 파일 수 ≤ 10,000개
- 악성 파일 패턴 탐지 (심볼릭 링크 공격, zip bomb)
**실패 시**: HTTP 400 반환 + 사유 메시지

### Step 2: 기술 스택 자동 탐지
**도구**: `tools/scanner/sast_runner.py --detect-stack`
```bash
python tools/scanner/sast_runner.py --detect-stack --path .tmp/scan_<scan_id>/
```
**탐지 대상**: package.json (Node.js), requirements.txt (Python), Gemfile (Ruby), go.mod (Go), pubspec.yaml (Flutter)
**출력**: `{ "detected_stack": ["nextjs@14.2", "prisma@5.x", "stripe-js@2.x"], "languages": ["typescript", "css"] }`

### Step 3: 도메인별 규칙 로드
**도구**: `tools/scanner/domain_rule_engine.py`
```bash
python tools/scanner/domain_rule_engine.py --domain <domain_type> --stack <detected_stack>
```
**출력**: 해당 도메인에 적용할 Semgrep 규칙셋 ID 목록 + 커스텀 규칙 경로

### Step 4: 정적 분석 (SAST) 실행
**도구**: `tools/scanner/sast_runner.py`
```bash
python tools/scanner/sast_runner.py --path .tmp/scan_<scan_id>/ --rules <rule_ids> --timeout 180
```
**출력**: SARIF 형식 결과 파일

### Step 5: 의존성 취약점 스캔 (SCA) 실행
**도구**: `tools/scanner/sca_runner.py`
```bash
python tools/scanner/sca_runner.py --path .tmp/scan_<scan_id>/
```
**출력**: 취약 패키지 목록 + CVE ID + CVSS 점수

### Step 6: 시크릿 스캐닝
**도구**: `tools/scanner/secret_scanner.py`
```bash
python tools/scanner/secret_scanner.py --path .tmp/scan_<scan_id>/
```
**출력**: 발견된 시크릿 목록 (API 키, 비밀번호, 토큰, 하드코딩된 URL)

### Step 7: (deep 모드 전용) 동적 분석 (DAST)
**도구**: `tools/scanner/dast_runner.py`
**전제조건**: Docker 샌드박스에서 앱 실행 가능해야 함
```bash
python tools/infra/sandbox_manager.py --create --scan-id <scan_id>
python tools/scanner/dast_runner.py --target http://sandbox-<scan_id>:3000 --rules <rule_ids>
python tools/infra/sandbox_manager.py --destroy --scan-id <scan_id>
```

### Step 8: 결과 통합 및 점수 산출
**도구**: `tools/report/score_calculator.py`
```bash
python tools/report/score_calculator.py \
  --sast-result .tmp/scan_<scan_id>/sast.sarif \
  --sca-result .tmp/scan_<scan_id>/sca.json \
  --secret-result .tmp/scan_<scan_id>/secrets.json \
  --domain <domain_type>
```
**출력**: `{ "score": 42, "grade": "F", "critical": 3, "high": 7, "medium": 12, "low": 5 }`

### Step 9: 자동 수정 제안 생성
**도구**: `tools/remediation/auto_fix_generator.py`
→ `workflows/auto_remediation.md` 참조

### Step 10: 리포트 생성 및 전달
**도구**: `tools/report/pdf_generator.py`
→ `workflows/report_generation.md` 참조

## 예외 처리

| 상황 | 대응 |
|------|------|
| 파일 압축 해제 실패 | HTTP 422 + "지원하지 않는 파일 형식" 메시지 |
| SAST 타임아웃 (180초 초과) | 부분 결과 반환 + "일부 파일 미스캔" 경고 |
| 의존성 파일 미발견 | SCA 건너뛰기 + 리포트에 "의존성 분석 불가" 표시 |
| 샌드박스 실행 실패 | DAST 건너뛰기 + 리포트에 "런타임 분석 불가" 표시 |
| 알 수 없는 기술 스택 | 범용 규칙셋만 적용 + 사용자에게 수동 입력 요청 |

## 학습 기록
- [2025-03-15] 초기 작성
- 이 워크플로우에서 반복적으로 발생하는 오류는 `workflows/error_log.md`에 기록하고 여기에 참조 링크를 추가할 것
