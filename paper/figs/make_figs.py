"""Generate every data figure in the paper from the results files on disk.

Run from the repository root:
    python paper/figs/make_figs.py

Writes PDF figures into paper/figs/ and paper/figs/derived_values.json, which
holds every value the figures plot plus the few aggregations the appendix
tables use that are not already stated in a results document (each entry names
its source file and how it was computed). Nothing is smoothed or invented;
figures use greyscale-safe styling (markers, hatching, line styles) so they
survive black-and-white printing.
"""
import csv
import json
import os
import statistics as st

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "paper", "figs")
R = lambda *p: os.path.join(ROOT, *p)  # noqa: E731

COL_W = 3.45  # IEEE column width, inches
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 7.5,
    "axes.labelsize": 7.5,
    "axes.titlesize": 7.5,
    "legend.fontsize": 6.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "axes.linewidth": 0.6,
    "lines.linewidth": 1.0,
    "pdf.fonttype": 42,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})
GREYS = ["0.0", "0.35", "0.6", "0.8"]
ALPHAS = ["0.1", "0.5", "5.0"]
SEEDS = [42, 1337, 2024]
derived = {}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def quartiles(xs):
    q = st.quantiles(xs, n=4, method="inclusive")
    return q[0], st.median(xs), q[2]


# ---------------------------------------------------------------- agreement
agree = [r for r in read_csv(R("results", "inspection", "agreement_metrics.csv")) if r["family_eligible"] == "True"]
by_alpha = {a: [r for r in agree if r["alpha"] == a] for a in ALPHAS}
headline = json.load(open(R("site", "public", "data", "headline.json"), encoding="utf-8"))
floor = headline["centralized_seed_instability_floor"]
chance = headline["chance_jaccard_at_10"]["value"]

d_alpha = {}
for a in ALPHAS:
    j = [float(r["jaccard_at_10"]) for r in by_alpha[a]]
    t = [float(r["kendall_weighted_tau"]) for r in by_alpha[a]]
    d_alpha[a] = {"n": len(j), "jaccard_at_10_q1_med_q3": quartiles(j), "tau_q1_med_q3": quartiles(t)}
derived["agreement_by_alpha_iqr"] = {
    "source": "results/inspection/agreement_metrics.csv, family_eligible==True rows; quartiles by statistics.quantiles(method='inclusive')",
    "values": d_alpha,
}

fams = ["Benign", "Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"]
d_fam = {}
for a in ALPHAS:
    for fam in fams:
        rows = [r for r in by_alpha[a] if r["family"] == fam]
        if len(rows) < 2:
            d_fam[f"{a}|{fam}"] = {"n": len(rows)}
            continue
        j = [float(r["jaccard_at_10"]) for r in rows]
        t = [float(r["kendall_weighted_tau"]) for r in rows]
        d_fam[f"{a}|{fam}"] = {"n": len(rows), "jaccard_at_10_q1_med_q3": quartiles(j), "tau_q1_med_q3": quartiles(t)}
derived["agreement_by_alpha_family_iqr"] = {
    "source": "results/inspection/agreement_metrics.csv, family_eligible==True rows, grouped by (alpha, family)",
    "values": d_fam,
}

