# Contributing to `ratctl` 🐀

Thank you for your interest in contributing to **`ratctl` (Reward Audit Tool)**! We welcome contributions from AI safety researchers, RL environment authors, software security engineers, and open-source developers.

---

## 🛠️ Local Development Setup

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Setup Workspace

```bash
# Clone the repository
git clone https://github.com/FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-.git
cd Reward-Hackability-Auditor--CLI---Claude-Skill-

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

### 3. Run the Test Suite

```bash
# Run unit and integration tests
pytest tests/ -v

# Run with statement coverage
pytest --cov=ratctl --cov-report=term-missing tests/

# Run the empirical benchmark suite
ratctl benchmark benchmarks --format markdown
```

---

## 💡 How to Add a Custom Detector

`ratctl`'s static detection engine is designed to be modular and easy to extend. To add a new static exploit detector:

1. Create a new file in `ratctl/detectors/my_custom_detector.py`.
2. Inherit from `BaseDetector` (or `Detector`).
3. Implement `name`, `exploit_class`, and `scan(source_files)`.
4. Register your detector in `ratctl/detectors/__init__.py`.

### Example Custom Detector Implementation:

```python
# ratctl/detectors/my_custom_detector.py
from __future__ import annotations

import re
from typing import Sequence

from ratctl.detectors.base import (
    BaseDetector,
    DetectorResult,
    ExploitClass,
    Severity,
    SourceFile,
)

class MyCustomDetector(BaseDetector):
    """Detects custom verifier bypass patterns."""

    @property
    def name(self) -> str:
        return "my_custom_detector"

    @property
    def exploit_class(self) -> ExploitClass:
        return ExploitClass.GRADER_MANIPULATION

    def scan(self, source_files: Sequence[SourceFile]) -> DetectorResult:
        result = DetectorResult(
            detector_name=self.name,
            exploit_class=self.exploit_class,
        )

        pattern = re.compile(r"""custom_evil_function\s*\(""", re.IGNORECASE)

        for src in source_files:
            result.files_scanned += 1
            for line_num, line in enumerate(src.content.splitlines(), start=1):
                if pattern.search(line):
                    result.findings.append(
                        self._make_finding(
                            file_path=src.path,
                            line_number=line_num,
                            title="Custom Verifier Bypass Detected",
                            description="Function call allows agent to bypass evaluation.",
                            evidence=line.strip(),
                            suggested_fix="Replace with isolated subprocess execution.",
                            severity=Severity.HIGH,
                        )
                    )

        return result
```

5. Add unit tests for your detector in `tests/test_detectors.py`.

---

## 🐛 Reporting a Vulnerability Pattern or Bug

If you discover a reward-hacking pattern in open-source RL verifiers that `ratctl` missed:

1. Open a **GitHub Issue** titled `[New Exploit Pattern] <Description>`.
2. Provide a minimal reproducible verifier snippet showing the flaw.
3. Describe how an RL agent could exploit the flaw to gain unearned reward.

---

## 📜 Pull Request Guidelines

- Ensure all new features or detectors include tests.
- Ensure all 91+ existing tests pass (`pytest tests/`).
- Maintain ASCII-safe output formatting for cross-platform compatibility (Windows/Linux/macOS).
- Keep pull requests focused on a single feature or bugfix.
