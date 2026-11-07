#!/usr/bin/env python3
"""Reproducible, dependency-free SVG chart for sanitized historical measurements."""
from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/data/2026-11-07-prefix-observations.json"
OUTPUT = ROOT / "docs/figures/shockwave-prefix-ttft-2026-11-07.svg"


def render(data: dict) -> str:
    pairs = data["pairs"]
    if len(pairs) != 2:
        raise ValueError("This historical visualization expects exactly two independently reported pairs")
    first = [p["first_ttft_s"] for p in pairs]
    second = [p["repeat_ttft_s"] for p in pairs]
    ratio = median(a / b for a, b in zip(first, second))
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="428" viewBox="0 0 960 428" role="img" '
        'aria-labelledby="title description">',
        '<title id="title">Shockwave first versus repeated prompt time to first token</title>',
        '<desc id="description">Two observed first/repeat prompt pairs. First requests took 4.771 and 4.322 seconds, repeated requests 0.553 and 0.536 seconds. Cache hits unverified.</desc>',
        '<rect width="960" height="428" rx="18" fill="#F8FAFC"/>',
        '<text x="36" y="47" font-family="sans-serif" font-weight="700" font-size="24" fill="#102A43">Shockwave · first-token latency</text>',
        '<text x="36" y="73" font-family="sans-serif" font-size="14" fill="#526477">Two independent first/repeat pairs · ~6,082 prompt tokens each · lower is better</text>',
        '<rect x="754" y="18" width="166" height="66" rx="12" fill="#DBEAFE"/>',
        f'<text x="774" y="50" font-family="sans-serif" font-size="28" font-weight="800" fill="#1D4ED8">{ratio:.2f}×</text>',
        '<text x="774" y="70" font-family="sans-serif" font-size="12" fill="#1E40AF">Median paired ratio</text>',
        '<rect x="36" y="99" width="13" height="13" rx="2" fill="#315E98"/>',
        '<text x="56" y="110" font-family="sans-serif" font-size="13" fill="#334155">First prompt</text>',
        '<rect x="184" y="99" width="13" height="13" rx="2" fill="#0D9488"/>',
        '<text x="204" y="110" font-family="sans-serif" font-size="13" fill="#334155">Repeated prompt</text>',
    ]
    start_x, scale = 166, 125
    for i, p in enumerate(pairs):
        y = 156 + i * 114
        elements += [
            f'<text x="36" y="{y + 22}" font-family="sans-serif" font-weight="700" font-size="16" fill="#102A43">Run {i+1}</text>',
            f'<text x="36" y="{y + 41}" font-family="sans-serif" font-size="12" fill="#64748B">{int(p["prompt_tokens"]):,} tokens</text>',
        ]
        for j, (val, color) in enumerate(((p["first_ttft_s"], "#315E98"), (p["repeat_ttft_s"], "#0D9488"))):
            ypos = y + j * 37
            bar_width = val * scale
            elements += [
                f'<rect x="{start_x}" y="{ypos}" width="{bar_width:.2f}" height="28" rx="6" fill="{color}"/>',
                f'<text x="{start_x + bar_width + 10:.1f}" y="{ypos + 20}" font-family="sans-serif" font-size="14" font-weight="700" fill="#102A43">{val:.3f}s</text>',
            ]
    elements += [
        '<line x1="166" y1="371" x2="792" y2="371" stroke="#CBD5E1" stroke-width="2"/>',
    ]
    for tick in range(0, 6):
        x = start_x + tick * scale
        elements += [
            f'<line x1="{x}" y1="368" x2="{x}" y2="377" stroke="#94A3B8"/>',
            f'<text x="{x}" y="394" font-family="sans-serif" text-anchor="middle" font-size="12" fill="#526477">{tick}s</text>',
        ]
    elements += [
        '<text x="36" y="417" font-family="sans-serif" font-size="13" font-weight="600" fill="#9A3412">TTFT speedup does not prove KV-cache hits. cached_tokens was unavailable in both runs.</text>',
        '</svg>',
    ]
    return "\n".join(elements) + "\n"


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(data), encoding="utf-8")
    print(f"Generated {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
