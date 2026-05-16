"""
Mineral AI Tracker - APScheduler (PRD v8.3)
Version: 8.3
Description: Daily 06:00 sweep of the Target List, one URL at a time
             (Sequential Memory-Optimized Mode).
"""

import asyncio
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from scrapers.target_list import iter_targets
from scrapers.crawler import scrape_and_send


_scheduler: Optional[AsyncIOScheduler] = None


async def run_target_list_sweep() -> None:
    """
    Iterate through The Target List sequentially.

    Sequential is important: each call to /api/intelligence/analyze loads
    Phi-3 / Mistral / Llama-3 into memory in turn with keep_alive=0, so
    running multiple URLs in parallel would defeat the memory savings.
    """
    logger.info("⏰ 06:00 Target List sweep starting...")
    count = 0
    failures = 0
    for tier, name, url in iter_targets():
        try:
            result = await scrape_and_send(url=url, source=f"{tier}:{name}")
            if result is None:
                failures += 1
            count += 1
            # Brief breather to let the OS reclaim RAM between SLM cycles
            await asyncio.sleep(2)
        except Exception as e:
            failures += 1
            logger.error(f"Sweep error for {name} ({url}): {e}")
    logger.info(
        f"✅ Target List sweep finished. Processed: {count}, failures: {failures}"
    )


def start_scheduler() -> AsyncIOScheduler:
    """
    Start the APScheduler. Triggers the Target List sweep every day at 06:00.
    Safe to call multiple times - returns the running instance.
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        logger.info("Scheduler already running")
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="Europe/Stockholm")
    _scheduler.add_job(
        run_target_list_sweep,
        trigger=CronTrigger(hour=6, minute=0),
        id="target_list_sweep",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("📅 APScheduler started - Target List sweep at 06:00 Europe/Stockholm")
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
