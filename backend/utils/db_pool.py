"""
Mineral AI Tracker - Database Connection Pool (PRD v10.0 Phase 10.3)
Version: 10.0
Description: Connection pooling for Celery workers to prevent DB exhaustion
"""

import os
import psycopg2
from psycopg2 import pool

# Connection pool for Celery workers
# This prevents DB connection exhaustion when multiple workers are spawned
connection_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=2,
    maxconn=10,
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=int(os.getenv('POSTGRES_PORT', 5432)),
    database=os.getenv('POSTGRES_DB', 'mineral_ai_tracker'),
    user=os.getenv('POSTGRES_USER', 'mineral_user'),
    password=os.getenv('POSTGRES_PASSWORD', 'mineralpass123'),
)


def get_pooled_connection():
    """Get a connection from the pool"""
    try:
        return connection_pool.getconn()
    except Exception as e:
        raise Exception(f"Failed to get connection from pool: {e}")


def return_connection(conn):
    """Return a connection to the pool"""
    try:
        connection_pool.putconn(conn)
    except Exception as e:
        raise Exception(f"Failed to return connection to pool: {e}")


def close_pool():
    """Close all connections in the pool"""
    connection_pool.closeall()
