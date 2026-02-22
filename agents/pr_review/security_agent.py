"""
SecurityAgent – Security & Robustness Review.

Dimension 5 of the PR review pipeline.

Detects:
  • Unsafe eval/exec usage
  • Injection risks (SQL, command, template)
  • Input sanitization gaps
  • Poor error handling
  • Meaningless exception types
  • Overly broad exception catching
"""

from __future__ import annotations

from typing import Any

from .base_review_agent import BaseReviewAgent


class SecurityReviewAgent(BaseReviewAgent):
    """Reviews PR diffs for security vulnerabilities and robustness issues."""

    name = "SecurityAgent"
    dimension = "security_concerns"

    @property
    def system_prompt(self) -> str:
        return """\
You are **SecurityAgent**, part of the **QuantumPR-GPT** elite review team.

Your job is to identify security vulnerabilities and robustness issues.

Before producing output:
- Simulate execution mentally.
- Think step-by-step internally.

🔎 REVIEW DIMENSIONS
- Detect unsafe eval/exec
- Detect injection risks
- Validate input sanitization
- Suggest better error handling
- Ensure meaningful exception types
- Detect overly broad exception catching

Return ONLY valid JSON:
{
  "findings": [
    {
      "file": "...",
      "risk": "...",
      "recommendation": "..."
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
                "severity": f.get("severity", "warning"),
                "category": f.get("category", "unknown"),
                "risk": f.get("risk", ""),
                "recommendation": f.get("recommendation", ""),
            })
        return {
            "agent": self.name,
            "dimension": self.dimension,
            "findings": validated,
        }
