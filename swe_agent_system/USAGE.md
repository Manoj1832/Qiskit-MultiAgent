# Usage Guide

The SWE Agent System provides a command-line interface (`swe-agent`) to interact with the agents.

## Common Commands

### 1. Process a Single Issue

This is the main mode of operation. It takes a GitHub issue URL, analyzes it, plans a solution, generates code, and validates it.

```bash
swe-agent process <ISSUE_URL>
```

**Example:**
```bash
swe-agent process https://github.com/Qiskit/qiskit/issues/11545
```

**Options:**
- `--repo`, `-r`: Manually specify the repository (owner/repo) if it cannot be auto-detected.
- `--output`, `-o`: Specify a directory to save artifacts (logs, patches, plans). Default is `traces`.

### 2. Run Benchmarks

Run the agent system against a set of issues defined in a text file.

```bash
swe-agent benchmark <ISSUES_FILE> --repo <OWNER/REPO>
```

**Example:**
Create a file named `issues.txt`:
```text
https://github.com/Qiskit/qiskit/issues/11545
https://github.com/Qiskit/qiskit/issues/11546
```

Run the benchmark:
```bash
swe-agent benchmark issues.txt --repo Qiskit/qiskit
```

### 3. View Results

Inspect the results of previous runs.

```bash
swe-agent results
```

To see details for a specific run:
```bash
swe-agent results --run-id <RUN_ID>
```

## Output Artifacts

The system generates several artifacts during execution in the output directory:

- **trace.log**: detailed execution log.
- **plan.md**: The implementation plan created by the Planner Agent.
- **patch.diff**: The generated code changes.
- **report.md**: A final summary of the actions taken.

## Troubleshooting

- **Authentication Errors**: Double-check your `ANTHROPIC_API_KEY` and `GITHUB_TOKEN` in the `.env` file.
- **Rate Limits**: If you encounter rate limits, try increasing the delay between requests or check your API tier.
