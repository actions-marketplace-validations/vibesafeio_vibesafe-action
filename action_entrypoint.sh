#!/bin/bash
set -e

# Trust the mounted workspace for git operations inside Docker
# (without this, Semgrep's git ls-files exits 128 → 0 files scanned)
git config --global --add safe.directory "${GITHUB_WORKSPACE:-/github/workspace}"

TARGET="${INPUT_PATH:-.}"
DOMAIN="${INPUT_DOMAIN:-auto}"
CUSTOM_RULES="${INPUT_CUSTOM_RULES:-}"

echo "::group::VibeSafe — Stack Detection"

python /vibesafe/tools/scanner/sast_runner.py \
  --detect-stack \
  --path "$TARGET" \
  > /tmp/stack.json
echo "Stack: $(cat /tmp/stack.json | python -c 'import json,sys; d=json.load(sys.stdin); print(d.get("detected_stack", []))')"

if [ "$DOMAIN" = "auto" ]; then
  python /vibesafe/tools/scanner/domain_rule_engine.py \
    --classify \
    --path "$TARGET" \
    > /tmp/domain.json
  DOMAIN=$(python -c "import json; d=json.load(open('/tmp/domain.json')); print(d['best_match'] if d['auto_classify'] else 'platform')")
fi
echo "Domain: $DOMAIN"

STACK=$(python -c "import json; d=json.load(open('/tmp/stack.json')); print(','.join(d.get('detected_stack', [])))")
LANGS=$(python -c "import json; d=json.load(open('/tmp/stack.json')); print(','.join(d.get('languages', [])))")
echo "Languages: $LANGS"
CUSTOM_RULES_ARG=""
if [ -n "$CUSTOM_RULES" ]; then
  CUSTOM_RULES_ARG="--custom-rules $CUSTOM_RULES"
fi
python /vibesafe/tools/scanner/domain_rule_engine.py \
  --domain "$DOMAIN" \
  --stack "$STACK" \
  --languages "$LANGS" \
  $CUSTOM_RULES_ARG \
  > /tmp/ruleset.json
echo "Rules: $(python -c "import json; print(json.load(open('/tmp/ruleset.json'))['semgrep_configs'])")"

echo "::endgroup::"

echo "::group::VibeSafe — SAST Scan"
RULES=$(python -c "import json; d=json.load(open('/tmp/ruleset.json')); print(','.join(d.get('semgrep_configs', ['p/owasp-top-ten'])))")
echo "Target: $TARGET ($(find "$TARGET" -name '*.py' -o -name '*.js' -o -name '*.ts' 2>/dev/null | wc -l) source files)"

# Diff-only mode: only report NEW findings introduced by this PR
# Uses Semgrep --baseline-commit (requires Semgrep Pro; falls back to full scan)
BASELINE_ARG=""
if [ -n "${GITHUB_BASE_REF:-}" ]; then
  git fetch origin "$GITHUB_BASE_REF" --depth=1 2>/dev/null || true
  BASELINE_COMMIT=$(git rev-parse "origin/$GITHUB_BASE_REF" 2>/dev/null || echo "")
  if [ -n "$BASELINE_COMMIT" ]; then
    BASELINE_ARG="--baseline-commit $BASELINE_COMMIT"
    echo "Diff mode: comparing against $GITHUB_BASE_REF ($BASELINE_COMMIT)"
  fi
fi

# Try diff-only first, fall back to full scan if baseline not supported
if [ -n "$BASELINE_ARG" ]; then
  python /vibesafe/tools/scanner/sast_runner.py \
    --path "$TARGET" \
    --rules "$RULES" \
    --output /tmp/sast.sarif \
    --timeout 120 \
    $BASELINE_ARG \
    2>/dev/null || {
    echo "Diff mode not available (requires Semgrep Pro). Falling back to full scan."
    BASELINE_ARG=""
    python /vibesafe/tools/scanner/sast_runner.py \
      --path "$TARGET" \
      --rules "$RULES" \
      --output /tmp/sast.sarif \
      --timeout 120
  }
else
  python /vibesafe/tools/scanner/sast_runner.py \
    --path "$TARGET" \
    --rules "$RULES" \
    --output /tmp/sast.sarif \
    --timeout 120
fi
echo "SARIF findings: $(python -c "import json; d=json.load(open('/tmp/sast.sarif')); print(sum(len(r.get('results',[])) for r in d.get('runs',[])))" 2>/dev/null || echo 'N/A')"
echo "::endgroup::"

echo "::group::VibeSafe — Secret Scan"
python /vibesafe/tools/scanner/secret_scanner.py \
  --path "$TARGET" \
  --output /tmp/secrets.json \
  || echo '{"secrets":[]}' > /tmp/secrets.json
echo "::endgroup::"

echo "::group::VibeSafe — Dependency Scan (SCA)"
python /vibesafe/tools/scanner/sca_scanner.py \
  --path "$TARGET" \
  --output /tmp/sca.json \
  || echo '{"vulnerabilities":[]}' > /tmp/sca.json
SCA_COUNT=$(python -c "import json; d=json.load(open('/tmp/sca.json')); print(d.get('total', 0))" 2>/dev/null || echo "0")
echo "Dependency vulnerabilities: $SCA_COUNT"
echo "::endgroup::"

echo "::group::VibeSafe — Score"
python /vibesafe/tools/report/score_calculator.py \
  --domain "$DOMAIN" \
  --sast-result /tmp/sast.sarif \
  --secret-result /tmp/secrets.json \
  --sca-result /tmp/sca.json \
  --stack-file /tmp/stack.json \
  > /tmp/score.json
cat /tmp/score.json
echo "::endgroup::"

# Export outputs for downstream steps
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
    f\"certified_block_reason={d.get('certified_block_reason') or ''}\",
]
import os
with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
    f.write('\n'.join(lines) + '\n')
"

echo "::group::VibeSafe — PR Comment"
python /vibesafe/tools/report/pr_commenter.py /tmp/score.json || echo "PR comment failed (non-fatal)"
echo "::endgroup::"

# Fail gate: exit non-zero if findings meet the fail-on threshold
FAIL_ON="${INPUT_FAIL_ON:-critical}"
if [ "$FAIL_ON" != "none" ]; then
  python -c "
import json, sys
d = json.load(open('/tmp/score.json'))
fail_on = '$FAIL_ON'.lower()
severity_levels = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
threshold = severity_levels.get(fail_on, 0)

failed = False
for sev, level in severity_levels.items():
    if level <= threshold and d.get(sev, 0) > 0:
        count = d[sev]
        print(f'::error::VibeSafe: {count} {sev} vulnerabilities found. Failing because fail-on={fail_on}.')
        failed = True
        break

if failed:
    sys.exit(1)
else:
    print(f'VibeSafe: No findings at or above {fail_on} severity. Check passed.')
"
fi
