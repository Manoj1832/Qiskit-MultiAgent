"""
Pydantic models for the Advanced PR Review pipeline.

These models define the structured contracts between the review agents
and the final aggregated report format.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enumerations ─────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ReviewRecommendation(str, Enum):
    APPROVE = "Approve"
    REQUEST_CHANGES = "Request Changes"
    MAJOR_REVISION = "Major Revision Required"


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ── Individual Finding Models ────────────────────────────────────────────────

class SyntaxFinding(BaseModel):
    """A single syntax/runtime safety finding."""
    file: str
    line: int = 0
    severity: str = "warning"
    category: str = ""
    issue: str
    fix: str = ""


class DesignFinding(BaseModel):
    """A single structural/design quality finding."""
    file: str
    severity: str = "info"
    category: str = ""
    issue: str
    suggestion: str = ""
    refactor_example: str = ""


class QuantumFinding(BaseModel):
    """A single quantum/Qiskit validation finding."""
    file: str
    gate_or_logic: str = ""
    severity: str = "warning"
    problem: str
    mathematical_reasoning: str = ""
    corrected_code: str = ""


class PerformanceFinding(BaseModel):
    """A single performance optimization finding."""
    file: str
    line: int = 0
    severity: str = "info"
    category: str = ""
    issue: str
    improvement: str = ""
    estimated_impact: str = ""


class SecurityFinding(BaseModel):
    """A single security/robustness finding."""
    file: str
    line: int = 0
    severity: str = "warning"
    category: str = ""
    risk: str
    recommendation: str = ""


# ── Review Statistics ────────────────────────────────────────────────────────

class ReviewStats(BaseModel):
    """Summary statistics of the review findings."""
    total_findings: int = 0
    critical: int = 0
    errors: int = 0
    warnings: int = 0
    info: int = 0


# ── PR Metadata ──────────────────────────────────────────────────────────────

class PRMetadata(BaseModel):
    """Metadata about the reviewed pull request."""
    repo: str
    pr_number: int
    pr_url: str = ""
    pr_title: str = ""
    pr_author: str = ""
    files_changed_count: int = 0
    additions: int = 0
    deletions: int = 0
    review_duration_seconds: float = 0.0
    agents_used: list[str] = Field(default_factory=list)


# ── Final Aggregated Report ──────────────────────────────────────────────────

class PRReviewReport(BaseModel):
    """
    The complete, structured PR review report produced by the
    multi-agent review pipeline.
    """
    summary: str = ""
    risk_level: str = "Medium"
    quality_score: int = 50
    syntax_issues: list[SyntaxFinding] = Field(default_factory=list)
    design_improvements: list[DesignFinding] = Field(default_factory=list)
    quantum_validation: list[QuantumFinding] = Field(default_factory=list)
    performance_optimizations: list[PerformanceFinding] = Field(default_factory=list)
    security_concerns: list[SecurityFinding] = Field(default_factory=list)
    overall_recommendation: str = "Request Changes"
    review_stats: ReviewStats = Field(default_factory=ReviewStats)
    meta: Optional[PRMetadata] = None
    reviewed_at: Optional[datetime] = None
