# Qiskit SWE-Agent Framework: Architecture, Workflow & Deep Dive

## Table of Contents
1. [Executive Overview](#executive-overview)
2. [What's New & Innovative](#whats-new--innovative)
3. [System Architecture](#system-architecture)
4. [Pipeline Workflow](#pipeline-workflow)
5. [Deep Dive: The Five Agents](#deep-dive-the-five-agents)
6. [Domain Knowledge Integration](#domain-knowledge-integration)
7. [Data Flow & Contracts](#data-flow--contracts)
8. [Repair Loop Mechanism](#repair-loop-mechanism)
9. [Key Design Patterns](#key-design-patterns)

---

## Executive Overview

The **Qiskit SWE-Agent Framework** is a sophisticated multi-agent orchestrator that **automatically converts GitHub issues into verified code patches** for the Qiskit quantum computing SDK. It represents a significant advancement over traditional single-LLM approaches by decomposing the problem into five specialized, domain-aware agents that work in a coordinated pipeline.

### Core Promise
- **Input**: A GitHub issue (description, labels, history)
- **Pipeline**: Five specialized agents analyze, plan, code, and validate
- **Output**: A production-ready patch + test coverage

### Philosophy
Rather than asking a single LLM to solve everything, this framework acknowledges that **different cognitive tasks require different specialized perspectives**:
- **Reconnaissance** (Sentry) → raw intelligence gathering
- **Triage** (Strategist) → domain-aware classification  
- **Planning** (Architect) → cross-file reasoning
- **Implementation** (Developer) → code generation
- **Verification** (Validator) → testing & quality assurance

---

## What's New & Innovative

### 1. **Qiskit Domain Encoding at Infrastructure Level**
Unlike generic software engineering agents, this framework **bakes in 13+ modules of Qiskit-specific knowledge** into the system itself:

- **40+ gate definitions** with unitarity checks
- **8 common Qiskit bug patterns** (transpiler pass ordering, parameter binding failures, etc.)
- **Quantum floating-point tolerance rules** (atol=1e-10, rtol=1e-7)
- **User-error vs. library-bug heuristics** (6 signals each way)
- **Transpiler pass category taxonomy** with interdependency mapping

This means agents don't have to *learn* Qiskit patterns—they're pre-equipped with deep domain knowledge.

### 2. **User-Error Gating**
The pipeline includes an early-exit gate:
- If the Strategist detects this is a user misunderstanding (not a library bug), the pipeline stops and provides remedial advice
- This prevents waste of compute on unsolvable issues

### 3. **Iterative Repair Loop**
Code generation is not one-shot:
- The **Developer** generates patches
- The **Validator** tests and validates them
- If tests fail, the Validator sends **structured, actionable feedback**
- The Developer iterates (configurable max iterations, default 3)
- Loop continues until tests pass

### 4. **Cross-Module Dependency Reasoning**
The Architect doesn't just localize a bug—it reasons about cascading impacts:
```
"If I change the gate definition in qiskit/circuit/library/,  
 I MUST also update the transpiler's basis_set logic  
 in qiskit/transpiler/passes/basis/."
```

### 5. **Structured Agent Contracts**
Every agent outputs **Pydantic models**, not unstructured text:
- Clear data validation between pipeline stages
- Type safety ensures agents don't pass malformed data downstream
- The Orchestrator validates all data flowing through the pipeline

### 6. **Quantum-Specific Code Generation**
The Developer agent understands:
- Gate vs. Instruction taxonomy
- Floating-point tolerance in statevector/operator comparisons
- Parameter binding consistency
- Rust↔Python boundary concerns

---

## System Architecture

### High-Level Component Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                    QISKIT SWE-AGENT FRAMEWORK                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          CENTRAL MANAGER (Orchestrator)                  │  │
│  │  ─────────────────────────────────────────────────────   │  │
│  │  • Coordinates the agent pipeline                        │  │
│  │  • Manages pipeline state & phase transitions            │  │
│  │  • Handles repair loop iterations                        │  │
│  │  • Validates data contracts between agents               │  │
│  │  • Renders rich terminal UI                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐              │
│         │                    │                    │              │
│         ▼                    ▼                    ▼              │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │   AGENTS    │    │   DOMAIN    │    │   UTILS     │        │
│   ├─────────────┤    ├─────────────┤    ├─────────────┤        │
│   │ • Sentry    │    │ • models.py │    │ • config.py │        │
│   │ • Strategist│    │ • qiskit_   │    │ • llm_      │        │
│   │ • Architect │    │   knowledge │    │   client.py │        │
│   │ • Developer │    │             │    │ • github_   │        │
│   │ • Validator │    │             │    │   helper.py │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Layer 1: Orchestrator (`orchestrator/`)
- **manager.py**: The `CentralManager` class
  - Instantiates all five agents
  - Orchestrates the execution sequence
  - Handles phase transitions (TRIAGE → PLANNING → CODING → VALIDATING)
  - Implements repair loop logic
  - Exports results as JSON or patches

- **cli.py**: Command-line interface
  - Parses `--repo`, `--issue`, `--agent`, `--output`, `--json-output` arguments
  - Entry point: `python main.py --repo Qiskit/qiskit --issue 12345`

### Layer 2: Agents (`agents/`)
Five specialized agents inheriting from `BaseAgent`:

1. **base_agent.py**: Abstract base class
   - Unified LLM access via `LLMClient`
   - Abstract methods: `system_prompt`, `build_user_prompt()`, `parse_response()`
   - Convenience: `call_llm_json()`, `call_llm_text()`

2. **sentry.py**: 🔍 Reconnaissance
   - Fetches issue data from GitHub
   - Maps repository structure
   - Finds related issues & recent commits
   - Returns: `SentryOutput`

3. **strategist.py**: 🧠 Triage
   - Classifies issue type (Bug, Feature, Quantum Correctness, etc.)
   - Identifies affected Qiskit modules
   - Detects user errors vs. library bugs
   - Returns: `StrategistOutput`

4. **architect.py**: 📐 Planning
   - Localizes bugs to specific files
   - Reasons about cross-file dependencies
   - Creates step-by-step implementation plan
   - Returns: `ArchitectOutput`

5. **developer.py**: 💻 Implementation
   - Generates unified diffs for each file change
   - Handles iterative repair feedback
   - Returns: `DeveloperOutput`

6. **validator.py**: ✅ Verification
   - Reviews code changes
   - Writes test cases
   - Validates quantum correctness
   - Returns: `ValidatorOutput`

### Layer 3: Domain Knowledge (`domain/`)

- **models.py** (327 lines)
  - Pydantic models for all agent contracts
  - Enumerations: `IssueType`, `Severity`, `QiskitModule`, `PipelineStatus`, etc.
  - Structures: `SentryOutput`, `StrategistOutput`, `ArchitectOutput`, `DeveloperOutput`, `ValidatorOutput`, `PipelineRun`

- **qiskit_knowledge.py** (396 lines)
  - **13 Qiskit module descriptions** with risk profiles
  - **40+ gate definitions** with unitarity rules
  - **8 common bug patterns** (gate decomposition mismatch, parameter binding failures, etc.)
  - **User-error signals** (6 heuristics that point to user misunderstanding)
  - **Library-bug signals** (6 heuristics that point to actual library issues)
  - **Transpiler pass categories** (analysis, transformation, routing, layout, scheduling, basis_change)
  - **Quantum floating-point precision constants** (atol=1e-10, rtol=1e-7)
  - **Testing conventions** (pytest paths, tolerance rules)

### Layer 4: Utilities (`utils/`)

- **config.py**: Environment variable loading
  - `GEMINI_API_KEY`, `MODEL_NAME`, `GITHUB_TOKEN`, `MAX_REPAIR_ITERATIONS`

- **llm_client.py**: Unified LLM wrapper
  - Abstracts Gemini API
  - `generate_json()`, `generate_text()` methods
  - Retry logic with `tenacity`

- **github_helper.py**: GitHub REST API utilities
  - `fetch_issue()`, `fetch_repo_tree()`, `fetch_file_content()`
  - `fetch_recent_commits()`, `search_related_issues()`

- **aci_tools.py**: Agent-Computer Interface
  - Sandboxed tool calls for agents (e.g., run tests, execute code patterns)

---

## Pipeline Workflow

### The Five-Phase Pipeline

```
GitHub Issue
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: RECONNAISSANCE (Sentry)                                │
│ ───────────────────────────────────────────────────────────────│
│ Task: Gather raw intelligence                                  │
│ • Fetch GitHub issue (title, body, labels, comments)          │
│ • Map repository file tree                                     │
│ • Find related issues (keyword search)                         │
│ • Retrieve recent commits for change context                  │
│ Output: SentryOutput { issue_data, repo_structure, ... }      │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: ISSUE TRIAGE (Strategist)                              │
│ ───────────────────────────────────────────────────────────────│
│ Task: Perform Qiskit-domain-aware classification               │
│ • Classify issue type (Bug, Quantum Correctness, etc.)         │
│ • Identify affected Qiskit modules                              │
│ • Map to domain concepts (Gate Definition, Transpilation)     │
│ • Detect user errors using heuristic signals                  │
│ • Flag Rust-layer involvement                                  │
│ Output: StrategistOutput { issue_type, modules, severity, ... }│
│                                                                  │
│ ⚠️  DECISION GATE: Is this a user error?                       │
│     → YES: STOP pipeline, provide remedial advice             │
│     → NO: Continue to Architect                               │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼ (only if NOT user error)
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: IMPLEMENTATION PLANNING (Architect)                    │
│ ───────────────────────────────────────────────────────────────│
│ Task: Create detailed cross-file implementation plan            │
│ • Localize bug to specific files & line ranges                │
│ • Fetch source code for context                                │
│ • Reason about cross-module dependencies                       │
│ • Create step-by-step PlanSteps                               │
│ • Identify affected test files                                 │
│ • Flag transpiler/circuit consistency risks                   │
│ Output: ArchitectOutput { file_locations, plan_steps, ... }    │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: CODE GENERATION (Developer)                            │
│ ───────────────────────────────────────────────────────────────│
│ Task: Implement fixes following Architect's plan                │
│ • Fetch actual source code                                      │
│ • Generate unified diffs for each file                          │
│ • Follow Architect's PlanSteps sequentially                    │
│ • Respect Qiskit coding conventions                             │
│ • Handle gate unitarity & parameter binding                    │
│ Output: DeveloperOutput { code_changes: [CodeChange], ... }    │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 5: VALIDATION (Validator)                                 │
│ ───────────────────────────────────────────────────────────────│
│ Task: Verify fix correctness                                    │
│ • Review code changes for logical correctness                  │
│ • Write new pytest test cases                                   │
│ • Check floating-point precision (atol, rtol)                 │
│ • Validate transpiler round-trip consistency                   │
│ • Gate unitary checks                                           │
│ Output: ValidatorOutput { is_valid, test_results, feedback }   │
│                                                                  │
│ ⚠️  DECISION GATE: All tests pass?                             │
│     → YES: ✅ Patch approved → FINAL PATCH                     │
│     → NO: 🔄 Send feedback to Developer (repair loop)          │
└─────────────────────────────────────────────────────────────────┘
     │
     ├─ (if tests fail and iterations < max)
     │    │
     │    ▼──────────────┐
     │                   │ (Developer receives feedback)
     │                   │
     │    ┌──────────────┘
     │    │
     │    ▼
     │ ┌─────────────────────────────────────────────────────────┐
     │ │ REPAIR LOOP: Developer ⇄ Validator (max 3 iters)       │
     │ │ • Developer refines code based on test feedback        │
     │ │ • Validator re-tests                                   │
     │ │ • Repeat until tests pass OR max iterations reached   │
     │ └─────────────────────────────────────────────────────────┘
     │    │
     └────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ FINAL OUTPUT                                                     │
│ ───────────────────────────────────────────────────────────────│
│ • PipelineRun { all agent outputs, final_patch, status }      │
│ • Unified diff (git apply compatible)                           │
│ • JSON export of full run (for evaluation)                      │
│ • Test results & validation summary                             │
└─────────────────────────────────────────────────────────────────┘
```

### Pipeline State Transitions

```python
PipelineStatus:
  PENDING      → Issue received, not yet started
  TRIAGE       → Sentry gathering intelligence
  PLANNING     → Architect creating plan
  CODING       → Developer generating patches
  VALIDATING   → Validator testing fixes
  REVIEWING    → (Reserved for human-in-loop future)
  COMPLETED    → ✅ Patch approved
  FAILED       → ❌ Pipeline errored or max iterations exceeded
```

---

## Deep Dive: The Five Agents

### Agent 1: The Sentry 🔍 (Reconnaissance)

**Role**: Gather raw intelligence about the repository and issue without analysis.

**Inputs**:
- GitHub repository (owner/name)
- Issue number

**Process**:
1. Call GitHub API to fetch issue metadata:
   - Title, body, labels, state, assignees
   - Comments and discussion history
   - Related PRs (if any)

2. Map repository structure:
   - Fetch top-level directory tree
   - Identify key source directories
   - Calculate repository size/complexity

3. Find contextual information:
   - Recent commits affecting relevant files
   - Related/duplicate issues (keyword search)
   - PR review comments (if applicable)

4. LLM-assisted summarization:
   - Distill recent commit messages
   - Identify structurally relevant directories

**Output: `SentryOutput`**
```python
SentryOutput:
  issue_data: GitHubIssueData
    - title, body, labels
    - author, creation_date
    - comments (full thread)
  repo_structure: dict
    - directory tree
    - key file locations
  recent_commits: list[CommitInfo]
    - hash, message, author, timestamp
  related_issues: list[IssueReference]
    - title, url, relevance score
  repo_health_notes: str
    - "Recent activity in transpiler passes"
```

**Key Code Pattern**:
```python
# From sentry.py
def run(self, repo: str, issue_number: int) -> SentryOutput:
    # 1. Fetch issue
    issue_data = fetch_issue(repo, issue_number)
    # 2. Map repo
    repo_structure = fetch_repo_tree(repo)
    # 3. Get commits
    commits = fetch_recent_commits(repo, limit=20)
    # 4. LLM summarizes
    summary = self.call_llm_json(self.build_user_prompt(...))
    # 5. Return structured output
    return SentryOutput(...)
```

**Why This Agent?**
- Separates raw data gathering from analysis
- Avoids wasting LLM compute on structured GitHub API calls
- Provides the complete context for downstream agents

---

### Agent 2: The Strategist 🧠 (Triage)

**Role**: Perform Qiskit-domain-aware classification and detect user errors early.

**Inputs**:
- Issue data (from Sentry)
- Repository structure (from Sentry)
- Recent commits (from Sentry)

**Process**:
1. Extract technical clues:
   - Stack traces, error messages
   - Affected files mentioned in issue
   - Keyword patterns (e.g., "transpiler", "gate", "parameter")

2. Classify using Qiskit domain knowledge:
   - **Issue Type**: Bug, Feature Request, Quantum Correctness, Deprecation, etc.
   - **Affected Modules**: Which Qiskit modules (circuit, transpiler, quantum_info, etc.)
   - **Domain Concepts**: Gate Definition, Transpilation Pass, Qubit Mapping, etc.
   - **Severity & Priority**: Based on risk profiles

3. User-Error Detection Gate ⚠️:
   - Apply **6 user-error heuristics**:
     - "Issue shows confusion about gate parameters"
     - "Stack trace indicates user code error"
     - "Issue asks 'is this expected behavior?' (suggests confusion)"
     - "No code shared; user trying to understand API"
     - "Error message matches known API misunderstanding"
     - "Discussion shows expert guidance resolves the issue"
   
   - Apply **6 library-bug heuristics**:
     - "Issue includes minimal reproducible example (MRE) from library code"
     - "Stack trace at C/Rust layer"
     - "Multiple users report same error"
     - "Behavior contradicts documentation"
     - "Error in critical path (transpiler, circuit, synthesis)"
     - "Issue references specific Qiskit version regression"

4. Flag special concerns:
   - Rust accelerator layer involvement (changes in `crates/`)
   - Floating-point precision criticality

**Output: `StrategistOutput`**
```python
StrategistOutput:
  issue_type: IssueType  # Bug, Quantum Correctness, etc.
  severity: Severity     # Critical, High, Medium, Low
  priority: Priority     # P0, P1, P2, P3
  affected_modules: list[QiskitModule]  # [circuit, transpiler]
  domain_concepts: list[QiskitDomainConcept]  # [Gate Definition, ...]
  is_user_error: bool    # ⚠️ Decision gate
  user_error_reason: str # (if is_user_error=True)
  confidence: Confidence # High, Medium, Low
  rust_layer_involved: bool
  quantum_precision_critical: bool
  analysis_summary: str
```

**The User-Error Gate** (Critical Innovation):
```python
if strategist_output.is_user_error:
    print("⚠️  This is a user misunderstanding, not a library bug.")
    print(f"Advice: {strategist_output.user_error_reason}")
    exit()  # Stop pipeline early
else:
    continue_to_architect()
```

---

### Agent 3: The Architect 📐 (Planning)

**Role**: Create a detailed, cross-file implementation plan with dependency reasoning.

**Inputs**:
- Strategist's triage (issue type, affected modules)
- Sentry's issue data & repository structure
- Source code files (fetched on-demand)

**Process**:

1. **Bug Localization**:
   - Use Strategist's module hints to search source code
   - Narrow down to specific files (e.g., `qiskit/circuit/library/standard_gates/x.py`)
   - Fetch actual source code for context
   - Identify exact line ranges

2. **Cross-File Dependency Reasoning**:
   - Map which other files depend on changes
   - Example: "If I fix gate unitarity in `library/`, I must update:
     - Transpiler basis_set logic in `passes/basis/`
     - Synthesis unitary checks in `synthesis/`
     - Tests in `test/`"

3. **Implementation Planning**:
   - Break down the fix into step-by-step `PlanStep`s
   - Each step: "Modify file X, change lines Y-Z, reason: R"
   - Foresee potential issues (e.g., "Watch for floating-point precision here")

4. **Test Identification**:
   - Identify which test files need to run
   - Flag any special test setup requirements

**Output: `ArchitectOutput`**
```python
ArchitectOutput:
  file_locations: list[FileLocation]
    - path: "qiskit/circuit/library/standard_gates/x.py"
    - lines_affected: (42, 78)
    - risk_level: HIGH
  plan_steps: list[PlanStep]
    - step_num: 1
    - file: "qiskit/circuit/library/standard_gates/x.py"
    - action: "Refactor X gate decomposition"
    - reason: "Current decomposition is incorrect for 1-qubit unitaries"
    - dependencies: ["defines X gate", "used by transpiler"]
  affected_test_files: ["test/unit/circuit/library/standard_gates/test_x.py"]
  cross_module_warnings: ["Transpiler basis_set may need update"]
  implementation_notes: str
```

**Key Innovation: Dependency Reasoning**
```
"If I change X:
  - File A depends on X (must update)
  - File B uses X transitively (watch for regression)
  - Tests for A, B, and X must all pass"
```

---

### Agent 4: The Developer 💻 (Code Generation)

**Role**: Write precise, minimal, correct code patches following the Architect's plan.

**Inputs**:
- Architect's plan (PlanSteps)
- Strategist's triage (for context)
- Source code (fetched for each file)

**Process**:

1. **Plan Execution**:
   - Iterate through Architect's `PlanStep`s sequentially
   - For each step, fetch the source file
   - Understand the current implementation

2. **Code Generation**:
   - Fix the issue following the PlanStep
   - Produce a unified diff (git-format)
   - Keep changes minimal (avoid unnecessary refactoring)

3. **Qiskit-Specific Concerns**:

   **Gate Unitary Correctness**:
   - Verify that fixed gate definition matches gate unitary
   - Example: If changing `X` gate decomposition, verify:
     ```python
     np.allclose(Operator(fixed_X_gate).data, 
                 Operator([RZ, SX, RZ, ...]).data)
     ```

   **Parameter Binding**:
   - Ensure parameter substitution is consistent
   - Handle `ParameterVector` and `ParameterExpression` correctly

   **Floating-Point Tolerance**:
   - Use `np.allclose(a, b, atol=1e-10, rtol=1e-7)` for quantum comparisons
   - Never use exact equality (`==`) for floats

   **Python↔Rust Boundary**:
   - If changes touch `_accelerate` crates, note recompilation needed
   - Test round-trip through Python/Rust boundary

4. **Iteration Support**:
   - Accept ValidatorOutput with test failures
   - Parse feedback and refine code
   - Jump back to step 1 with refined understanding

**Output: `DeveloperOutput`**
```python
DeveloperOutput:
  code_changes: list[CodeChange]
    - file_path: "qiskit/circuit/library/standard_gates/x.py"
    - unified_diff: "--- a/...\n+++ b/...\n@@ ..."
    - change_description: "Fix X gate unitary consistency"
  summary: str  # "Modified 2 files, 45 lines changed"
  iteration_count: int
```

**Repair Loop Pattern**:
```python
iteration = 0
while iteration < max_iterations:
    developer_output = developer.run(
        architect_output, 
        strategist_output, 
        validator_feedback  # None on first iteration
    )
    validator_output = validator.run(developer_output, ...)
    
    if validator_output.is_valid:
        return developer_output  # ✅ Success!
    else:
        iteration += 1
        validator_feedback = validator_output.feedback
        # Loop back to Developer with feedback
```

---

### Agent 5: The Validator ✅ (Verification)

**Role**: Verify code correctness, write tests, and provide actionable repair feedback.

**Inputs**:
- Developer's code changes (DeveloperOutput)
- Architect's plan (for context)
- Strategist's triage (for context)

**Process**:

1. **Code Review**:
   - Analyze Developer's diffs for logical correctness
   - Check Qiskit conventions compliance
   - Flag any obvious issues

2. **Test Analysis**:
   - Identify which existing tests are affected
   - Determine test requirements from Architect's plan
   - Design new test cases

3. **Test Case Writing**:
   - Write pytest test cases for the fix
   - Include Qiskit-specific validations:
     - Gate unitary checks
     - Floating-point tolerance assertions
     - Transpiler round-trip tests

4. **Quantum-Specific Validation**:
   - **Floating-Point Precision**:
     ```python
     # ✅ Correct
     assert np.allclose(sv1, sv2, atol=1e-10, rtol=1e-7)
     # ❌ Wrong
     assert (sv1 == sv2).all()
     ```
   
   - **Gate Unitary Consistency**:
     ```python
     gate = XGate()
     assert_gates_equivalent(gate, gate.definition)
     ```
   
   - **Parameter Binding Round-Trip**:
     ```python
     theta = Parameter('θ')
     qc_param = QuantumCircuit(1)
     qc_param.rz(theta, 0)
     qc_bound = qc_param.bind_parameters({theta: 0.5})
     # Verify binding succeeded
     ```

5. **Feedback Generation** (if tests fail):
   - Parse test output
   - Identify failure reasons
   - Generate structured feedback with:
     - Which tests failed
     - Why they failed (not just assertion message)
     - Actionable suggestions for Developer

**Output: `ValidatorOutput`**
```python
ValidatorOutput:
  is_valid: bool
  test_results: list[TestResult]
    - test_name: "test_xgate_unitary"
    - passed: bool
    - output: str
  written_tests: list[str]  # New test cases written
  feedback: str  # (if is_valid=False) Repair suggestions
  validation_summary: str
```

**Feedback Example** (if tests fail):
```
Feedback to Developer:
─────────────────────
[FAILED] test_xgate_transpilation
  Root cause: X gate definition doesn't match unitary.
  
[SUGGESTED FIX]
  The new decomposition produces a global phase shift.
  Revisit line 57 in x.py; remove the RZ(0) gate (unnecessary).

[ALSO CHECK]
  Parameter binding test_rz_parameter failed.
  Verify ParameterExpression substitution in line 42.
```

---

## Domain Knowledge Integration

### The `qiskit_knowledge.py` Knowledge Base (396 lines)

This module encodes tribal knowledge that would normally require hiring a senior Qiskit contributor. It's injected directly into agent system prompts.

#### 1. **Module Risk Map** (13 modules)
Each module includes: description, risk level, key files

```python
QISKIT_MODULE_MAP = {
    "qiskit/circuit": {  # RISK: HIGH
        "description": "Core quantum circuit representation...",
        "key_files": "quantumcircuit.py, gate.py, library/standard_gates/",
    },
    "qiskit/transpiler": {  # RISK: CRITICAL ⚠️
        "description": "Transpilation pipeline with interdependent passes...",
        "key_files": "passmanager.py, passes/optimization/, passes/routing/",
    },
    # + 11 more modules
}
```

#### 2. **Gate vs. Instruction Taxonomy**
Distinguishes 40+ gates from instructions with test implications:

```python
GATE_VS_INSTRUCTION = """
GATE: Unitary, reversible, matrix representable
  Example: XGate, RZGate, CXGate
  Testing: Can compare unitaries with np.allclose

INSTRUCTION: Non-unitary or circuit-scoped
  Example: Barrier, Delay, Reset, Measure
  Testing: Cannot use unitary comparison
"""
```

#### 3. **Common Qiskit Bug Patterns** (8 patterns)

```python
COMMON_BUG_PATTERNS = [
    {
        "pattern": "Gate Decomposition Inconsistency",
        "description": "Gate.definition doesn't match gate's unitary",
        "example": "X gate definition has wrong Euler angles",
        "symptom": "Transpiler produces wrong unitary circuit",
    },
    {
        "pattern": "Parameter Binding Failure",
        "description": "ParameterExpression not substituted correctly",
        "symptom": "Circuit with bound parameters produces wrong statevector",
    },
    # + 6 more patterns
]
```

#### 4. **User-Error vs. Library-Bug Signals** (6 each)

**User-Error Signals** (points to user misunderstanding):
- "Issue shows confusion about gate parameters"
- "Stack trace in user code (not Qiskit internals)"
- "Issue asks 'is this expected behavior?'"
- etc.

**Library-Bug Signals** (points to actual library issue):
- "Issue includes minimal reproducible example from library code"
- "Stack trace at C/Rust layer"
- "Multiple users report same error"
- etc.

#### 5. **Transpiler Pass Categories**

```python
TRANSPILER_PASS_CATEGORIES = {
    "analysis": "Read circuit without modification (e.g., Width, Size)",
    "transformation": "Modify circuit logic (e.g., Decompose, Unroll)",
    "routing": "Add SWAP gates for backend connectivity",
    "layout": "Assign qubits to physical qubits",
    "scheduling": "Insert delays between gates",
    "basis_change": "Convert to target basis set",
}
```

#### 6. **Quantum Floating-Point Precision Constants**

```python
QUANTUM_PRECISION = {
    "atol": 1e-10,  # Absolute tolerance
    "rtol": 1e-7,   # Relative tolerance
    "note": "Use np.allclose(a, b, atol=1e-10, rtol=1e-7)",
}
```

#### 7. **Testing Conventions**

```python
TESTING_CONVENTIONS = {
    "unit_tests": "test/unit/ — focused component tests",
    "integration_tests": "test/integration/ — cross-module tests",
    "tolerance": "atol=1e-10, rtol=1e-7 for quantum states",
    "pytest_markers": "@pytest.mark.slow, @slow_only",
}
```

### How Domain Knowledge Flows to Agents

Each agent's system prompt includes injected domain knowledge:

```python
# In strategist.py
@property
def system_prompt(self) -> str:
    module_summary = "\n".join(
        f"  • {mod}: {info['description']} (Risk: {info['risk']})"
        for mod, info in QISKIT_MODULE_MAP.items()
    )
    bug_patterns = "\n".join(f"  • {bp['pattern']}: ..." for bp in COMMON_BUG_PATTERNS)
    
    return f"""
You are The Strategist...

═══ QISKIT MODULES ═══
{module_summary}

═══ COMMON BUG PATTERNS ═══
{bug_patterns}

═══ USER-ERROR SIGNALS ═══
{user_error_signals}
...
"""
```

This ensures **every agent starts with deep Qiskit expertise** baked in.

---

## Data Flow & Contracts

### The Contract Between Agents

Each agent outputs a Pydantic model that the next agent consumes:

```
┌──────────────────┐
│ Sentry           │  inputs: repo, issue_number
│ ↓                │  outputs: SentryOutput
└──────────────────┘
         │
         V
┌──────────────────┐
│ Strategist       │  inputs: SentryOutput
│ ↓                │  outputs: StrategistOutput
└──────────────────┘
         │
         V (if not user error)
┌──────────────────┐
│ Architect        │  inputs: StrategistOutput, SentryOutput
│ ↓                │  outputs: ArchitectOutput
└──────────────────┘
         │
         V
┌──────────────────┐
│ Developer        │  inputs: ArchitectOutput, [ValidatorOutput?]
│ ↓                │  outputs: DeveloperOutput
└──────────────────┘
         │
         V
┌──────────────────┐
│ Validator        │  inputs: DeveloperOutput, ArchitectOutput
│ ↓                │  outputs: ValidatorOutput
└──────────────────┘
         │
         ├─ (is_valid=True) → Final Patch
         │
         └─ (is_valid=False, iterations < max)
            → Feedback loops to Developer
```

### Type Safety with Pydantic

All models inherit from `BaseModel` and enforce strict typing:

```python
# From domain/models.py
class StrategistOutput(BaseModel):
    issue_type: IssueType
    affected_modules: list[QiskitModule]
    is_user_error: bool
    severity: Severity
    priority: Priority
    confidence: Confidence
    # + more fields
```

The Manager validates: `StrategistOutput.parse_obj(raw_dict)` throws if schema mismatch.

---

## Repair Loop Mechanism

### Iteration Logic (Max 3 by default)

```python
# In manager.py
developer_outputs = []
validator_outputs = []

for iteration in range(self.max_iterations):
    print(f"\n[Iteration {iteration + 1}]")
    
    # Developer generates/refines code
    dev_output = self.developer.run(
        strategist_output=strategist_output,
        architect_output=architect_output,
        validator_feedback=validator_outputs[-1].feedback if validator_outputs else None,
    )
    developer_outputs.append(dev_output)
    
    # Validator tests the code
    val_output = self.validator.run(
        developer_output=dev_output,
        architect_output=architect_output,
        strategist_output=strategist_output,
    )
    validator_outputs.append(val_output)
    
    # Check success condition
    if val_output.is_valid:
        pipeline.final_patch = dev_output.code_changes
        pipeline.status = PipelineStatus.COMPLETED
        return pipeline
    
    # Log failure and continue loop if iterations remain
    console.print(f"  ⚠️  Tests failed. {self.max_iterations - iteration - 1} retries remaining.")
    console.print(f"  Feedback: {val_output.feedback}\n")

# If we exit the loop without success
pipeline.status = PipelineStatus.FAILED
pipeline.final_patch = None  # No valid patch
```

### Repair Feedback Structure

The Validator's feedback is **structured, not free-form**:

```python
class ValidatorOutput(BaseModel):
    is_valid: bool
    test_results: list[TestResult]
    feedback: str  # Actionable suggestions
    feedback_tags: list[str]  # e.g., ["floating_point", "unitary_mismatch"]
    suggestions: list[str]  # e.g., ["Check line 42", "Remove RZ(0) gate"]
```

Example:
```
feedback_tags: ["floating_point", "parameter_binding"]
suggestions: [
  "Use np.allclose with atol=1e-10, rtol=1e-7",
  "Parameter binding is failing; check ParameterExpression.substitution()"
]
```

The Developer uses these tags to focus refinement.

---

## Key Design Patterns

### Pattern 1: Template Method + Protocol Inheritance

```python
# BaseAgent establishes the template
class BaseAgent(ABC):
    @abstractmethod
    def system_prompt(self) -> str:
        ...
    
    @abstractmethod
    def build_user_prompt(self, **kwargs) -> str:
        ...
    
    @abstractmethod
    def parse_response(self, raw: dict) -> Any:
        ...
    
    # Template method: concrete, not overridden
    def call_llm_json(self, user_prompt: str):
        raw = self.llm.generate_json(user_prompt, self.system_prompt)
        return self.parse_response(raw)

# Each agent implements the three abstract methods
class SentryAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return "You are The Sentry..."
    
    def build_user_prompt(self, **kwargs) -> str:
        return f"Issue: {issue}, Recent commits: {commits}..."
    
    def parse_response(self, raw: dict) -> SentryOutput:
        return SentryOutput(**raw)
```

### Pattern 2: Pydantic-Based Data Validation

Every stage output is validated:

```python
try:
    strategist_output = StrategistOutput.parse_obj(llm_response)
except ValidationError as e:
    self.logger.error(f"Strategist output invalid: {e}")
    raise
```

This **prevents garbage data from flowing downstream**.

### Pattern 3: Early-Exit Gating

Strategic decision points stop the pipeline:

```python
if strategist_output.is_user_error:
    console.print("⚠️  User error detected. Pipeline stops.")
    return pipeline
```

### Pattern 4: Rich Terminal UI for Visibility

The Manager renders progress at every phase:

```python
def _print_phase(self, title: str, emoji: str):
    console.print(f"\n{emoji} {title}")
    console.print("─" * 60)

def _print_table(self, data):
    table = Table()
    table.add_column("Module", style="cyan")
    table.add_column("Risk", style="red")
    console.print(table)
```

Result: Beautiful, informative terminal output showing real-time progress.

### Pattern 5: Configuration-Driven Orchestration

All orchestration logic is configurable:

```python
# config.py
MAX_REPAIR_ITERATIONS = int(os.getenv("MAX_REPAIR_ITERATIONS", "3"))
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", None)
```

No hardcoded limits—easily adjustable for experimentation.

---

## Execution Flow Example

**User runs:**
```bash
python main.py --repo Qiskit/qiskit --issue 12345 --json-output result.json
```

**What happens:**

1. **CLI Parsing** (orchestrator/cli.py):
   - Parses `--repo`, `--issue`, `--json-output` flags
   - Instantiates `CentralManager()`

2. **Manager.run()** begins:
   - Creates `PipelineRun(run_id, repo, issue_number)`
   - Prints beautiful header with run details

3. **Phase 1 — Sentry** (2-5 seconds):
   - Fetches GitHub issue #12345
   - Maps Qiskit repo structure
   - Finds recent commits
   - Returns `SentryOutput`

4. **Phase 2 — Strategist** (3-10 seconds):
   - Analyzes issue using domain knowledge
   - Detects affected modules
   - Checks: is this a user error?
   - Returns `StrategistOutput`
   - If user error → **STOP**, print advice

5. **Phase 3 — Architect** (5-15 seconds):
   - Localizes bug to files & lines
   - Fetches source code
   - Reasons about cross-file impact
   - Creates step-by-step plan
   - Returns `ArchitectOutput`

6. **Phase 4-5 — Developer ⇄ Validator Loop**:
   - **Iteration 1**:
     - Developer generates patches (10-30 seconds)
     - Validator tests patches (5-10 seconds)
     - Tests fail? Continue loop
   - **Iteration 2**:
     - Developer refines based on feedback (10-30 seconds)
     - Validator re-tests (5-10 seconds)
     - Tests pass? → SUCCESS
   - **Exit** when tests pass OR max iterations reached

7. **Final Output**:
   - Writes unified diff to stdout (or `--output file`)
   - Writes JSON summary to `result.json`
   - Prints final summary table

**Total time**: 1-3 minutes for full pipeline (varies by issue complexity)

---

## Summary

The **Qiskit SWE-Agent Framework** represents a significant advancement in automated software engineering by:

1. **Decomposing the problem** into five specialized, well-defined roles
2. **Embedding domain expertise** (Qiskit knowledge) at the infrastructure level
3. **Implementing early-exit gating** to avoid wasting compute on unsolvable issues
4. **Using structured data contracts** (Pydantic models) for type-safe agent communication
5. **Enabling iterative refinement** through a Developer ⇄ Validator feedback loop
6. **Providing rich visibility** via beautiful terminal UI and JSON export

This is not a single-LLM black box—it's a **orchestrated multi-agent system** where each agent is an expert in its domain, and the Manager ensures they work together seamlessly to convert GitHub issues into verified, production-ready patches.

