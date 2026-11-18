"""Make every image the Final Review deck uses. Real data only; nothing is invented.

Run from the repository root:
    python docs/ppt/make_ppt_figs.py

Writes into docs/ppt/figs/:
  * fig_agreement_alpha.png, fig_kl_scatter.png, fig_byzagent_lift.png
      the paper's own figures, made by running paper/figs/make_figs.py with larger fonts
      only (same data, colours and marks). The run's derived_values.json must equal the
      paper's, or the script stops.
  * fig_alpha_silos.png + alpha_silo_counts.csv
      share of each family per silo at alpha=0.1 and alpha=5.0 (seed 42), from
      data/processed/partitions/label_distribution_a{0.1,5.0}_s42.csv. The counts are
      checked cell by cell against the report's tables (docs/report/src/
      06a_appendix_data_model.md, tab:silo-a01-s42 and tab:silo-a50-s42) before plotting.
  * dash_live_alert.png, dash_trust.png, dash_hotswap_gate.png
      crops of the tracked dashboard screenshots in docs/dashboard_v2/screens/.
"""
import csv
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pymupdf  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "ppt", "figs")
os.makedirs(OUT, exist_ok=True)
R = lambda *p: os.path.join(ROOT, *p)  # noqa: E731

FAMILIES = ["Benign", "DoS", "DDoS", "PortScan", "BruteForce", "Bot", "WebAttack", "Infiltration", "Heartbleed"]
# Okabe-Ito, as in paper/figs/make_figs.py; Benign is light grey so the attack families stand out.
FAM_COLOUR = {"Benign": "#D9D9D9", "DoS": "#D55E00", "DDoS": "#E69F00", "PortScan": "#0072B2",
              "BruteForce": "#009E73", "Bot": "#CC79A7", "WebAttack": "#56B4E9",
              "Infiltration": "#F0E442", "Heartbleed": "#000000"}


def paper_figs_for_slides():
    """Re-run paper/figs/make_figs.py unchanged in its data and colours, with larger fonts
    and slightly larger canvases so the text reads at slide size. Output goes to a temp
    folder; its derived_values.json must equal the paper's, which proves the plotted
    values are identical."""
    import json
    import tempfile
    src = open(R("paper", "figs", "make_figs.py"), encoding="utf-8").read()
    tmp = tempfile.mkdtemp(prefix="xfed_ppt_figs_")
    subs = [
        ('OUT = os.path.join(ROOT, "paper", "figs")', f"OUT = {tmp!r}"),
        ("COL_W = 3.45", "COL_W = 3.45 * 1.12"),
        ('"font.size": 7.5', '"font.size": 11'), ('"axes.labelsize": 7.5', '"axes.labelsize": 11'),
        ('"axes.titlesize": 7.5', '"axes.titlesize": 11'), ('"legend.fontsize": 6.5', '"legend.fontsize": 9.5'),
        ('"xtick.labelsize": 7', '"xtick.labelsize": 10.5'), ('"ytick.labelsize": 7', '"ytick.labelsize": 10.5'),
        ("fontsize=6)", "fontsize=9.5)"), ("fontsize=6,", "fontsize=9.5,"), ("fontsize=5.5,", "fontsize=9,"),
    ]
    for a, b in subs:
        if a not in src:
            sys.exit(f"make_figs.py changed; cannot find {a!r}")
        src = src.replace(a, b)
    src = re.sub(r"figsize=\(COL_W, ([\d.]+)\)", lambda m: f"figsize=(COL_W, {float(m.group(1)) * 1.35:.3f})", src)
    ns = {"__file__": R("paper", "figs", "make_figs.py"), "__name__": "__slides__"}
    exec(compile(src, "make_figs_slides", "exec"), ns)
    plt.close("all")
    mine = json.load(open(os.path.join(tmp, "derived_values.json"), encoding="utf-8"))
    paper = json.load(open(R("paper", "figs", "derived_values.json"), encoding="utf-8"))
    if mine != paper:
        sys.exit("plotted values differ from paper/figs/derived_values.json")
    print("slide figures plot the same values as the paper (derived_values.json identical)")
    for name in ["fig_agreement_alpha", "fig_kl_scatter", "fig_byzagent_lift"]:
        doc = pymupdf.open(os.path.join(tmp, name + ".pdf"))
        pix = doc[0].get_pixmap(dpi=400, alpha=False)
        pix.save(os.path.join(OUT, name + ".png"))
        print(f"{name}.png  {pix.width}x{pix.height}")
        doc.close()


