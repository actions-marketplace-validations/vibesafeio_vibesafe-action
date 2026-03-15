# Workflow: 도메인 자동 분류 (domain_classification)

## 목표
사용자가 도메인 유형을 선택하지 않았거나 잘못 선택한 경우, 소스 코드 분석을 통해 서비스 도메인을 자동 판별한다.

## 필수 입력값
| 필드 | 타입 | 설명 |
|------|------|------|
| source_path | path | 압축 해제된 소스 코드 경로 |
| user_selected_domain | enum \| null | 사용자가 선택한 도메인 (없을 수 있음) |

## 분류 시그널

### 이커머스 시그널
- 파일명/경로: `cart`, `checkout`, `payment`, `order`, `product`, `catalog`, `shipping`
- 패키지: `stripe`, `paypal`, `shopify-api`, `square`, `braintree`
- 코드 패턴: PCI 관련 변수명, 가격 계산 로직, 재고 관리

### 게임 시그널
- 파일명/경로: `game`, `player`, `score`, `level`, `inventory`, `matchmaking`
- 패키지: `socket.io`, `colyseus`, `phaser`, `unity-webgl`, `playfab`
- 코드 패턴: 실시간 통신, 게임 상태 동기화, 리더보드

### 플랫폼/SaaS 시그널
- 파일명/경로: `tenant`, `workspace`, `organization`, `billing`, `subscription`
- 패키지: `@auth0`, `clerk`, `supabase`, `firebase-admin`
- 코드 패턴: 멀티테넌시 격리, 역할 기반 접근 제어(RBAC), API 키 발급

### 헬스케어 시그널
- 파일명/경로: `patient`, `diagnosis`, `prescription`, `medical`, `health`, `ehr`
- 패키지: `fhir`, `hl7`, `dicom-parser`
- 코드 패턴: PHI 필드, 진료 기록 CRUD, HIPAA 관련 설정

### 핀테크 시그널
- 파일명/경로: `account`, `transaction`, `transfer`, `kyc`, `aml`, `ledger`
- 패키지: `plaid`, `dwolla`, `moov`, `tink`
- 코드 패턴: 잔액 계산, 이체 로직, KYC 문서 업로드

### 교육 시그널
- 파일명/경로: `student`, `course`, `grade`, `assignment`, `enrollment`, `classroom`
- 패키지: `lti`, `scorm`, `canvas-api`
- 코드 패턴: 성적 CRUD, 학습 기록, 학부모 연락처

## 실행 순서

### Step 1: 파일 구조 분석
```bash
python tools/scanner/domain_rule_engine.py --classify --path <source_path>
```

### Step 2: 신뢰도 산출
각 도메인별 시그널 매칭 수를 기반으로 신뢰도 점수(0.0~1.0) 산출.
- 신뢰도 ≥ 0.7: 자동 분류 적용
- 0.4 ≤ 신뢰도 < 0.7: 사용자에게 확인 요청 ("이커머스 서비스로 보입니다. 맞습니까?")
- 신뢰도 < 0.4: 사용자에게 수동 선택 요청

### Step 3: 사용자 선택과 자동 분류 불일치 처리
사용자가 "게임"을 선택했으나 자동 분류 결과 "이커머스" 신뢰도가 0.8인 경우:
→ 두 도메인의 규칙셋을 **모두** 적용하되, 사용자에게 불일치 알림 표시

## 학습 기록
- [2025-03-15] 초기 작성
