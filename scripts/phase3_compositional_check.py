"""ByzAgent Phase 3, Step 3b supplement -- per-silo, cross-condition flag-rate
breakdown, checking whether ByzAgent's malicious-flag-rate=1.0 result is
confounded by the same compositional-extremity axis Phase 2 found for
Krum/trimmed-mean (PHASE2_SUMMARY.md's "OPEN ITEM FOR 01_PLANNING"), rather
than assuming it away. No new LLM calls -- reads the same raw replay output
scripts/phase3_analysis.py already consumed, plus the existing Phase 0/2
composition table.
"""
import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Pilli\Capstone\xfed-ids")
RAW_PATH = PROJECT_ROOT / "results/inspection/phase3_gate_raw_a0.5_s42.json"
COMPOSITION_PATH = PROJECT_ROOT / "results/inspection/silo_family_composition_a0.5_s42.csv"
OUT_PATH = PROJECT_ROOT / "results/inspection/phase3_compositional_check_a0.5_s42.json"

raw = json.loads(RAW_PATH.read_text())
conditions = raw["conditions"]
results = raw["results"]

# per-silo flag rate per condition
flag_rate = {}  # silo_num -> condition -> rate
for cond_name, cond_results in results.items():
    counts = {i: 0 for i in range(10)}
    totals = {i: 0 for i in range(10)}
    for round_str, rd in cond_results.items():
        for d in rd["decisions"]:
            silo_num = int(d["client_id"].split("_")[1])
            totals[silo_num] += 1
            if d["decision"] in ("downweight", "quarantine"):
                counts[silo_num] += 1
    for i in range(10):
        flag_rate.setdefault(i, {})[cond_name] = counts[i] / totals[i] if totals[i] else None

# composition context, if the file exists (Phase 0/2 artifact)
composition = {}
if COMPOSITION_PATH.exists():
    with open(COMPOSITION_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = int(row["silo"])
            total = int(row["TOTAL"])
            benign = int(row["Benign"])
            row["pct_benign"] = round(100 * benign / total, 1) if total else None
            composition[sid] = row

print(f"{'silo':>4} {'malicious_in':>16} {'clean_FPR':>10} {'f3_rate':>10} {'f2_rate':>10}  composition")
table_rows = []
for i in range(10):
    mal_in = []
    for cond_name, cond_meta in conditions.items():
        if i in cond_meta["malicious_silos"]:
            mal_in.append(cond_name)
    comp = composition.get(i, {})
    comp_str = ""
    if comp:
        comp_str = f"benign%={comp.get('pct_benign')} rows={comp.get('TOTAL')}"
    row = {
        "silo": i,
        "malicious_in": mal_in,
        "clean_flag_rate": flag_rate[i].get("clean"),
        "f3_flag_rate": flag_rate[i].get("f3_{0,3,5}"),
        "f2_flag_rate": flag_rate[i].get("f2_{0,3}"),
        "composition_row": comp,
    }
    table_rows.append(row)
    print(f"{i:>4} {','.join(mal_in) or '-':>16} "
          f"{flag_rate[i].get('clean'):>10.2f} "
          f"{flag_rate[i].get('f3_{0,3,5}'):>10.2f} "
          f"{flag_rate[i].get('f2_{0,3}'):>10.2f}  {comp_str}")

OUT_PATH.write_text(json.dumps(table_rows, indent=2))
print(f"\nWrote {OUT_PATH}")
