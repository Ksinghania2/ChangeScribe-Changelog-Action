"""Draw the architecture diagram and the processing flowchart used in the report."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "assets")
IND, LIGHT, GREEN, AMBER = "#4f46e5", "#eef2ff", "#dcfce7", "#fef3c7"


def box(ax, x, y, w, h, text, fc=LIGHT, ec=IND, fs=8, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, p, q, label=None, style="-|>"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=13, lw=1.3, color="#334155"))
    if label:
        ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + .12, label, ha="center", fontsize=7.5, color="#475569")


def architecture():
    fig, ax = plt.subplots(figsize=(12.5, 5.6)); ax.set_xlim(0, 12); ax.set_ylim(0, 6.2); ax.axis("off")
    box(ax, .2, 4.4, 2.2, 1.1, "GitHub REST API\nPRs - comments - commits", GREEN, "#16a34a")
    box(ax, .2, 2.7, 2.2, 1.1, "Local git clone\n git log --numstat", GREEN, "#16a34a")
    box(ax, 3.2, 3.4, 2.0, 1.6, "1. Collector\nnormalises to\nChange objects", bold=True)
    box(ax, 5.9, 3.4, 2.2, 1.6, "2. Parser\nclassify - de-noise\nextract why - chunk", bold=True)
    box(ax, 8.8, 3.4, 2.2, 1.6, "3. Summarizer\nLLM writer or\noffline heuristic", bold=True)
    box(ax, 8.8, 1.0, 2.2, 1.4, "4. Renderer\nKeep-a-Changelog\nMarkdown", bold=True)
    box(ax, 5.6, 1.0, 2.5, 1.4, "Outputs\nCHANGELOG.md\nREADME block - Web UI", AMBER, "#d97706")
    box(ax, 8.8, 5.3, 2.2, .75, "Anthropic Messages API", "#fce7f3", "#db2777", fs=8)
    box(ax, 2.9, 0.9, 2.2, 1.5, "Interfaces\nCLI - Flask web app\nGitHub Action - Docker", "#e0f2fe", "#0284c7")
    arrow(ax, (2.4, 4.95), (3.2, 4.5)); arrow(ax, (2.4, 3.25), (3.2, 4.0))
    arrow(ax, (5.2, 4.2), (5.9, 4.2), "Change[]"); arrow(ax, (8.1, 4.2), (8.8, 4.2), "chunks")
    arrow(ax, (9.9, 3.4), (9.9, 2.4), "Entry[]"); arrow(ax, (8.8, 1.7), (8.1, 1.7))
    arrow(ax, (9.9, 5.3), (9.9, 5.0), style="<|-|>")
    arrow(ax, (5.1, 1.7), (5.6, 1.7), style="<|-")
    ax.text(4.2, 6.0, "ChangeScribe - system architecture", ha="center", fontsize=12, fontweight="bold")
    fig.savefig(os.path.join(OUT, "architecture.png"), dpi=170, bbox_inches="tight"); plt.close(fig)


def flowchart():
    fig, ax = plt.subplots(figsize=(6.2, 8.6)); ax.set_xlim(0, 10); ax.set_ylim(0, 14); ax.axis("off")
    cx = 5
    def node(y, text, fc=LIGHT, ec=IND, w=4.6, h=.95):
        box(ax, cx - w / 2, y, w, h, text, fc, ec, fs=8.5)
    def dia(y, text):
        ax.add_patch(plt.Polygon([(cx, y + 1.0), (cx + 2.5, y + .5), (cx, y), (cx - 2.5, y + .5)], fc=AMBER, ec="#d97706", lw=1.4))
        ax.text(cx, y + .5, text, ha="center", va="center", fontsize=8)
    node(13, "Start: repo + time window", GREEN, "#16a34a")
    dia(11.6, "Source?")
    node(10.2, "GitHub API: merged PRs,\nreview comments, direct commits", w=3.7)
    ax.text(2.0, 11.7, "GitHub", fontsize=8); ax.text(7.8, 11.7, "local", fontsize=8)
    node(8.8, "Normalise to Change objects")
    dia(7.4, "Noise commit?")
    node(6.0, "Classify (prefix, label,\nkeyword, file path) + find 'why'")
    node(4.6, "Chunk into token-bounded batches")
    dia(3.2, "API key set & call OK?")
    node(1.8, "Write entry:\nLLM sentence + impact", w=2.4)
    node(.4, "Render Markdown, update\nCHANGELOG.md / README block", GREEN, "#16a34a")
    ax.add_patch(FancyBboxPatch((7.6, 1.8), 2.2, .95, boxstyle="round,pad=0.02,rounding_size=0.12", fc=LIGHT, ec=IND, lw=1.4))
    ax.text(8.7, 2.27, "Offline\nheuristic entry", ha="center", va="center", fontsize=8)
    ax.add_patch(FancyBboxPatch((7.6, 7.45), 2.2, .6, boxstyle="round,pad=0.02,rounding_size=0.12", fc="#fee2e2", ec="#dc2626", lw=1.4))
    ax.text(8.7, 7.75, "Discard", ha="center", va="center", fontsize=8)
    for a, b in [((cx, 13), (cx, 12.6)), ((cx, 10.2 + .95), (cx, 10.2 + .95)), ((cx, 10.2), (cx, 9.75)),
                 ((cx, 8.8), (cx, 8.4)), ((cx, 7.4), (cx, 6.95)), ((cx, 6.0), (cx, 5.55)),
                 ((cx, 4.6), (cx, 4.2)), ((cx, 3.2), (cx, 2.75)), ((cx, 1.8), (cx, 1.35))]:
        if a != b: arrow(ax, a, b)
    arrow(ax, (cx, 11.6), (cx, 11.15)); arrow(ax, (7.5, 11.95), (7.5, 9.2)); arrow(ax, (7.5, 9.27), (7.3, 9.27))
    arrow(ax, (7.5, 7.9), (7.6, 7.75)); ax.text(7.55, 8.15, "yes", fontsize=7.5)
    ax.text(cx + .1, 6.85, "no", fontsize=7.5)
    arrow(ax, (7.5, 3.7), (8.7, 3.7)); arrow(ax, (8.7, 3.7), (8.7, 2.75)); ax.text(7.7, 3.85, "no", fontsize=7.5)
    ax.text(cx + .1, 2.9, "yes", fontsize=7.5)
    arrow(ax, (8.7, 1.8), (8.7, 1.0)); arrow(ax, (8.7, 1.0), (7.3, .9))
    fig.savefig(os.path.join(OUT, "flowchart.png"), dpi=170, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    architecture(); flowchart(); print("diagrams written")
