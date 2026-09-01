"""
Generate docs/demo.gif — ratctl audit dashboard in rewardspy panel style.
Layout mirrors the reference:
  - Top status bar: ratctl● env_name | score | VULNERABLE
  - Diagnosis panel (full width)
  - Middle row: Audit Overview | Exploit Status | Severity Breakdown (sparkline-style)
  - Bottom row: Findings Detail | Recommendations
  - Recent Findings table
  - Footer keybinds
Story arc: scan starts → detectors run → findings appear → score rises → VULNERABLE locked in
"""

from __future__ import annotations
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

random.seed(7)

# ─── Canvas & Palette ────────────────────────────────────────────────────────
W, H     = 1020, 600
BG       = (10, 14, 23)       # near-black background
PANEL    = (14, 20, 36)       # panel fill
BORDER   = (38, 54, 82)       # panel border
CYAN     = (0, 198, 198)      # primary accent
CYAN_D   = (0, 120, 130)      # dim cyan
MAG      = (180, 80, 200)     # magenta / purple accent
GREEN    = (46, 204, 113)     # pass / ok
GREEN_D  = (18, 90, 50)
YELLOW   = (230, 175, 0)      # warning
RED      = (220, 60, 55)      # critical / alert
RED_D    = (100, 22, 20)
WHITE    = (232, 238, 248)
DIM      = (105, 125, 150)
TITLE_BG = (20, 30, 52)

EXPLOIT_CLASSES = [
    "TEST_TAMPERING",
    "GRADER_MANIPULATION",
    "PREMATURE_TERMINATION",
    "ENV_HIJACKING",
    "REWARD_SKIPPING",
    "LLM_JUDGE_BIAS",
]

FINDINGS = [
    ("TEST_TAMPERING",        "CRITICAL", "os.remove('tests/test_solution.py')",        "server/app.py:18"),
    ("GRADER_MANIPULATION",   "CRITICAL", "sys._getframe(1) — stack introspection",     "server/app.py:27"),
    ("PREMATURE_TERMINATION", "CRITICAL", "sys.exit(0) before grader completes",        "server/app.py:34"),
    ("ENV_HIJACKING",         "HIGH",     "subprocess.run(['git','log','-n','1'])",     "server/app.py:30"),
]

