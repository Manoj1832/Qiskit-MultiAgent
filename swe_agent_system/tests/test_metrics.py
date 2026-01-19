"""Tests for benchmarking metrics."""

import pytest
from swe_agent_system.benchmarking.metrics import (
    MetricsCalculator,
    PatchMetrics,
    ResolutionMetrics,
)


class TestPatchMetrics:
    """Tests for PatchMetrics dataclass."""
    
    def test_total_changes(self):
        """Should calculate total changes correctly."""
        metrics = PatchMetrics(
            lines_added=10,
            lines_removed=5,
            files_changed=2,
            minimality_score=0.8,
            correctness_score=0.9,
        )
        
        assert metrics.total_changes == 15


class TestResolutionMetrics:
    """Tests for ResolutionMetrics dataclass."""
    
    def test_test_delta(self):
        """Should calculate test delta correctly."""
        metrics = ResolutionMetrics(
            issue_id="1",
            resolved=True,
            tests_before=100,
            tests_after=100,
            passing_before=90,
            passing_after=95,
            regressions=0,
            fixes=5,
            execution_time=60.0,
            tokens_used=10000,
        )
        
        assert metrics.test_delta == 5
    
    def test_is_improvement_true(self):
        """Should identify improvements."""
        metrics = ResolutionMetrics(
            issue_id="1",
            resolved=True,
            tests_before=100,
            tests_after=100,
            passing_before=90,
            passing_after=95,
            regressions=0,
            fixes=5,
            execution_time=60.0,
            tokens_used=10000,
        )
        
        assert metrics.is_improvement
    
    def test_is_improvement_false_with_regressions(self):
        """Should not be improvement if regressions occurred."""
        metrics = ResolutionMetrics(
            issue_id="1",
            resolved=True,
            tests_before=100,
            tests_after=100,
            passing_before=90,
            passing_after=92,
            regressions=1,
            fixes=3,
            execution_time=60.0,
            tokens_used=10000,
        )
        
        assert not metrics.is_improvement


class TestMetricsCalculator:
    """Tests for MetricsCalculator class."""
    
    def test_patch_minimality_under_estimate(self):
        """Patches with fewer changes than estimated should score 1.0."""
        score = MetricsCalculator.calculate_patch_minimality(
            lines_added=5,
            lines_removed=3,
            estimated_necessary=10,
        )
        assert score == 1.0
    
    def test_patch_minimality_at_estimate(self):
        """Patches matching estimate should score 1.0."""
        score = MetricsCalculator.calculate_patch_minimality(
            lines_added=5,
            lines_removed=5,
            estimated_necessary=10,
        )
        assert score == 1.0
    
    def test_patch_minimality_over_estimate(self):
        """Patches exceeding estimate should have reduced score."""
        score = MetricsCalculator.calculate_patch_minimality(
            lines_added=15,
            lines_removed=5,
            estimated_necessary=10,
        )
        assert 0 < score < 1.0
    
    def test_correctness_all_pass(self):
        """All tests passing should give high score."""
        score = MetricsCalculator.calculate_correctness_score(
            tests_passed=100,
            tests_total=100,
            regressions=0,
        )
        assert score == 1.0
    
    def test_correctness_with_failures(self):
        """Failures should reduce score."""
        score = MetricsCalculator.calculate_correctness_score(
            tests_passed=80,
            tests_total=100,
            regressions=0,
        )
        assert score == 0.8
    
    def test_correctness_with_regressions(self):
        """Regressions should heavily penalize score."""
        score = MetricsCalculator.calculate_correctness_score(
            tests_passed=95,
            tests_total=100,
            regressions=2,
        )
        assert score < 0.6  # 0.95 - 0.4 penalty
    
    def test_pr_acceptance_high(self):
        """High quality should give high acceptance likelihood."""
        score = MetricsCalculator.calculate_pr_acceptance_likelihood(
            code_quality_score=90,
            test_coverage_adequate=True,
            blocking_issues=0,
            review_score=85,
        )
        assert score > 0.8
    
    def test_pr_acceptance_with_blocking(self):
        """Blocking issues should reduce acceptance."""
        score = MetricsCalculator.calculate_pr_acceptance_likelihood(
            code_quality_score=90,
            test_coverage_adequate=True,
            blocking_issues=2,
            review_score=85,
        )
        assert score < 0.5
    
    def test_aggregate_metrics(self):
        """Should aggregate multiple results correctly."""
        results = [
            ResolutionMetrics("1", True, 100, 100, 90, 95, 0, 5, 60, 10000),
            ResolutionMetrics("2", True, 100, 100, 85, 90, 0, 5, 70, 12000),
            ResolutionMetrics("3", False, 100, 100, 80, 78, 2, 0, 80, 15000),
        ]
        
        aggregated = MetricsCalculator.aggregate_run_metrics(results)
        
        assert aggregated["total_issues"] == 3
        assert aggregated["resolved"] == 2
        assert aggregated["resolution_rate"] == 2/3
        assert aggregated["total_regressions"] == 2
        assert aggregated["total_tokens"] == 37000
    
    def test_aggregate_empty(self):
        """Should handle empty results."""
        aggregated = MetricsCalculator.aggregate_run_metrics([])
        assert aggregated["status"] == "no_results"
