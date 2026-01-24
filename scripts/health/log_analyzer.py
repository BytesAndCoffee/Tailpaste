#!/usr/bin/env python3
"""
Log analyzer for Tailpaste
Analyzes Docker logs for errors, patterns, and performance metrics
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class LogAnalyzer:
    def __init__(self, container_name: str = "tailpaste", lines: int = 1000):
        self.container_name = container_name
        self.lines = lines
        self.logs: List[str] = []
        self.errors: List[Tuple[str, str]] = []
        self.warnings: List[Tuple[str, str]] = []
        self.metrics: Dict = {}

    def fetch_logs(self) -> bool:
        """Fetch logs from Docker container"""
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(self.lines), self.container_name],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                print(f"❌ Failed to fetch logs: {result.stderr}")
                return False

            # Combine stdout and stderr
            self.logs = (result.stdout + result.stderr).split("\n")
            print(f"✅ Fetched {len(self.logs)} log lines")
            return True

        except subprocess.TimeoutExpired:
            print("❌ Log fetch timed out")
            return False
        except FileNotFoundError:
            print("❌ Docker CLI not found")
            return False
        except Exception as e:
            print(f"❌ Error fetching logs: {e}")
            return False

    def analyze_errors(self):
        """Analyze and categorize errors"""
        error_patterns = {
            "database": r"(database|sqlite|sql)",
            "network": r"(connection|timeout|network|socket)",
            "tailscale": r"(tailscale|tailnet)",
            "authentication": r"(auth|authentication|unauthorized)",
            "python": r"(exception|traceback|error:)",
            "disk": r"(disk|storage|space|no such file)",
        }

        for line in self.logs:
            if not line.strip():
                continue

            lower_line = line.lower()

            # Skip false positives
            if "error_log" in lower_line or "no error" in lower_line:
                continue

            # Check for errors
            if (
                "error" in lower_line
                or "exception" in lower_line
                or "fail" in lower_line
            ):
                category = "general"
                for cat, pattern in error_patterns.items():
                    if re.search(pattern, lower_line, re.IGNORECASE):
                        category = cat
                        break

                self.errors.append((category, line.strip()))

            # Check for warnings
            elif "warn" in lower_line:
                self.warnings.append(("warning", line.strip()))

    def analyze_patterns(self):
        """Analyze log patterns and metrics"""
        # Request patterns
        request_pattern = re.compile(r"(GET|POST|PUT|DELETE|HEAD)\s+(\S+)")
        status_pattern = re.compile(r"\s(\d{3})\s")
        ip_pattern = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")

        requests = []
        status_codes = []
        ips = []

        for line in self.logs:
            # Find HTTP requests
            req_match = request_pattern.search(line)
            if req_match:
                requests.append((req_match.group(1), req_match.group(2)))

            # Find status codes
            status_match = status_pattern.search(line)
            if status_match:
                status_codes.append(status_match.group(1))

            # Find IPs
            ip_match = ip_pattern.search(line)
            if ip_match:
                ips.append(ip_match.group(0))

        # Count occurrences
        self.metrics = {
            "total_requests": len(requests),
            "request_methods": dict(Counter([r[0] for r in requests])),
            "request_paths": dict(Counter([r[1] for r in requests]).most_common(10)),
            "status_codes": dict(Counter(status_codes)),
            "unique_ips": len(set(ips)),
            "top_ips": dict(Counter(ips).most_common(5)),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }

    def print_summary(self):
        """Print analysis summary"""
        print("\n" + "=" * 60)
        print("📊 Log Analysis Summary")
        print("=" * 60 + "\n")

        # Metrics
        print("📈 Metrics:")
        print(f"  Total requests: {self.metrics.get('total_requests', 0)}")
        print(f"  Errors found: {self.metrics.get('error_count', 0)}")
        print(f"  Warnings found: {self.metrics.get('warning_count', 0)}")
        print(f"  Unique IPs: {self.metrics.get('unique_ips', 0)}")

        # Request methods
        if self.metrics.get("request_methods"):
            print("\n🔧 Request Methods:")
            for method, count in self.metrics["request_methods"].items():
                print(f"  {method}: {count}")

        # Status codes
        if self.metrics.get("status_codes"):
            print("\n📡 Status Codes:")
            for code, count in sorted(self.metrics["status_codes"].items()):
                print(f"  {code}: {count}")

        # Top paths
        if self.metrics.get("request_paths"):
            print("\n🌐 Top Request Paths:")
            for path, count in list(self.metrics["request_paths"].items())[:5]:
                print(f"  {path}: {count}")

        # Top IPs
        if self.metrics.get("top_ips"):
            print("\n🌍 Top IP Addresses:")
            for ip, count in list(self.metrics["top_ips"].items())[:5]:
                print(f"  {ip}: {count}")

        # Error categories
        if self.errors:
            print("\n❌ Error Categories:")
            error_cats = Counter([e[0] for e in self.errors])
            for category, count in error_cats.most_common():
                print(f"  {category}: {count}")

            print("\n  Recent Errors:")
            for category, error in self.errors[-5:]:
                print(f"    [{category}] {error[:80]}...")

        # Warnings
        if self.warnings:
            print("\n⚠️  Recent Warnings:")
            for _, warning in self.warnings[-5:]:
                print(f"  {warning[:80]}...")

        print("\n" + "=" * 60)

    def export_report(self, output_path: str):
        """Export analysis to JSON file"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "container": self.container_name,
            "lines_analyzed": len(self.logs),
            "metrics": self.metrics,
            "errors": [{"category": cat, "message": msg} for cat, msg in self.errors],
            "warnings": [
                {"category": cat, "message": msg} for cat, msg in self.warnings
            ],
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Report exported to: {output_path}")

    def run_analysis(self):
        """Run complete log analysis"""
        print("\n" + "=" * 60)
        print("📋 Tailpaste Log Analyzer")
        print(f"⏰ {datetime.now().isoformat()}")
        print(f"📦 Container: {self.container_name}")
        print(f"📏 Lines to analyze: {self.lines}")
        print("=" * 60 + "\n")

        if not self.fetch_logs():
            return False

        print("🔍 Analyzing logs...")
        self.analyze_errors()
        self.analyze_patterns()

        self.print_summary()
        return True


def main():
    parser = argparse.ArgumentParser(description="Analyze Tailpaste Docker logs")
    parser.add_argument(
        "--container",
        default="tailpaste",
        help="Docker container name (default: tailpaste)",
    )
    parser.add_argument(
        "--lines",
        type=int,
        default=1000,
        help="Number of log lines to analyze (default: 1000)",
    )
    parser.add_argument("--export", help="Export analysis to JSON file", default=None)
    parser.add_argument(
        "--errors-only", action="store_true", help="Only show errors and warnings"
    )

    args = parser.parse_args()

    analyzer = LogAnalyzer(container_name=args.container, lines=args.lines)

    if not analyzer.run_analysis():
        sys.exit(1)

    if args.export:
        analyzer.export_report(args.export)

    if args.errors_only and analyzer.errors:
        print("\n" + "=" * 60)
        print("❌ All Errors:")
        print("=" * 60)
        for category, error in analyzer.errors:
            print(f"[{category}] {error}")

    sys.exit(0)


if __name__ == "__main__":
    main()
