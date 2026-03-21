# VibeSafe Web Scanner — Iteration Log

**Goal:** URL 입력 → 30초 안에 보안+접근성 점수. 가입 없이. 코딩 모르는 바이브 코더가 쓸 수 있어야 함.

---

## Iteration 1 — 서버 뼈대
- Homepage 로드 ✅, API scan 시작 ✅, 잘못된 URL 거부 ✅
- 결과: 기본 동작 확인

## Iteration 2 — E2E 스캔 (실패)
- cli_scanner.py --json이 "Cloning..." 메시지를 stdout에 섞어 JSON 파싱 실패
- 수정: --json 모드에서 print 문 조건부 처리

## Iteration 3 — E2E 재시도 (성공)
- 깨끗한 JSON 출력 확인
- vibecost-test (소규모 clean repo): 100/100 Grade A

## Iteration 4 — 실제 프로젝트 스캔
- goodable (Lovable 프로젝트): 0/100 Grade F, 1,673 findings
- Stack 자동 감지: fastapi + nextjs + react
- 약 20초 소요

## Iteration 5 — 프론트엔드 필드 검증
- score 필드 모두 존재 ✅
- 발견: deductions가 비어있음 → SARIF에서 직접 findings 추출 필요

## Iteration 6 — findings 추출 추가
- SARIF에서 severity + file + line + message + rule_id 추출
- 50개 제한 (대형 repo 대응)
- 프론트엔드가 sast.findings를 표시하도록 수정

## Iteration 7 — findings 검증 (성공)
- goodable: 50 findings 포함, 샘플 확인 OK
- 발견: 파일 경로에 /tmp/ prefix 노출

## Iteration 8 — 경로 정리
- scan_prefix 제거 로직 추가
- 파일 경로가 프로젝트 상대 경로로 표시

## Iteration 9 — 에러 핸들링
- 존재하지 않는 repo: error 반환 ✅
- 잘못된 scan ID: 404 ✅
- Private repo: error 반환 ✅

## Iteration 10 — 최종 E2E
- brand-zen (Lovable 프로젝트): 0/100 Grade F, 4 critical, 652 medium
- 50 findings 표시, 파일 경로 clean (no /tmp/) ✅
- 약 20초 소요

---

## 남은 이슈
- password-comparison-timing-js가 `===` 전부를 잡아서 FP 많음 (652건 대부분이 이것)
- 이 룰은 비밀번호 비교만 잡아야 하는데 모든 === 비교를 잡고 있음 → 수정 필요
