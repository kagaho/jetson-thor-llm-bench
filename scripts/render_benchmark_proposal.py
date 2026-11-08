#!/usr/bin/env python3
"""Render the README's conceptual suite map as a GIF and a still PNG.

Regenerate with: python3 scripts/render_benchmark_proposal.py
Pillow is a rendering-only dependency; the benchmark and tests do not import it.
All suite labels stay visible in every frame. Animation does not represent a run.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/figures"
WIDTH, HEIGHT, SCALE = 1280, 900, 2
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
BACKGROUND = "#0C1626"
CARD = "#152338"
BORDER = "#30445F"
WHITE = "#F3F7FC"
MUTED = "#AEC0D7"
GROUPS = (
    ("Model response", "How does it respond?", "#7BA5FF", (
        ("quick", "First-token and response timing"),
        ("reasoning", "Compare thinking settings"),
        ("context", "Retrieve from longer inputs"),
        ("vision", "Check the image API"),
    )),
    ("Context reuse", "Does shared context help?", "#45D4C1", (
        ("prefix", "Repeat the same request"),
        ("agent", "Shared context, new task"),
    )),
    ("Agent simulation", "Can it follow a workflow?", "#BAA2FF", (
        ("tool-routing", "Choose a structured tool"),
        ("agent-multiturn", "Follow fixed simulated tasks"),
        ("agent-generalization", "Vary fixtures, check evidence"),
    )),
)
POSITIONS = (44, 452, 860)
CAPTIONS = {
    "overview": "One model. Complementary tests.",
    "response": "01  Observe the response",
    "reuse": "02  Test shared context",
    "simulation": "03  Follow the evidence",
    "reports": "04  Read the measurements",
    "offline": "05  Check the harness",
}


def color_mix(first: str, second: str, amount: float) -> tuple[int, int, int]:
    a = tuple(int(first[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(second[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


def font(size: int, *, bold: bool = False, mono: bool = False):
    name = "DejaVuSansMono" if mono else "DejaVuSans"
    path = FONT_DIR / (name + ("-Bold" if bold else "") + ".ttf")
    return ImageFont.truetype(str(path), size * SCALE)


def text(draw, xy, value, size=20, fill=WHITE, bold=False, mono=False, anchor=None):
    draw.text(tuple(round(c * SCALE) for c in xy), value,
              font=font(size, bold=bold, mono=mono), fill=fill, anchor=anchor)


def box(draw, bounds, fill, outline=None, width=1, radius=18):
    draw.rounded_rectangle(tuple(round(c * SCALE) for c in bounds),
                           radius=radius * SCALE, fill=fill, outline=outline,
                           width=width * SCALE)


def line(draw, points, fill=BORDER, width=2):
    draw.line([(round(x * SCALE), round(y * SCALE)) for x, y in points],
              fill=fill, width=width * SCALE, joint="curve")


def packet(draw, points, progress, color):
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    distance = min(1.0, max(0.0, progress)) * sum(lengths)
    for start, end, length in zip(points, points[1:], lengths):
        if distance <= length:
            fraction = distance / length if length else 0
            x, y = (a + (b - a) * fraction for a, b in zip(start, end))
            for radius, strength in ((11, .15), (7, .35), (3.5, 1.0)):
                fill = color_mix(BACKGROUND, color, strength)
                draw.ellipse(tuple(round(c * SCALE) for c in
                                   (x - radius, y - radius, x + radius, y + radius)), fill=fill)
            return
        distance -= length


def top_route(center):
    return [(640, 239), (640, 266), (center, 266), (center, 292)]


def bottom_route(center):
    return [(center, 626), (center, 650), (640, 650), (640, 676)]


def render_frame(phase="overview", progress=.5):
    image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), BACKGROUND)
    draw = ImageDraw.Draw(image)
    active = {"response": 0, "reuse": 1, "simulation": 2}.get(phase)
    emphasis = math.sin(math.pi * progress) if active is not None else 0

    # The whole diagram is present before motion starts.
    text(draw, (44, 30), "JETSON THOR LLM BENCH", size=17, bold=True, fill=MUTED)
    text(draw, (44, 73), "What can your local model do?", size=41, bold=True)
    text(draw, (44, 130), "Choose a question. Run the matching suite. Keep the evidence.",
         size=21, fill=MUTED)
    text(draw, (44, 201), CAPTIONS[phase], size=20,
         fill=GROUPS[active][2] if active is not None else MUTED)
    box(draw, (460, 175, 820, 239), "#1D304A", outline="#567497", radius=16)
    text(draw, (640, 206), "Already-running local model", size=21, bold=True, anchor="mm")

    for x in POSITIONS:
        center = x + 188
        line(draw, top_route(center))
        line(draw, bottom_route(center))
    if active is not None:
        accent = GROUPS[active][2]
        center = POSITIONS[active] + 188
        line(draw, top_route(center), color_mix(BORDER, accent, emphasis), width=3)
        line(draw, bottom_route(center), color_mix(BORDER, accent, emphasis), width=3)
        if progress < .5:
            packet(draw, top_route(center), progress * 2, accent)
        else:
            packet(draw, bottom_route(center), (progress - .5) * 2, accent)

    for i, ((title, description, accent, suites), x) in enumerate(zip(GROUPS, POSITIONS)):
        selected = i == active
        outline = color_mix(BORDER, accent, .3 + .7 * emphasis) if selected else BORDER
        box(draw, (x, 292, x + 376, 626), CARD, outline=outline, width=3 if selected else 1)
        box(draw, (x + 20, 316, x + 26, 343), accent, radius=3)
        text(draw, (x + 40, 313), title, size=25, bold=True)
        text(draw, (x + 22, 352), description, size=18, fill=MUTED)
        line(draw, [(x + 22, 383), (x + 354, 383)], fill=BORDER, width=1)
        ys = {4: (399, 453, 507, 561), 3: (406, 482, 558), 2: (426, 526)}[len(suites)]
        for y, (name, detail) in zip(ys, suites):
            text(draw, (x + 23, y), name, size=20, bold=True, mono=True)
            text(draw, (x + 23, y + 28), detail, size=18, fill=MUTED)

    report_active = phase == "reports"
    box(draw, (44, 676, 1236, 756), "#192D41", outline="#45D4C1" if report_active else BORDER,
        width=3 if report_active else 1)
    text(draw, (72, 688), "Evidence you can inspect", size=26, bold=True)
    text(draw, (72, 727), "Latency  ·  Token usage  ·  Completion  ·  Scoped task outcomes", size=18, fill=MUTED)
    text(draw, (1208, 706), "REVIEWABLE REPORTS", size=15, fill="#45D4C1", bold=True, anchor="rm")
    if report_active:
        packet(draw, [(730, 706), (950, 706)], progress, "#45D4C1")

    offline_active = phase == "offline"
    box(draw, (44, 784, 1236, 846), "#17253A", outline="#F3C77B" if offline_active else BORDER,
        width=3 if offline_active else 1, radius=14)
    box(draw, (66, 804, 84, 822), "#294454", outline="#45D4C1", radius=4)
    line(draw, [(70, 812), (74, 816), (81, 808)], fill="#45D4C1", width=2)
    text(draw, (99, 798), "Offline harness checks", size=23, bold=True)
    text(draw, (444, 805), "Fixtures  ·  Protocols  ·  Grading  ·  Privacy", size=18, fill=MUTED)
    text(draw, (1208, 816), "NO MODEL NEEDED", size=15, bold=True,
         fill="#F3C77B" if offline_active else MUTED, anchor="rm")
    text(draw, (44, 870), "Sequential requests. Simulated agent tools. No generated code executed.",
         size=18, fill=MUTED)
    return image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    still = render_frame()
    still.save(DEST / "benchmark-proposal.png", optimize=True)

    # One shared palette avoids color flicker as highlights move.
    phases = ("overview", "response", "reuse", "simulation", "reports", "offline")
    swatches = Image.new("RGB", (320 * len(phases), 225))
    for i, phase in enumerate(phases):
        swatches.paste(render_frame(phase).resize((320, 225)), (320 * i, 0))
    adaptive = swatches.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    colors = adaptive.getpalette()[:96 * 3]
    # Reserve the small accent areas explicitly; adaptive palettes otherwise
    # favor large background/text regions and can wash out the branch colors.
    for value in (BACKGROUND, CARD, BORDER, WHITE, MUTED, "#1D304A", "#567497",
                  "#192D41", "#17253A", "#294454", "#F3C77B"):
        colors.extend(int(value[i:i + 2], 16) for i in (1, 3, 5))
    for _, _, accent, _ in GROUPS:
        for base in (BACKGROUND, BORDER, CARD):
            for step in range(13):
                colors.extend(color_mix(base, accent, step / 12))
    colors.extend([0] * (768 - len(colors)))
    palette = Image.new("P", (1, 1))
    palette.putpalette(colors)
    frames, durations = [], []
    timeline = [("overview", 1), ("response", 18), ("reuse", 18),
                ("simulation", 18), ("reports", 12), ("offline", 12), ("overview", 1)]
    for phase, count in timeline:
        for i in range(count):
            progress = i / (count - 1) if count > 1 else .5
            frame = render_frame(phase, progress).quantize(palette=palette, dither=Image.Dither.NONE)
            frames.append(frame)
            durations.append(120 if count > 1 else 1100)
    animation = DEST / "benchmark-proposal.gif"
    frames[0].save(animation, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, disposal=1, optimize=False,
                   comment=b"Conceptual suite map, not a live run or measured result. Pillow rendering-only.")
    print(f"Generated {animation.relative_to(ROOT)} ({animation.stat().st_size:,} bytes)")
    print(f"Generated {(DEST / 'benchmark-proposal.png').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
