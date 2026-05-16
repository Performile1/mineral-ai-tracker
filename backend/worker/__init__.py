"""
Mineral AI Tracker - Celery Worker Package
Version: 10.0
Description: Celery task definitions for async job processing
"""

from .tasks import task_run_backtest

__all__ = ["task_run_backtest"]
