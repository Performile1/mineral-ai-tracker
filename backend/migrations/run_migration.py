"""
Database Migration Runner
Execute SQL migrations for Mineral AI Tracker
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
import sys

def execute_migration(sql_file_path):
    """Execute SQL migration file"""
    print(f"Executing migration: {sql_file_path}")
    
    # Read SQL file with UTF-8 encoding
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # Connect to database
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="mineral_ai_tracker",
        user="mineral_user",
        password="mineralpass123",
        cursor_factory=RealDictCursor
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()
            print("Migration executed successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <sql_file>")
        sys.exit(1)
    
    sql_file = sys.argv[1]
    execute_migration(sql_file)
