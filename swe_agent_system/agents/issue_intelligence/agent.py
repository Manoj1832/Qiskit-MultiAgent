"""
Issue Intelligence Agent - Semantic understanding of GitHub issues.
"""

from typing import Any

from ..base_agent import BaseAgent, AgentConfig
from ...orchestrator.state_machine import ExecutionContext


class IssueIntelligenceAgent(BaseAgent):
    """
    Agent responsible for semantic understanding of GitHub issues.
    
    Capabilities:
    - Classify issue type (bug, feature, enhancement, question)
    - Extract key information (affected components, error messages, steps to reproduce)
    - Summarize the issue in technical terms
    """
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        config = AgentConfig(
            name="issue_intelligence",
            model=model,
            temperature=0.1,  # Low temperature for consistent classification
            max_output_tokens=4096,
        )
        super().__init__(config)
    
    def get_system_prompt(self) -> str:
        return """You are an expert software engineering analyst specializing in analyzing GitHub issues for large open-source projects.

Your task is to analyze a GitHub issue and extract structured information that will help other agents understand and fix the problem.

Always respond with a valid JSON object containing your analysis.

Be precise, technical, and thorough in your analysis."""
    
    def build_prompt(self, context: ExecutionContext) -> str:
        issue_data = context.issue_analysis.get("raw_issue", {})
        
        return f"""Analyze the following GitHub issue from the {context.repository} repository:

## Issue #{issue_data.get('number', context.issue_id)}
**Title:** {issue_data.get('title', 'Unknown')}

**Body:**
{issue_data.get('body', 'No description provided')}

**Labels:** {', '.join(issue_data.get('labels', []))}

**Comments:**
{self._format_comments(issue_data.get('comments', []))}

---

Provide your analysis as a JSON object with the following structure:
```json
{{
    "issue_type": "bug|feature|enhancement|question|documentation",
    "severity": "critical|high|medium|low",
    "summary": "A concise technical summary of the issue",
    "affected_components": ["list", "of", "affected", "modules"],
    "key_symptoms": ["list", "of", "observed", "symptoms"],
    "error_messages": ["any", "error", "messages", "mentioned"],
    "steps_to_reproduce": ["step1", "step2"],
    "expected_behavior": "What the user expects",
    "actual_behavior": "What actually happens",
    "potential_root_causes": ["possible", "causes"],
    "related_keywords": ["keywords", "for", "code", "search"],
    "confidence_score": 0.85
}}
```"""
    
    def _format_comments(self, comments: list[str]) -> str:
        if not comments:
            return "No comments"
        
        formatted = []
        for i, comment in enumerate(comments[:5], 1):  # Limit to first 5 comments
            formatted.append(f"Comment {i}:\n{comment[:500]}")  # Truncate long comments
        
        return "\n\n".join(formatted)
    
    def parse_response(self, response_text: str) -> dict[str, Any]:
        parsed = self._extract_json_from_response(response_text)
        
        # Ensure required fields have defaults
        defaults = {
            "issue_type": "unknown",
            "severity": "medium",
            "summary": "",
            "affected_components": [],
            "key_symptoms": [],
            "error_messages": [],
            "steps_to_reproduce": [],
            "expected_behavior": "",
            "actual_behavior": "",
            "potential_root_causes": [],
            "related_keywords": [],
            "confidence_score": 0.5,
        }
        
        for key, default_value in defaults.items():
            if key not in parsed:
                parsed[key] = default_value
        
        parsed["success"] = True
        return parsed
