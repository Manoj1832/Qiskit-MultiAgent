"""
Base agent class for all AI agents in the system.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from ..observability import AgentLogger
from ..orchestrator.state_machine import ExecutionContext


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    model: str = "gemini-2.5-flash"
    temperature: float = 0.2
    max_output_tokens: int = 8192
    system_prompt: str = ""


class AgentResponse(BaseModel):
    """Structured response from an agent."""
    success: bool
    data: dict[str, Any]
    tokens_used: int = 0
    error: str | None = None


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    
    Each agent is:
    - Stateless and prompt-driven
    - Uses Google Gemini for reasoning
    - Returns structured outputs
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize the agent.
        
        Args:
            config: Agent configuration
        """
        self.config = config
        self.logger = AgentLogger(config.name)
        
        # Configure Gemini - client reads GEMINI_API_KEY from environment
        self.client = genai.Client()
        self.model_name = config.model
        self.generation_config = types.GenerateContentConfig(
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
        )
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass
    
    @abstractmethod
    def build_prompt(self, context: ExecutionContext) -> str:
        """Build the prompt for the LLM based on context."""
        pass
    
    @abstractmethod
    def parse_response(self, response_text: str) -> dict[str, Any]:
        """Parse the LLM response into structured data."""
        pass
    
    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        """
        Execute the agent's task.
        
        Args:
            context: Execution context with issue data
            
        Returns:
            Dictionary with agent output and metadata
        """
        try:
            # Build prompt
            system_prompt = self.get_system_prompt()
            user_prompt = self.build_prompt(context)
            
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            self.logger.log_prompt(full_prompt, {"issue_id": context.issue_id})
            
            # Call Gemini using new API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=self.generation_config,
            )
            
            response_text = response.text
            tokens_used = 0
            
            # Try to get token count if available
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_used = getattr(response.usage_metadata, "total_token_count", 0)
            
            self.logger.log_response(response_text, tokens_used)
            
            # Parse response
            parsed = self.parse_response(response_text)
            parsed["tokens_used"] = tokens_used
            parsed["raw_response"] = response_text
            
            return parsed
            
        except Exception as e:
            self.logger.log_error(e, {"context": context.issue_id})
            return {
                "success": False,
                "error": str(e),
                "tokens_used": 0,
            }
    
    def _extract_json_from_response(self, text: str) -> dict[str, Any]:
        """
        Extract JSON from a response that may contain markdown code blocks.
        
        Args:
            text: Raw response text
            
        Returns:
            Parsed JSON dictionary
        """
        import json
        import re
        
        # Try to find JSON in code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try parsing the entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Return as raw text
        return {"raw_text": text}
