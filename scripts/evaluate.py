"""Reproducible offline evaluation on the labelled synthetic sprint.

    python scripts/evaluate.py            # writes docs/assets/metrics.json + charts
"""
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import make_demo_repo  # noqa: E402
from changescribe import collector, parser, renderer, summarizer  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "assets")
CATS = ["feature", "fix", "perf", "refactor", "docs", "test", "build", "breaking", "chore"]


def main():
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        make_demo_repo.build(d)
        truth = {t["id"]: t for t in json.load(open(os.path.join(d, ".gold.json")))}
        t0 = time.perf_counter()
        raw = collector.collect_local(d, collector.parse_since("30d"))
        t_collect = time.perf_counter() - t0
        original = {c.id: c.title for c in raw}
        conventional = {i for i, t in original.items() if parser.CONVENTIONAL.match(t)}
        raw_chars = sum(len(c.title) + len(c.body) for c in raw)

        t1 = time.perf_counter()
        kept = parser.process(raw)
        entries = summarizer.HeuristicSummarizer().summarize(kept)
        md = renderer.render_section(entries, "Eval")
        t_process = time.perf_counter() - t1

    kept_ids = {c.id for c in kept}
    # --- noise filtering
    gold_noise = {i for i, t in truth.items() if t["gold_noise"]}
    dropped = set(truth) - kept_ids
    tp = len(dropped & gold_noise)
    noise_p = tp / len(dropped) if dropped else 1.0
    noise_r = tp / len(gold_noise)
    # --- classification (only genuine changes that were kept)
    pairs = []
    for c in kept:
        t = truth[c.id]
        pred = "breaking" if c.breaking else c.category
        pairs.append((t["gold_category"], pred, c.id in conventional))
    acc = sum(g == p for g, p, _ in pairs) / len(pairs)
    conv = [g == p for g, p, cv in pairs if cv]
    free = [g == p for g, p, cv in pairs if not cv]
    per_cat = {}
    for cat in CATS:
        tp_c = sum(1 for g, p, _ in pairs if g == cat and p == cat)
        pred_c = sum(1 for _, p, _ in pairs if p == cat)
        gold_c = sum(1 for g, _, _ in pairs if g == cat)
        prec = tp_c / pred_c if pred_c else 0.0
        rec = tp_c / gold_c if gold_c else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_cat[cat] = {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3), "support": gold_c}
    macro_f1 = sum(v["f1"] for v in per_cat.values() if v["support"]) / sum(1 for v in per_cat.values() if v["support"])
    # --- rationale ("why") capture
    gold_reason = {i for i, t in truth.items() if t["gold_has_reason"]}
    got_reason = {c.id for c in kept if c.rationale}
    reason_r = len(gold_reason & got_reason) / len(gold_reason)
    reason_fp = len(got_reason - gold_reason)
    # --- compression / readability
    out_chars = len(md)
    metrics = {
        "commits_total": len(truth),
        "commits_kept": len(kept),
        "noise_precision": round(noise_p, 3), "noise_recall": round(noise_r, 3),
        "classification_accuracy": round(acc, 3),
        "accuracy_conventional": round(sum(conv) / len(conv), 3), "n_conventional": len(conv),
        "accuracy_freeform": round(sum(free) / len(free), 3), "n_freeform": len(free),
        "macro_f1": round(macro_f1, 3), "per_category": per_cat,
        "rationale_recall": round(reason_r, 3), "rationale_false_positives": reason_fp,
        "raw_chars": raw_chars, "output_chars": out_chars,
        "entries_written": len(entries),
        "collect_ms": round(t_collect * 1000, 1), "process_ms": round(t_process * 1000, 1),
        "baseline": {"noise_in_output": len(gold_noise), "entries_with_reason": 0, "categories": 0},
    }
    json.dump(metrics, open(os.path.join(OUT, "metrics.json"), "w"), indent=2)
    with open(os.path.join(OUT, "sample_output.md"), "w") as fh:
        fh.write(md)
    print(json.dumps(metrics, indent=2))
    charts(metrics, pairs)


def charts(m, pairs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    ind, red, grey = "#4f46e5", "#e11d48", "#94a3b8"

    # 1 per-category precision / recall
    cats = [c for c in CATS if m["per_category"][c]["support"]]
    x = range(len(cats))
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ax.bar([i - .2 for i in x], [m["per_category"][c]["precision"] for c in cats], .4, label="Precision", color=ind)
    ax.bar([i + .2 for i in x], [m["per_category"][c]["recall"] for c in cats], .4, label="Recall", color="#a5b4fc")
    ax.set_xticks(list(x)); ax.set_xticklabels(cats, rotation=25); ax.set_ylim(0, 1.1)
    ax.set_title("Category classification quality"); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "chart_per_category.png"), dpi=160); plt.close(fig)

    # 2 raw log vs generated changelog
    fig, ax = plt.subplots(figsize=(6, 3.6))
    labels = ["Commits in\nraw log", "Noise lines\nremoved", "Entries in\nchangelog"]
    vals = [m["commits_total"], m["commits_total"] - m["commits_kept"], m["entries_written"]]
    b = ax.bar(labels, vals, color=[grey, red, ind])
    for r, v in zip(b, vals):
        ax.text(r.get_x() + r.get_width() / 2, v + .5, str(v), ha="center")
    ax.set_title("From raw history to changelog"); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "chart_reduction.png"), dpi=160); plt.close(fig)

    # 3 accuracy by commit style + overall metrics
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    names = ["Conventional\ncommits", "Free-form\ncommits", "Overall\naccuracy", "Macro F1", "Rationale\nrecall"]
    vals = [m["accuracy_conventional"], m["accuracy_freeform"], m["classification_accuracy"], m["macro_f1"], m["rationale_recall"]]
    b = ax.bar(names, vals, color=[ind, "#818cf8", "#4338ca", "#a5b4fc", "#0ea5e9"])
    for r, v in zip(b, vals):
        ax.text(r.get_x() + r.get_width() / 2, v + .02, f"{v:.0%}", ha="center")
    ax.set_ylim(0, 1.12); ax.set_title("Offline-backend accuracy on labelled sprint"); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "chart_accuracy.png"), dpi=160); plt.close(fig)


if __name__ == "__main__":
    main()
