"""
PR Review Orchestrator – Multi-Agent PR Review Pipeline.

Fetches a GitHub Pull Request (diff + metadata), fans out to 5 specialist
review agents in parallel, then consolidates via the AggregatorAgent.

Pipeline:
  1. Fetch PR diff & metadata from GitHub API
  2. Fan-out to 5 specialist agents (syntax, architecture, quantum, perf, security)
  3. Collect all findings
  4. Pass to AggregatorAgent for final scoring and recommendation
  5. Output structured JSON review report
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .syntax_agent import SyntaxReviewAgent
from .quantum_validator_agent import QuantumValidatorReviewAgent
from .architecture_agent import ArchitectureReviewAgent
from .performance_agent import PerformanceReviewAgent
from .security_agent import SecurityReviewAgent
from .aggregator_agent import AggregatorReviewAgent

from utils.config import get_github_repo_token

logger = logging.getLogger(__name__)
console = Console()


# ── GitHub PR Fetching ────────────────────────────────────────────────────────

GITHUB_API = "https://api.github.com"


def _gh_headers() -> dict[str, str]:
    """Build GitHub API headers with optional auth."""
    h: dict[str, str] = {"Accept": "application/vnd.github+json"}
    token = get_github_repo_token()
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def fetch_pr_metadata(repo: str, pr_number: int) -> dict[str, Any]:
    """Fetch PR metadata from GitHub."""
    url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers=_gh_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()

    return {
        "repo": repo,
        "pr_number": pr_number,
        "title": data.get("title", ""),
        "body": data.get("body", "") or "",
        "author": (data.get("user") or {}).get("login", ""),
        "state": data.get("state", ""),
        "labels": [l["name"] for l in data.get("labels", [])],
        "created_at": data.get("created_at", ""),
        "updated_at": data.get("updated_at", ""),
        "base_branch": (data.get("base") or {}).get("ref", "main"),
        "head_branch": (data.get("head") or {}).get("ref", ""),
        "mergeable": data.get("mergeable"),
        "additions": data.get("additions", 0),
        "deletions": data.get("deletions", 0),
        "changed_files": data.get("changed_files", 0),
        "html_url": data.get("html_url", ""),
    }


def fetch_pr_diff(repo: str, pr_number: int) -> str:
    """Fetch the unified diff of the PR."""
    url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}"
    headers = _gh_headers()
    headers["Accept"] = "application/vnd.github.v3.diff"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_pr_files(repo: str, pr_number: int) -> list[dict[str, Any]]:
    """Fetch the list of changed files in the PR."""
    url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/files"
    resp = requests.get(url, headers=_gh_headers(), timeout=30)
    resp.raise_for_status()
    files = []
    for f in resp.json():
        files.append({
            "filename": f.get("filename", ""),
            "status": f.get("status", ""),
            "additions": f.get("additions", 0),
            "deletions": f.get("deletions", 0),
            "changes": f.get("changes", 0),
            "patch": f.get("patch", ""),
        })
    return files


# ── Orchestrator ──────────────────────────────────────────────────────────────


class PRReviewOrchestrator:
    """
    Multi-agent PR review orchestrator.

    Usage::

        orchestrator = PRReviewOrchestrator()
        report = orchestrator.review_pr(repo="Qiskit/qiskit", pr_number=1234)
        print(json.dumps(report, indent=2))
    """

    def __init__(self, parallel: bool = True) -> None:
        self.parallel = parallel
        self.syntax_agent = SyntaxReviewAgent()
        self.architecture_agent = ArchitectureReviewAgent()
        self.quantum_agent = QuantumValidatorReviewAgent()
        self.performance_agent = PerformanceReviewAgent()
        self.security_agent = SecurityReviewAgent()
        self.aggregator = AggregatorReviewAgent()

    def review_pr(
        self,
        repo: str,
        pr_number: int,
        verbose: bool = True,
    ) -> dict[str, Any]:
        """
        Run the full multi-agent review pipeline on a GitHub PR.

        Parameters
        ----------
        repo : str
            GitHub repository in ``owner/name`` format.
        pr_number : int
            The pull request number to review.
        verbose : bool
            If True, print rich terminal output.

        Returns
        -------
        dict
            The full structured review report (JSON-serializable).
        """
        start_time = time.time()

        if verbose:
            self._print_header(repo, pr_number)

        # ── Step 1: Fetch PR data ────────────────────────────────────
        if verbose:
            console.print("\n[bold cyan]📥 Fetching PR data from GitHub (parallel)...[/bold cyan]")

        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                f_meta = executor.submit(fetch_pr_metadata, repo, pr_number)
                f_diff = executor.submit(fetch_pr_diff, repo, pr_number)
                f_files = executor.submit(fetch_pr_files, repo, pr_number)

                pr_metadata = f_meta.result(timeout=30)
                pr_diff = f_diff.result(timeout=30)
                pr_files = f_files.result(timeout=30)

        except requests.HTTPError as exc:
            error_msg = f"Failed to fetch PR #{pr_number} from {repo}: {exc}"
            logger.error(error_msg)
            if verbose:
                console.print(f"[red]❌ {error_msg}[/red]")
            return {"error": error_msg, "overall_recommendation": "Error"}

        pr_metadata["files_changed"] = [f["filename"] for f in pr_files]
        pr_metadata["files_detail"] = pr_files

        if verbose:
            self._print_pr_info(pr_metadata)

        # ── Step 2: Fan out to specialist agents ─────────────────────
        specialist_agents = [
            ("SyntaxAgent", self.syntax_agent),
            ("ArchitectureAgent", self.architecture_agent),
            ("QuantumValidator", self.quantum_agent),
            ("PerformanceAgent", self.performance_agent),
            ("SecurityAgent", self.security_agent),
        ]

        agent_reports: dict[str, dict[str, Any]] = {}

        if self.parallel:
            agent_reports = self._run_agents_parallel(
                specialist_agents, pr_diff, pr_metadata, verbose
            )
        else:
            agent_reports = self._run_agents_sequential(
                specialist_agents, pr_diff, pr_metadata, verbose
            )

        # ── Step 3: Aggregation ──────────────────────────────────────
        if verbose:
            console.print("\n[bold cyan]🧠 Aggregating findings...[/bold cyan]")

        aggregator_metadata = {**pr_metadata, "agent_reports": agent_reports}
        final_report = self.aggregator.review(pr_diff, aggregator_metadata)

        # ── Step 4: Enrich the report ────────────────────────────────
        elapsed = time.time() - start_time
        final_report["meta"] = {
            "repo": repo,
            "pr_number": pr_number,
            "pr_url": pr_metadata.get("html_url", ""),
            "pr_title": pr_metadata.get("title", ""),
            "pr_author": pr_metadata.get("author", ""),
            "files_changed_count": pr_metadata.get("changed_files", 0),
            "additions": pr_metadata.get("additions", 0),
            "deletions": pr_metadata.get("deletions", 0),
            "review_duration_seconds": round(elapsed, 2),
            "agents_used": [name for name, _ in specialist_agents] + ["AggregatorAgent"],
        }

        if verbose:
            self._print_final_report(final_report, elapsed)

        return final_report

    # ── Parallel execution ───────────────────────────────────────────────

    def _run_agents_parallel(
        self,
        agents: list[tuple[str, Any]],
        pr_diff: str,
        pr_metadata: dict[str, Any],
        verbose: bool,
    ) -> dict[str, dict[str, Any]]:
        """Run all specialist agents in parallel using threads."""
        results: dict[str, dict[str, Any]] = {}

        if verbose:
            console.print("\n[bold cyan]🔎 Running 5 specialist agents in parallel...[/bold cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            futures = {}
            with ThreadPoolExecutor(max_workers=5) as executor:
                for name, agent in agents:
                    task_id = progress.add_task(f"  {name}...", total=None)
                    future = executor.submit(agent.review, pr_diff, pr_metadata)
                    futures[future] = (name, task_id)

                for future in as_completed(futures):
                    name, task_id = futures[future]
                    try:
                        result = future.result(timeout=120)
                        results[name] = result
                        progress.update(task_id, description=f"  ✅ {name} done")
                    except Exception as exc:
                        logger.error("%s agent failed: %s", name, exc)
                        results[name] = {
                            "agent": name,
                            "error": str(exc),
                            "findings": [],
                        }
                        progress.update(task_id, description=f"  ❌ {name} failed")

        if verbose:
            self._print_agent_results(results)

        return results

    def _run_agents_sequential(
        self,
        agents: list[tuple[str, Any]],
        pr_diff: str,
        pr_metadata: dict[str, Any],
        verbose: bool,
    ) -> dict[str, dict[str, Any]]:
        """Run agents one at a time (useful for debugging)."""
        results: dict[str, dict[str, Any]] = {}

        for name, agent in agents:
            if verbose:
                console.print(f"\n  🔎 Running {name}...")
            try:
                result = agent.review(pr_diff, pr_metadata)
                results[name] = result
                if verbose:
                    findings_count = len(result.get("findings", []))
                    console.print(f"    ✅ {name}: {findings_count} findings")
            except Exception as exc:
                logger.error("%s agent failed: %s", name, exc)
                results[name] = {
                    "agent": name,
                    "error": str(exc),
                    "findings": [],
                }
                if verbose:
                    console.print(f"    ❌ {name} failed: {exc}")

        return results

    # ── Pretty Printing ──────────────────────────────────────────────────

    def _print_header(self, repo: str, pr_number: int) -> None:
        console.print()
        console.print(
            Panel(
                "[bold cyan]QuantumPR-GPT[/bold cyan] "
                "[dim]— Multi-Agent PR Review Engine[/dim]\n\n"
                f"Repository:  [bold]{repo}[/bold]\n"
                f"PR Number:   [bold]#{pr_number}[/bold]\n"
                f"Agents:      6 (5 specialist + 1 aggregator)",
                title="🔬 Advanced PR Review",
                border_style="cyan",
            )
        )

    def _print_pr_info(self, meta: dict[str, Any]) -> None:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row("Title", meta.get("title", ""))
        table.add_row("Author", meta.get("author", ""))
        table.add_row("State", meta.get("state", ""))
        table.add_row("Labels", ", ".join(meta.get("labels", [])) or "—")
        table.add_row("Files", str(meta.get("changed_files", 0)))
        table.add_row("Additions", f"+{meta.get('additions', 0)}")
        table.add_row("Deletions", f"-{meta.get('deletions', 0)}")
        console.print(table)

    def _print_agent_results(self, results: dict[str, dict[str, Any]]) -> None:
        table = Table(title="Agent Results", box=None, padding=(0, 2))
        table.add_column("Agent", style="bold cyan")
        table.add_column("Findings", style="bold")
        table.add_column("Status")

        for name, result in results.items():
            if "error" in result and result["error"]:
                table.add_row(name, "—", "[red]❌ Error[/red]")
            else:
                count = len(result.get("findings", []))
                status = "[green]✅[/green]" if count == 0 else f"[yellow]⚠️ {count}[/yellow]"
                table.add_row(name, str(count), status)

        console.print()
        console.print(table)

    def _print_final_report(self, report: dict[str, Any], elapsed: float) -> None:
        risk = report.get("risk_level", "Unknown")
        score = report.get("quality_score", "—")
        recommendation = report.get("overall_recommendation", "Unknown")

        risk_color = {"Low": "green", "Medium": "yellow", "High": "red"}.get(risk, "white")
        rec_color = {
            "Approve": "green",
            "Request Changes": "yellow",
            "Major Revision Required": "red",
        }.get(recommendation, "white")

        stats = report.get("review_stats", {})

        console.print()
        console.print(
            Panel(
                f"[bold]Quality Score:[/bold]  [{risk_color}]{score}/100[/{risk_color}]\n"
                f"[bold]Risk Level:[/bold]     [{risk_color}]{risk}[/{risk_color}]\n"
                f"[bold]Recommendation:[/bold] [{rec_color}]{recommendation}[/{rec_color}]\n"
                f"\n"
                f"[bold]Summary:[/bold]\n{report.get('summary', 'N/A')}\n"
                f"\n"
                f"[dim]Findings:[/dim]  "
                f"Critical: {stats.get('critical', 0)}  |  "
                f"Errors: {stats.get('errors', 0)}  |  "
                f"Warnings: {stats.get('warnings', 0)}  |  "
                f"Info: {stats.get('info', 0)}\n"
                f"[dim]Duration:[/dim]  {elapsed:.1f}s",
                title="📋 Final PR Review Report",
                border_style=risk_color,
            )
        )

        # Print individual dimensions
        dimensions = [
            ("🔧 Syntax Issues", "syntax_issues"),
            ("🏗️  Design Improvements", "design_improvements"),
            ("⚛️  Quantum Validation", "quantum_validation"),
            ("⚡ Performance", "performance_optimizations"),
            ("🔒 Security", "security_concerns"),
        ]

        for emoji_title, key in dimensions:
            items = report.get(key, [])
            if items:
                console.print(f"\n  [bold]{emoji_title}[/bold] ({len(items)} findings):")
                for item in items[:5]:  # cap at 5 per dimension
                    if isinstance(item, dict):
                        file_name = item.get("file", "")
                        issue_text = (
                            item.get("issue", "")
                            or item.get("problem", "")
                            or item.get("risk", "")
                        )
                        console.print(f"    • [dim]{file_name}[/dim] — {issue_text[:100]}")
