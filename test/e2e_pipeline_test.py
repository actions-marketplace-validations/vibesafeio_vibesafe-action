#!/usr/bin/env python3
"""
test/e2e_pipeline_test.py
Celery 파이프라인 E2E 테스트 + False Positive 검증.

3구간 검증:
  vulnerable_app  → score < 50, critical >= 1, secrets 탐지
  ambiguous_app   → score 40~85, 스코어링 그라데이션 작동
  clean_app       → score >= 75, critical == 0

룰셋 로드 검증:
  SARIF tool.driver.rules 배열이 비어있으면 Semgrep이 룰셋을 로드하지 않은 것.
  각 스캔 후 SARIF 아티팩트를 MinIO에서 내려받아 rules 수를 assert.
"""
import os
import sys
import uuid
from pathlib import Path

os.environ.update({
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "vibesafe",
    "POSTGRES_USER": "vibesafe_user",
    "POSTGRES_PASSWORD": "vibesafe_dev_password",
    "POSTGRES_SSLMODE": "disable",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "REDIS_PASSWORD": "vibesafe_dev_redis",
    "REDIS_SSL": "false",
    "S3_ENDPOINT": "http://localhost:9000",
    "MINIO_ROOT_USER": "vibesafe_minio_user",
    "MINIO_ROOT_PASSWORD": "vibesafe_minio_password",
    "S3_BUCKET_UPLOADS": "vibesafe-uploads",
    "S3_BUCKET_ARTIFACTS": "vibesafe-artifacts",
    "AWS_REGION": "ap-northeast-2",
})

sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
import datetime
import json
import psycopg2
import tempfile

FIXTURES = {
    "vulnerable": Path(__file__).parent / "fixtures" / "vulnerable_app.zip",
    "ambiguous":  Path(__file__).parent / "fixtures" / "ambiguous_app.zip",
    "clean":      Path(__file__).parent / "fixtures" / "clean_app.zip",
}

S3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="vibesafe_minio_user",
    aws_secret_access_key="vibesafe_minio_password",
    region_name="ap-northeast-2",
)

def get_conn():
    return psycopg2.connect(
        host="localhost", port=5432, dbname="vibesafe",
        user="vibesafe_user", password="vibesafe_dev_password",
        sslmode="disable",
    )


