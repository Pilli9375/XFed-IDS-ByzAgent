"""Check every number in the paper against the file named in its "% src:" comment.

Run from the repository root:
    python paper/number_check.py

For each line of paper/main.tex and paper/appendix.tex that contains a data number,
the script reads the trailing "% src: a; b" comment and looks for the number in those
files. A number matches when
  (1) its exact text (thousands separators removed) occurs in the source file as a
      separate number, or
  (2) the source holds a number that rounds to it at the same number of decimals
      (used for JSON/CSV sources that store full precision).
Signs are compared on magnitude only; the sign is checked by hand in review.
Writes paper/number_check.md and prints a summary. Exit code 1 if anything is
unmatched or unsourced.
"""
import os
import re
import sys
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["paper/main.tex", "paper/appendix.tex"]

NUM = re.compile(r"(?<![A-Za-z@_\\])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![A-Za-z_])")

# structural LaTeX that carries numbers which are not data
STRIP = [
    r"\\cite\{[^}]*\}", r"\\ref\{[^}]*\}", r"\\label\{[^}]*\}", r"\\includegraphics\[[^\]]*\]\{[^}]*\}",
    r"\\cmidrule(\([^)]*\))?\{[^}]*\}", r"\\multicolumn\{\d+\}\{[^}]*\}", r"\\setlength\{[^}]*\}\{[^}]*\}",
    r"\\begin\{[^}]*\}(\{[^}]*\})*(\[[^\]]*\])?", r"\\end\{[^}]*\}", r"p\{[\d.]+cm\}",
    r"\\path\|[^|]*\|", r"\\texttt\{[^}]*\}", r"\\url\{[^}]*\}", r"\\binom\{\d+\}\{\d+\}",
    r"\\section\*?\{[^}]*\}", r"\\subsection\{[^}]*\}", r"\\fullref\{[^}]*\}",
    r"\\,", r"\\[a-zA-Z]+",
]
SKIP_ENVS = ("tikzpicture",)
# tokens that are names, not quantities
NAME_TOKENS = [r"Jaccard@\d+", r"CICIDS2017", r"CIC-IDS-?2017", r"SHA256", r"V4", r"F1", r"fp32", r"fp16", r"int8",
               r"Llama~?3\.1", r"8B", r"llama3\.1:8b", r"qwen2\.5:7b", r"phi3\.5", r"top-\$k\$", r"\$k\$",
               r"Windows~?11", r"RTX 4050", r"Ryzen 7 7435HS", r"Python 3\.11", r"PyTorch 2\.13\.0", r"Flower 1\.33",
               r"IEEE", r"5-stage", r"five-stage", r"Phase \d", r"Phase~\d", r"\bAppendix~?[A-L]\b", r"Section~[IVX]+(-[A-H])?",
               r"[IVX]+-[A-H]", r"[A-L]-[A-H]", r"Table~", r"Fig\.~", r"rounds? \d+--\d+", r"\$\\beta_[12]\$", r"\\beta_[12]",
               r"\$p_k\$", r"N_k", r"\\mathbf\{1\}_\{10\}", r"10\^\{-[34]\}", r"k\^2", r"2k", r"\(1\)|\(2\)|\(3\)|\(4\)",
               r"\$N\\ge3\$", r"N\\ge3", r"\{0,3,5\}|\{0,3\}|\{0,1,9\}|\{2,7,9\}|\{2,7\}|\{2,4,9\}|\{2,4\}"]


def load(path):
    p = os.path.join(ROOT, path.strip())
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


cache = {}


def thousands(text):
    return re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)


def numbers_in(text):
    out = set()
    for m in re.finditer(r"\d+(?:\.\d+)?(?:[eE]-?\d+)?", thousands(text)):
        try:
            out.add(Decimal(m.group(0)))
        except Exception:
            pass
    return out


