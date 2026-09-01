"""Tests for ratctl.ui web dashboard subsystem."""

from ratctl.ui.dashboard import generate_dashboard_html


def test_generate_dashboard_html():
    sample_report = {
        "gameability_score": 85,
        "total_findings": 2,
        "format_detected": "openenv",
        "total_files_scanned": 4,
        "class_scores": {
            "PREMATURE_TERMINATION": {
                "findings": [
                    {
                        "severity": "critical",
                        "title": "sys.exit(0) detected",
                        "file_path": "verifier.py",
                        "line_number": 10,
                        "evidence": "sys.exit(0)",
                    }
                ]
            }
        },
    }

    html = generate_dashboard_html(sample_report)
    assert "<title>ratctl Security Dashboard" in html
    assert "85/100" in html or "PREMATURE_TERMINATION" in html
    assert "sys.exit(0)" in html
