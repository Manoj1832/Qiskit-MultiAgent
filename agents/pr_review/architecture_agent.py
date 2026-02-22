"""
ArchitectureAgent – Structural & Design Quality Review.

Dimension 2 of the PR review pipeline.

Detects:
  • Code duplication
  • Modularization opportunities
  • Separation of concerns violations
  • Single-responsibility principle violations
  • Better abstraction patterns
  • Circular dependencies
  • Tight coupling between modules
  • Interface improvement suggestions
"""

from __future__ import annotations

from typing import Any

from .base_review_agent import BaseReviewAgent


class ArchitectureReviewAgent(BaseReviewAgent):
    """Reviews PR diffs for structural and design quality issues."""

    name = "ArchitectureAgent"
    dimension = "design_improvements"

    @property
    def system_prompt(self) -> str:
        return """\
You are **ArchitectureAgent**, part of the **QuantumPR-GPT** elite review team.

Your job is to perform a deep, production-grade review of structural and design quality.

Before producing output:
- Simulate execution mentally.
- Think step-by-step internally.

🔎 REVIEW DIMENSIONS
- Detect code duplication
- Suggest modularization improvements
- Suggest separation of concerns
- Detect violation of single-responsibility principle
- Suggest better abstraction patterns
- Identify circular dependencies
- Detect tight coupling between modules
- Suggest interface improvements

Return ONLY valid JSON:
{
  "findings": [
    {
      "file": "...",
      "issue": "...",
      "suggestion": "...",
      "refactor_example": "..."
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
            f"Description:\n{pr_metadata.get('body', 'No description.')}",
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
                "severity": f.get("severity", "info"),
                "category": f.get("category", "unknown"),
                "issue": f.get("issue", ""),
                "suggestion": f.get("suggestion", ""),
                "refactor_example": f.get("refactor_example", ""),
            })
        return {
            "agent": self.name,
            "dimension": self.dimension,
            "findings": validated,
        }
