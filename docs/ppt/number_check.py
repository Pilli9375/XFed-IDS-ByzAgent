"""Check every number in the Final Review deck against the repo files named for its slide.

Run from the repository root (after docs/ppt/build_ppt.py):
    python docs/ppt/number_check.py

Reads docs/ppt/XFed_Capstone_Final_Review.pptx (slide text, tables and speaker notes) and
docs/ppt/slide_sources.json (the source files for each slide, and for each line of the demo
script). For every number it looks in that slide's source files. A number matches when
  (1) its exact text (thousands separators removed) occurs in a source as a separate number, or
  (2) a source holds a number that rounds to it at the same number of decimals, or
  (3) for a version string such as 2.13.0, the exact string occurs in a source.
Signs are compared on magnitude (the sign of each negative value was checked by hand).
Not counted, because they are names, not quantities: metric and dataset names (Jaccard@10,
CICIDS2017, V4, SHA256), number formats (fp32, fp16, int8, 4-bit), the model name
llama3.1:8b-instruct-q4_K_M, macro-F1 / F1, registration numbers, run names
(fedavg_a0.5_s42), bibliography markers [n], slide numbers, and times in the demo table.

Writes docs/ppt/number_sources.csv (slide, number, source file, status) and
docs/ppt/number_check.md. Exit code 1 if anything is unmatched.
"""
import csv
import json
import os
import re
import sys
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from pptx import Presentation

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PPT = os.path.join(ROOT, "docs", "ppt")
DECK = os.path.join(PPT, "XFed_Capstone_Final_Review.pptx")

NAMES = [r"Jaccard@\d+", r"CICIDS2017", r"CIC-IDS-2017", r"CSE-CIC-IDS-2018", r"\bV4\b", r"SHA256", r"fp32",
         r"fp16", r"int8", r"4-bit", r"llama3\.1:8b-instruct-q4_K_M", r"llama3\.1:8b", r"Llama 3\.1", r"llama3\.1",
         r"\b8B\b", r"macro-F1", r"\bF1\b", r"\d{2}BCE\d{4}", r"fedavg_a\d\.\d_s\d+", r"\[\d+\]", r"top-10",
         r"top-k", r"Dir\(α\)", r"\bp50\b", r"arXiv:\d{4}\.\d{5}", r"XFed-IDS", r"Table I\b", r"Section 5\.2",
         r"section 5\.2", r"Llama 3\.1 8B"]
VERSION = re.compile(r"\b\d+\.\d+\.\d+(?:\+cu\d+)?\b")
NUM = re.compile(r"(?<![A-Za-z@_\d.])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?:e-?\d+)?(?![A-Za-z_\d])")

cache = {}


def load(path):
    if path not in cache:
        p = os.path.join(ROOT, path)
        txt = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
        nums = set()
        if txt:
            plain = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", txt)
            for m in re.finditer(r"\d+(?:\.\d+)?(?:[eE]-?\d+)?", plain):
                try:
                    nums.add(Decimal(m.group(0)))
                except Exception:
                    pass
        cache[path] = (txt, nums)
    return cache[path]


def match(token, sources):
    if VERSION.fullmatch(token):
        for s in sources:
            txt, _ = load(s)
            if txt and token in txt:
                return s, "match (version string)"
        return None, "UNMATCHED"
    plain = token.replace(",", "")
    places = len(plain.split(".")[1].split("e")[0]) if "." in plain else 0
    try:
        target = Decimal(plain)
    except Exception:
        return None, "UNMATCHED"
    for s in sources:
        txt, nums = load(s)
        if txt is None:
            continue
        if target in nums or re.search(r"(?<![\d.])" + re.escape(token) + r"(?![\d])", txt):
            return s, "match (exact)"
    q = Decimal(1).scaleb(-places)
    for s in sources:
        txt, nums = load(s)
        for n in nums:
            for mode in (ROUND_HALF_UP, ROUND_HALF_EVEN):
                if n.quantize(q, rounding=mode) == target and n != target:
                    return s, "match (rounded)"
    return None, "UNMATCHED"


