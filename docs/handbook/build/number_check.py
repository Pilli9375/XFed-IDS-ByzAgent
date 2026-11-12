"""Number check: list every number in the handbook next to its cited source and confirm it.

For each paragraph / list item / table row of XFed_Team_Handbook.md:
  * extract the numbers in it (decimals, comma-grouped integers, percentages, ×-ratios, ranges);
  * collect the files cited in that unit with "(source: ...)", plus the units in the same
    section (a number's source is often given once per table or paragraph group);
  * confirm the number's literal text occurs in a cited file, or (CSV/JSON) that a value in the
    file rounds to it at the shown precision.
Numbers not found in a cited file are then searched in the project's canonical text
(CLAUDE.md, README.md, data/README.md, docs/*.md, results/**/*SUMMARY*.md) and reported.
Writes build/number_check.md. Section numbers, years, dates and commit hashes are skipped.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HB = Path(__file__).resolve().parents[1]
ROOT = HB.parents[1]
md = (HB / "XFed_Team_Handbook.md").read_text(encoding="utf-8")

CORPUS_FILES = [ROOT / "CLAUDE.md", ROOT / "README.md", ROOT / "data/README.md", *sorted((ROOT / "docs").glob("*.md")),
                *sorted((ROOT / "results").glob("*/*SUMMARY*.md")), ROOT / "results/inspection/residual_audit.md",
                *sorted((ROOT / "configs").glob("*.yaml")), ROOT / "federated/pyproject.toml", ROOT / "APP.bat", ROOT / "film/README.md"]
_cache: dict[Path, str] = {}


def text_of(p: Path) -> str:
    if p not in _cache:
        try:
            _cache[p] = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            _cache[p] = ""
    return _cache[p]


CORPUS = "\n".join(text_of(p) for p in CORPUS_FILES)

NUM = re.compile(r"(?<![\w.#/§-])[−-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.#/§-])[−+-]?\d+\.\d+|(?<![\w.#/§-])\d+(?=%|×|x\b| µs| pp| B\b| bytes| rows| flows| s\b)")
SKIP_LINE = re.compile(r"^#{1,4} |^\|[-| :]+\|$|^```")


def norm(s: str) -> str:
    return s.replace("−", "-").replace("+", "")


def float_hits(numtxt: str, blob: str) -> bool:
    n = norm(numtxt).replace(",", "")
    try:
        v = float(n)
    except ValueError:
        return False
    dec = len(n.split(".")[1]) if "." in n else 0
    for m in re.finditer(r"-?\d+\.\d+(?:e-?\d+)?|-?\d+", blob):
        try:
            x = float(m.group(0))
        except ValueError:
            continue
        if round(x, dec) == round(v, dec) or round(abs(x), dec) == round(abs(v), dec):
            return True
        if dec and round(x * 100, max(dec - 0, 0)) == round(v, dec):  # fraction shown as %
            return True
    return False


def found(numtxt: str, blob: str, structured: bool) -> bool:
    cands = {numtxt, norm(numtxt), numtxt.replace("−", "-"), numtxt.lstrip("+−-"), norm(numtxt).replace(",", "")}
    if any(c and c in blob for c in cands):
        return True
    return structured and len(blob) < 20000 and float_hits(numtxt, blob)


def resolve(path_txt: str) -> list[Path]:
    out = []
    for p in re.findall(r"`([^`]+)`", path_txt):
        p = p.strip().rstrip(",")
        cand = ROOT / p
        if "{" in p or "*" in p:
            base = p.split("{")[0].split("*")[0]
            cand_dir = (ROOT / base).parent
            if cand_dir.exists():
                out += [q for q in cand_dir.rglob("*") if q.is_file() and q.suffix in (".csv", ".json", ".md", ".yaml")][:50]
            continue
        if cand.is_file():
            out.append(cand)
        elif (ROOT / "results" / p).is_file():
            out.append(ROOT / "results" / p)
        else:
            hits = list(ROOT.glob(f"results/**/{Path(p).name}")) + list(ROOT.glob(f"docs/**/{Path(p).name}"))
            out += hits[:3]
    return out


units: list[tuple[str, str, int]] = []  # (section, text, line no)
section = ""
buf: list[str] = []
start = 0
in_code = False
for i, ln in enumerate(md.split("\n"), 1):
    if ln.startswith("```"):
        in_code = not in_code
        continue
    if in_code:
        continue
    if re.match(r"^#{1,3} ", ln):
        if buf:
            units.append((section, " ".join(buf), start)); buf = []
        section = ln.lstrip("# ").strip()
        continue
    if not ln.strip() or ln.startswith("|") or re.match(r"^\s*([-*]|\d+\.)\s", ln) or ln.startswith("!["):
        if buf:
            units.append((section, " ".join(buf), start)); buf = []
        if ln.strip() and not SKIP_LINE.match(ln):
            units.append((section, ln, i))
        continue
    if not buf:
        start = i
    buf.append(ln)
if buf:
    units.append((section, " ".join(buf), start))

sec_sources: dict[str, list[Path]] = {}
for sec, txt, _ in units:
    for m in re.finditer(r"\(source: (.+?)\)(?=[\s.,;:|]|$)", txt):
        sec_sources.setdefault(sec, []).extend(resolve(m.group(1)))
    for m in re.finditer(r"Source:? ?(?:data/processed|results|docs)[^\s)]*", txt):
        pass

rows = []
for sec, txt, ln in units:
    if re.match(r"^\s*!\[", txt) and "source" not in txt.lower():
        pass
    own = []
    for m in re.finditer(r"\(source: (.+?)\)(?=[\s.,;:|]|$)", txt):
        own += resolve(m.group(1))
    own += resolve(" ".join(f"`{p}`" for p in re.findall(r"(?:results|docs|data|configs)/[\w./{}*-]+\.(?:csv|json|md|yaml)", txt)))
    scope = own + sec_sources.get(sec, [])
    body = re.sub(r"\(source: .+?\)(?=[\s.,;:|]|$)", "", txt)
    body = re.sub(r"`[^`]*`", lambda m: m.group(0) if re.search(r"\d", m.group(0)) and "/" not in m.group(0) else "", body)
    body = re.sub(r"\b\d+\.\d+(?:\.\d+)*\s(?=[A-Z])|\[\d+\.\d+(?:\.\d+)?\]\(#|\(#[\w-]+\)", " ", body)  # section refs
    body = re.sub(r"20\d\d-\d\d-\d\d", " ", body)
    for m in NUM.finditer(body):
        n = m.group(0)
        if re.fullmatch(r"[−+-]?\d", n):
            continue
        blob_struct = [(p, text_of(p)) for p in dict.fromkeys(scope)]
        ok_file = next((p for p, b in blob_struct if found(n, b, p.suffix in (".csv", ".json"))), None)
        status = "cited-file" if ok_file else ("canonical-text" if found(n, CORPUS, False) else "NOT FOUND")
        rows.append((ln, sec, n, str(ok_file.relative_to(ROOT)).replace("\\", "/") if ok_file else "", status))

nf = [r for r in rows if r[4] == "NOT FOUND"]
cf = sum(r[4] == "cited-file" for r in rows)
ct = sum(r[4] == "canonical-text" for r in rows)
out = ["# Handbook number check", "",
       f"Numbers extracted: **{len(rows)}** · confirmed in a cited file: **{cf}** · confirmed in canonical project text "
       f"(CLAUDE.md, README.md, data/README.md, docs/, phase summaries, configs): **{ct}** · not found: **{len(nf)}**", "",
       "Generated by `build/number_check.py`. 'Not found' rows are reviewed by hand below the table.", "",
       "| line | section | number | confirmed in | status |", "|---|---|---|---|---|"]
for ln, sec, n, f, st in rows:
    out.append(f"| {ln} | {sec[:48]} | {n} | {f} | {st} |")
(HB / "build" / "number_check.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"{len(rows)} numbers; cited-file {cf}; canonical {ct}; NOT FOUND {len(nf)}")
for r in nf:
    print("  NF", r[0], r[1][:40], "|", r[2])
