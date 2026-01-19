"""Tests for the SWE-bench benchmark runner."""

import pytest
import json
import tempfile
from pathlib import Path
from swe_agent_system.benchmarking.swe_bench_runner import (
    SWEBenchRunner,
    BenchmarkRun,
    IssueResult,
)


class TestIssueResult:
    """Tests for IssueResult dataclass."""
    
    def test_issue_result_creation(self):
        """Should create issue result with all fields."""
        result = IssueResult(
            issue_id="123",
            issue_url="https://github.com/test/repo/issues/123",
            status="success",
            execution_time_seconds=120.0,
            tokens_used=15000,
            cost_usd=0.05,
            tests_passed=True,
            regressions=0,
            patch_generated=True,
            patch_files=["file1.py", "file2.py"],
        )
        
        assert result.issue_id == "123"
        assert result.status == "success"
        assert result.tests_passed
        assert len(result.patch_files) == 2


class TestBenchmarkRun:
    """Tests for BenchmarkRun class."""
    
    def test_add_result(self):
        """Should add results to run."""
        run = BenchmarkRun(
            run_id="test_run",
            started_at="2024-01-01T00:00:00",
            repository="test/repo",
        )
        
        result = IssueResult(
            issue_id="1",
            issue_url="url",
            status="success",
            execution_time_seconds=60,
            tokens_used=10000,
            cost_usd=0.02,
            tests_passed=True,
            regressions=0,
            patch_generated=True,
        )
        
        run.add_result(result)
        
        assert run.total_issues == 1
        assert len(run.results) == 1
    
    def test_get_summary(self):
        """Should calculate summary statistics."""
        run = BenchmarkRun(
            run_id="test_run",
            started_at="2024-01-01T00:00:00",
            repository="test/repo",
        )
        
        run.add_result(IssueResult(
            "1", "url", "success", 60, 10000, 0.02, True, 0, True
        ))
        run.add_result(IssueResult(
            "2", "url", "success", 80, 12000, 0.03, True, 0, True
        ))
        run.add_result(IssueResult(
            "3", "url", "failed", 100, 15000, 0.04, False, 1, False
        ))
        
        summary = run.get_summary()
        
        assert summary["total_issues"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] == pytest.approx(2/3)
        assert summary["tests_passed"] == 2
        assert summary["total_tokens"] == 37000
    
    def test_empty_summary(self):
        """Should handle empty results."""
        run = BenchmarkRun(
            run_id="empty",
            started_at="2024-01-01T00:00:00",
        )
        
        summary = run.get_summary()
        assert summary["status"] == "no_results"
    
    def test_to_dict(self):
        """Should convert to dictionary."""
        run = BenchmarkRun(
            run_id="test",
            started_at="2024-01-01T00:00:00",
            repository="repo",
        )
        
        data = run.to_dict()
        
        assert data["run_id"] == "test"
        assert data["repository"] == "repo"
        assert "summary" in data
        assert "results" in data


class TestSWEBenchRunner:
    """Tests for SWEBenchRunner class."""
    
    def test_start_run(self):
        """Should start new benchmark run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = SWEBenchRunner(tmpdir)
            run = runner.start_run("test/repo")
            
            assert run.repository == "test/repo"
            assert runner.current_run is not None
    
    def test_record_result(self):
        """Should record result to current run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = SWEBenchRunner(tmpdir)
            runner.start_run("test/repo")
            
            result = IssueResult(
                "1", "url", "success", 60, 10000, 0.02, True, 0, True
            )
            runner.record_result(result)
            
            assert runner.current_run.total_issues == 1
    
    def test_complete_run(self):
        """Should save run to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = SWEBenchRunner(tmpdir)
            run = runner.start_run("test/repo")
            
            result = IssueResult(
                "1", "url", "success", 60, 10000, 0.02, True, 0, True
            )
            runner.record_result(result)
            
            path = runner.complete_run()
            
            assert path.exists()
            
            # Verify content
            with open(path) as f:
                data = json.load(f)
            assert data["repository"] == "test/repo"
            assert len(data["results"]) == 1
    
    def test_load_run(self):
        """Should load saved run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = SWEBenchRunner(tmpdir)
            run = runner.start_run("test/repo")
            run_id = run.run_id
            
            runner.record_result(IssueResult(
                "1", "url", "success", 60, 10000, 0.02, True, 0, True
            ))
            runner.complete_run()
            
            # Load it back
            loaded = runner.load_run(run_id)
            
            assert loaded.run_id == run_id
            assert loaded.repository == "test/repo"
            assert len(loaded.results) == 1
    
    def test_compare_runs(self):
        """Should compare two benchmark runs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = SWEBenchRunner(tmpdir)
            
            # First run
            run1 = runner.start_run("repo")
            runner.record_result(IssueResult(
                "1", "url", "success", 60, 10000, 0.02, True, 0, True
            ))
            runner.record_result(IssueResult(
                "2", "url", "failed", 80, 12000, 0.03, False, 1, False
            ))
            runner.complete_run()
            run1_id = run1.run_id
            
            # Second run (better)
            run2 = runner.start_run("repo")
            runner.record_result(IssueResult(
                "1", "url", "success", 50, 9000, 0.018, True, 0, True
            ))
            runner.record_result(IssueResult(
                "2", "url", "success", 70, 11000, 0.025, True, 0, True
            ))
            runner.complete_run()
            run2_id = run2.run_id
            
            comparison = runner.compare_runs(run1_id, run2_id)
            
            assert comparison["success_rate_delta"] > 0  # Run 2 is better
