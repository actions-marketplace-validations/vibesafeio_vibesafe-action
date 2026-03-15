"""
worker/tasks.py
Celery 스캔 파이프라인 태스크.
workflows/scan_submission.md Step 1~10 순서를 Python subprocess로 실행한다.
"""
from __future__ import annotations
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import boto3
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from worker.celery_app import celery_app
from tools.infra.db_client import (
    update_scan_status,
    save_scan_results,
    save_vulnerabilities,
    record_stat_snapshot,
    get_pg_connection,
)

logger = logging.getLogger(__name__)

# ─── S3 클라이언트 ────────────────────────────────────────────────────────

def get_s3():
    is_local = os.environ.get("NODE_ENV") == "development" or os.environ.get("S3_ENDPOINT")
    kwargs = dict(region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))
    if is_local:
        kwargs.update(
            endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:9000"),
            aws_access_key_id=os.environ.get("MINIO_ROOT_USER", "vibesafe_minio_user"),
            aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", "vibesafe_minio_password"),
        )
    return boto3.client("s3", **kwargs)


BUCKETS = {
    "uploads": os.environ.get("S3_BUCKET_UPLOADS", "vibesafe-uploads"),
    "artifacts": os.environ.get("S3_BUCKET_ARTIFACTS", "vibesafe-artifacts"),
}

# ─── 헬퍼 ────────────────────────────────────────────────────────────────

