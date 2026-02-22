"""
Advanced PR Review Agent – Multi-Agent Architecture.

This package implements a 6-agent review pipeline:
  1. SyntaxAgent       – Syntax & runtime safety checks
  2. QuantumValidator   – Qiskit/quantum-specific validation
  3. ArchitectureAgent  – Structural & design quality audit
  4. PerformanceAgent   – Performance & scalability analysis
  5. SecurityAgent      – Security & robustness assessment
  6. AggregatorAgent    – Final consolidation → structured JSON report
"""

from .syntax_agent import SyntaxReviewAgent
from .quantum_validator_agent import QuantumValidatorReviewAgent
from .architecture_agent import ArchitectureReviewAgent
from .performance_agent import PerformanceReviewAgent
from .security_agent import SecurityReviewAgent
from .aggregator_agent import AggregatorReviewAgent
from .pr_review_orchestrator import PRReviewOrchestrator

__all__ = [
    "SyntaxReviewAgent",
    "QuantumValidatorReviewAgent",
    "ArchitectureReviewAgent",
    "PerformanceReviewAgent",
    "SecurityReviewAgent",
    "AggregatorReviewAgent",
    "PRReviewOrchestrator",
]
