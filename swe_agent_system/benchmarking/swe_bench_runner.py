"""
SWE-bench style evaluation runner.
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class IssueResult:
    """Result of processing a single issue."""
    issue_id: str
    issue_url: str
    status: str  # success, failed, timeout, error
    execution_time_seconds: float
    tokens_used: int
    cost_usd: float
    tests_passed: bool
    regressions: int
    patch_generated: bool
    patch_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkRun:
    """Complete benchmark run results."""
    run_id: str
    started_at: str
    completed_at: str | None = None
    repository: str = ""
    total_issues: int = 0
    results: list[IssueResult] = field(default_factory=list)
    
    def add_result(self, result: IssueResult) -> None:
        """Add an issue result to the benchmark."""
        self.results.append(result)
        self.total_issues = len(self.results)
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics of the benchmark run."""
        if not self.results:
            return {"status": "no_results"}
        
        successful = [r for r in self.results if r.status == "success"]
        failed = [r for r in self.results if r.status == "failed"]
        
        total_tokens = sum(r.tokens_used for r in self.results)
        total_cost = sum(r.cost_usd for r in self.results)
        total_time = sum(r.execution_time_seconds for r in self.results)
        
        tests_passed = sum(1 for r in self.results if r.tests_passed)
        patches_generated = sum(1 for r in self.results if r.patch_generated)
        total_regressions = sum(r.regressions for r in self.results)
        
        return {
            "run_id": self.run_id,
            "repository": self.repository,
            "total_issues": self.total_issues,
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / self.total_issues if self.total_issues > 0 else 0,
            "tests_passed": tests_passed,
            "test_pass_rate": tests_passed / self.total_issues if self.total_issues > 0 else 0,
            "patches_generated": patches_generated,
            "total_regressions": total_regressions,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "total_time_seconds": total_time,
            "avg_time_per_issue": total_time / self.total_issues if self.total_issues > 0 else 0,
        }
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "repository": self.repository,
            "total_issues": self.total_issues,
            "summary": self.get_summary(),
            "results": [asdict(r) for r in self.results],
        }


class SWEBenchRunner:
    """
    Runner for SWE-bench style evaluations.
    """
    
    def __init__(self, output_dir: Path | str = "experiments"):
        """
        Initialize the benchmark runner.
        
        Args:
            output_dir: Directory to store benchmark results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_run: BenchmarkRun | None = None
    
    def start_run(self, repository: str) -> BenchmarkRun:
        """
        Start a new benchmark run.
        
        Args:
            repository: Repository being benchmarked
            
        Returns:
            New BenchmarkRun instance
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        self.current_run = BenchmarkRun(
            run_id=run_id,
            started_at=datetime.utcnow().isoformat(),
            repository=repository,
        )
        return self.current_run
    
    def record_result(self, result: IssueResult) -> None:
        """Record a result for the current run."""
        if self.current_run:
            self.current_run.add_result(result)
    
    def complete_run(self) -> Path:
        """
        Complete the current run and save results.
        
        Returns:
            Path to the saved results file
        """
        if not self.current_run:
            raise ValueError("No active benchmark run")
        
        self.current_run.completed_at = datetime.utcnow().isoformat()
        
        # Save to file
        output_path = self.output_dir / f"{self.current_run.run_id}.json"
        with open(output_path, "w") as f:
            json.dump(self.current_run.to_dict(), f, indent=2)
        
        return output_path
    
    def load_run(self, run_id: str) -> BenchmarkRun:
        """Load a previous benchmark run."""
        run_path = self.output_dir / f"{run_id}.json"
        
        with open(run_path) as f:
            data = json.load(f)
        
        run = BenchmarkRun(
            run_id=data["run_id"],
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            repository=data.get("repository", ""),
            total_issues=data.get("total_issues", 0),
        )
        
        for result_data in data.get("results", []):
            result = IssueResult(**result_data)
            run.results.append(result)
        
        return run
    
    def compare_runs(self, run_id_1: str, run_id_2: str) -> dict[str, Any]:
        """Compare two benchmark runs."""
        run1 = self.load_run(run_id_1)
        run2 = self.load_run(run_id_2)
        
        summary1 = run1.get_summary()
        summary2 = run2.get_summary()
        
        return {
            "run_1": run_id_1,
            "run_2": run_id_2,
            "success_rate_delta": summary2["success_rate"] - summary1["success_rate"],
            "test_pass_rate_delta": summary2["test_pass_rate"] - summary1["test_pass_rate"],
            "avg_time_delta": summary2["avg_time_per_issue"] - summary1["avg_time_per_issue"],
            "cost_delta": summary2["total_cost_usd"] - summary1["total_cost_usd"],
        }
