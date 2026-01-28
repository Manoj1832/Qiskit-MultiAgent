# Enterprise-Grade Multi-Agent Software Engineering AI System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A scalable, enterprise-grade multi-agent AI system that autonomously performs software engineering tasks on real-world codebases, benchmarked using SWE-bench-style evaluation.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Presentation Layer                            │
│                 CLI / Experiment Runner                          │
├─────────────────────────────────────────────────────────────────┤
│                 Orchestration & Policy Layer                     │
│          Agent Manager | State Machine | Policies                │
├─────────────────────────────────────────────────────────────────┤
│                Multi-Agent Intelligence Layer                    │
│  Issue Intel | Impact | Planner | CodeGen | Review | Validator  │
├─────────────────────────────────────────────────────────────────┤
│                 Tooling & Integration Layer                      │
│          GitHub Client | Repo Indexer | Test Runner             │
├─────────────────────────────────────────────────────────────────┤
│               Observability & Benchmarking Layer                 │
│         Structured Logging | Metrics | SWE-bench Eval           │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

> For detailed instructions, see the [Setup Guide](swe_agent_system/SETUP.md) and [Usage Guide](swe_agent_system/USAGE.md).

### Prerequisites

- Python 3.10+
- Anthropic API key
- GitHub Personal Access Token

### Installation

```bash
# Clone the repository
cd swe_agent_system

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e .
```

### Configuration

1. Copy the example environment file:
```bash
copy .env.example .env
```

2. Edit `.env` with your API keys:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GITHUB_TOKEN=your_github_token_here
```

### Usage

**Process a single issue:**
```bash
swe-agent process https://github.com/Qiskit/qiskit/issues/1234
```

**Run benchmark on multiple issues:**
```bash
swe-agent benchmark issues.txt --repo Qiskit/qiskit
```

**View benchmark results:**
```bash
swe-agent results --run-id run_1234567890
```

## 🤖 Agent Pipeline

| Agent | Role |
|-------|------|
| **Issue Intelligence** | Semantic understanding and classification of GitHub issues |
| **Impact Assessment** | Technical severity and business impact analysis |
| **Planner** | Step-by-step solution planning with risk assessment |
| **Code Generator** | Production-quality patch and test generation |
| **PR Reviewer** | Static and semantic code review |
| **Validator** | Test execution and regression detection |

## 📊 Benchmarking

The system uses SWE-bench-style metrics:

- **Resolution Rate**: Percentage of issues successfully resolved
- **Test Pass Rate**: Percentage of generated fixes that pass tests
- **Regression Rate**: Percentage of fixes that introduce regressions
- **Patch Minimality**: How focused the generated patches are
- **Cost Efficiency**: Tokens and cost per issue

## 📁 Project Structure

```
swe_agent_system/
├── orchestrator/          # State machine and execution control
├── agents/                # AI agents (6 specialized agents)
├── repo_intelligence/     # Code indexing and analysis
├── integrations/          # GitHub and test runner
├── benchmarking/          # SWE-bench evaluation
├── observability/         # Logging and tracing
├── configs/               # Configuration files
└── cli.py                 # Command-line interface
```

## 🔒 Security

- Read-only GitHub access by default
- Scoped API tokens
- Prompt sanitization
- Output validation before execution

## 📝 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

Inspired by [SWE-bench](https://www.swebench.com/) and IBM-style engineering principles.
