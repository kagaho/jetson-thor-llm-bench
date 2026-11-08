"""Render the reviewed Shockwave A/B2 numeric comparison as a static SVG (stdlib)."""
from pathlib import Path

DEST = Path(__file__).resolve().parents[1] / "docs/figures/shockwave-a-b2-memory-and-tool-latency.svg"


def render() -> str:
    panels = [
        ("Available RAM (GiB)", 1.1, 2.9, 3.5, "Higher is better", "1.1", "2.9"),
        ("Median tool-decision latency (s)", 2.9165, 3.1947, 3.6, "Lower is better", "2.92", "3.19"),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 940 515" role="img" aria-labelledby="title desc">',
        '<title id="title">Shockwave baseline A versus experimental B2</title>',
        '<desc id="desc">Available RAM: A 1.1 GiB, B2 2.9 GiB. Median tool-decision latency: A 2.9165 seconds, B2 3.1947 seconds. Differences are not all causally attributable to KV cache sizing.</desc>',
        '<rect width="940" height="515" rx="18" fill="#122032"/>',
        '<text x="28" y="49" fill="#FFFFFF" font-size="28" font-family="Arial, sans-serif" font-weight="bold">Shockwave · KV-cache A/B2</text>',
        '<text x="28" y="82" fill="#B7C6DB" font-size="17" font-family="Arial, sans-serif">Same model and image · different KV cache, startup threshold and context</text>',
        '<rect x="29" y="102" width="16" height="16" fill="#729AF8" rx="3"/>',
        '<text x="54" y="116" fill="#E7EEF8" font-size="16" font-family="Arial, sans-serif">A · automatic KV</text>',
        '<rect x="258" y="102" width="16" height="16" fill="#31C9BC" rx="3"/>',
        '<text x="283" y="116" fill="#E7EEF8" font-size="16" font-family="Arial, sans-serif">B2 · 4 GiB KV</text>',
    ]
    for index, (title, first, second, maximum, direction, la, lb) in enumerate(panels):
        base=154+index*165
        parts.extend([
            f'<text x="28" y="{base}" fill="#FFFFFF" font-size="21" font-family="Arial, sans-serif">{title}</text>',
            f'<text x="730" y="{base}" fill="#B7C6DB" font-size="16" font-family="Arial, sans-serif">{direction}</text>',
        ])
        for i,(value,label,color) in enumerate([(first,la,"#729AF8"),(second,lb,"#31C9BC")]):
            y=base+18+i*33
            parts.extend([
                f'<rect x="28" y="{y}" width="760" height="22" rx="5" fill="#293950"/>',
                f'<rect x="28" y="{y}" width="{760*value/maximum:.2f}" height="22" rx="5" fill="{color}"/>',
                f'<text x="806" y="{y+18}" fill="#EAF1FA" font-size="18" font-family="Arial, sans-serif">{label}</text>',
            ])
    parts += [
        '<text x="28" y="480" fill="#AABDD4" font-size="15" font-family="Arial, sans-serif">A: 213K context / 5.26 GiB cache · B2: 131K context / 4 GiB cache · 30/30 routing passes each</text>',
        '</svg>',''
    ]
    return "\n".join(parts)


if __name__ == "__main__":
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(render(), encoding="utf-8")
    print(DEST)
