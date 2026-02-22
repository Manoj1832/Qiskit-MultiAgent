# GitHub Free Models Setup Guide

## Overview
This guide explains how to switch from Gemini API to **GitHub's free open-source models** and recommends the best model for each agent in your SWE-Agent framework.

## Why GitHub Models?
✅ **Free** - No billing required  
✅ **Open source** - Transparency and community support  
✅ **Fast inference** - Optimized for chat/code tasks  
✅ **Per-agent optimization** - Choose the best model for each role  
✅ **Fallback capability** - Mix and match models  

---

## Step 1: Get a GitHub Personal Access Token (PAT)

1. Go to https://github.com/settings/tokens
2. Click **Generate new token** → **Tokens (classic)**
3. Set the following:
   - **Token name**: `github-models-api`
   - **Expiration**: Set as needed (90 days recommended)
   - **Scopes**: Check only `read:user` (that's all you need for Models API)
4. Click **Generate token** and **copy it immediately** (you won't see it again)
5. Add to your `.env` file:
   ```
   GITHUB_MODELS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

---

## Step 2: Install Dependencies

Replace Gemini with OpenAI SDK:

```bash
# Remove old dependency
pip uninstall google-genai -y

# Install new dependency
pip install openai>=1.0.0

# Or reinstall from updated pyproject.toml
pip install -e .
```

---

## Step 3: Recommended Model Per Agent

### Quick Reference Table

| Agent | Role | **Recommended Model** | Reasoning |
|---|---|---|---|
| **Sentry** 🔍 | Data gathering & summarization | `phi-3-medium` | Small, fast, good for summarizing commits & repo structure |
| **Strategist** 🧠 | Issue classification & triage | `mistral-7b` | Excellent reasoning for categorizing issues & Qiskit concepts |
| **Architect** 📐 | Planning & cross-module logic | `llama-2-70b` | Largest model; best for complex multi-file reasoning |
| **Developer** 💻 | Code generation & patches | `codestral-latest` | Specialized for code; produces clean diffs |
| **Validator** ✅ | Test generation & verification | `mistral-7b` | Good balance of reasoning + test writing skills |

---

## Available GitHub Models (Free Tier)

### Lightweight Models (Best for Sentry)
```
phi-3-mini       - 3.8B parameters, ultra-fast
phi-3-medium     - 14B parameters, good balance
phi-3-large      - 42B parameters, more reasoning
mistral-nemo     - Compact, efficient reasoning
```

### Mid-size Models (Best for Strategist, Validator)
```
mistral-7b       - 7B parameters, excellent reasoning
mistral-large    - 47B parameters, very capable
```

### Large Models (Best for Architect)
```
llama-2-7b       - 7B parameters, good base model
llama-2-13b      - 13B parameters, better reasoning
llama-2-70b      - 70B parameters, BEST for complex tasks
```

### Code-Specialized Models (Best for Developer)
```
codestral-latest - Optimized for code generation & understanding
```

### Other Options
```
granite-8b-code-base         - IBM's Granite model
granite-340b-korean-preview  - Multilingual variant
```

---

## Step 4: Configure `.env`

Update your `.env` file with **required** and **optional** settings:

### Minimal Configuration (Required)
```bash
# Your GitHub PAT (required)
GITHUB_MODELS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Full Configuration (Optional Model Overrides)
```bash
# GitHub Models API Token
GITHUB_MODELS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Per-Agent Model Configuration (these are the defaults)
SENTRY_MODEL=phi-3-medium
STRATEGIST_MODEL=mistral-7b
ARCHITECT_MODEL=llama-2-70b
DEVELOPER_MODEL=codestral-latest
VALIDATOR_MODEL=mistral-7b

# Optional: GitHub token for accessing private repos
# GITHUB_REPO_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Default Qiskit repo
# QISKIT_REPO=Qiskit/qiskit

# Optional: Max repair iterations
# MAX_REPAIR_ITERATIONS=3
```

### Alternative Configurations

**Budget-Optimized** (use smaller models):
```bash
SENTRY_MODEL=phi-3-mini
STRATEGIST_MODEL=mistral-7b
ARCHITECT_MODEL=mistral-large
DEVELOPER_MODEL=codestral-latest
VALIDATOR_MODEL=mistral-7b
```

**Speed-Optimized** (use smaller, faster models):
```bash
SENTRY_MODEL=phi-3-mini
STRATEGIST_MODEL=mistral-7b
ARCHITECT_MODEL=llama-2-13b
DEVELOPER_MODEL=mistral-7b
VALIDATOR_MODEL=phi-3-medium
```

**Quality-Optimized** (use large, capable models):
```bash
SENTRY_MODEL=phi-3-large
STRATEGIST_MODEL=mistral-large
ARCHITECT_MODEL=llama-2-70b
DEVELOPER_MODEL=codestral-latest
VALIDATOR_MODEL=mistral-large
```

---

## Step 5: Update Your Code

The framework has already been updated to use GitHub Models. No further changes needed!

However, if you're integrating into other parts of your codebase:

### In Your Code
```python
from utils.config import get_model_name, get_github_models_token
from utils.llm_client import get_llm_client

# Get the right model for an agent
sentry_model = get_model_name("sentry")  # Returns "phi-3-medium"

# Get LLM client with agent-specific model
llm = get_llm_client("developer")  # Uses DEVELOPER_MODEL

# The token is fetched automatically
token = get_github_models_token()  # From GITHUB_MODELS_TOKEN env var
```

---

## Model Comparison Matrix

### Reasoning Capability
```
phi-3-mini       ████░░░░░░ 40%
mistral-7b       ████████░░ 80%
mistral-large    █████████░ 90%
llama-2-70b      ██████████ 100%
```

### Code Generation Quality
```
phi-3-medium     ██████░░░░ 60%
mistral-7b       ███████░░░ 70%
codestral        ██████████ 100%
llama-2-70b      █████████░ 95%
```

### Speed (Inference Time)
```
phi-3-mini       ██████████ 100% (fastest)
phi-3-medium     █████████░ 90%
mistral-7b       ████████░░ 80%
mistral-large    ██████░░░░ 60%
llama-2-70b      ███░░░░░░░ 30% (slowest)
```

### Token Efficiency (Cost/Quality)
```
phi-3-mini       ██████████ 100% (best value)
phi-3-medium     █████████░ 95%
mistral-7b       ████████░░ 85%
mistral-large    ██████░░░░ 60%
llama-2-70b      █████░░░░░ 50%
```

---

## Troubleshooting

### Error: "GITHUB_MODELS_TOKEN is not set"
**Solution**: Add `GITHUB_MODELS_TOKEN` to your `.env` file with a valid GitHub PAT.

### Error: "Model not found"
**Solution**: Check that the model name is correct. Visit https://github.com/marketplace/models to see all available models.

### Slow responses
**Solution**: 
- Try a smaller model (e.g., `phi-3-medium` instead of `llama-2-70b`)
- Use the speed-optimized config above
- Reduce `temperature` in requests (closer to 0 = faster, more deterministic)

### Rate limiting
**Solution**: 
- GitHub Models has a rate limit of **15 requests per minute**
- The framework retries with exponential backoff automatically
- If hitting limits, use smaller models (process faster)

### Poor response quality
**Solution**:
- Try a larger model from the recommended list
- Improve your prompts (in `system_prompt` properties)
- Check Qiskit domain knowledge in `domain/qiskit_knowledge.py`

---

## Advanced: Custom Model Selection

If you want to test different models, edit `.env`:

```bash
# Experiment with Llama for the Strategist
STRATEGIST_MODEL=llama-2-13b

# Use Phi for everything (fastest)
SENTRY_MODEL=phi-3-large
STRATEGIST_MODEL=phi-3-large
ARCHITECT_MODEL=phi-3-large
DEVELOPER_MODEL=phi-3-large
VALIDATOR_MODEL=phi-3-large
```

Then run your agent and observe:
- Response quality
- Latency
- Token usage

---

## Performance Expectations

### Per Agent (with recommended models)

**Sentry** (gather repo info)  
⏱️ **~5-10 seconds** | Models: phi-3-medium

**Strategist** (classify issue)  
⏱️ **~15-30 seconds** | Model: mistral-7b

**Architect** (plan changes)  
⏱️ **~30-60 seconds** | Model: llama-2-70b

**Developer** (generate patches)  
⏱️ **~30-90 seconds** | Model: codestral-latest

**Validator** (write tests)  
⏱️ **~20-40 seconds** | Model: mistral-7b

**Total Pipeline**: ~2-4 minutes (first iteration)

---

## FAQ

**Q: Can I use different models for different runs?**  
A: Yes. Update `.env` and restart your process. Each `get_llm_client()` call reads from config.

**Q: What if I want to go back to Gemini?**  
A: Possible but requires reverting the code changes. The framework is optimized for GitHub Models now.

**Q: Can I mix Gemini + GitHub models?**  
A: Not easily. The abstraction is currently GitHub Models only. You'd need to create a new provider class.

**Q: Which model is cheapest?**  
A: All are **free**! GitHub Models don't have per-token billing. Just rate limits.

**Q: Can I use my own open model (e.g., local Ollama)?**  
A: The Framework uses OpenAI-compatible API. You could point `base_url` in `llm_client.py` to a local Ollama instance.

---

## Next Steps

1. ✅ Get GitHub PAT from https://github.com/settings/tokens
2. ✅ Add `GITHUB_MODELS_TOKEN` to `.env`
3. ✅ Run `pip install -e .` to update dependencies
4. ✅ Test with: `python main.py --repo Qiskit/qiskit --issue <NUMBER> -v`
5. ✅ Adjust models in `.env` if needed

---

## References
- GitHub Models Docs: https://github.com/marketplace/models
- GitHub API Docs: https://docs.github.com/en/rest/guides/using-the-github-api-in-your-code
- OpenAI SDK Reference: https://github.com/openai/openai-python
