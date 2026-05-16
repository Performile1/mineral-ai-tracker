"""
Mineral AI Tracker - Celery Worker (PRD v10.0 Phase 10.3)
Version: 10.0
Description: Celery application for async task processing
"""

import os
from celery import Celery

# Celery application setup
celery_app = Celery(
    'mineral_ai_worker',
    broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,  # Process one task at a time (for Ollama)
)
