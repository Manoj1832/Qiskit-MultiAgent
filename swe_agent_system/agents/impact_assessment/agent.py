"""
Impact Assessment Agent - Technical and business severity analysis.
"""

from typing import Any

from ..base_agent import BaseAgent, AgentConfig
from ...orchestrator.state_machine import ExecutionContext


class ImpactAssessmentAgent(BaseAgent):
    """
    Agent responsible for assessing the impact of an issue.
    
    Capabilities:
    - Evaluate technical severity
    - Assess business impact
    - Identify affected user segments
    - Estimate fix complexity
    """
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        config = AgentConfig(
            name="impact_assessment",
            model=model,
            temperature=0.2,
            max_output_tokens=4096,
        )
        super().__init__(config)
    
    def get_system_prompt(self) -> str:
        return """You are a senior software engineer and technical program manager specializing in issue triage and impact assessment for enterprise software projects.

Your task is to assess the technical and business impact of a GitHub issue based on the provided analysis.

Consider factors like:
- How many users are affected
- Whether it's a regression
- Security implications
- Performance impact
- API stability concerns

Always respond with a valid JSON object containing your assessment."""
    
    def build_prompt(self, context: ExecutionContext) -> str:
        issue_analysis = context.issue_analysis
        
        return f"""Based on the following issue analysis, assess the impact:

## Issue Summary
**Type:** {issue_analysis.get('issue_type', 'unknown')}
**Severity (initial):** {issue_analysis.get('severity', 'unknown')}
**Summary:** {issue_analysis.get('summary', 'No summary')}

**Affected Components:**
{', '.join(issue_analysis.get('affected_components', []))}

**Key Symptoms:**
{chr(10).join('- ' + s for s in issue_analysis.get('key_symptoms', []))}

**Potential Root Causes:**
{chr(10).join('- ' + c for c in issue_analysis.get('potential_root_causes', []))}

**Repository:** {context.repository}

---

Provide your impact assessment as a JSON object:
```json
{{
    "technical_severity": "critical|high|medium|low",
    "business_impact": "critical|high|medium|low",
    "user_impact_scope": "all_users|most_users|some_users|few_users",
    "is_regression": true|false,
    "is_security_related": true|false,
    "is_performance_related": true|false,
    "breaking_change_risk": "high|medium|low|none",
    "estimated_fix_complexity": "trivial|simple|moderate|complex|very_complex",
    "estimated_hours": 4,
    "priority_score": 85,
    "affected_apis": ["list", "of", "public", "apis"],
    "risk_factors": ["list", "of", "risks"],
    "mitigation_suggestions": ["temporary", "workarounds"],
    "recommended_action": "immediate_fix|scheduled_fix|needs_investigation|wont_fix",
    "justification": "Brief explanation of the assessment"
}}
```"""
    
    def parse_response(self, response_text: str) -> dict[str, Any]:
        parsed = self._extract_json_from_response(response_text)
        
        # Ensure required fields have defaults
        defaults = {
            "technical_severity": "medium",
            "business_impact": "medium",
            "user_impact_scope": "some_users",
            "is_regression": False,
            "is_security_related": False,
            "is_performance_related": False,
            "breaking_change_risk": "low",
            "estimated_fix_complexity": "moderate",
            "estimated_hours": 8,
            "priority_score": 50,
            "affected_apis": [],
            "risk_factors": [],
            "mitigation_suggestions": [],
            "recommended_action": "scheduled_fix",
            "justification": "",
        }
        
        for key, default_value in defaults.items():
            if key not in parsed:
                parsed[key] = default_value
        
        parsed["success"] = True
        return parsed
