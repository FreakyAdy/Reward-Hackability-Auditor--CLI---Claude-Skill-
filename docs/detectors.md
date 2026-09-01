# Detector Architecture & Mathematical Specifications

This document provides the formal detection specification, abstract syntax tree (AST) matching logic, and scoring formulas implemented across `ratctl`'s static detection engine.

---

## 1. Mathematical Scoring Engine

`ratctl` maps detected exploit severity weights to a normalized **Gameability Score** $G \in [0, 100]$ using a soft-clipping exponential sigmoid:

$$S_{\text{raw}} = \sum_{k \in \mathcal{E}} W(k) \times N(k)$$

Where $\mathcal{E}$ is the set of active findings, $W(k)$ is the severity weight assigned to finding $k$, and $N(k)$ is the finding frequency count. The weights for severities are defined as:

$$\text{Weight}(\text{CRITICAL}) = 1.0, \quad \text{Weight}(\text{HIGH}) = 0.6, \quad \text{Weight}(\text{MEDIUM}) = 0.35, \quad \text{Weight}(\text{LOW}) = 0.15, \quad \text{Weight}(\text{INFO}) = 0.05$$

The final score is computed as:

$$G = \text{min}\left(100, \text{round}\left(100 \times \left(1 - e^{-S_{\text{raw}} / 7.5}\right)\right)\right)$$

### Verification Threshold Gating

When running CI quality gates (`--fail-on 'gameability>0.3'`), `ratctl` computes the normalized metric $g = G / 100.0$. If $g > 0.30$, `ratctl` exits with exit code `1` (fail-closed).

---

## 2. Exploit Class Specifications

`ratctl` implements 6 peer-reviewed detector modules targeting distinct reward-hacking vectors:

```text
+-----------------------------------------------------------------------------------+
|                            DETECTOR MODULE MATRIX                                 |
+------------------------------+---------------------------+------------------------+
| Detector Module              | AST Node Target           | Severity Level         |
+------------------------------+---------------------------+------------------------+
| 1. TestTamperingDetector     | Call(os.remove), Assign   | CRITICAL (1.0)         |
| 2. GraderManipulationDetector| Call(sys._getframe), Eq   | CRITICAL (1.0)         |
| 3. PrematureTermination      | Call(sys.exit), os._exit  | CRITICAL (1.0)         |
| 4. EnvHijackingDetector      | Subprocess("git log")     | HIGH (0.6)             |
| 5. RewardSkippingDetector    | Try(bare except: return)  | HIGH (0.6) / MED (0.35)|
| 6. LLMJudgeBiasDetector      | Rubric YAML Regex         | MEDIUM (0.35)          |
+------------------------------+---------------------------+------------------------+
```

### 2.1 Test Tampering (`test_tampering.py`)
- **AST Pattern**: Walks `ast.Call` nodes targeting `os.remove()`, `os.unlink()`, `shutil.rmtree()`, or file write operations (`open(..., 'w')`) targeting test files (matching `test_*.py` or `*_test.py`).
- **Rationale**: Agents operating inside containerized environments will delete assertion files so test runners output exit code 0 automatically.

### 2.2 Grader Manipulation (`grader_manipulation.py`)
- **AST Pattern**: Detects `inspect.stack()`, `inspect.currentframe()`, `sys._getframe()`, and custom class `__eq__()` overloading returning unconditional `True`.
- **Rationale**: Graders sharing in-process memory space expose caller stack frames, allowing agents to extract ground-truth answers directly from caller scope.

### 2.3 Premature Termination (`premature_termination.py`)
- **AST Pattern**: Target `ast.Call` nodes invoking `sys.exit(0)`, `os._exit(0)`, or `exit(0)`.
- **Rationale**: Calling exit code `0` halts evaluation harnesses early, tricking orchestration pipelines into marking the trajectory as successful.

### 2.4 Environment Hijacking (`env_hijacking.py`)
- **AST Pattern**: Detects subprocess commands containing `git log`, `git show`, `cat /tmp/answer`, or reading solution environment variables (`os.environ["GOLDEN_PATCH"]`).
- **Rationale**: Benchmark containers frequently retain unstripped repository metadata or local secret files containing complete task solutions.

### 2.5 Reward Component Skipping (`reward_skipping.py`)
- **AST Pattern**: Scans for bare `except:` or `except Exception:` blocks containing `return True` or `return 1.0`, as well as unconditioned reward assignments (`reward = 1.0`).
- **Rationale**: Environment authors wrap verifier bodies in catch-all exception blocks to avoid agent crashes, inadvertently converting runtime crashes into maximum reward.

### 2.6 LLM-Judge Bias (`llm_judge_bias.py`)
- **Pattern**: Regex scanning over rubric files (`rubric.yaml`, `eval.yaml`) targeting verbosity bias patterns (rewarding raw text length over correctness criteria).
- **Rationale**: LLM-as-a-judge evaluators exhibit sycophancy and verbosity bias unless explicitly constrained by correctness-first prompt rubrics.
