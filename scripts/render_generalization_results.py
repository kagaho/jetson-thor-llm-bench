#!/usr/bin/env python3
"""Render curated numeric benchmark evidence; Matplotlib is a rendering-only dependency.

The benchmark and offline test suite do not import or require Matplotlib.
This script reads the reviewed docs/data fixture, never raw model responses.
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/data/2026-11-08-generalization-observations.json"
SVG_NS = "http://www.w3.org/2000/svg"
STEM = "agent-generalization-{kind}-2026-11-08"


def render(data: dict, output_dir: Path, preview_dir: Path | None = None) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    summary = data["summary"]
    cases = list(summary["cases"].items())
    background, foreground, muted = "#122032", "#E7EEF8", "#B7C6DB"
    green, red, blue = "#31C9BC", "#F08E83", "#729AF8"
    output_dir.mkdir(parents=True, exist_ok=True)
    if preview_dir:
        preview_dir.mkdir(parents=True, exist_ok=True)

    with plt.rc_context({"font.family": "DejaVu Sans", "svg.fonttype": "none",
                         "svg.hashsalt": "thorbench-generalization-20261108"}):
        for kind in ("outcomes", "latency"):
            fig, ax = plt.subplots(figsize=(12, 6), facecolor=background)
            fig.subplots_adjust(left=.28, right=.77, top=.70, bottom=.23)
            ax.set_facecolor(background)
            ax.set_yticks(range(len(cases)), [name for name, _ in cases], color=foreground)
            ax.set_ylim(len(cases) - .5, -.5)
            ax.tick_params(axis="both", colors=muted, labelsize=10, length=0, pad=9)
            ax.spines[["top", "right", "left"]].set_visible(False)
            ax.spines["bottom"].set_color(muted)
            ax.set_axisbelow(True)
            ax.grid(axis="x", color=muted, alpha=.18)
            title = "Seeded simulated-agent " + ("outcomes" if kind == "outcomes" else "latency")
            fig.text(.04, .93, title, color="white", fontsize=23, weight="bold")
            fig.text(.04, .875, f"Scorer {data['scorer_version']} | protocol {data['protocol_version']} | "
                     f"seed {data['seed']}", color=muted, fontsize=11)
            descriptions = []
            if kind == "outcomes":
                fig.text(.04, .82, f"{summary['passed']}/{summary['total']} heuristic passes "
                         f"({summary['passed'] / summary['total']:.1%}); all episodes included",
                         color=foreground, fontsize=12)
                for i, (name, case) in enumerate(cases):
                    passed, failed = case["passed"], case["total"] - case["passed"]
                    ax.barh(i, passed, color=green, height=.54)
                    ax.barh(i, failed, left=passed, color=red, height=.54)
                    ax.text(5.12, i, f"{passed} passed / {failed} failed", color=foreground,
                            va="center", fontsize=10)
                    descriptions.append(f"{name}: {passed} passed, {failed} failed")
                ax.set_xlim(0, 5)
                ax.set_xticks(range(6))
                ax.set_xlabel("Episodes per family", color=muted, labelpad=12)
                handles = [Patch(color=green, label="Passed"), Patch(color=red, label="Failed")]
                footer = "All five failures: excessive_verbosity on the no-tool control."
            else:
                fig.text(.04, .82, f"Overall median {summary['median_elapsed_s']:.2f} s | "
                         f"p90 {summary['p90_elapsed_s']:.2f} s; failures included",
                         color=foreground, fontsize=12)
                for i, (name, case) in enumerate(cases):
                    median, p90 = case["median_elapsed_s"], case["p90_elapsed_s"]
                    ax.barh(i, median, color=blue, height=.50)
                    ax.plot([median, p90], [i, i], color=green, linewidth=2)
                    ax.scatter([p90], [i], color=green, marker="D", s=35, zorder=3)
                    ax.text(61.5, i, f"{median:.2f} / {p90:.2f} s", color=foreground,
                            va="center", fontsize=10)
                    descriptions.append(f"{name}: median {median:.4f} s, p90 {p90:.4f} s")
                ax.set_xlim(0, 60)
                ax.set_xticks(range(0, 61, 10))
                ax.set_xlabel("Whole-episode latency (seconds)", color=muted, labelpad=12)
                handles = [Patch(color=blue, label="Median"),
                           Line2D([0], [0], color=green, marker="D", label="p90")]
                footer = "Runtime conditions were uncontrolled; lower latency does not establish correctness."
            fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(.275, .79),
                       ncol=2, frameon=False, labelcolor=foreground, fontsize=10)
            fig.text(.04, .10, footer, color=muted, fontsize=10)
            fig.text(.04, .055, "Five variants of six public templates; no real code or tests executed. "
                     "This is a scorer 0.7.2 measurement.", color=muted, fontsize=10)

            # Accessible, numeric descriptions and no timestamp in the exported SVG.
            output = io.StringIO()
            fig.savefig(output, format="svg", metadata={"Date": None, "Creator": "thorbench"})
            root = ET.fromstring(output.getvalue())
            root.set("role", "img")
            root.set("aria-labelledby", "chart-title chart-description")
            heading = ET.Element(f"{{{SVG_NS}}}title", {"id": "chart-title"})
            heading.text = title + f"; scorer {data['scorer_version']}; seed {data['seed']}"
            description = ET.Element(f"{{{SVG_NS}}}desc", {"id": "chart-description"})
            description.text = "; ".join(descriptions) + ". " + footer
            root.insert(0, heading)
            root.insert(1, description)
            ET.register_namespace("", SVG_NS)
            destination = output_dir / (STEM.format(kind=kind) + ".svg")
            destination.write_text(ET.tostring(root, encoding="unicode") + "\n", encoding="utf-8")
            if preview_dir:
                fig.savefig(preview_dir / (kind + ".png"), dpi=120, facecolor=background)
            plt.close(fig)
            print(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/figures")
    parser.add_argument("--preview-dir", type=Path)
    args = parser.parse_args()
    render(json.loads(DATA.read_text(encoding="utf-8")), args.output_dir, args.preview_dir)


if __name__ == "__main__":
    main()