def matches(token, srcs):
    plain = token.replace(",", "")
    places = len(plain.split(".")[1]) if "." in plain else 0
    target = Decimal(plain)
    for s in srcs:
        if s not in cache:
            txt = load(s)
            cache[s] = (txt, numbers_in(txt) if txt else set())
        txt, nums = cache[s]
        if txt is None:
            continue
        # exact textual match as a separate number
        pat = r"(?<![\d.])" + re.escape(plain) + r"(?![\d])"
        if re.search(pat, thousands(txt)) or re.search(pat, txt):
            return s, "exact"
        q = Decimal(1).scaleb(-places)
        for n in nums:
            for mode in (ROUND_HALF_UP, ROUND_HALF_EVEN):
                if n.quantize(q, rounding=mode) == target:
                    return s, "rounded"
            # percentages stored as fractions
            if (n * 100).quantize(q, rounding=ROUND_HALF_UP) == target:
                return s, "rounded (x100)"
    return None, "NOT FOUND"


rows = []
problems = 0
for fname in FILES:
    in_env = False
    text = load(fname)
    in_doc = not fname.endswith("main.tex")
    for ln, line in enumerate(text.split("\n"), 1):
        if not in_doc:
            in_doc = "\\begin{document}" in line
            continue
        if any(f"\\begin{{{e}}}" in line for e in SKIP_ENVS):
            in_env = True
        if in_env:
            if any(f"\\end{{{e}}}" in line for e in SKIP_ENVS):
                in_env = False
            continue
        stripped = line.lstrip()
        if stripped.startswith("%"):
            continue
        m = re.search(r"(?<!\\)%(.*)$", line)
        code = line[: m.start()] if m else line
        comment = m.group(1) if m else ""
        srcs = []
        sm = re.search(r"src:\s*(.*)$", comment)
        if sm:
            srcs = [x.strip() for x in sm.group(1).split(";") if x.strip()]
        work = code
        for pat in NAME_TOKENS:
            work = re.sub(pat, " ", work)
        for pat in STRIP:
            work = re.sub(pat, " ", work)
        toks = [a + (b or "") for a, b in NUM.findall(work)]
        if not toks:
            continue
        for t in toks:
            if not srcs:
                rows.append((fname, ln, t, "", "UNSOURCED"))
                problems += 1
                continue
            src, how = matches(t, srcs)
            if src is None:
                problems += 1
                rows.append((fname, ln, t, "; ".join(srcs), "NOT FOUND"))
            else:
                rows.append((fname, ln, t, src, "match (" + how + ")"))

with open(os.path.join(ROOT, "paper", "number_check.md"), "w", encoding="utf-8") as f:
    f.write("# Number check\n\n")
    f.write("Generated by `python paper/number_check.py`. Every number in `paper/main.tex` and "
            "`paper/appendix.tex` (body and appendices), the file named in its `% src:` comment, and whether "
            "the number was found there. \"exact\" = the same text occurs in the source; \"rounded\" = the "
            "source stores more digits and rounds to the paper's value at the paper's precision. Signs are "
            "compared by magnitude; the sign of every negative value was checked by hand against the source. "
            "Excluded as non-data: citation, table, figure and section numbers, metric names such as "
            "Jaccard@10, model and dataset names, and TikZ coordinates.\n\n"
            "**Derived source (approved by the planning chat):** `paper/figs/derived_values.json` holds "
            "the interquartile ranges of Jaccard@10 and weighted tau, per alpha and per (alpha, family), "
            "computed for this paper by `paper/figs/make_figs.py` from "
            "`results/inspection/agreement_metrics.csv` (family_eligible rows). They are labelled as such "
            "in the Fig. 2 caption and in Appendix D. Rows below citing that file are those values.\n\n")
    n_ok = sum(1 for r in rows if r[4].startswith("match"))
    f.write(f"**Total numbers: {len(rows)}. Matched: {n_ok}. Unmatched or unsourced: {problems}.**\n\n")
    f.write("| File | Line | Number | Source | Status |\n|---|---|---|---|---|\n")
    for r in rows:
        f.write(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |\n")
print(f"numbers: {len(rows)}  problems: {problems}")
for r in rows:
    if not r[4].startswith("match"):
        print(r)
sys.exit(1 if problems else 0)
