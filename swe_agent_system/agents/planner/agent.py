"""
Planner Agent - Step-by-step solution planning.
"""

from typing import Any

from ..base_agent import BaseAgent, AgentConfig
from ...orchestrator.state_machine import ExecutionContext


class PlannerAgent(BaseAgent):
    """
    Agent responsible for creating a detailed fix plan.
    
    Capabilities:
    - Analyze affected files and components
    - Create step-by-step fix plan
    - Identify test requirements
    - Assess risk of proposed changes
    """
    
    def __init__(self, model: str = "gemini-2.5-flash"):
        config = AgentConfig(
            name="planner",
            model=model,
            temperature=0.3,
            max_output_tokens=8192,
        )
        super().__init__(config)
    
    def get_system_prompt(self) -> str:
        return """You are a senior software architect specializing in planning fixes for complex open-source projects.

Your task is to create a detailed, actionable plan for fixing a GitHub issue.

Your plans should be:
- Specific and actionable
- Low-risk and minimal
- Well-scoped with clear boundaries
- Testable

Always respond with a valid JSON object containing your plan."""
    
    def build_prompt(self, context: ExecutionContext) -> str:
        issue_analysis = context.issue_analysis
        impact = context.impact_assessment
        
        return f"""Create a detailed fix plan for the following issue:

## Issue Analysis
**Type:** {issue_analysis.get('issue_type', 'unknown')}
**Summary:** {issue_analysis.get('summary', 'No summary')}

**Affected Components:**
{', '.join(issue_analysis.get('affected_components', []))}

**Potential Root Causes:**
{chr(10).join('- ' + c for c in issue_analysis.get('potential_root_causes', []))}

**Related Keywords for Code Search:**
{', '.join(issue_analysis.get('related_keywords', []))}

## Impact Assessment
**Technical Severity:** {impact.get('technical_severity', 'unknown')}
**Fix Complexity:** {impact.get('estimated_fix_complexity', 'unknown')}
**Risk Factors:**
{chr(10).join('- ' + r for r in impact.get('risk_factors', []))}

**Repository:** {context.repository}

---

Provide your fix plan as a JSON object:
```json
{{
    "plan_summary": "Brief overview of the fix approach",
    "files_to_modify": [
        {{
            "path": "path/to/file.py",
            "change_type": "modify|create|delete",
            "description": "What changes are needed",
            "estimated_lines": 10
        }}
    ],
    "implementation_steps": [
        {{
            "step_number": 1,
            "description": "Detailed step description",
            "files_involved": ["file1.py"],
            "expected_outcome": "What this step achieves"
        }}
    ],
    "test_requirements": [
        {{
            "test_type": "unit|integration|regression",
            "description": "What needs to be tested",
            "test_file": "test_file.py"
        }}
    ],
    "risk_assessment": {{
        "overall_risk": "low|medium|high",
        "breaking_changes": false,
        "backward_compatibility": true,
        "risks": ["list", "of", "specific", "risks"]
    }},
    "dependencies": ["any", "required", "changes", "first"],
    "rollback_strategy": "How to revert if something goes wrong",
    "estimated_effort_hours": 4,
    "confidence_score": 0.85
}}
```"""
    
    def parse_response(self, response_text: str) -> dict[str, Any]:
        parsed = self._extract_json_from_response(response_text)
        
        # Ensure required fields have defaults
        defaults = {
            "plan_summary": "",
            "files_to_modify": [],
            "implementation_steps": [],
            "test_requirements": [],
            "risk_assessment": {
                "overall_risk": "medium",
                "breaking_changes": False,
                "backward_compatibility": True,
                "risks": [],
            },
            "dependencies": [],
            "rollback_strategy": "",
            "estimated_effort_hours": 8,
            "confidence_score": 0.5,
        }
        
        for key, default_value in defaults.items():
            if key not in parsed:
                parsed[key] = default_value
        
        parsed["success"] = True
        return parsed
