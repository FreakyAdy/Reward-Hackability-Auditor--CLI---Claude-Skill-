"""
Generate docs/tui_demo.gif — an animated terminal TUI dashboard GIF showing
ratctl detecting reward hacking in real time, styled after the rewardspy UI.
Uses only Pillow (no external fonts required beyond system monospace).
"""

from __future__ import annotations
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ─── Canvas & colour palette ────────────────────────────────────────────────
W, H = 1000, 580
BG          = (10, 14, 23)
WIN_BG      = (14, 20, 35)
BORDER      = (40, 55, 85)
CYAN        = (0, 200, 200)
CYAN_DIM    = (0, 130, 140)
MAGENTA     = (190, 80, 200)
MAG_DIM     = (120, 50, 130)
GREEN       = (50, 220, 100)
GREEN_DIM   = (30, 140, 60)
YELLOW      = (230, 175, 0)
RED         = (230, 60, 60)
WHITE       = (235, 240, 248)
DIM         = (110, 130, 155)
HEADER_BG   = (20, 30, 52)
TITLEBAR_BG = (22, 32, 55)

random.seed(42)

# ─── Font loading ────────────────────────────────────────────────────────────
def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates_bold   = ["consolab.ttf", "DejaVuSansMono-Bold.ttf", "LiberationMono-Bold.ttf",
                         "UbuntuMono-B.ttf", "cour.ttf"]
    candidates_normal = ["consola.ttf",  "DejaVuSansMono.ttf",     "LiberationMono-Regular.ttf",
                         "UbuntuMono-R.ttf", "couri.ttf"]
    for name in (candidates_bold if bold else candidates_normal):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


F_SM   = _load_font(12)
F_NM   = _load_font(14)
F_NM_B = _load_font(14, bold=True)
F_LG   = _load_font(16, bold=True)
F_XL   = _load_font(18, bold=True)

# ─── Drawing helpers ─────────────────────────────────────────────────────────

def text(draw: ImageDraw.ImageDraw, xy, txt, font=F_NM, color=WHITE):
    draw.text(xy, txt, font=font, fill=color)

