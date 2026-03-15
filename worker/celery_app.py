from __future__ import annotations
"""
worker/celery_app.py
Celery 앱 초기화 — tasks.py에서 임포트하여 사용
"""
import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://:vibesafe_dev_redis@localhost:6379/0")

celery_app = Celery(
    "vibesafe_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_soft_time_limit=300,   # 5분 소프트 타임아웃
    task_time_limit=360,        # 6분 하드 타임아웃
    worker_prefetch_multiplier=1,   # 스캔은 CPU 집약적 → 1개씩 처리
    task_acks_late=True,            # 완료 후 ack → 실패 시 재처리
)