# ─── Font loader ─────────────────────────────────────────────────────────────
def _f(size, bold=False):
    for name in (["consolab.ttf","DejaVuSansMono-Bold.ttf","cour.ttf"] if bold
                 else ["consola.ttf","DejaVuSansMono.ttf","couri.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()

F11  = _f(11);  F12  = _f(12);  F13  = _f(13);  F14  = _f(14)
F11B = _f(11, True); F12B = _f(12, True); F13B = _f(13, True)
F14B = _f(14, True); F15B = _f(15, True); F16B = _f(16, True)
F18B = _f(18, True)

def tw(draw, s, font):
    return int(draw.textlength(s, font=font))

# ─── Drawing primitives ───────────────────────────────────────────────────────
def t(draw, xy, s, font=F13, color=WHITE):
    draw.text(xy, s, font=font, fill=color)

def panel_box(draw, box, title="", title_col=CYAN, fill=PANEL):
    draw.rounded_rectangle(box, radius=5, fill=fill, outline=BORDER, width=1)
    if title:
        tx, ty = box[0] + 10, box[1] - 9
        draw.rounded_rectangle([tx-2, ty-1, tx + tw(draw,title,F11B)+4, ty+13],
                                radius=3, fill=PANEL)
        t(draw, (tx, ty), title, font=F11B, color=title_col)

def hbar(draw, x, y, value, width=180, height=9, color=CYAN):
    filled = max(0, min(width, int(value * width)))
    draw.rounded_rectangle([x, y, x+width, y+height], radius=3, fill=(22,32,52))
    if filled > 0:
        draw.rounded_rectangle([x, y, x+filled, y+height], radius=3, fill=color)

def sparkbars(draw, x, y, values, width=260, height=55):
    """Histogram-style sparkline like rewardspy."""
    if not values:
        return
    n   = len(values)
    cw  = max(2, width // n)
    lo, hi = min(values), max(values)
    span = hi - lo if hi != lo else 1.0
    for i, v in enumerate(values):
        h_px = max(2, int(((v - lo) / span) * height))
        cx = x + i * cw
        frac = (v - lo) / span
        r = int(CYAN_D[0]*(1-frac) + MAG[0]*frac)
        g = int(CYAN_D[1]*(1-frac) + MAG[1]*frac)
        b = int(CYAN_D[2]*(1-frac) + MAG[2]*frac)
        draw.rectangle([cx, y+height-h_px, cx+cw-1, y+height], fill=(r,g,b))

def dot_bg(draw):
    for gx in range(0, W, 22):
        for gy in range(36, H, 22):
            draw.point((gx, gy), fill=(18, 26, 42))


# ─── Frame renderer ───────────────────────────────────────────────────────────
def render(
    n_found: int,       # 0–4 findings revealed
    n_detectors: int,   # 0–6 detectors completed
    score: int,         # 0–85
    phase: str,         # "scanning" | "found" | "locked"
) -> Image.Image:

    img = Image.new("RGB", (W, H), BG)
    d   = ImageDraw.Draw(img)
    dot_bg(d)

    found = FINDINGS[:n_found]
    vulnerable = n_found > 0 and phase == "locked"

    # ── macOS titlebar ────────────────────────────────────────────────────────
    d.rectangle([0, 0, W, 36], fill=TITLE_BG)
    d.ellipse([14, 11, 26, 23], fill=(255, 95, 86))
    d.ellipse([34, 11, 46, 23], fill=(255, 189, 46))
    d.ellipse([54, 11, 66, 23], fill=(39, 201, 63))
    t(d, (W//2-65, 10), "ratctl — audit dashboard", font=F12, color=DIM)
    d.line([0, 36, W, 36], fill=BORDER)

    # ── Status bar ────────────────────────────────────────────────────────────
    d.rectangle([0, 37, W, 62], fill=(16, 24, 42))
    # ratctl pill
    d.rounded_rectangle([12, 42, 68, 58], radius=4, fill=GREEN_D)
    t(d, (14, 42), " ratctl", font=F13B, color=GREEN)
    t(d, (14, 42), "●", font=F13B, color=GREEN)
    t(d, (80, 42),  "vulnerable_env", font=F13B, color=WHITE)
    t(d, (258, 43), "score:", font=F12, color=DIM)
    score_col = RED if score > 50 else (YELLOW if score > 20 else GREEN)
    t(d, (308, 42), f"{score}/100", font=F13B, color=score_col)
    t(d, (390, 43), "|", font=F12, color=BORDER)
    t(d, (405, 43), f"detectors: {n_detectors}/6", font=F12, color=DIM)
    t(d, (530, 43), "|", font=F12, color=BORDER)
    t(d, (545, 43), f"findings: {n_found}", font=F12, color=DIM if n_found==0 else RED)
    # Status label (right)
    status_s, status_c = (
        ("VULNERABLE", RED) if vulnerable else
        ("SCANNING...", YELLOW) if phase == "scanning" else
        ("ANALYSING",  CYAN)
    )
    sw = tw(d, status_s, F14B)
    t(d, (W - sw - 18, 42), status_s, font=F14B, color=status_c)
    d.line([0, 62, W, 62], fill=BORDER)

    # ── Layout constants ──────────────────────────────────────────────────────
    PAD  = 12
    TOP  = 74
    MH   = 148   # middle row height
    BH   = 108   # bottom row height
    RH   = 95    # recent findings height
    FH   = 28    # footer

    OW = 205     # audit overview width
    SW = 195     # exploit status width
    CX = PAD + OW + SW + 18  # curve start x
    CW = W - CX - PAD        # curve width

    MID_Y  = TOP + 5 + 30   # diagnosis height = 30+top
    DIAG_H = 68

    # ── Diagnosis panel (full width) ──────────────────────────────────────────
    DIAG_BOX = [PAD, TOP, W-PAD, TOP+DIAG_H]
    diag_border = MAG if vulnerable else (YELLOW if n_found > 0 else CYAN)
    d.rounded_rectangle(DIAG_BOX, radius=5, fill=PANEL, outline=diag_border, width=1)
    # title tag
    dt = "Diagnosis"
    d.rounded_rectangle([PAD+8, TOP-9, PAD+8+tw(d,dt,F11B)+6, TOP+5],
                        radius=3, fill=PANEL)
    t(d, (PAD+10, TOP-9), dt, font=F11B, color=diag_border)

    if vulnerable:
        t(d, (PAD+12, TOP+10), "[!]  4 reward-hacking exploits detected.", font=F13B, color=RED)
        t(d, (PAD+12, TOP+30),
          "Static analysis found CRITICAL and HIGH severity exploits across 4 detector classes.",
          font=F12, color=WHITE)
        t(d, (PAD+12, TOP+48),
          "This environment is gameable. Block deployment until findings are resolved.",
          font=F11, color=YELLOW)
    elif n_found > 0:
        t(d, (PAD+12, TOP+10), f"[!]  {n_found} exploit(s) found so far — scan in progress...", font=F13B, color=YELLOW)
        t(d, (PAD+12, TOP+30), "Continuing scan across remaining detector classes.", font=F12, color=WHITE)
        t(d, (PAD+12, TOP+48), "Do not deploy until all detectors complete.", font=F11, color=DIM)
    elif phase == "scanning":
        t(d, (PAD+12, TOP+10), f"Running detector {n_detectors+1}/6: {EXPLOIT_CLASSES[min(n_detectors,5)]}...", font=F13B, color=CYAN)
        t(d, (PAD+12, TOP+30), "No findings yet. Scanning source files for exploit patterns.", font=F12, color=WHITE)
        t(d, (PAD+12, TOP+48), "Format detected: openenv (99% confidence)  |  Files: 6", font=F11, color=DIM)
    else:
        t(d, (PAD+12, TOP+18), "[OK]  No reward-hacking exploits detected.", font=F13B, color=GREEN)
        t(d, (PAD+12, TOP+40), "All 6 static detectors passed. Environment is hardened.", font=F12, color=DIM)

    # ── Middle row ────────────────────────────────────────────────────────────
    MY = TOP + DIAG_H + 10

    # Audit Overview
    OV_BOX = [PAD, MY, PAD+OW, MY+MH]
    panel_box(d, OV_BOX, "Audit Overview", CYAN)
    rows = [
        ("score",     f"{score}/100",       score_col),
        ("findings",  str(n_found),          RED if n_found else DIM),
        ("detectors", f"{n_detectors}/6",    CYAN),
        ("files",     "6",                   WHITE),
        ("format",    "openenv (99%)",        MAG),
        ("precision", "100.0%",              GREEN),
        ("recall",    "78.3%",               GREEN),
    ]
    for i, (k, v, vc) in enumerate(rows):
        ry = MY + 16 + i * 18
        t(d, (PAD+10, ry), k,  font=F12, color=DIM)
        t(d, (PAD+100, ry), v, font=F12, color=vc)

    # Exploit Status (like "Hack Status" in rewardspy)
    SX = PAD + OW + 8
    SB = [SX, MY, SX+SW, MY+MH]
    panel_box(d, SB, "Exploit Status", CYAN)

    statuses = []
    for i, cls in enumerate(EXPLOIT_CLASSES):
        caught = any(f[0] == cls for f in found)
        scanned = i < n_detectors
        if not scanned:
            statuses.append((cls, "pending", DIM))
        elif caught:
            statuses.append((cls, "CAUGHT", RED))
        else:
            statuses.append((cls, "clean",  GREEN))

    for i, (cls, status, sc) in enumerate(statuses):
        ry = MY + 14 + i * 20
        icon = "[X]" if status == "CAUGHT" else ("[OK]" if status == "clean" else "[..]")
        ic   = RED   if status == "CAUGHT" else (GREEN if status == "clean" else DIM)
        t(d, (SX+10, ry), icon, font=F12B, color=ic)
        label = cls.replace("_", " ").title()[:18]
        t(d, (SX+52, ry), label, font=F12, color=sc)

    # Overall verdict line
    ov_y = MY + MH - 22
    d.line([SX+8, ov_y-4, SX+SW-8, ov_y-4], fill=BORDER)
    if vulnerable:
        t(d, (SX+10, ov_y), "[X]", font=F12B, color=RED)
        t(d, (SX+38, ov_y), "Overall: VULNERABLE", font=F12B, color=RED)
    elif n_detectors == 6:
        t(d, (SX+10, ov_y), "[OK]", font=F12B, color=GREEN)
        t(d, (SX+40, ov_y), "Overall: CLEAN", font=F12B, color=GREEN)
    else:
        t(d, (SX+10, ov_y), "[..]", font=F12B, color=YELLOW)
        t(d, (SX+40, ov_y), "Overall: SCANNING", font=F12B, color=YELLOW)

    # Severity / Score Curve
    CB = [CX, MY, CX+CW, MY+MH]
    panel_box(d, CB, "Severity Breakdown", MAG)
    # Build a histogram of scored weights per detector
    bar_labels = [c.replace("_", " ")[:10] for c in EXPLOIT_CLASSES]
    bar_vals   = []
    for cls in EXPLOIT_CLASSES:
        caught = any(f[0] == cls for f in found)
        bar_vals.append(0.85 if cls in ("TEST_TAMPERING","GRADER_MANIPULATION","PREMATURE_TERMINATION")
                        else 0.55 if cls == "ENV_HIJACKING" else 0.1)
    # Only show bars for scanned detectors
    display_vals = [bar_vals[i] if i < n_detectors else 0.0 for i in range(6)]
    sparkbars(d, CX+8, MY+16, display_vals, width=CW-16, height=MH-50)
    d.line([CX+8, MY+MH-32, CX+CW-8, MY+MH-32], fill=BORDER)
    t(d, (CX+8,  MY+MH-28), "0.0", font=F11, color=DIM)
    t(d, (CX+CW-30, MY+MH-28), "1.0", font=F11, color=DIM)
    t(d, (CX+8, MY+MH-14), "detector risk score", font=F11, color=DIM)

    # ── Bottom row: Findings Detail | Recommendations ─────────────────────────
    BY = MY + MH + 10
    BW = (W - 3*PAD) // 2

    FD_BOX = [PAD, BY, PAD+BW, BY+BH]
    panel_box(d, FD_BOX, "Findings Detail", RED if n_found else DIM)
    if found:
        for i, (cls, sev, ev, loc) in enumerate(found[:3]):
            fy = BY + 14 + i * 28
            sc = RED if sev == "CRITICAL" else YELLOW
            t(d, (PAD+10, fy),    f"[{sev}]",  font=F11B, color=sc)
            sw2 = tw(d, f"[{sev}]", F11B)
            t(d, (PAD+14+sw2, fy), f" {cls}",  font=F11,  color=WHITE)
            t(d, (PAD+10, fy+14),  f"  {ev[:54]}", font=F11, color=YELLOW)
            t(d, (PAD+10, fy+24),  f"  {loc}",     font=F11, color=DIM)
    else:
        t(d, (PAD+10, BY+38), "No findings yet...", font=F12, color=DIM)

    # Recommendations
    RX = PAD + BW + PAD
    RB = [RX, BY, RX+BW, BY+BH]
    panel_box(d, RB, "Recommendations", CYAN)
    recs = [
        ("Mount test files read-only",        "TEST_TAMPERING"),
        ("Sandbox sys module (block _getframe)","GRADER_MANIPULATION"),
        ("Trap sys.exit in grading harness",  "PREMATURE_TERMINATION"),
        ("Remove .git dir from agent sandbox","ENV_HIJACKING"),
    ]
    visible = [r for r in recs if any(f[0] == r[1] for f in found)]
    if visible:
        for i, (rec, _) in enumerate(visible[:3]):
            t(d, (RX+10, BY+14+i*27), f"[!]", font=F11B, color=YELLOW)
            t(d, (RX+34, BY+14+i*27), rec, font=F11, color=WHITE)
    else:
        t(d, (RX+10, BY+38), "No recommendations yet.", font=F12, color=DIM)

    # ── Recent Findings table ─────────────────────────────────────────────────
    RFY = BY + BH + 10
    RF_BOX = [PAD, RFY, W-PAD, RFY+RH]
    panel_box(d, RF_BOX, "Recent Findings", CYAN)
    # headers
    cols = [("class", PAD+10), ("severity", PAD+210), ("evidence", PAD+310), ("location", PAD+620)]
    for lbl, cx2 in cols:
        t(d, (cx2, RFY+10), lbl, font=F11B, color=DIM)
    d.line([PAD+6, RFY+24, W-PAD-6, RFY+24], fill=BORDER)

    for i, (cls, sev, ev, loc) in enumerate(found[:4]):
        ry = RFY + 28 + i*16
        sc = RED if sev == "CRITICAL" else YELLOW
        t(d, (PAD+10,  ry), cls,         font=F11, color=WHITE)
        t(d, (PAD+210, ry), f"[{sev}]",  font=F11B, color=sc)
        t(d, (PAD+310, ry), ev[:40],     font=F11, color=YELLOW)
        t(d, (PAD+620, ry), loc,         font=F11, color=DIM)

    # ── Footer ────────────────────────────────────────────────────────────────
    FY = H - FH
    d.rectangle([0, FY, W, H], fill=TITLE_BG)
    d.line([0, FY, W, FY], fill=BORDER)
    kx = 12
    for key, label in [("q","Quit"),("e","Export JSON"),("r","Re-scan"),("a","Clear")]:
        kw = tw(d, f" {key} ", F12B) + 2
        d.rounded_rectangle([kx, FY+6, kx+kw, FY+22], radius=3, fill=WHITE)
        t(d, (kx+2, FY+6), f" {key} ", font=F12B, color=BG)
        kx += kw + 4
        t(d, (kx, FY+8), f"{label}   ", font=F11, color=DIM)
        kx += tw(d, f"{label}   ", F11)
    t(d, (W-80, FY+8), "^palette", font=F11, color=DIM)

    return img


# ─── Build animation ──────────────────────────────────────────────────────────
def generate():
    frames, durs = [], []

    def add(img, ms):
        frames.append(img)
        durs.append(ms)

    # Phase 1: Detectors running, no findings yet
    for nd in range(0, 4):
        add(render(0, nd, 0, "scanning"), 400)

    # Phase 2: First finding appears (TEST_TAMPERING)
    add(render(1, 4, 0, "scanning"), 150)
    add(render(1, 4, 22, "scanning"), 500)

    # Phase 3: Second finding
    add(render(2, 5, 0, "scanning"), 150)
    add(render(2, 5, 45, "scanning"), 500)

    # Phase 4: Third finding
    add(render(3, 5, 0, "scanning"), 150)
    add(render(3, 5, 65, "scanning"), 500)

    # Phase 5: Fourth finding + scan completes
    add(render(4, 6, 0, "found"), 150)
    add(render(4, 6, 85, "found"), 800)

    # Phase 6: Score locks in, VULNERABLE banner
    for _ in range(2):
        add(render(4, 6, 85, "locked"), 200)
        add(render(4, 6, 85, "found"),  150)
    # Final hold
    add(render(4, 6, 85, "locked"), 3500)

    out = Path("docs")
    out.mkdir(exist_ok=True)
    gif_path = out / "demo.gif"
    frames[0].save(gif_path, save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, optimize=False)
    print(f"Saved {gif_path}  ({gif_path.stat().st_size//1024} KB, {len(frames)} frames)")
    frames[-1].convert("RGB").save(out / "demo_preview.png")
    print("Preview: docs/demo_preview.png")

if __name__ == "__main__":
    generate()
