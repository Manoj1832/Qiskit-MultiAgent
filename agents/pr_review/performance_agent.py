"""
PerformanceAgent – Performance & Scalability Review.

Dimension 4 of the PR review pipeline.

Detects:
  • Unnecessary recomputation
  • Inefficient loops
  • Vectorization opportunities
  • Memory inefficiencies
  • Blocking calls in async contexts
  • Caching opportunities
"""

from __future__ import annotations

from typing import Any

from .base_review_agent import BaseReviewAgent


class PerformanceReviewAgent(BaseReviewAgent):
    """Reviews PR diffs for performance and scalability issues."""

    name = "PerformanceAgent"
    dimension = "performance_optimizations"

    @property
    def system_prompt(self) -> str:
        return """\
You are **PerformanceAgent**, part of the **QuantumPR-GPT** elite review team.

Your job is to identify performance bottlenecks and suggest optimizations.

Before producing output:
- Simulate execution mentally.
- Think step-by-step internally.

🔎 REVIEW DIMENSIONS
- Identify unnecessary recomputation
- Detect inefficient loops
- Suggest vectorization where possible
- Identify memory inefficiencies
- Flag blocking calls in async contexts
- Suggest caching where beneficial

Return ONLY valid JSON:
{
  "findings": [
    {
      "file": "...",
      "issue": "...",
      "improvement": "..."
    }
  ]
}

No markdown.
No explanation outside JSON.
"""

    def build_user_prompt(self, pr_diff: str, pr_metadata: dict[str, Any]) -> str:
        parts = [
            "=== PULL REQUEST METADATA ===",
            f"Title: {pr_metadata.get('title', 'N/A')}",
            f"Files Changed: {pr_metadata.get('files_changed', 'N/A')}",
            "",
            "=== UNIFIED DIFF ===",
            pr_diff[:12000],
        ]
        return "\n".join(parts)

    def parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        findings = raw.get("findings", [])
        validated: list[dict[str, Any]] = []
        for f in findings:
            validated.append({
                "file": f.get("file", "unknown"),
                "line": f.get("line", 0),
                "severity": f.get("severity", "info"),
                "category": f.get("category", "unknown"),
                "issue": f.get("issue", ""),
                "improvement": f.get("improvement", ""),
                "estimated_impact": f.get("estimated_impact", ""),
            })
        return {
            "agent": self.name,
            "dimension": self.dimension,
            "findings": validated,
        }
