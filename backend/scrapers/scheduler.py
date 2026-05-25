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
from utils.database import get_db_connection, release_db_connection


_scheduler: Optional[AsyncIOScheduler] = None


async def contract_decay_job() -> None:
    """
    Nightly cron (03:00 Europe/Stockholm) — Sprint 9.4

    Downgrades TAKE_OR_PAY and OFFTAKE edges whose contract_expiry_date has
    passed to STANDARD and clears the numeric volume.  Logs the count of
    degraded edges for admin-dashboard observability.
    """
    logger.info("⏰ [Contract Decay] Checking for expired contracts...")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE supply_chain_edges
                   SET contract_type           = 'STANDARD',
                       contract_volume_numeric = NULL
                 WHERE contract_expiry_date < CURRENT_DATE
                   AND contract_type IN ('TAKE_OR_PAY', 'OFFTAKE')
            """)
            degraded = cur.rowcount
            conn.commit()
        logger.info(
            f"✅ [Contract Decay] {degraded} edge(s) downgraded to STANDARD "
            "(contracts past expiry_date)"
        )
    except Exception as exc:
        conn.rollback()
        logger.error(f"[Contract Decay] Job failed: {exc}")
    finally:
        release_db_connection(conn)


async def omniscient_pipeline_job() -> None:
    """
    Nightly cron (07:00 Europe/Stockholm) — Sprint 16

    Runs the four Omniscient Expansion intelligence modules sequentially
    after the 06:00 Target List sweep has refreshed node data:
      1. Chokepoint Oracle   — raises friction on affected corridors
      2. Secondary Supply    — monitors scrap spread collapse
      3. M&A Predictor       — scores every PRODUCER node for buyout risk
      4. Sentiment Crawler   — writes early-warning labor signals
    Each module is error-isolated so one failure never blocks the others.
    """
    logger.info("⏰ 07:00 Omniscient Pipeline starting...")

    # 1 — Chokepoint Oracle
    try:
        from agents.chokepoint_oracle import run_chokepoint_oracle
        alerts = await run_chokepoint_oracle()
        logger.info(f"✅ Chokepoint Oracle: {len(alerts)} alert(s)")
    except Exception as exc:
        logger.error(f"Omniscient Pipeline: Chokepoint Oracle failed: {exc}")

    # 2 — Secondary Supply Engine
    try:
        from agents.secondary_supply import run_secondary_supply_engine
        triggered = await run_secondary_supply_engine()
        logger.info(f"✅ Secondary Supply Engine: {len(triggered)} alert(s)")
    except Exception as exc:
        logger.error(f"Omniscient Pipeline: Secondary Supply Engine failed: {exc}")

    # 3 — M&A Predictor (full PRODUCER sweep)
    try:
        from agents.ma_predictor import run_ma_predictor_sweep
        predictions = await run_ma_predictor_sweep()
        logger.info(f"✅ M&A Predictor: {len(predictions)} node(s) scored")
    except Exception as exc:
        logger.error(f"Omniscient Pipeline: M&A Predictor failed: {exc}")

    # 4 — Sentiment Crawler
    try:
        from workers.sentiment_crawler import run_sentiment_crawl
        warnings = await run_sentiment_crawl()
        logger.info(f"✅ Sentiment Crawler: {len(warnings)} early warning(s)")
    except Exception as exc:
        logger.error(f"Omniscient Pipeline: Sentiment Crawler failed: {exc}")

    logger.info("✅ Omniscient Pipeline complete")


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
    _scheduler.add_job(
        contract_decay_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="contract_decay",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        omniscient_pipeline_job,
        trigger=CronTrigger(hour=7, minute=0),
        id="omniscient_pipeline",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info(
        "📅 APScheduler started — Target List sweep 06:00 "
        "| Contract Decay 03:00 "
        "| Omniscient Pipeline 07:00 (Europe/Stockholm)"
    )
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
