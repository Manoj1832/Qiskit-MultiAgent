"""
Observability module for structured logging.
"""

import os
import structlog
from typing import Any


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured logging for the system."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(indent=2),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class AgentLogger:
    """Logger wrapper specifically for agent execution tracing."""
    
    def __init__(self, agent_name: str):
        self.logger = get_logger(f"agent.{agent_name}")
        self.agent_name = agent_name
    
    def log_prompt(self, prompt: str, context: dict[str, Any] | None = None) -> None:
        """Log an outgoing prompt to the LLM."""
        self.logger.info(
            "prompt_sent",
            agent=self.agent_name,
            prompt_length=len(prompt),
            context=context or {},
        )
    
    def log_response(self, response: str, tokens_used: int = 0) -> None:
        """Log a response from the LLM."""
        self.logger.info(
            "response_received",
            agent=self.agent_name,
            response_length=len(response),
            tokens_used=tokens_used,
        )
    
    def log_error(self, error: Exception, context: dict[str, Any] | None = None) -> None:
        """Log an error during agent execution."""
        self.logger.error(
            "agent_error",
            agent=self.agent_name,
            error_type=type(error).__name__,
            error_message=str(error),
            context=context or {},
        )
    
    def log_decision(self, decision: str, reasoning: str) -> None:
        """Log a decision made by the agent."""
        self.logger.info(
            "decision_made",
            agent=self.agent_name,
            decision=decision,
            reasoning=reasoning,
        )
