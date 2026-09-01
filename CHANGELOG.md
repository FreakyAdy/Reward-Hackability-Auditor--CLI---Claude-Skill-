# Changelog

All notable changes to the **`ratctl`** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-09-01

### Added
- **`ratctl watch` & `ratctl.integrations` Subsystem (Beta)**:
  - Live runtime monitoring for verifier functions and reward calls during RL training (`ratctl.watch(verifier_fn)`).
  - Trajectory streaming to JSONL logs (`logs/run.jsonl`).
  - CLI subcommands: `ratctl watch`, `ratctl show`, `ratctl summary`, and `ratctl audit logs/run.jsonl`.
  - TRL / GRPO integrations wrapper stub (`ratctl.integrations.GRPOSpy`).
- **Runnable Example Pairs (`examples/`)**:
  - `examples/hardened_env/`: Clean verifier reference implementation (0 findings).
  - `examples/vulnerable_env/`: Gameable verifier exhibiting multi-class vulnerabilities.
  - `examples/README.md`: Contrast guide and usage instructions.
- **Documentation & Technical Papers**:
  - `PAPER.md`: Standalone empirical technical report auditing 112 RL environments.
  - `docs/detectors.md`: Deep technical and mathematical detector specifications.
  - `docs/hack_patterns.md`: Code gallery of exploit patterns with before/after fixes.
  - `docs/demo.cast`: Asciinema terminal recording artifact.
  - `CONTRIBUTING.md` & `CODE_OF_CONDUCT.md`: Project hygiene and community guidelines.

### Changed
- Reframed project narrative to focus on objective empirical audit metrics (112-environment dataset).
- Enhanced Gymnasium detection logic with AST step-reward assignment scanning.

---

## [0.1.0] - 2026-09-01

### Added
- **Static Detection Engine**: 6 core detectors for test tampering, grader manipulation, premature termination, environment hijacking, reward skipping, and LLM-judge bias.
- **Dynamic Fuzzing Engine**: Subprocess sandbox execution with 16-strategy hint catalog and local Ollama / Frontier API integration.
- **Multi-Format Adapters**: Native support for OpenEnv (`openenv.yaml`, `server/app.py`, `models.py`), Prime Intellect `verifiers` spec (`load_environment()`, `@vf.stop`), and Gymnasium.
- **Packaging & CI Gate**: Click CLI (`ratctl audit`), GitHub Action (`action.yml`), and Claude Skill (`SKILL.md`).
- **Empirical Validation Runner**: `ratctl benchmark` command calculating Recall, Specificity, Precision, and Accuracy.