fig, axes = plt.subplots(1, 2, figsize=(COL_W, 1.75))
for ax, col, key, title in [
    (axes[0], "jaccard_at_10", "jaccard_at_10", "(a) Jaccard@10"),
    (axes[1], "kendall_weighted_tau", "kendall_weighted_tau", r"(b) weighted Kendall's $\tau$"),
]:
    data = [[float(r[col]) for r in by_alpha[a]] for a in ALPHAS]
    if key == "jaccard_at_10":
        lo, hi = floor["jaccard_at_10_range"]
        ax.axhline(chance, color="0.2", ls=":", lw=0.9)
    else:
        lo, hi = floor["tau_range"]
    ax.axhspan(lo, hi, facecolor="0.85", edgecolor="0.4", hatch="////", lw=0.4, zorder=0)
    bp = ax.boxplot(data, widths=0.5, patch_artist=True, showfliers=False,
                    medianprops=dict(color="black", lw=1.4), whiskerprops=dict(lw=0.6),
                    capprops=dict(lw=0.6), boxprops=dict(lw=0.6))
    for b in bp["boxes"]:
        b.set_facecolor("white")
    meds = [st.median(x) for x in data]
    ax.plot([1, 2, 3], meds, "ko-", ms=3, lw=0.8, zorder=5)
    ax.set_xticks([1, 2, 3], [r"$\alpha$=0.1", "0.5", "5.0"])
    ax.set_ylim(0, 1.0)
    ax.set_title(title, pad=2)
    ax.grid(axis="y", lw=0.3, color="0.85")
axes[0].set_ylabel("silo vs. global agreement")
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
handles = [Patch(facecolor="0.85", edgecolor="0.4", hatch="////", lw=0.4, label="seed-noise floor (range)"),
           Line2D([], [], color="0.2", ls=":", lw=0.9, label="chance (Jaccard@10)"),
           Line2D([], [], color="black", marker="o", ms=3, lw=0.8, label="median")]
fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.07), handlelength=1.6)
fig.tight_layout(w_pad=0.8)
fig.savefig(os.path.join(OUT, "fig_agreement_alpha.pdf"))
plt.close(fig)
derived["fig_agreement_alpha"] = {
    "medians_jaccard": [st.median([float(r["jaccard_at_10"]) for r in by_alpha[a]]) for a in ALPHAS],
    "medians_tau": [st.median([float(r["kendall_weighted_tau"]) for r in by_alpha[a]]) for a in ALPHAS],
    "floor_jaccard_range": floor["jaccard_at_10_range"],
    "floor_tau_range": floor["tau_range"],
    "chance": chance,
    "source": "results/inspection/agreement_metrics.csv; site/public/data/headline.json (floor, chance)",
}

# ---------------------------------------------------------------- ByzAgent flag rates (ceiling effect)
def flag_rates(raw, cond):
    res = raw["results"][cond]
    counts = {f"silo_{i}": [0, 0] for i in range(10)}
    for rnd, payload in res.items():
        for dcs in payload["decisions"]:
            c = counts[dcs["client_id"]]
            c[1] += 1
            c[0] += dcs["decision"] in ("downweight", "quarantine")
    return {k: v[0] / v[1] for k, v in counts.items()}


raw42 = json.load(open(R("results", "inspection", "phase3_gate_raw_a0.5_s42.json"), encoding="utf-8"))
rawms = json.load(open(R("results", "inspection", "multiseed_agent_gate_raw.json"), encoding="utf-8"))
pairs = {
    42: (flag_rates(raw42, "clean"), flag_rates(raw42, "f3_{0,3,5}")),
    1337: (flag_rates(rawms, "s1337_clean"), flag_rates(rawms, "s1337_sudden")),
    2024: (flag_rates(rawms, "s2024_clean"), flag_rates(rawms, "s2024_sudden")),
}
d_lift = {}
for s, (c, a) in pairs.items():
    for silo in (0, 3, 5):
        k = f"silo_{silo}"
        d_lift[f"{s}|{silo}"] = {"clean": round(c[k], 4), "attack": round(a[k], 4), "lift": round(a[k] - c[k], 4)}
derived["byzagent_flag_rates_malicious"] = {
    "source": "results/inspection/phase3_gate_raw_a0.5_s42.json (clean, f3_{0,3,5}); results/inspection/multiseed_agent_gate_raw.json (s1337/s2024 clean, sudden); flag = downweight or quarantine, share of 20 rounds",
    "values": d_lift,
}

