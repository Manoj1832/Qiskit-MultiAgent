"""
State machine for orchestrating agent execution.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any


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


# Valid state transitions
VALID_TRANSITIONS: list[StateTransition] = [
    # Normal flow
    StateTransition(ExecutionState.PENDING, ExecutionState.ANALYZING),
    StateTransition(ExecutionState.ANALYZING, ExecutionState.ASSESSING),
    StateTransition(ExecutionState.ASSESSING, ExecutionState.PLANNING),
    StateTransition(ExecutionState.PLANNING, ExecutionState.GENERATING),
    StateTransition(ExecutionState.GENERATING, ExecutionState.REVIEWING),
    StateTransition(ExecutionState.REVIEWING, ExecutionState.VALIDATING),
    StateTransition(ExecutionState.VALIDATING, ExecutionState.COMPLETE),
    
    # Retry/rework flows
    StateTransition(ExecutionState.REVIEWING, ExecutionState.GENERATING, "code review failed"),
    StateTransition(ExecutionState.VALIDATING, ExecutionState.GENERATING, "tests failed"),
    
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
        self._transitions: dict[ExecutionState, list[ExecutionState]] = {}
        for transition in VALID_TRANSITIONS:
            if transition.from_state not in self._transitions:
                self._transitions[transition.from_state] = []
            self._transitions[transition.from_state].append(transition.to_state)
    
    def can_transition_to(self, target_state: ExecutionState) -> bool:
        """Check if transition to target state is valid."""
        valid_targets = self._transitions.get(self.current_state, [])
        return target_state in valid_targets
    
    def transition_to(self, target_state: ExecutionState) -> None:
        """Transition to a new state."""
        if not self.can_transition_to(target_state):
            raise InvalidTransitionError(
                f"Cannot transition from {self.current_state.name} to {target_state.name}"
            )
        self.current_state = target_state
        self.state_history.append(target_state)
    
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
