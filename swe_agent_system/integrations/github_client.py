"""
GitHub API client for repository and issue access.
"""

import os
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
    
    def get_repository(self, repo_name: str) -> Repository:
        """Get a repository by name (e.g., 'Qiskit/qiskit')."""
        if repo_name not in self._repo_cache:
            self._repo_cache[repo_name] = self.github.get_repo(repo_name)
        return self._repo_cache[repo_name]
    
    def get_issue(self, repo_name: str, issue_number: int) -> IssueData:
        """
        Fetch issue data from GitHub.
        
        Args:
            repo_name: Repository in format "owner/repo"
            issue_number: Issue number
            
        Returns:
            IssueData with issue details
        """
        repo = self.get_repository(repo_name)
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
    
    def get_issue_from_url(self, url: str) -> IssueData:
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
        
        return self.get_issue(repo_name, issue_number)
    
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
    
    def get_rate_limit(self) -> dict[str, Any]:
        """Get current API rate limit status."""
        rate_limit = self.github.get_rate_limit()
        return {
            "remaining": rate_limit.core.remaining,
            "limit": rate_limit.core.limit,
            "reset_at": rate_limit.core.reset.isoformat(),
        }
