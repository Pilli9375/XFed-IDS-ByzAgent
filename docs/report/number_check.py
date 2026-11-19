"""Check every number in the report's chapter text against the file named in its source comment.

Run from the repository root:
    python docs/report/number_check.py

Each block of docs/report/src/*.md (a paragraph, list, quotation or table, with the heading
above it) that contains a data number must be followed by a line

    <!-- src: path/one; path/two -->

naming the repository files the numbers were copied from. A number matches when
  (1) its text (thousands separators removed) occurs in a source file as a separate number, or
  (2) a source holds a number that rounds to it at the same number of decimals, or
  (3) a source holds the same quantity as a fraction (0.388 shown as 38.8%).
The same rules as paper/number_check.py. Signs are compared on magnitude; negative values were
checked by hand.

Not treated as data: citation numbers, cross-references to chapters, sections, tables and figures,
ISO dates (taken from git log), version numbers inside tool names, metric names such as Jaccard@10,
model names, and code. Blocks marked <!-- numcheck: ignore --> hold formulas or structural numbers
and are listed as ignored.

Writes docs/report/number_check.md and docs/report/number_sources.csv. Exit code 1 if any number
is unmatched or unsourced.
"""
import csv
import os
import re
import sys
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "docs", "report", "src")

NUM = re.compile(r"(?<![A-Za-z@_\\/.\d])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![A-Za-z_]|\.[A-Za-z])")

STRIP = [
    r"`[^`]*`",                                   # code, paths, identifiers
    r"https?://\S+",                              # URLs
    r"!\[[^\]]*\]\([^)]*\)",                      # image path (caption kept separately)
    r"\{#[^}]*\}",                                # labels and options
    r"\[@[^\]]*\]",                               # citations
    r"@(?:fig|tab|sec):[\w-]+",                   # cross-references
    r"\b20\d\d-\d\d-\d\d\b",                      # ISO dates (git log)
    r"\b(?:Sections?|Chapters?)\s+\d+(?:\.\d+)*(?:\.[A-S])?(?:(?:,\s*|\s+(?:and|to|or)\s+)\d+(?:\.\d+)*(?:\.[A-S])?)*",
    r"\b\d\.[A-S](?:\.\d+)?\b",                   # appendix section numbers, 6.E or 6.E.3
    r"(?<=\|)[\s,]*(?:\d\.\d(?:\.\d)?(?:\s*(?:,|to|and)\s*)?)+[\s,]*(?=\||\(|$)",  # cells that only list sections
    r"\bChapter\s+\d\b",
]
NAME_TOKENS = [
    r"Jaccard@\d+", r"J@\d+", r"CICIDS2017", r"CIC-IDS-?2017", r"SHA-?256", r"FIPS 180-4", r"IEEE 754",
    r"binary(?:32|16)", r"fp32", r"fp16", r"int8", r"F1(?:_c)?", r"Llama 3\.1 8B", r"Llama 3\.1", r"Llama 3",
    r"llama3\.1:8b-instruct-q4_K_M", r"qwen2\.5:7b-instruct-q4_K_M", r"phi3\.5:latest", r"Phi-3\.5",
    r"Qwen 2\.5 7B", r"RTX 4050", r"Ryzen 7 7435HS", r"Windows 11", r"Python 3\.11(?:\.15)?", r"8-word",
    r"Phases? \d(?: (?:to|and) \d)?", r"Part [12]", r"β1", r"β2", r"Dir\(α·1(?:_N)?\)", r"1_N", r"\bp_k\b",
    r"\bw_t\b", r"w_\(t\+1\)", r"n_i", r"n_c", r"φ_j", r"\bU\(0,1\)", r"IEEEtran", r"React 19", r"WCAG",
    r"Remotion", r"Brygada 1918", r"Fontsource", r"[A-Z][a-z]+ \d+\.\d+(?:\.\d+)? \(",
    r"\b(?:\d{1,2}|[12]\d{3}) (?=Mbps)", r"U\+\w+", r"Figure \d+\.\d+", r"Table \d+\.\d+",
]
CODE_FENCE = re.compile(r"^```")


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
        pat = r"(?<![\d.])" + re.escape(plain) + r"(?![\d])"
        if re.search(pat, thousands(txt)) or re.search(pat, txt):
            return s, "exact"
        q = Decimal(1).scaleb(-places)
        for n in nums:
            if n.adjusted() > 12:
                continue
            try:
                for mode in (ROUND_HALF_UP, ROUND_HALF_EVEN):
                    if n.quantize(q, rounding=mode) == target:
                        return s, "rounded"
                if (n * 100).quantize(q, rounding=ROUND_HALF_UP) == target:
                    return s, "rounded (x100)"
            except Exception:
                continue
    return None, "NOT FOUND"


