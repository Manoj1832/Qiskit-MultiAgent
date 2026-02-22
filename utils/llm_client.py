"""
Unified LLM client wrapper for the entire SWE-agent framework.

All agents call through this single client so that:
  * API-key management is centralised.
  * Rate-limit retries are handled uniformly.
  * Switching LLM providers is a one-line change.

Currently integrated with GitHub Models API (free, open-source models).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from openai import OpenAI
from openai import APIError as ClientError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import get_github_models_token, get_model_name

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper around GitHub Models API with retry logic."""

    def __init__(
        self,
        api_token: Optional[str] = None,
        model_name: Optional[str] = None,
        agent_name: str = "default",
    ) -> None:
        self._api_token = api_token or get_github_models_token()
        # Get agent-specific model or fall back to default
        self.model_name = model_name or get_model_name(agent_name)
        
        # Initialize OpenAI client pointed at GitHub Models endpoint
        self.client = OpenAI(
            api_key=self._api_token,
            base_url="https://models.inference.ai.azure.com",
        )

    # ── Core Generation ──────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type(ClientError),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _generate(
        self,
        user_prompt: str,
        system_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """Send a prompt to GitHub Models and return the raw text response."""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

    # ── JSON-safe Generation ─────────────────────────────────────────────

    def generate_json(
        self,
        user_prompt: str,
        system_prompt: str,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """
        Generate a response and parse it as JSON.

        Handles common LLM quirks:
          - Stripping markdown code fences.
          - Multiple retry attempts on parse failure.
        """
        raw = self._generate(user_prompt, system_prompt, temperature)
        return self._parse_json(raw)

    def generate_text(
        self,
        user_prompt: str,
        system_prompt: str,
        temperature: float = 0.3,
    ) -> str:
        """Generate a plain-text response (e.g., code, patches)."""
        return self._generate(user_prompt, system_prompt, temperature)

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """Strip code fences and parse JSON from LLM output."""
        cleaned = raw.strip()

        # Strip ```json ... ``` or ``` ... ```
        if cleaned.startswith("```"):
            # Remove opening fence (possibly with language tag)
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("LLM returned invalid JSON:\n%.500s", cleaned)
            raise ValueError(
                "LLM did not return valid JSON. Raw output starts with: "
                f"{cleaned[:200]!r}"
            ) from exc


# ── Module-level convenience ──────────────────────────────────────────────────

_clients: dict[str, LLMClient] = {}


def get_llm_client(agent_name: str = "default") -> LLMClient:
    """Return (and lazily create) a shared LLMClient instance for the given agent.
    
    Each agent can have its own configured model (from environment variables).
    """
    global _clients
    if agent_name not in _clients:
        _clients[agent_name] = LLMClient(agent_name=agent_name)
    return _clients[agent_name]

