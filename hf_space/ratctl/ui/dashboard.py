"""Web UI Dashboard for ratctl.

Launches a local interactive web server rendering real-time audit reports,
benchmark metrics, and live trajectory monitoring.
"""

from __future__ import annotations

import http.server
import json
import socketserver
import threading
import webbrowser
from pathlib import Path
from typing import Any

from ratctl.analyzer import audit
from ratctl.watch import summarize_logs, read_logs


def generate_dashboard_html(report_data: dict[str, Any], watch_logs: list[dict] | None = None) -> str:
    """Generate a self-contained, modern glassmorphic web dashboard HTML string."""
    report_json_str = json.dumps(report_data)
    logs_json_str = json.dumps(watch_logs or [])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ratctl Security Dashboard | Reward-Hackability Auditor</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-dark: #0b0f19;
      --bg-card: rgba(18, 26, 44, 0.75);
      --border-card: rgba(255, 255, 255, 0.08);
      --accent-red: #ff4757;
      --accent-orange: #ffa502;
      --accent-green: #2ed573;
      --accent-blue: #3742fa;
      --accent-cyan: #00d2d3;
      --text-main: #f1f2f6;
      --text-muted: #a4b0be;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background: var(--bg-dark);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      background-image: 
        radial-gradient(circle at 10% 20%, rgba(55, 66, 250, 0.15) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(255, 71, 87, 0.12) 0%, transparent 40%);
    }}

    header {{
      padding: 18px 40px;
      border-bottom: 1px solid var(--border-card);
      background: rgba(11, 15, 25, 0.8);
      backdrop-filter: blur(12px);
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }}

    .logo-group {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .logo-icon {{
      font-size: 28px;
    }}
    .logo-title {{
      font-size: 20px;
      font-weight: 800;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, #fff 0%, #a4b0be 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .badge {{
      background: rgba(0, 210, 211, 0.15);
      color: var(--accent-cyan);
      border: 1px solid rgba(0, 210, 211, 0.3);
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .container {{
      max-width: 1300px;
      width: 100%;
      margin: 0 auto;
      padding: 32px 24px;
      flex: 1;
    }}

    .top-grid {{
      display: grid;
      grid-template-columns: 340px 1fr;
      gap: 24px;
      margin-bottom: 32px;
    }}

    .card {{
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: 16px;
      padding: 24px;
      backdrop-filter: blur(16px);
      box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
      transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    .card:hover {{
      border-color: rgba(255, 255, 255, 0.18);
    }}

    .score-box {{
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }}
    .score-circle {{
      width: 140px;
      height: 140px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 42px;
      font-weight: 800;
      margin: 16px 0;
      position: relative;
      background: radial-gradient(circle, rgba(18, 26, 44, 0.9) 60%, transparent 100%);
      box-shadow: 0 0 30px rgba(0, 0, 0, 0.5);
    }}

    .verdict-badge {{
      display: inline-block;
      padding: 6px 16px;
      border-radius: 30px;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
    }}
    .verdict-pass {{ background: rgba(46, 213, 115, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); }}
    .verdict-fail {{ background: rgba(255, 71, 87, 0.2); color: var(--accent-red); border: 1px solid var(--accent-red); }}

    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }}
    .stat-tile {{
      background: rgba(255, 255, 255, 0.03);
      border-radius: 12px;
      padding: 16px;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }}
    .stat-val {{
      font-size: 26px;
      font-weight: 700;
      margin-top: 4px;
    }}
    .stat-lbl {{
      font-size: 12px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .section-title {{
      font-size: 18px;
      font-weight: 700;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .findings-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    .findings-table th {{
      text-align: left;
      padding: 12px 16px;
      color: var(--text-muted);
      font-size: 12px;
      text-transform: uppercase;
      border-bottom: 1px solid var(--border-card);
    }}
    .findings-table td {{
      padding: 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      vertical-align: top;
    }}
    .findings-table tr:hover {{
      background: rgba(255, 255, 255, 0.02);
    }}

    .sev-critical {{ color: var(--accent-red); font-weight: 700; }}
    .sev-high {{ color: var(--accent-orange); font-weight: 700; }}
    .sev-medium {{ color: var(--accent-orange); font-weight: 600; }}
    .sev-low {{ color: #eccc68; font-weight: 500; }}
    .sev-info {{ color: var(--accent-cyan); font-weight: 500; }}

    code {{
      font-family: 'JetBrains Mono', monospace;
      background: rgba(0, 0, 0, 0.4);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 12px;
      color: #70a1ff;
    }}
  </style>
</head>
<body>

  <header>
    <div class="logo-group">
      <span class="logo-icon">🐀</span>
      <span class="logo-title">ratctl Security Dashboard</span>
      <span class="badge">v0.2.0</span>
    </div>
    <div style="font-size: 13px; color: var(--text-muted);">
      Target: <code id="env-path">./environment</code>
    </div>
  </header>

  <div class="container">

    <div class="top-grid">
      <!-- Score Circle Card -->
      <div class="card score-box">
        <div style="font-size: 13px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Gameability Score</div>
        <div class="score-circle" id="score-num">--</div>
        <div id="verdict-tag" class="verdict-badge">PENDING</div>
      </div>

      <!-- Quick Metrics Grid -->
      <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
        <div class="section-title">📊 Audit Telemetry Overview</div>
        <div class="stats-grid">
          <div class="stat-tile">
            <div class="stat-lbl">Format Detected</div>
            <div class="stat-val" id="stat-format">--</div>
          </div>
          <div class="stat-tile">
            <div class="stat-lbl">Files Scanned</div>
            <div class="stat-val" id="stat-files">0</div>
          </div>
          <div class="stat-tile">
            <div class="stat-lbl">Total Findings</div>
            <div class="stat-val" id="stat-findings">0</div>
          </div>
        </div>
        <div style="margin-top: 16px; font-size: 13px; color: var(--text-muted);">
          Audited against 6 exploit classes (Test Tampering, Grader Introspection, Exit Manipulation, Git Leaks, Reward Skipping, LLM Judge Bias).
        </div>
      </div>
    </div>

    <!-- Findings Table Card -->
    <div class="card">
      <div class="section-title">🔍 Security Findings & Evidence</div>
      <table class="findings-table">
        <thead>
          <tr>
            <th>Severity</th>
            <th>Exploit Class</th>
            <th>Title & Finding</th>
            <th>Location</th>
            <th>Evidence Snippet</th>
          </tr>
        </thead>
        <tbody id="findings-body">
          <tr><td colspan="5" style="text-align:center; color: var(--text-muted);">No findings loaded.</td></tr>
        </tbody>
      </table>
    </div>

  </div>

  <script>
    const reportData = {report_json_str};

    function renderDashboard(data) {{
      const score = data.gameability_score || 0;
      const scoreEl = document.getElementById("score-num");
      const verdictEl = document.getElementById("verdict-tag");

      scoreEl.innerText = score + "/100";
      if (score > 30) {{
        scoreEl.style.border = "4px solid var(--accent-red)";
        scoreEl.style.color = "var(--accent-red)";
        verdictEl.innerText = "FAIL (GAMEABLE)";
        verdictEl.className = "verdict-badge verdict-fail";
      }} else {{
        scoreEl.style.border = "4px solid var(--accent-green)";
        scoreEl.style.color = "var(--accent-green)";
        verdictEl.innerText = "PASS (HARDENED)";
        verdictEl.className = "verdict-badge verdict-pass";
      }}

      document.getElementById("stat-format").innerText = data.format_detected || "raw";
      document.getElementById("stat-files").innerText = data.total_files_scanned || 0;
      document.getElementById("stat-findings").innerText = data.total_findings || 0;
      document.getElementById("env-path").innerText = data.target_path || "./environment";

      const tbody = document.getElementById("findings-body");
      tbody.innerHTML = "";

      let allFindings = [];
      if (data.class_scores) {{
        for (const [cls, cs] of Object.entries(data.class_scores)) {{
          if (cs.findings && cs.findings.length > 0) {{
            cs.findings.forEach(f => {{
              allFindings.push({{ ...f, class: cls }});
            }});
          }}
        }}
      }}

      if (allFindings.length === 0) {{
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 32px; color: var(--accent-green); font-weight:600;">✅ No security vulnerabilities detected in this verifier!</td></tr>`;
        return;
      }}

      allFindings.forEach(f => {{
        const tr = document.createElement("tr");
        const sevClass = "sev-" + (f.severity || "info").toLowerCase();
        tr.innerHTML = `
          <td><span class="${{sevClass}}">${{(f.severity || "INFO").toUpperCase()}}</span></td>
          <td><code>${{f.class}}</code></td>
          <td>
            <strong style="color:#fff;">${{f.title}}</strong><br>
            <span style="font-size:12px; color:var(--text-muted);">${{f.description || ""}}</span>
          </td>
          <td><code>${{f.file_path}}:${{f.line_number || 1}}</code></td>
          <td><code>${{f.evidence || ""}}</code></td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    renderDashboard(reportData);
  </script>
</body>
</html>
"""


def launch_dashboard(path: str = ".", port: int = 8500) -> None:
    """Run audit and launch local browser dashboard."""
    report = audit(path)
    report_dict = report.to_dict()
    report_dict["target_path"] = str(path)

    html_content = generate_dashboard_html(report_dict)

    class DashboardHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))

        def log_message(self, format, *args):
            pass  # Suppress HTTP server noise

    server = socketserver.TCPServer(("127.0.0.1", port), DashboardHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"🐀 ratctl Web UI Dashboard running at {url}")

    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    webbrowser.open(url)
