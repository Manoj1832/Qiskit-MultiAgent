"""
Policies for controlling agent execution behavior.
"""

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class RetryPolicy:
    """Policy for controlling retry behavior."""
    max_retries: int = 3
    initial_delay_seconds: float = 5.0  # Increased from 1.0
    max_delay_seconds: float = 120.0    # Increased from 30.0 for rate limits
    exponential_base: float = 2.0
    rate_limit_delay_seconds: float = 60.0  # Wait 60s on rate limit
    
    def get_delay(self, attempt: int, is_rate_limit: bool = False) -> float:
        """Calculate delay for a given retry attempt (0-indexed)."""
        if is_rate_limit:
            # For rate limits, wait longer
            return self.rate_limit_delay_seconds * (attempt + 1)
        delay = self.initial_delay_seconds * (self.exponential_base ** attempt)
        return min(delay, self.max_delay_seconds)
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if we should retry after an error."""
        # Don't retry if we've exceeded max retries
        if attempt >= self.max_retries:
            return False
        
        error_str = str(error).lower()
        
        # Check for rate limit / quota errors - should retry with delay
        if "429" in error_str or "resource_exhausted" in error_str or "rate limit" in error_str:
            return True
        
        # Define retryable error types
        retryable_errors = (
            ConnectionError,
            TimeoutError,
        )
        
        return isinstance(error, retryable_errors)
    
    def is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit error."""
        error_str = str(error).lower()
        return "429" in error_str or "resource_exhausted" in error_str or "rate limit" in error_str


@dataclass
class BudgetPolicy:
    """Policy for controlling token and cost budgets."""
    max_tokens_per_issue: int = 100000
    max_cost_per_issue_usd: float = 5.0
    max_tokens_per_agent: int = 25000
    
    # Approximate OpenAI pricing (per 1K tokens)
    input_cost_per_1k: float = 0.00015  # GPT-4o-mini
    output_cost_per_1k: float = 0.0006
    
    def check_token_budget(self, current_tokens: int, requested_tokens: int) -> bool:
        """Check if token budget allows for more tokens."""
        return (current_tokens + requested_tokens) <= self.max_tokens_per_issue
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a given number of tokens."""
        input_cost = (input_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost
    
    def check_cost_budget(self, current_cost: float, estimated_additional: float) -> bool:
        """Check if cost budget allows for additional spending."""
        return (current_cost + estimated_additional) <= self.max_cost_per_issue_usd


@dataclass
class TimeoutPolicy:
    """Policy for controlling execution timeouts."""
    agent_execution_seconds: int = 300
    github_api_seconds: int = 30
    test_runner_seconds: int = 600
    total_issue_seconds: int = 3600
    
    def get_timeout(self, operation: str) -> int:
        """Get timeout for a specific operation type."""
        timeouts = {
            "agent": self.agent_execution_seconds,
            "github": self.github_api_seconds,
            "test": self.test_runner_seconds,
            "total": self.total_issue_seconds,
        }
        return timeouts.get(operation, self.agent_execution_seconds)


@dataclass
class SecurityPolicy:
    """Policy for security and access control."""
    github_read_only: bool = True
    allow_code_execution: bool = False
    sanitize_prompts: bool = True
    validate_outputs: bool = True
    allowed_file_extensions: tuple[str, ...] = (".py", ".md", ".txt", ".yaml", ".yml", ".json")
    
    def is_file_allowed(self, filename: str) -> bool:
        """Check if a file type is allowed for modification."""
        return any(filename.endswith(ext) for ext in self.allowed_file_extensions)
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize input text to prevent prompt injection."""
        if not self.sanitize_prompts:
            return text
        
        # Basic sanitization - remove potential injection patterns
        dangerous_patterns = [
            "ignore previous instructions",
            "disregard above",
            "system prompt",
        ]
        
        sanitized = text
        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern, "[FILTERED]")
        
        return sanitized


class PolicyManager:
    """Manages all policies for the system."""
    
    def __init__(
        self,
        retry: RetryPolicy | None = None,
        budget: BudgetPolicy | None = None,
        timeout: TimeoutPolicy | None = None,
        security: SecurityPolicy | None = None,
    ):
        self.retry = retry or RetryPolicy()
        self.budget = budget or BudgetPolicy()
        self.timeout = timeout or TimeoutPolicy()
        self.security = security or SecurityPolicy()
    
    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "PolicyManager":
        """Create PolicyManager from configuration dictionary."""
        retry_config = config.get("retry", {})
        budget_config = config.get("budgets", {})
        timeout_config = config.get("timeouts", {})
        security_config = config.get("security", {})
        
        return cls(
            retry=RetryPolicy(**retry_config) if retry_config else None,
            budget=BudgetPolicy(**budget_config) if budget_config else None,
            timeout=TimeoutPolicy(**timeout_config) if timeout_config else None,
            security=SecurityPolicy(**security_config) if security_config else None,
        )
