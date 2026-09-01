"""Hugging Face Space Application for ratctl (Reward-Hackability Auditor).

Interactive web demo allowing users to audit RL verifier code and reward functions
for reward-hacking exploits in real time.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import gradio as gr

# Ensure local ratctl package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from ratctl.analyzer import audit
from ratctl.ui.dashboard import generate_dashboard_html


EXAMPLES = {
    "🚨 Multi-Exploit Vulnerable Verifier": """import os
import sys
import subprocess

def grade_submission(agent_code: str) -> float:
    # Exploit 1: Private stack introspection to detect grading harness
    caller = sys._getframe(1)
    if "test_harness" in caller.f_code.co_filename:
        return 1.0

    # Exploit 2: Tampering with test files before evaluation
    if os.path.exists("tests/test_solution.py"):
        os.remove("tests/test_solution.py")

    # Exploit 3: Inspecting git commit history to extract golden answers
    history = subprocess.run(["git", "log", "-n", "1"], capture_output=True, text=True)

    # Exploit 4: Premature exit with code 0 to short-circuit verification
    if "bypass" in agent_code:
        sys.exit(0)

    return 0.0
""",
    "🛡️ Hardened & Isolated Verifier": """import ast
import subprocess

def verify_code(agent_submission: str, test_suite_path: str = "/readonly/tests/test_spec.py") -> float:
    # Hardened verifier: AST syntax check + subprocess execution in isolated container
    try:
        ast.parse(agent_submission)
    except SyntaxError:
        return 0.0

    # Execute tests in isolated read-only sandbox with non-zero exit validation
    proc = subprocess.run(
        ["pytest", test_suite_path, "-q"],
        capture_output=True,
        timeout=10,
    )
    if proc.returncode == 0:
        return 1.0
    return 0.0
""",
    "🕵️ Grader Stack Introspection Exploit": """import sys

def verify_step(state, action):
    # Agent checks caller frames to inspect hidden environment parameters
    frame = sys._getframe(2)
    secret_target = frame.f_locals.get("target_goal", 0)
    
    if action == secret_target:
        return 1.0
    return 0.0
""",
    "🚪 Premature Exit Bypass Exploit": """import sys

def evaluate_agent(solution: str):
    # If the verifier catches sys.exit(0) as passing without checking the solution:
    if len(solution) > 0:
        sys.exit(0)
    return 0.0
""",
    "📝 Test File Tampering Exploit": """import os

def check_solution(workspace_dir: str):
    test_path = os.path.join(workspace_dir, "tests", "test_core.py")
    # Vulnerability: verifier deletes or truncates test file
    if os.path.exists(test_path):
        os.remove(test_path)
    return 1.0
