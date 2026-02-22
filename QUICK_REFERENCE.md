# Quick Reference: Agent Models & Setup

## TL;DR - Just Do This

1. **Get GitHub PAT:**
   ```
   https://github.com/settings/tokens
   → Generate new token (classic)
   → Scopes: ✓ read:user only
   → Copy token
   ```

2. **Update `.env`:**
   ```
   GITHUB_MODELS_TOKEN=ghp_xxxxxxxxxxxxx
   ```

3. **Install:**
   ```bash
   pip install -e .
   ```

4. **Run:**
   ```bash
   python main.py --repo Qiskit/qiskit --issue 12345 -v
   ```

---

## Agent → Best Model Mapping

```
Sentry      ──→  phi-3-medium       (summarization)
Strategist  ──→  mistral-7b        (reasoning)
Architect   ──→  llama-2-70b       (planning)
Developer   ──→  codestral-latest  (coding)
Validator   ──→  mistral-7b        (testing)
```

### Override in `.env`
```bash
SENTRY_MODEL=phi-3-mini              # faster
STRATEGIST_MODEL=mistral-7b          # balanced
ARCHITECT_MODEL=llama-2-70b          # smartest
DEVELOPER_MODEL=codestral-latest     # code expert
VALIDATOR_MODEL=mistral-7b           # balanced
```

---

## Available Models (All Free!)

**Lightweight** (fast, <15B params)
- `phi-3-mini` (3.8B)
- `phi-3-medium` (14B)
- `mistral-nemo` (12B)

**Mid-size** (balanced, 7-47B)
- `mistral-7b`
- `mistral-large` (47B)

**Large** (powerful, >47B)
- `llama-2-13b`
- `llama-2-70b` ⭐ Best reasoning
- `codestral-latest` ⭐ Best coding

---

## Model Selection by Priority

### 🏃 Speed First
```
SENTRY_MODEL=phi-3-mini
STRATEGIST_MODEL=phi-3-large
ARCHITECT_MODEL=mistral-7b
DEVELOPER_MODEL=mistral-7b
VALIDATOR_MODEL=phi-3-medium
```

### ⚖️ Balanced (Default)
```
SENTRY_MODEL=phi-3-medium
STRATEGIST_MODEL=mistral-7b
ARCHITECT_MODEL=llama-2-70b
DEVELOPER_MODEL=codestral-latest
VALIDATOR_MODEL=mistral-7b
```

### 🧠 Quality First
```
SENTRY_MODEL=phi-3-large
STRATEGIST_MODEL=mistral-large
ARCHITECT_MODEL=llama-2-70b
DEVELOPER_MODEL=codestral-latest
VALIDATOR_MODEL=mistral-large
```

---

## Agent Roles (Why These Models?)

| Agent | Role | Task | Model | Why? |
|-------|------|------|-------|------|
| 🔍 Sentry | Gather data | Summarize commits, find relevant files | phi-3-medium | Fast, doesn't need deep reasoning |
| 🧠 Strategist | Classify issue | Bug type, severity, components | mistral-7b | Strong reasoning, understands Qiskit context |
| 📐 Architect | Plan fix | Trace dependencies, multi-file logic | llama-2-70b | Largest model = best for complex reasoning |
| 💻 Developer | Write code | Generate diffs, fix implementations | codestral-latest | Code-specialized, produces clean patches |
| ✅ Validator | Test fix | Write tests, verify correctness | mistral-7b | Good at test synthesis & code review |

---

## Common Issues & Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| `GITHUB_MODELS_TOKEN not set` | Missing `.env` var | Add `GITHUB_MODELS_TOKEN=ghp_xxx` to `.env` |
| `Model not found` | Wrong model name | Check https://github.com/marketplace/models |
| `Rate limit exceeded` | >15 req/min | Automatic retry. Try faster models. |
| `Poor quality output` | Model too small | Use llama-2-70b instead of phi-3-mini |
| `Too slow` | Model too large | Use phi-3-medium or mistral-7b |

---

## Timing Expectations

```
Sentry (phi-3-medium)        ~5s   ████░░░░░░
Strategist (mistral-7b)     ~20s   █████████░
Architect (llama-2-70b)     ~45s   ██████████
Developer (codestral)       ~60s   ██████████
Validator (mistral-7b)      ~30s   █████████░
─────────────────────────────────────────────
TOTAL (1 iteration)        ~160s   (≈2.5 min)
```

With 3 repair iterations: ~5-7 minutes

---

## Migration from Gemini

```python
# OLD (Gemini)
from utils.config import get_gemini_api_key, get_model_name
key = get_gemini_api_key()
model = get_model_name()

# NEW (GitHub Models)
from utils.config import get_github_models_token, get_model_name
token = get_github_models_token()
model = get_model_name("sentry")  # agent-specific!
```

---

## Why GitHub Models > Gemini?

✅ **Free** - No API billing ever  
✅ **Open** - Community-driven, transparent  
✅ **Private** - Runs on Azure infrastructure  
✅ **Fast** - Optimized for inference  
✅ **Flexible** - Pick best model per agent  
✅ **Simple** - OpenAI-compatible API  

---

## Model Playground (Try Them!)

### Test Sentry (data gathering)
```bash
# Fast, good summarization
SENTRY_MODEL=phi-3-medium
```

### Test Strategist (analysis)
```bash
# Classic choice, excellent reasoning
STRATEGIST_MODEL=mistral-7b
# Or try: mistral-large (better)
```

### Test Architect (planning)
```bash
# Largest, best for complex logic
ARCHITECT_MODEL=llama-2-70b
# Or try: llama-2-13b (faster, decent)
```

### Test Developer (coding)
```bash
# Code specialist
DEVELOPER_MODEL=codestral-latest
# Or try: mistral-7b (faster, decent)
```

### Test Validator (testing)
```bash
# Good at writing tests
VALIDATOR_MODEL=mistral-7b
# Or try: phi-3-medium (faster)
```

---

## Advanced: Mix & Match

Pick different tiers for different agents:

**Fast Pipeline:**
```bash
SENTRY_MODEL=phi-3-mini
STRATEGIST_MODEL=phi-3-large
ARCHITECT_MODEL=mistral-7b
DEVELOPER_MODEL=mistral-7b
VALIDATOR_MODEL=phi-3-medium
# Total time: ~2 min
```

**Balanced Pipeline:**
```bash
SENTRY_MODEL=phi-3-medium
STRATEGIST_MODEL=mistral-7b
ARCHITECT_MODEL=llama-2-70b
DEVELOPER_MODEL=codestral-latest
VALIDATOR_MODEL=mistral-7b
# Total time: ~2.5 min
```

**High-Quality Pipeline:**
```bash
SENTRY_MODEL=phi-3-large
STRATEGIST_MODEL=mistral-large
ARCHITECT_MODEL=llama-2-70b
DEVELOPER_MODEL=codestral-latest
VALIDATOR_MODEL=mistral-large
# Total time: ~3.5 min
```

---

## Environment Variables Reference

```bash
# REQUIRED
GITHUB_MODELS_TOKEN=ghp_xxxxxxxxxxxx

# OPTIONAL (Per-Agent Models)
SENTRY_MODEL=phi-3-medium
STRATEGIST_MODEL=mistral-7b
ARCHITECT_MODEL=llama-2-70b
DEVELOPER_MODEL=codestral-latest
VALIDATOR_MODEL=mistral-7b

# OPTIONAL (Private Repos)
GITHUB_REPO_TOKEN=ghp_xxxxxxxxxxxx

# OPTIONAL (Qiskit Target)
QISKIT_REPO=Qiskit/qiskit

# OPTIONAL (Loop Iterations)
MAX_REPAIR_ITERATIONS=3
```

---

## Testing Your Setup

```bash
# Check token is set
echo $GITHUB_MODELS_TOKEN

# Check pip packages
pip list | grep openai

# Dry-run the sentry agent
python -c "
from agents.sentry import SentryAgent
s = SentryAgent()
print(f'Model: {s.llm.model_name}')
"
```

---

## Support

📖 **Full Guide:** See `GITHUB_MODELS_GUIDE.md`  
📝 **Migration Details:** See `MIGRATION_SUMMARY.md`  
🔗 **Models:** https://github.com/marketplace/models  
🆘 **Issues:** Check code comments in `utils/llm_client.py`  

---

**You're all set! 🚀**
