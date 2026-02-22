"""
AggregatorAgent – Final Consolidation & Scoring Agent.

Dimension 6 (final) of the PR review pipeline.

Receives output from all 5 specialist agents, then:
  • Deduplicates findings
  • Assigns risk level (Low / Medium / High)
  • Computes a quality score (0–100)
  • Produces the final structured JSON report
  • Makes the overall recommendation (Approve / Request Changes / Major Revision)
"""

from __future__ import annotations

import json
from typing import Any

from .base_review_agent import BaseReviewAgent


class AggregatorReviewAgent(BaseReviewAgent):
    """Consolidates all sub-agent findings into a final PR review report."""

    name = "AggregatorAgent"
    dimension = "final_report"

    @property
    def system_prompt(self) -> str:
        return """\
You are **QuantumPR-GPT**, an elite Qiskit-aware pull request review agent and final aggregator.

Your job is to perform a deep, production-grade code review on pull requests by consolidating reports from 5 specialist agents.

You do NOT summarize normally; you provide a high-fidelity engineering analysis.

Before producing output:
1. Simulate execution mentally.
2. Simulate pytest.
3. Simulate transpiler passes if Qiskit involved.
4. Think step-by-step internally.

Return ONLY valid JSON:
{
  "summary": "...",
  "risk_level": "Low | Medium | High",
  "syntax_issues": [
    {
      "file": "...",
      "line": 0,
      "issue": "...",
      "fix": "..."
    }
  ],
  "design_improvements": [
    {
      "file": "...",
      "issue": "...",
      "suggestion": "...",
      "refactor_example": "..."
    }
  ],
  "quantum_validation": [
    {
      "file": "...",
      "gate_or_logic": "...",
      "problem": "...",
      "mathematical_reasoning": "...",
      "corrected_code": "..."
    }
  ],
  "performance_optimizations": [
    {
      "file": "...",
      "issue": "...",
      "improvement": "..."
    }
  ],
  "security_concerns": [
    {
      "file": "...",
      "risk": "...",
      "recommendation": "..."
    }
  ],
  "overall_recommendation": "Approve | Request Changes | Major Revision Required"
}

No markdown.
No explanation outside JSON.
No repetition of input.
"""

    def build_user_prompt(self, pr_diff: str, pr_metadata: dict[str, Any]) -> str:
        agent_reports = pr_metadata.get("agent_reports", {})

        parts = [
            "=== PULL REQUEST METADATA ===",
            f"Title: {pr_metadata.get('title', 'N/A')}",
            f"Author: {pr_metadata.get('author', 'N/A')}",
            f"Files Changed: {pr_metadata.get('files_changed', 'N/A')}",
            "",
            "=== SPECIALIST AGENT REPORTS ===",
            "",
        ]

        for agent_name, report in agent_reports.items():
            parts.append(f"--- {agent_name} ---")
            parts.append(json.dumps(report, indent=2))
            parts.append("")

        return "\n".join(parts)

    def parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": raw.get("summary", ""),
            "risk_level": raw.get("risk_level", "Medium"),
            "quality_score": raw.get("quality_score", 50),
            "syntax_issues": raw.get("syntax_issues", []),
            "design_improvements": raw.get("design_improvements", []),
            "quantum_validation": raw.get("quantum_validation", []),
            "performance_optimizations": raw.get("performance_optimizations", []),
            "security_concerns": raw.get("security_concerns", []),
            "overall_recommendation": raw.get("overall_recommendation", "Request Changes"),
            "review_stats": raw.get("review_stats", {
                "total_findings": 0,
                "critical": 0,
                "errors": 0,
                "warnings": 0,
                "info": 0,
            }),
        }