def run_tool(cmd: list[str], timeout: int = 180) -> dict:
    """Python tool 스크립트를 실행하고 JSON 결과를 반환한다."""
    result = subprocess.run(
        [sys.executable] + cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode not in (0, 1):  # semgrep: 1 = findings found
        raise RuntimeError(f"도구 실행 실패 ({cmd[0]}): {result.stderr[:500]}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw_output": result.stdout}


def save_artifact_record(scan_id: str, artifact_type: str, s3_key: str, bucket: str, size: int = 0):
    """scan_artifacts 테이블에 S3 파일 경로를 기록한다."""
    import uuid as _uuid
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scan_artifacts (id, scan_id, artifact_type, s3_key, s3_bucket, file_size_bytes, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (scan_id, artifact_type) DO UPDATE
                SET s3_key = EXCLUDED.s3_key, file_size_bytes = EXCLUDED.file_size_bytes
                """,
                (str(_uuid.uuid4()), scan_id, artifact_type, s3_key, bucket, size),
            )
        conn.commit()


# ─── 메인 태스크 ──────────────────────────────────────────────────────────

@celery_app.task(name="worker.tasks.scan_pipeline", bind=True, max_retries=1)
def scan_pipeline(self: Task, scanId: str, userId: str, s3Key: str, domainType: str, scanDepth: str):
    """
    보안 스캔 파이프라인 — scan_submission.md Step 1~10 구현.
    """
    s3 = get_s3()
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"vibesafe_scan_{scanId[:8]}_"))

    try:
        update_scan_status(scanId, "RUNNING")
        logger.info(f"[{scanId}] 스캔 시작 — 도메인:{domainType}, 깊이:{scanDepth}")

        # ── Step 1: S3에서 소스 파일 다운로드 ─────────────────────────────
        zip_path = tmp_dir / "source.zip"
        s3.download_file(BUCKETS["uploads"], s3Key, str(zip_path))
        logger.info(f"[{scanId}] S3 다운로드 완료: {zip_path.stat().st_size} bytes")

        # ── Step 2: 파일 압축 해제 및 검증 ───────────────────────────────
        source_dir = tmp_dir / "source"
        extract_result = run_tool([
            "tools/infra/file_extractor.py",
            "--input", str(zip_path),
            "--output", str(source_dir),
        ])
        if "error" in extract_result:
            raise ValueError(f"파일 추출 실패: {extract_result['error']}")

        # ── Step 3: 기술 스택 자동 탐지 ──────────────────────────────────
        stack_result = run_tool([
            "tools/scanner/sast_runner.py",
            "--detect-stack",
            "--path", str(source_dir),
        ])
        detected_stack = stack_result.get("detected_stack", [])
        logger.info(f"[{scanId}] 탐지된 스택: {detected_stack}")

        # ── Step 4: 도메인 규칙셋 로드 ───────────────────────────────────
        ruleset_result = run_tool([
            "tools/scanner/domain_rule_engine.py",
            "--domain", domainType,
            "--stack", ",".join(detected_stack) if detected_stack else "",
        ])
        rule_ids = ruleset_result.get("semgrep_configs", ["p/owasp-top-ten"])

        # ── Step 5: SAST 실행 ─────────────────────────────────────────────
        sast_output = tmp_dir / "sast.sarif"
        run_tool([
            "tools/scanner/sast_runner.py",
            "--path", str(source_dir),
            "--rules", ",".join(rule_ids),
            "--output", str(sast_output),
            "--timeout", "180",
        ], timeout=200)

        # ── Step 6: SCA 실행 ──────────────────────────────────────────────
        sca_output = tmp_dir / "sca.json"
        run_tool([
            "tools/scanner/sca_runner.py",
            "--path", str(source_dir),
            "--output", str(sca_output),
        ])

        # ── Step 7: 시크릿 스캐닝 ────────────────────────────────────────
        secrets_output = tmp_dir / "secrets.json"
        run_tool([
            "tools/scanner/secret_scanner.py",
            "--path", str(source_dir),
            "--output", str(secrets_output),
        ])

        # ── Step 8: DAST (deep 모드 전용) ────────────────────────────────
        dast_output = tmp_dir / "dast.json"
        if scanDepth == "deep":
            try:
                run_tool([
                    "tools/infra/sandbox_manager.py",
                    "--create",
                    "--scan-id", scanId,
                    "--source-path", str(source_dir),
                ], timeout=60)
                run_tool([
                    "tools/scanner/dast_runner.py",
                    "--target", f"http://sandbox-{scanId}:3000",
                    "--scan-type", "baseline",
                    "--output", str(dast_output),
                    "--timeout", "120",
                ], timeout=150)
            except Exception as e:
                logger.warning(f"[{scanId}] DAST 실패 (건너뜀): {e}")
            finally:
                subprocess.run(
                    [sys.executable, "tools/infra/sandbox_manager.py", "--destroy", "--scan-id", scanId],
                    capture_output=True,
                )

        # ── Step 9: 점수 산출 ─────────────────────────────────────────────
        score_args = [
            "tools/report/score_calculator.py",
            "--domain", domainType,
        ]
        if sast_output.exists():
            score_args += ["--sast-result", str(sast_output)]
        if sca_output.exists():
            score_args += ["--sca-result", str(sca_output)]
        if secrets_output.exists():
            score_args += ["--secret-result", str(secrets_output)]

        score_result = run_tool(score_args)
        save_scan_results(scanId, score_result)
        logger.info(f"[{scanId}] 보안 점수: {score_result.get('score')} ({score_result.get('grade')})")

        # ── Step 10: 자동 수정 제안 ───────────────────────────────────────
        vulns_json = tmp_dir / "vulnerabilities.json"
        patches_dir = tmp_dir / "patches"

        # 취약점 통합 (SAST + SCA + Secrets)
        all_vulns: list[dict] = []

        # SAST: SARIF 형식 → 직접 파싱 (data.get("vulnerabilities") 로 읽으면 빈 배열)
        if sast_output.exists():
            from tools.report.score_calculator import parse_sarif_vulnerabilities
            sast_vulns = parse_sarif_vulnerabilities(sast_output)
            for i, v in enumerate(sast_vulns):
                v.setdefault("vuln_id", f"{scanId[:8]}-sast-{i:04d}")
                v.setdefault("scan_id", scanId)
            all_vulns.extend(sast_vulns)

        # SCA + Secrets: JSON 형식
        for result_file, source in [(sca_output, "sca"), (secrets_output, "secrets")]:
            if result_file.exists():
                data = json.loads(result_file.read_text())
                vulns_from_file = data.get("vulnerabilities", data.get("secrets", []))
                for i, v in enumerate(vulns_from_file):
                    v.setdefault("vuln_id", f"{scanId[:8]}-{source}-{i:04d}")
                    v.setdefault("scan_id", scanId)
                all_vulns.extend(vulns_from_file)

        vulns_json.write_text(json.dumps({"vulnerabilities": all_vulns}))

        run_tool([
            "tools/remediation/auto_fix_generator.py",
            "--scan-id", scanId,
            "--vuln-file", str(vulns_json),
            "--source-path", str(source_dir),
            "--output", str(patches_dir),
        ], timeout=120)

        # 취약점 DB 저장
        if all_vulns:
            save_vulnerabilities(scanId, all_vulns)

        # 익명 통계 기록 (사용자/파일 정보 없음)
        try:
            record_stat_snapshot(
                domainType, detected_stack, all_vulns,
                score_result.get("score", 0), score_result.get("grade", "F"),
            )
        except Exception as e:
            logger.warning(f"[{scanId}] 통계 기록 실패 (건너뜀): {e}")

        # ── 리포트 생성 ───────────────────────────────────────────────────
        report_output = tmp_dir / "report.html"
        compliance_output = tmp_dir / "compliance.json"

        run_tool([
            "tools/report/compliance_checker.py",
            "--domain", domainType,
            "--scan-results", str(vulns_json),
        ])

        run_tool([
            "tools/report/pdf_generator.py",
            "--scan-id", scanId,
            "--format", "html",
            "--language", "ko",
            "--output", str(report_output),
            "--score-file", str(tmp_dir / "score.json"),
            "--vulns-file", str(vulns_json),
        ])

        # ── S3에 아티팩트 업로드 ──────────────────────────────────────────
        artifact_map = {
            "sast_sarif": sast_output,
            "sca_json": sca_output,
            "secrets_json": secrets_output,
            "report_pdf": report_output,
        }
        if dast_output.exists():
            artifact_map["dast_json"] = dast_output

        for artifact_type, file_path in artifact_map.items():
            if file_path.exists():
                s3_key = f"artifacts/{scanId}/{file_path.name}"
                s3.upload_file(str(file_path), BUCKETS["artifacts"], s3_key)
                save_artifact_record(scanId, artifact_type, s3_key, BUCKETS["artifacts"], file_path.stat().st_size)

        update_scan_status(scanId, "COMPLETED")
        logger.info(f"[{scanId}] 스캔 완료")

    except SoftTimeLimitExceeded:
        update_scan_status(scanId, "FAILED", "스캔 시간 초과 (300초)")
        logger.error(f"[{scanId}] 타임아웃")
        raise

    except Exception as e:
        error_msg = str(e)[:500]
        update_scan_status(scanId, "FAILED", error_msg)
        logger.error(f"[{scanId}] 스캔 실패: {error_msg}", exc_info=True)
        raise

    finally:
        # .tmp/ 정리
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