def blocks_of(path):
    """Yield (chapter, section, kind, text, sources, ignored) for each block of a chapter file."""
    lines = open(path, encoding="utf-8").read().split("\n")
    chapter = section = ""
    buf, kind, in_code = [], "text", False
    pending_heading = ""

    def flush():
        nonlocal buf, pending_heading
        text = "\n".join(buf).strip()
        buf = []
        return text

    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if CODE_FENCE.match(s):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            i += 1
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m:
            if buf:
                out.append([chapter, section, flush(), [], False])
            title = re.sub(r"\{#[^}]*\}", "", m.group(2)).strip()
            if len(m.group(1)) == 1:
                chapter = title
            section = title
            pending_heading = title
            out.append([chapter, section, title, [], False, "heading"])
            i += 1
            continue
        sm = re.match(r"^<!--\s*src:\s*(.*?)\s*-->$", s)
        if sm:
            srcs = [x.strip() for x in sm.group(1).split(";") if x.strip()]
            if buf:
                out.append([chapter, section, flush(), srcs, False])
            elif out:
                out[-1][3] = srcs
            i += 1
            continue
        if re.match(r"^<!--\s*numcheck:\s*ignore\s*-->$", s):
            if buf:
                out.append([chapter, section, flush(), [], True])
            elif out:
                out[-1][4] = True
            i += 1
            continue
        if not s:
            if buf:
                out.append([chapter, section, flush(), [], False])
            i += 1
            continue
        buf.append(line)
        i += 1
    if buf:
        out.append([chapter, section, flush(), [], False])
    # a heading's numbers are checked against the sources of the block that follows it
    for k, b in enumerate(out):
        if len(b) == 6 and k + 1 < len(out):
            b[3], b[4] = out[k + 1][3], out[k + 1][4]
    return out


def tokens(text):
    work = text
    for pat in STRIP:
        work = re.sub(pat, " ", work)
    for pat in NAME_TOKENS:
        work = re.sub(pat, " ", work)
    work = re.sub(r"<!--.*?-->", " ", work)
    return [a + (b or "") for a, b in NUM.findall(work)]


def main():
    rows, problems, ignored = [], 0, []
    files = [os.path.join(d, f) for d in ("src", "src_short")
             for f in sorted(os.listdir(os.path.join(ROOT, "docs", "report", d))) if f.endswith(".md")]
    for fname in files:
        for blk in blocks_of(os.path.join(ROOT, "docs", "report", fname)):
            chapter, section, text, srcs, ign = blk[:5]
            toks = tokens(text)
            if not toks:
                continue
            if ign:
                ignored.append((fname, section, len(toks)))
                continue
            for t in toks:
                if not srcs:
                    rows.append((fname, chapter, section, t, "", "UNSOURCED", text[:90]))
                    problems += 1
                    continue
                src, how = matches(t, srcs)
                if src is None:
                    problems += 1
                    rows.append((fname, chapter, section, t, "; ".join(srcs), "NOT FOUND", text[:90]))
                else:
                    rows.append((fname, chapter, section, t, src, "match (" + how + ")", ""))
    out_dir = os.path.join(ROOT, "docs", "report")
    with open(os.path.join(out_dir, "number_sources.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["number", "file", "chapter", "section", "source_file", "status"])
        for fname, chapter, section, t, src, status, _ in rows:
            w.writerow([t, fname, chapter, section, src, status])
    n_ok = sum(1 for r in rows if r[5].startswith("match"))
    with open(os.path.join(out_dir, "number_check.md"), "w", encoding="utf-8") as f:
        f.write("# Number check: Capstone report\n\n")
        f.write("Generated by `python docs/report/number_check.py`. Every number in the chapter text "
                "(`docs/report/src/*.md`, front matter, chapters and appendix) is looked up in the file named "
                "in the source comment that follows its block. \"exact\" means the same text occurs in the "
                "source; \"rounded\" means the source stores more digits and rounds to the report's value; "
                "\"x100\" means the source stores a fraction shown here as a percentage. Signs are compared by "
                "magnitude, and negative values were checked by hand. Dates come from `git log` and are not "
                "counted. Code excerpts are copied from the repository files named in their captions and are "
                "not counted.\n\n")
        f.write(f"**Total numbers: {len(rows)}. Matched: {n_ok}. Unmatched or unsourced: {problems}.**\n\n")
        f.write(f"Blocks marked as formulas or structure (numcheck: ignore): {len(ignored)} blocks, "
                f"{sum(n for *_, n in ignored)} tokens, listed at the end.\n\n")
        if problems:
            f.write("## Problems\n\n| File | Section | Number | Sources | Status | Text |\n|---|---|---|---|---|---|\n")
            for fname, chapter, section, t, src, status, text in rows:
                if not status.startswith("match"):
                    f.write(f"| {fname} | {section} | {t} | {src} | {status} | {text.replace('|', '/')} |\n")
            f.write("\n")
        f.write("## All numbers\n\n| File | Section | Number | Source | Status |\n|---|---|---|---|---|\n")
        for fname, chapter, section, t, src, status, _ in rows:
            f.write(f"| {fname} | {section} | {t} | {src} | {status} |\n")
        f.write("\n## Ignored blocks (formulas and structure)\n\n| File | Section | Tokens |\n|---|---|---|\n")
        for fname, section, n in ignored:
            f.write(f"| {fname} | {section} | {n} |\n")
    print(f"numbers: {len(rows)}; matched: {n_ok}; problems: {problems}")
    for fname, chapter, section, t, src, status, text in rows:
        if not status.startswith("match"):
            print(f"  {status:10s} {fname:32s} {t:>12s}  [{section[:40]}] {text[:70]!r}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
