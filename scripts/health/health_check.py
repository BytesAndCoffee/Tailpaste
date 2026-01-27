#!/usr/bin/env python3
"""
Enhanced health monitoring script for Tailpaste CI/CD system
Checks service health, database integrity, Tailscale connectivity, and container status
Supports continuous monitoring integration with GitHub Actions workflows
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.error import URLError
from urllib.request import Request, urlopen


class HealthChecker:
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.results: Dict[str, bool] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.metrics: Dict[str, Any] = {}
        self.session_id = (
            f"health-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        )

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from file or use defaults"""
        default_config = {
            # Default to the tailpaste service hostname used in CI runners
            "service_url": os.getenv("TAILPASTE_URL", "http://tailpaste:8080"),
            "storage_path": os.getenv("STORAGE_PATH", "./storage"),
            "max_db_size_mb": 500,
            "response_timeout": 10,
            "critical_error_threshold": 10,
            "tailscale_check": True,
            "container_name": "tailpaste",
            "max_response_time_ms": 2000,
            "max_paste_create_time_ms": 5000,
        }

        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def check_service_availability(self) -> bool:
        """Check if the service responds to HTTP requests with detailed metrics"""
        print("🔍 Checking service availability...")

        response_times = []
        http_codes = []
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            try:
                req = Request(self.config["service_url"])
                req.add_header(
                    "User-Agent", f"HealthChecker/2.0 (session:{self.session_id})"
                )

                start_time = time.time()
                with urlopen(req, timeout=self.config["response_timeout"]) as response:
                    response_time = time.time() - start_time
                    response_time_ms = int(response_time * 1000)
                    status_code = response.getcode()

                    response_times.append(response_time_ms)
                    http_codes.append(status_code)

                    if status_code == 200:
                        avg_response_time = sum(response_times) // len(response_times)
                        print(
                            f"  ✅ Service is available (attempt {attempt}/{max_attempts}, response time: {response_time_ms}ms)"
                        )

                        # Store metrics
                        self.metrics.update(
                            {
                                "avg_response_time_ms": avg_response_time,
                                "response_times_ms": response_times,
                                "http_codes": http_codes,
                                "attempts_needed": attempt,
                            }
                        )

                        if avg_response_time > self.config["max_response_time_ms"]:
                            self.warnings.append(
                                f"Slow response time: {avg_response_time}ms"
                            )

                        return True
                    else:
                        self.errors.append(
                            f"Unexpected status code on attempt {attempt}: {status_code}"
                        )
                        if attempt < max_attempts:
                            time.sleep(1)  # Brief delay before retry

            except URLError as e:
                response_times.append(0)
                http_codes.append(0)
                if attempt == max_attempts:
                    self.errors.append(
                        f"Service unavailable after {max_attempts} attempts: {e}"
                    )
                    print(f"  ❌ Service is not available: {e}")
                else:
                    print(f"  ⏳ Attempt {attempt}/{max_attempts} failed, retrying...")
                    time.sleep(1)
            except Exception as e:
                response_times.append(0)
                http_codes.append(0)
                if attempt == max_attempts:
                    self.errors.append(
                        f"Health check error after {max_attempts} attempts: {e}"
                    )
                    print(f"  ❌ Error during health check: {e}")
                else:
                    time.sleep(1)

        # Store failure metrics
        self.metrics.update(
            {
                "response_times_ms": response_times,
                "http_codes": http_codes,
                "attempts_needed": max_attempts,
                "all_attempts_failed": True,
            }
        )

        return False

    def check_basic_functionality(self) -> bool:
        """Test basic paste creation and retrieval functionality"""
        print("📝 Checking basic functionality...")

        if not self.results.get("service", False):
            print("  ⚠️  Skipping functionality check - service not available")
            return True  # Don't fail if service is already down

        try:
            # Test paste creation
            test_content = f"Health check test - {datetime.now(timezone.utc).isoformat()} - {os.urandom(4).hex()}"

            create_req = Request(
                self.config["service_url"],
                data=test_content.encode("utf-8"),
                headers={
                    "Content-Type": "text/plain",
                    "User-Agent": f"HealthChecker/2.0 (session:{self.session_id})",
                },
            )
            create_req.get_method = lambda: "POST"

            start_time = time.time()
            with urlopen(
                create_req, timeout=self.config["response_timeout"]
            ) as response:
                create_time_ms = int((time.time() - start_time) * 1000)
                paste_response = response.read().decode("utf-8").strip()

                if paste_response:
                    print(f"  ✅ Paste creation successful ({create_time_ms}ms)")

                    # Store metrics
                    self.metrics["paste_create_time_ms"] = create_time_ms

                    if create_time_ms > self.config["max_paste_create_time_ms"]:
                        self.warnings.append(f"Slow paste creation: {create_time_ms}ms")

                    # Test paste retrieval
                    paste_id = (
                        paste_response.split("/")[-1]
                        if "/" in paste_response
                        else paste_response
                    )

                    if paste_id and paste_id != paste_response:
                        retrieve_url = f"{self.config['service_url']}/{paste_id}"
                        retrieve_req = Request(retrieve_url)
                        retrieve_req.add_header(
                            "User-Agent",
                            f"HealthChecker/2.0 (session:{self.session_id})",
                        )

                        start_time = time.time()
                        with urlopen(
                            retrieve_req, timeout=self.config["response_timeout"]
                        ) as response:
                            retrieve_time_ms = int((time.time() - start_time) * 1000)
                            retrieved_content = response.read().decode("utf-8")

                            self.metrics["paste_retrieve_time_ms"] = retrieve_time_ms

                            if retrieved_content == test_content:
                                print(
                                    f"  ✅ Paste retrieval successful ({retrieve_time_ms}ms)"
                                )
                                return True
                            else:
                                self.errors.append("Paste retrieval content mismatch")
                                print("  ❌ Paste retrieval failed - content mismatch")
                                return False
                    else:
                        print("  ⚠️  Could not extract paste ID for retrieval test")
                        return True  # Creation worked, that's the main functionality
                else:
                    self.errors.append("Paste creation returned empty response")
                    print("  ❌ Paste creation failed - empty response")
                    return False

        except URLError as e:
            self.errors.append(f"Functionality test failed: {e}")
            print(f"  ❌ Functionality test failed: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Unexpected functionality test error: {e}")
            print(f"  ❌ Unexpected error during functionality test: {e}")
            return False

    def check_container_health(self) -> bool:
        """Check Docker container health and status"""
        print("🐳 Checking container health...")

        container_name = self.config["container_name"]

        try:
            # Check if container is running
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--format",
                    "{{.Names}}",
                    "--filter",
                    f"name={container_name}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                self.warnings.append("Could not check container status")
                print("  ⚠️  Could not check container status")
                return True

            running_containers = result.stdout.strip().split("\n")
            if container_name not in running_containers:
                self.errors.append(f"Container '{container_name}' is not running")
                print(f"  ❌ Container '{container_name}' is not running")
                return False

            print(f"  ✅ Container '{container_name}' is running")

            # Get container details
            inspect_result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    container_name,
                    "--format",
                    "{{.State.Status}},{{.State.Health.Status}},{{.RestartCount}}",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if inspect_result.returncode == 0:
                status_parts = inspect_result.stdout.strip().split(",")
                container_status = (
                    status_parts[0] if len(status_parts) > 0 else "unknown"
                )
                health_status = status_parts[1] if len(status_parts) > 1 else "none"
                restart_count = (
                    int(status_parts[2])
                    if len(status_parts) > 2 and status_parts[2].isdigit()
                    else 0
                )

                print(
                    f"  📊 Status: {container_status}, Health: {health_status}, Restarts: {restart_count}"
                )

                # Store metrics
                self.metrics.update(
                    {
                        "container_status": container_status,
                        "container_health": health_status,
                        "restart_count": restart_count,
                    }
                )

                if restart_count > 0:
                    self.warnings.append(
                        f"Container has restarted {restart_count} times"
                    )

                if container_status != "running":
                    self.errors.append(
                        f"Container status is '{container_status}', expected 'running'"
                    )
                    return False

            # Get resource usage
            stats_result = subprocess.run(
                [
                    "docker",
                    "stats",
                    container_name,
                    "--no-stream",
                    "--format",
                    "{{.CPUPerc}},{{.MemUsage}}",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if stats_result.returncode == 0:
                stats_parts = stats_result.stdout.strip().split(",")
                cpu_usage = stats_parts[0] if len(stats_parts) > 0 else "N/A"
                mem_usage = stats_parts[1] if len(stats_parts) > 1 else "N/A"

                print(f"  📈 CPU: {cpu_usage}, Memory: {mem_usage}")

                # Store metrics
                self.metrics.update({"cpu_usage": cpu_usage, "memory_usage": mem_usage})

            return True

        except FileNotFoundError:
            self.warnings.append("Docker CLI not found")
            print("  ⚠️  Docker CLI not found")
            return True
        except subprocess.TimeoutExpired:
            self.warnings.append("Container health check timed out")
            print("  ⚠️  Container health check timed out")
            return True
        except Exception as e:
            self.warnings.append(f"Container health check error: {e}")
            print(f"  ⚠️  Error checking container health: {e}")
            return True

    def check_database(self) -> bool:
        """Check database integrity and size"""
        print("🗄️  Checking database health...")

        db_path = Path(self.config["storage_path"]) / "pastes.db"

        if not db_path.exists():
            self.warnings.append("Database file does not exist yet")
            print("  ⚠️  Database file does not exist (new installation?)")
            return True

        try:
            # Check file size
            db_size_mb = db_path.stat().st_size / (1024 * 1024)
            print(f"  📊 Database size: {db_size_mb:.2f} MB")

            if db_size_mb > self.config["max_db_size_mb"]:
                self.warnings.append(
                    f"Database size ({db_size_mb:.2f} MB) exceeds threshold "
                    f"({self.config['max_db_size_mb']} MB)"
                )

            # Check database integrity
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]

            if result != "ok":
                self.errors.append(f"Database integrity check failed: {result}")
                print(f"  ❌ Database integrity check failed: {result}")
                return False

            # Get paste count
            cursor.execute("SELECT COUNT(*) FROM pastes")
            paste_count = cursor.fetchone()[0]
            print(f"  📝 Total pastes: {paste_count}")

            # Get recent pastes count
            cursor.execute(
                "SELECT COUNT(*) FROM pastes WHERE created_at > datetime('now', '-24 hours')"
            )
            recent_count = cursor.fetchone()[0]
            print(f"  📅 Pastes in last 24h: {recent_count}")

            conn.close()
            print("  ✅ Database is healthy")
            return True

        except sqlite3.Error as e:
            self.errors.append(f"Database error: {e}")
            print(f"  ❌ Database error: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Unexpected database error: {e}")
            print(f"  ❌ Unexpected error: {e}")
            return False

    def check_tailscale(self) -> bool:
        """Check Tailscale connectivity"""
        if not self.config["tailscale_check"]:
            return True

        print("🔐 Checking Tailscale connectivity...")

        try:
            # Check if tailscale is running
            result = subprocess.run(
                ["tailscale", "status"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                print("  ✅ Tailscale is connected")

                # Get IP address
                ip_result = subprocess.run(
                    ["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=5
                )
                if ip_result.returncode == 0:
                    ip = ip_result.stdout.strip()
                    print(f"  🌐 Tailscale IP: {ip}")

                return True
            else:
                self.errors.append("Tailscale is not connected")
                print(f"  ❌ Tailscale is not connected: {result.stderr}")
                return False

        except FileNotFoundError:
            self.warnings.append("Tailscale CLI not found (might be in Docker)")
            print("  ⚠️  Tailscale CLI not found")
            return True
        except subprocess.TimeoutExpired:
            self.errors.append("Tailscale check timed out")
            print("  ❌ Tailscale check timed out")
            return False
        except Exception as e:
            self.errors.append(f"Tailscale check error: {e}")
            print(f"  ❌ Error checking Tailscale: {e}")
            return False

    def check_docker_logs(self) -> bool:
        """Check Docker logs for critical errors"""
        print("📋 Checking Docker logs for errors...")

        try:
            result = subprocess.run(
                ["docker", "logs", "--tail=100", "tailpaste"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                self.warnings.append("Could not retrieve Docker logs")
                print("  ⚠️  Could not retrieve Docker logs")
                return True

            # Count error lines (excluding false positives)
            error_count = 0
            for line in result.stderr.split("\n"):
                if "error" in line.lower() and "error_log" not in line.lower():
                    error_count += 1

            if error_count > self.config["critical_error_threshold"]:
                self.errors.append(
                    f"Found {error_count} errors in recent logs "
                    f"(threshold: {self.config['critical_error_threshold']})"
                )
                print(f"  ❌ Too many errors in logs: {error_count}")
                return False
            elif error_count > 0:
                self.warnings.append(f"Found {error_count} errors in recent logs")
                print(f"  ⚠️  Found {error_count} errors in recent logs")
            else:
                print("  ✅ No critical errors in logs")

            return True

        except FileNotFoundError:
            self.warnings.append("Docker CLI not found")
            print("  ⚠️  Docker CLI not found")
            return True
        except subprocess.TimeoutExpired:
            self.warnings.append("Docker logs check timed out")
            print("  ⚠️  Docker logs check timed out")
            return True
        except Exception as e:
            self.warnings.append(f"Docker logs check error: {e}")
            print(f"  ⚠️  Error checking Docker logs: {e}")
            return True

    def run_all_checks(self) -> bool:
        """Run all health checks"""
        print("\n" + "=" * 60)
        print("🏥 Enhanced Tailpaste Health Check")
        print(f"⏰ {datetime.now(timezone.utc).isoformat()}")
        print(f"🆔 Session: {self.session_id}")
        print("=" * 60 + "\n")

        checks = [
            ("service", self.check_service_availability),
            ("functionality", self.check_basic_functionality),
            ("database", self.check_database),
            ("container", self.check_container_health),
            ("tailscale", self.check_tailscale),
            ("logs", self.check_docker_logs),
        ]

        for check_name, check_func in checks:
            try:
                self.results[check_name] = check_func()
            except Exception as e:
                self.errors.append(f"Unexpected error in {check_name} check: {e}")
                self.results[check_name] = False
            print()

        return self._print_summary()

    def _print_summary(self) -> bool:
        """Print health check summary"""
        print("=" * 60)
        print("📊 Health Check Summary")
        print("=" * 60)

        # Print active configuration
        print("\n🛠️ Active Configuration:")
        for key, value in self.config.items():
            print(f"  {key}: {value}")

        print()
        all_passed = all(self.results.values())

        for check_name, passed in self.results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {check_name.capitalize()}: {status}")

        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")

        if self.errors:
            print("\n❌ Errors:")
            for error in self.errors:
                print(f"  - {error}")

        print("\n" + "=" * 60)

        if all_passed:
            print("✅ All checks passed!")
        else:
            print("❌ Some checks failed!")

        print("=" * 60 + "\n")

        return all_passed

    def export_results(self, output_path: str):
        """Export results to JSON file"""
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "checks": {
                name: {"status": "passed" if passed else "failed"}
                for name, passed in self.results.items()
            },
            "errors": self.errors,
            "warnings": self.warnings,
            "metrics": self.metrics,
            "overall_status": "healthy" if all(self.results.values()) else "unhealthy",
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"📄 Results exported to: {output_path}")

    def get_overall_status(self) -> str:
        """Get overall health status as string"""
        if not self.results:
            return "unknown"

        failed_checks = [name for name, passed in self.results.items() if not passed]

        if not failed_checks:
            return "healthy"

        # Check if only non-critical checks failed
        critical_checks = {"service", "functionality", "container"}
        critical_failures = [
            check for check in failed_checks if check in critical_checks
        ]

        if critical_failures:
            return "unhealthy"
        else:
            return "degraded"

    def get_health_summary(self) -> dict:
        """Get a summary of health check results for monitoring integration"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "overall_status": self.get_overall_status(),
            "checks": {
                name: {"status": "passed" if passed else "failed"}
                for name, passed in self.results.items()
            },
            "metrics": self.metrics,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "details": {"errors": self.errors, "warnings": self.warnings},
        }


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced health monitoring for Tailpaste CI/CD system"
    )
    parser.add_argument("--config", help="Path to configuration file", default=None)
    parser.add_argument("--export", help="Export results to JSON file", default=None)
    parser.add_argument("--silent", action="store_true", help="Only output summary")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--summary", action="store_true", help="Output health summary for monitoring"
    )

    args = parser.parse_args()

    checker = HealthChecker(config_path=args.config)

    if args.silent:
        # Redirect stdout to devnull for silent mode
        sys.stdout = open(os.devnull, "w")

    success = checker.run_all_checks()

    if args.silent:
        sys.stdout = sys.__stdout__

    if args.json:
        print(json.dumps(checker.get_health_summary(), indent=2))
    elif args.summary:
        summary = checker.get_health_summary()
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Errors: {summary['error_count']}")
        print(f"Warnings: {summary['warning_count']}")

    if args.export:
        checker.export_results(args.export)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
