"""Generate animated demo.gif hero image for README.md."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Canvas configuration
WIDTH, HEIGHT = 900, 520
BG_COLOR = (11, 15, 25)          # Dark background
WINDOW_BG = (18, 26, 44)        # Terminal window background
TITLE_BG = (26, 36, 58)         # Window titlebar
TEXT_WHITE = (241, 242, 246)
TEXT_DIM = (164, 176, 190)
TEXT_CYAN = (0, 210, 211)
TEXT_RED = (255, 71, 87)
TEXT_GREEN = (46, 213, 115)
TEXT_YELLOW = (255, 165, 2)
TEXT_PURPLE = (165, 94, 234)

try:
    font = ImageFont.truetype("consola.ttf", 15)
    font_bold = ImageFont.truetype("consolab.ttf", 15)
    font_title = ImageFont.truetype("consolab.ttf", 13)
except Exception:
    font = ImageFont.load_default()
    font_bold = font
    font_title = font


def draw_window_frame(draw: ImageDraw.ImageDraw, title: str = "ratctl audit -- ./vulnerable_env"):
    """Draw macOS-style window controls and title bar."""
    # Window container
    draw.rounded_rectangle([30, 20, WIDTH - 30, HEIGHT - 20], radius=12, fill=WINDOW_BG, outline=(50, 60, 85), width=1)
    # Titlebar
    draw.rounded_rectangle([30, 20, WIDTH - 30, 60], radius=12, fill=TITLE_BG)
    draw.rectangle([30, 50, WIDTH - 30, 60], fill=TITLE_BG)  # Flatten bottom corners of titlebar
    draw.line([30, 60, WIDTH - 30, 60], fill=(50, 60, 85), width=1)

    # Window dots
    draw.ellipse([48, 36, 58, 46], fill=(255, 95, 86))   # Red
    draw.ellipse([66, 36, 76, 46], fill=(255, 189, 46))  # Yellow
    draw.ellipse([84, 36, 94, 46], fill=(39, 201, 63))   # Green

    # Window title
    draw.text((WIDTH // 2 - 110, 34), title, font=font_title, fill=TEXT_DIM)


def render_frame(lines: list[tuple[str, tuple[int, int, int]]]) -> Image.Image:
    """Render a single terminal frame with colored lines."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_window_frame(draw)

    y = 80
    x_start = 55
    line_spacing = 20

    for line_text, color in lines:
        if line_text.startswith("$ "):
            draw.text((x_start, y), "$ ", font=font_bold, fill=TEXT_GREEN)
            draw.text((x_start + 20, y), line_text[2:], font=font_bold, fill=TEXT_WHITE)
        elif "CRITICAL" in line_text:
            draw.text((x_start, y), line_text, font=font_bold, fill=TEXT_RED)
        elif "HIGH" in line_text:
            draw.text((x_start, y), line_text, font=font_bold, fill=TEXT_YELLOW)
        elif "FAIL:" in line_text:
            draw.text((x_start, y), line_text, font=font_bold, fill=TEXT_RED)
        elif "Gameability Score:" in line_text:
            draw.text((x_start, y), line_text, font=font_bold, fill=TEXT_RED)
        elif "RATCTL" in line_text or "=== " in line_text:
            draw.text((x_start, y), line_text, font=font_bold, fill=TEXT_CYAN)
        else:
            draw.text((x_start, y), line_text, font=font, fill=color)

        y += line_spacing

    return img


def generate_demo_gif():
    """Build multi-frame animation sequence and save to docs/demo.gif."""
    frames = []

    # Frame 1: Command prompt
    f1_lines = [
        ("$ ratctl audit ./vulnerable_env --fail-on 'gameability>0.3'", TEXT_WHITE),
    ]

    # Frame 2: Format scan
    f2_lines = f1_lines + [
        ("Scanning environment files at ./vulnerable_env...", TEXT_DIM),
        ("Format Detected: openenv (99% confidence)", TEXT_PURPLE),
    ]

    # Frame 3: Header & Score
    f3_lines = f2_lines + [
        ("=" * 64, TEXT_CYAN),
        ("  RATCTL AUDIT REPORT — Gameability Score: 85/100 [CRITICAL]", TEXT_RED),
        ("=" * 64, TEXT_CYAN),
        ("  Total Findings: 4  |  Files Scanned: 6", TEXT_WHITE),
    ]

    # Frame 4: Critical Findings Live
    f4_lines = f3_lines + [
        ("----------------------------------------------------------------", TEXT_DIM),
        ("  [TEST_TAMPERING] - CRITICAL: Deleting test files (server/app.py:18)", TEXT_RED),
        ("  Evidence: os.remove('tests/test_solution.py')", TEXT_YELLOW),
        ("  [GRADER_MANIPULATION] - CRITICAL: Stack introspection (server/app.py:27)", TEXT_RED),
        ("  Evidence: caller = sys._getframe(1)", TEXT_YELLOW),
        ("  [PREMATURE_TERMINATION] - CRITICAL: sys.exit(0) early exit (server/app.py:34)", TEXT_RED),
        ("  Evidence: sys.exit(0)", TEXT_YELLOW),
        ("  [ENV_HIJACKING] - HIGH: Git history leak (server/app.py:30)", TEXT_YELLOW),
    ]

    # Frame 5: Verdict FAIL
    f5_lines = f4_lines + [
        ("=" * 64, TEXT_CYAN),
        ("FAIL: Gameability score 85/100 exceeds threshold 30%", TEXT_RED),
    ]

    img_f1 = render_frame(f1_lines)
    img_f2 = render_frame(f2_lines)
    img_f3 = render_frame(f3_lines)
    img_f4 = render_frame(f4_lines)
    img_f5 = render_frame(f5_lines)

    # Sequence with holds
    animation_sequence = [
        (img_f1, 1000),
        (img_f2, 800),
        (img_f3, 1000),
        (img_f4, 1500),
        (img_f5, 3000),
    ]

    images = []
    durations = []
    for img, d in animation_sequence:
        images.append(img)
        durations.append(d)

    out_dir = Path("docs")
    out_dir.mkdir(exist_ok=True)
    gif_path = out_dir / "demo.gif"

    images[0].save(
        gif_path,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
    )
    print(f"Created animated demo GIF at {gif_path} ({gif_path.stat().st_size} bytes)")


if __name__ == "__main__":
    generate_demo_gif()