fig, ax = plt.subplots(figsize=(COL_W, 1.55))
ypos, labels = [], []
y = 0
markers = {0: "o", 3: "s", 5: "^"}
for s in SEEDS:
    for silo in (0, 3, 5):
        v = d_lift[f"{s}|{silo}"]
        ax.plot([v["clean"], v["attack"]], [y, y], color="0.45", lw=1.0, zorder=1)
        ax.scatter([v["clean"]], [y], marker=markers[silo], facecolor="white", edgecolor="black", s=36, lw=0.7, zorder=2)
        ax.scatter([v["attack"]], [y], marker=markers[silo], facecolor="black", edgecolor="black", s=12, lw=0.7, zorder=3)
        ypos.append(y)
        labels.append(f"seed {s}, silo {silo}")
        y += 1
    y += 0.6
ax.set_yticks(ypos, labels, fontsize=6)
ax.invert_yaxis()
ax.set_xlim(-0.05, 1.05)
ax.set_xlabel("share of 20 rounds flagged (downweight or quarantine)")
ax.grid(axis="x", lw=0.3, color="0.85")
ax.scatter([], [], marker="o", facecolor="white", edgecolor="black", s=14, label="clean run (no attack)")
ax.scatter([], [], marker="o", facecolor="black", edgecolor="black", s=14, label="sudden attack, f=3")
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, handletextpad=0.2)
fig.savefig(os.path.join(OUT, "fig_byzagent_lift.pdf"))
plt.close(fig)

# ---------------------------------------------------------------- FedAvg validation curves (round lottery)
fig, axes = plt.subplots(1, 3, figsize=(7.1, 1.6), sharey=True)
styles = {42: ("-", "o"), 1337: ("--", "s"), 2024: (":", "^")}
lot = {(r["alpha"], int(r["seed"])): r for r in read_csv(R("results", "federated", "round_lottery_val.csv"))}
for ax, a in zip(axes, ALPHAS):
    for s in SEEDS:
        h = json.load(open(R("results", "federated", f"fedavg_a{a}_s{s}", "round_history.json"), encoding="utf-8"))
        xs = [p["round"] for p in h if p["round"] >= 1]
        ys = [p["val_macro_f1_headline"] for p in h if p["round"] >= 1]
        ls, mk = styles[s]
        ax.plot(xs, ys, color="black", ls=ls, lw=0.8, label=f"seed {s}")
        b = lot[(a, s)]
        ax.plot([int(b["best_round"])], [float(b["best_val"])], marker=mk, color="black", ms=3.5, mfc="white")
    ax.set_title(rf"FedAvg, $\alpha$={a}", pad=2)
    ax.set_xlabel("round")
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.grid(lw=0.3, color="0.85")
axes[0].set_ylabel("val macro-F1 (7 headline)")
axes[0].legend(frameon=False, loc="lower right")
fig.tight_layout(w_pad=0.5)
fig.savefig(os.path.join(OUT, "fig_val_curves.pdf"))
plt.close(fig)

# ---------------------------------------------------------------- round-wise agreement vs val F1
rw = read_csv(R("results", "inspection", "round_wise_agreement.csv"))
rounds = [5, 10, 15, 20]
fig, axes = plt.subplots(1, 2, figsize=(COL_W, 1.6))
d_rw = {}
for a, (ls, mk) in zip(ALPHAS, [("-", "o"), ("--", "s"), (":", "^")]):
    mj = []
    mf = []
    for rd in rounds:
        rows = [float(r["jaccard_at_10"]) for r in rw if r["alpha"] == a and int(r["round"]) == rd]
        mj.append(st.mean(rows))
        f1s = []
        for s in SEEDS:
            h = json.load(open(R("results", "federated", f"fedavg_a{a}_s{s}", "round_history.json"), encoding="utf-8"))
            f1s.append([p for p in h if p["round"] == rd][0]["val_macro_f1_headline"])
        mf.append(st.mean(f1s))
    d_rw[a] = {"mean_jaccard": mj, "mean_val_f1": mf}
    axes[0].plot(rounds, mj, color="black", ls=ls, marker=mk, ms=3, mfc="white", label=rf"$\alpha$={a}")
    axes[1].plot(rounds, mf, color="black", ls=ls, marker=mk, ms=3, mfc="white")
