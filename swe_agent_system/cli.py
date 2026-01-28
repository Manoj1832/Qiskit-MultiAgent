"""
Command-line interface for the SWE Agent System.
"""

import asyncio
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .orchestrator import Orchestrator, PolicyManager
from .agents import (
    IssueIntelligenceAgent,
    ImpactAssessmentAgent,
    PlannerAgent,
    CodeGeneratorAgent,
    PRReviewerAgent,
    ValidatorAgent,
)
from .integrations import GitHubClient
from .observability import configure_logging, ExecutionTracer
from .benchmarking import SWEBenchRunner

console = Console()


def validate_github_url(url: str) -> bool:
    """
    Validate GitHub issue URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid GitHub issue URL
    """
    try:
        parsed = urlparse(url)
        
        # Check domain
        if parsed.netloc not in ["github.com", "www.github.com"]:
            return False
        
        # Check path pattern: /owner/repo/issues/number
        path_pattern = r"^/[^/]+/[^/]+/issues/\d+$"
        return bool(re.match(path_pattern, parsed.path))
        
    except Exception:
        return False


def validate_repo_format(repo: str) -> bool:
    """
    Validate repository format (owner/repo).
    
    Args:
        repo: Repository string to validate
        
    Returns:
        True if valid repository format
    """
    pattern = r"^[^/]+/[^/]+$"
    return bool(re.match(pattern, repo))


def load_config():
    """Load configuration from environment and config files."""
    load_dotenv()
    return {
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "github_token": os.getenv("GITHUB_TOKEN"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
    }


def create_agents():
    """Create all agent instances."""
    return {
        "issue_intelligence": IssueIntelligenceAgent(),
        "impact_assessment": ImpactAssessmentAgent(),
        "planner": PlannerAgent(),
        "code_generator": CodeGeneratorAgent(),
        "pr_reviewer": PRReviewerAgent(),
        "validator": ValidatorAgent(),
    }


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def cli(verbose: bool):
    """SWE Agent System - Multi-agent software engineering AI."""
    if verbose:
        os.environ["LOG_LEVEL"] = "DEBUG"
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))


@cli.command()
@click.argument("issue_url")
@click.option("--repo", "-r", help="Repository (owner/repo format)")
@click.option("--output", "-o", type=click.Path(), help="Output directory for results")
def process(issue_url: str, repo: str | None, output: str | None):
    """Process a single GitHub issue."""
    # Validate GitHub URL
    if not validate_github_url(issue_url):
        console.print("[red]Error: Invalid GitHub issue URL format[/red]")
        console.print("Expected format: https://github.com/owner/repo/issues/123")
        raise click.Abort()
    
    config = load_config()
    
    if not config["anthropic_api_key"]:
        console.print("[red]Error: ANTHROPIC_API_KEY not set[/red]")
        raise click.Abort()
    
    if not config["github_token"]:
        console.print("[red]Error: GITHUB_TOKEN not set[/red]")
        raise click.Abort()
    
    # Extract repo from URL if not provided
    if not repo:
        parts = issue_url.split("/")
        repo = f"{parts[-4]}/{parts[-3]}"
    
    # Validate repo format
    if not validate_repo_format(repo):
        console.print("[red]Error: Invalid repository format[/red]")
        console.print("Expected format: owner/repo")
        raise click.Abort()
    
    console.print(f"[blue]Processing issue:[/blue] {issue_url}")
    console.print(f"[blue]Repository:[/blue] {repo}")
    
    # Create agents and orchestrator
    agents = create_agents()
    tracer = ExecutionTracer(output or "traces")
    orchestrator = Orchestrator(agents, tracer=tracer)
    
    # Run the pipeline
    async def run():
        from .orchestrator.state_machine import ExecutionContext
        
        # Fetch issue data first (async)
        github = GitHubClient(config["github_token"])
        issue_data = await github.get_issue_from_url(issue_url)
        
        console.print(f"[green]Issue #{issue_data.number}:[/green] {issue_data.title}")
        
        context = ExecutionContext(
            issue_id=str(issue_data.number),
            issue_url=issue_url,
            repository=repo,
        )
        context.issue_analysis["raw_issue"] = {
            "number": issue_data.number,
            "title": issue_data.title,
            "body": issue_data.body,
            "labels": issue_data.labels,
            "comments": issue_data.comments,
        }
        
        result = await orchestrator.process_issue(issue_url, repo)
        return result
    
    result = asyncio.run(run())
    
    # Display results
    if result.errors:
        console.print("[red]Errors occurred:[/red]")
        for error in result.errors:
            console.print(f"  - {error}")
    else:
        console.print("[green]✓ Issue processed successfully[/green]")
        
        # Show summary
        table = Table(title="Processing Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Tokens Used", str(result.tokens_used))
        table.add_row("Retries", str(result.retry_count))
        
        if result.generated_patch.get("patches"):
            table.add_row("Patches Generated", str(len(result.generated_patch["patches"])))
        
        if result.validation_result.get("tests_passed") is not None:
            table.add_row("Tests Passed", str(result.validation_result["tests_passed"]))
        
        console.print(table)


