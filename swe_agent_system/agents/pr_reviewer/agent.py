"""
PR Review Agent - Static and semantic code review.
"""

from typing import Any

from ..base_agent import BaseAgent, AgentConfig
from ...orchestrator.state_machine import ExecutionContext


class PRReviewerAgent(BaseAgent):
    """
    Agent responsible for reviewing generated code patches.
    
    Capabilities:
    - Static code analysis
    - Semantic review for correctness
    - Style and convention checking
    - Security vulnerability detection
    """
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        config = AgentConfig(
            name="pr_reviewer",
            model=model,
            temperature=0.2,
            max_output_tokens=8192,
        )
        super().__init__(config)
    
    def get_system_prompt(self) -> str:
        return """You are a senior code reviewer specializing in Python projects.

Your task is to review generated code patches for quality, correctness, and adherence to best practices.

Be thorough but constructive. Focus on:
- Correctness: Does the code fix the issue?
- Quality: Is the code clean, readable, and maintainable?
- Safety: Are there security or stability concerns?
- Style: Does it follow project conventions?

Always respond with a valid JSON object containing your review."""
    
    def build_prompt(self, context: ExecutionContext) -> str:
        issue_analysis = context.issue_analysis
        plan = context.execution_plan
        patches = context.generated_patch
        
        return f"""Review the following code patches:

## Issue Being Fixed
{issue_analysis.get('summary', 'No summary')}

## Fix Plan
{plan.get('plan_summary', 'No plan summary')}

## Generated Patches
{self._format_patches(patches.get('patches', []))}

## Generated Tests
{self._format_tests(patches.get('test_code', []))}

---

Provide your review as a JSON object:
```json
{{
    "overall_verdict": "approve|request_changes|needs_discussion",
    "overall_score": 85,
    "correctness": {{
        "score": 90,
        "issues": ["list", "of", "correctness", "issues"],
        "suggestions": ["improvements"]
    }},
    "code_quality": {{
        "score": 80,
        "issues": ["quality", "issues"],
        "suggestions": ["improvements"]
    }},
    "security": {{
        "score": 95,
        "vulnerabilities": ["any", "security", "issues"],
        "recommendations": ["security", "improvements"]
    }},
    "style": {{
        "score": 85,
        "issues": ["style", "issues"],
        "suggestions": ["style", "fixes"]
    }},
    "test_coverage": {{
        "adequate": true,
        "missing_tests": ["what", "should", "be", "tested"],
        "suggestions": ["test", "improvements"]
    }},
    "line_comments": [
        {{
            "file": "path/to/file.py",
            "line": 10,
            "severity": "error|warning|suggestion",
            "comment": "Specific feedback"
        }}
    ],
    "summary": "Overall review summary",
    "requires_changes": false,
    "blocking_issues": ["list", "of", "must-fix", "issues"]
}}
```"""
    
    def _format_patches(self, patches: list[dict]) -> str:
        if not patches:
            return "No patches generated"
        
        parts = []
        for i, patch in enumerate(patches, 1):
            parts.append(f"""
### Patch {i}: {patch.get('file_path', 'unknown')}
**Type:** {patch.get('change_type', 'unknown')}
**Description:** {patch.get('description', '')}

```python
{patch.get('new_code', 'No code')}
```
""")
        return "\n".join(parts)
    
    def _format_tests(self, tests: list[dict]) -> str:
        if not tests:
            return "No tests generated"
        
        parts = []
        for test in tests:
            parts.append(f"""
### {test.get('file_path', 'test.py')}
```python
{test.get('code', 'No test code')[:1500]}
```
""")
        return "\n".join(parts)
    
    def parse_response(self, response_text: str) -> dict[str, Any]:
        parsed = self._extract_json_from_response(response_text)
        
        # Ensure required fields have defaults
        defaults = {
            "overall_verdict": "needs_discussion",
            "overall_score": 50,
            "correctness": {"score": 50, "issues": [], "suggestions": []},
            "code_quality": {"score": 50, "issues": [], "suggestions": []},
            "security": {"score": 50, "vulnerabilities": [], "recommendations": []},
            "style": {"score": 50, "issues": [], "suggestions": []},
            "test_coverage": {"adequate": False, "missing_tests": [], "suggestions": []},
            "line_comments": [],
            "summary": "",
            "requires_changes": True,
            "blocking_issues": [],
        }
        
        for key, default_value in defaults.items():
            if key not in parsed:
                parsed[key] = default_value
        
        parsed["success"] = True
        return parsed
