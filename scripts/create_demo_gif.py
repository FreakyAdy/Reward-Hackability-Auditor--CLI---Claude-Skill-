"""
Generate docs/demo.gif — animated GIF showing ratctl audit catching a reward hack.
The story arc:
  Frame 1-2: Command typed
  Frame 3: Scanning...
  Frame 4: CRITICAL findings fire one by one
  Frame 5: Score: 85/100 CRITICAL
  Frame 6: FAIL: threshold exceeded (the tool CAUGHT it — this is success)
"""

from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ─── Palette ─────────────────────────────────────────────────────────────────
W, H        = 920, 500
BG          = (10, 14, 23)
WIN_BG      = (14, 20, 35)
TITLEBAR    = (22, 32, 55)
BORDER      = (38, 52, 78)
CYAN        = (0, 200, 200)
GREEN       = (46, 204, 113)
GREEN_DIM   = (20, 100, 55)
RED         = (231, 76, 60)
RED_DIM     = (120, 30, 20)
YELLOW      = (241, 196, 15)
WHITE       = (235, 240, 248)
DIM         = (110, 130, 155)
PURPLE      = (155, 89, 182)
ORANGE      = (230, 126, 34)

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (["consolab.ttf","DejaVuSansMono-Bold.ttf"] if bold
                 else ["consola.ttf","DejaVuSansMono.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()

F12   = _font(12)
F13   = _font(13)
F14   = _font(14)
F14B  = _font(14, bold=True)
F15B  = _font(15, bold=True)
F16B  = _font(16, bold=True)
F18B  = _font(18, bold=True)

def text(draw, xy, s, font=F14, color=WHITE):
    draw.text(xy, s, font=font, fill=color)

def dot_grid(draw):
    for gx in range(0, W, 24):
        for gy in range(36, H, 24):
            draw.point((gx, gy), fill=(20, 28, 45))

def titlebar(draw, img):
    draw.rectangle([0, 0, W, 36], fill=TITLEBAR)
    draw.ellipse([14, 11, 26, 23], fill=(255, 95, 86))
    draw.ellipse([34, 11, 46, 23], fill=(255, 189, 46))
    draw.ellipse([54, 11, 66, 23], fill=(39, 201, 63))
    text(draw, (W//2 - 90, 10), "ratctl audit — terminal", font=F12, color=DIM)
    draw.line([0, 36, W, 36], fill=BORDER)

def prompt(draw, y, cmd=""):
    text(draw, (28, y), "$", font=F14B, color=GREEN)
    text(draw, (44, y), cmd, font=F14B, color=WHITE)

def cursor_blink(draw, x, y, on: bool):
    if on:
        draw.rectangle([x, y+1, x+9, y+17], fill=CYAN)

def base_frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    dot_grid(draw)
    titlebar(draw, img)
    return img, draw

# ─── FINDING lines ───────────────────────────────────────────────────────────
FINDINGS = [
    ("[CRITICAL]", "TEST_TAMPERING",       "os.remove('tests/test_solution.py')",       "server/app.py:18"),
    ("[CRITICAL]", "GRADER_MANIPULATION",  "caller = sys._getframe(1)",                 "server/app.py:27"),
    ("[CRITICAL]", "PREMATURE_TERMINATION","sys.exit(0) before verification completes", "server/app.py:34"),
    ("[HIGH]",     "ENV_HIJACKING",        "subprocess.run(['git','log','-n','1'])",     "server/app.py:30"),
]

def render_finding(draw, y: int, badge: str, cls: str, evidence: str, loc: str):
    badge_col = RED if "[CRITICAL]" in badge else ORANGE
    text(draw, (28,  y),     badge,    font=F13,  color=badge_col)
    bw = int(draw.textlength(badge, font=F13))
    text(draw, (32 + bw, y), f" {cls}", font=F13,  color=WHITE)
    text(draw, (28, y+17),   f"  {evidence}", font=F12, color=YELLOW)
    text(draw, (28, y+32),   f"  {loc}",      font=F12, color=DIM)


# ─── Frame builders ───────────────────────────────────────────────────────────

def frame_typing(cursor: bool) -> Image.Image:
    img, draw = base_frame()
    prompt(draw, 55, "ratctl audit ./vulnerable_env --fail-on 'gameability>0.3'")
    if cursor:
        xc = 44 + int(draw.textlength("ratctl audit ./vulnerable_env --fail-on 'gameability>0.3'", font=F14B))
        cursor_blink(draw, xc + 2, 55, True)
    return img

def frame_scanning() -> Image.Image:
    img, draw = base_frame()
    prompt(draw, 55, "ratctl audit ./vulnerable_env --fail-on 'gameability>0.3'")
    text(draw, (28, 88),  "Scanning environment files at ./vulnerable_env ...", font=F13, color=DIM)
    text(draw, (28, 108), "Format Detected: openenv (99% confidence)", font=F13, color=PURPLE)
    text(draw, (28, 128), "Running 6 static detectors ...", font=F13, color=DIM)
    return img

def frame_findings(n_findings: int) -> Image.Image:
    """Show n findings revealed so far."""
    img, draw = base_frame()
    prompt(draw, 55, "ratctl audit ./vulnerable_env --fail-on 'gameability>0.3'")
    text(draw, (28, 88),  "Format Detected: openenv (99% confidence)", font=F12, color=PURPLE)

    # Separator
    text(draw, (28, 110), "=" * 74, font=F12, color=CYAN)
    text(draw, (28, 125), "  RATCTL AUDIT REPORT", font=F14B, color=CYAN)
    text(draw, (28, 143), "=" * 74, font=F12, color=CYAN)
    text(draw, (28, 160), "-" * 74, font=F12, color=BORDER)

    y = 178
    for i in range(min(n_findings, len(FINDINGS))):
        badge, cls, ev, loc = FINDINGS[i]
        render_finding(draw, y, badge, cls, ev, loc)
        y += 58
        draw.line([28, y - 6, W - 28, y - 6], fill=(30, 42, 65))

    return img

def frame_score(show_fail: bool = False) -> Image.Image:
    img, draw = base_frame()
    prompt(draw, 50, "ratctl audit ./vulnerable_env --fail-on 'gameability>0.3'")

    # All 4 findings shown
    text(draw, (28, 80),  "Format Detected: openenv (99% confidence)", font=F12, color=PURPLE)
    text(draw, (28, 96),  "=" * 74, font=F12, color=CYAN)

    # Score box
    draw.rounded_rectangle([22, 110, W - 22, 195], radius=8, fill=(18, 10, 10), outline=RED, width=2)
    text(draw, (38, 120), "Gameability Score:", font=F16B, color=WHITE)
    text(draw, (268, 120), "85 / 100", font=F16B, color=RED)

    # badge
    draw.rounded_rectangle([370, 116, 455, 138], radius=4, fill=RED_DIM)
    text(draw, (378, 118), "CRITICAL", font=F13, color=RED)

    text(draw, (38, 150), "Total Findings:  4", font=F13, color=WHITE)
    text(draw, (220, 150), "|", font=F13, color=DIM)
    text(draw, (235, 150), "Files Scanned:  6", font=F13, color=WHITE)
    text(draw, (400, 150), "|", font=F13, color=DIM)
    text(draw, (415, 150), "Format: openenv", font=F13, color=WHITE)

    # Mini findings summary
    text(draw, (28, 206), "-" * 74, font=F12, color=BORDER)
    y = 218
    for badge, cls, ev, loc in FINDINGS:
        badge_col = RED if "[CRITICAL]" in badge else ORANGE
        text(draw, (28, y), badge, font=F12, color=badge_col)
        bw = int(draw.textlength(badge, font=F12))
        text(draw, (32 + bw, y), f" {cls}  —  {ev[:52]}", font=F12, color=WHITE)
        y += 20

    text(draw, (28, y + 6), "=" * 74, font=F12, color=CYAN)

    # FAIL verdict
    if show_fail:
        draw.rounded_rectangle([22, y + 24, W - 22, y + 68], radius=8,
                                fill=(20, 6, 6), outline=RED, width=2)
        text(draw, (38, y + 30), "FAIL", font=F18B, color=RED)
        text(draw, (100, y + 33), "Gameability score 85/100 exceeds threshold 30%", font=F14B, color=WHITE)
        text(draw, (38, y + 52), "Exit code: 1  —  Reward hack caught. Block this deployment.", font=F12, color=GREEN)

    return img

# ─── Build animation sequence ─────────────────────────────────────────────────

def generate():
    out = Path("docs")
    out.mkdir(exist_ok=True)

    sequence: list[tuple[Image.Image, int]] = []

    # Typing command (cursor blink × 3)
    for i in range(6):
        sequence.append((frame_typing(cursor=i % 2 == 0), 200))

    # Scanning
    sequence.append((frame_scanning(), 900))

    # Findings appear one by one
    for n in range(1, 5):
        hold = 600 if n < 4 else 400
        sequence.append((frame_findings(n), hold))

    # Score — no fail yet (let viewer read)
    sequence.append((frame_score(show_fail=False), 1200))

    # FAIL verdict fires
    for _ in range(3):
        sequence.append((frame_score(show_fail=True), 250))
        sequence.append((frame_score(show_fail=False), 200))

    # Final hold: FAIL caught clearly
    sequence.append((frame_score(show_fail=True), 3500))

    frames, durations = zip(*sequence)

    gif_path = out / "demo.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=list(frames[1:]),
        duration=list(durations),
        loop=0,
        optimize=False,
    )
    size_kb = gif_path.stat().st_size // 1024
    print(f"Saved {gif_path}  ({size_kb} KB, {len(frames)} frames)")

    # Save preview of final frame
    frames[-1].convert("RGB").save(out / "demo_preview.png")
    print("Preview saved to docs/demo_preview.png")

if __name__ == "__main__":
    generate()
