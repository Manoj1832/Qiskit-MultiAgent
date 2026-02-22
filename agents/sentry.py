"""
The Sentry — Git & PR Reviewer Agent.

Responsibilities:
  1. Fetch GitHub issue data (title, body, labels, comments).
  2. Map the repository structure (key directories, affected files).
  3. Find related issues and recent commits.
  4. Surface PR review comments if a PR is linked.

The Sentry does NOT analyse the issue — it only gathers intelligence.
It feeds its SentryOutput to the Strategist.
"""

from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent
from domain.models import SentryOutput, GitHubIssueData
from utils.github_helper import (
    fetch_issue,
    fetch_repo_tree,
    fetch_recent_commits,
    search_related_issues,
)


class SentryAgent(BaseAgent):
    """Gathers intelligence about the repo and the issue."""

    name = "Sentry"

    # The Sentry is mostly tool-driven, but uses the LLM to summarise
    # recent commits and identify structurally relevant directories.

    @property
    def system_prompt(self) -> str:
        return """\
You are **The Sentry**, the intelligence branch of the **QuantumPR-GPT** elite engineering team.

Your job is to perform a deep reconnaissance of the repository to gather every possible clue about the reported issue.

Before producing output:
1. Scan the repo structure for hidden modules.
2. Analyze recent commit patterns for structural erosion.
3. Think step-by-step internally.

🔎 RECONNAISSANCE DIMENSIONS
- Map structurally relevant directories
- Summarize recent commit velocity and focus
- Detect repository health anomalies
- Identify related issue clusters

Return ONLY valid JSON:
{
  "recent_commits_summary": "...",
  "relevant_directories": ["..."],
  "repo_health_notes": "..."
}

No markdown.
No explanation outside JSON.
No speculation about the bug.
"""

    def build_user_prompt(self, **kwargs: Any) -> str:
        commits = kwargs.get("commits", [])
        tree = kwargs.get("tree", [])
        keywords = kwargs.get("keywords", [])

        parts = [
            "=== Recent Commits ===",
            *[f"  {c['sha']} | {c['message']} ({c['author']})" for c in commits[:15]],
            "",
            "=== Repository Tree (top-level) ===",
            *[f"  {p}" for p in tree[:80]],
            "",
            f"Issue keywords: {', '.join(keywords)}",
        ]
        return "\n".join(parts)

    def parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Validate that the response contains the expected keys."""
        return {
            "recent_commits_summary": raw.get("recent_commits_summary", ""),
            "relevant_directories": raw.get("relevant_directories", []),
            "repo_health_notes": raw.get("repo_health_notes", ""),
        }

    # ── Main entry-point ─────────────────────────────────────────────────

    def run(self, repo: str, issue_number: int) -> SentryOutput:
        """
        Gather all intelligence about *repo* issue #*issue_number*.
        """
        self.logger.info(
            "🔍 Sentry scanning %s#%d …", repo, issue_number
        )

        # 1. Fetch issue data
        issue_raw = fetch_issue(repo, issue_number)
        issue_data = GitHubIssueData(**issue_raw)

        # 2. Fetch repo tree
        tree = fetch_repo_tree(repo, max_depth=2)

        # 3. Fetch recent commits
        commits = fetch_recent_commits(repo, max_count=15)

        # 4. Extract keywords from issue for related-issue search
        keywords = (
            issue_data.title.split()[:5]
            + issue_data.labels[:3]
        )

        # 5. Search related issues
        related = search_related_issues(repo, keywords, max_results=5)
        related_issue_nums = [
            r["number"] for r in related
            if r["number"] != issue_number
        ]

        # 6. Use LLM to summarise commits & tree relevance
        user_prompt = self.build_user_prompt(
            commits=commits, tree=tree, keywords=keywords,
        )
        try:
            raw = self.call_llm_json(user_prompt)
            llm_summary = self.parse_response(raw)
        except Exception as exc:
            self.logger.warning("LLM summary failed: %s", exc)
            llm_summary = {
                "recent_commits_summary": "Could not generate summary.",
                "relevant_directories": [],
            }

        return SentryOutput(
            issue_data=issue_data,
            repo_structure=llm_summary.get("relevant_directories", tree[:30]),
            related_issues=related_issue_nums,
            recent_commits_summary=llm_summary.get(
                "recent_commits_summary", ""
            ),
        )
