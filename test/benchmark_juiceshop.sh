#!/bin/bash
set -e
# ──────────────────────────────────────────────────────────
# VibeSafe Benchmark: OWASP Juice Shop
#
# 누구나 실행하여 README의 벤치마크 수치를 검증할 수 있다.
# 사용법: ./test/benchmark_juiceshop.sh
# ──────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WORK_DIR="/tmp/vibesafe-benchmark"

echo "=== VibeSafe Benchmark: OWASP Juice Shop ==="
echo ""

# 1. Clone Juice Shop
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
echo "[1/5] Cloning OWASP Juice Shop..."
git clone --depth=1 https://github.com/juice-shop/juice-shop.git "$WORK_DIR/juice-shop" 2>&1 | tail -1

# 2. Stack Detection
echo "[2/5] Detecting stack..."
cd "$PROJECT_DIR"
python3 tools/scanner/sast_runner.py --detect-stack --path "$WORK_DIR/juice-shop" > "$WORK_DIR/stack.json"
echo "Stack: $(python3 -c "import json; d=json.load(open('$WORK_DIR/stack.json')); print(d['detected_stack'])")"
echo "Languages: $(python3 -c "import json; d=json.load(open('$WORK_DIR/stack.json')); print(d['languages'])")"

# 3. SAST Scan
echo "[3/5] Running SAST scan (this may take 2-5 minutes)..."
LANGS=$(python3 -c "import json; d=json.load(open('$WORK_DIR/stack.json')); print(','.join(d.get('languages', [])))")
python3 tools/scanner/domain_rule_engine.py --domain ecommerce --stack "" --languages "$LANGS" > "$WORK_DIR/ruleset.json"
RULES=$(python3 -c "import json; d=json.load(open('$WORK_DIR/ruleset.json')); print(','.join(d['semgrep_configs']))")
python3 tools/scanner/sast_runner.py \
  --path "$WORK_DIR/juice-shop" \
  --rules "$RULES" \
  --output "$WORK_DIR/sast.sarif" \
  --timeout 300 > /dev/null 2>&1
SAST_COUNT=$(python3 -c "import json; d=json.load(open('$WORK_DIR/sast.sarif')); print(sum(len(r.get('results',[])) for r in d.get('runs',[])))")
echo "SAST findings: $SAST_COUNT"

# 4. Secret Scan
echo "[4/5] Running secret scan..."
python3 tools/scanner/secret_scanner.py \
  --path "$WORK_DIR/juice-shop" \
  --output "$WORK_DIR/secrets.json" > /dev/null 2>&1 || echo '{"secrets":[]}' > "$WORK_DIR/secrets.json"
SECRET_COUNT=$(python3 -c "import json; d=json.load(open('$WORK_DIR/secrets.json')); print(d.get('total_secrets', 0))")
echo "Secret findings: $SECRET_COUNT"

# 5. Score
echo "[5/5] Calculating score..."
python3 tools/report/score_calculator.py \
  --domain ecommerce \
  --sast-result "$WORK_DIR/sast.sarif" \
  --secret-result "$WORK_DIR/secrets.json" \
  --stack-file "$WORK_DIR/stack.json" \
  > "$WORK_DIR/score.json"

echo ""
echo "=== BENCHMARK RESULTS ==="
python3 -c "
import json
d = json.load(open('$WORK_DIR/score.json'))
print(f'Score:    {d[\"score\"]}/100')
print(f'Grade:    {d[\"grade\"]}')
print(f'Critical: {d[\"critical\"]}')
print(f'High:     {d[\"high\"]}')
print(f'Medium:   {d[\"medium\"]}')
print(f'Low:      {d[\"low\"]}')
print(f'Total:    {d[\"total_vulnerabilities\"]}')
print(f'Domain:   {d[\"domain\"]}')
"
echo ""
echo "Full results saved to $WORK_DIR/"
echo "Verify: cat $WORK_DIR/score.json"

# Cleanup
rm -rf "$WORK_DIR/juice-shop"
