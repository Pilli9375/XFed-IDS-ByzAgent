"""Find 8-word runs that the report shares with its sources.

Run from the repository root:
    python docs/report/overlap_check.py

Compares every 8-word sequence of the report's prose (docs/report/src/*.md; tables, code
excerpts and source comments removed) against:
  * the abstract of every cited paper, saved in paper/_sources/*.txt (git-ignored),
  * the IEEE paper (paper/main.tex and paper/appendix.tex, LaTeX stripped),
  * README.md,
  * docs/handbook/ (the handbook and its source chapters).
Sentences whose shared runs lie entirely inside wording the project requires verbatim (the locked
ByzAgent claim and the other locked phrases), or are made of result numbers, are listed as exempt.
Writes docs/report/overlap_check.md. Exit code 1 if any sentence is counted.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
N = 8

EXEMPT_PHRASES = [
    "both effects are present a real compositional confound saturates some silos flag rates independent of any attack "
    "real attack responsive detection is also present and becomes visible where silos are not already saturated seed 42s "
    "apparent null was partly a ceiling artifact of that seeds unusually bimodal composition",
    "produces decisions plus a rationale of measured fidelity",
    "multi krum excluded a malicious silo 0 of the time",
    "classical krums exclusions are chance level it keeps 1 of 10 every round",
    "directional not significant",
    "this specific attack biases val_accuracy upward for malicious clients on this benign heavy validation set",
]


def numeric(gram):
    return sum(tok.isdigit() for tok in gram.split()) >= 4


def words(text):
    text = text.lower().replace("\u2019", "'").replace("'", "")
    return re.findall(r"[a-z0-9_]+", text)


def report_prose():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "docs", "report", "src", "*.md"))):
        text = open(f, encoding="utf-8").read()
        text = re.sub(r"```.*?```", " ", text, flags=re.S)
        lines = []
        for line in text.split("\n"):
            s = line.strip()
            if s.startswith("|") or s.startswith("<!--") or s.startswith("Code:"):
                continue
            lines.append(line)
        t = "\n".join(lines)
        t = re.sub(r"\{#[^}]*\}", " ", t)
        t = re.sub(r"\[@[^\]]*\]", " ", t)
        t = re.sub(r"@(?:fig|tab|sec):[\w-]+", " ", t)
        t = re.sub(r"`[^`]*`", " ", t)
        t = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", t)
        out.append((os.path.basename(f), t))
    return out


def strip_latex(tex):
    tex = re.sub(r"(?<!\\)%.*$", "", tex, flags=re.M)
    tex = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", " ", tex, flags=re.S)
    tex = re.sub(r"\\(cite|ref|label|includegraphics|url|bibliography|bibliographystyle|input)(\[[^\]]*\])?\{[^}]*\}", " ", tex)
    tex = re.sub(r"\$[^$]*\$", " ", tex)
    tex = re.sub(r"\\[a-zA-Z]+\*?", " ", tex)
    return tex.replace("~", " ").replace("{", " ").replace("}", " ").replace("&", " . ")


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?:])\s+|\n\s*\n|\n[-0-9]+[.)]?\s", text) if s.strip()]


sources = {}
for p in glob.glob(os.path.join(ROOT, "paper", "_sources", "*.txt")):
    sources["abstract:" + os.path.basename(p)[:-4]] = open(p, encoding="utf-8").read()
for f in ("paper/main.tex", "paper/appendix.tex"):
    sources[f] = strip_latex(open(os.path.join(ROOT, f), encoding="utf-8").read())
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
for fname, prose in report_prose():
    for sent in sentences(prose):
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
                gw = set(g.split())
                return (numeric(g) or g in exempt_grams or any(g in ph for ph in locked)
                        or any(len(gw - set(ph.split())) <= 2 for ph in locked))
            exempt = all(covered(g) for g in found)
            hits.append((fname, sent, found, exempt))

counted = [h for h in hits if not h[3]]
with open(os.path.join(ROOT, "docs", "report", "overlap_check.md"), "w", encoding="utf-8") as f:
    f.write("# Overlap check (8-word runs): Capstone report\n\n")
    f.write(f"Sources compared: {sum(1 for k in sources if k.startswith('abstract:'))} saved abstracts of cited papers "
            "(`paper/_sources/`, git-ignored), the IEEE paper (`paper/main.tex`, `paper/appendix.tex`), `README.md`, "
            "and every Markdown file under `docs/handbook/`. Report prose only: tables, code excerpts and the "
            "verbatim ByzAgent prompt are excluded, because they reproduce data or code by design.\n\n")
    f.write(f"**Sentences sharing an 8-word run: {len(hits)} total; {len(hits) - len(counted)} exempt "
            f"(locked wording the project requires verbatim, or runs made of result numbers); {len(counted)} counted.**\n\n")
    for fname, sent, found, exempt in hits:
        f.write(f"- {'EXEMPT' if exempt else 'COUNTED'} ({fname}): \"{' '.join(sent.split())[:300]}\"\n")
        for g, src in list(found.items())[:4]:
            f.write(f"  - `{g}` in {', '.join(sorted(src))}\n")
with open(os.path.join(ROOT, "docs", "report", "private", "overlap_worklist.txt"), "w", encoding="utf-8") as f:
    for fname, sent, found, exempt in counted:
        f.write(f"@@ {fname}\n{' '.join(sent.split())}\n   >> {' | '.join(list(found)[:6])}\n")
print(f"sentences with shared 8-grams: {len(hits)}; exempt: {len(hits) - len(counted)}; counted: {len(counted)}")
for fname, sent, found, exempt in counted:
    print("---", fname, " ".join(sent.split())[:200])
    for g, src in list(found.items())[:3]:
        print("    ", g, "|", ", ".join(sorted(src))[:100])
sys.exit(1 if counted else 0)