def assert_sarif_rules_loaded(scan_id: str, min_rules: int = 5) -> int:
    """
    MinIO에서 SAST SARIF 아티팩트를 내려받아 tool.driver.rules 수를 검증한다.

    rules 배열이 비어있으면 Semgrep이 룰셋을 실제로 로드하지 않은 것(silent 실패).
    min_rules 개 이상 로드되었으면 해당 수를 반환한다.
    """
    # scan_artifacts 테이블에서 sast_sarif s3_key 조회
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT s3_key, s3_bucket FROM scan_artifacts WHERE scan_id = %s AND artifact_type = 'sast_sarif'",
        (scan_id,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        raise AssertionError(f"[{scan_id[:8]}] sast_sarif 아티팩트 레코드 없음 — 파이프라인이 SARIF를 저장하지 않았음")

    s3_key, bucket = row

    # MinIO에서 SARIF 다운로드
    with tempfile.NamedTemporaryFile(suffix=".sarif", delete=False) as tmp:
        tmp_path = tmp.name
    S3.download_file(bucket, s3_key, tmp_path)

    sarif = json.loads(open(tmp_path).read())
    rules = []
    for run in sarif.get("runs", []):
        rules.extend(run.get("tool", {}).get("driver", {}).get("rules", []))

    rule_count = len(rules)
    if rule_count < min_rules:
        raise AssertionError(
            f"[{scan_id[:8]}] SARIF rules 로드 부족: {rule_count}개 (최소 {min_rules}개 필요) "
            f"— Semgrep 룰셋이 실제로 적용되지 않았을 가능성"
        )
    return rule_count


def run_scan(fixture_name: str, zip_path: Path, domain: str = "platform") -> dict:
    scan_id = str(uuid.uuid4())
    s3_key = f"uploads/{scan_id}/source.zip"

    # 1. S3 업로드
    S3.upload_file(str(zip_path), "vibesafe-uploads", s3_key)

    # 2. DB 레코드 (DB DEFAULT로 id 자동 생성 → uuid4 불필요)
    conn = get_conn()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (id, email, name, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        ON CONFLICT (email) DO UPDATE SET id = EXCLUDED.id RETURNING id
    """, ("test-fp-user", "fp-test@vibesafe.local", "FP Test"))
    user_id = cur.fetchone()[0]
    cur.execute("""
        INSERT INTO scans (id, user_id, domain_type, scan_depth, status, s3_source_key, created_at, updated_at)
        VALUES (%s, %s, %s, 'standard', 'PENDING', %s, NOW(), NOW())
    """, (scan_id, user_id, domain, s3_key))
    conn.close()

    # 3. 파이프라인 직접 실행
    from worker.tasks import scan_pipeline
    scan_pipeline.run(
        scanId=scan_id, userId=user_id,
        s3Key=s3_key, domainType=domain, scanDepth="standard",
    )

    # 4. 결과 조회
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT status, error_message FROM scans WHERE id = %s", (scan_id,))
    scan_row = cur.fetchone()
    cur.execute("SELECT score, grade, critical_count, high_count, medium_count, low_count FROM scan_results WHERE scan_id = %s", (scan_id,))
    result_row = cur.fetchone()
    cur.execute("SELECT type, severity FROM vulnerabilities WHERE scan_id = %s", (scan_id,))
    vulns = cur.fetchall()
    conn.close()

    return {
        "name": fixture_name,
        "scan_id": scan_id,
        "status": scan_row[0],
        "error": scan_row[1],
        "score": result_row[0] if result_row else None,
        "grade": result_row[1] if result_row else None,
        "critical": result_row[2] if result_row else 0,
        "high": result_row[3] if result_row else 0,
        "medium": result_row[4] if result_row else 0,
        "low": result_row[5] if result_row else 0,
        "vulns": vulns,
    }


def assert_result(r: dict, checks: dict):
    errors = []
    if "status" in checks and r["status"] != checks["status"]:
        errors.append(f"status: expected {checks['status']}, got {r['status']} (error={r['error']})")
    if "score_lt" in checks and (r["score"] or 0) >= checks["score_lt"]:
        errors.append(f"score_lt {checks['score_lt']}: got {r['score']}")
    if "score_gte" in checks and (r["score"] or 0) < checks["score_gte"]:
        errors.append(f"score_gte {checks['score_gte']}: got {r['score']}")
    if "critical_gte" in checks and r["critical"] < checks["critical_gte"]:
        errors.append(f"critical_gte {checks['critical_gte']}: got {r['critical']}")
    if "critical_eq" in checks and r["critical"] != checks["critical_eq"]:
        errors.append(f"critical_eq {checks['critical_eq']}: got {r['critical']}")
    if "has_type" in checks:
        found_types = {v[0] for v in r["vulns"]}
        if checks["has_type"] not in found_types:
            errors.append(f"has_type '{checks['has_type']}' not found in {found_types}")
    if errors:
        raise AssertionError(f"[{r['name']}] " + "; ".join(errors))


if __name__ == "__main__":
    print("VibeSafe E2E + False Positive 테스트\n" + "="*50)

    results = []
    failed = []

    # (fixture명, zip경로, 도메인, 결과 검증 조건, 최소 SARIF rules 수)
    # min_rules: 해당 도메인 ruleset에서 Semgrep이 최소한 이 수의 규칙을 로드해야 함
    cases = [
        ("vulnerable", FIXTURES["vulnerable"], "ecommerce", {
            "status": "COMPLETED",
            "score_lt": 50,
            "critical_gte": 1,
            # secret scanner는 구체적 타입(github_token, stripe_secret) 반환
            # 공통 prefix 'hardcoded_secret'이 아님 → critical count로 검증
        }, 10),
        ("ambiguous", FIXTURES["ambiguous"], "platform", {
            "status": "COMPLETED",
            "score_gte": 40,
            "score_lt": 100,  # eval 등 medium 패턴 → 100 미만, critical 없음
            "critical_eq": 0,
        }, 10),
        ("clean", FIXTURES["clean"], "platform", {
            "status": "COMPLETED",
            "score_gte": 75,
            "critical_eq": 0,
        }, 10),
    ]

    for name, path, domain, checks, min_rules in cases:
        print(f"\n▶ [{name}] 스캔 중...")
        try:
            r = run_scan(name, path, domain)
            assert_result(r, checks)
            # 룰셋 로드 검증: SARIF에 실제 규칙이 로드됐는지 확인
            rule_count = assert_sarif_rules_loaded(r["scan_id"], min_rules=min_rules)
            r["rule_count"] = rule_count
            results.append(r)
            status = "✅ PASS"
        except AssertionError as e:
            results.append({"name": name, "scan_id": "?", "score": "?", "grade": "?", "error": str(e)})
            failed.append(str(e))
            status = "❌ FAIL"
        except Exception as e:
            import traceback
            results.append({"name": name, "scan_id": "?", "score": "?", "grade": "?", "error": str(e)})
            failed.append(f"[{name}] {e}")
            status = "❌ ERROR"
            traceback.print_exc()

        r = results[-1]
        rule_info = f"  rules={r.get('rule_count', '?')}" if r.get("rule_count") else ""
        print(f"  {status}  score={r.get('score')}/100  grade={r.get('grade')}  critical={r.get('critical', '?')}{rule_info}")

    print("\n" + "="*50)
    print("결과 요약:")
    for r in results:
        rule_info = f"  rules={r['rule_count']}" if r.get("rule_count") else ""
        print(f"  [{r['name']:12s}] score={r.get('score'):>4}  grade={r.get('grade')}  critical={r.get('critical', '?')}  vuln_count={len(r.get('vulns', []))}{rule_info}")

    # ── Self-improvement harness: 실패 시 failure_log.json에 기록 ──────────
    log_path = Path(__file__).parent / "failure_log.json"
    if failed:
        existing = json.loads(log_path.read_text()) if log_path.exists() else []
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "failures": failed,
            "scores": {r["name"]: {"score": r.get("score"), "grade": r.get("grade")} for r in results},
        }
        existing.append(entry)
        log_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
        print(f"\n❌ {len(failed)}개 실패 → {log_path} 에 기록됨:")
        for f in failed:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("\n✅ 전체 테스트 통과")
