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
- `action.yml` + `Dockerfile.action` + `action_entrypoint.sh` = 사용자가 `uses: vibesafeio/vibesafe-action@v1`로 호출
- `action.yml`의 `image:`는 현재 `Dockerfile.action` (로컬 빌드). 첫 GHCR 이미지 push 후 `docker://ghcr.io/vibesafeio/vibesafe-action:v1`으로 교체.
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

---

## Harness: 자기 검증 루프

이 섹션은 모든 코드 변경에 적용되는 자기 검증 프로토콜이다.
코드를 작성한 후, **커밋 전에 반드시** 아래 루프를 실행한다.

### Phase 1: 실행 검증 (필수)

변경한 코드를 반드시 실제로 실행해서 동작을 확인한다.

```bash
# Python 도구 변경 시
python3 <변경한_파일.py> --help  # 최소한 import 에러 없는지

# PR 코멘트 변경 시
python3 tools/report/pr_commenter.py /tmp/score.json --dry-run

# 파이프라인 변경 시
python3 test/e2e_pipeline_test.py

# Docker 관련 변경 시
docker build -f Dockerfile.action -t vibesafe-action-test . && \
docker run --rm -v /tmp/vibesafe_docker_test/source:/scan_target:ro \
  -e INPUT_PATH=/scan_target -e INPUT_DOMAIN=platform \
  -e GITHUB_OUTPUT=/dev/null vibesafe-action-test
```

"코드 완성 ≠ 기능 완성". 이 프로젝트에서 실행 안 해보고 넘긴 코드에서 버그 12개가 나왔다.
실행 결과를 확인하지 않은 코드는 커밋하지 않는다.

### Phase 2: 침묵하는 실패 점검

이 프로젝트에서 가장 위험했던 버그는 **에러 없이 덜 잡는 버그**였다:
- `--config` 플래그 버그: Semgrep이 룰셋을 절반만 로드했는데 에러 없이 정상 완료
- `capture_output=True` 버그: Docker에서 SAST가 0건을 반환했는데 파이프라인은 성공
- SARIF `level=None` 버그: high severity가 low로 처리됐는데 점수는 나옴

변경한 코드에서 아래를 점검한다:
- subprocess 호출이 실패해도 빈 결과로 넘어가는 경로가 있는가?
- 파일이 없거나 비어있을 때 기본값으로 조용히 넘어가는가?
- JSON 파싱에서 키가 없을 때 빈 리스트/dict로 대체하는가?
- 위 중 하나라도 해당되면: 해당 경로에서 warning 로그를 추가하거나, 의도적 fallback임을 주석으로 명시한다.

### Phase 3: 환경 호환성

- [ ] Python 3.9에서 동작하는가? (`list[str] | None` 금지 → `from __future__ import annotations` 사용)
- [ ] Docker 환경에서 로컬과 다르게 동작할 수 있는가? (파일 경로, stderr 처리, 네트워크)
- [ ] 새 외부 패키지를 추가했는가? (금지 — 표준 라이브러리 + 기존 설치분만 사용)

### Phase 4: Doom Loop 감지

같은 파일을 3번 이상 수정하고 있으면 멈추고 접근을 재고한다.
같은 에러를 다른 방식으로 2번 이상 고치려 했으면 멈추고 근본 원인을 다시 분석한다.

### Phase 5: 자기 검증 보고서

매 Task 또는 의미 있는 변경 단위를 완료한 후, 아래 형식으로 보고서를 출력한다:

```
## 자기 검증 보고서

**변경 파일:** (목록)
**실행 검증:** ✅ 통과 / ❌ 실패 — (어떤 명령으로 테스트했는지)
**침묵하는 실패 가능성:** 없음 / 있음 — (있으면 어디서, 왜 허용했는지)
**환경 호환성:** ✅ / ❌ — (Python 3.9, Docker)
**Doom Loop:** 발생 안 함 / 발생 — (있으면 어떻게 탈출했는지)
**이 구현에서 가장 깨지기 쉬운 부분:** (한 줄)
**내가 확인 못 한 것:** (한 줄)
**Docker 이미지 재빌드 필요:** 예 / 아니오
```

이 보고서 없이 커밋하지 않는다.

### 실패 기록

버그를 발견하면 아래 형식으로 이 섹션 하단에 추가한다:

```
#### 실패 기록 YYYY-MM-DD: (한 줄 제목)
- 원인: (근본 원인)
- 교훈: (같은 류의 버그를 앞으로 어떻게 방지하는지)
- 추가한 방어: (린터 규칙, 테스트, 가드레일 등)
```

이 기록이 쌓이면 반복되는 패턴을 Phase 2 체크리스트에 추가한다.
에이전트가 고생하면 그건 하네스가 부족하다는 신호다 — 하네스를 고친다.

#### 실패 기록 2026-03-18: git safe.directory 미설정으로 Semgrep 0건 반환
- 원인: Docker 컨테이너 내 마운트된 /github/workspace가 git safe.directory에 등록되지 않아 `git ls-files` exit 128 → Semgrep이 파일 0개 스캔
- 교훈: Docker 안에서 git 명령이 필요한 도구는 safe.directory 설정 필수. Semgrep은 exit 0으로 정상 종료하므로 Phase 2 침묵 실패에 해당
- 추가한 방어: action_entrypoint.sh 첫 줄에 `git config --global --add safe.directory` 추가

#### 실패 기록 2026-03-18: Flask 앱에서 Django 오탐 4건 발화
- 원인: detect_stack이 requirements.txt만 확인 → import문 기반 프레임워크 미감지 → 프레임워크 충돌 필터 미작동
- 교훈: 의존성 파일 없이 직접 import하는 프로젝트가 많음. 파일 내용 기반 감지 필요
- 추가한 방어: sast_runner.py의 detect_stack에 Python import문 기반 프레임워크 감지 추가
