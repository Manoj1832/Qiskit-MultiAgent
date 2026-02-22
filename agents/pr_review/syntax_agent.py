"""
SyntaxAgent – Syntax & Runtime Safety Review.

Dimension 1 of the PR review pipeline.

Detects:
  • Syntax errors, missing imports, undefined variables
  • Incorrect function signatures, dead code
  • Potential runtime exceptions
  • Incorrect async usage, type mismatches
"""

from __future__ import annotations

from typing import Any

from .base_review_agent import BaseReviewAgent


class SyntaxReviewAgent(BaseReviewAgent):
    """Reviews PR diffs for syntax and runtime safety issues."""

    name = "SyntaxAgent"
    dimension = "syntax_issues"

    @property
    def system_prompt(self) -> str:
        return """\
You are **SyntaxAgent**, part of the **QuantumPR-GPT** elite review team.

Your job is to perform a deep, production-grade review of syntax and runtime safety.

Before producing output:
- Simulate execution mentally.
- Simulate pytest.
- Think step-by-step internally.

🔎 REVIEW DIMENSIONS
- Detect syntax errors
- Identify missing imports
- Detect undefined variables
- Spot incorrect function signatures
- Detect dead code
- Flag potential runtime exceptions
- Identify incorrect async usage
- Detect type mismatches

Return ONLY valid JSON:
{
  "findings": [
    {
      "file": "...",
      "line": 0,
      "issue": "...",
      "fix": "..."
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
            f"Author: {pr_metadata.get('author', 'N/A')}",
            f"Files Changed: {pr_metadata.get('files_changed', 'N/A')}",
            f"Description:\n{pr_metadata.get('body', 'No description provided.')}",
            "",
            "=== UNIFIED DIFF ===",
            pr_diff[:12000],  # cap to avoid token overflow
        ]
        return "\n".join(parts)

    def parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        findings = raw.get("findings", [])
        # Normalize and validate each finding
        validated: list[dict[str, Any]] = []
        for f in findings:
            validated.append({
                "file": f.get("file", "unknown"),
                "line": f.get("line", 0),
                "severity": f.get("severity", "warning"),
                "category": f.get("category", "unknown"),
                "issue": f.get("issue", ""),
                "fix": f.get("fix", ""),
            })
        return {
            "agent": self.name,
            "dimension": self.dimension,
            "findings": validated,
        }
