"""
Metrics collection and calculation for benchmarking.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class PatchMetrics:
    """Metrics for evaluating a generated patch."""
    lines_added: int
    lines_removed: int
    files_changed: int
    minimality_score: float  # 0-1, higher is more minimal
    correctness_score: float  # 0-1, based on test results
    
    @property
    def total_changes(self) -> int:
        return self.lines_added + self.lines_removed


@dataclass
class ResolutionMetrics:
    """Metrics for issue resolution quality."""
    issue_id: str
    resolved: bool
    tests_before: int
    tests_after: int
    passing_before: int
    passing_after: int
    regressions: int
    fixes: int
    execution_time: float
    tokens_used: int
    
    @property
    def test_delta(self) -> int:
        return self.passing_after - self.passing_before
    
    @property
    def is_improvement(self) -> bool:
        return self.test_delta > 0 and self.regressions == 0


class MetricsCalculator:
    """
    Calculates various metrics for benchmarking.
    """
    
    @staticmethod
    def calculate_patch_minimality(
        lines_added: int,
        lines_removed: int,
        estimated_necessary: int,
    ) -> float:
        """
        Calculate how minimal a patch is compared to expected changes.
        
        Args:
            lines_added: Lines added in the patch
            lines_removed: Lines removed in the patch
            estimated_necessary: Estimated necessary line changes
            
        Returns:
            Minimality score between 0 and 1
        """
        if estimated_necessary == 0:
            return 1.0 if lines_added + lines_removed == 0 else 0.0
        
        total_changes = lines_added + lines_removed
        
        if total_changes <= estimated_necessary:
            return 1.0
        
        # Score decreases as changes exceed estimate
        excess_ratio = (total_changes - estimated_necessary) / estimated_necessary
        return max(0.0, 1.0 - (excess_ratio * 0.5))
    
    @staticmethod
    def calculate_correctness_score(
        tests_passed: int,
        tests_total: int,
        regressions: int,
    ) -> float:
        """
        Calculate correctness score based on test results.
        
        Args:
            tests_passed: Number of tests passing after fix
            tests_total: Total number of tests
            regressions: Number of tests that started failing
            
        Returns:
            Correctness score between 0 and 1
        """
        if tests_total == 0:
            return 0.5  # No tests, uncertain
        
        pass_rate = tests_passed / tests_total
        
        # Penalize regressions heavily
        regression_penalty = min(1.0, regressions * 0.2)
        
        return max(0.0, pass_rate - regression_penalty)
    
    @staticmethod
    def calculate_pr_acceptance_likelihood(
        code_quality_score: float,
        test_coverage_adequate: bool,
        blocking_issues: int,
        review_score: float,
    ) -> float:
        """
        Estimate likelihood that a PR would be accepted.
        
        Args:
            code_quality_score: Code quality score (0-100)
            test_coverage_adequate: Whether test coverage is sufficient
            blocking_issues: Number of blocking review issues
            review_score: Overall review score (0-100)
            
        Returns:
            Acceptance likelihood between 0 and 1
        """
        # Normalize scores to 0-1
        quality_factor = code_quality_score / 100
        review_factor = review_score / 100
        coverage_factor = 1.0 if test_coverage_adequate else 0.7
        
        # Blocking issues significantly reduce likelihood
        blocking_penalty = min(1.0, blocking_issues * 0.3)
        
        base_score = (quality_factor * 0.3 + review_factor * 0.4 + coverage_factor * 0.3)
        
        return max(0.0, base_score - blocking_penalty)
    
    @staticmethod
    def aggregate_run_metrics(results: list[ResolutionMetrics]) -> dict[str, Any]:
        """
        Aggregate metrics across multiple issue resolutions.
        
        Args:
            results: List of resolution metrics
            
        Returns:
            Aggregated metrics dictionary
        """
        if not results:
            return {"status": "no_results"}
        
        total = len(results)
        resolved = sum(1 for r in results if r.resolved)
        improvements = sum(1 for r in results if r.is_improvement)
        total_regressions = sum(r.regressions for r in results)
        total_fixes = sum(r.fixes for r in results)
        total_tokens = sum(r.tokens_used for r in results)
        total_time = sum(r.execution_time for r in results)
        
        return {
            "total_issues": total,
            "resolved": resolved,
            "resolution_rate": resolved / total,
            "improvements": improvements,
            "improvement_rate": improvements / total,
            "total_regressions": total_regressions,
            "total_fixes": total_fixes,
            "net_test_delta": total_fixes - total_regressions,
            "total_tokens": total_tokens,
            "avg_tokens_per_issue": total_tokens / total,
            "total_time_seconds": total_time,
            "avg_time_per_issue": total_time / total,
        }
