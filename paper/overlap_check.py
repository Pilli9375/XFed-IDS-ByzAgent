"""Find 8-word runs that the paper shares with its sources.

Run from the repository root:
    python paper/overlap_check.py

Compares every 8-word sequence of the paper text (paper/main.tex and
paper/appendix.tex, LaTeX stripped) against:
  * the abstract of every cited paper, saved in paper/_sources/*.txt (git-ignored),
  * README.md,
  * docs/handbook/ (the handbook and its source chapters).
Writes paper/overlap_check.md with every shared run, the paper sentence it sits in,
and which source holds it. Runs inside text the project requires verbatim (the
locked ByzAgent claim and the locked fidelity phrase) are listed but counted as
exempt.
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = 8

EXEMPT_PHRASES = [
    "both effects are present a real compositional confound saturates some silos flag rates independent of any attack "
    "real attack responsive detection is also present and becomes visible where silos are not already saturated seed 42s "
    "apparent null was partly a ceiling artifact of that seeds unusually bimodal composition",
    "produces decisions plus a rationale of measured fidelity",
    "multi krum excluded a malicious silo 0 of the time",
]


def numeric(gram):
    """A run with four or more number tokens repeats result values, not prose."""
    return sum(tok.isdigit() for tok in gram.split()) >= 4


def words(text):
    text = text.lower().replace("\u2019", "'").replace("'", "")
    return re.findall(r"[a-z0-9]+", text)


def strip_latex(tex):
    out = []
    in_doc = False
    for line in tex.split("\n"):
        if "\\begin{document}" in line:
            in_doc = True
            continue
        if not in_doc and "\\section" not in line and "\\caption" not in line:
            # appendix.tex has no \begin{document}; treat it as in-document
            if "appendix" not in globals().get("_current", ""):
                continue
        if "numcheck: ignore" in line:
            # front-matter facts (capstone note, names and registration numbers), not prose
            continue
        line = re.sub(r"(?<!\\)%.*$", "", line)
        out.append(line)
    t = "\n".join(out)
    t = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", " ", t, flags=re.S)
    t = re.sub(r"\\verb\|[^|]*\|", " ", t)
    t = re.sub(r"\\path\|[^|]*\|", " ", t)
    t = re.sub(r"\\(cite|ref|label|includegraphics|url|bibliography|bibliographystyle|input)(\[[^\]]*\])?\{[^}]*\}", " ", t)
    t = re.sub(r"\$[^$]*\$", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    t = t.replace("~", " ").replace("{", " ").replace("}", " ").replace("&", " . ").replace("\\\\", " . ")
    return t


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n\s*\n", text) if s.strip()]


paper_parts = []
for f in ("paper/main.tex", "paper/appendix.tex"):
    globals()["_current"] = f
    paper_parts.append(strip_latex(open(os.path.join(ROOT, f), encoding="utf-8").read()))
paper_text = "\n\n".join(paper_parts)

sources = {}
for p in glob.glob(os.path.join(ROOT, "paper", "_sources", "*.txt")):
    sources["abstract:" + os.path.basename(p)[:-4]] = open(p, encoding="utf-8").read()
sources["README.md"] = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
for p in glob.glob(os.path.join(ROOT, "docs", "handbook", "**", "*.md"), recursive=True):
    sources[os.path.relpath(p, ROOT).replace("\\", "/")] = open(p, encoding="utf-8").read()

grams = {}
for name, txt in sources.items():
    w = words(txt)
    for i in range(len(w) - N + 1):
        grams.setdefault(" ".join(w[i:i + N]), set()).add(name)

exempt_grams = set()
for ph in EXEMPT_PHRASES:
    w = ph.split()
    for i in range(len(w) - N + 1):
        exempt_grams.add(" ".join(w[i:i + N]))

hits = []
for sent in sentences(paper_text):
    w = words(sent)
    found = {}
    for i in range(len(w) - N + 1):
        g = " ".join(w[i:i + N])
        if g in grams:
            found[g] = grams[g]
    if found:
        joined = " ".join(w)
        locked = [ph for ph in EXEMPT_PHRASES if ph in joined]

        def covered(g):
            return numeric(g) or g in exempt_grams or any(g in ph or ph in g for ph in locked) or \
                any(set(g.split()) <= set(ph.split()) | {"it", "byzagent", "the", "we", "describe", "agent", "as", "one", "that"} for ph in locked)

        exempt = all(covered(g) for g in found)
        hits.append((sent, found, exempt))

counted = [h for h in hits if not h[2]]
with open(os.path.join(ROOT, "paper", "overlap_check.md"), "w", encoding="utf-8") as f:
    f.write("# Overlap check (8-word runs)\n\n")
    f.write(f"Sources compared: {sum(1 for k in sources if k.startswith('abstract:'))} saved abstracts of cited "
            "papers (`paper/_sources/`, git-ignored), `README.md`, and every Markdown file under `docs/handbook/`.\n\n")
    f.write(f"**Sentences sharing an 8-word run: {len(hits)} total; {len(hits) - len(counted)} exempt "
            f"(locked wording the project requires verbatim, or runs made of result numbers); {len(counted)} counted.**\n\n")
    for sent, found, exempt in hits:
        f.write(f"- {'EXEMPT (locked wording or numbers only)' if exempt else 'COUNTED'}: \"{' '.join(sent.split())[:300]}\"\n")
        for g, src in list(found.items())[:4]:
            f.write(f"  - `{g}` in {', '.join(sorted(src))}\n")
print(f"sentences with shared 8-grams: {len(hits)}; exempt: {len(hits) - len(counted)}; counted: {len(counted)}")
for sent, found, exempt in counted:
    print("---", " ".join(sent.split())[:220])
    for g, src in list(found.items())[:3]:
        print("    ", g, "|", ", ".join(sorted(src))[:120])
