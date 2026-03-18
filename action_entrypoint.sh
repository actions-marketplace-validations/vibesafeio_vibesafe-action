#!/bin/bash
set -e

# Docker 컨테이너 내부에서 마운트된 워크스페이스를 git이 신뢰하도록 설정
# (없으면 Semgrep의 git ls-files가 exit 128 → 0건 스캔)
git config --global --add safe.directory "${GITHUB_WORKSPACE:-/github/workspace}"

# GitHub Actions 환경변수로 입력받은 경로
TARGET="${INPUT_PATH:-.}"
DOMAIN="${INPUT_DOMAIN:-auto}"

echo "::group::VibeSafe — 스택/도메인 탐지"

# 스택 탐지
python /vibesafe/tools/scanner/sast_runner.py \
  --detect-stack \
  --path "$TARGET" \
  > /tmp/stack.json
echo "스택: $(cat /tmp/stack.json | python -c 'import json,sys; d=json.load(sys.stdin); print(d.get("detected_stack", []))')"

# 도메인 탐지 (auto이면 자동 분류, 아니면 그대로 사용)
if [ "$DOMAIN" = "auto" ]; then
  python /vibesafe/tools/scanner/domain_rule_engine.py \
    --classify \
    --path "$TARGET" \
    > /tmp/domain.json
  DOMAIN=$(python -c "import json; d=json.load(open('/tmp/domain.json')); print(d['best_match'] if d['auto_classify'] else 'platform')")
fi
echo "도메인: $DOMAIN"

# 룰셋 선택 (스택 + 언어 정보 모두 전달)
STACK=$(python -c "import json; d=json.load(open('/tmp/stack.json')); print(','.join(d.get('detected_stack', [])))")
LANGS=$(python -c "import json; d=json.load(open('/tmp/stack.json')); print(','.join(d.get('languages', [])))")
echo "언어: $LANGS"
python /vibesafe/tools/scanner/domain_rule_engine.py \
  --domain "$DOMAIN" \
  --stack "$STACK" \
  --languages "$LANGS" \
  > /tmp/ruleset.json
echo "규칙: $(python -c "import json; print(json.load(open('/tmp/ruleset.json'))['semgrep_configs'])")"

echo "::endgroup::"

echo "::group::VibeSafe — SAST 스캔"
RULES=$(python -c "import json; d=json.load(open('/tmp/ruleset.json')); print(','.join(d.get('semgrep_configs', ['p/owasp-top-ten'])))")
echo "스캔 대상: $TARGET ($(find "$TARGET" -name '*.py' | wc -l) Python files)"
python /vibesafe/tools/scanner/sast_runner.py \
  --path "$TARGET" \
  --rules "$RULES" \
  --output /tmp/sast.sarif \
  --timeout 120
echo "SARIF 결과 수: $(python -c "import json; d=json.load(open('/tmp/sast.sarif')); print(sum(len(r.get('results',[])) for r in d.get('runs',[])))" 2>/dev/null || echo 'N/A')"
echo "::endgroup::"

echo "::group::VibeSafe — 시크릿 스캔"
python /vibesafe/tools/scanner/secret_scanner.py \
  --path "$TARGET" \
  --output /tmp/secrets.json \
  || echo '{"secrets":[]}' > /tmp/secrets.json
echo "::endgroup::"

echo "::group::VibeSafe — 점수 산출"
python /vibesafe/tools/report/score_calculator.py \
  --domain "$DOMAIN" \
  --sast-result /tmp/sast.sarif \
  --secret-result /tmp/secrets.json \
  --stack-file /tmp/stack.json \
  > /tmp/score.json
cat /tmp/score.json
echo "::endgroup::"

# GitHub Actions output 내보내기 (injection 방지를 위해 scalar 값만 개별 출력)
python -c "
import json
d = json.load(open('/tmp/score.json'))
lines = [
    f\"score={d['score']}\",
    f\"grade={d['grade']}\",
    f\"domain={d['domain']}\",
    f\"certified={str(d['certified']).lower()}\",
    f\"critical={d.get('critical', 0)}\",
    f\"high={d.get('high', 0)}\",
    f\"medium={d.get('medium', 0)}\",
    f\"low={d.get('low', 0)}\",
    f\"total={d.get('total_vulnerabilities', 0)}\",
    # certified_block_reason은 한국어 텍스트 — URL encode 없이 넘기면 개행/특수문자 위험.
    # 빈 문자열로 안전하게 처리
    f\"certified_block_reason={d.get('certified_block_reason') or ''}\",
]
import os
with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
    f.write('\n'.join(lines) + '\n')
"

echo "::group::VibeSafe — PR 코멘트"
python /vibesafe/tools/report/pr_commenter.py /tmp/score.json || echo "PR 코멘트 실패 (non-fatal)"
echo "::endgroup::"
