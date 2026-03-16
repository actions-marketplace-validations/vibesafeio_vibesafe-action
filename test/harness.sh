#!/bin/bash
set -e
# ──────────────────────────────────────────────────────────
# VibeSafe Harness Loop — 변경 전후 파이프라인 검증
#
# 사용법:
#   ./test/harness.sh          # 전체 검증
#   ./test/harness.sh quick    # Docker 빌드 스킵 (코드만 검증)
#
# 이 스크립트가 실패하면 push하지 마라.
# ──────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$SCRIPT_DIR/harness_log.json"
FIXTURE_DIR="$SCRIPT_DIR/fixtures"
FAILURES=()

log() { echo "[$1] $2"; }
pass() { log "PASS" "$1"; }
fail() { log "FAIL" "$1"; FAILURES+=("$1"); }

# ── 1. 테스트 픽스처 준비 ────────────────────────────────
mkdir -p "$FIXTURE_DIR"

# 취약한 Python 코드 (반드시 탐지되어야 함)
cat > "$FIXTURE_DIR/vuln_python.py" << 'VULN'
import os, sqlite3, subprocess
from flask import Flask, request, jsonify
app = Flask(__name__)
API_KEY = "sk-proj-abc123def456ghi789jkl012"

@app.route("/search")
def search():
    q = request.args.get("q", "")
    db = sqlite3.connect("test.db")
    sql = f"SELECT * FROM users WHERE name LIKE '%{q}%'"
    return jsonify(db.execute(sql).fetchall())

@app.route("/run", methods=["POST"])
def run_cmd():
    cmd = request.json.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return jsonify({"out": result.stdout})

@app.route("/eval", methods=["POST"])
def do_eval():
    return jsonify({"result": str(eval(request.json.get("expr")))})
VULN

# 안전한 Python 코드 (취약점 0이어야 함)
cat > "$FIXTURE_DIR/safe_python.py" << 'SAFE'
import os
from flask import Flask
app = Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run()
SAFE

# ── 2. Python 유닛 테스트 ─────────────────────────────────
log "TEST" "domain_rule_engine: language-based ruleset selection"
python3 -c "
from tools.scanner.domain_rule_engine import get_ruleset
r = get_ruleset('platform', [], ['python'])
assert 'p/python' in r['semgrep_configs'], 'p/python missing for Python lang'
r2 = get_ruleset('platform', [], ['go'])
assert 'p/golang' in r2['semgrep_configs'], 'p/golang missing for Go lang'
r3 = get_ruleset('platform', [], ['java'])
assert 'p/java' in r3['semgrep_configs'], 'p/java missing for Java lang'
" && pass "language-based ruleset" || fail "language-based ruleset"

log "TEST" "domain_rule_engine: --validate (pack existence)"
python3 tools/scanner/domain_rule_engine.py --validate > /dev/null 2>&1 \
  && pass "ruleset pack validation" || fail "ruleset pack validation"

log "TEST" "secret_scanner: detects hardcoded API key"
python3 -c "
from tools.scanner.secret_scanner import scan_file
from pathlib import Path
findings = scan_file(Path('$FIXTURE_DIR/vuln_python.py'))
types = [f['type'] for f in findings]
assert 'openai_key' in types, f'OpenAI key not detected, found: {types}'
" && pass "secret detection (OpenAI key)" || fail "secret detection (OpenAI key)"

# ── 3. Docker 빌드 + 파이프라인 테스트 ────────────────────
if [ "${1:-full}" != "quick" ]; then
    log "TEST" "Docker build"
    docker build -f "$PROJECT_DIR/Dockerfile.action" -t vibesafe-action:harness "$PROJECT_DIR" > /dev/null 2>&1 \
      && pass "Docker build" || fail "Docker build"

    log "TEST" "Vulnerable code detection (full pipeline)"
    SCORE=$(docker run --rm --entrypoint sh -v "$FIXTURE_DIR:/workspace" vibesafe-action:harness -c '
      python /vibesafe/tools/scanner/sast_runner.py --detect-stack --path /workspace > /tmp/stack.json
      LANGS=$(python -c "import json; d=json.load(open(\"/tmp/stack.json\")); print(\",\".join(d.get(\"languages\",[])))")
      python /vibesafe/tools/scanner/domain_rule_engine.py --domain platform --stack "" --languages "$LANGS" > /tmp/ruleset.json
      RULES=$(python -c "import json; d=json.load(open(\"/tmp/ruleset.json\")); print(\",\".join(d[\"semgrep_configs\"]))")
      python /vibesafe/tools/scanner/sast_runner.py --path /workspace --rules "$RULES" --output /tmp/sast.sarif --timeout 120 > /dev/null 2>&1
      python /vibesafe/tools/scanner/secret_scanner.py --path /workspace --output /tmp/secrets.json > /dev/null 2>&1 || echo "{\"secrets\":[]}" > /tmp/secrets.json
      python /vibesafe/tools/report/score_calculator.py --domain platform --sast-result /tmp/sast.sarif --secret-result /tmp/secrets.json
    ' 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['score'])")

    if [ -n "$SCORE" ] && [ "$SCORE" -lt 70 ]; then
        pass "vulnerable code scored $SCORE/100 (expected < 70)"
    else
        fail "vulnerable code scored ${SCORE:-ERROR}/100 (should be < 70)"
    fi
else
    log "SKIP" "Docker tests (quick mode)"
fi

# ── 4. 결과 기록 ─────────────────────────────────────────
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

if [ ${#FAILURES[@]} -eq 0 ]; then
    STATUS="pass"
    log "RESULT" "All tests passed ✓"
else
    STATUS="fail"
    log "RESULT" "FAILURES: ${FAILURES[*]}"
fi

# Append to log
python3 -c "
import json, os
log_path = '$LOG_FILE'
existing = json.loads(open(log_path).read()) if os.path.exists(log_path) else []
existing.append({
    'timestamp': '$TIMESTAMP',
    'commit': '$COMMIT',
    'status': '$STATUS',
    'failures': $(python3 -c "import json; print(json.dumps([$(printf '"%s",' "${FAILURES[@]}")]))" 2>/dev/null || echo '[]'),
})
# Keep last 100 entries
existing = existing[-100:]
open(log_path, 'w').write(json.dumps(existing, indent=2))
"

[ ${#FAILURES[@]} -eq 0 ] || exit 1
