# 🤖 SWE Agent System - Project Overview

## What This Project Does

This is an **AI-powered software engineering assistant** that can **automatically fix bugs** in open-source projects like Qiskit (IBM's quantum computing library).

Instead of a human developer reading a bug report, understanding the code, writing a fix, and testing it - **this system uses AI agents to do it automatically**.

---

## How It Works (Step by Step)

When you run:
```bash
swe-agent process https://github.com/Qiskit/qiskit/issues/12345
```

The system executes a pipeline of 6 specialized AI agents:

```
┌─────────────────────────────────────────────────────────────────┐
│  1. ISSUE INTELLIGENCE AGENT                                    │
│     • Reads the GitHub issue                                    │
│     • Understands what the bug is                               │
│     • Classifies: Is it a bug? Feature? Documentation?          │
├─────────────────────────────────────────────────────────────────┤
│  2. IMPACT ASSESSMENT AGENT                                     │
│     • How serious is this bug?                                  │
│     • How many users are affected?                              │
│     • Is it a security issue?                                   │
├─────────────────────────────────────────────────────────────────┤
│  3. PLANNER AGENT                                               │
│     • Creates a step-by-step plan to fix the bug                │
│     • Identifies which files need to change                     │
│     • Estimates complexity and risk                             │
├─────────────────────────────────────────────────────────────────┤
│  4. CODE GENERATOR AGENT                                        │
│     • Writes the actual code fix                                │
│     • Creates unit tests for the fix                            │
│     • Follows project coding conventions                        │
├─────────────────────────────────────────────────────────────────┤
│  5. PR REVIEWER AGENT                                           │
│     • Reviews the generated code                                │
│     • Checks for bugs, security issues, style problems          │
│     • Suggests improvements                                     │
├─────────────────────────────────────────────────────────────────┤
│  6. VALIDATOR AGENT                                             │
│     • Runs the tests                                            │
│     • Verifies the fix works                                    │
│     • Checks for regressions (did we break something else?)     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    📦 OUTPUT: Code patch ready to submit!
```

---

## Real-World Example

**GitHub Issue #12345:**
> "The `measure()` function returns wrong register name which breaks QASM export"

**What the system does:**

| Step | Agent | Action |
|------|-------|--------|
| 1 | 🔍 Issue Intelligence | "This is a bug in the `measure()` function affecting QASM export" |
| 2 | 📊 Impact Assessment | "Medium severity, affects users doing quantum circuit export" |
| 3 | 📋 Planner | "Need to fix `measure.py`, line ~150, change register naming" |
| 4 | 💻 Code Generator | Writes actual Python code fix + test case |
| 5 | ✅ PR Reviewer | "Code looks good, follows conventions" |
| 6 | 🧪 Validator | "All tests pass, no regressions" |

---

## Why This Matters

| Traditional Approach | SWE Agent System |
|---------------------|------------------|
| Human reads issue | AI reads issue |
| Human searches codebase | AI indexes & searches |
| Human writes fix (hours/days) | AI writes fix (minutes) |
| Human reviews code | AI reviews code |
| Human runs tests | AI runs tests |

**Goal:** Automate repetitive software engineering tasks so developers can focus on harder problems.

---

## System Architecture

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

---

## Benchmarking (SWE-bench Style)

The project includes **SWE-bench style evaluation** which measures:

| Metric | Description |
|--------|-------------|
| Resolution Rate | How many bugs did the AI successfully fix? |
| Test Pass Rate | Did the fixes pass all tests? |
| Regression Rate | Did it introduce any new bugs? |
| Patch Minimality | How focused were the changes? |
| Cost Efficiency | Tokens and cost per issue |

This is inspired by [SWE-bench](https://www.swebench.com/), a famous benchmark for evaluating AI coding assistants.

---

## Quick Start

### Prerequisites
- Python 3.10+
- Google Gemini API key
- GitHub Personal Access Token

### Installation
```bash
cd swe_agent_system
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -e .
```

### Configuration
```bash
# Copy and edit .env file
copy .env.example .env
# Add your GEMINI_API_KEY and GITHUB_TOKEN
```

### Usage
```bash
# Process a single issue
swe-agent process https://github.com/Qiskit/qiskit/issues/12345

# Run benchmarks
swe-agent benchmark issues.txt -r Qiskit/qiskit

# View results
swe-agent results

# Show version
swe-agent version
```

---

## Project Structure

```
swe_agent_system/
├── orchestrator/          # State machine and execution control
│   ├── engine.py          # Main orchestration logic
│   ├── state_machine.py   # Execution states
│   └── policies.py        # Retry, budget, security policies
├── agents/                # 6 AI agents
│   ├── issue_intelligence/
│   ├── impact_assessment/
│   ├── planner/
│   ├── code_generator/
│   ├── pr_reviewer/
│   └── validator/
├── repo_intelligence/     # Code indexing and analysis
├── integrations/          # GitHub client, test runner
├── benchmarking/          # SWE-bench evaluation
├── observability/         # Logging and tracing
├── configs/               # Configuration files
├── tests/                 # 73 unit tests
└── cli.py                 # Command-line interface
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| AI/LLM | Google Gemini 2.5 Flash |
| Language | Python 3.10+ |
| GitHub API | PyGithub |
| CLI | Click + Rich |
| Logging | Structlog |
| Testing | Pytest |
| Validation | Pydantic |

---

## Summary

**This project is an AI software engineer that can:**

1. ✅ Read GitHub issues automatically
2. ✅ Understand bugs and their impact
3. ✅ Plan fixes step-by-step
4. ✅ Write code patches
5. ✅ Review its own code
6. ✅ Test and validate fixes

All powered by **Google Gemini AI** and designed for enterprise-scale open-source projects like **Qiskit**, following **IBM-style engineering principles**.

---

## License

MIT License

## Inspiration

- [SWE-bench](https://www.swebench.com/) - Benchmark for AI coding assistants
- [Qiskit](https://github.com/Qiskit/qiskit) - IBM's quantum computing library
