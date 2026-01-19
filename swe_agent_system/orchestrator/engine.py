"""
Main orchestration engine for coordinating agent execution.
"""

import time
from typing import Any
from pathlib import Path

from .state_machine import StateMachine, ExecutionState, ExecutionContext, InvalidTransitionError
from .policies import PolicyManager, RetryPolicy, BudgetPolicy
from ..observability import get_logger, AgentLogger, ExecutionTracer


class Orchestrator:
    """
    Main orchestration engine that coordinates agent execution.
    
    Responsibilities:
    - Enforce agent execution order
    - Maintain execution state
    - Control retries and fallbacks
    - Manage context flow between agents
    - Enforce token and cost budgets
    """
    
    def __init__(
        self,
        agents: dict[str, Any],
        policy_manager: PolicyManager | None = None,
        tracer: ExecutionTracer | None = None,
    ):
        self.agents = agents
        self.policy_manager = policy_manager or PolicyManager()
        self.tracer = tracer or ExecutionTracer()
        self.state_machine = StateMachine()
        self.logger = get_logger("orchestrator")
        
        # Execution metrics
        self.total_tokens_used = 0
        self.total_cost = 0.0
    
    async def process_issue(self, issue_url: str, repository: str) -> ExecutionContext:
        """
        Process a GitHub issue through the full agent pipeline.
        
        Args:
            issue_url: URL of the GitHub issue
            repository: Repository in format "owner/repo"
            
        Returns:
            ExecutionContext with all agent outputs
        """
        # Extract issue ID from URL
        issue_id = issue_url.split("/")[-1]
        
        # Initialize context
        context = ExecutionContext(
            issue_id=issue_id,
            issue_url=issue_url,
            repository=repository,
        )
        
        # Start tracing
        self.tracer.start_trace(issue_id)
        self.tracer.add_event("execution_started", {"issue_url": issue_url})
        
        self.logger.info(
            "Starting issue processing",
            issue_id=issue_id,
            repository=repository,
        )
        
        try:
            # Transition to first state
            self.state_machine.transition_to(ExecutionState.ANALYZING)
            
            # Execute agent pipeline
            while not self.state_machine.is_terminal:
                agent_name = self.state_machine.get_next_agent()
                
                if agent_name and agent_name in self.agents:
                    context = await self._execute_agent(agent_name, context)
                    
                    # Move to next state
                    self._advance_state(context)
                else:
                    self.logger.error("Agent not found", agent_name=agent_name)
                    self.state_machine.transition_to(ExecutionState.FAILED)
            
            # Record completion
            status = "success" if self.state_machine.current_state == ExecutionState.COMPLETE else "failed"
            self.tracer.complete_trace(status)
            
            return context
            
        except Exception as e:
            self.logger.error("Execution failed", error=str(e))
            context.errors.append(str(e))
            self.tracer.add_event("execution_failed", {"error": str(e)})
            self.tracer.complete_trace("failed")
            self.state_machine.transition_to(ExecutionState.FAILED)
            return context
    
    async def _execute_agent(self, agent_name: str, context: ExecutionContext) -> ExecutionContext:
        """Execute a single agent with retry logic."""
        agent = self.agents[agent_name]
        agent_logger = AgentLogger(agent_name)
        
        start_time = time.time()
        attempt = 0
        last_error: Exception | None = None
        
        while attempt <= self.policy_manager.retry.max_retries:
            try:
                # Check budget before execution
                if not self.policy_manager.budget.check_token_budget(
                    context.tokens_used,
                    self.policy_manager.budget.max_tokens_per_agent
                ):
                    raise BudgetExceededError("Token budget exceeded")
                
                # Execute agent
                self.tracer.add_event(
                    "agent_started",
                    {"attempt": attempt},
                    agent=agent_name,
                )
                
                result = await agent.execute(context)
                
                # Update context based on agent
                context = self._update_context(agent_name, context, result)
                
                duration_ms = (time.time() - start_time) * 1000
                self.tracer.add_event(
                    "agent_completed",
                    {"result": "success"},
                    agent=agent_name,
                    duration_ms=duration_ms,
                )
                
                agent_logger.log_response(str(result), result.get("tokens_used", 0))
                return context
                
            except Exception as e:
                last_error = e
                agent_logger.log_error(e, {"attempt": attempt})
                
                if not self.policy_manager.retry.should_retry(attempt, e):
                    break
                
                # Check if it's a rate limit error and use appropriate delay
                is_rate_limit = self.policy_manager.retry.is_rate_limit_error(e)
                delay = self.policy_manager.retry.get_delay(attempt, is_rate_limit=is_rate_limit)
                
                if is_rate_limit:
                    self.logger.info(
                        f"Rate limit hit, waiting {delay}s before retry",
                        agent=agent_name,
                        attempt=attempt,
                    )
                
                time.sleep(delay)
                attempt += 1
                context.retry_count += 1
        
        # All retries failed
        context.errors.append(f"{agent_name}: {str(last_error)}")
        raise AgentExecutionError(f"Agent {agent_name} failed after {attempt} attempts: {last_error}")
    
    def _update_context(
        self,
        agent_name: str,
        context: ExecutionContext,
        result: dict[str, Any],
    ) -> ExecutionContext:
        """Update context with agent output."""
        context_mapping = {
            "issue_intelligence": "issue_analysis",
            "impact_assessment": "impact_assessment",
            "planner": "execution_plan",
            "code_generator": "generated_patch",
            "pr_reviewer": "review_result",
            "validator": "validation_result",
        }
        
        field_name = context_mapping.get(agent_name)
        if field_name:
            setattr(context, field_name, result)
        
        # Update token count
        context.tokens_used += result.get("tokens_used", 0)
        
        return context
    
    def _advance_state(self, context: ExecutionContext) -> None:
        """Advance the state machine based on current state and context."""
        current = self.state_machine.current_state
        
        # Define next state based on current state
        next_state_map = {
            ExecutionState.ANALYZING: ExecutionState.ASSESSING,
            ExecutionState.ASSESSING: ExecutionState.PLANNING,
            ExecutionState.PLANNING: ExecutionState.GENERATING,
            ExecutionState.GENERATING: ExecutionState.REVIEWING,
            ExecutionState.REVIEWING: ExecutionState.VALIDATING,
            ExecutionState.VALIDATING: ExecutionState.COMPLETE,
        }
        
        # Check for rework conditions
        if current == ExecutionState.REVIEWING:
            review = context.review_result
            if review.get("requires_changes", False):
                self.state_machine.transition_to(ExecutionState.GENERATING)
                return
        
        if current == ExecutionState.VALIDATING:
            validation = context.validation_result
            if validation.get("tests_passed", False) is False:
                self.state_machine.transition_to(ExecutionState.GENERATING)
                return
        
        # Normal progression
        next_state = next_state_map.get(current)
        if next_state:
            self.state_machine.transition_to(next_state)


class AgentExecutionError(Exception):
    """Raised when an agent fails to execute."""
    pass


class BudgetExceededError(Exception):
    """Raised when token or cost budget is exceeded."""
    pass
