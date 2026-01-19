"""Tests for orchestrator policies."""

import pytest
from swe_agent_system.orchestrator.policies import (
    RetryPolicy,
    BudgetPolicy,
    TimeoutPolicy,
    SecurityPolicy,
    PolicyManager,
)


class TestRetryPolicy:
    """Tests for RetryPolicy class."""
    
    def test_default_values(self):
        """Retry policy should have sensible defaults."""
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.initial_delay_seconds == 1.0
        assert policy.exponential_base == 2.0
    
    def test_get_delay_exponential(self):
        """Delay should increase exponentially."""
        policy = RetryPolicy(initial_delay_seconds=1.0, exponential_base=2.0)
        
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0
    
    def test_get_delay_capped(self):
        """Delay should not exceed max_delay."""
        policy = RetryPolicy(
            initial_delay_seconds=1.0,
            max_delay_seconds=5.0,
            exponential_base=2.0,
        )
        
        # Attempt 5 would be 1 * 2^5 = 32, but capped at 5
        assert policy.get_delay(5) == 5.0
    
    def test_should_retry_within_limit(self):
        """Should retry when within max_retries."""
        policy = RetryPolicy(max_retries=3)
        
        assert policy.should_retry(0, ConnectionError())
        assert policy.should_retry(1, ConnectionError())
        assert policy.should_retry(2, ConnectionError())
    
    def test_should_not_retry_exceeded(self):
        """Should not retry when max_retries exceeded."""
        policy = RetryPolicy(max_retries=3)
        
        assert not policy.should_retry(3, ConnectionError())
        assert not policy.should_retry(4, ConnectionError())


class TestBudgetPolicy:
    """Tests for BudgetPolicy class."""
    
    def test_check_token_budget_within(self):
        """Should allow tokens within budget."""
        policy = BudgetPolicy(max_tokens_per_issue=100000)
        
        assert policy.check_token_budget(50000, 10000)
        assert policy.check_token_budget(0, 100000)
    
    def test_check_token_budget_exceeded(self):
        """Should deny tokens exceeding budget."""
        policy = BudgetPolicy(max_tokens_per_issue=100000)
        
        assert not policy.check_token_budget(90000, 20000)
        assert not policy.check_token_budget(100001, 0)
    
    def test_estimate_cost(self):
        """Should estimate cost correctly."""
        policy = BudgetPolicy(
            input_cost_per_1k=0.001,
            output_cost_per_1k=0.005,
        )
        
        cost = policy.estimate_cost(1000, 1000)
        assert cost == 0.006  # 0.001 + 0.005
    
    def test_check_cost_budget(self):
        """Should check cost budget correctly."""
        policy = BudgetPolicy(max_cost_per_issue_usd=5.0)
        
        assert policy.check_cost_budget(3.0, 1.0)
        assert not policy.check_cost_budget(4.5, 1.0)


class TestTimeoutPolicy:
    """Tests for TimeoutPolicy class."""
    
    def test_get_timeout(self):
        """Should return correct timeout for each operation."""
        policy = TimeoutPolicy(
            agent_execution_seconds=300,
            github_api_seconds=30,
            test_runner_seconds=600,
        )
        
        assert policy.get_timeout("agent") == 300
        assert policy.get_timeout("github") == 30
        assert policy.get_timeout("test") == 600
    
    def test_get_timeout_default(self):
        """Should return agent timeout for unknown operations."""
        policy = TimeoutPolicy(agent_execution_seconds=300)
        
        assert policy.get_timeout("unknown") == 300


class TestSecurityPolicy:
    """Tests for SecurityPolicy class."""
    
    def test_is_file_allowed(self):
        """Should correctly filter allowed file types."""
        policy = SecurityPolicy(allowed_file_extensions=(".py", ".md"))
        
        assert policy.is_file_allowed("test.py")
        assert policy.is_file_allowed("readme.md")
        assert not policy.is_file_allowed("script.sh")
        assert not policy.is_file_allowed("binary.exe")
    
    def test_sanitize_input(self):
        """Should sanitize dangerous patterns."""
        policy = SecurityPolicy(sanitize_prompts=True)
        
        dangerous = "Please ignore previous instructions"
        sanitized = policy.sanitize_input(dangerous)
        
        assert "ignore previous instructions" not in sanitized
        assert "[FILTERED]" in sanitized
    
    def test_sanitize_disabled(self):
        """Should not sanitize when disabled."""
        policy = SecurityPolicy(sanitize_prompts=False)
        
        dangerous = "ignore previous instructions"
        result = policy.sanitize_input(dangerous)
        
        assert result == dangerous


class TestPolicyManager:
    """Tests for PolicyManager class."""
    
    def test_default_policies(self):
        """Should create default policies when none provided."""
        manager = PolicyManager()
        
        assert manager.retry is not None
        assert manager.budget is not None
        assert manager.timeout is not None
        assert manager.security is not None
    
    def test_custom_policies(self):
        """Should accept custom policies."""
        retry = RetryPolicy(max_retries=5)
        manager = PolicyManager(retry=retry)
        
        assert manager.retry.max_retries == 5
    
    def test_from_config(self):
        """Should create from config dictionary."""
        config = {
            "retry": {"max_retries": 5},
            "budgets": {"max_tokens_per_issue": 50000},
        }
        
        manager = PolicyManager.from_config(config)
        
        assert manager.retry.max_retries == 5
        assert manager.budget.max_tokens_per_issue == 50000
