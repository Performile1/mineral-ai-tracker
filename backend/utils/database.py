"""
Mineral AI Tracker - Database Utilities
Description: Database connection and data persistence utilities
PRD v10.0 Phase 10.3: Added connection pooling for Celery workers
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from loguru import logger

from models.macro import MineralDemandSignal


# Phase 10.3: Connection pooling for Celery workers
connection_pool = None

def get_connection_pool():
    """Get or create connection pool for Celery workers"""
    global connection_pool
    if connection_pool is None:
        try:
            connection_pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "mineral_ai_tracker"),
                user=os.getenv("POSTGRES_USER", "mineral_user"),
                password=os.getenv("POSTGRES_PASSWORD", "mineralpass123")
            )
            logger.info("Created database connection pool for Celery workers")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    return connection_pool


def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "mineral_ai_tracker"),
            user=os.getenv("POSTGRES_USER", "mineral_user"),
            password=os.getenv("POSTGRES_PASSWORD", "mineralpass123")
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def get_pooled_connection():
    """Get connection from pool (for Celery workers)"""
    try:
        pool = get_connection_pool()
        return pool.getconn()
    except Exception as e:
        logger.error(f"Failed to get connection from pool: {e}")
        raise


def return_pooled_connection(conn):
    """Return connection to pool"""
    try:
        pool = get_connection_pool()
        pool.putconn(conn)
    except Exception as e:
        logger.error(f"Failed to return connection to pool: {e}")


def save_macro_signals(signals: list[MineralDemandSignal]):
    """
    Save macro demand signals to database
    
    Args:
        signals: List of MineralDemandSignal objects
    """
    if not signals:
        logger.warning("No signals to save")
        return
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        saved_count = 0
        for signal in signals:
            # Only save signals with confidence > 0.6 (Zero-Hallucination)
            if signal.confidence <= 0.6:
                continue
            
            data = {
                "mineral": signal.mineral,
                "sector": signal.sector.value,
                "supply_deficit_score": signal.supply_deficit_score,
                "catalyst_event": signal.catalyst_event,
                "source_url": signal.source_url,
                "logged_at": signal.logged_at
            }
            
            # Insert into macro_demand table
            cur.execute(
                """
                INSERT INTO public.macro_demand 
                (mineral, sector, supply_deficit_score, catalyst_event, source_url, logged_at)
                VALUES (%(mineral)s, %(sector)s, %(supply_deficit_score)s, %(catalyst_event)s, %(source_url)s, %(logged_at)s)
                ON CONFLICT DO NOTHING
                """,
                data
            )
            saved_count += 1
        
        conn.commit()
        logger.info(f"Saved {saved_count} macro signals to database")
        
        cur.close()
        
    except Exception as e:
        logger.error(f"Error saving macro signals: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
