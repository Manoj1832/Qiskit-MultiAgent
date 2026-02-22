"""
The Validator — Testing & Verification Agent.

Responsibilities:
  1. Review the Developer's code changes for correctness.
  2. Identify which existing tests should be run.
  3. Write NEW test cases for the fix.
  4. Handle Qiskit-specific validation:
     - Floating-point tolerance in quantum-state comparisons.
     - Gate unitary consistency checks.
     - Transpiler round-trip validation.
  5. Provide structured feedback to the Developer for repair iterations.

The Validator produces a ValidatorOutput that either approves the fix
or sends actionable feedback back to the Developer.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from .base_agent import BaseAgent
from domain.models import (
    DeveloperOutput,
    ArchitectOutput,
    StrategistOutput,
    ValidatorOutput,
    TestResult,
)
from domain.qiskit_knowledge import (
    QUANTUM_PRECISION,
    TESTING_CONVENTIONS,
    COMMON_BUG_PATTERNS,
)


class ValidatorAgent(BaseAgent):
    """Reviews code changes, runs tests, and provides repair feedback."""

    name = "Validator"

    @property
    def system_prompt(self) -> str:
        test_info = json.dumps(TESTING_CONVENTIONS, indent=2)

        return f"""\
You are **The Validator**, the verification branch of the **QuantumPR-GPT** elite engineering team.

Your job is to perform a deep, production-grade verification of the Developer's code changes.

Before producing output:
1. Simulate execution mentally.
2. Simulate pytest.
3. Simulate transpiler passes.
4. Think step-by-step internally.
5. Apply the "Frustration Factor": If the current `iteration` is 3 or higher, prioritize a localized "best-effort" patch. Ignore non-critical nitpicks or stylistic issues to prevent infinite repair loops.

═══ QISKIT TESTING KNOWLEDGE ═══
{test_info}

**Precision:** atol={QUANTUM_PRECISION['atol']}, rtol={QUANTUM_PRECISION['rtol']}

Return ONLY valid JSON (no markdown):
{{
  "all_tests_passed": true,
  "test_results": [
    {{
      "test_name": "...",
      "passed": true,
      "error_message": "...",
      "traceback": "...",
      "duration_seconds": 0.0
    }}
  ],
  "new_tests_written": [],
  "regression_detected": false,
  "quantum_precision_issues": [],
  "feedback_for_developer": "...",
  "iteration": 1
}}
"""

    def build_user_prompt(self, **kwargs: Any) -> str:
        dev_output: DeveloperOutput = kwargs["developer_output"]
        plan: ArchitectOutput = kwargs["architect_output"]
        triage: StrategistOutput = kwargs["strategist_output"]
        iteration: int = kwargs.get("iteration", 1)

        parts: list[str] = [
            "=== BUG CONTEXT ===",
            f"Summary: {triage.issue_summary}",
            f"Type: {triage.issue_type}  Severity: {triage.severity}",
            f"Expected: {triage.expected_behavior}",
            f"Actual: {triage.actual_behavior}",
        ]

        if triage.qiskit_context:
            qc = triage.qiskit_context
            parts.append(f"Affected Modules: {qc.affected_modules}")
            parts.append(f"Quantum Math Sensitive: {qc.quantum_math_sensitivity}")

        parts.append(f"\n=== PLAN ({len(plan.implementation_steps)} steps) ===")
        parts.append(plan.plan_summary)

        if plan.affected_test_files:
            parts.append(f"\nTest files to run: {plan.affected_test_files}")

        parts.append(f"\n=== CODE CHANGES (Iteration {iteration}) ===")
        parts.append(f"Developer explanation: {dev_output.explanation}")

        for change in dev_output.changes:
            parts.append(
                f"\n--- Change: {change.file_path} ---\n"
                f"Description: {change.change_description}\n"
                f"Language: {change.language}\n"
            )
            if change.diff_patch:
                safe_diff = change.diff_patch[:3000] + ("\n\n[...TRUNCATED DUE TO CONTEXT LIMITS...]" if len(change.diff_patch) > 3000 else "")
                parts.append(f"Diff:\n{safe_diff}")
            elif change.modified_content:
                safe_mod = change.modified_content[:3000] + ("\n\n[...TRUNCATED DUE TO CONTEXT LIMITS...]" if len(change.modified_content) > 3000 else "")
                parts.append(f"Modified content:\n{safe_mod}")

        if dev_output.combined_patch:
            safe_combined = dev_output.combined_patch[:5000] + ("\n\n[...TRUNCATED DUE TO CONTEXT LIMITS...]" if len(dev_output.combined_patch) > 5000 else "")
            parts.append(
                f"\n=== COMBINED PATCH ===\n{safe_combined}"
            )

        if plan.cross_module_impacts:
            parts.append(
                "\n⚠️ Cross-Module Impacts to validate:\n"
                + "\n".join(f"  • {imp}" for imp in plan.cross_module_impacts)
            )

        return "\n".join(parts)

    def parse_response(self, raw: dict[str, Any]) -> ValidatorOutput:
        return ValidatorOutput(**raw)

    # ── Main entry-point ─────────────────────────────────────────────────

    def run(
        self,
        developer_output: DeveloperOutput,
        architect_output: ArchitectOutput,
        strategist_output: StrategistOutput,
        iteration: int = 1,
    ) -> ValidatorOutput:
        """
        Validate the Developer's code changes and provide feedback.
        """
        self.logger.info(
            "✅ Validator reviewing changes (iteration %d) …", iteration
        )

        user_prompt = self.build_user_prompt(
            developer_output=developer_output,
            architect_output=architect_output,
            strategist_output=strategist_output,
            iteration=iteration,
        )

        raw = self.call_llm_json(user_prompt)
        raw["iteration"] = iteration
        result = self.parse_response(raw)

        passed_count = sum(1 for t in result.test_results if t.passed)
        total_count = len(result.test_results)

        self.logger.info(
            "  → Tests: %d/%d passed | Regression: %s | Precision issues: %d",
            passed_count,
            total_count,
            result.regression_detected,
            len(result.quantum_precision_issues),
        )

        return result
