"""Generate the handbook's SVG diagrams into docs/handbook/img/.

Data-driven figures read their numbers from files on disk at build time:
  fig03  data/processed/partitions/label_distribution_a{0.1,5.0}_s42.csv
  fig13  results/federated/fedavg_a5.0_s42/round_history.json
Every other figure is either a schematic (labelled as such in its caption) or
draws numbers that the handbook text quotes with a source, copied verbatim.
Stdlib only. Run from the repo root:  python docs/handbook/build/make_figures.py
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "handbook" / "img"
OUT.mkdir(parents=True, exist_ok=True)

INK, MUTE, LINE = "#1f2937", "#6b7280", "#d1d5db"
BLUE, RED, GREEN, AMBER, PURPLE, TEAL = "#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0d9488"
FAM_COL = {"Benign": "#9ca3af", "Bot": "#7c3aed", "BruteForce": "#d97706", "DDoS": "#dc2626",
           "DoS": "#f97316", "Heartbleed": "#111827", "Infiltration": "#0d9488",
           "PortScan": "#2563eb", "WebAttack": "#db2777"}
FONT = "font-family:Inter,'Segoe UI',Arial,sans-serif"


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'style="{FONT}">\n<rect width="{w}" height="{h}" fill="#ffffff"/>\n'
            f'<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{MUTE}"/></marker></defs>\n'
            + body + "\n</svg>\n")


def t(x, y, s, size=13, fill=INK, anchor="start", weight="400", italic=False):
    st = ' font-style="italic"' if italic else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}"{st}>{escape(str(s))}</text>')


def box(x, y, w, h, fill="#f3f4f6", stroke=LINE, r=8, sw=1.2):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def line(x1, y1, x2, y2, col=MUTE, sw=1.5, arrow=False, dash=None):
    a = ' marker-end="url(#ar)"' if arrow else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{sw}"{a}{d}/>'


def labelled_box(x, y, w, h, title, lines=(), fill="#f3f4f6", stroke=LINE, tcol=INK, size=14):
    out = [box(x, y, w, h, fill, stroke), t(x + w / 2, y + 24, title, size, tcol, "middle", "700")]
    for i, l in enumerate(lines):
        out.append(t(x + w / 2, y + 44 + i * 17, l, 12, MUTE, "middle"))
    return "\n".join(out)


def write(name, content):
    (OUT / name).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------- fig01 pipeline
def fig01():
    b = []
    b.append(labelled_box(250, 15, 300, 76, "1. Data", ["Distrinet CICIDS2017 V4", "8 families + Benign"], "#eff6ff", BLUE))
    b.append(line(400, 91, 400, 110, arrow=True))
    b.append(labelled_box(250, 112, 300, 76, "2. Federated training", ["10 orgs · Flower · FedAvg", "α ∈ {0.1, 0.5, 5.0} × 3 seeds"], "#eff6ff", BLUE))
    b.append(line(340, 188, 200, 215, arrow=True))
    b.append(line(460, 188, 600, 215, arrow=True))
    b.append(labelled_box(40, 217, 320, 96, "3. Explanation check", ["client-side SHAP, top-k only", "Jaccard@10 · weighted τ", "vs chance and seed-noise floor"], "#f0fdf4", GREEN))
    b.append(labelled_box(440, 217, 320, 96, "4. Trust check (ByzAgent)", ["LLM: trust / downweight / quarantine", "vs Krum, Multi-Krum, trimmed mean", "rationale fidelity audited"], "#fef2f2", RED))
    b.append(t(400, 262, "separate", 11, MUTE, "middle", italic=True))
    b.append(t(400, 276, "experiments", 11, MUTE, "middle", italic=True))
    b.append(line(200, 313, 340, 344, arrow=True))
    b.append(line(600, 313, 460, 344, arrow=True))
    b.append(labelled_box(250, 346, 300, 66, "5. Dashboard", ["FastAPI + React · Live / Investigate / Limits"], "#faf5ff", PURPLE))
    write("fig01_pipeline.svg", svg(800, 422, "\n".join(b)))


# ---------------------------------------------------------------- fig02 rounds
def fig02():
    b = [labelled_box(300, 20, 200, 64, "Server", ["global model w"], "#eff6ff", BLUE)]
    xs = [40, 190, 340, 490, 640]
    labels = ["Org 1", "Org 2", "Org 3", "…", "Org 10"]
    for x, lab in zip(xs, labels):
        if lab == "…":
            b.append(t(x + 60, 225, "…", 22, MUTE, "middle"))
            continue
        b.append(box(x, 190, 120, 70, "#f9fafb"))
        b.append(t(x + 60, 214, lab, 14, INK, "middle", "700"))
        b.append(t(x + 60, 233, "private traffic", 11, MUTE, "middle"))
        b.append(t(x + 60, 250, "3 local epochs", 11, MUTE, "middle"))
        b.append(line(395, 84, x + 50, 188, BLUE, 1.3, True))
        b.append(line(x + 70, 188, 405, 86, GREEN, 1.3, True, "5,3"))
    b.append(t(120, 120, "① send global weights", 12, BLUE))
    b.append(t(540, 120, "③ send updated weights", 12, GREEN))
    b.append(t(400, 290, "② each org trains on its own data — raw traffic never leaves", 12, INK, "middle"))
    b.append(t(400, 312, "④ server: FedAvg weighted mean → score on validation → checkpoint → repeat (20 rounds)", 12, INK, "middle"))
    write("fig02_rounds.svg", svg(800, 330, "\n".join(b)))


# ---------------------------------------------------------------- fig03 alpha (real data)
def fig03():
    fams = ["Benign", "Bot", "BruteForce", "DDoS", "DoS", "Heartbleed", "Infiltration", "PortScan", "WebAttack"]
    b = []
    y0 = 30
    for k, alpha in enumerate(["0.1", "5.0"]):
        path = ROOT / f"data/processed/partitions/label_distribution_a{alpha}_s42.csv"
        rows = list(csv.DictReader(path.open()))
        top = y0 + k * 200
        b.append(t(20, top + 12, f"α = {alpha}, seed 42", 14, INK, "start", "700"))
        for i, r in enumerate(rows):
            x = 120 + i * 64
            counts = [int(r[f]) for f in fams]
            tot = sum(counts) or 1
            yy = top + 160
            for f, c in zip(fams, counts):
                h = 140 * c / tot
                if h <= 0:
                    continue
                yy -= h
                b.append(f'<rect x="{x}" y="{yy:.2f}" width="44" height="{h:.2f}" fill="{FAM_COL[f]}"/>')
            b.append(t(x + 22, top + 176, f"silo {r['silo']}", 10, MUTE, "middle"))
        b.append(line(115, top + 160, 760, top + 160, LINE, 1))
    lx = 120
    for f in fams:
        b.append(f'<rect x="{lx}" y="420" width="10" height="10" fill="{FAM_COL[f]}"/>')
        b.append(t(lx + 14, 429, f, 10, INK))
        lx += 72
    b.append(t(20, 450, "Each bar is one silo's flows, shown as shares of that silo. Source: data/processed/partitions/label_distribution_a{α}_s42.csv", 10, MUTE))
    write("fig03_alpha.svg", svg(800, 460, "\n".join(b)))


# ---------------------------------------------------------------- fig04 splits
def fig04():
    b = [box(40, 40, 720, 46, "#f3f4f6"), t(400, 68, "1,913,502 cleaned flows", 14, INK, "middle", "700")]
    b.append(line(250, 86, 250, 118, arrow=True)); b.append(line(640, 86, 640, 118, arrow=True))
    b.append(box(40, 120, 520, 50, "#eff6ff", BLUE)); b.append(t(300, 150, "train pool 1,435,126 (75%)", 13, INK, "middle", "700"))
    b.append(box(580, 120, 180, 50, "#fef2f2", RED)); b.append(t(670, 142, "test 478,376 (25%)", 13, RED, "middle", "700"))
    b.append(t(670, 160, "scored once per checkpoint", 10, MUTE, "middle"))
    b.append(line(200, 170, 200, 205, arrow=True)); b.append(line(480, 170, 480, 205, arrow=True))
    b.append(box(40, 207, 360, 50, "#eff6ff", BLUE)); b.append(t(220, 237, "training rows → 10 silos (Dirichlet α)", 13, INK, "middle"))
    b.append(box(420, 207, 140, 50, "#f0fdf4", GREEN)); b.append(t(490, 229, "validation 10%", 13, GREEN, "middle", "700"))
    b.append(t(490, 246, "143,513 rows", 10, MUTE, "middle"))
    b.append(t(400, 290, "Both splits are group-aware: identical feature vectors never straddle a boundary.", 12, MUTE, "middle"))
    b.append(t(400, 308, "Every model / round / setting choice is made on validation.", 12, MUTE, "middle"))
    write("fig04_splits.svg", svg(800, 320, "\n".join(b)))


# ---------------------------------------------------------------- fig05 MLP
def fig05():
    b = []
    layers = [(80, 9, "82 features", "input"), (290, 10, "128", "ReLU · LayerNorm · dropout 0.1"),
              (500, 7, "64", "ReLU · LayerNorm · dropout 0.1"), (700, 9, "9 logits", "one per class")]
    pts = []
    for x, n, lab, sub in layers:
        ys = [60 + i * (220 / (n - 1)) for i in range(n)]
        pts.append((x, ys))
    for (x1, y1s), (x2, y2s) in zip(pts, pts[1:]):
        for a in y1s:
            for c in y2s:
                b.append(line(x1, a, x2, c, "#e5e7eb", 0.6))
    for (x, ys), (_, n, lab, sub) in zip(pts, layers):
        for y in ys:
            b.append(f'<circle cx="{x}" cy="{y:.1f}" r="7" fill="#eff6ff" stroke="{BLUE}" stroke-width="1.4"/>')
        b.append(t(x, 312, lab, 13, INK, "middle", "700"))
        b.append(t(x, 330, sub, 10, MUTE, "middle"))
    b.append(t(400, 30, "MLP [128, 64] · 19,849 parameters (configs/model.yaml) · dots are not to scale", 12, MUTE, "middle"))
    write("fig05_mlp.svg", svg(800, 345, "\n".join(b)))


# ---------------------------------------------------------------- fig06 softmax (illustrative)
def fig06():
    logits = [4.0, 1.0, 0.5, 0.2, -1.0, -2.0, -2.0, -0.5, 0.0]
    import math
    e = [math.exp(z) for z in logits]
    p = [v / sum(e) for v in e]
    names = ["DDoS", "DoS", "PortScan", "Benign", "Bot", "Heartbleed", "Infiltr.", "BruteF.", "WebAtt."]
    b = [t(200, 25, "logits (raw scores)", 13, INK, "middle", "700"), t(600, 25, "softmax probabilities", 13, INK, "middle", "700")]
    for i, (n, z, q) in enumerate(zip(names, logits, p)):
        y = 45 + i * 26
        b.append(t(70, y + 13, n, 11, INK, "end"))
        x0 = 200
        w = z * 25
        b.append(f'<rect x="{min(x0, x0 + w)}" y="{y}" width="{abs(w)}" height="16" fill="{BLUE if z >= 0 else LINE}"/>')
        b.append(t(470, y + 13, n, 11, INK, "end"))
        b.append(f'<rect x="480" y="{y}" width="{q * 260:.1f}" height="16" fill="{GREEN}"/>')
    b.append(line(200, 40, 200, 285, MUTE, 1))
    b.append(line(340, 160, 395, 160, MUTE, 1.5, True))
    b.append(t(400, 300, "Illustrative values, not from any model. Probabilities sum to 1; the leader is exaggerated.", 11, MUTE, "middle"))
    write("fig06_softmax.svg", svg(800, 310, "\n".join(b)))


# ---------------------------------------------------------------- fig07 imbalance (data/README.md §5)
def fig07():
    import math
    data = [("Benign", 1440899), ("PortScan", 186160), ("DoS", 177491), ("DDoS", 95144), ("BruteForce", 6972),
            ("Bot", 4703), ("WebAttack", 2056), ("Infiltration", 66), ("Heartbleed", 11)]
    b = []
    mx = math.log10(2_000_000)
    for i, (n, c) in enumerate(data):
        y = 20 + i * 30
        w = 520 * math.log10(c) / mx
        col = FAM_COL[n]
        b.append(t(130, y + 15, n, 12, INK, "end"))
        b.append(f'<rect x="140" y="{y}" width="{w:.1f}" height="20" fill="{col}"/>')
        b.append(t(146 + w, y + 15, f"{c:,}", 11, MUTE))
    fx = 140 + 520 * 3 / mx
    b.append(line(fx, 15, fx, 290, RED, 1.2, False, "4,3"))
    b.append(t(fx + 4, 300, "1,000-flow floor", 11, RED))
    b.append(t(400, 318, "Log scale. Source: data/README.md §5.", 11, MUTE, "middle"))
    write("fig07_imbalance.svg", svg(800, 328, "\n".join(b)))


# ---------------------------------------------------------------- fig08 SHAP bill (illustrative)
def fig08():
    steps = [("base value E[f]", 0, 1.0), ("Flow Packets/s", 1.0, 2.6), ("Fwd Packet Length Std", 2.6, 3.5),
             ("Flow Duration", 3.5, 3.1), ("Init Win Bytes", 3.1, 3.7), ("other features", 3.7, 4.0)]
    b = [t(400, 22, "Sharing the bill: each feature's SHAP value moves the output up (red) or down (teal)", 13, INK, "middle", "700")]
    sc = 120
    for i, (n, a, z) in enumerate(steps):
        y = 40 + i * 36
        b.append(t(210, y + 17, n, 12, INK, "end"))
        if i == 0:
            b.append(f'<rect x="220" y="{y}" width="{z * sc}" height="22" fill="{LINE}"/>')
            continue
        col = RED if z > a else TEAL
        x = 220 + min(a, z) * sc
        b.append(f'<rect x="{x}" y="{y}" width="{abs(z - a) * sc}" height="22" fill="{col}"/>')
        b.append(t(x + abs(z - a) * sc + 6, y + 16, ("+" if z > a else "−") + "share", 11, MUTE))
    y = 40 + 6 * 36
    b.append(f'<rect x="220" y="{y}" width="{4.0 * sc}" height="22" fill="{INK}"/>')
    b.append(t(210, y + 17, "model output f(x)", 12, INK, "end", "700"))
    b.append(t(400, 300, "base value + Σ SHAP = output (additivity). Illustrative values, not from any model.", 11, MUTE, "middle"))
    write("fig08_shap_bill.svg", svg(800, 310, "\n".join(b)))


# ---------------------------------------------------------------- fig09 Jaccard (made-up lists)
def fig09():
    shared = ["Flow Pkts/s", "Fwd Pkt Len Std", "Pkt Len Var", "Bwd Pkt Len Std", "Flow Duration", "Init Win Bytes", "Pkt Len Max"]
    a_only = ["Flow IAT Mean", "SYN Flag Cnt", "Fwd IAT Std"]
    b_only = ["Subflow Fwd Bytes", "ACK Flag Cnt", "Bwd IAT Max"]
    b = [f'<ellipse cx="300" cy="190" rx="220" ry="150" fill="{BLUE}" fill-opacity="0.08" stroke="{BLUE}"/>',
         f'<ellipse cx="500" cy="190" rx="220" ry="150" fill="{GREEN}" fill-opacity="0.08" stroke="{GREEN}"/>',
         t(170, 30, "Model A top-10", 13, BLUE, "middle", "700"), t(630, 30, "Model B top-10", 13, GREEN, "middle", "700")]
    for i, f in enumerate(a_only):
        b.append(t(190, 150 + i * 30, f, 11, INK, "middle"))
    for i, f in enumerate(b_only):
        b.append(t(610, 150 + i * 30, f, 11, INK, "middle"))
    for i, f in enumerate(shared):
        b.append(t(400, 100 + i * 25, f, 11, INK, "middle", "700"))
    b.append(t(400, 368, "shared = 7 · union = 10 + 10 − 7 = 13 · Jaccard@10 = 7/13. Made-up lists for teaching.", 12, INK, "middle"))
    write("fig09_jaccard.svg", svg(800, 380, "\n".join(b)))


# ---------------------------------------------------------------- fig10 number line (values from contribution_a §2)
def fig10():
    X = lambda v: 60 + v * 680
    b = [line(X(0), 120, X(1), 120, INK, 1.5)]
    for v in [0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        b.append(line(X(v), 115, X(v), 125, INK, 1)); b.append(t(X(v), 142, f"{v:.1f}", 11, MUTE, "middle"))
    b.append(f'<rect x="{X(0.429)}" y="70" width="{X(0.484) - X(0.429)}" height="50" fill="{PURPLE}" fill-opacity="0.18" stroke="{PURPLE}"/>')
    b.append(t(X(0.456), 62, "seed-noise floor 0.429–0.484", 11, PURPLE, "middle", "700"))
    b.append(line(X(0.065), 80, X(0.065), 120, MUTE, 1.5, False, "4,3"))
    b.append(t(X(0.065), 72, "chance 0.065", 11, MUTE, "middle"))
    b.append(line(X(0.250), 100, X(0.429), 100, RED, 3))
    for v, lab, col in [(0.333, "α=0.1  0.333", RED), (0.538, "α=0.5  0.538", BLUE), (0.667, "α=5.0  0.667", GREEN)]:
        b.append(f'<circle cx="{X(v)}" cy="100" r="7" fill="{col}"/>')
        b.append(t(X(v), 175, lab, 12, col, "middle", "700"))
    b.append(t(X(0.34), 195, "red bar: α=0.1 cluster-bootstrap CI [0.250, 0.429] — touches the floor", 11, RED, "middle"))
    b.append(t(400, 222, "Median Jaccard@10 (source: docs/contribution_a_results.md §2)", 11, MUTE, "middle"))
    write("fig10_numberline.svg", svg(800, 232, "\n".join(b)))


# ---------------------------------------------------------------- fig11 Krum (schematic)
def fig11():
    honest = [(260, 150), (285, 175), (240, 185), (300, 140), (270, 205), (230, 160)]
    unusual = [(520, 90), (560, 230)]
    attack = [(470, 300), (110, 270)]
    b = [t(400, 24, "Krum: score each update by distance to its nearest neighbours; keep the most central one", 13, INK, "middle", "700")]
    for p in honest:
        b.append(line(270, 175, p[0], p[1], LINE, 1))
    for (x, y) in honest:
        b.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{BLUE}"/>')
    b.append(f'<circle cx="270" cy="175" r="16" fill="none" stroke="{GREEN}" stroke-width="2.5"/>')
    b.append(t(270, 240, "kept (most central)", 11, GREEN, "middle", "700"))
    for (x, y) in unusual:
        b.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{AMBER}"/>')
    for (x, y) in attack:
        b.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{RED}"/>')
    b.append(t(560, 70, "honest but unusual traffic mix", 11, AMBER, "middle"))
    b.append(t(470, 330, "attacker", 11, RED, "middle"))
    lx = 620
    for col, lab in [(BLUE, "typical honest org"), (AMBER, "honest, unusual (non-IID)"), (RED, "attacker")]:
        b.append(f'<circle cx="{lx}" cy="{150 + [BLUE, AMBER, RED].index(col) * 24}" r="7" fill="{col}"/>')
        b.append(t(lx + 14, 155 + [BLUE, AMBER, RED].index(col) * 24, lab, 11, INK))
    b.append(t(400, 360, "Under non-IID data, unusual honest orgs sit as far out as attackers. Schematic, not data.", 11, MUTE, "middle"))
    write("fig11_krum.svg", svg(800, 372, "\n".join(b)))


# ---------------------------------------------------------------- fig12 Multi-Krum vs trimmed mean (schematic)
def fig12():
    b = [t(200, 24, "Multi-Krum (n − f kept)", 14, INK, "middle", "700"), t(600, 24, "Trimmed mean (per weight)", 14, INK, "middle", "700")]
    for i in range(10):
        y = 45 + i * 24
        drop = i in (3, 8, 9)
        b.append(box(110, y, 180, 18, "#fee2e2" if drop else "#eff6ff", RED if drop else BLUE, 4))
        b.append(t(200, y + 13, f"org {i}  {'dropped whole' if drop else 'kept'}", 11, INK, "middle"))
    vals = [0.2, 0.25, 0.3, 0.31, 0.33, 0.35, 0.4, 0.42, 0.9, -0.5]
    s = sorted(vals)
    for i, v in enumerate(s):
        x = 430 + i * 34
        cut = i < 2 or i >= 8
        b.append(box(x, 120, 28, 28, "#fee2e2" if cut else "#f0fdf4", RED if cut else GREEN, 4))
        b.append(t(x + 14, 139, f"{v:+.1f}".replace("+", ""), 9, INK, "middle"))
    b.append(t(600, 105, "one weight's 10 values, sorted", 11, MUTE, "middle"))
    b.append(t(600, 175, "drop the lowest and highest β·n, average the rest,", 11, INK, "middle"))
    b.append(t(600, 192, "repeat for every weight independently", 11, INK, "middle"))
    b.append(t(400, 300, "Schematic, made-up values. Both rules need f (the number of attackers) in advance.", 11, MUTE, "middle"))
    write("fig12_multikrum_trim.svg", svg(800, 312, "\n".join(b)))


# ---------------------------------------------------------------- fig13 round lottery (real data)
def fig13():
    hist = json.loads((ROOT / "results/federated/fedavg_a5.0_s42/round_history.json").read_text())
    pts = [(h["round"], h["val_macro_f1_headline"]) for h in hist]
    X = lambda r: 70 + r * 33
    Y = lambda v: 290 - v * 230
    b = [line(70, 290, 740, 290, INK, 1), line(70, 50, 70, 290, INK, 1)]
    for v in [0, 0.25, 0.5, 0.75, 1.0]:
        b.append(line(66, Y(v), 740, Y(v), "#f3f4f6", 1)); b.append(t(60, Y(v) + 4, f"{v:.2f}", 10, MUTE, "end"))
    for r in range(0, 21, 2):
        b.append(t(X(r), 306, str(r), 10, MUTE, "middle"))
    d = " ".join(f"{'M' if i == 0 else 'L'}{X(r):.1f},{Y(v):.1f}" for i, (r, v) in enumerate(pts))
    b.append(f'<path d="{d}" fill="none" stroke="{BLUE}" stroke-width="2"/>')
    best = max(pts, key=lambda p: p[1])
    last = pts[-1]
    for (r, v), col, lab in [(best, GREEN, f"best round {best[0]}: {best[1]:.4f}"), (last, RED, f"round {last[0]}: {last[1]:.4f}")]:
        b.append(f'<circle cx="{X(r)}" cy="{Y(v)}" r="6" fill="{col}"/>')
    b.append(t(X(best[0]) - 10, Y(best[1]) + 20, f"best round {best[0]}: {best[1]:.4f}", 11, GREEN, "end", "700"))
    b.append(t(X(last[0]) - 10, Y(last[1]) + 38, f"round {last[0]}: {last[1]:.4f}", 11, RED, "end", "700"))
    b.append(t(405, 324, "round", 11, MUTE, "middle"))
    b.append(t(400, 20, "FedAvg α=5.0 seed 42 — validation macro-F1 per round (four decimals for display)", 12, INK, "middle", "700"))
    b.append(t(400, 342, "Source: results/federated/fedavg_a5.0_s42/round_history.json", 10, MUTE, "middle"))
    write("fig13_round_lottery.svg", svg(800, 352, "\n".join(b)))


# ---------------------------------------------------------------- fig14 explanation pipeline
def fig14():
    b = [box(20, 20, 360, 300, "#f9fafb"), t(200, 44, "inside each organization (×10, plus global)", 12, MUTE, "middle", "700")]
    steps = ["14 fixed eval rows (2 per family)", "own scaler → own model", "GradientExplainer, nsamples=4000",
             "200-row seeded background (own train data)", "SHAP of the true class", "rank → top-k list"]
    for i, s in enumerate(steps):
        y = 60 + i * 42
        b.append(box(45, y, 310, 30, "#ffffff", BLUE, 6)); b.append(t(200, y + 20, s, 12, INK, "middle"))
        if i:
            b.append(line(200, y - 12, 200, y, MUTE, 1.2, True))
    b.append(line(380, 290, 450, 170, GREEN, 2, True))
    b.append(t(415, 260, "top-k only", 11, GREEN, "middle", "700"))
    b.append(box(455, 60, 320, 230, "#f0fdf4", GREEN))
    b.append(t(615, 86, "server", 13, INK, "middle", "700"))
    for i, s in enumerate(["eligibility (silo ≥ 400, family ≥ 20)", "Jaccard@10, weighted τ vs global", "median per α",
                           "compare with chance 0.065", "and seed-noise floor 0.429", "parity monitor (N≥3 draws)"]):
        b.append(t(615, 116 + i * 28, s, 12, INK, "middle"))
    write("fig14_expl_pipeline.svg", svg(800, 340, "\n".join(b)))


# ---------------------------------------------------------------- fig15 ByzAgent loop
def fig15():
    b = [labelled_box(30, 40, 200, 90, "10 orgs train", ["(3 poisoned in attack runs)"], "#f9fafb"),
         labelled_box(300, 40, 200, 90, "5 statistics / org", ["update_norm · cosines", "train_loss · val_accuracy"], "#eff6ff", BLUE),
         labelled_box(570, 40, 200, 90, "ByzAgent (LLM)", ["llama3.1:8b, local", "temperature 0.2"], "#fef2f2", RED),
         labelled_box(570, 200, 200, 90, "JSON decisions", ["trust / downweight / quarantine", "+ rationale per org"], "#fef2f2", RED),
         labelled_box(300, 200, 200, 90, "weights", ["trust 1× · downweight 0.3×", "quarantine 0×"], "#f9fafb"),
         labelled_box(30, 200, 200, 90, "audit (offline)", ["citation accuracy", "decision correlation, stability"], "#faf5ff", PURPLE)]
    b += [line(230, 85, 298, 85, arrow=True), line(500, 85, 568, 85, arrow=True), line(670, 130, 670, 198, arrow=True),
          line(568, 245, 502, 245, arrow=True), line(300, 245, 232, 245, MUTE, 1.5, True, "4,3")]
    b.append(t(400, 320, "Never in the prompt: true attacker identity, oracle f, which statistic is strongest.", 12, RED, "middle"))
    b.append(t(400, 338, "Reported numbers are replays of logged statistics, not a live run where decisions drove training.", 11, MUTE, "middle"))
    write("fig15_byzagent_loop.svg", svg(800, 350, "\n".join(b)))


# ---------------------------------------------------------------- fig16 confound (contribution_b §5)
def fig16():
    rows = [("0", "9.2%", 0.95, 1.00, "malicious"), ("3", "0.3%", 1.00, 1.00, "malicious"), ("5", "0.1%", 1.00, 1.00, "malicious"),
            ("8", "12.3%", 0.95, 1.00, "never malicious")]
    X = lambda v: 330 + v * 380
    b = [t(400, 22, "Seed 42: flag rate with no attack (open) vs under f=3 attack (filled)", 13, INK, "middle", "700")]
    for v in [0, 0.5, 1.0]:
        b.append(line(X(v), 40, X(v), 205, "#f3f4f6", 1)); b.append(t(X(v), 222, f"{v:.1f}", 10, MUTE, "middle"))
    for i, (s, ben, c, a, role) in enumerate(rows):
        y = 60 + i * 34
        col = RED if role == "malicious" else AMBER
        b.append(t(40, y + 5, f"silo {s}", 12, INK, "start", "700"))
        b.append(t(110, y + 5, f"{ben} Benign", 11, MUTE))
        b.append(t(210, y + 5, role, 11, col))
        b.append(line(X(c), y, X(a), y, col, 2))
        b.append(f'<circle cx="{X(c)}" cy="{y}" r="7" fill="#fff" stroke="{col}" stroke-width="2"/>')
        b.append(f'<circle cx="{X(a)}" cy="{y}" r="6" fill="{col}"/>')
    y = 60 + 4 * 34
    b.append(t(40, y + 5, "silos 1,2,4,6,7,9", 12, INK, "start", "700"))
    b.append(t(170, y + 5, "81.5–98.0% Benign · clean 0.00–0.25 · f=3 0.00–0.05", 11, MUTE))
    b.append(t(400, 245, "The four lowest-Benign silos are flagged almost always, attack or not. Source: docs/contribution_b_results.md §5", 10, MUTE, "middle"))
    write("fig16_confound.svg", svg(800, 255, "\n".join(b)))


# ---------------------------------------------------------------- fig17 dumbbell (contribution_b §7)
def fig17():
    rows = [("silo 0", "42", 0.95, 1.00), ("silo 3", "42", 1.00, 1.00), ("silo 5", "42", 1.00, 1.00),
            ("silo 0", "1337", 0.05, 0.10), ("silo 3", "1337", 0.00, 0.40), ("silo 5", "1337", 0.00, 0.95),
            ("silo 0", "2024", 0.00, 0.35), ("silo 3", "2024", 1.00, 0.95), ("silo 5", "2024", 0.25, 1.00)]
    X = lambda v: 220 + v * 460
    b = [t(400, 22, "Malicious silos: clean-run flag rate (open) → sudden-attack flag rate (filled)", 13, INK, "middle", "700")]
    for v in [0, 0.25, 0.5, 0.75, 1.0]:
        b.append(line(X(v), 38, X(v), 352, "#f3f4f6", 1)); b.append(t(X(v), 368, f"{v:.2f}", 10, MUTE, "middle"))
    for i, (s, seed, c, a) in enumerate(rows):
        y = 52 + i * 34 + (int(i / 3) * 6)
        lift = a - c
        col = GREEN if lift >= 0.3 else (AMBER if c >= 0.9 else MUTE)
        b.append(t(70, y + 5, s, 12, INK, "start", "700"))
        b.append(t(130, y + 5, f"seed {seed}", 11, MUTE))
        b.append(line(X(c), y, X(a), y, col, 3))
        b.append(f'<circle cx="{X(c)}" cy="{y}" r="7" fill="#fff" stroke="{col}" stroke-width="2"/>')
        b.append(f'<circle cx="{X(a)}" cy="{y}" r="6" fill="{col}"/>')
        b.append(t(705, y + 5, f"{c:.2f} → {a:.2f}", 11, INK))
    b.append(t(400, 388, "green: large lift (attack-responsive) · amber: baseline already ≥ 0.90 (ceiling). Source: docs/contribution_b_results.md §5, §7; MULTISEED_VALIDATION_SUMMARY.md", 10, MUTE, "middle"))
    write("fig17_dumbbell.svg", svg(800, 398, "\n".join(b)))


# ---------------------------------------------------------------- fig18 prereg timeline (git history, 2026-10-12)
def fig18():
    ev = [("b2b9bee", "rule: test once, for one preregistered config"), ("ad249bd", "Part 1: rule + candidates, before any run"),
          ("c58d91f", "budget cut revised before any result"), ("65ab660", "timing-only budget guard"),
          ("c5abcaf", "validation grid → fedavgm_m0.9 selected"), ("212f8de", "α=5.0 validation runs"),
          ("1a17277", "SEAL: 9 checkpoints hashed, committed"), ("b21a4bf", "single test evaluation + results")]
    b = [line(60, 60, 60, 60 + 7 * 40, BLUE, 3)]
    for i, (h, s) in enumerate(ev):
        y = 60 + i * 40
        col = RED if h in ("1a17277", "b21a4bf") else BLUE
        b.append(f'<circle cx="60" cy="{y}" r="8" fill="{col}"/>')
        b.append(t(80, y + 5, h, 12, MUTE))
        b.append(t(160, y + 5, s, 13, INK, "start", "700" if col == RED else "400"))
    b.append(box(560, 50, 210, 120, "#f0fdf4", GREEN))
    b.append(t(665, 76, "validation only", 13, GREEN, "middle", "700"))
    b.append(t(665, 98, "method path has no", 11, INK, "middle"))
    b.append(t(665, 114, "test evaluation at all", 11, INK, "middle"))
    b.append(box(560, 250, 210, 80, "#fef2f2", RED))
    b.append(t(665, 276, "test set touched once", 13, RED, "middle", "700"))
    b.append(t(665, 298, "script refuses a second run", 11, INK, "middle"))
    b.append(t(400, 30, "All on 2026-10-12, in commit order (git log)", 12, MUTE, "middle"))
    write("fig18_prereg_timeline.svg", svg(800, 360, "\n".join(b)))


# ---------------------------------------------------------------- fig19 funnel (data/README.md §4.5)
def fig19():
    st = [("raw flows", 2099976, "#9ca3af"), ("− Inf/NaN (5)", 2099971, "#9ca3af"), ("− family conflicts (44,005)", 2055966, AMBER),
          ("− cross-file duplicates (142,464)", 1913502, BLUE)]
    b = []
    for i, (lab, n, col) in enumerate(st):
        w = 600 * n / 2099976
        y = 25 + i * 52
        b.append(f'<rect x="{400 - w / 2:.1f}" y="{y}" width="{w:.1f}" height="38" rx="6" fill="{col}" fill-opacity="0.85"/>')
        b.append(t(400, y + 24, f"{lab}: {n:,}", 13, "#ffffff", "middle", "700"))
    b.append(t(400, 245, "Retained 1,913,502 (8.88% dropped). Source: data/README.md §4.5", 11, MUTE, "middle"))
    write("fig19_funnel.svg", svg(800, 256, "\n".join(b)))


# ---------------------------------------------------------------- fig20 dashboard architecture
def fig20():
    b = [labelled_box(20, 60, 180, 100, "simulator", ["replays 500 validation", "SHAP-pool rows", "(test blocked)"], "#f0fdf4", GREEN),
         labelled_box(270, 30, 260, 160, "FastAPI backend", ["served model fedavg_a0.5_s42 r18", "ONNX fp32 (startup gate)", "SHAP pool + LLM summaries",
                                                              "results files → /source", "hot-swap worker (subprocess)"], "#eff6ff", BLUE),
         labelled_box(600, 60, 180, 100, "React frontend", ["Live · Investigate", "Limits", "3 themes"], "#faf5ff", PURPLE)]
    b += [line(200, 110, 268, 110, arrow=True), line(530, 110, 598, 110, arrow=True), t(565, 100, "/api", 11, MUTE, "middle")]
    b.append(t(400, 220, "Every number in the UI links to the results file it was read from.", 12, MUTE, "middle"))
    write("fig20_dashboard_arch.svg", svg(800, 232, "\n".join(b)))


# ---------------------------------------------------------------- fig21 hot-swap gate
def fig21():
    b = [labelled_box(10, 50, 150, 80, "analyst", ["confirms family"], "#f9fafb"),
         labelled_box(195, 50, 160, 80, "pick ≤200 rows", ["train rows of that", "family (no val rows)"], "#f9fafb"),
         labelled_box(390, 50, 170, 80, "warm start", ["from BASE model", "2 rounds × 3 epochs"], "#eff6ff", BLUE),
         labelled_box(595, 40, 190, 100, "gate", ["candidate val macro-F1", "≥ incumbent?", "(no tolerance)"], "#fffbeb", AMBER),
         labelled_box(470, 200, 150, 64, "accept", ["swap + banner"], "#f0fdf4", GREEN),
         labelled_box(640, 200, 150, 64, "reject", ["keep incumbent"], "#fef2f2", RED)]
    b += [line(160, 90, 193, 90, arrow=True), line(355, 90, 388, 90, arrow=True), line(560, 90, 593, 90, arrow=True),
          line(660, 140, 560, 198, GREEN, 1.5, True), line(715, 140, 715, 198, RED, 1.5, True)]
    b.append(t(300, 240, "every attempt → append-only audit log; one-click revert", 12, MUTE, "middle"))
    write("fig21_hotswap.svg", svg(800, 280, "\n".join(b)))


# ---------------------------------------------------------------- fig22 test exposure (docs/test_set_exposure_audit.md)
def fig22():
    items = [("headline: one eval of each validation-selected checkpoint", "no choice"),
             ("3 recorded rationales cite test (epochs, μ, scaler)", "re-checked on val"),
             ("(a) legacy client-side scoring, 35 runs", "unread"),
             ("(b) round-20 scoring for old round lottery", "superseded"),
             ("(c) 14 fixed rows as SHAP inputs", "inputs only"),
             ("(d) 514 display rows; simulator before 2026-10-13", "display only"),
             ("(e) 18 centralized pilot/baseline runs, 3 XGBoost seeds", "development"),
             ("(f) one preregistered evaluation (FedAvgM)", "sealed first")]
    b = [box(20, 20, 160, 330, "#fef2f2", RED), t(100, 170, "test set", 14, RED, "middle", "700"), t(100, 190, "478,376 rows", 11, MUTE, "middle")]
    for i, (s, v) in enumerate(items):
        y = 30 + i * 40
        col = AMBER if i == 1 else (GREEN if i in (0, 7) else MUTE)
        b.append(line(180, 185, 220, y + 14, LINE, 1))
        b.append(box(222, y, 420, 28, "#ffffff", LINE, 5)); b.append(t(232, y + 19, s, 11, INK))
        b.append(t(655, y + 19, v, 11, col, "start", "700"))
    write("fig22_test_exposure.svg", svg(800, 370, "\n".join(b)))


# ---------------------------------------------------------------- fig23 repo map
def fig23():
    groups = [("configs/", "every parameter", BLUE), ("data/", "decision record", BLUE), ("federated/", "Flower app (authoritative)", BLUE),
              ("src/", "data, models, attacks, agents, hotswap", BLUE), ("tools/", "SHAP, metrics, audits", GREEN),
              ("scripts/", "checks, phase gates", GREEN), ("results/", "every number's file", AMBER), ("docs/", "canonical results", AMBER),
              ("backend/", "FastAPI", PURPLE), ("frontend/", "React dashboard", PURPLE), ("site/", "showcase site", PURPLE), ("film/", "explainer film", PURPLE)]
    b = []
    for i, (n, d, col) in enumerate(groups):
        x = 20 + (i % 4) * 195
        y = 20 + (i // 4) * 80
        b.append(box(x, y, 180, 62, "#ffffff", col, 8, 1.6))
        b.append(t(x + 90, y + 26, n, 14, col, "middle", "700"))
        b.append(t(x + 90, y + 46, d, 11, MUTE, "middle"))
    write("fig23_repo.svg", svg(800, 262, "\n".join(b)))


def copy_pngs():
    for name in ["agreement_vs_alpha", "agreement_vs_round", "accuracy_agreement_decoupling", "entropy_kl_partial_correlation",
                 "fedprox_vs_fedavg_per_seed", "parity_monitor", "deletion_curve", "insertion_curve", "instability_floor_vs_alpha"]:
        src = ROOT / "results" / "figures" / f"{name}.png"
        if src.exists():
            shutil.copyfile(src, OUT / f"{name}.png")


if __name__ == "__main__":
    for f in [fig01, fig02, fig03, fig04, fig05, fig06, fig07, fig08, fig09, fig10, fig11, fig12, fig13, fig14, fig15,
              fig16, fig17, fig18, fig19, fig20, fig21, fig22, fig23]:
        f()
    copy_pngs()
    print("figures:", len(list(OUT.glob("*.svg"))), "svg,", len(list(OUT.glob("*.png"))), "png")
