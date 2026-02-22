"""
Base class for all PR review sub-agents.

Each review sub-agent focuses on one dimension (syntax, quantum, architecture,
performance, security).  They share the same LLM access and JSON parsing logic
provided by this base class.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from utils.llm_client import LLMClient, get_llm_client


class BaseReviewAgent(ABC):
    """Abstract base for every PR review sub-agent."""

    name: str = "BaseReviewAgent"
    dimension: str = "unknown"  # e.g., "syntax", "quantum", "architecture"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.logger = logging.getLogger(f"pr_review.{self.name}")
        self.llm = llm or get_llm_client(agent_name=self.name.lower())


    # ── Abstract interface ───────────────────────────────────────────────

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the full system prompt specialised for this dimension."""
        ...

    @abstractmethod
    def build_user_prompt(self, pr_diff: str, pr_metadata: dict[str, Any]) -> str:
        """Build the user-facing prompt from PR data."""
        ...

    @abstractmethod
    def parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Parse and validate the raw JSON response from the LLM."""
        ...

    # ── Convenience ──────────────────────────────────────────────────────

    def call_llm_json(self, user_prompt: str) -> dict[str, Any]:
        """Call the LLM and parse the response as JSON."""
        self.logger.info("🔎 %s agent sending prompt to LLM …", self.name)
        return self.llm.generate_json(
            user_prompt=user_prompt,
            system_prompt=self.system_prompt,
        )

    def review(self, pr_diff: str, pr_metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Run this agent's review dimension on the given PR.

        Parameters
        ----------
        pr_diff : str
            The unified diff of the pull request.
        pr_metadata : dict
            Metadata about the PR (title, body, author, files changed, etc.).

        Returns
        -------
        dict
            Structured findings for this dimension.
        """
        user_prompt = self.build_user_prompt(pr_diff, pr_metadata)
        try:
            raw = self.call_llm_json(user_prompt)
            return self.parse_response(raw)
        except Exception as exc:
            self.logger.error("%s review failed: %s", self.name, exc)
            return {
                "agent": self.name,
                "dimension": self.dimension,
                "error": str(exc),
                "findings": [],
            }
