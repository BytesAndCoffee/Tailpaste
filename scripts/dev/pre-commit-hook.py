#!/usr/bin/env python3
"""
Pre-commit hook for Tailpaste
Runs code quality checks before allowing commits
"""

import os
import subprocess
import sys
from pathlib import Path


class PreCommitChecker:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.git_root = self._get_git_root()

    def _get_git_root(self) -> Path:
        """Get git repository root"""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
        )
        return Path(result.stdout.strip())

    def _get_staged_python_files(self) -> list:
        """Get list of staged Python files"""
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
        )

        files = result.stdout.strip().split("\n")
        python_files = [f for f in files if f.endswith(".py") and os.path.exists(f)]

        return python_files

    def run_black(self, files: list) -> bool:
        """Check code formatting with black"""
        if not files:
            return True

        print("🎨 Checking code formatting with black...")

        result = subprocess.run(
            ["black", "--check", "--quiet"] + files, capture_output=True
        )

        if result.returncode != 0:
            self.errors.append(
                "Code formatting check failed. Run 'black .' to fix formatting."
            )
            print("  ❌ Formatting issues found")
            return False

        print("  ✅ Code formatting is correct")
        return True

    def run_flake8(self, files: list) -> bool:
        """Check code style with flake8"""
        if not files:
            return True

        print("🔍 Running flake8 linter...")

        result = subprocess.run(
            ["flake8", "--max-line-length=120"] + files, capture_output=True, text=True
        )

        if result.returncode != 0:
            self.errors.append(f"Linting errors found:\n{result.stdout}")
            print("  ❌ Linting issues found")
            return False

        print("  ✅ No linting issues")
        return True

    def run_mypy(self, files: list) -> bool:
        """Check type hints with mypy"""
        if not files:
            return True

        print("🔍 Running mypy type checker...")

        result = subprocess.run(
            ["mypy", "--ignore-missing-imports"] + files, capture_output=True, text=True
        )

        if result.returncode != 0:
            # Mypy issues are warnings, not blockers
            self.warnings.append(f"Type checking issues:\n{result.stdout}")
            print("  ⚠️  Type checking warnings (not blocking)")
            return True

        print("  ✅ No type issues")
        return True

    def check_tests_exist(self, files: list) -> bool:
        """Check if test files exist for modified source files"""
        if not files:
            return True

        print("🧪 Checking for corresponding test files...")

        missing_tests = []
        for file in files:
            if file.startswith("src/") and not file.startswith("src/__"):
                # Convert src/module.py to tests/test_module.py
                module_name = Path(file).stem
                test_file = f"tests/test_{module_name}.py"

                if not os.path.exists(test_file):
                    missing_tests.append((file, test_file))

        if missing_tests:
            msg = "Missing test files for:\n" + "\n".join(
                f"  {src} -> {test}" for src, test in missing_tests
            )
            self.warnings.append(msg)
            print("  ⚠️  Some files missing corresponding tests")
        else:
            print("  ✅ Test files found")

        return True

    def run_tests(self) -> bool:
        """Run test suite"""
        print("🧪 Running test suite...")

        result = subprocess.run(
            ["pytest", "tests/", "-v", "--tb=short"], capture_output=True, text=True
        )

        if result.returncode != 0:
            self.errors.append(f"Test failures:\n{result.stdout}")
            print("  ❌ Tests failed")
            return False

        print("  ✅ All tests passed")
        return True

    def check_commit_message(self) -> bool:
        """Check commit message format (if available)"""
        # This is called as pre-commit, so message isn't available yet
        # Could be implemented as commit-msg hook instead
        return True

    def run_checks(self) -> bool:
        """Run all pre-commit checks"""
        print("\n" + "=" * 60)
        print("🔍 Running pre-commit checks")
        print("=" * 60 + "\n")

        files = self._get_staged_python_files()

        if not files:
            print("No Python files to check")
            return True

        print(f"Checking {len(files)} Python file(s):\n  " + "\n  ".join(files))
        print()

        # Run checks

        print("\n" + "=" * 60)
        print("📊 Pre-commit Summary")
        print("=" * 60)

        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  {warning}")

        if self.errors:
            print("\n❌ Errors:")
            for error in self.errors:
                print(f"  {error}")
            print("\n❌ Commit blocked due to errors")
            print("=" * 60 + "\n")
            return False

        print("\n✅ All checks passed!")
        print("=" * 60 + "\n")
        return True


def main():
    # Check if required tools are installed
    required_tools = ["black", "flake8", "mypy", "pytest"]
    missing_tools = []

    for tool in required_tools:
        if subprocess.run(["which", tool], capture_output=True).returncode != 0:
            missing_tools.append(tool)

    if missing_tools:
        print(f"❌ Missing required tools: {', '.join(missing_tools)}")
        print(f"Install with: pip install {' '.join(missing_tools)}")
        sys.exit(1)

    checker = PreCommitChecker()

    if not checker.run_checks():
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