def read_counts(alpha):
    path = R("data", "processed", "partitions", f"label_distribution_a{alpha}_s42.csv")
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return {int(r["silo"]): {k: int(r[k]) for k in FAMILIES} for r in rows}


def report_table(label):
    """Parse a silo table from the report: rows '| silo | Benign | ... |'."""
    text = open(R("docs", "report", "src", "06a_appendix_data_model.md"), encoding="utf-8").read()
    start = text.index("{#" + label)
    lines = []
    for ln in text[start:].splitlines()[1:]:
        if not ln.startswith("|"):
            break  # the table ends at its first non-table line
        lines.append(ln)
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    out = {}
    for ln in lines[2:]:
        cells = [c.strip().replace(",", "").replace("*", "") for c in ln.strip("|").split("|")]
        if not re.fullmatch(r"\d+", cells[0]):
            continue
        out[int(cells[0])] = {h: int(v) for h, v in zip(header[1:], cells[1:]) if h in FAMILIES}
    return out


def alpha_figure():
    data = {}
    for alpha, label in [("0.1", "tab:silo-a01-s42"), ("5.0", "tab:silo-a50-s42")]:
        counts = read_counts(alpha)
        rep = report_table(label)
        for silo, fams in counts.items():
            for fam, n in fams.items():
                if rep[silo][fam] != n:
                    sys.exit(f"MISMATCH alpha={alpha} silo={silo} {fam}: csv {n} vs report {rep[silo][fam]}")
        data[alpha] = counts
    print("silo counts match the report tables (alpha 0.1 and 5.0, seed 42)")

    with open(os.path.join(OUT, "alpha_silo_counts.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["alpha", "seed", "silo"] + FAMILIES + ["total"])
        for alpha, counts in data.items():
            for silo in sorted(counts):
                row = [counts[silo][k] for k in FAMILIES]
                w.writerow([alpha, 42, silo] + row + [sum(row)])

    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial"],
                         "font.size": 15, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6), sharey=True)
    titles = {"0.1": "α = 0.1  (strong skew)", "5.0": "α = 5.0  (near-IID control)"}
    for ax, alpha in zip(axes, ["0.1", "5.0"]):
        counts = data[alpha]
        silos = sorted(counts)
        left = [0.0] * len(silos)
        for fam in FAMILIES:
            share = [counts[s][fam] / sum(counts[s].values()) for s in silos]
            ax.barh(silos, share, left=left, color=FAM_COLOUR[fam], edgecolor="white", linewidth=0.4,
                    label=fam, height=0.78)
            left = [a + b for a, b in zip(left, share)]
        ax.set_title(titles[alpha], fontsize=16, color="#572314", fontweight="bold")
        ax.set_xlim(0, 1)
        ax.set_xticks([0, 0.5, 1])
        ax.set_xticklabels(["0", "50%", "100%"])
        ax.set_xlabel("share of the silo's flows")
    axes[0].set_yticks(range(10))
    axes[0].invert_yaxis()  # shared y axis: invert once, silo 0 on top
    axes[0].set_ylabel("silo")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=9, fontsize=13, frameon=False,
               bbox_to_anchor=(0.5, -0.04), handlelength=1.0, columnspacing=0.8)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_alpha_silos.png"), dpi=300)
    plt.close(fig)
    print("fig_alpha_silos.png")


def crop(src, box, name):
    im = Image.open(R("docs", "dashboard_v2", "screens", src)).convert("RGB")
    im.crop(box).save(os.path.join(OUT, name))
    print(name, box)


if __name__ == "__main__":
    paper_figs_for_slides()
    alpha_figure()
    # Live route, Deep Sea theme, 1440 px: the selected alert with its LLM summary and SHAP bars
    crop("live_deep-sea_1440.png", (404, 259, 1027, 960), "dash_live_alert.png")
    # Live route: the trust-check panel (flag rate, clean run vs attack run)
    crop("live_deep-sea_1440.png", (1044, 259, 1412, 816), "dash_trust.png")
    # Hot-swap dialog: the validation gate rejecting a candidate
    crop("hotswap_rejected_detail_deep-sea.png", (460, 228, 981, 673), "dash_hotswap_gate.png")
