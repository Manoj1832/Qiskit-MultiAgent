"""
Test runner for executing and validating tests.
"""

import subprocess
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TestResult:
    """Result of a test execution."""
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_output: str
    duration_seconds: float


class TestRunner:
    """
    Runs tests on a repository and analyzes results.
    """
    
    def __init__(self, repo_path: Path | str, timeout_seconds: int = 600):
        """
        Initialize test runner.
        
        Args:
            repo_path: Path to the repository root
            timeout_seconds: Maximum time to run tests
        """
        self.repo_path = Path(repo_path)
        self.timeout = timeout_seconds
    
    def run_tests(
        self,
        test_path: str | None = None,
        markers: list[str] | None = None,
        verbose: bool = True,
    ) -> TestResult:
        """
        Run pytest on the repository.
        
        Args:
            test_path: Specific test file or directory (optional)
            markers: Pytest markers to filter tests (optional)
            verbose: Enable verbose output
            
        Returns:
            TestResult with test outcomes
        """
        import time
        start_time = time.time()
        
        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        
        if test_path:
            cmd.append(test_path)
        
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        if verbose:
            cmd.append("-v")
        
        # Add JSON output for parsing
        cmd.extend(["--tb=short", "-q"])
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            duration = time.time() - start_time
            
            # Parse pytest output
            return self._parse_pytest_output(result, duration)
            
        except subprocess.TimeoutExpired:
            return TestResult(
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                error_output=f"Tests timed out after {self.timeout} seconds",
                duration_seconds=self.timeout,
            )
        except Exception as e:
            return TestResult(
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                error_output=str(e),
                duration_seconds=time.time() - start_time,
            )
    
    def _parse_pytest_output(
        self,
        result: subprocess.CompletedProcess,
        duration: float,
    ) -> TestResult:
        """Parse pytest output to extract test results."""
        output = result.stdout + result.stderr
        
        # Parse summary line: "X passed, Y failed, Z skipped"
        passed = 0
        failed = 0
        skipped = 0
        
        for line in output.split("\n"):
            line = line.lower()
            if "passed" in line or "failed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed" and i > 0:
                        try:
                            passed = int(parts[i - 1])
                        except ValueError:
                            pass
                    elif part == "failed" and i > 0:
                        try:
                            failed = int(parts[i - 1])
                        except ValueError:
                            pass
                    elif part == "skipped" and i > 0:
                        try:
                            skipped = int(parts[i - 1])
                        except ValueError:
                            pass
        
        total = passed + failed + skipped
        
        return TestResult(
            passed=(failed == 0 and result.returncode == 0),
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_output=output if failed > 0 else "",
            duration_seconds=duration,
        )
    
    def run_specific_tests(self, test_files: list[str]) -> dict[str, TestResult]:
        """
        Run tests on specific test files.
        
        Args:
            test_files: List of test file paths
            
        Returns:
            Dictionary mapping file paths to test results
        """
        results = {}
        for test_file in test_files:
            results[test_file] = self.run_tests(test_path=test_file)
        return results
    
    def calculate_delta(
        self,
        before: TestResult,
        after: TestResult,
    ) -> dict[str, int]:
        """
        Calculate the delta between two test runs.
        
        Args:
            before: Test results before changes
            after: Test results after changes
            
        Returns:
            Dictionary with delta values
        """
        return {
            "passed_delta": after.passed_tests - before.passed_tests,
            "failed_delta": after.failed_tests - before.failed_tests,
            "total_delta": after.total_tests - before.total_tests,
            "regressions": max(0, after.failed_tests - before.failed_tests),
            "fixes": max(0, before.failed_tests - after.failed_tests),
        }
