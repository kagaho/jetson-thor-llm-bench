#!/usr/bin/env python3
"""Render static charts from reviewed aggregate comparison data (stdlib only)."""
from html import escape
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/data/fp8-hybrid-comparison.json"
COLORS = ("#38bdf8", "#fbbf24")
LABELS = ("B2 / NVIDIA NVFP4", "H2 / FP8 hybrid, 4 GiB KV")


def document(title, panels, note):
    height = 166 + sum(104 + 70 * len(panel[2]) for panel in panels) + 55
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {height}" role="img" aria-labelledby="title desc">',
             f'<title id="title">{escape(title)}</title>',
             f'<desc id="desc">{escape(note)} Values are printed next to every bar; missing values are marked n/a.</desc>',
             f'<rect width="1000" height="{height}" rx="20" fill="#102033"/>',
             '<style>text{font-family:Arial,sans-serif;fill:#e8f1fb}.muted{fill:#aabed3}</style>',
             f'<text x="34" y="46" font-size="25" font-weight="700">{escape(title)}</text>',
             '<text x="34" y="73" font-size="14" class="muted">Same benchmark protocols; checkpoint, runtime and serving features differ.</text>']
    for i, label in enumerate(LABELS):
        x = 34 + i * 320
        parts += [f'<rect x="{x}" y="96" width="18" height="13" rx="3" fill="{COLORS[i]}"/>',
                  f'<text x="{x+27}" y="108" font-size="14">{escape(label)}</text>']
    y = 132
    for heading, units, rows, subtitle in panels:
        h = 104 + 70 * len(rows)
        numbers = [value for _, values, _ in rows for value in values if value is not None]
        maximum = 100 if units == "%" else max(numbers, default=1) * 1.12
        maximum = max(maximum, 0.001)
        parts += [f'<rect x="24" y="{y}" width="952" height="{h-14}" rx="14" fill="#192e45"/>',
                  f'<text x="44" y="{y+30}" font-size="19" font-weight="700">{escape(heading)}</text>',
                  f'<text x="44" y="{y+53}" font-size="12" class="muted">{escape(subtitle)}</text>']
        left, width = 285, 535
        for tick in range(5):
            x = left + width * tick / 4
            value = maximum * tick / 4
            parts += [f'<line x1="{x}" y1="{y+68}" x2="{x}" y2="{y+h-37}" stroke="#29445e"/>',
                      f'<text x="{x}" y="{y+h-22}" font-size="11" text-anchor="middle" class="muted">{value:.1f}</text>']
        for index, (label, values, annotations) in enumerate(rows):
            row_y = y + 83 + index * 70
            parts.append(f'<text x="44" y="{row_y+15}" font-size="14">{escape(label)}</text>')
            for i, value in enumerate(values):
                bar_y = row_y - 3 + i * 24
                length = width * value / maximum if value is not None else 0
                if value is not None:
                    parts.append(f'<rect x="{left}" y="{bar_y}" width="{length:.2f}" height="16" rx="3" fill="{COLORS[i]}"/>')
                annotation = annotations[i] if annotations else ("n/a" if value is None else f"{value:.2f} {units}")
                parts.append(f'<text x="{left+length+9:.2f}" y="{bar_y+13}" font-size="12">{escape(annotation)}</text>')
        y += h
    parts += [f'<text x="34" y="{height-30}" font-size="12" class="muted">{escape(note)}</text>', '</svg>']
    return "\n".join(parts) + "\n"


def render(data):
    arms = [data[name] for name in ("b2", "hybrid")]
    rates = []
    for category in ("Q&A", "Code", "JSON", "Math", "LongCode"):
        values = []
        for arm in arms:
            requests = [row for row in arm["forum_c1"]["requests"] if row["category"] == category]
            values.append(statistics.mean(row["completion_tokens"] / row["elapsed_s"] for row in requests)
                          if len(requests) == 2 and arm["forum_c1"]["completed"] else None)
        rates.append((category, values, None))
    rates.append(("Overall (two-pass mean)",
                  [arm["forum_c1"].get("mean_two_pass_end_to_end_tokens_s") for arm in arms], None))
    gates, latencies = [], []
    for key, label in (("tool-routing", "First tool decision"), ("agent-multiturn", "Fixed multi-turn"),
                       ("agent-generalization", "Seeded workflows")):
        summaries = [arm["suites"][key]["summary"] for arm in arms]
        gates.append((label, [100 * s["passed"] / s["total"] for s in summaries],
                      [f'{s["passed"]}/{s["total"]} ({100*s["passed"]/s["total"]:.1f}%)' for s in summaries]))
        latencies.append((label, [s["median_elapsed_s"] for s in summaries], None))
    ttft = []
    for suite, scenario, label in (("quick", "quick", "Quick response"),
            ("prefix", "prefix_first", "Prefix: first"), ("prefix", "prefix_repeat", "Prefix: repeat"),
            ("agent", "agent_first", "Agent prefix: first"), ("agent", "agent_followup", "Agent prefix: follow-up")):
        ttft.append((label, [arm["suites"][suite]["summary"]["scenarios"][scenario]["median_ttft_s"]
                            for arm in arms], None))
    return {
        "fp8-hybrid-throughput-and-outcomes.svg": document(
            "B2 versus FP8 hybrid: throughput and outcomes",
            [("Forum sgbench C1: end-to-end output rate", "tok/s", rates,
              "Two passes; includes prefill and TTFT. Per-category bars average two request rates."),
             ("Existing task success criteria", "%", gates,
              "Failures remain in denominators. Simulated tasks; no generated code was executed.")],
            "One host and finite runs. The throughput test does not establish output correctness."),
        "fp8-hybrid-latency-and-first-token.svg": document(
            "B2 versus FP8 hybrid: response latency",
            [("Median task/request latency", "s", latencies,
              "All recorded task outcomes, including failures; duration also depends on generated tokens and tool turns."),
             ("Median time to first streamed token", "s", ttft,
              "Quick: three runs. Prefix groups: five pairs; fresh markers differ across deployments.")],
            "Lower latency alone does not establish equal work, quality or cache-hit attribution."),
    }


if __name__ == "__main__":
    for filename, content in render(json.loads(DATA.read_text())).items():
        destination = ROOT / "docs/figures" / filename
        destination.write_text(content)
        print(destination)
