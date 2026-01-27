#!/usr/bin/env python3
"""
Database initialization and schema for orchestration system.
Creates SQLite tables for job tracking, state management, and health metrics.
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def init_database(db_path: str) -> None:
    """Initialize orchestration database with schema."""
    
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Jobs and runs tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                commit TEXT,
                version TEXT,
                status TEXT NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                triggered_by TEXT,
                environment TEXT,
                metadata TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)
        
        # Workflow dependencies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_dependencies (
                workflow TEXT PRIMARY KEY,
                depends_on TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)
        
        # State variables (replicated from GitHub)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state_variables (
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                source TEXT,
                synced_at TIMESTAMP,
                updated_at TIMESTAMP NOT NULL
            )
        """)
        
        # Health metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_metrics (
                timestamp TIMESTAMP PRIMARY KEY,
                service_status TEXT,
                database_size_mb REAL,
                disk_usage_percent REAL,
                container_statuses TEXT,
                tailscale_connected INTEGER,
                issues TEXT
            )
        """)
        
        # Audit log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                action TEXT NOT NULL,
                actor TEXT,
                details TEXT,
                result TEXT
            )
        """)
        
        # Initialize default workflow dependencies
        workflows = [
            ("ci", None),
            ("integration-tests", "ci"),
            ("security", None),
            ("deploy", "integration-tests"),
            ("health-check", None),
            ("recovery", "health-check"),
            ("rollback", None),
        ]
        
        for workflow, deps in workflows:
            cursor.execute("""
                INSERT OR IGNORE INTO workflow_dependencies (workflow, depends_on, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (workflow, deps, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        
        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_commit ON jobs(commit)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_timestamp ON health_metrics(timestamp DESC)")
        
        conn.commit()
        print(f"✅ Database initialized: {db_path}")
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    import os
    db_path = os.getenv("ORCHESTRATION_DB_PATH", "/data/state/orchestration.db")
    init_database(db_path)
