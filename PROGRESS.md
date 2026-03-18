# VibeSafe Progress Tracker

Last checked: 2026-03-18 13:10

## Gap 3: Actionability (Priority 1) — DONE (Phase 1)
- [x] PR 코멘트에 취약점 상세 (파일+줄+스니펫+메시지)
- [x] 같은 file:line 그룹핑 (+N건 관련 탐지)
- [x] 프레임워크 충돌 필터링 (Flask<>Django)
- [x] Import문 기반 프레임워크 감지 (requirements.txt 없는 프로젝트)
- [x] 상단 요약 테이블 수치를 필터링 후 수치로 교체
- [ ] score_calculator에도 프레임워크 필터링 적용 (점수 자체 보정)
- [ ] auto-fix PR 생성 (v1.0 이후)

## Gap 1: Awareness (Priority 2) — IN PROGRESS
- [x] GeekNews 글 초안 작성 (docs/geeknews_draft.md)
- [ ] OKKY 글 초안 작성
- [x] PR 코멘트 스크린샷 (증거) — 사용자가 캡처 완료
- [ ] GeekNews 발행 (사용자 리뷰 후)
- [ ] 충격 사례 데이터 정리 완료 (초안에 포함)

## Gap 5: Trust (Priority 4) — IN PROGRESS
- [x] OWASP Juice Shop 벤치마크 실행 (36건 탐지, 0/100 F)
- [x] README에 Snyk/CodeQL 설치시간 비교 추가
- [ ] 벤치마크 결과를 README/docs에 공식 게시
- [ ] GitHub Stars 20개 목표 (현재: ?)
- [ ] 실사용 레포 10개 목표

## Gap 4: Timing (Priority 3) — NOT STARTED
- [ ] pre-commit hook 프로토타입
- [ ] MCP 서버 설계

## Gap 2: Setup — MAINTAINED
- [x] 24줄 YAML 설치
- [x] 서버 없음
- [x] README 첫 화면에 설치시간 비교 추가

## Pending Deploy
- [ ] pr_commenter.py 수정 push + Docker rebuild + PR 재트리거
- [ ] README push
