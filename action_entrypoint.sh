#!/bin/bash
set -e

# Trust the mounted workspace for git operations inside Docker
# (without this, Semgrep's git ls-files exits 128 → 0 files scanned)
git config --global --add safe.directory "${GITHUB_WORKSPACE:-/github/workspace}"

TARGET="${INPUT_PATH:-.}"
DOMAIN="${INPUT_DOMAIN:-auto}"

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
python /vibesafe/tools/scanner/domain_rule_engine.py \
  --domain "$DOMAIN" \
  --stack "$STACK" \
  --languages "$LANGS" \
  > /tmp/ruleset.json
echo "Rules: $(python -c "import json; print(json.load(open('/tmp/ruleset.json'))['semgrep_configs'])")"

echo "::endgroup::"

echo "::group::VibeSafe — SAST Scan"
RULES=$(python -c "import json; d=json.load(open('/tmp/ruleset.json')); print(','.join(d.get('semgrep_configs', ['p/owasp-top-ten'])))")
echo "Target: $TARGET ($(find "$TARGET" -name '*.py' -o -name '*.js' -o -name '*.ts' | wc -l) source files)"
python /vibesafe/tools/scanner/sast_runner.py \
  --path "$TARGET" \
  --rules "$RULES" \
  --output /tmp/sast.sarif \
  --timeout 120
echo "SARIF findings: $(python -c "import json; d=json.load(open('/tmp/sast.sarif')); print(sum(len(r.get('results',[])) for r in d.get('runs',[])))" 2>/dev/null || echo 'N/A')"
echo "::endgroup::"

echo "::group::VibeSafe — Secret Scan"
python /vibesafe/tools/scanner/secret_scanner.py \
  --path "$TARGET" \
  --output /tmp/secrets.json \
  || echo '{"secrets":[]}' > /tmp/secrets.json
echo "::endgroup::"

echo "::group::VibeSafe — Score"
python /vibesafe/tools/report/score_calculator.py \
  --domain "$DOMAIN" \
  --sast-result /tmp/sast.sarif \
  --secret-result /tmp/secrets.json \
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
