"""
Code Generator Agent - Patch and test creation.
"""

from typing import Any

from ..base_agent import BaseAgent, AgentConfig
from ...orchestrator.state_machine import ExecutionContext


class CodeGeneratorAgent(BaseAgent):
    """
    Agent responsible for generating code patches and tests.
    
    Capabilities:
    - Generate production-quality code patches
    - Create unit tests for changes
    - Follow project coding conventions
    - Produce minimal, focused changes
    """
    
    def __init__(self, model: str = "gemini-2.5-flash"):
        config = AgentConfig(
            name="code_generator",
            model=model,
            temperature=0.2,  # Lower temperature for consistent code
            max_output_tokens=16384,  # Larger for code generation
        )
        super().__init__(config)
    
    def get_system_prompt(self) -> str:
        return """You are an expert software engineer specializing in writing production-quality Python code.

Your task is to generate code patches to fix GitHub issues based on a detailed plan.

Your code should:
- Follow Python best practices and PEP8
- Be minimal and focused on the specific fix
- Include appropriate type hints
- Handle edge cases
- Be well-documented with docstrings

Always respond with a valid JSON object containing the patches."""
    
    def build_prompt(self, context: ExecutionContext) -> str:
        issue_analysis = context.issue_analysis
        plan = context.execution_plan
        
        # Get file contents if available (would be populated by repo intelligence)
        file_contexts = plan.get("file_contexts", {})
        
        return f"""Generate code patches based on the following plan:

## Issue Summary
{issue_analysis.get('summary', 'No summary')}

## Fix Plan
**Summary:** {plan.get('plan_summary', 'No plan summary')}

**Files to Modify:**
{self._format_files_to_modify(plan.get('files_to_modify', []))}

**Implementation Steps:**
{self._format_implementation_steps(plan.get('implementation_steps', []))}

## File Contexts
{self._format_file_contexts(file_contexts)}

---

Provide your patches as a JSON object:
```json
{{
    "patches": [
        {{
            "file_path": "path/to/file.py",
            "change_type": "modify|create|delete",
            "description": "What this patch does",
            "original_code": "The original code being replaced (for modify)",
            "new_code": "The new code to insert/replace",
            "line_start": 10,
            "line_end": 20
        }}
    ],
    "test_code": [
        {{
            "file_path": "tests/test_fix.py",
            "description": "Tests for the fix",
            "code": "Full test file content"
        }}
    ],
    "imports_added": ["list", "of", "new", "imports"],
    "summary": "Overall summary of changes made",
    "confidence_score": 0.85
}}
```

IMPORTANT: Generate complete, working code. Do not use placeholders or TODOs."""
    
    def _format_files_to_modify(self, files: list[dict]) -> str:
        if not files:
            return "No files specified"
        
        lines = []
        for f in files:
            lines.append(f"- {f.get('path', 'unknown')}: {f.get('description', '')}")
        return "\n".join(lines)
    
    def _format_implementation_steps(self, steps: list[dict]) -> str:
        if not steps:
            return "No steps specified"
        
        lines = []
        for step in steps:
            num = step.get("step_number", "?")
            desc = step.get("description", "")
            lines.append(f"{num}. {desc}")
        return "\n".join(lines)
    
    def _format_file_contexts(self, contexts: dict[str, str]) -> str:
        if not contexts:
            return "No file contexts available"
        
        parts = []
        for path, content in contexts.items():
            parts.append(f"### {path}\n```python\n{content[:2000]}\n```")
        return "\n\n".join(parts)
    
    def parse_response(self, response_text: str) -> dict[str, Any]:
        parsed = self._extract_json_from_response(response_text)
        
        # Ensure required fields have defaults
        defaults = {
            "patches": [],
            "test_code": [],
            "imports_added": [],
            "summary": "",
            "confidence_score": 0.5,
        }
        
        for key, default_value in defaults.items():
            if key not in parsed:
                parsed[key] = default_value
        
        parsed["success"] = len(parsed.get("patches", [])) > 0
        return parsed