def tokens(text):
    t = text
    for pat in NAMES:
        t = re.sub(pat, " ", t)
    out = [m.group(0) for m in VERSION.finditer(t)]
    t = VERSION.sub(" ", t)
    t = re.sub(r"(\d)[–-](\d)", r"\1 \2", t)          # ranges 5.1–10.3, dates 2026-10-12
    out += [m.group(0) for m in NUM.finditer(t)]
    return out


def slide_texts(slide):
    parts = []
    for sh in slide.shapes:
        if sh.has_text_frame:
            if 'type="slidenum"' in sh._element.xml:
                continue  # the template's page-number field
            parts.append(("text", sh.text_frame.text))
        if sh.has_table:
            for row in sh.table.rows:
                for cell in row.cells:
                    parts.append(("table", cell.text_frame.text))
    if slide.has_notes_slide:
        parts.append(("notes", slide.notes_slide.notes_text_frame.text))
    return parts


def main():
    meta = json.load(open(os.path.join(PPT, "slide_sources.json"), encoding="utf-8"))
    prs = Presentation(DECK)
    rows = []
    for n, (slide, m) in enumerate(zip(prs.slides, meta["slides"]), start=1):
        for where, text in slide_texts(slide):
            for tok in tokens(text):
                src, status = match(tok, m["sources"])
                rows.append((f"slide {n}", where, tok, src or "; ".join(m["sources"]) or "(none)", status))
    for d in meta["demo"]:
        for tok in tokens(d["text"]):
            src, status = match(tok, d["sources"])
            rows.append((f"demo {d['time']}", "speaker_script.md", tok, src or "; ".join(d["sources"]) or "(none)",
                         status))
    bad = [r for r in rows if r[4] == "UNMATCHED"]
    with open(os.path.join(PPT, "number_sources.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["slide", "where", "number", "source_file", "status"])
        w.writerows(rows)
    L = ["# Number check: Capstone Final Review deck\n",
         "Generated by `python docs/ppt/number_check.py`. Every number on every slide (text boxes, tables and "
         "speaker notes) and in the demo script is looked up in the repo files listed for that slide in "
         "`docs/ppt/slide_sources.json`. \"exact\" = the same number occurs in the source; \"rounded\" = the "
         "source stores more digits and rounds to the slide's value; \"version string\" = a software version "
         "found verbatim. Signs are compared by magnitude; every negative value (the cleaning row removals, the "
         "defence costs in pp, the best-validation changes, the KL partial correlations, the int8 drop) was "
         "checked by hand against its source. Names that contain digits are not counted (see the script's "
         "docstring).\n",
         "Numbers inside figures are not text and are not in this table: the three paper figures are drawn by "
         "`paper/figs/make_figs.py` from results files and their plotted values are verified identical to the "
         "paper's (`derived_values.json`) by `docs/ppt/make_ppt_figs.py`; the α picture is drawn from "
         "`data/processed/partitions/label_distribution_a{0.1,5.0}_s42.csv` after a cell-by-cell match with the "
         "report's silo tables (counts saved in `docs/ppt/figs/alpha_silo_counts.csv`); the dashboard images are "
         "crops of tracked screenshots.\n",
         f"**Total numbers: {len(rows)}. Matched: {len(rows) - len(bad)}. Unmatched: {len(bad)}.**\n"]
    if bad:
        L.append("## Unmatched\n")
        L.append("| Slide | Where | Number | Sources searched |")
        L.append("|---|---|---|---|")
        for r in bad:
            L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |")
        L.append("")
    L.append("## All numbers\n")
    L.append("| Slide | Where | Number | Source | Status |")
    L.append("|---|---|---|---|---|")
    for r in rows:
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")
    open(os.path.join(PPT, "number_check.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"numbers: {len(rows)}, matched: {len(rows) - len(bad)}, unmatched: {len(bad)}")
    for r in bad:
        print("  UNMATCHED", r)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