axes[0].set_title("(a) mean Jaccard@10", pad=2)
axes[1].set_title("(b) mean val macro-F1", pad=2)
for ax in axes:
    ax.set_xticks(rounds)
    ax.set_xlabel("round")
    ax.grid(lw=0.3, color="0.85")
axes[0].legend(frameon=False, fontsize=6)
fig.tight_layout(w_pad=0.8)
fig.savefig(os.path.join(OUT, "fig_round_wise.pdf"))
plt.close(fig)
derived["round_wise"] = {"source": "results/inspection/round_wise_agreement.csv (mean over silos and seeds); results/federated/fedavg_a*_s*/round_history.json (mean val F1 over seeds)", "values": d_rw}

# ---------------------------------------------------------------- KL vs agreement scatter
smh = read_csv(R("results", "inspection", "size_matched_heterogeneity.csv"))
fig, axes = plt.subplots(1, 2, figsize=(COL_W, 1.6), sharey=True)
for ax, a in zip(axes, ["0.1", "0.5"]):
    rows = [r for r in smh if r["alpha"] == a and r["jaccard_at_10"] not in ("", "nan")]
    for s, mk in zip(SEEDS, ["o", "s", "^"]):
        xs = [float(r["kl_from_global"]) for r in rows if int(r["seed"]) == s]
        ys = [float(r["jaccard_at_10"]) for r in rows if int(r["seed"]) == s]
        ax.scatter(xs, ys, marker=mk, facecolor="white" if s != 42 else "black", edgecolor="black", s=10, lw=0.6, label=f"seed {s}")
    ax.set_title(rf"$\alpha$={a} (n={len(rows)})", pad=2)
    ax.set_xlabel("KL(silo labels || global)")
    ax.grid(lw=0.3, color="0.85")
axes[0].set_ylabel("Jaccard@10 vs. global")
axes[1].legend(frameon=False, fontsize=5.5, loc="upper right")
fig.tight_layout(w_pad=0.6)
fig.savefig(os.path.join(OUT, "fig_kl_scatter.pdf"))
plt.close(fig)

# ---------------------------------------------------------------- Phase 0: clean vs poisoned validation curves
runs = [
    ("fedavg_a0.5_s42", "clean", "-"),
    ("fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5", "sudden f=3 {0,3,5}", "--"),
    ("fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3", "sudden f=2 {0,3}", ":"),
    ("fedavg_a0.5_s42_poisoned_f3_gradual_silos0-3-5", "gradual f=3 {0,3,5}", "-."),
]
fig, ax = plt.subplots(figsize=(COL_W, 1.7))
for tag, lab, ls in runs:
    h = json.load(open(R("results", "federated", tag, "round_history.json"), encoding="utf-8"))
    xs = [p["round"] for p in h if p["round"] >= 1]
    ys = [p["val_macro_f1_headline"] for p in h if p["round"] >= 1]
    ax.plot(xs, ys, color="black" if ls != ":" else "0.35", ls=ls, lw=0.9, label=lab)
ax.axvspan(15.5, 20.5, color="0.9", zorder=0)
ax.text(18, 0.42, "final-5\nwindow", ha="center", fontsize=6)
ax.set_xlabel("round")
ax.set_ylabel("val macro-F1")
ax.set_xticks([1, 5, 10, 15, 20])
ax.grid(lw=0.3, color="0.85")
ax.legend(frameon=False, fontsize=6, loc="lower center", ncol=2)
fig.savefig(os.path.join(OUT, "fig_phase0_curves.pdf"))
plt.close(fig)

with open(os.path.join(OUT, "derived_values.json"), "w", encoding="utf-8") as f:
    json.dump(derived, f, indent=1)
print("figures written to", OUT)
