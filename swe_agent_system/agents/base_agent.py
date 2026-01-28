"""
Base agent class for all AI agents in the system.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import anthropic
from pydantic import BaseModel

from ..observability import AgentLogger
from ..orchestrator.state_machine import ExecutionContext


class AgentError(Exception):
    """Base exception for agent-related errors."""
    pass


class APIError(AgentError):
    """Raised when API calls fail."""
    def __init__(self, message: str, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message, retryable=True)
        self.retry_after = retry_after


class AuthenticationError(APIError):
    """Raised when API authentication fails."""
    def __init__(self, message: str):
        super().__init__(message, retryable=False)


class ContentFilterError(APIError):
    """Raised when content is filtered by API."""
    def __init__(self, message: str):
        super().__init__(message, retryable=False)


class TokenLimitError(AgentError):
    """Raised when token limits are exceeded."""
    pass


class ResponseParsingError(AgentError):
    """Raised when agent response cannot be parsed."""
    pass


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    model: str = "claude-sonnet-4-20250514"
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
    - Uses Anthropic Claude for reasoning
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
        
        # Configure Anthropic - client reads ANTHROPIC_API_KEY from environment
        self.client = anthropic.Anthropic()
        self.model_name = config.model
    
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
            
            self.logger.log_prompt(user_prompt, {"issue_id": context.issue_id})
            
            # Call Anthropic API
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=self.config.max_output_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            )
            
            response_text = response.content[0].text
            if not response_text:
                raise ResponseParsingError("Empty response from API")
            
            tokens_used = self._extract_token_usage(response)
            
            self.logger.log_response(response_text, tokens_used)
            
            # Parse response
            parsed = self.parse_response(response_text)
            parsed["tokens_used"] = tokens_used
            parsed["raw_response"] = response_text
            parsed["success"] = True
            
            return parsed
            
        except ResponseParsingError as e:
            self.logger.log_error(e, {"context": context.issue_id, "error_type": "parsing"})
            return {
                "success": False,
                "error": str(e),
                "tokens_used": 0,
                "retryable": True,  # Parsing errors might be resolved with retry
            }
            
        except Exception as e:
            # Handle API-related errors specifically
            if "anthropic" in str(type(e)).lower() or "API" in str(type(e)):
                error = self._handle_api_error(e)
                self.logger.log_error(error, {"context": context.issue_id, "error_type": type(error).__name__})
                return {
                    "success": False,
                    "error": str(error),
                    "tokens_used": 0,
                    "retryable": getattr(error, "retryable", False),
                }
            else:
                self.logger.log_error(e, {"context": context.issue_id, "error_type": "unexpected"})
                return {
                    "success": False,
                    "error": str(e),
                    "tokens_used": 0,
                    "retryable": False,
                }
    
    def _extract_token_usage(self, response) -> int:
        """
        Extract token usage from API response with robust fallbacks.
        
        Args:
            response: API response object
            
        Returns:
            Number of tokens used
        """
        # Primary method: usage object
        if hasattr(response, "usage") and response.usage:
            input_tokens = getattr(response.usage, "input_tokens", 0)
            output_tokens = getattr(response.usage, "output_tokens", 0)
            return input_tokens + output_tokens
        
        # Fallback: estimate from response length
        if hasattr(response, "content") and response.content:
            text = response.content[0].text if response.content else ""
            if text:
                # Rough estimation: ~4 characters per token
                estimated_tokens = len(text) // 4
                return max(estimated_tokens, 1)
        
        return 0
    
    def _handle_api_error(self, error: Exception) -> AgentError:
        """
        Convert API errors to specific agent exceptions.
        
        Args:
            error: Original API error
            
        Returns:
            Specific agent error
        """
        error_message = str(error)
        status_code = getattr(error, "status_code", None)
        
        # Rate limit errors
        if "rate limit" in error_message.lower() or "quota" in error_message.lower():
            retry_after = None
            if hasattr(error, "retry_after"):
                retry_after = error.retry_after
            return RateLimitError(error_message, retry_after)
        
        # Authentication errors
        if any(keyword in error_message.lower() for keyword in ["auth", "unauthorized", "forbidden", "invalid_api_key"]):
            return AuthenticationError(error_message)
        
        # Content filter errors
        if any(keyword in error_message.lower() for keyword in ["content filter", "safety", "blocked"]):
            return ContentFilterError(error_message)
        
        # Token limit errors
        if any(keyword in error_message.lower() for keyword in ["token limit", "too long", "max length"]):
            return TokenLimitError(error_message)
        
        # Generic API error
        retryable = status_code is None or status_code >= 500  # Retry server errors
        return APIError(error_message, status_code, retryable)
    
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