"""
}


def audit_code_snippet(code: str, env_format: str = "raw") -> tuple[str, str, str]:
    """Audit a code snippet string and return formatted results."""
    if not code or not code.strip():
        return (
            "<div style='padding:20px; color:#ff4757;'>⚠️ Please enter or select a verifier code snippet to audit.</div>",
            "**No code provided.**",
            "{}"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "verifier.py"
        file_path.write_text(code, encoding="utf-8")

        # Run ratctl audit
        score = audit(file_path, format_override=env_format)
        report_dict = score.to_dict()
        report_dict["target_path"] = "verifier.py"

        # Generate HTML dashboard component
        html_dashboard = generate_dashboard_html(report_dict)

        # Generate Markdown Summary
        verdict_badge = "🔴 **FAIL: GAMEABLE (VULNERABLE)**" if score.gameability_score > 30 else "🟢 **PASS: HARDENED (SAFE)**"
        md_lines = [
            f"### 🐀 Audit Verdict: {verdict_badge}",
            f"- **Gameability Score**: `{score.gameability_score}/100` (Fail threshold: >30)",
            f"- **Total Findings**: `{score.total_findings}` across `{score.total_files_scanned}` file(s)",
            f"- **Format Detected**: `{score.format_detected}` ({score.format_confidence:.0%})",
            "",
            "#### Detected Findings by Exploit Class:"
        ]

        has_findings = False
        for cls_name, cs in score.class_scores.items():
            if cs.finding_count > 0:
                has_findings = True
                md_lines.append(f"\n##### `[{cls_name.upper()}]` — {cs.finding_count} finding(s) (Max: `{cs.max_severity}`)")
                for f in cs.findings:
                    md_lines.append(f"- **{f.title}** (`Line {f.line_number}`)")
                    md_lines.append(f"  - *Evidence*: `{f.evidence}`")
                    md_lines.append(f"  - *Remediation*: {f.suggested_fix}")

        if not has_findings:
            md_lines.append("\n✅ **No security vulnerabilities detected.** Verifier passes standard exploit checks.")

        escaped_html = html_dashboard.replace('"', '&quot;')
        iframe_html = f'<iframe srcdoc="{escaped_html}" style="width:100%; height:620px; border:none; border-radius:12px;"></iframe>'

        return (
            iframe_html,
            "\n".join(md_lines),
            json.dumps(report_dict, indent=2)
        )


def build_app() -> gr.Blocks:
    custom_css = """
    .gradio-container { max-width: 1300px !important; margin: auto !important; }
    #header-box { text-align: center; margin-bottom: 20px; }
    """

    with gr.Blocks(title="ratctl — Reward-Hackability Auditor", css=custom_css, theme=gr.themes.Soft()) as demo:
        with gr.Column(elem_id="header-box"):
            gr.Markdown(
                """
                # 🐀 `ratctl` — Reward-Hackability Auditor for RL Environments
                ### *Fuzz your verifier before an RL agent does.*
                
                Audit reinforcement learning environment verifiers, reward functions, and grading harnesses for 
                reward-hacking vulnerabilities (**Test Tampering, Grader Introspection, Exit Success, Git Leaks, Reward Bias**).
                """
            )

        with gr.Row():
            with gr.Column(scale=5):
                code_input = gr.Code(
                    value=EXAMPLES["🚨 Multi-Exploit Vulnerable Verifier"],
                    language="python",
                    label="Verifier / Reward Function Code (Python)",
                    lines=18,
                )

                with gr.Row():
                    example_selector = gr.Dropdown(
                        choices=list(EXAMPLES.keys()),
                        value="🚨 Multi-Exploit Vulnerable Verifier",
                        label="Load Preset Verifier Example",
                    )
                    format_selector = gr.Dropdown(
                        choices=["raw", "openenv", "verifiers", "gymnasium"],
                        value="raw",
                        label="Environment Format",
                    )

                audit_btn = gr.Button("🔍 Run ratctl Security Audit", variant="primary", size="lg")

            with gr.Column(scale=6):
                with gr.Tabs():
                    with gr.TabItem("📊 Interactive Security Dashboard"):
                        dashboard_output = gr.HTML(label="Visual Dashboard")
                    with gr.TabItem("📋 Findings & Remediation"):
                        markdown_output = gr.Markdown(label="Audit Report")
                    with gr.TabItem("💾 Raw JSON Telemetry"):
                        json_output = gr.Code(language="json", label="JSON Report")

        # Wire examples
        example_selector.change(
            fn=lambda name: EXAMPLES[name],
            inputs=[example_selector],
            outputs=[code_input]
        )

        # Wire audit execution
        audit_btn.click(
            fn=audit_code_snippet,
            inputs=[code_input, format_selector],
            outputs=[dashboard_output, markdown_output, json_output]
        )

        # Trigger initial run on load
        demo.load(
            fn=audit_code_snippet,
            inputs=[code_input, format_selector],
            outputs=[dashboard_output, markdown_output, json_output]
        )

        gr.Markdown(
            """
            ---
            ### 📚 Reference & Empirical Study
            - **GitHub Repository**: [`FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-`](https://github.com/FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-)
            - **Large-Scale Audit**: Audited 112 public RL post-training environments: 61.6% vulnerability rate.
            - **CLI & CI Gate**: `pip install ratctl` → `ratctl audit ./my_env --fail-on 'gameability>0.3'`
            """
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch()
