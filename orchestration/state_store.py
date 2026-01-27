#!/usr/bin/env python3
"""
State management for orchestration system.
Provides database interface for jobs, workflows, and health metrics.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class StateStore:
    """Persistent state storage for CI/CD orchestration."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with JSON support."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ===== Job Management =====
    
    def create_job(
        self,
        job_id: str,
        job_type: str,
        triggered_by: str = "api",
        **kwargs
    ) -> bool:
        """Create a new job record."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO jobs (
                    id, type, commit, version, status, triggered_by, 
                    environment, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job_type,
                kwargs.get("commit"),
                kwargs.get("version"),
                "queued",
                triggered_by,
                kwargs.get("environment", "test"),
                json.dumps({k: v for k, v in kwargs.items() if k not in ["commit", "version", "environment"]}),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            conn.commit()
            logger.info(f"Created job {job_id} ({job_type})")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to create job {job_id}: {e}")
            return False
        finally:
            conn.close()
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if row:
                return {
                    "id": row["id"],
                    "type": row["type"],
                    "status": row["status"],
                    "commit": row["commit"],
                    "version": row["version"],
                    "triggered_by": row["triggered_by"],
                    "environment": row["environment"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "metadata": json.loads(row["metadata"] or "{}"),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None
        finally:
            conn.close()
    
    def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs
    ) -> bool:
        """Update job status."""
        conn = self._get_connection()
        try:
            updates = {"status": status, "updated_at": datetime.utcnow().isoformat()}
            if "completed_at" in kwargs and status in ["success", "failure", "recovered"]:
                updates["completed_at"] = kwargs.get("completed_at", datetime.utcnow().isoformat())
            if "started_at" in kwargs and status == "running":
                updates["started_at"] = kwargs.get("started_at", datetime.utcnow().isoformat())
            
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [job_id]
            
            conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
            conn.commit()
            logger.info(f"Updated job {job_id} status to {status}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to update job {job_id}: {e}")
            return False
        finally:
            conn.close()
    
    def list_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List jobs with optional filtering."""
        conn = self._get_connection()
        try:
            query = "SELECT * FROM jobs WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            if job_type:
                query += " AND type = ?"
                params.append(job_type)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    # ===== State Variables =====
    
    def set_state_variable(
        self,
        name: str,
        value: str,
        source: str = "api"
    ) -> bool:
        """Set or update a state variable."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO state_variables 
                (name, value, source, updated_at)
                VALUES (?, ?, ?, ?)
            """, (name, value, source, datetime.utcnow().isoformat()))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to set state variable {name}: {e}")
            return False
        finally:
            conn.close()
    
    def get_state_variable(self, name: str) -> Optional[str]:
        """Get a state variable."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT value FROM state_variables WHERE name = ?", (name,)
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    
    def get_all_state_variables(self) -> Dict[str, str]:
        """Get all state variables."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT name, value FROM state_variables"
            ).fetchall()
            return {row[0]: row[1] for row in rows}
        finally:
            conn.close()
    
    # ===== Health Metrics =====
    
    def record_health_metric(
        self,
        service_status: str,
        database_size_mb: float,
        disk_usage_percent: float,
        container_statuses: Dict[str, str],
        tailscale_connected: bool,
        issues: List[str]
    ) -> bool:
        """Record health metric snapshot."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO health_metrics 
                (timestamp, service_status, database_size_mb, disk_usage_percent, 
                 container_statuses, tailscale_connected, issues)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                service_status,
                database_size_mb,
                disk_usage_percent,
                json.dumps(container_statuses),
                int(tailscale_connected),
                json.dumps(issues)
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to record health metric: {e}")
            return False
        finally:
            conn.close()
    
    def get_latest_health_metric(self) -> Optional[Dict[str, Any]]:
        """Get latest health metric."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM health_metrics ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            if row:
                return {
                    "timestamp": row["timestamp"],
                    "service_status": row["service_status"],
                    "database_size_mb": row["database_size_mb"],
                    "disk_usage_percent": row["disk_usage_percent"],
                    "container_statuses": json.loads(row["container_statuses"]),
                    "tailscale_connected": bool(row["tailscale_connected"]),
                    "issues": json.loads(row["issues"]),
                }
            return None
        finally:
            conn.close()
    
    # ===== Audit Log =====
    
    def log_action(
        self,
        action: str,
        actor: str,
        details: Dict[str, Any],
        result: str
    ) -> bool:
        """Log an action for audit trail."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO audit_log (timestamp, action, actor, details, result)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                action,
                actor,
                json.dumps(details),
                result
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to log action: {e}")
            return False
        finally:
            conn.close()
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
