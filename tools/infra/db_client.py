#!/usr/bin/env python3
"""
tools/infra/db_client.py
PostgreSQL (스캔 결과, 사용자 데이터) 및 Redis (세션, 캐시) 클라이언트.
모든 DB 접근은 이 모듈을 통해 이루어진다.
"""
from __future__ import annotations
import json
import os
from contextlib import contextmanager

from typing import Any, Optional

import psycopg2
import psycopg2.extras
import redis


# ─── 연결 설정 ───────────────────────────────────────────

def get_pg_connection():
    """환경 변수에서 PostgreSQL 연결을 생성한다."""
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        sslmode=os.environ.get("POSTGRES_SSLMODE", "require"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def get_redis_client() -> redis.Redis:
    """환경 변수에서 Redis 클라이언트를 생성한다."""
    return redis.Redis(
        host=os.environ["REDIS_HOST"],
        port=int(os.environ.get("REDIS_PORT", 6379)),
        password=os.environ.get("REDIS_PASSWORD"),
        ssl=os.environ.get("REDIS_SSL", "true").lower() == "true",
        decode_responses=True,
    )


@contextmanager
def pg_cursor():
    """트랜잭션 관리를 포함한 PostgreSQL 커서 컨텍스트 매니저."""
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── 스캔 CRUD ───────────────────────────────────────────

def create_scan(scan_id: str, user_id: str, domain_type: str, scan_depth: str) -> dict:
    with pg_cursor() as cur:
        cur.execute(
            """
            INSERT INTO scans (id, user_id, domain_type, scan_depth, status, created_at)
            VALUES (%s, %s, %s, %s, 'pending', NOW())
            RETURNING *
            """,
            (scan_id, user_id, domain_type, scan_depth),
        )
        return dict(cur.fetchone())


def update_scan_status(scan_id: str, status: str, error_message: Optional[str] = None) -> None:
    with pg_cursor() as cur:
        cur.execute(
            """
            UPDATE scans
            SET status = %s,
                error_message = %s,
                updated_at = NOW(),
                completed_at = CASE WHEN %s IN ('completed', 'failed') THEN NOW() ELSE NULL END
            WHERE id = %s
            """,
            (status, error_message, status, scan_id),
        )


def save_scan_results(scan_id: str, results: dict) -> None:
    with pg_cursor() as cur:
        cur.execute(
            """
            INSERT INTO scan_results (scan_id, score, grade, critical_count, high_count,
                                      medium_count, low_count, raw_results, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (scan_id) DO UPDATE
            SET score = EXCLUDED.score,
                grade = EXCLUDED.grade,
                raw_results = EXCLUDED.raw_results,
                updated_at = NOW()
            """,
            (
                scan_id,
                results.get("score"),
                results.get("grade"),
                results.get("critical", 0),
                results.get("high", 0),
                results.get("medium", 0),
                results.get("low", 0),
                json.dumps(results),
            ),
        )


def get_scan(scan_id: str) -> Optional[dict]:
    with pg_cursor() as cur:
        cur.execute("SELECT * FROM scans WHERE id = %s", (scan_id,))
        row = cur.fetchone()
        return dict(row) if row else None


# ─── 취약점 CRUD ─────────────────────────────────────────

def save_vulnerabilities(scan_id: str, vulnerabilities: list[dict]) -> None:
    import uuid as _uuid
    rows = [
        {
            "id": str(_uuid.uuid4()),
            "scan_id": scan_id,
            "vuln_id": v.get("vuln_id", f"{scan_id[:8]}-{i:04d}"),
            "type": v.get("type", "unknown"),
            "severity": v.get("severity", "info"),
            "file": v.get("file") or v.get("file_path"),
            "line": v.get("line") or v.get("line_number"),
            "description_ko": v.get("description_ko"),
            "description_simple": v.get("description_simple"),
            "patch": v.get("patch"),
            "ai_prompt": v.get("ai_prompt"),
            "cvss_score": v.get("cvss_score"),
            "domain_weight": v.get("domain_weight"),
            "final_score": v.get("final_score"),
        }
        for i, v in enumerate(vulnerabilities)
    ]
    with pg_cursor() as cur:
        psycopg2.extras.execute_batch(
            cur,
            """
            INSERT INTO vulnerabilities (id, scan_id, vuln_id, type, severity, file_path, line_number,
                                         description_ko, description_simple, patch, ai_prompt,
                                         cvss_score, domain_weight, final_score, status, created_at)
            VALUES (%(id)s, %(scan_id)s, %(vuln_id)s, %(type)s, %(severity)s, %(file)s, %(line)s,
                    %(description_ko)s, %(description_simple)s, %(patch)s, %(ai_prompt)s,
                    %(cvss_score)s, %(domain_weight)s, %(final_score)s, 'open', NOW())
            ON CONFLICT (vuln_id) DO NOTHING
            """,
            rows,
        )


def record_stat_snapshot(
    domain_type: str,
    detected_stack: list,
    vulnerabilities: list,
    score: int,
    grade: str,
) -> None:
    """익명 통계 스냅샷 기록 — 사용자/파일 정보 없음."""
    from collections import Counter

    vuln_type_counts = dict(Counter(v.get("type", "unknown") for v in vulnerabilities))
    severity_counts = Counter(v.get("severity", "info") for v in vulnerabilities)

    import uuid as _uuid
    with pg_cursor() as cur:
        cur.execute(
            """
            INSERT INTO vuln_stat_snapshots
              (id, domain_type, detected_stack, total_vulns,
               critical_count, high_count, medium_count, low_count,
               vuln_type_counts, security_score, security_grade, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                str(_uuid.uuid4()),
                domain_type,
                json.dumps(detected_stack),
                len(vulnerabilities),
                severity_counts.get("critical", 0),
                severity_counts.get("high", 0),
                severity_counts.get("medium", 0),
                severity_counts.get("low", 0),
                json.dumps(vuln_type_counts),
                score,
                grade,
            ),
        )


def suppress_vulnerability(vuln_id: str, reason: str, user_id: str) -> None:
    """오탐 신고 처리 — 상태를 suppressed로 변경하고 이유를 기록."""
    with pg_cursor() as cur:
        cur.execute(
            """
            UPDATE vulnerabilities
            SET status = 'suppressed',
                suppression_reason = %s,
                suppressed_by = %s,
                suppressed_at = NOW()
            WHERE vuln_id = %s
            """,
            (reason, user_id, vuln_id),
        )


# ─── Redis 캐시 유틸 ─────────────────────────────────────

def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    r = get_redis_client()
    r.setex(key, ttl_seconds, json.dumps(value))


def cache_get(key: str) -> Optional[Any]:
    r = get_redis_client()
    val = r.get(key)
    return json.loads(val) if val else None


def cache_ruleset(domain: str, stack_hash: str, ruleset: dict, ttl_seconds: int = 86400) -> None:
    cache_set(f"ruleset:{domain}:{stack_hash}", ruleset, ttl_seconds)


def get_cached_ruleset(domain: str, stack_hash: str) -> Optional[dict]:
    return cache_get(f"ruleset:{domain}:{stack_hash}")


# ─── CLI (디버그/운영 유틸) ──────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="VibeSafe DB 클라이언트 CLI")
    parser.add_argument("--get-scan", metavar="SCAN_ID", help="스캔 정보 조회")
    parser.add_argument("--ping", action="store_true", help="DB/Redis 연결 확인")
    args = parser.parse_args()

    if args.ping:
        try:
            with pg_cursor() as cur:
                cur.execute("SELECT 1")
            print("PostgreSQL: OK")
        except Exception as e:
            print(f"PostgreSQL: FAIL — {e}")
        try:
            r = get_redis_client()
            r.ping()
            print("Redis: OK")
        except Exception as e:
            print(f"Redis: FAIL — {e}")

    elif args.get_scan:
        result = get_scan(args.get_scan)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
