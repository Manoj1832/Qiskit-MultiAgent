"""Tests for the orchestrator state machine."""

import pytest
from swe_agent_system.orchestrator.state_machine import (
    StateMachine,
    ExecutionState,
    ExecutionContext,
    InvalidTransitionError,
)


class TestExecutionState:
    """Tests for ExecutionState enum."""
    
    def test_all_states_exist(self):
        """Verify all expected states are defined."""
        expected_states = [
            "PENDING", "ANALYZING", "ASSESSING", "PLANNING",
            "GENERATING", "REVIEWING", "VALIDATING", "COMPLETE", "FAILED"
        ]
        for state_name in expected_states:
            assert hasattr(ExecutionState, state_name)
    
    def test_terminal_states(self):
        """Verify terminal states are correctly identified."""
        terminal = [ExecutionState.COMPLETE, ExecutionState.FAILED]
        non_terminal = [
            ExecutionState.PENDING, ExecutionState.ANALYZING,
            ExecutionState.ASSESSING, ExecutionState.PLANNING,
            ExecutionState.GENERATING, ExecutionState.REVIEWING,
            ExecutionState.VALIDATING,
        ]
        
        sm = StateMachine()
        for state in terminal:
            sm.current_state = state
            assert sm.is_terminal
        
        for state in non_terminal:
            sm.current_state = state
            assert not sm.is_terminal


class TestStateMachine:
    """Tests for StateMachine class."""
    
    def test_initial_state(self):
        """State machine starts in PENDING state."""
        sm = StateMachine()
        assert sm.current_state == ExecutionState.PENDING
    
    def test_valid_transition(self):
        """Valid transitions should succeed."""
        sm = StateMachine()
        sm.transition_to(ExecutionState.ANALYZING)
        assert sm.current_state == ExecutionState.ANALYZING
    
    def test_invalid_transition_raises(self):
        """Invalid transitions should raise InvalidTransitionError."""
        sm = StateMachine()
        with pytest.raises(InvalidTransitionError):
            sm.transition_to(ExecutionState.COMPLETE)  # Can't go directly to COMPLETE
    
    def test_full_pipeline_transition(self):
        """Test transitioning through the full pipeline."""
        sm = StateMachine()
        
        pipeline = [
            ExecutionState.ANALYZING,
            ExecutionState.ASSESSING,
            ExecutionState.PLANNING,
            ExecutionState.GENERATING,
            ExecutionState.REVIEWING,
            ExecutionState.VALIDATING,
            ExecutionState.COMPLETE,
        ]
        
        for state in pipeline:
            sm.transition_to(state)
            assert sm.current_state == state
    
    def test_state_history_tracking(self):
        """State history should track all transitions."""
        sm = StateMachine()
        sm.transition_to(ExecutionState.ANALYZING)
        sm.transition_to(ExecutionState.ASSESSING)
        
        assert len(sm.state_history) == 3
        assert sm.state_history[0] == ExecutionState.PENDING
        assert sm.state_history[1] == ExecutionState.ANALYZING
        assert sm.state_history[2] == ExecutionState.ASSESSING
    
    def test_reset(self):
        """Reset should return to initial state."""
        sm = StateMachine()
        sm.transition_to(ExecutionState.ANALYZING)
        sm.transition_to(ExecutionState.ASSESSING)
        sm.reset()
        
        assert sm.current_state == ExecutionState.PENDING
        assert len(sm.state_history) == 1
    
    def test_get_next_agent(self):
        """Should return correct agent name for each state."""
        sm = StateMachine()
        
        sm.transition_to(ExecutionState.ANALYZING)
        assert sm.get_next_agent() == "issue_intelligence"
        
        sm.transition_to(ExecutionState.ASSESSING)
        assert sm.get_next_agent() == "impact_assessment"
        
        sm.transition_to(ExecutionState.PLANNING)
        assert sm.get_next_agent() == "planner"
    
    def test_can_transition_to(self):
        """Should correctly check valid transitions."""
        sm = StateMachine()
        
        assert sm.can_transition_to(ExecutionState.ANALYZING)
        assert not sm.can_transition_to(ExecutionState.COMPLETE)
        assert not sm.can_transition_to(ExecutionState.VALIDATING)


class TestExecutionContext:
    """Tests for ExecutionContext dataclass."""
    
    def test_context_creation(self):
        """Context should be created with required fields."""
        context = ExecutionContext(
            issue_id="123",
            issue_url="https://github.com/test/repo/issues/123",
            repository="test/repo",
        )
        
        assert context.issue_id == "123"
        assert context.repository == "test/repo"
        assert context.tokens_used == 0
        assert context.retry_count == 0
        assert context.errors == []
    
    def test_context_defaults(self):
        """Context should have empty defaults for agent data."""
        context = ExecutionContext(
            issue_id="1",
            issue_url="url",
            repository="repo",
        )
        
        assert context.issue_analysis == {}
        assert context.impact_assessment == {}
        assert context.execution_plan == {}
        assert context.generated_patch == {}
        assert context.review_result == {}
        assert context.validation_result == {}
