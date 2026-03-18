# VibeSafe Progress Tracker

Last checked: 2026-03-18 14:17

## Gap 3: Actionability (Priority 1) — DONE (Phase 1)
- [x] PR 코멘트에 취약점 상세 (파일+줄+스니펫+메시지)
- [x] 같은 file:line 그룹핑 (+N건 관련 탐지)
- [x] 프레임워크 충돌 필터링 (Flask<>Django)
- [x] Import문 기반 프레임워크 감지
- [x] 상단 요약 테이블 수치를 필터링 후 수치로 교체
- [x] score_calculator에도 프레임워크 필터링 적용
- [x] PR 최종 확인: 10건, Critical 1 / High 7 / Medium 2, 수치 일치
- [x] auto-fix 설계 문서 작성 (docs/auto_fix_design.md)
- [ ] auto-fix Phase 1 구현 (룰 기반 수정 제안)

## Gap 1: Awareness (Priority 2) — DRAFTS READY
- [x] GeekNews 글 초안 (docs/geeknews_draft.md)
- [x] OKKY 글 초안 (docs/okky_draft.md)
- [x] PR 코멘트 스크린샷 (증거) — 사용자가 캡처 완료
- [ ] 사용자 리뷰 후 GeekNews 발행
- [ ] 사용자 리뷰 후 OKKY 발행

## Gap 5: Trust (Priority 4) — BENCHMARK DONE
- [x] OWASP Juice Shop 벤치마크 실행 (36건 탐지, 0/100 F)
- [x] README에 Snyk/CodeQL 설치시간 비교 추가
- [x] README에 OWASP 벤치마크 결과 게시
- [ ] GitHub Stars 20개 목표
- [ ] 실사용 레포 10개 목표

## Gap 4: Timing (Priority 3) — PROTOTYPE TESTED
- [x] pre-commit hook 프로토타입 (tools/pre_commit_hook.py)
- [x] pre-commit hook 테스트 (시크릿 감지 → commit 차단 확인)
- [x] .git/hooks/pre-commit에 설치됨
- [ ] MCP 서버 설계
- [ ] README에 pre-commit 설치 가이드 추가

## Gap 2: Setup — MAINTAINED
- [x] 24줄 YAML 설치
- [x] 서버 없음
- [x] README 첫 화면에 설치시간 비교 + 벤치마크 추가

## Pending (토큰 필요)
- [ ] 최신 코드 push (6 commits behind remote)
- [ ] Docker rebuild + v0 tag 업데이트