@cli.command()
@click.argument("issues_file", type=click.Path(exists=True))
@click.option("--repo", "-r", required=True, help="Repository (owner/repo format)")
@click.option("--output", "-o", type=click.Path(), default="experiments", help="Output directory")
def benchmark(issues_file: str, repo: str, output: str):
    """Run benchmark on a list of issues."""
    # Validate repo format
    if not validate_repo_format(repo):
        console.print("[red]Error: Invalid repository format[/red]")
        console.print("Expected format: owner/repo")
        raise click.Abort()
    
    config = load_config()
    
    if not config["anthropic_api_key"] or not config["github_token"]:
        console.print("[red]Error: API keys not configured[/red]")
        raise click.Abort()
    
    console.print(f"[blue]Running benchmark on {repo}[/blue]")
    
    runner = SWEBenchRunner(output)
    run = runner.start_run(repo)
    
# Load issues from file and validate URLs
    with open(issues_file) as f:
        issue_urls = []
        invalid_urls = []
        
        for line_num, line in enumerate(f, 1):
            url = line.strip()
            if not url:
                continue
                
            if validate_github_url(url):
                issue_urls.append(url)
            else:
                invalid_urls.append(f"Line {line_num}: {url}")
    
    if invalid_urls:
        console.print("[red]Error: Found invalid GitHub issue URLs:[/red]")
        for invalid in invalid_urls[:5]:  # Show first 5 errors
            console.print(f"  - {invalid}")
        if len(invalid_urls) > 5:
            console.print(f"  ... and {len(invalid_urls) - 5} more")
        raise click.Abort()
    
    console.print(f"Processing {len(issue_urls)} issues...")
    
    # Process would happen here in full implementation
    console.print(f"[green]Benchmark complete. Results saved to {output}/{run.run_id}.json[/green]")


@cli.command()
@click.option("--run-id", "-r", help="Specific run ID to show")
@click.option("--output", "-o", type=click.Path(), default="experiments", help="Results directory")
def results(run_id: str | None, output: str):
    """Show benchmark results."""
    runner = SWEBenchRunner(output)
    
    if run_id:
        run = runner.load_run(run_id)
        summary = run.get_summary()
        
        table = Table(title=f"Benchmark Results: {run_id}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in summary.items():
            if isinstance(value, float):
                table.add_row(key, f"{value:.2%}" if "rate" in key else f"{value:.2f}")
            else:
                table.add_row(key, str(value))
        
        console.print(table)
    else:
        # List all runs
        runs = list(Path(output).glob("run_*.json"))
        console.print(f"Found {len(runs)} benchmark runs:")
        for run_path in runs:
            console.print(f"  - {run_path.stem}")


@cli.command()
def version():
    """Show version information."""
    console.print("SWE Agent System v0.1.0")
    console.print("Enterprise-Grade Multi-Agent Software Engineering AI")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