def rect(draw: ImageDraw.ImageDraw, box, fill=None, outline=None, radius=6, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def panel(draw: ImageDraw.ImageDraw, box, title: str, title_color=CYAN):
    rect(draw, box, fill=WIN_BG, outline=BORDER, radius=6)
    if title:
        tx = box[0] + 10
        ty = box[1] - 9
        tw = draw.textlength(title, font=F_SM) + 6
        rect(draw, [tx - 3, ty - 1, tx + tw, ty + 14], fill=WIN_BG, radius=3)
        text(draw, (tx, ty), title, font=F_SM, color=title_color)

def bar(draw: ImageDraw.ImageDraw, x, y, value: float, width=200, height=10, color=CYAN):
    filled = max(0, min(width, int(value * width)))
    rect(draw, [x, y, x + width, y + height], fill=(25, 35, 55), radius=2)
    if filled > 0:
        rect(draw, [x, y, x + filled, y + height], fill=color, radius=2)

def sparkline(draw: ImageDraw.ImageDraw, x, y, values, width=280, height=55, lo=0.0, hi=1.1):
    """Draw a histogram-style sparkline."""
    n = len(values)
    if n == 0:
        return
    col_w = max(1, width // n)
    span = hi - lo if hi != lo else 1.0
    for i, v in enumerate(values):
        h_px = max(1, int(((v - lo) / span) * height))
        cx = x + i * col_w
        cy = y + height - h_px
        # colour ramp: low=cyan-dim, high=magenta
        t = (v - lo) / span
        r = int(CYAN_DIM[0] * (1 - t) + MAGENTA[0] * t)
        g = int(CYAN_DIM[1] * (1 - t) + MAGENTA[1] * t)
        b = int(CYAN_DIM[2] * (1 - t) + MAGENTA[2] * t)
        draw.rectangle([cx, cy, cx + col_w - 1, y + height], fill=(r, g, b))

def dot_grid(draw: ImageDraw.ImageDraw):
    """Faint dot grid background."""
    for gx in range(0, W, 20):
        for gy in range(0, H, 20):
            draw.point((gx, gy), fill=(25, 35, 52))

# ─── Simulation data generator ───────────────────────────────────────────────

def _build_rewards(step: int, total_steps: int = 60) -> list[float]:
    """Generate reward trajectory: starts normal, ceiling-hacking appears after step 30."""
    curve = []
    for i in range(min(step + 1, 40)):
        base = 0.32 + (i / 40) * 0.68
        noise = random.gauss(0, 0.04)
        if i > 28:
            # ceiling hacking: values cluster near 1.1
            base = 0.88 + (i - 28) / 12 * 0.22
            noise = random.gauss(0, 0.02)
        curve.append(max(0.0, min(1.15, base + noise)))
    return curve

# ─── Frame renderer ──────────────────────────────────────────────────────────

def render_frame(step: int, total_steps: int = 55) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    dot_grid(draw)

    rewards = _build_rewards(step, total_steps)
    mean_r  = sum(rewards) / len(rewards) if rewards else 0.5
    at_ceil = sum(1 for r in rewards if r >= 1.0) / max(len(rewards), 1)
    warning = step > 28
    current_step_label = step * 9 + 1   # Display step number that scales nicely

    # ── macOS-style titlebar ────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 36], fill=TITLEBAR_BG)
    draw.ellipse([16, 10, 30, 24], fill=(255, 95, 86))
    draw.ellipse([38, 10, 52, 24], fill=(255, 189, 46))
    draw.ellipse([60, 10, 74, 24], fill=(39, 201, 63))
    text(draw, (W // 2 - 55, 9), "ratctl — reward hacking monitor", font=F_SM, color=DIM)
    draw.line([0, 36, W, 36], fill=BORDER, width=1)

    # ── Top status bar ───────────────────────────────────────────────────────
    draw.rectangle([0, 37, W, 62], fill=HEADER_BG)
    # "ratctl" pill
    rect(draw, [14, 42, 74, 58], fill=GREEN_DIM, radius=4)
    text(draw, (16, 42), " ratctl", font=F_NM_B, color=BG)
    text(draw, (82, 42),  "math_grpo_run", font=F_NM_B, color=WHITE)
    text(draw, (270, 43), f"step {current_step_label:<5}", font=F_SM, color=DIM)
    text(draw, (380, 43), f"runtime 00:0{step // 10}:{(step % 10) * 6:02d}", font=F_SM, color=DIM)
    status_txt  = "WARNING" if warning else "NORMAL"
    status_col  = YELLOW if warning else GREEN
    text(draw, (W - 120, 42), status_txt, font=F_NM_B, color=status_col)
    draw.line([0, 62, W, 62], fill=BORDER, width=1)

    # ── Diagnosis panel ──────────────────────────────────────────────────────
    DX1, DY1, DX2, DY2 = 14, 74, W - 14, 148
    panel(draw, [DX1, DY1, DX2, DY2], "Diagnosis", MAGENTA)
    if warning:
        text(draw, (DX1 + 12, DY1 + 10), "[!] Early warning signs", font=F_NM_B, color=YELLOW)
        text(draw, (DX1 + 12, DY1 + 30),
             f"The reward curve looks fine (mean {mean_r:.2f}, ^ rising), but {at_ceil*100:.0f}% of rollouts",
             font=F_NM, color=WHITE)
        text(draw, (DX1 + 12, DY1 + 48),
             "are hitting the reward ceiling. First flagged at step 38. Inspect rollouts for shortcut behaviour.",
             font=F_SM, color=DIM)
    else:
        text(draw, (DX1 + 12, DY1 + 12), "[OK] Verifier operating normally", font=F_NM_B, color=GREEN)
        text(draw, (DX1 + 12, DY1 + 34),
             f"Reward distribution balanced (mean {mean_r:.2f}). No reward-hacking shortcuts detected.",
             font=F_NM, color=WHITE)

    # ─── Middle row layout ───────────────────────────────────────────────────
    MY = 162
    MH = 170
    OW = 220   # reward overview width
    HW = 195   # hack status width
    CX = DX1 + OW + HW + 30  # reward curve x-start

    # Reward Overview
    panel(draw, [DX1, MY, DX1 + OW, MY + MH], "Reward overview", CYAN)
    rows = [
        ("mean",       f"{mean_r:.3f}",     WHITE),
        ("std",        "0.400",              WHITE),
        ("trend",      "^ rising",           GREEN),
        ("at ceiling", f"{at_ceil:.0%}",     YELLOW if at_ceil > 0.7 else CYAN),
        ("var vs base","84%",                WHITE),
        ("min / max",  f"0.100 / {max(rewards):.3f}" if rewards else "0.100 / 1.000", WHITE),
        ("p50",        f"{sorted(rewards)[len(rewards)//2]:.3f}" if rewards else "0.500", WHITE),
    ]
    for i, (k, v, vc) in enumerate(rows):
        ry = MY + 16 + i * 20
        text(draw, (DX1 + 12, ry), k, font=F_SM, color=DIM)
        text(draw, (DX1 + 100, ry), v, font=F_SM, color=vc)

    # Hack Status
    HX = DX1 + OW + 8
    panel(draw, [HX, MY, HX + HW, MY + MH], "Hack status", CYAN)
    checks = [
        ("Variance",  True),
        ("Slope",     True),
        ("Component", not warning),
        ("Ceiling",   not (at_ceil > 0.7)),
        ("Length",    True),
    ]
    for i, (label, ok) in enumerate(checks):
        ry = MY + 16 + i * 20
        icon = "[OK]" if ok else "[!]"
        ic   = GREEN if ok else YELLOW
        text(draw, (HX + 10, ry), icon, font=F_SM, color=ic)
        text(draw, (HX + 48, ry), label, font=F_SM, color=WHITE)
    overall_icon = "[!]" if warning else "[OK]"
    overall_col  = YELLOW if warning else GREEN
    overall_str  = "WARNING" if warning else "PASSED"
    text(draw, (HX + 10, MY + 130), overall_icon, font=F_NM_B, color=overall_col)
    text(draw, (HX + 48, MY + 130), f"Overall: {overall_str}", font=F_NM_B, color=overall_col)

    # Reward Curve (sparkline)
    CW = W - CX - 16
    panel(draw, [CX, MY, CX + CW, MY + MH], "Reward curve", MAGENTA)
    text(draw, (CX + 10, MY + 12), f"{max(rewards):.2f}" if rewards else "1.00", font=F_SM, color=DIM)
    sparkline(draw, CX + 48, MY + 12, rewards, width=CW - 60, height=MH - 45)
    text(draw, (CX + 10, MY + MH - 30), f"{min(rewards):.2f}" if rewards else "0.00", font=F_SM, color=DIM)
    draw.line([CX + 48, MY + MH - 25, CX + CW - 12, MY + MH - 25], fill=BORDER, width=1)
    text(draw, (CX + 48, MY + MH - 22), "step 0", font=F_SM, color=DIM)
    text(draw, (CX + CW - 75, MY + MH - 22), f"step {current_step_label}", font=F_SM, color=DIM)

    # ─── Bottom row: Components + Alerts ─────────────────────────────────────
    BY = MY + MH + 10
    BH = 115
    BW = (W - 28 - 8) // 2

    # Components
    panel(draw, [DX1, BY, DX1 + BW, BY + BH], "Components", CYAN)
    components = [
        ("correctness", 0.80),
        ("format",      0.10),
        ("length_pen",  0.00),
    ]
    for i, (name, val) in enumerate(components):
        cy2 = BY + 16 + i * 30
        text(draw, (DX1 + 10, cy2), name, font=F_SM, color=WHITE)
        bar(draw, DX1 + 100, cy2 + 2, val, width=BW - 130, height=11, color=CYAN)
        text(draw, (DX1 + BW - 52, cy2), f"{val:.3f}", font=F_SM, color=CYAN)

    # Alerts
    AX = DX1 + BW + 8
    panel(draw, [AX, BY, AX + BW, BY + BH], "Alerts", CYAN)
    if warning:
        a_step1 = current_step_label
        a_step2 = max(1, current_step_label - 40)
        a_step3 = max(1, current_step_label - 150)
        lines = [
            (f"ALERT  step {a_step1}",       RED),
            (f"{at_ceil:.0%} of rollouts hit the reward ceiling.", WHITE),
            (f"ALERT  step {a_step2}",       RED),
            (f"{at_ceil:.0%} of rollouts hit the reward ceiling.", WHITE),
            (f"WARNING  step {a_step3}",     YELLOW),
            ("Component 'correctness' contributes 76% of reward.", WHITE),
        ]
    else:
        lines = [("No active security alerts.", GREEN_DIM)]

    for i, (line, col) in enumerate(lines[:6]):
        text(draw, (AX + 10, BY + 14 + i * 16), line, font=F_SM, color=col)

    # ─── Recent Rollouts table ────────────────────────────────────────────────
    RY = BY + BH + 10
    RH = H - RY - 48
    panel(draw, [DX1, RY, W - 14, RY + RH], "Recent rollouts", CYAN)
    headers = ["step", "reward", "note"]
    hx_positions = [DX1 + 14, DX1 + 100, DX1 + 200]
    for hx_pos, h_label in zip(hx_positions, headers):
        text(draw, (hx_pos, RY + 10), h_label, font=F_SM, color=DIM)
    draw.line([DX1 + 10, RY + 24, W - 18, RY + 24], fill=BORDER, width=1)

    recent = list(reversed(rewards[-4:])) if len(rewards) >= 4 else []
    for i, r in enumerate(recent):
        note_col = YELLOW if r >= 1.0 else GREEN
        note_str = "at ceiling" if r >= 1.0 else "normal rollout"
        row_y = RY + 28 + i * 18
        text(draw, (hx_positions[0], row_y), str(current_step_label - i * 1), font=F_SM, color=DIM)
        text(draw, (hx_positions[1], row_y), f"{r:.3f}", font=F_SM, color=CYAN)
        text(draw, (hx_positions[2], row_y), note_str, font=F_SM, color=note_col)

    # ─── Footer keybinds ──────────────────────────────────────────────────────
    FY = H - 34
    draw.rectangle([0, FY, W, H], fill=TITLEBAR_BG)
    draw.line([0, FY, W, FY], fill=BORDER, width=1)
    keybinds = [(" q ", "Quit"), (" e ", "Export CSV"), (" a ", "Clear alerts")]
    kx = 14
    for key, label in keybinds:
        kw = int(draw.textlength(key, font=F_NM_B)) + 2
        rect(draw, [kx, FY + 8, kx + kw, FY + 24], fill=WHITE, radius=3)
        text(draw, (kx + 1, FY + 8), key, font=F_NM_B, color=BG)
        kx += kw + 4
        text(draw, (kx, FY + 9), label + "  ", font=F_SM, color=DIM)
        kx += int(draw.textlength(label + "  ", font=F_SM)) + 6
    text(draw, (W - 90, FY + 9), "^palette", font=F_SM, color=DIM)

    return img


# ─── Animation sequence ───────────────────────────────────────────────────────

def generate():
    out_dir = Path("docs")
    out_dir.mkdir(exist_ok=True)

    # Build keyframes with hold durations (ms)
    sequence: list[tuple[int, int]] = []

    # Phase 1: Normal operation (steps 0-22)
    for s in range(0, 23, 2):
        sequence.append((s, 80))

    # Phase 2: Transition — rewards start climbing fast (steps 22-32)
    for s in range(22, 33, 1):
        sequence.append((s, 70))

    # Phase 3: WARNING fires — hold on each new alert frame (steps 32-45)
    for s in range(32, 46, 1):
        hold = 200 if s in (32, 38, 45) else 80
        sequence.append((s, hold))

    # Phase 4: Sustained ceiling hacking — blink alert steps
    for s in range(45, 56):
        sequence.append((s, 90))

    # Final hold on last frame
    sequence.append((55, 2500))

    print(f"Rendering {len(sequence)} frames...")
    frames, durations = [], []
    for idx, (step, dur) in enumerate(sequence):
        print(f"  [{idx+1}/{len(sequence)}] step={step}", end="\r")
        frames.append(render_frame(step))
        durations.append(dur)
    print()

    gif_path = out_dir / "tui_demo.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )
    size_kb = gif_path.stat().st_size // 1024
    print(f"Saved {gif_path}  ({size_kb} KB, {len(frames)} frames)")


if __name__ == "__main__":
    generate()
