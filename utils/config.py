"""
Configuration management — loads settings from environment / .env file.

All agents share these settings.  The `.env` file is expected at the project
root (two levels up from this file, i.e. the `SWE agent/` directory).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Resolve .env relative to the SWE agent root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

# Also try the IBM project root
_IBM_ROOT = _PROJECT_ROOT.parent
_IBM_ENV_PATH = _IBM_ROOT / ".env"

# Load both (project-level takes precedence)
load_dotenv(_IBM_ENV_PATH)
load_dotenv(_ENV_PATH, override=True)


def get_github_models_token() -> str:
    """Return the GitHub Personal Access Token for Models API."""
    token = os.getenv("GITHUB_MODELS_TOKEN", "")
    if not token:
        raise EnvironmentError(
            "GITHUB_MODELS_TOKEN is not set.\n"
            "To use GitHub Models (free), you need a GitHub PAT.\n"
            "1. Go to: https://github.com/settings/tokens\n"
            "2. Create a new token (create > tokens (classic))\n"
            "3. Scopes: 'read:user' is sufficient for Models API\n"
            "4. Set GITHUB_MODELS_TOKEN=<your_token> in .env"
        )
    return token


def get_model_name(agent_name: str = "default") -> str:
    """Return the GitHub Models model name to use for the given agent.
    
    Args:
        agent_name: One of 'sentry', 'strategist', 'architect', 'developer', 'validator'
    """
    # Per-agent model configuration for optimal performance
    # Model names must match GitHub Models API identifiers exactly
    # Check available models at: https://github.com/marketplace/models
    agent_models = {
        "sentry": os.getenv("SENTRY_MODEL", "gpt-4o-mini"),
        "strategist": os.getenv("STRATEGIST_MODEL", "gpt-4o-mini"),
        "architect": os.getenv("ARCHITECT_MODEL", "gpt-4o"),
        "developer": os.getenv("DEVELOPER_MODEL", "gpt-4o-mini"),
        "validator": os.getenv("VALIDATOR_MODEL", "gpt-4o-mini"),
        # PR Review specialists (Switched to mini to avoid 429 rate limits)
        "syntaxagent": "gpt-4o-mini",
        "performanceagent": "gpt-4o-mini",
        "securityagent": "gpt-4o-mini",
        "architectureagent": "gpt-4o-mini",
        "quantumvalidator": "gpt-4o-mini",
        "aggregatoragent": "gpt-4o-mini",
    }
    return agent_models.get(agent_name.lower(), "gpt-4o-mini")




def get_github_repo_token() -> Optional[str]:
    """Return the optional GitHub token for accessing private repos (separate from Models API)."""
    return os.getenv("GITHUB_REPO_TOKEN")


def get_max_repair_iterations() -> int:
    """How many times the Developer↔Validator loop can retry."""
    return int(os.getenv("MAX_REPAIR_ITERATIONS", "3"))


def get_qiskit_repo() -> str:
    """Default Qiskit repository to target."""
    return os.getenv("QISKIT_REPO", "Qiskit/qiskit")


def get_llm_provider() -> str:
    """Return the LLM provider (currently: 'github-models')."""
    return os.getenv("LLM_PROVIDER", "github-models")
