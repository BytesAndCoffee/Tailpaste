#!/usr/bin/env python3
"""
Health monitoring script for Tailpaste
Checks service health, database integrity, and Tailscale connectivity
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen


class HealthChecker:
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.results: Dict[str, bool] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from file or use defaults"""
        default_config = {
            "service_url": os.getenv("TAILPASTE_URL", "http://localhost:8080"),
            "storage_path": os.getenv("STORAGE_PATH", "./storage"),
            "max_db_size_mb": 500,
            "response_timeout": 10,
            "critical_error_threshold": 10,
            "tailscale_check": True,
        }

        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def check_service_availability(self) -> bool:
        """Check if the service responds to HTTP requests"""
        print("🔍 Checking service availability...")

        try:
            req = Request(self.config["service_url"])
            req.add_header("User-Agent", "HealthChecker/1.0")

            start_time = time.time()
            with urlopen(req, timeout=self.config["response_timeout"]) as response:
                response_time = time.time() - start_time
                status_code = response.getcode()

                if status_code == 200:
                    print(
                        f"  ✅ Service is available (response time: {response_time:.2f}s)"
                    )

                    if response_time > 5:
                        self.warnings.append(
                            f"Slow response time: {response_time:.2f}s"
                        )

                    return True
                else:
                    self.errors.append(f"Unexpected status code: {status_code}")
                    return False

        except URLError as e:
            self.errors.append(f"Service unavailable: {e}")
            print(f"  ❌ Service is not available: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Health check error: {e}")
            print(f"  ❌ Error during health check: {e}")
            return False

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
        print("🏥 Tailpaste Health Check")
        print(f"⏰ {datetime.now().isoformat()}")
        print("=" * 60 + "\n")

        checks = [
            ("service", self.check_service_availability),
            ("database", self.check_database),
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
            "timestamp": datetime.now().isoformat(),
            "checks": self.results,
            "errors": self.errors,
            "warnings": self.warnings,
            "overall_status": "healthy" if all(self.results.values()) else "unhealthy",
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"📄 Results exported to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Health monitoring for Tailpaste service"
    )
    parser.add_argument("--config", help="Path to configuration file", default=None)
    parser.add_argument("--export", help="Export results to JSON file", default=None)
    parser.add_argument("--silent", action="store_true", help="Only output summary")

    args = parser.parse_args()

    checker = HealthChecker(config_path=args.config)

    if args.silent:
        # Redirect stdout to devnull for silent mode
        sys.stdout = open(os.devnull, "w")

    success = checker.run_all_checks()

    if args.silent:
        sys.stdout = sys.__stdout__

    if args.export:
        checker.export_results(args.export)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
