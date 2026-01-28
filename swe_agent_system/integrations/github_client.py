"""
GitHub API client for repository and issue access.
"""

import os
import time
import asyncio
from dataclasses import dataclass
from typing import Any
from github import Github, GithubException
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Repository import Repository


@dataclass
class IssueData:
    """Structured representation of a GitHub issue."""
    number: int
    title: str
    body: str
    state: str
    labels: list[str]
    comments: list[str]
    url: str
    created_at: str
    updated_at: str
    author: str


@dataclass
class FileContent:
    """Structured representation of a file from the repository."""
    path: str
    content: str
    sha: str
    size: int


class RateLimiter:
    """Proactive rate limiter for GitHub API calls."""
    
    def __init__(self, safety_margin: int = 100):
        self.safety_margin = safety_margin
        self.last_check = 0
        self.cached_limits = None
        self.check_interval = 60  # Check rate limits every 60 seconds
    
    async def check_rate_limit(self, github_client: Github) -> dict[str, Any]:
        """Check current rate limit status with caching."""
        now = time.time()
        
        # Use cached value if recent enough
        if (self.cached_limits and 
            now - self.last_check < self.check_interval):
            return self.cached_limits
        
        try:
            rate_limit = github_client.get_rate_limit()
            # Handle different PyGithub versions and access patterns
            try:
                # Try accessing core attribute first
                core_limit = rate_limit.core
            except (AttributeError, TypeError):
                try:
                    # Try rate attribute as fallback
                    core_limit = rate_limit.rate
                except (AttributeError, TypeError):
                    # Use the rate_limit object directly
                    core_limit = rate_limit
            
            if core_limit and hasattr(core_limit, 'remaining'):
                limits = {
                    "remaining": core_limit.remaining,
                    "limit": core_limit.limit,
                    "reset_at": core_limit.reset.timestamp(),
                    "reset_in": max(0, core_limit.reset.timestamp() - now),
                }
            else:
                # Fallback for older versions or different structures
                limits = {
                    "remaining": getattr(rate_limit, 'remaining', 1000),
                    "limit": getattr(rate_limit, 'limit', 5000),
                    "reset_at": now + 3600,
                    "reset_in": 3600,
                }
            
            self.cached_limits = limits
            self.last_check = now
            return limits
            
        except Exception:
            # Fallback to conservative limits
            return {
                "remaining": 1000,
                "limit": 5000,
                "reset_at": now + 3600,
                "reset_in": 3600,
            }
    
    async def wait_if_needed(self, github_client: Github, estimated_cost: int = 1) -> None:
        """Wait if rate limit might be exceeded."""
        limits = await self.check_rate_limit(github_client)
        
        # If we're too close to the limit, wait
        if limits["remaining"] <= (estimated_cost + self.safety_margin):
            wait_time = limits["reset_in"] + 1  # Wait until reset + 1 second buffer
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                # Refresh limits after waiting
                await self.check_rate_limit(github_client)


class GitHubClient:
    """
    Client for interacting with GitHub API.
    
    By default, operates in read-only mode for security.
    """
    
    def __init__(self, token: str | None = None, read_only: bool = True):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub Personal Access Token. If not provided, uses GITHUB_TOKEN env var.
            read_only: If True, prevents any write operations.
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN env var or pass token.")
        
        self.github = Github(self.token)
        self.read_only = read_only
        self._repo_cache: dict[str, Repository] = {}
        self.rate_limiter = RateLimiter()
    
    async def get_repository(self, repo_name: str) -> Repository:
        """Get a repository by name (e.g., 'Qiskit/qiskit')."""
        await self.rate_limiter.wait_if_needed(self.github, estimated_cost=1)
        
        if repo_name not in self._repo_cache:
            self._repo_cache[repo_name] = self.github.get_repo(repo_name)
        return self._repo_cache[repo_name]
    
    async def get_issue(self, repo_name: str, issue_number: int) -> IssueData:
        """
        Fetch issue data from GitHub.
        
        Args:
            repo_name: Repository in format "owner/repo"
            issue_number: Issue number
            
        Returns:
            IssueData with issue details
        """
        await self.rate_limiter.wait_if_needed(self.github, estimated_cost=2)
        
        repo = await self.get_repository(repo_name)
        issue = repo.get_issue(issue_number)
        
        # Fetch comments
        comments = [c.body for c in issue.get_comments()]
        
        return IssueData(
            number=issue.number,
            title=issue.title,
            body=issue.body or "",
            state=issue.state,
            labels=[label.name for label in issue.labels],
            comments=comments,
            url=issue.html_url,
            created_at=issue.created_at.isoformat(),
            updated_at=issue.updated_at.isoformat(),
            author=issue.user.login if issue.user else "unknown",
        )
    
    async def get_issue_from_url(self, url: str) -> IssueData:
        """
        Fetch issue data from a GitHub issue URL.
        
        Args:
            url: Full GitHub issue URL
            
        Returns:
            IssueData with issue details
        """
        # Parse URL: https://github.com/owner/repo/issues/123
        parts = url.rstrip("/").split("/")
        issue_number = int(parts[-1])
        repo_name = f"{parts[-4]}/{parts[-3]}"
        
        return await self.get_issue(repo_name, issue_number)
    
    def get_file_content(self, repo_name: str, file_path: str, ref: str = "main") -> FileContent:
        """
        Get content of a file from the repository.
        
        Args:
            repo_name: Repository in format "owner/repo"
            file_path: Path to file in the repository
            ref: Branch or commit reference
            
        Returns:
            FileContent with file data
        """
        repo = self.get_repository(repo_name)
        content = repo.get_contents(file_path, ref=ref)
        
        # Handle single file (not directory)
        if isinstance(content, list):
            raise ValueError(f"{file_path} is a directory, not a file")
        
        return FileContent(
            path=content.path,
            content=content.decoded_content.decode("utf-8"),
            sha=content.sha,
            size=content.size,
        )
    
    def list_directory(self, repo_name: str, path: str = "", ref: str = "main") -> list[str]:
        """
        List files in a directory of the repository.
        
        Args:
            repo_name: Repository in format "owner/repo"
            path: Directory path (empty for root)
            ref: Branch or commit reference
            
        Returns:
            List of file/directory paths
        """
        repo = self.get_repository(repo_name)
        contents = repo.get_contents(path, ref=ref)
        
        if not isinstance(contents, list):
            contents = [contents]
        
        return [c.path for c in contents]
    
    def search_code(self, repo_name: str, query: str, max_results: int = 10) -> list[str]:
        """
        Search for code in the repository.
        
        Args:
            repo_name: Repository in format "owner/repo"
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of file paths matching the query
        """
        full_query = f"{query} repo:{repo_name}"
        results = self.github.search_code(full_query)
        
        return [r.path for r in list(results)[:max_results]]
    
    def get_pull_request(self, repo_name: str, pr_number: int) -> dict[str, Any]:
        """
        Get pull request details.
        
        Args:
            repo_name: Repository in format "owner/repo"
            pr_number: Pull request number
            
        Returns:
            Dictionary with PR details
        """
        repo = self.get_repository(repo_name)
        pr = repo.get_pull(pr_number)
        
        return {
            "number": pr.number,
            "title": pr.title,
            "body": pr.body,
            "state": pr.state,
            "merged": pr.merged,
            "files_changed": [f.filename for f in pr.get_files()],
            "additions": pr.additions,
            "deletions": pr.deletions,
        }
    
    async def get_rate_limit(self) -> dict[str, Any]:
        """Get current API rate limit status."""
        return await self.rate_limiter.check_rate_limit(self.github)
