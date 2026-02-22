"""
CLI entry point for the Advanced PR Review Agent.

Usage examples:

  # Review a specific PR
  python pr_review_cli.py --repo Qiskit/qiskit --pr 13456

  # Review with verbose output
  python pr_review_cli.py --repo Qiskit/qiskit --pr 13456 -v

  # Save review to JSON
  python pr_review_cli.py --repo Qiskit/qiskit --pr 13456 --output review.json

  # Sequential mode (for debugging)
  python pr_review_cli.py --repo Qiskit/qiskit --pr 13456 --sequential
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console

console = Console()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="quantum-pr-review",
        description=(
            "QuantumPR-GPT — Multi-Agent PR Review Engine for Qiskit"
        ),
    )

    parser.add_argument(
        "--repo",
        type=str,
        default="Qiskit/qiskit",
        help="GitHub repository in owner/name format (default: Qiskit/qiskit)",
    )
    parser.add_argument(
        "--pr",
        type=int,
        required=True,
        help="GitHub Pull Request number to review",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Save the review report as JSON to this file",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run agents sequentially instead of in parallel (for debugging)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose / debug logging",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress terminal output, only output JSON",
    )

    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    # Logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )

    from agents.pr_review.pr_review_orchestrator import PRReviewOrchestrator

    orchestrator = PRReviewOrchestrator(parallel=not args.sequential)
    report = orchestrator.review_pr(
        repo=args.repo,
        pr_number=args.pr,
        verbose=not args.quiet,
    )

    # Save to file if requested
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        console.print(f"\n[green]✅ Review saved to: {args.output}[/green]")

    # If quiet mode, print JSON to stdout
    if args.quiet:
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
