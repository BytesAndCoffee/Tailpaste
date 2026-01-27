#!/usr/bin/env python3
"""
Orchestration API Server
REST API for GitHub Actions to trigger and query CI/CD workflows.
Provides endpoints for job submission, status queries, and health checks.
"""

import os
import uuid
import logging
import json
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Tuple

from flask import Flask, request, jsonify
from orchestration.state_store import StateStore

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state store
state_store = None


def init_state_store():
    """Initialize state store on app startup."""
    global state_store
    db_path = os.getenv("ORCHESTRATION_DB_PATH", "/data/state/orchestration.db")
    state_store = StateStore(db_path)
    logger.info(f"Initialized state store: {db_path}")


def create_app():
    """Create and configure Flask app."""
    app = Flask(__name__)
    app.config['JSON_SORT_KEYS'] = False
    
    # Initialize state store on startup
    with app.app_context():
        init_state_store()
    
    # ===== Error Handlers =====
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request"}), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        return jsonify({"error": "Internal server error"}), 500
    
    # ===== Middleware =====
    
    def require_json(f):
        """Decorator to require JSON request body."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({"error": "Request must be JSON"}), 400
            return f(*args, **kwargs)
        return decorated_function
    
    # ===== Health & Status Endpoints =====
    
    @app.route('/api/health/status', methods=['GET'])
    def health_status():
        """Get system health status."""
        try:
            latest_metric = state_store.get_latest_health_metric()
            
            if latest_metric:
                return jsonify({
                    "status": latest_metric["service_status"],
                    "timestamp": latest_metric["timestamp"],
                    "metrics": {
                        "database_size_mb": latest_metric["database_size_mb"],
                        "disk_usage_percent": latest_metric["disk_usage_percent"],
                    },
                    "container_statuses": latest_metric["container_statuses"],
                    "tailscale_connected": latest_metric["tailscale_connected"],
                    "issues": latest_metric["issues"]
                }), 200
            else:
                return jsonify({
                    "status": "initializing",
                    "timestamp": datetime.utcnow().isoformat()
                }), 200
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/state', methods=['GET'])
    def get_state():
        """Get all state variables for GitHub Actions sync."""
        try:
            variables = state_store.get_all_state_variables()
            return jsonify({
                "variables": variables,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
        except Exception as e:
            logger.error(f"State query error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ===== Job Management Endpoints =====
    
    @app.route('/api/trigger/ci', methods=['POST'])
    @require_json
    def trigger_ci():
        """Trigger CI workflow."""
        try:
            data = request.get_json()
            
            # Validate required fields
            if not data.get("commit"):
                return jsonify({"error": "Missing 'commit' field"}), 400
            
            job_id = f"ci-{uuid.uuid4().hex[:8]}"
            
            success = state_store.create_job(
                job_id=job_id,
                job_type="ci",
                triggered_by="github-actions",
                commit=data.get("commit"),
                branch=data.get("branch", "develop"),
                python_versions=data.get("python_versions", ["3.10", "3.11", "3.12"]),
                github_run_id=data.get("github_run_id")
            )
            
            if success:
                state_store.log_action(
                    action="trigger_ci",
                    actor="github-actions",
                    details={"job_id": job_id, "commit": data.get("commit")},
                    result="success"
                )
                return jsonify({
                    "job_id": job_id,
                    "status": "queued",
                    "message": "CI workflow queued"
                }), 201
            else:
                return jsonify({"error": "Failed to create job"}), 500
        except Exception as e:
            logger.error(f"CI trigger error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/trigger/integration-tests', methods=['POST'])
    @require_json
    def trigger_integration_tests():
        """Trigger integration tests."""
        try:
            data = request.get_json()
            
            if not data.get("commit"):
                return jsonify({"error": "Missing 'commit' field"}), 400
            
            job_id = f"int-{uuid.uuid4().hex[:8]}"
            
            success = state_store.create_job(
                job_id=job_id,
                job_type="integration-tests",
                triggered_by="github-actions",
                commit=data.get("commit"),
                python_version=data.get("python_version", "3.11"),
                github_run_id=data.get("github_run_id")
            )
            
            if success:
                state_store.log_action(
                    action="trigger_integration_tests",
                    actor="github-actions",
                    details={"job_id": job_id, "commit": data.get("commit")},
                    result="success"
                )
                return jsonify({
                    "job_id": job_id,
                    "status": "queued",
                    "message": "Integration tests queued"
                }), 201
            else:
                return jsonify({"error": "Failed to create job"}), 500
        except Exception as e:
            logger.error(f"Integration tests trigger error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/trigger/deploy', methods=['POST'])
    @require_json
    def trigger_deploy():
        """Trigger deployment."""
        try:
            data = request.get_json()
            
            if not data.get("version"):
                return jsonify({"error": "Missing 'version' field"}), 400
            
            job_id = f"dep-{uuid.uuid4().hex[:8]}"
            
            success = state_store.create_job(
                job_id=job_id,
                job_type="deploy",
                triggered_by="github-actions",
                version=data.get("version"),
                environment=data.get("environment", "production"),
                github_run_id=data.get("github_run_id")
            )
            
            if success:
                state_store.log_action(
                    action="trigger_deploy",
                    actor="github-actions",
                    details={"job_id": job_id, "version": data.get("version")},
                    result="success"
                )
                return jsonify({
                    "job_id": job_id,
                    "status": "queued",
                    "message": "Deployment queued"
                }), 201
            else:
                return jsonify({"error": "Failed to create job"}), 500
        except Exception as e:
            logger.error(f"Deploy trigger error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/job/<job_id>', methods=['GET'])
    def get_job(job_id: str):
        """Get job status and details."""
        try:
            job = state_store.get_job(job_id)
            
            if not job:
                return jsonify({"error": "Job not found"}), 404
            
            return jsonify(job), 200
        except Exception as e:
            logger.error(f"Job query error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/job/<job_id>/status', methods=['PATCH'])
    @require_json
    def update_job_status(job_id: str):
        """Update job status (internal use by orchestrator)."""
        try:
            data = request.get_json()
            
            if not data.get("status"):
                return jsonify({"error": "Missing 'status' field"}), 400
            
            success = state_store.update_job_status(
                job_id=job_id,
                status=data.get("status"),
                completed_at=data.get("completed_at"),
                started_at=data.get("started_at")
            )
            
            if success:
                state_store.log_action(
                    action="update_job_status",
                    actor="orchestrator",
                    details={"job_id": job_id, "status": data.get("status")},
                    result="success"
                )
                return jsonify({"message": "Status updated"}), 200
            else:
                return jsonify({"error": "Failed to update status"}), 500
        except Exception as e:
            logger.error(f"Status update error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ===== Recovery & Rollback =====
    
    @app.route('/api/recovery/execute', methods=['POST'])
    @require_json
    def execute_recovery():
        """Execute recovery procedure."""
        try:
            data = request.get_json()
            
            if not data.get("recovery_action"):
                return jsonify({"error": "Missing 'recovery_action' field"}), 400
            
            recovery_id = f"rec-{uuid.uuid4().hex[:8]}"
            
            success = state_store.create_job(
                job_id=recovery_id,
                job_type="recovery",
                triggered_by="github-actions",
                recovery_action=data.get("recovery_action"),
                affected_workflow=data.get("affected_workflow")
            )
            
            if success:
                state_store.log_action(
                    action="execute_recovery",
                    actor="github-actions",
                    details={"recovery_id": recovery_id, "action": data.get("recovery_action")},
                    result="success"
                )
                return jsonify({
                    "recovery_id": recovery_id,
                    "status": "queued",
                    "message": "Recovery procedure queued"
                }), 201
            else:
                return jsonify({"error": "Failed to queue recovery"}), 500
        except Exception as e:
            logger.error(f"Recovery trigger error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/rollback/execute', methods=['POST'])
    @require_json
    def execute_rollback():
        """Execute rollback procedure."""
        try:
            data = request.get_json()
            
            if not data.get("target_version"):
                return jsonify({"error": "Missing 'target_version' field"}), 400
            
            rollback_id = f"roll-{uuid.uuid4().hex[:8]}"
            
            success = state_store.create_job(
                job_id=rollback_id,
                job_type="rollback",
                triggered_by="github-actions",
                target_version=data.get("target_version"),
                reason=data.get("reason")
            )
            
            if success:
                state_store.log_action(
                    action="execute_rollback",
                    actor="github-actions",
                    details={"rollback_id": rollback_id, "target_version": data.get("target_version")},
                    result="success"
                )
                return jsonify({
                    "rollback_id": rollback_id,
                    "status": "queued",
                    "message": "Rollback procedure queued"
                }), 201
            else:
                return jsonify({"error": "Failed to queue rollback"}), 500
        except Exception as e:
            logger.error(f"Rollback trigger error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ===== Admin Endpoints =====
    
    @app.route('/api/admin/jobs', methods=['GET'])
    def list_jobs():
        """List jobs with optional filtering."""
        try:
            status = request.args.get("status")
            job_type = request.args.get("type")
            limit = int(request.args.get("limit", 50))
            
            jobs = state_store.list_jobs(status=status, job_type=job_type, limit=limit)
            return jsonify({"jobs": jobs}), 200
        except Exception as e:
            logger.error(f"Job list error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/admin/audit-log', methods=['GET'])
    def get_audit_log():
        """Get audit log entries."""
        try:
            limit = int(request.args.get("limit", 100))
            entries = state_store.get_audit_log(limit=limit)
            return jsonify({"entries": entries}), 200
        except Exception as e:
            logger.error(f"Audit log error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/sync-variables', methods=['POST'])
    @require_json
    def sync_variables():
        """Sync state variables to GitHub Actions."""
        try:
            data = request.get_json()
            variables = data.get("variables", {})
            
            for name, value in variables.items():
                state_store.set_state_variable(name, str(value), source="api")
            
            return jsonify({"message": f"Synced {len(variables)} variables"}), 200
        except Exception as e:
            logger.error(f"Variable sync error: {e}")
            return jsonify({"error": str(e)}), 500
    
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)
