# Setup Guide

## Prerequisites

Before setting up the SWE Agent System, ensure you have the following installed:

- **Python 3.10** or higher
- **Git**

You will also need the following API keys:

1.  **Anthropic API Key**: For the LLM reasoning capabilities (Claude 3.5 Sonnet).
2.  **GitHub Personal Access Token (Classic)**: With `repo` scope to read/write to repositories.

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/Manoj1832/Qiskit-MultiAgent.git
cd Qiskit-MultiAgent/swe_agent_system
```

### 2. Create a Virtual Environment

It is recommended to use a virtual environment to manage dependencies.

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install the package in editable mode along with its dependencies:

```bash
pip install -e .
```

### 4. Configuration

1.  Copy the example environment file to `.env`:
    ```bash
    # Windows
    copy .env.example .env
    
    # Linux/Mac
    cp .env.example .env
    ```

2.  Open `.env` in your text editor and add your API keys:
    ```ini
    ANTHROPIC_API_KEY=sk-ant-api03-...
    GITHUB_TOKEN=ghp_...
    ```

3.  (Optional) Configure reliable logging:
    ```ini
    LOG_LEVEL=INFO
    ```

## Verification

To verify the installation, run the version command:

```bash
swe-agent version
```

You should see output similar to:
```
SWE Agent System v0.1.0
Enterprise-Grade Multi-Agent Software Engineering AI
```
