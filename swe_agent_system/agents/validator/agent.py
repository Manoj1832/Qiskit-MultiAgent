"""
Validator Agent - Test execution and verification.
"""

from typing import Any

from ..base_agent import BaseAgent, AgentConfig
from ...orchestrator.state_machine import ExecutionContext


class ValidatorAgent(BaseAgent):
    """
    Agent responsible for validating fixes through testing.
    
    Capabilities:
    - Analyze test results
    - Detect regressions
    - Verify fix correctness
    - Recommend additional tests
    """
    
    def __init__(self, model: str = "gemini-2.5-flash"):  # Faster model for validation
        config = AgentConfig(
            name="validator",
            model=model,
            temperature=0.1,
            max_output_tokens=4096,
        )
        super().__init__(config)
    
    def get_system_prompt(self) -> str:
        return """You are a QA engineer specializing in test analysis and validation.

Your task is to analyze test results and determine if a fix is successful.

Consider:
- Did the tests pass?
- Were there any regressions?
- Is the fix complete?
- Are there edge cases not covered?

Always respond with a valid JSON object containing your validation results."""
    
    def build_prompt(self, context: ExecutionContext) -> str:
        issue_analysis = context.issue_analysis
        patches = context.generated_patch
        review = context.review_result
        
        # Test results would be populated by the test runner
        test_results = context.validation_result.get("test_output", {})
        
        return f"""Validate the following fix:

## Issue Summary
{issue_analysis.get('summary', 'No summary')}

## Changes Made
{patches.get('summary', 'No summary')}

## Review Result
**Verdict:** {review.get('overall_verdict', 'unknown')}
**Score:** {review.get('overall_score', 0)}

## Test Results
{self._format_test_results(test_results)}

---

Provide your validation as a JSON object:
```json
{{
    "tests_passed": true,
    "all_tests_passed": true,
    "new_tests_passed": true,
    "regressions_detected": false,
    "regression_details": [],
    "fix_verified": true,
    "fix_complete": true,
    "missing_coverage": ["areas", "not", "tested"],
    "edge_cases": ["edge", "cases", "to", "consider"],
    "validation_summary": "Summary of validation results",
    "ready_for_merge": true,
    "blocking_issues": [],
    "recommendations": ["any", "recommendations"],
    "confidence_score": 0.9
}}
```"""
    
    def _format_test_results(self, results: dict) -> str:
        if not results:
            return "No test results available"
        
        return f"""
- **Passed:** {results.get('passed', 0)}
- **Failed:** {results.get('failed', 0)}
- **Skipped:** {results.get('skipped', 0)}
- **Total:** {results.get('total', 0)}

**Error Output:**
```
{results.get('error_output', 'No errors')[:1000]}
```
"""
    
    def parse_response(self, response_text: str) -> dict[str, Any]:
        parsed = self._extract_json_from_response(response_text)
        
        # Ensure required fields have defaults
        defaults = {
            "tests_passed": False,
            "all_tests_passed": False,
            "new_tests_passed": False,
            "regressions_detected": False,
            "regression_details": [],
            "fix_verified": False,
            "fix_complete": False,
            "missing_coverage": [],
            "edge_cases": [],
            "validation_summary": "",
            "ready_for_merge": False,
            "blocking_issues": [],
            "recommendations": [],
            "confidence_score": 0.5,
        }
        
        for key, default_value in defaults.items():
            if key not in parsed:
                parsed[key] = default_value
        
        parsed["success"] = True
        return parsed
