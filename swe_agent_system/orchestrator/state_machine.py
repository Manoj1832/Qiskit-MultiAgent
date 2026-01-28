"""
State machine for orchestrating agent execution.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Callable


class ExecutionState(Enum):
    """States in the agent execution pipeline."""
    PENDING = auto()
    ANALYZING = auto()       # Issue Intelligence Agent
    ASSESSING = auto()       # Impact Assessment Agent
    PLANNING = auto()        # Planning Agent
    GENERATING = auto()      # Code Generation Agent
    REVIEWING = auto()       # PR Review Agent
    VALIDATING = auto()      # Validation Agent
    COMPLETE = auto()
    FAILED = auto()


@dataclass
class StateTransition:
    """Defines a valid state transition."""
    from_state: ExecutionState
    to_state: ExecutionState
    condition: str | None = None  # Optional condition description
    guard: Callable[['ExecutionContext'], bool] | None = None  # Optional guard function


# Transition guard functions
def has_issue_analysis(context: 'ExecutionContext') -> bool:
    """Check if issue analysis is complete."""
    return bool(context.issue_analysis.get("summary"))


def has_impact_assessment(context: 'ExecutionContext') -> bool:
    """Check if impact assessment is complete."""
    return bool(context.impact_assessment.get("severity"))


def has_execution_plan(context: 'ExecutionContext') -> bool:
    """Check if execution plan is complete."""
    return bool(context.execution_plan.get("plan_summary"))


def has_generated_patches(context: 'ExecutionContext') -> bool:
    """Check if code patches were generated."""
    return bool(context.generated_patch.get("patches"))


def review_passed(context: 'ExecutionContext') -> bool:
    """Check if code review passed."""
    return not context.review_result.get("requires_changes", False)


def validation_passed(context: 'ExecutionContext') -> bool:
    """Check if validation passed."""
    return context.validation_result.get("tests_passed", False) is not False


def retry_code_generation(context: 'ExecutionContext') -> bool:
    """Check if code generation should be retried."""
    return context.retry_count < 3  # Max 3 retries


def token_budget_ok(context: 'ExecutionContext') -> bool:
    """Check if token budget is acceptable."""
    return context.tokens_used < 100000  # 100k token limit


# Valid state transitions with guards
VALID_TRANSITIONS: list[StateTransition] = [
    # Normal flow
    StateTransition(ExecutionState.PENDING, ExecutionState.ANALYZING, guard=token_budget_ok),
    StateTransition(ExecutionState.ANALYZING, ExecutionState.ASSESSING, guard=has_issue_analysis),
    StateTransition(ExecutionState.ASSESSING, ExecutionState.PLANNING, guard=has_impact_assessment),
    StateTransition(ExecutionState.PLANNING, ExecutionState.GENERATING, guard=has_execution_plan),
    StateTransition(ExecutionState.GENERATING, ExecutionState.REVIEWING, guard=has_generated_patches),
    StateTransition(ExecutionState.REVIEWING, ExecutionState.VALIDATING, guard=review_passed),
    StateTransition(ExecutionState.VALIDATING, ExecutionState.COMPLETE, guard=validation_passed),
    
    # Retry/rework flows
    StateTransition(
        ExecutionState.REVIEWING, 
        ExecutionState.GENERATING, 
        "code review failed",
        guard=retry_code_generation
    ),
    StateTransition(
        ExecutionState.VALIDATING, 
        ExecutionState.GENERATING, 
        "tests failed",
        guard=retry_code_generation
    ),
    
    # Failure from any state
    StateTransition(ExecutionState.ANALYZING, ExecutionState.FAILED),
    StateTransition(ExecutionState.ASSESSING, ExecutionState.FAILED),
    StateTransition(ExecutionState.PLANNING, ExecutionState.FAILED),
    StateTransition(ExecutionState.GENERATING, ExecutionState.FAILED),
    StateTransition(ExecutionState.REVIEWING, ExecutionState.FAILED),
    StateTransition(ExecutionState.VALIDATING, ExecutionState.FAILED),
]


@dataclass
class ExecutionContext:
    """Context passed between agents during execution."""
    issue_id: str
    issue_url: str
    repository: str
    
    # Data populated by agents
    issue_analysis: dict[str, Any] = field(default_factory=dict)
    impact_assessment: dict[str, Any] = field(default_factory=dict)
    execution_plan: dict[str, Any] = field(default_factory=dict)
    generated_patch: dict[str, Any] = field(default_factory=dict)
    review_result: dict[str, Any] = field(default_factory=dict)
    validation_result: dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    tokens_used: int = 0
    retry_count: int = 0
    errors: list[str] = field(default_factory=list)


class StateMachine:
    """Manages state transitions for agent execution."""
    
    def __init__(self):
        self.current_state = ExecutionState.PENDING
        self.state_history: list[ExecutionState] = [ExecutionState.PENDING]
        self._build_transition_map()
    
    def _build_transition_map(self) -> None:
        """Build a lookup map for valid transitions."""
        self._transitions: dict[ExecutionState, list[StateTransition]] = {}
        for transition in VALID_TRANSITIONS:
            if transition.from_state not in self._transitions:
                self._transitions[transition.from_state] = []
            self._transitions[transition.from_state].append(transition)
    
    def can_transition_to(self, target_state: ExecutionState, context: ExecutionContext | None = None) -> bool:
        """Check if transition to target state is valid."""
        valid_transitions = self._transitions.get(self.current_state, [])
        
        for transition in valid_transitions:
            if transition.to_state == target_state:
                # Check guard if present and context provided
                if transition.guard and context:
                    return transition.guard(context)
                return True
        
        return False
    
    def transition_to(self, target_state: ExecutionState, context: ExecutionContext | None = None) -> None:
        """Transition to a new state."""
        if not self.can_transition_to(target_state, context):
            guard_failed = context and not self._check_guard_only(target_state, context)
            if guard_failed:
                raise InvalidTransitionError(
                    f"Transition guard failed: {self.current_state.name} to {target_state.name}"
                )
            else:
                raise InvalidTransitionError(
                    f"Cannot transition from {self.current_state.name} to {target_state.name}"
                )
        self.current_state = target_state
        self.state_history.append(target_state)
    
    def _check_guard_only(self, target_state: ExecutionState, context: ExecutionContext) -> bool:
        """Check only the guard condition for a transition."""
        valid_transitions = self._transitions.get(self.current_state, [])
        
        for transition in valid_transitions:
            if transition.to_state == target_state and transition.guard:
                return transition.guard(context)
        
        return True
    
    def reset(self) -> None:
        """Reset state machine to initial state."""
        self.current_state = ExecutionState.PENDING
        self.state_history = [ExecutionState.PENDING]
    
    @property
    def is_terminal(self) -> bool:
        """Check if current state is terminal."""
        return self.current_state in (ExecutionState.COMPLETE, ExecutionState.FAILED)
    
    def get_next_agent(self) -> str | None:
        """Get the agent name for the current state."""
        agent_map = {
            ExecutionState.ANALYZING: "issue_intelligence",
            ExecutionState.ASSESSING: "impact_assessment",
            ExecutionState.PLANNING: "planner",
            ExecutionState.GENERATING: "code_generator",
            ExecutionState.REVIEWING: "pr_reviewer",
            ExecutionState.VALIDATING: "validator",
        }
        return agent_map.get(self.current_state)


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass
