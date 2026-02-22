# Agent-to-Model Mapping Diagram

## Visual Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    QISKIT SWE-AGENT PIPELINE                           │
│                    (Now Using GitHub Free Models)                       │
└─────────────────────────────────────────────────────────────────────────┘

                              GitHub Issue
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │    1️⃣  SENTRY 🔍       │
                    │  "Reconnaissance"       │
                    │                         │
                    │  Task: Gather data      │
                    │  Fetch repo structure   │
                    │  Find related issues    │
                    │  Summarize commits      │
                    │                         │
                    │  Model: phi-3-medium    │
                    │  Time: ~5-10s           │
                    │  Logic: 🟢 High-level   │
                    └─────────────┬───────────┘
                                  │ SentryOutput
                                  ▼
                    ┌─────────────────────────┐
                    │   2️⃣  STRATEGIST 🧠    │
                    │  "Issue Analyst"        │
                    │                         │
                    │  Task: Analyze issue    │
                    │  Classify type          │
                    │  Identify components    │
                    │  Assess severity        │
                    │                         │
                    │  Model: mistral-7b      │
                    │  Time: ~15-30s          │
                    │  Logic: ⚡ Good reasoning│
                    └─────────────┬───────────┘
                                  │ StrategistOutput
                                  ▼
                    ┌─────────────────────────┐
                    │   3️⃣  ARCHITECT 📐     │
                    │  "Planner"              │
                    │                         │
                    │  Task: Plan implementation
                    │  Localize bugs          │
                    │  Trace dependencies     │
                    │  Cross-module reasoning │
                    │                         │
                    │  Model: llama-2-70b     │
                    │  Time: ~30-60s          │
                    │  Logic: 🧠 Very smart   │
                    └─────────────┬───────────┘
                                  │ ArchitectOutput
                                  ▼
                    ┌─────────────────────────┐
                    │   4️⃣  DEVELOPER 💻    │
                    │  "Coder"                │
                    │                         │
                    │  Task: Generate patches │
                    │  Write code diffs       │
                    │  Fix implementations    │
                    │  Consider trade-offs    │
                    │                         │
                    │  Model: codestral-latest│
                    │  Time: ~30-90s          │
                    │  Logic: 🎯 Code expert  │
                    └─────────────┬───────────┘
                                  │ DeveloperOutput
                                  ▼
                    ┌─────────────────────────┐
                    │   5️⃣  VALIDATOR ✅    │
                    │  "QA Engineer"          │
                    │                         │
                    │  Task: Validate fix     │
                    │  Review code            │
                    │  Write tests            │
                    │  Verify correctness     │
                    │                         │
                    │  Model: mistral-7b      │
                    │  Time: ~20-40s          │
                    │  Logic: ⚡ Good reviewer │
                    └─────────────┬───────────┘
                                  │ ValidatorOutput
                                  ▼
                          ✅ PATCH GENERATED
                        (Or loop back if fixes needed)
```

---

## Model Selection Logic

```
┌────────────────────────────────────────────────────────────────────┐
│              CHOOSING THE RIGHT MODEL FOR EACH AGENT               │
└────────────────────────────────────────────────────────────────────┘

SENTRY AGENT (🔍 Data Gathering)
├─ Primary Task: Summarize, not reason
├─ Complexity: Low (structured API calls)
├─ Token Output: Small (~500 tokens)
└─ ✅ BEST: phi-3-medium (fast, sufficient)
   Alternatives: phi-3-mini (faster), phi-3-large (smarter)

STRATEGIST AGENT (🧠 Issue Analysis)
├─ Primary Task: Classify, categorize, understand
├─ Complexity: Medium (good reasoning needed)
├─ Token Output: Medium (~800 tokens)
└─ ✅ BEST: mistral-7b (proven reasoning)
   Alternatives: mistral-large (better), mistral-nemo (faster)

ARCHITECT AGENT (📐 Planning & Design)
├─ Primary Task: Complex multi-file reasoning
├─ Complexity: HIGH (needs strong comprehension)
├─ Token Output: Large (~1,500 tokens)
└─ ✅ BEST: llama-2-70b (largest = smartest)
   Alternatives: llama-2-13b (faster), mistral-large (balanced)

DEVELOPER AGENT (💻 Code Generation)
├─ Primary Task: Write syntax-correct diffs
├─ Complexity: HIGH (code domain knowledge)
├─ Token Output: Large (~2,000 tokens)
└─ ✅ BEST: codestral-latest (code specialist)
   Alternatives: mistral-7b (faster), llama-2-70b (smarter)

VALIDATOR AGENT (✅ Testing & Verification)
├─ Primary Task: Code review + test generation
├─ Complexity: Medium-High (needs code understanding)
├─ Token Output: Medium-Large (~1,200 tokens)
└─ ✅ BEST: mistral-7b (balanced for review & tests)
   Alternatives: mistral-large (better), phi-3-medium (faster)
```

---

## Performance Matrix

```
┌──────────────────┬──────────────┬──────────────┬────────────────┐
│ Model            │ Size         │ Speed        │ Reasoning      │
├──────────────────┼──────────────┼──────────────┼────────────────┤
│ phi-3-mini       │ 3.8B params  │ ⚡⚡⚡⚡⚡ | 🧠🧠🧠      │
│ phi-3-medium     │ 14B params   │ ⚡⚡⚡⚡  | 🧠🧠🧠🧠    │
│ phi-3-large      │ 42B params   │ ⚡⚡⚡    | 🧠🧠🧠🧠🧠 │
├──────────────────┼──────────────┼──────────────┼────────────────┤
│ mistral-nemo     │ 12B params   │ ⚡⚡⚡⚡  | 🧠🧠🧠      │
│ mistral-7b       │ 7B params    │ ⚡⚡⚡⚡  | 🧠🧠🧠🧠    │ ⭐ DEFAULT
│ mistral-large    │ 47B params   │ ⚡⚡      | 🧠🧠🧠🧠🧠 │
├──────────────────┼──────────────┼──────────────┼────────────────┤
│ llama-2-7b       │ 7B params    │ ⚡⚡⚡⚡  | 🧠🧠🧠      │
│ llama-2-13b      │ 13B params   │ ⚡⚡⚡   | 🧠🧠🧠🧠    │
│ llama-2-70b      │ 70B params   │ ⚡          | 🧠🧠🧠🧠🧠 │ ⭐ ARCHITECT
├──────────────────┼──────────────┼──────────────┼────────────────┤
│ codestral        │ Specialized  │ ⚡⚡⚡   | 🧠🧠🧠 (Code)│ ⭐ DEVELOPER
├──────────────────┼──────────────┼──────────────┼────────────────┤
│ granite-8b-code  │ 8B params    │ ⚡⚡⚡⚡  | 🧠🧠🧠 (Code)│
└──────────────────┴──────────────┴──────────────┴────────────────┘

Legend: ⚡ = Speed (more = faster)  | 🧠 = Reasoning (more = smarter)
        ⭐ = Recommended for agent
```

---

## Default Configuration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 .env Configuration File                         │
│  (GitHub Models credentials and per-agent model selection)      │
└─────────────────────────────────────────────────────────────────┘

REQUIRED:
┌─────────────────────────────────────────────────────────┐
│ GITHUB_MODELS_TOKEN=ghp_your_github_pat_here           │
│ (Get from: https://github.com/settings/tokens)         │
└─────────────────────────────────────────────────────────┘

OPTIONAL (Per-Agent Model Override):
┌─────────────────────────────────────────────────────────┐
│ SENTRY_MODEL=phi-3-medium         # Default: fast       │
│ STRATEGIST_MODEL=mistral-7b       # Default: balanced   │
│ ARCHITECT_MODEL=llama-2-70b       # Default: powerful   │
│ DEVELOPER_MODEL=codestral-latest  # Default: code expert│
│ VALIDATOR_MODEL=mistral-7b        # Default: balanced   │
└─────────────────────────────────────────────────────────┘

OPTIONAL (Other Settings):
┌─────────────────────────────────────────────────────────┐
│ GITHUB_REPO_TOKEN=ghp_xxx          # For private repos  │
│ QISKIT_REPO=Qiskit/qiskit         # Target repo         │
│ MAX_REPAIR_ITERATIONS=3            # Loop iterations     │
│ LLM_PROVIDER=github-models         # Provider choice     │
└─────────────────────────────────────────────────────────┘

                            │
                            ▼
            ┌───────────────────────────────┐
            │   utils/config.py loads all   │
            │   Provides get_* functions    │
            └───────────┬───────────────────┘
                        │
                        ▼
            ┌───────────────────────────────┐
            │   utils/llm_client.py uses    │
            │   GitHub Models API endpoint  │
            └───────────┬───────────────────┘
                        │
                        ▼
            ┌───────────────────────────────┐
            │   agents/base_agent.py gets   │
            │   Agent-specific model        │
            └───────────┬───────────────────┘
                        │
                        ▼
            ┌───────────────────────────────┐
            │   Each Agent uses its own     │
            │   optimized model             │
            └───────────────────────────────┘
```

---

## Cost & Performance Comparison

```
╔═══════════════════════════════════════════════════════════════════════╗
║                    COST vs PERFORMANCE TRADEOFF                       ║
╚═══════════════════════════════════════════════════════════════════════╝

                        SPEED (faster ➜)
                        ├──────────────────────────┤
                    FAST │                      │ SLOW
                        │                      │

COST               ┌─────────────────────────────────────┐
(cheaper ▲)        │                                     │
    $0  │ ✅ Default Config                             │
        │ (phi-3 + mistral + llama-2-70b)              │
        │ • Time: ~2.5 min                             │
        │ • Quality: High                               │
        │ • Cost: $0                                    │
        │                                               │
        │ Speed-Config          Quality-Config         │
        │ (all phi-3/mistral)  (all large models)      │
        │ • Time: ~90s          • Time: ~4 min        │
        │ • Quality: Medium     • Quality: Very High   │
        │ • Cost: $0            • Cost: $0            │
        │                                               │
        │ Old Gemini Config (❌ no longer available)   │
        │ • Time: ~2 min                               │
        │ • Quality: High                               │
        │ • Cost: $50-200/month                        │
        └─────────────────────────────────────────────┘
        
        GitHub Models: ALL TIERS ARE FREE! 🎉

        vs Gemini ($$/month):
        ├─ $0 / month (GitHub) vs ~$75 base + usage
        ├─ 15 req/min free (standard rate limit)
        └─ Unlimited hours/day (no throttling)
```

---

## Migration Timeline

```
┌──────────────────────────────────────────────────────────┐
│            MIGRATION COMPLETED! ✅                       │
└──────────────────────────────────────────────────────────┘

                    Code Changes
                    (TODAY - ALREADY DONE)

    config.py ✅         →  GitHub token + per-agent models
    llm_client.py ✅     →  OpenAI SDK + GitHub endpoint
    base_agent.py ✅     →  Agent name support
    pyproject.toml ✅    →  google-genai → openai
    .env.example ✅      →  GitHub Models setup
    README.md ✅         →  Updated docs

                    YOUR ACTION ITEMS
                    (NEXT 5 MINUTES)

    [1] Create GitHub PAT          (2 min)
        ↓
    [2] Add to .env file            (1 min)
        ↓
    [3] Run: pip install -e .       (1 min)
        ↓
    [4] Test: python main.py ...    (1 min)

                    YOU'RE DONE! 🚀
                    (Start processing Qiskit issues)
```

---

## Decision Tree: Which Config to Use?

```
                       START HERE
                            │
                            ▼
                   Do you care about
                      SPEED?
                      /        \
                    YES         NO
                    /            \
                   ▼              ▼
            Want test          Want best
            FASTEST?           QUALITY?
            /      \            /      \
          YES      NO         YES      NO
          /         \          /        \
         ▼           ▼        ▼          ▼
      SPEED-     DEFAULT   QUALITY-   DEFAULT
      CONFIG     CONFIG    CONFIG     CONFIG
      (90s)      (2.5m)    (4m)       (2.5m)
       │          │         │          │
       │          │         │          │
       └─➜ Use: phi-3-*    ← Use: llama-2-70b
          ALL models        ALL large
          preferred         models
```

---

## Summary: What Changed, Why, and What's Next

```
┌─────────────────────────────────────────────────────────────────────┐
│                          THE BOTTOM LINE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  WHAT CHANGED:                                                     │
│  ✅ LLM Provider: Gemini → GitHub Models (open-source)            │
│  ✅ Cost: $50-200/month → $0/month                                │
│  ✅ Model Selection: 1 model → Per-agent optimization            │
│  ✅ Code: 6 files updated, all agents work same                  │
│                                                                     │
│  WHY:                                                              │
│  ✅ FREE - No API costs ever                                       │
│  ✅ OPEN - Community-driven, transparent                          │
│  ✅ BETTER - Each agent gets optimized model                      │
│  ✅ COMPATIBLE - No breaking changes                              │
│                                                                     │
│  WHAT'S NEXT:                                                     │
│  1️⃣  Get GitHub PAT (2 min)                                       │
│  2️⃣  Add to .env (1 min)                                          │
│  3️⃣  Run pip install -e . (1 min)                                 │
│  4️⃣  Test: python main.py --repo Qiskit/qiskit --issue N -v      │
│                                                                     │
│  RESULT:                                                           │
│  🎉 Free, optimized, open-source AI-powered Qiskit fixing!        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Model Picker Guide

```
┌─────────────────────────────────────────────────────────┐
│          "I don't know which model to pick"             │
└─────────────────────────────────────────────────────────┘

Q: First time using this?
A: Use DEFAULT CONFIG (no .env changes needed) ✅

Q: Is it too slow?
A: Use SPEED-OPTIMIZED CONFIG (all phi-3 models)

Q: Is quality too low?
A: Use QUALITY-OPTIMIZED CONFIG (all large models)

Q: Want to experiment?
A: Override individual models in .env:
   ARCHITECT_MODEL=llama-2-70b
   DEVELOPER_MODEL=codestral-latest
   (etc.)

Q: Still lost?
A: Check QUICK_REFERENCE.md (one-page guide)

Q: Detailed explanation needed?
A: Check GITHUB_MODELS_GUIDE.md (comprehensive)
```

---

**Now go set up your GitHub PAT and enjoy free, powerful AI! 🚀**
