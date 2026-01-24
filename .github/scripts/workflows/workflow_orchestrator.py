#!/usr/bin/env python3
"""
Workflow Orchestrator - Comprehensive workflow dependency validation and state management
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


class WorkflowOrchestrator:
    def __init__(self, repo: str, session_id: str):
        self.repo = repo
        self.session_id = session_id
        self.workflow_states = {}
        self.dependency_graph = {
            'ci': {'depends_on': [], 'triggers': ['integration-test']},
            'integration-test': {'depends_on': ['ci'], 'triggers': ['deploy']},
            'deploy': {'depends_on': ['integration-test'], 'triggers': ['health-monitor']},
            'health-monitor': {'depends_on': [], 'triggers': ['recovery']},
            'recovery': {'depends_on': ['health-monitor'], 'triggers': ['deploy']},
            'manual-rollback': {'depends_on': [], 'triggers': []}
        }
        self.critical_workflows = ['ci', 'integration-test', 'deploy']
        self.monitoring_workflows = ['health-monitor', 'recovery']
        self.manual_workflows = ['manual-rollback']
    
    def get_workflow_runs(self, workflow: str, limit: int = 10) -> List[Dict]:
        """Get recent workflow runs"""
        try:
            cmd = ['gh', 'run', 'list', '--workflow', f'{workflow}.yml', '--limit', str(limit), '--json', 'databaseId,status,conclusion,createdAt,updatedAt,headSha']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                print(f"Warning: Could not get runs for workflow {workflow}: {result.stderr}")
                return []
        except Exception as e:
            print(f"Error getting workflow runs for {workflow}: {e}")
            return []
    
    def get_workflow_state(self, workflow: str) -> Dict:
        """Get comprehensive workflow state"""
        runs = self.get_workflow_runs(workflow, 5)
        
        if not runs:
            return {
                'status': 'unknown',
                'last_run': None,
                'recent_runs': [],
                'health': 'unknown'
            }
        
        latest_run = runs[0]
        
        # Determine workflow health based on recent runs
        recent_conclusions = [run.get('conclusion') for run in runs[:3] if run.get('conclusion')]
        
        if not recent_conclusions:
            health = 'unknown'
        elif all(c == 'success' for c in recent_conclusions):
            health = 'healthy'
        elif any(c == 'success' for c in recent_conclusions):
            health = 'degraded'
        else:
            health = 'unhealthy'
        
        return {
            'status': latest_run.get('status', 'unknown'),
            'conclusion': latest_run.get('conclusion'),
            'last_run': latest_run,
            'recent_runs': runs,
            'health': health,
            'last_updated': latest_run.get('updatedAt'),
            'head_sha': latest_run.get('headSha')
        }
    
    def validate_dependencies(self, workflow: str) -> Tuple[bool, List[str]]:
        """Validate that workflow dependencies are satisfied"""
        issues = []
        
        if workflow not in self.dependency_graph:
            issues.append(f"Unknown workflow: {workflow}")
            return False, issues
        
        dependencies = self.dependency_graph[workflow]['depends_on']
        
        for dep in dependencies:
            dep_state = self.get_workflow_state(dep)
            
            if dep_state['health'] == 'unhealthy':
                issues.append(f"Dependency {dep} is unhealthy")
            elif dep_state['status'] == 'in_progress':
                issues.append(f"Dependency {dep} is still running")
            elif dep_state['conclusion'] == 'failure':
                issues.append(f"Dependency {dep} failed in last run")
        
        return len(issues) == 0, issues
    
    def check_workflow_sequencing(self) -> Dict[str, Dict]:
        """Check if workflows are running in proper sequence"""
        sequencing_issues = {}
        
        for workflow, config in self.dependency_graph.items():
            state = self.get_workflow_state(workflow)
            issues = []
            
            # Check if workflow is running when dependencies haven't completed
            if state['status'] == 'in_progress':
                for dep in config['depends_on']:
                    dep_state = self.get_workflow_state(dep)
                    if dep_state['status'] == 'in_progress':
                        issues.append(f"Running concurrently with dependency {dep}")
                    elif dep_state['conclusion'] != 'success':
                        issues.append(f"Running despite dependency {dep} not successful")
            
            if issues:
                sequencing_issues[workflow] = {
                    'issues': issues,
                    'state': state
                }
        
        return sequencing_issues
    
    def get_system_state_consistency(self) -> Dict:
        """Check consistency of system state across workflows"""
        try:
            # Get key state variables
            cmd = ['gh', 'variable', 'list', '--repo', self.repo, '--json', 'name,value']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {'error': 'Could not retrieve system variables'}
            
            variables = {var['name']: var['value'] for var in json.loads(result.stdout)}
            
            # Check key consistency points
            consistency_checks = {
                'deployment_state': self._check_deployment_consistency(variables),
                'circuit_breaker_state': self._check_circuit_breaker_consistency(variables),
                'artifact_state': self._check_artifact_consistency(variables),
                'recovery_state': self._check_recovery_consistency(variables)
            }
            
            return consistency_checks
            
        except Exception as e:
            return {'error': f'State consistency check failed: {e}'}
    
    def _check_deployment_consistency(self, variables: Dict[str, str]) -> Dict:
        """Check deployment state consistency"""
        deployed_digest = variables.get('DEPLOYED_ARTIFACT_DIGEST', '')
        deployment_status = variables.get('DEPLOYMENT_STATUS', '')
        deployment_in_progress = variables.get('DEPLOYMENT_IN_PROGRESS', 'false')
        
        issues = []
        
        if deployment_in_progress == 'true':
            deployment_started_at = variables.get('DEPLOYMENT_STARTED_AT', '')
            if deployment_started_at:
                # Check if deployment has been running too long (>30 minutes)
                try:
                    started_time = datetime.fromisoformat(deployment_started_at.replace('Z', '+00:00'))
                    if (datetime.now(timezone.utc) - started_time).total_seconds() > 1800:
                        issues.append('Deployment has been in progress for over 30 minutes')
                except:
                    issues.append('Invalid deployment start timestamp')
        
        if not deployed_digest and deployment_status == 'successful':
            issues.append('Deployment marked successful but no artifact digest recorded')
        
        return {
            'status': 'consistent' if not issues else 'inconsistent',
            'issues': issues,
            'deployed_digest': deployed_digest,
            'deployment_status': deployment_status,
            'deployment_in_progress': deployment_in_progress == 'true'
        }
    
    def _check_circuit_breaker_consistency(self, variables: Dict[str, str]) -> Dict:
        """Check circuit breaker state consistency"""
        cb_status = variables.get('CIRCUIT_BREAKER_STATUS', 'closed')
        recovery_failure_count = int(variables.get('RECOVERY_FAILURE_COUNT', '0'))
        deployment_failure_count = int(variables.get('DEPLOYMENT_FAILURE_COUNT', '0'))
        recovery_threshold = int(variables.get('CIRCUIT_BREAKER_THRESHOLD', '3'))
        deployment_threshold = int(variables.get('DEPLOYMENT_CIRCUIT_BREAKER_THRESHOLD', '5'))
        
        issues = []
        
        # Check if circuit breaker should be open based on failure counts
        should_be_open = (recovery_failure_count >= recovery_threshold or 
                         deployment_failure_count >= deployment_threshold)
        
        if should_be_open and cb_status != 'open':
            issues.append(f'Circuit breaker should be open (recovery: {recovery_failure_count}/{recovery_threshold}, deployment: {deployment_failure_count}/{deployment_threshold})')
        
        if cb_status == 'open' and not should_be_open:
            issues.append('Circuit breaker is open but failure counts are below thresholds')
        
        return {
            'status': 'consistent' if not issues else 'inconsistent',
            'issues': issues,
            'circuit_breaker_status': cb_status,
            'recovery_failures': f'{recovery_failure_count}/{recovery_threshold}',
            'deployment_failures': f'{deployment_failure_count}/{deployment_threshold}'
        }
    
    def _check_artifact_consistency(self, variables: Dict[str, str]) -> Dict:
        """Check artifact state consistency"""
        deployed_digest = variables.get('DEPLOYED_ARTIFACT_DIGEST', '')
        backup_digest = variables.get('BACKUP_ARTIFACT_DIGEST', '')
        
        issues = []
        
        if deployed_digest and backup_digest and deployed_digest == backup_digest:
            issues.append('Deployed and backup artifacts are the same')
        
        return {
            'status': 'consistent' if not issues else 'inconsistent',
            'issues': issues,
            'deployed_digest': deployed_digest[:12] + '...' if deployed_digest else 'none',
            'backup_digest': backup_digest[:12] + '...' if backup_digest else 'none'
        }
    
    def _check_recovery_consistency(self, variables: Dict[str, str]) -> Dict:
        """Check recovery state consistency"""
        recovery_session = variables.get('RECOVERY_SESSION_ID', '')
        recovery_in_progress = bool(recovery_session)
        last_health_status = variables.get('LAST_HEALTH_CHECK_STATUS', '')
        
        issues = []
        
        if recovery_in_progress:
            recovery_start = variables.get('RECOVERY_START_TIME', '')
            if recovery_start:
                try:
                    start_time = datetime.fromisoformat(recovery_start.replace('Z', '+00:00'))
                    if (datetime.now(timezone.utc) - start_time).total_seconds() > 900:  # 15 minutes
                        issues.append('Recovery session has been active for over 15 minutes')
                except:
                    issues.append('Invalid recovery start timestamp')
        
        return {
            'status': 'consistent' if not issues else 'inconsistent',
            'issues': issues,
            'recovery_in_progress': recovery_in_progress,
            'last_health_status': last_health_status
        }
    
    def generate_orchestration_report(self) -> Dict:
        """Generate comprehensive orchestration report"""
        report = {
            'session_id': self.session_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'workflow_states': {},
            'dependency_validation': {},
            'sequencing_issues': {},
            'system_consistency': {},
            'recommendations': []
        }
        
        # Get workflow states
        for workflow in self.dependency_graph.keys():
            report['workflow_states'][workflow] = self.get_workflow_state(workflow)
        
        # Validate dependencies
        for workflow in self.dependency_graph.keys():
            valid, issues = self.validate_dependencies(workflow)
            report['dependency_validation'][workflow] = {
                'valid': valid,
                'issues': issues
            }
        
        # Check sequencing
        report['sequencing_issues'] = self.check_workflow_sequencing()
        
        # Check system consistency
        report['system_consistency'] = self.get_system_state_consistency()
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)
        
        return report
    
    def _generate_recommendations(self, report: Dict) -> List[str]:
        """Generate actionable recommendations based on report"""
        recommendations = []
        
        # Check for unhealthy workflows
        for workflow, state in report['workflow_states'].items():
            if state['health'] == 'unhealthy':
                if workflow in self.critical_workflows:
                    recommendations.append(f'CRITICAL: {workflow} workflow is unhealthy - investigate immediately')
                else:
                    recommendations.append(f'WARNING: {workflow} workflow is unhealthy - review recent failures')
        
        # Check for dependency issues
        for workflow, validation in report['dependency_validation'].items():
            if not validation['valid']:
                recommendations.append(f'Dependency issues in {workflow}: {", ".join(validation["issues"])}')
        
        # Check for sequencing issues
        if report['sequencing_issues']:
            recommendations.append('Workflow sequencing issues detected - review concurrent executions')
        
        # Check system consistency
        consistency = report['system_consistency']
        if not isinstance(consistency, dict) or 'error' in consistency:
            recommendations.append('System state consistency check failed - manual verification needed')
        else:
            for check_name, check_result in consistency.items():
                if isinstance(check_result, dict) and check_result.get('status') == 'inconsistent':
                    recommendations.append(f'System state inconsistency in {check_name}: {", ".join(check_result.get("issues", []))}')
        
        # Check for stuck processes
        deployment_state = consistency.get('deployment_state', {})
        if deployment_state.get('deployment_in_progress'):
            recommendations.append('Deployment appears to be stuck - consider manual intervention')
        
        recovery_state = consistency.get('recovery_state', {})
        if recovery_state.get('recovery_in_progress'):
            recommendations.append('Recovery session appears to be stuck - consider manual intervention')
        
        if not recommendations:
            recommendations.append('All workflows and system state appear healthy')
        
        return recommendations


if __name__ == "__main__":
    import os
    repo = os.getenv('GITHUB_REPOSITORY')
    session_id = os.getenv('ORCHESTRATION_SESSION_ID')
    
    orchestrator = WorkflowOrchestrator(repo, session_id)
    report = orchestrator.generate_orchestration_report()
    
    print(json.dumps(report, indent=2))
