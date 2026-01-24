"""Unit tests for health_check.py script.

Tests the HealthChecker class, specifically focusing on the _print_summary method
to ensure correct inclusion and formatting of configuration settings.
"""

import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "health"))

from health_check import HealthChecker  # noqa: E402


class TestHealthChecker:
    """Test suite for HealthChecker class."""

    def test_print_summary_includes_configuration(self, capsys):
        """Test that _print_summary includes configuration settings in output."""
        # Create a checker with known configuration
        checker = HealthChecker()
        checker.config = {
            "service_url": "http://localhost:8080",
            "storage_path": "./storage",
            "max_db_size_mb": 500,
        }
        checker.results = {"test_check": True}

        # Call _print_summary
        result = checker._print_summary()

        # Capture output
        captured = capsys.readouterr()

        # Verify configuration section is present
        assert "🛠️ Active Configuration:" in captured.out
        assert "service_url: http://localhost:8080" in captured.out
        assert "storage_path: ./storage" in captured.out
        assert "max_db_size_mb: 500" in captured.out

        # Verify it's before the summary results
        config_index = captured.out.index("🛠️ Active Configuration:")
        summary_index = captured.out.index("Test_check: ✅ PASS")
        assert config_index < summary_index

        # Verify function returns True for passing checks
        assert result is True

    def test_print_summary_configuration_formatting(self, capsys):
        """Test that configuration key-value pairs are properly formatted."""
        checker = HealthChecker()
        checker.config = {
            "key1": "value1",
            "key2": 123,
            "key3": True,
        }
        checker.results = {}

        checker._print_summary()
        captured = capsys.readouterr()

        # Verify each key-value pair is on its own line with proper format
        assert "key1: value1" in captured.out
        assert "key2: 123" in captured.out
        assert "key3: True" in captured.out

    def test_print_summary_with_failing_checks(self, capsys):
        """Test _print_summary with failing checks includes configuration."""
        checker = HealthChecker()
        checker.config = {"test_config": "test_value"}
        checker.results = {"check1": True, "check2": False}
        checker.errors = ["Test error message"]

        result = checker._print_summary()

        captured = capsys.readouterr()

        # Verify configuration is still displayed
        assert "🛠️ Active Configuration:" in captured.out
        assert "test_config: test_value" in captured.out

        # Verify errors are displayed
        assert "❌ Errors:" in captured.out
        assert "Test error message" in captured.out

        # Verify function returns False for failing checks
        assert result is False

    def test_print_summary_with_warnings(self, capsys):
        """Test _print_summary with warnings includes configuration."""
        checker = HealthChecker()
        checker.config = {"test_config": "test_value"}
        checker.results = {"check1": True}
        checker.warnings = ["Warning message 1", "Warning message 2"]

        result = checker._print_summary()

        captured = capsys.readouterr()

        # Verify configuration is displayed
        assert "🛠️ Active Configuration:" in captured.out

        # Verify warnings are displayed
        assert "⚠️  Warnings:" in captured.out
        assert "Warning message 1" in captured.out
        assert "Warning message 2" in captured.out

        assert result is True

    def test_print_summary_empty_configuration(self, capsys):
        """Test _print_summary handles empty configuration gracefully."""
        checker = HealthChecker()
        checker.config = {}
        checker.results = {"check1": True}

        result = checker._print_summary()

        captured = capsys.readouterr()

        # Verify configuration section header is still present
        assert "🛠️ Active Configuration:" in captured.out
        # But no key-value pairs
        assert result is True

    def test_print_summary_configuration_order_before_results(self, capsys):
        """Test that configuration appears before check results in output."""
        checker = HealthChecker()
        checker.config = {"config_key": "config_value"}
        checker.results = {"service": True, "database": True}

        checker._print_summary()
        captured = capsys.readouterr()

        # Find positions of key elements
        header_pos = captured.out.index("📊 Health Check Summary")
        config_pos = captured.out.index("🛠️ Active Configuration:")
        service_pos = captured.out.index("Service:")

        # Verify order: header -> config -> results
        assert header_pos < config_pos < service_pos

    def test_print_summary_multiple_config_values(self, capsys):
        """Test _print_summary with multiple configuration values."""
        checker = HealthChecker()
        checker.config = {
            "service_url": "http://localhost:8080",
            "storage_path": "./storage",
            "max_db_size_mb": 500,
            "response_timeout": 10,
            "critical_error_threshold": 10,
            "tailscale_check": True,
        }
        checker.results = {"check": True}

        checker._print_summary()
        captured = capsys.readouterr()

        # Verify all configuration items are present
        for key, value in checker.config.items():
            assert f"{key}: {value}" in captured.out

    def test_print_summary_preserves_existing_functionality(self, capsys):
        """Test that adding configuration doesn't break existing summary functionality."""
        checker = HealthChecker()
        checker.config = {"test": "value"}
        checker.results = {
            "service": True,
            "database": False,
            "tailscale": True,
        }
        checker.errors = ["Database connection failed"]
        checker.warnings = ["Slow response time"]

        result = checker._print_summary()

        captured = capsys.readouterr()

        # Verify all existing elements are still present
        assert "📊 Health Check Summary" in captured.out
        assert "Service: ✅ PASS" in captured.out
        assert "Database: ❌ FAIL" in captured.out
        assert "Tailscale: ✅ PASS" in captured.out
        assert "❌ Errors:" in captured.out
        assert "Database connection failed" in captured.out
        assert "⚠️  Warnings:" in captured.out
        assert "Slow response time" in captured.out
        assert "❌ Some checks failed!" in captured.out

        assert result is False

    def test_init_loads_default_config(self):
        """Test that HealthChecker initializes with default configuration."""
        checker = HealthChecker()

        # Verify default configuration is loaded
        assert "service_url" in checker.config
        assert "storage_path" in checker.config
        assert "max_db_size_mb" in checker.config
        assert "response_timeout" in checker.config
        assert "critical_error_threshold" in checker.config
        assert "tailscale_check" in checker.config

        # Verify default values
        assert checker.config["max_db_size_mb"] == 500
        assert checker.config["response_timeout"] == 10
        assert checker.config["critical_error_threshold"] == 10
        assert checker.config["tailscale_check"] is True
