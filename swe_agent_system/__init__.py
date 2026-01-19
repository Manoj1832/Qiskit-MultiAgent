"""
SWE Agent System - Enterprise-Grade Multi-Agent Software Engineering AI

A scalable, enterprise-grade multi-agent AI system that autonomously
performs software engineering tasks on real-world codebases, benchmarked
using SWE-bench-style evaluation.
"""

__version__ = "0.1.0"

from .orchestrator import Orchestrator, ExecutionContext, ExecutionState
from .agents import (
    BaseAgent,
    IssueIntelligenceAgent,
    ImpactAssessmentAgent,
    PlannerAgent,
    CodeGeneratorAgent,
    PRReviewerAgent,
    ValidatorAgent,
)
from .integrations import GitHubClient, TestRunner
from .repo_intelligence import RepositoryIndexer, DependencyGraph
from .benchmarking import SWEBenchRunner, MetricsCalculator
from .observability import configure_logging, get_logger

__all__ = [
    # Version
    "__version__",
    # Orchestrator
    "Orchestrator",
    "ExecutionContext",
    "ExecutionState",
    # Agents
    "BaseAgent",
    "IssueIntelligenceAgent",
    "ImpactAssessmentAgent",
    "PlannerAgent",
    "CodeGeneratorAgent",
    "PRReviewerAgent",
    "ValidatorAgent",
    # Integrations
    "GitHubClient",
    "TestRunner",
    # Repo Intelligence
    "RepositoryIndexer",
    "DependencyGraph",
    # Benchmarking
    "SWEBenchRunner",
    "MetricsCalculator",
    # Observability
    "configure_logging",
    "get_logger",
]
