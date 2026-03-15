# VibeSafe — Claude 작업 가이드라인

이 파일은 이 프로젝트에서 반복된 실수와 교훈을 기록한다.
새 세션을 시작할 때 반드시 읽고 동일한 실수를 반복하지 않는다.

---

## 반복된 버그 패턴 (하드 룰)

### 1. Python 파일 생성 시 첫 줄에 `from __future__ import annotations`
- **왜**: Python 3.9에서 `list[str] | None` 타입힌트가 런타임 에러를 낸다.
- **발생 횟수**: 4개 파일에서 4번 반복됨 (score_calculator, auto_fix_generator, domain_rule_engine, sast_runner).
- **룰**: 새 Python 파일 작성 시 shebang/docstring 직후 `from __future__ import annotations` 추가. 기존 파일 수정 시도 전 해당 줄 존재 여부 확인.

### 2. subprocess에서 Semgrep 호출 시 `capture_output=True` 금지
- **왜**: `stderr=PIPE`이면 Semgrep이 원격 ruleset 로드에 실패(exit 7 = MISSING_CONFIG). 로컬 캐시 환경에서는 재현 안 되고, Docker/CI의 깨끗한 환경에서만 재현됨. 모든 사용자에게 SAST가 침묵하며 실패하는 최악의 시나리오.
- **룰**: `subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=...)`

### 3. Semgrep ruleset 팩 이름 추가 시 `--validate` 먼저 실행
- **왜**: `p/nodejs-security`, `p/ssrf`는 존재하지 않는 팩이었다. 로컬에서는 캐시로 통과하지만 CI에서 exit 7.
- **룰**: `domain_rule_engine.py`에 팩 추가 후 반드시 `python tools/scanner/domain_rule_engine.py --validate` 실행. CI `publish-action.yml`에도 게이트로 들어있음.

### 4. DB에 raw SQL INSERT 시 ID/타임스탬프 직접 생성
- **왜**: Prisma ORM이 cuid()/uuid() 및 @updatedAt을 자동 생성하지만, psycopg2 raw SQL은 그렇지 않다.
- **룰**: `uuid4()`로 id 생성, `updated_at=NOW()` 명시. ON CONFLICT DO NOTHING 추가.

### 5. 코드 완성 ≠ 검증 완료. 만들면 즉시 돌려라
- **왜**: "검증은 나중에" 패턴이 7개 버그(1차)와 3개 버그(Docker 빌드 후)로 이어졌다. 그 중 2개는 사용자에게 거짓 안전감을 주는 치명적 silent 버그였다.
- **룰**: 새 도구/스크립트 작성 후 즉시 직접 실행 확인. Docker 이미지 만들면 즉시 `docker run`. "배포 직전에 테스트"는 금지.

### 6. GitHub Actions workflow에서 `${{ }}` 인터폴레이션으로 JSON을 JS 문자열에 넣지 않는다
- **왜**: `JSON.parse('${{ steps.x.outputs.json }}')` 패턴은 값에 작은따옴표나 특수문자가 있으면 JS 문법이 깨진다. 보안 도구의 scan 결과에 파일 경로, 취약점 설명 등 임의 문자열이 포함될 수 있어 injection 위험이 더 크다.
- **룰**: `env:` 블록에서 `VARNAME: ${{ steps.x.outputs.value }}`로 전달하고, JS 내에서 `process.env.VARNAME`으로 읽는다. JSON 전체가 필요하면 개별 scalar output으로 분리한다.

---

## 아키텍처 결정 사항

### GitHub Action 구조
- `action.yml` + `Dockerfile.action` + `action_entrypoint.sh` = 사용자가 `uses: vibesafe/vibesafe-action@v1`로 호출
- `action.yml`의 `image:`는 현재 `Dockerfile.action` (로컬 빌드). 첫 GHCR 이미지 push 후 `docker://ghcr.io/vibesafe/vibesafe-action:v1`으로 교체.
- PR 코멘트에서 `${{ steps.*.outputs.score_json }}`처럼 JSON 전체를 JS 문자열에 인터폴레이션 금지 (injection 취약). `env:` 블록 경유 → `process.env.*` 패턴 사용.

### 스코어링
- Certified 배지 hard gate: critical==0 AND high==0 AND score>=85 AND 위험 rule_id 블랙리스트 없음
- `p/nodejs-security`, `p/ssrf` = 미존재 팩. 대체: `p/javascript` + `p/owasp-top-ten`
- 취약 앱 0점은 정상: critical×2 (weight 2.0 ecommerce) = 80점 감점, 클램프 결과

### 검증 레이어 두 개 (둘 다 유지)
- `domain_rule_engine.py --validate` → 팩 존재 여부 (유령 팩 차단)
- `assert_sarif_rules_loaded(min_rules=10)` → 탐지 범위 유지 (팩 내용 변경 감지)

---

## TODO (미완, 배포 전)

- [ ] 실제 GitHub 테스트 레포에서 PR 열고 Action 코멘트 확인 (마지막 검증)
- [ ] `git tag v0.1.0 && git push --tags` → GHCR 첫 이미지 빌드/푸시
- [ ] `action.yml` image를 GHCR 참조로 교체

## TODO (나중에)

- [ ] `score_calculator.py --verbose`: 감점 항목별 내역 출력 (0점 원인 투명화)
- [ ] high >= 1 시 등급 B 이하 캡 (90/A for eval app 오해 방지)
- [ ] Share 페이지 + Certified 배지 UI (GitHub Action으로 첫 사용자 유입 후)
