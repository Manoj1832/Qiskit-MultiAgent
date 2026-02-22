"""
QuantumValidatorAgent – Quantum & Qiskit-Specific Validation.

Dimension 3 of the PR review pipeline.

Validates:
  • Gate definitions and unitary consistency
  • .inverse() correctness
  • Operator(gate).equiv(...) usage
  • Controlled gate structure
  • Classical bit misuse in gates
  • Global phase correctness
  • Floating-point comparisons (flags exact == on quantum objects)
  • Transpiler safety
  • Decomposition consistency
"""

from __future__ import annotations

import json
from typing import Any

from .base_review_agent import BaseReviewAgent
from domain.qiskit_knowledge import (
    QUANTUM_PRECISION,
    STANDARD_GATES,
    GATE_VS_INSTRUCTION,
    TRANSPILER_PASS_CATEGORIES,
    TRANSPILER_PRESET_LEVELS,
    COMMON_BUG_PATTERNS,
)


class QuantumValidatorReviewAgent(BaseReviewAgent):
    """Reviews quantum/Qiskit-specific correctness in PR diffs."""

    name = "QuantumValidator"
    dimension = "quantum_validation"

    @property
    def system_prompt(self) -> str:
        gate_taxonomy = json.dumps(STANDARD_GATES, indent=2)
        precision = json.dumps(QUANTUM_PRECISION, indent=2)
        bug_patterns = json.dumps(COMMON_BUG_PATTERNS, indent=2)

        return f"""\
You are the **QuantumValidatorAgent** of the **QuantumPR-GPT** team. You are an elite Qiskit-aware engineer.

Your job is to perform a deep, production-grade code review on Qiskit logic.

Before producing output:
- Simulate execution mentally.
- Simulate transpiler passes.
- Think step-by-step internally.

═══ REVIEW DIMENSIONS ═══
- Validate gate definitions & Verify unitary consistency
- Check .inverse() correctness (Operator(gate).equiv(...))
- Validate controlled gate structure
- Detect misuse of classical bits in gates
- Check global phase correctness
- Ensure floating-point comparisons use tolerances (Flag exact == usage)
- Validate transpiler safety
- Ensure decomposition consistency

═══ QISKIT CONTEXT ═══
{gate_taxonomy}
{GATE_VS_INSTRUCTION}
Precision: {precision}

═══ COMMON BUG PATTERNS ═══
{bug_patterns}

If quantum logic is incorrect, you MUST provide:
1. Mathematical reasoning
2. Corrected circuit logic
3. Corrected code snippet

Return ONLY valid JSON:
{{
  "findings": [
    {{
      "file": "...",
      "gate_or_logic": "...",
      "problem": "...",
      "mathematical_reasoning": "...",
      "corrected_code": "..."
    }}
  ]
}}

No markdown.
No explanation outside JSON.
"""

    def build_user_prompt(self, pr_diff: str, pr_metadata: dict[str, Any]) -> str:
        parts = [
            "=== PULL REQUEST METADATA ===",
            f"Title: {pr_metadata.get('title', 'N/A')}",
            f"Files Changed: {pr_metadata.get('files_changed', 'N/A')}",
            f"Labels: {', '.join(pr_metadata.get('labels', []))}",
            "",
            "=== UNIFIED DIFF ===",
            pr_diff[:14000],
        ]
        return "\n".join(parts)

    def parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        findings = raw.get("findings", [])
        validated: list[dict[str, Any]] = []
        for f in findings:
            validated.append({
                "file": f.get("file", "unknown"),
                "gate_or_logic": f.get("gate_or_logic", ""),
                "severity": f.get("severity", "warning"),
                "problem": f.get("problem", ""),
                "mathematical_reasoning": f.get("mathematical_reasoning", ""),
                "corrected_code": f.get("corrected_code", ""),
            })
        return {
            "agent": self.name,
            "dimension": self.dimension,
            "findings": validated,
        }
