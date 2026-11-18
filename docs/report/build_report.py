"""Build the VIT-AP Capstone Project Report (thesis) from the university template.

Run from the repository root, in the xfed conda env (python-docx, pymupdf, pywin32):

    python docs/report/build_report.py              # both builds, Word export to PDF
    python docs/report/build_report.py --no-pdf     # .docx only (no Word needed)

Inputs
  docs/report/private/CAPSTONE_THESIS_Sample_Format.docx   university template (git-ignored)
  docs/report/private/biodata.md                           member biodata (git-ignored)
  docs/report/private/photos/<RegNo>.jpg|png               optional biodata photos (git-ignored)
  docs/report/src/*.md                                     chapter text (tracked; edit these)
  paper/refs.bib                                           the 58 verified references

Outputs
  docs/report/XFed_Capstone_Report.docx / .pdf                      public build, no biodata
  docs/report/private/XFed_Capstone_Report_SUBMISSION.docx / .pdf   submission build, with biodata

The template's own page setup, margins, logo, fonts and sample-page formatting are kept.
Its sample content (the automobile project) is deleted. Front pages are rewritten in
place; everything after the acknowledgement is generated from docs/report/src/.

Markdown dialect used in src/*.md (deliberately small):
  # Title                         chapter (one per file, numbered by file order)
  ## Title {#sec:id}              section  N.M
  ### Title {#sec:id}             subsection N.M.K
  - item / 1. item                bullet / numbered list
  > text                          indented quotation
  Table: Caption {#tab:id}        caption line, followed by a pipe table
  ![Caption](repo/path.png){#fig:id width=14}       figure (width in cm)
  Code: Caption {#fig:id} [repo/path.py]            caption line, followed by a fenced block
  **bold**, *italic*, `code`, [@key; @key2] citations, @fig:id / @tab:id / @sec:id references
  <!-- src: file; file -->        source of the numbers in the preceding block (see number_check.py)
"""
import argparse
import copy
import os
import re
import subprocess
import sys
from pathlib import Path

import docx
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "report"
PRIVATE = REPORT / "private"
SRC = REPORT / "src"
TEMPLATE = PRIVATE / "CAPSTONE_THESIS_Sample_Format.docx"
BIODATA = PRIVATE / "biodata.md"
PHOTOS = PRIVATE / "photos"
BIB = ROOT / "paper" / "refs.bib"

# ------------------------------------------------------------------ front-page variables
# Leave DEPARTMENT empty while there is no separate department: the certificate then reads "HoD"
# (above the School and University lines) and the acknowledgement thanks "the Head of the Department,
# School of Computer Science and Engineering". Set a name (e.g. "Networking and Security") and rebuild
# to print "HoD, Department of <name>" and "the Head of the Department, Department of <name>".
DEPARTMENT = ""
TITLE = "XFED-IDS-BYZAGENT: EXPLAINABLE AND TRUST-AWARE FEDERATED INTRUSION DETECTION"
GUIDE = "Prof. Gargi Madala"
MONTH_YEAR = "NOVEMBER 2026"
MEMBERS = [  # (name as printed, registration number)
    ("V Naga Adithya", "23BCE9062"),
    ("T Shaun", "23BCE9916"),
    ("P Sampath", "23BCE8614"),
    ("D Tharun", "23BCE8818"),
]
REPO_URL = "https://github.com/Pilli9375/XFed-IDS-ByzAgent"

# ------------------------------------------------------------------ template paragraph indices
# Body-element indices in the template (checked against its text at build time).
T_TITLE, T_NAMES, T_GUIDE, T_DATE = 0, (18, 19, 20, 21), 26, 38
T_CERT_BODY, T_CERT_GUIDE, T_CERT_HOD = 42, 45, 58
T_ACK_VC, T_ACK_HOD, T_ACK_GUIDE, T_ACK_FAMILY = 65, 67, 69, 73
T_ACK_MEMBERS = (76, 77, 78, 79)
T_LAST_KEPT = 79  # everything after the acknowledgement's member list is regenerated

FONT = "Times New Roman"


# ================================================================== small XML helpers
def set_text(p, text, keep_run=0):
    """Replace a paragraph's text, keeping the formatting of one existing run."""
    runs = p.runs
    rpr = copy.deepcopy(runs[keep_run]._r.rPr) if runs and runs[keep_run]._r.rPr is not None else None
    for r in list(p._p):
        if r.tag in (qn("w:r"), qn("w:proofErr"), qn("w:hyperlink"), qn("w:bookmarkStart"), qn("w:bookmarkEnd")):
            p._p.remove(r)
    run = p.add_run(text)
    if rpr is not None:
        run._r.insert(0, rpr)
    return run


def add_run_like(p, text, like_rpr=None, bold=None, italic=None, highlight=False):
    run = p.add_run(text)
    if like_rpr is not None:
        run._r.insert(0, copy.deepcopy(like_rpr))
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if highlight:
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return run


def ppr(p):
    return p._p.get_or_add_pPr()


def set_spacing(p, line=None, before=None, after=None):
    sp = ppr(p).find(qn("w:spacing"))
    if sp is None:
        sp = OxmlElement("w:spacing")
        ppr(p).append(sp)
    if line is not None:
        sp.set(qn("w:line"), str(line))
        sp.set(qn("w:lineRule"), "auto")
    if before is not None:
        sp.set(qn("w:before"), str(before))
    if after is not None:
        sp.set(qn("w:after"), str(after))


def page_break_before(p):
    el = OxmlElement("w:pageBreakBefore")
    ppr(p).insert(0, el)


def keep_next(p):
    ppr(p).append(OxmlElement("w:keepNext"))


def add_field(p, instr, placeholder=""):
    """Complex field (begin / instr / separate / result / end) appended to paragraph p."""
    def fc(t):
        r = OxmlElement("w:r")
        f = OxmlElement("w:fldChar")
        f.set(qn("w:fldCharType"), t)
        r.append(f)
        return r
    p._p.append(fc("begin"))
    r = OxmlElement("w:r")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instr} "
    r.append(it)
    p._p.append(r)
    p._p.append(fc("separate"))
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = placeholder
    r.append(t)
    p._p.append(r)
    p._p.append(fc("end"))


def tc_entry(p, text, level=1):
    """TC field: a Table of Contents entry independent of the paragraph's own text."""
    safe = text.replace('"', "'")
    add_field(p, f'TC "{safe}" \\f C \\l {level}')


def ensure_style(doc, name, base, size=None, bold=None, italic=None, align=None, outline=None,
                 line=None, before=None, after=None, keep=False, indent_first=None):
    styles = doc.styles
    try:
        st = styles[name]
    except KeyError:
        st = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    st.base_style = styles[base]
    f = st.font
    f.name = FONT
    st.element.get_or_add_rPr()
    rfonts = st.element.rPr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        st.element.rPr.insert(0, rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(a), FONT)
    if size:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    pf = st.paragraph_format
    if align is not None:
        pf.alignment = align
    if keep:
        pf.keep_with_next = True
    if indent_first is not None:
        pf.first_line_indent = indent_first
    p_pr = st.element.get_or_add_pPr()
    if line is not None or before is not None or after is not None:
        sp = p_pr.find(qn("w:spacing"))
        if sp is None:
            sp = OxmlElement("w:spacing")
            p_pr.append(sp)
        if line is not None:
            sp.set(qn("w:line"), str(line))
            sp.set(qn("w:lineRule"), "auto")
        if before is not None:
            sp.set(qn("w:before"), str(before))
        if after is not None:
            sp.set(qn("w:after"), str(after))
    if outline is not None:
        ol = p_pr.find(qn("w:outlineLvl"))
        if ol is None:
            ol = OxmlElement("w:outlineLvl")
            p_pr.append(ol)
        ol.set(qn("w:val"), str(outline))
    return st


# ================================================================== bibliography
LATEX_ACCENTS = {
    r'\"u': "ü", r'\"o': "ö", r'\"a': "ä", r'\"I': "Ï", r'\"i': "ï", r"\'a": "á", r"\'e": "é",
    r"\'i": "í", r"\'o": "ó", r"\'u": "ú", r"\'E": "É", r"\~a": "ã", r"\~n": "ñ", r"\`e": "è",
    r"\`a": "à", r"\c{c}": "ç", r"\v{s}": "š", r"\v{c}": "č", r"\ss": "ß", r"\&": "&",
}


def detex(s):
    s = re.sub(r"\{\\([\"'`~^])\{?(\w)\}?\}", lambda m: LATEX_ACCENTS.get("\\" + m.group(1) + m.group(2), m.group(2)), s)
    s = re.sub(r"\\([\"'`~^])\{?(\w)\}?", lambda m: LATEX_ACCENTS.get("\\" + m.group(1) + m.group(2), m.group(2)), s)
    for k, v in LATEX_ACCENTS.items():
        s = s.replace(k, v)
    s = s.replace("--", "–").replace("~", " ")
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


def parse_bib(path):
    text = path.read_text(encoding="utf-8")
    entries = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        kind, key = m.group(1).lower(), m.group(2)
        i, depth = m.end(), 1
        while depth and i < len(text):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        body = text[m.end():i - 1]
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*", body):
            j = fm.end()
            if body[j] == "{":
                d, k = 1, j + 1
                while d:
                    d += {"{": 1, "}": -1}.get(body[k], 0)
                    k += 1
                val = body[j + 1:k - 1]
            else:
                val = re.match(r"[^,\n]+", body[j:]).group(0)
            fields.setdefault(fm.group(1).lower(), val)
        entries[key] = (kind, fields)
    return entries


def ieee_authors(raw):
    names = [detex(a) for a in re.split(r"\s+and\s+", raw)]
    out = []
    for n in names:
        if "," in n:
            last, first = [x.strip() for x in n.split(",", 1)]
        else:
            parts = n.split()
            if len(parts) == 1:
                out.append(n)
                continue
            # keep particles with the surname
            k = len(parts) - 1
            while k > 1 and parts[k - 1][0].islower():
                k -= 1
            if k < len(parts) and parts[k] == "y" and k > 1:  # Spanish double surname, e.g. Aguera y Arcas
                k -= 1
            first, last = " ".join(parts[:k]), " ".join(parts[k:])
        initials = " ".join(
            "-".join(x[0] + "." for x in tok.split("-") if x) if not tok.endswith(".") else tok
            for tok in first.split()
        )
        out.append(f"{initials} {last}".strip())
    if len(out) > 6:
        return out[0] + " et al."
    if len(out) <= 2:
        return " and ".join(out)
    return ", ".join(out[:-1]) + ", and " + out[-1]


def ieee_reference(kind, f):
    au = ieee_authors(f.get("author", "")) if f.get("author") else ""
    title = detex(f.get("title", ""))
    year = detex(f.get("year", ""))
    parts = [au + "," if au else "", f"\u201c{title},\u201d"]
    if kind == "article":
        s = f"*{detex(f.get('journal', ''))}*"
        if f.get("volume"):
            s += f", vol. {detex(f['volume'])}"
        if f.get("number"):
            s += f", no. {detex(f['number'])}"
        if f.get("pages"):
            pg = detex(f["pages"])
            s += (f", pp. {pg}" if "–" in pg else f", Art. no. {pg}")
        s += f", {year}"
        parts.append(s)
    elif kind == "inproceedings":
        s = f"in *{detex(f.get('booktitle', ''))}*"
        if f.get("series"):
            s += f" ({detex(f['series'])})"
        s += f", {year}"
        if f.get("pages"):
            s += f", pp. {detex(f['pages'])}"
        parts.append(s)
    elif kind == "book":
        s = f"*{title}*"
        parts = [au + "," if au else "", s]
        if f.get("series"):
            parts.append(detex(f["series"]))
        if f.get("publisher"):
            parts.append(detex(f["publisher"]))
        parts.append(year)
        return " ".join(p for p in parts if p).replace(" ,", ",") + "."
    else:
        hp = detex(f.get("howpublished", ""))
        parts.append(", ".join(x for x in (hp, year) if x))
    s = " ".join(p for p in parts if p)
    extra = []
    if f.get("note") and kind != "misc":
        extra.append(detex(f["note"]))
    if f.get("doi"):
        extra.append("doi: " + detex(f["doi"]))
    s = s + "." + ("" if not extra else " " + ". ".join(extra) + ".")
    return s.replace(",.", ".").replace("..", ".")


# ================================================================== markdown parsing
LABEL_RE = re.compile(r"\{#((?:fig|tab|sec):[\w-]+)([^}]*)\}")
SRC_RE = re.compile(r"<!--\s*src:\s*(.*?)\s*-->")
CMT_RE = re.compile(r"<!--.*?-->")


TEXT_WIDTH_CM = 16.4  # body section: 12240 twips page, 1701 + 1080 margins


def column_widths(rows, ncol, total, size=10.0):
    """Column widths (cm): every column is wide enough for its longest unbreakable token at the
    table's font size (numbers never wrap), and the space left over goes to the columns that hold
    the most text."""
    def plain(c):
        return re.sub(r"[*`]|\[@[^\]]*\]|@\w+:[\w-]+", "xxxx", c)
    pt_per_char = 0.52 * size          # Times New Roman, average glyph width
    pad = 0.42                         # left + right cell margins, cm
    mins, weights = [], []
    for ci in range(ncol):
        cells = [plain(r[ci]) if ci < len(r) else "" for r in rows]
        body, head = cells[1:] or cells, cells[0]
        longest_body = max((len(t) for c in body for t in c.split()), default=1)
        longest_head = max((len(t) for t in head.split()), default=1) * 1.1   # header is bold
        need = max(longest_body, longest_head) * pt_per_char / 28.35 + pad
        mins.append(max(need, 0.9))
        weights.append(sum(len(c) for c in body) / max(len(body), 1))
    if sum(mins) >= total:
        return [m * total / sum(mins) for m in mins]
    extra = total - sum(mins)
    wsum = sum(weights) or 1.0
    return [m + extra * w / wsum for m, w in zip(mins, weights)]


def split_row(row):
    """Split a pipe-table row on unescaped pipes; "\\|" inside a cell is a literal pipe."""
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    cells = re.split(r"(?<!\\)\|", row)
    return [c.replace("\\|", "|").strip() for c in cells]


def strip_comments(s):
    return CMT_RE.sub("", s).rstrip()


def parse_markdown(text):
    """Return a list of blocks: dicts with a 'type' key."""
    lines = text.replace("\r\n", "\n").split("\n")
    blocks, i = [], 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s or (s.startswith("<!--") and s.endswith("-->")):
            i += 1
            continue
        if s.startswith("```"):
            raise ValueError(f"fenced block without a 'Code:' caption at line {i + 1}")
        m = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m:
            lvl, title = len(m.group(1)), m.group(2)
            lab = LABEL_RE.search(title)
            label = lab.group(1) if lab else None
            title = LABEL_RE.sub("", title).strip()
            blocks.append({"type": "heading", "level": lvl, "text": title, "label": label})
            i += 1
            continue
        if s.startswith("Table:"):
            cap = s[len("Table:"):].strip()
            lab = LABEL_RE.search(cap)
            label, opts = (lab.group(1), lab.group(2)) if lab else (None, "")
            cap = strip_comments(LABEL_RE.sub("", cap)).strip()
            size = re.search(r"size=([\d.]+)", opts)
            i += 1
            rows = []
            while i < len(lines) and (lines[i].strip().startswith("|") or lines[i].strip().startswith("<!--")):
                if lines[i].strip().startswith("|"):
                    rows.append(lines[i].strip())
                i += 1
            blocks.append({"type": "table", "caption": cap, "label": label, "rows": rows,
                           "size": float(size.group(1)) if size else 10.0})
            continue
        if s.startswith("Code:"):
            cap = s[len("Code:"):].strip()
            lab = LABEL_RE.search(cap)
            label = lab.group(1) if lab else None
            cap = LABEL_RE.sub("", cap)
            pm = re.search(r"\[([^\]]+)\]\s*$", cap)
            path = pm.group(1) if pm else ""
            cap = cap[:pm.start()].strip() if pm else cap.strip()
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                i += 1
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i].rstrip("\n"))
                i += 1
            i += 1
            blocks.append({"type": "code", "caption": cap, "label": label, "path": path, "lines": code})
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            blocks.append({"type": "table", "caption": None, "label": None, "rows": rows, "size": 12.0})
            continue
        m = re.match(r"^!\[(.*)\]\(([^)]+)\)(\{[^}]*\})?", s)
        if m:
            opts = m.group(3) or ""
            lab = re.search(r"#((?:fig):[\w-]+)", opts)
            w = re.search(r"width=([\d.]+)", opts)
            blocks.append({"type": "figure", "caption": m.group(1), "path": m.group(2),
                           "label": lab.group(1) if lab else None, "width": float(w.group(1)) if w else 15.0})
            i += 1
            continue
        if re.match(r"^(-|\d+\.)\s+", s):
            items, numbered = [], bool(re.match(r"^\d+\.", s))
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("<!--"):
                t = lines[i].strip()
                mm = re.match(r"^(-|\d+\.)\s+(.*)$", t)
                if mm:
                    items.append(mm.group(2))
                else:
                    items[-1] += " " + t
                i += 1
            blocks.append({"type": "list", "numbered": numbered, "items": items})
            continue
        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            blocks.append({"type": "quote", "text": " ".join(buf)})
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3}\s|Table:|Code:|!\[|```|>|-\s|\d+\.\s)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        blocks.append({"type": "para", "text": " ".join(buf)})
    for b in blocks:  # remove inline comments from rendered text
        for k in ("text", "caption"):
            if b.get(k):
                b[k] = strip_comments(b[k])
        if "items" in b:
            b["items"] = [strip_comments(x) for x in b["items"]]
    return blocks


# ================================================================== builder
class Report:
    def __init__(self, submission):
        self.submission = submission
        self.doc = docx.Document(str(TEMPLATE))
        self.bib = parse_bib(BIB)
        self.cite_order = []
        self.labels = {}
        self.missing_photos = []

    # ---------------------------------------------------------------- styles
    def make_styles(self):
        d = self.doc
        ensure_style(d, "Report Body", "Normal", size=12, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line=360, after=120,
                     indent_first=Cm(1.27))
        ensure_style(d, "Report Body NoIndent", "Report Body", indent_first=Cm(0))
        ensure_style(d, "Chapter Number", "Normal", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=360)
        ensure_style(d, "Chapter Title", "Normal", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=360,
                     after=360, keep=True)
        ensure_style(d, "Section Heading", "Normal", size=14, bold=True, line=360, before=240, after=120,
                     outline=1, keep=True)
        ensure_style(d, "Subsection Heading", "Normal", size=13, bold=True, line=360, before=180, after=60,
                     outline=2, keep=True)
        ensure_style(d, "Figure Caption", "Caption", align=WD_ALIGN_PARAGRAPH.CENTER, after=240, line=240)
        ensure_style(d, "Table Caption", "Normal", size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, before=120,
                     after=120, keep=True, line=240)
        ensure_style(d, "Report Code", "Plain Text", size=10, line=240)
        ensure_style(d, "Report Reference", "Default", size=11.5, line=276, after=120)
        ensure_style(d, "Table Text", "Normal", line=240)

    # ---------------------------------------------------------------- front pages
    def check_template(self):
        body = list(self.doc.element.body.iterchildren())
        P = lambda i: Paragraph(body[i], self.doc).text
        expect = {T_TITLE: "TITLE OF THE PROJECT", T_GUIDE: "DR. YYYYY", T_DATE: "NOVEMBER 2026",
                  T_CERT_GUIDE: "<Name of the Guide>", T_ACK_MEMBERS[0]: "[Name of Student 1]"}
        for i, txt in expect.items():
            if txt not in P(i):
                raise SystemExit(f"template changed: body[{i}] = {P(i)!r}, expected {txt!r}")

    def front_pages(self):
        body = list(self.doc.element.body.iterchildren())
        P = lambda i: Paragraph(body[i], self.doc)
        # title page
        set_text(P(T_TITLE), TITLE.replace(": ", ":\n", 1))
        for idx, (name, reg) in zip(T_NAMES, MEMBERS):
            set_text(P(idx), f"{name} ({reg})")
        set_text(P(T_GUIDE), GUIDE)
        set_text(P(T_DATE), MONTH_YEAR)

        # certificate
        p = P(T_CERT_BODY)
        rpr = copy.deepcopy(p.runs[0]._r.rPr)
        for r in list(p._p):
            if r.tag != qn("w:pPr"):
                p._p.remove(r)
        names = [f"{n} ({r})" for n, r in MEMBERS]
        add_run_like(p, "This is to certify that the Capstone Project work titled \u201c", rpr)
        add_run_like(p, TITLE, rpr, bold=True)
        add_run_like(p, "\u201d that is being submitted by " + ", ".join(names[:-1]) + ", and " + names[-1] +
                     " is in partial fulfillment of the requirements for the award of Bachelor of Technology, is a "
                     "record of bonafide work done under my guidance. The contents of this Project work, in full or "
                     "in parts, have neither been taken from any other source nor have been submitted to any other "
                     "Institute or University for award of any degree or diploma and the same is certified.", rpr)
        set_text(P(T_CERT_GUIDE), GUIDE)
        p = P(T_CERT_HOD)
        rpr = copy.deepcopy(p.runs[0]._r.rPr)
        for r in list(p._p):
            if r.tag != qn("w:pPr"):
                p._p.remove(r)
        add_run_like(p, f"HoD, Department of {DEPARTMENT}" if DEPARTMENT else "HoD", rpr)

        # acknowledgement
        heading = None
        for el in body[T_CERT_HOD:T_ACK_VC]:
            if Paragraph(el, self.doc).text.strip() == "ACKNOWLEDGEMENT":
                heading = Paragraph(el, self.doc)
        if heading is not None:
            tc_entry(heading, "ACKNOWLEDGEMENT", 1)
            # The certificate fills its page exactly, so the template's separate page-break
            # paragraph would land on a page of its own; break before the heading instead.
            prev = heading._p.getprevious()
            if prev is not None and prev.xpath('.//w:br[@w:type="page"]') and not Paragraph(prev, self.doc).text.strip():
                prev.getparent().remove(prev)
            page_break_before(heading)
            # Empty spacer paragraphs between acknowledgement paragraphs: keep them, but at 6 pt
            # so the four names stay on the acknowledgement page after the added dataset sentence.
            el = heading._p.getnext()
            while el is not None and el is not P(T_ACK_MEMBERS[0] - 1)._p:
                if el.tag == qn("w:p") and not Paragraph(el, self.doc).text.strip():
                    sp = Paragraph(el, self.doc)
                    sp_spacing = ppr(sp).find(qn("w:spacing"))
                    if sp_spacing is None:
                        sp_spacing = OxmlElement("w:spacing")
                        ppr(sp).append(sp_spacing)
                    sp_spacing.set(qn("w:line"), "120")
                    sp_spacing.set(qn("w:lineRule"), "exact")
                el = el.getnext()
        p = P(T_ACK_VC)
        set_text(p, p.text.replace("Dr. Dr. P. Arulmozhivarman", "Dr. P. Arulmozhivarman"))
        p = P(T_ACK_HOD)
        rpr = copy.deepcopy(p.runs[0]._r.rPr)
        for r in list(p._p):
            if r.tag != qn("w:pPr"):
                p._p.remove(r)
        add_run_like(p, "We express our sincere thanks to Dr. S. Sudhakar Ilango, Dean, SCOPE, Dr. Saroj Kumar "
                        "Panigrahy, Associate Dean, SCOPE, and the Head of the Department, "
                        + (f"Department of {DEPARTMENT}" if DEPARTMENT else "School of Computer Science and Engineering")
                        + ", for the continuous encouragement, academic support, and facilities provided "
                        "throughout the project.", rpr)
        p = P(T_ACK_GUIDE)
        rpr = copy.deepcopy(p.runs[0]._r.rPr)
        set_text(p, p.text.replace("<Name of the Guide>", GUIDE))
        # one sentence for the dataset providers, added to the faculty-and-staff paragraph so the
        # acknowledgement keeps the template's paragraph structure and stays on one page
        faculty = P(T_ACK_FAMILY - 2)
        # keep "Project Team Members:" and the four names together on one page
        for idx in (T_ACK_MEMBERS[0] - 1,) + T_ACK_MEMBERS[:-1]:
            keep_next(P(idx))
        set_text(faculty, faculty.text.rstrip() +
                 " We also thank the Canadian Institute for Cybersecurity (CIC) at the University of New Brunswick "
                 "for releasing the CICIDS2017 dataset, and the DistriNet research group at KU Leuven for the "
                 "corrected version of it on which every experiment in this report was run.")
        for idx, (name, reg) in zip(T_ACK_MEMBERS, MEMBERS):
            set_text(P(idx), f"{name} \u2013 {reg}")

        # delete everything after the member list, keeping the final section properties
        body = list(self.doc.element.body.iterchildren())
        last = body.index(P(T_ACK_MEMBERS[-1])._p)
        for el in body[last + 1:]:
            if el.tag != qn("w:sectPr"):
                self.doc.element.body.remove(el)

    # ---------------------------------------------------------------- inline text
    def resolve_cites(self, keys):
        nums = []
        for k in keys:
            if k not in self.bib:
                raise SystemExit(f"citation key not in paper/refs.bib: {k}")
            if k not in self.cite_order:
                self.cite_order.append(k)
            nums.append(self.cite_order.index(k) + 1)
        nums = sorted(set(nums))
        # compress runs: [3]-[5]
        out, i = [], 0
        while i < len(nums):
            j = i
            while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
                j += 1
            out.append(f"[{nums[i]}]\u2013[{nums[j]}]" if j - i >= 2 else ", ".join(f"[{n}]" for n in nums[i:j + 1]))
            i = j + 1
        return ", ".join(out)

    def expand(self, text):
        """Resolve citations and cross-references to plain text."""
        text = re.sub(r"\[((?:@[\w-]+(?:;\s*)?)+)\]",
                      lambda m: self.resolve_cites(re.findall(r"@([\w-]+)", m.group(1))), text)

        def ref(m):
            lab = m.group(1)
            if lab not in self.labels:
                raise SystemExit(f"unknown reference @{lab}")
            return self.labels[lab]
        return re.sub(r"(?<![\w/])@((?:fig|tab|sec):[\w-]+)", ref, text)

    def add_inline(self, p, text, size=None, base_bold=False):
        text = self.expand(text)
        for tok in re.split(r"(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)", text):
            if not tok:
                continue
            bold, italic = base_bold, False
            if tok.startswith("**"):
                tok, bold = tok[2:-2], True
            elif tok.startswith("`"):
                tok = tok[1:-1]
            elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
                tok, italic = tok[1:-1], True
            r = p.add_run(tok)
            r.bold = bold or None
            r.italic = italic or None
            if size:
                r.font.size = Pt(size)

    # ---------------------------------------------------------------- blocks
    def para(self, text, style="Report Body"):
        p = self.doc.add_paragraph(style=style)
        self.add_inline(p, text)
        return p

    def heading_page(self, text, size=14, bold=True, tc=None, style_line=360):
        p = self.doc.add_paragraph(style="Normal")
        page_break_before(p)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_spacing(p, line=style_line, after=240)
        r = p.add_run(text)
        r.bold = bold
        r.font.size = Pt(size)
        if tc:
            tc_entry(p, tc, 1)
        return p

    def table(self, b):
        rows = [split_row(r) for r in b["rows"]]
        aligns = []
        if len(rows) > 1 and all(re.match(r"^:?-+:?$", c) for c in rows[1]):
            for c in rows[1]:
                aligns.append(WD_ALIGN_PARAGRAPH.RIGHT if c.endswith(":") and not c.startswith(":")
                              else WD_ALIGN_PARAGRAPH.CENTER if c.startswith(":") and c.endswith(":")
                              else WD_ALIGN_PARAGRAPH.LEFT)
            rows = [rows[0]] + rows[2:]
        cap = self.doc.add_paragraph(style="Table Caption")
        cap.add_run(self.labels[b["label"]] + " ")
        self.add_inline(cap, b["caption"])
        ncol = max(len(r) for r in rows)
        t = self.doc.add_table(rows=len(rows), cols=ncol)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_pr = t._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement(f"w:{edge}")
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), "4")
            e.set(qn("w:color"), "000000")
            borders.append(e)
        tbl_pr.append(borders)
        # column widths in proportion to the text each column holds
        widths = column_widths(rows, ncol, TEXT_WIDTH_CM, b["size"])
        w = tbl_pr.find(qn("w:tblW"))
        if w is None:
            w = OxmlElement("w:tblW")
            tbl_pr.append(w)
        w.set(qn("w:w"), str(int(sum(widths) * 567)))
        w.set(qn("w:type"), "dxa")
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        tbl_pr.append(layout)
        for gc, wd in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(int(wd * 567)))
        keep_rows = len(rows) <= 16
        for ri, row in enumerate(rows):
            tr = t.rows[ri]
            if ri == 0:
                trpr = tr._tr.get_or_add_trPr()
                h = OxmlElement("w:tblHeader")
                trpr.append(h)
            tr._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
            for ci in range(ncol):
                cell = tr.cells[ci]
                cell.width = Cm(widths[ci])
                p = cell.paragraphs[0]
                p.style = self.doc.styles["Table Text"]
                if aligns and ci < len(aligns):
                    p.alignment = aligns[ci]
                txt = row[ci] if ci < len(row) else ""
                self.add_inline(p, txt, size=b["size"], base_bold=(ri == 0))
                if ri < len(rows) - 1 and keep_rows:
                    keep_next(p)
        self.doc.add_paragraph(style="Table Text")  # spacer after table

    def plain_table(self, b):
        """Two-column list without caption or borders (abbreviations, symbols)."""
        rows = [split_row(r) for r in b["rows"]]
        rows = [r for r in rows if not all(re.match(r"^:?-+:?$", c) for c in r)]
        t = self.doc.add_table(rows=len(rows), cols=len(rows[0]))
        for ri, row in enumerate(rows):
            for ci, txt in enumerate(row):
                cell = t.rows[ri].cells[ci]
                cell.width = Cm(3.5) if ci == 0 else Cm(12.5)
                p = cell.paragraphs[0]
                p.style = self.doc.styles["Table Text"]
                set_spacing(p, line=300, after=40)
                self.add_inline(p, txt, size=12, base_bold=(ri == 0))

    def figure(self, b):
        path = ROOT / b["path"]
        if not path.exists():
            raise SystemExit(f"figure file missing: {b['path']}")
        p = self.doc.add_paragraph(style="Normal")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_spacing(p, before=120)
        keep_next(p)
        p.add_run().add_picture(str(path), width=Cm(b["width"]))
        cap = self.doc.add_paragraph(style="Figure Caption")
        cap.add_run(self.labels[b["label"]] + " ")
        self.add_inline(cap, b["caption"])

    def code(self, b):
        for k, line in enumerate(b["lines"]):
            p = self.doc.add_paragraph(style="Report Code")
            ppr(p).append(OxmlElement("w:keepLines"))
            if k < len(b["lines"]) - 1:
                keep_next(p)
            ind = OxmlElement("w:ind")
            ind.set(qn("w:left"), "360")
            ppr(p).append(ind)
            r = p.add_run(line if line else " ")
            r.font.name = FONT
            r._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), FONT)
        cap = self.doc.add_paragraph(style="Figure Caption")
        cap.add_run(self.labels[b["label"]] + " ")
        self.add_inline(cap, b["caption"] + (f" (`{b['path']}`)" if b["path"] else ""))

    def lst(self, b):
        for k, item in enumerate(b["items"], 1):
            p = self.doc.add_paragraph(style="Report Body NoIndent")
            set_spacing(p, after=60)
            ind = OxmlElement("w:ind")
            ind.set(qn("w:left"), "720")
            ind.set(qn("w:hanging"), "360")
            ppr(p).append(ind)
            p.add_run(f"{k}.\t" if b["numbered"] else "\u2022\t")
            self.add_inline(p, item)

    def quote(self, b):
        p = self.doc.add_paragraph(style="Report Body NoIndent")
        ind = OxmlElement("w:ind")
        ind.set(qn("w:left"), "720")
        ind.set(qn("w:right"), "720")
        ppr(p).append(ind)
        self.add_inline(p, b["text"])

    # ---------------------------------------------------------------- numbering pass
    def number(self, chapters):
        for ch_no, (title, blocks) in enumerate(chapters, 1):
            sec = sub = fig = tab = 0
            appendix = title.strip().lower() == "appendix"
            for b in blocks:
                if b["type"] == "heading" and b["level"] == 2:
                    sec, sub = sec + 1, 0
                    b["num"] = f"{ch_no}.{chr(64 + sec) if appendix else sec}"
                elif b["type"] == "heading" and b["level"] == 3:
                    sub += 1
                    b["num"] = f"{ch_no}.{chr(64 + sec) if appendix else sec}.{sub}"
                elif b["type"] in ("figure", "code"):
                    fig += 1
                    b["num"] = f"Figure {ch_no}.{fig}"
                elif b["type"] == "table":
                    tab += 1
                    b["num"] = f"Table {ch_no}.{tab}"
                else:
                    continue
                if b.get("label"):
                    if b["label"] in self.labels:
                        raise SystemExit(f"duplicate label {b['label']}")
                    self.labels[b["label"]] = ("Section " + b["num"]) if b["type"] == "heading" else b["num"]
                elif b["type"] in ("figure", "code", "table"):
                    raise SystemExit(f"{b['type']} without a label: {b.get('caption')}")

    # ---------------------------------------------------------------- whole document
    def build(self, out_docx):
        self.check_template()
        self.make_styles()
        self.front_pages()

        abstract = (SRC / "00_abstract.md").read_text(encoding="utf-8")
        chapter_files = sorted(f for f in SRC.glob("[0-9][0-9]*_*.md") if not f.name.startswith("00_"))
        chapters = []
        for f in chapter_files:
            for blk in parse_markdown(f.read_text(encoding="utf-8")):
                if blk["type"] == "heading" and blk["level"] == 1:
                    chapters.append((blk["text"], []))
                if not chapters:
                    raise SystemExit(f"{f.name}: text before the first chapter heading")
                chapters[-1][1].append(blk)
        self.number(chapters)

        # abstract
        p = self.heading_page("ABSTRACT", size=12, tc="ABSTRACT")
        for blk in parse_markdown(abstract):
            if blk["type"] == "para":
                self.para(blk["text"])

        # contents and lists (real Word fields; Word fills them in on export)
        self.heading_page("TABLE OF CONTENTS")
        p = self.doc.add_paragraph(style="Normal")
        add_field(p, 'TOC \\f C \\l "1-1" \\t "Section Heading,2,Subsection Heading,3" \\h \\z',
                  "Right-click and choose Update Field to build the table of contents.")
        self.heading_page("List of Tables", tc="LIST OF TABLES")
        p = self.doc.add_paragraph(style="Normal")
        add_field(p, 'TOC \\h \\z \\t "Table Caption,1"', "Right-click and choose Update Field.")
        self.heading_page("List of Figures", tc="LIST OF FIGURES")
        p = self.doc.add_paragraph(style="Normal")
        add_field(p, 'TOC \\h \\z \\t "Figure Caption,1"', "Right-click and choose Update Field.")
        for fname, heading in (("00_abbreviations.md", "List of Abbreviations"), ("00_symbols.md", "List of Symbols")):
            path = SRC / fname
            if not path.exists():
                continue
            self.heading_page(heading, tc=heading.upper())
            for blk in parse_markdown(path.read_text(encoding="utf-8")):
                if blk["type"] == "table":
                    self.plain_table(blk)
                elif blk["type"] == "para":
                    self.para(blk["text"], style="Report Body NoIndent")

        # chapters
        for ch_no, (f, blocks) in enumerate(chapters, 1):
            for b in blocks:
                t = b["type"]
                if t == "heading" and b["level"] == 1:
                    p = self.doc.add_paragraph(style="Chapter Number")
                    page_break_before(p)
                    p.add_run(f"CHAPTER {ch_no}")
                    tc_entry(p, f"CHAPTER {ch_no}    {b['text'].upper()}", 1)
                    keep_next(p)
                    p = self.doc.add_paragraph(style="Chapter Title")
                    p.add_run(b["text"].upper())
                elif t == "heading":
                    st = "Section Heading" if b["level"] == 2 else "Subsection Heading"
                    p = self.doc.add_paragraph(style=st)
                    p.add_run(f"{b['num']}\t")
                    self.add_inline(p, b["text"])
                    tabs = OxmlElement("w:tabs")
                    tab = OxmlElement("w:tab")
                    tab.set(qn("w:val"), "left")
                    tab.set(qn("w:pos"), "851" if b["level"] == 2 else "993")
                    tabs.append(tab)
                    ppr(p).append(tabs)
                elif t == "para":
                    self.para(b["text"])
                elif t == "table":
                    self.table(b)
                elif t == "figure":
                    self.figure(b)
                elif t == "code":
                    self.code(b)
                elif t == "list":
                    self.lst(b)
                elif t == "quote":
                    self.quote(b)

        # references (chapter 7), IEEE style, in order of first citation
        n_ch = len(chapters) + 1
        p = self.doc.add_paragraph(style="Chapter Number")
        page_break_before(p)
        p.add_run(f"CHAPTER {n_ch}")
        tc_entry(p, f"CHAPTER {n_ch}    REFERENCES", 1)
        keep_next(p)
        p = self.doc.add_paragraph(style="Chapter Title")
        p.add_run("REFERENCES")
        for k, key in enumerate(self.cite_order, 1):
            kind, fields = self.bib[key]
            p = self.doc.add_paragraph(style="Report Reference")
            ind = OxmlElement("w:ind")
            ind.set(qn("w:left"), "567")
            ind.set(qn("w:hanging"), "567")
            ppr(p).append(ind)
            p.add_run(f"[{k}]\t")
            ref = ieee_reference(kind, fields)
            for tok in re.split(r"(\*[^*]+\*)", ref):
                if tok.startswith("*") and tok.endswith("*"):
                    p.add_run(tok[1:-1]).italic = True
                elif tok:
                    p.add_run(tok)
        self.uncited = sorted(set(self.bib) - set(self.cite_order))

        if self.submission:
            self.biodata()

        self.doc.core_properties.title = "XFed-IDS-ByzAgent: Explainable and Trust-Aware Federated Intrusion Detection"
        self.doc.core_properties.author = ", ".join(n for n, _ in MEMBERS)
        self.doc.core_properties.subject = "B.Tech Capstone Project Report, VIT-AP University"
        self.doc.core_properties.keywords = ""
        self.doc.core_properties.comments = ""
        self.doc.save(str(out_docx))

    # ---------------------------------------------------------------- biodata (submission build only)
    def biodata(self):
        text = BIODATA.read_text(encoding="utf-8")
        people = []
        for blockm in re.finditer(r"^##\s+(.*?)\n(.*?)(?=^##\s|\Z)", text, re.S | re.M):
            fields = dict(re.findall(r"^-\s*([^:]+):\s*(.*)$", blockm.group(2), re.M))
            people.append(fields)
        self.heading_page("BIODATA", tc="BIODATA", style_line=259)
        labels = [("Name", "Name"), ("Mobile Number", "Mobile"), ("E-mail", "E-mail"),
                  ("Permanent Address", "Permanent Address")]
        for k, person in enumerate(people):
            reg = person.get("Reg. No.", "").strip()
            photo = None
            for folder in (PHOTOS, PRIVATE):  # private/photos/ or directly in private/
                for ext in (".jpg", ".jpeg", ".png"):
                    cand = folder / f"{reg}{ext}"
                    if photo is None and cand.exists():
                        photo = cand
            if photo is None:
                self.missing_photos.append(f"{person.get('Name', '?')} ({reg})")
            t = self.doc.add_table(rows=1, cols=2 if photo else 1)
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            if photo:
                cell = t.rows[0].cells[0]
                cell.width = Cm(4.2)
                cell.paragraphs[0].add_run().add_picture(str(photo), width=Cm(3.5))
                info = t.rows[0].cells[1]
                info.width = Cm(11.5)
            else:
                info = t.rows[0].cells[0]
            first = True
            for label, key in labels:
                p = info.paragraphs[0] if first else info.add_paragraph()
                first = False
                p.style = self.doc.styles["Normal"]
                set_spacing(p, line=360)
                tabs = OxmlElement("w:tabs")
                tab = OxmlElement("w:tab")
                tab.set(qn("w:val"), "left")
                tab.set(qn("w:pos"), "2268")
                tabs.append(tab)
                ppr(p).append(tabs)
                ind = OxmlElement("w:ind")
                ind.set(qn("w:left"), "2410")
                ind.set(qn("w:hanging"), "2410")
                ppr(p).append(ind)
                p.add_run(f"{label}\t: {person.get(key, '').strip()}")
            spacer = self.doc.add_paragraph(style="Normal")
            set_spacing(spacer, after=480)


# ================================================================== figures that must be prepared
def prepare_figures():
    """Rasterise the paper's PDF figures and crop the pipeline diagram out of paper/main.pdf."""
    import fitz  # pymupdf
    out = REPORT / "figs"
    out.mkdir(exist_ok=True)
    for pdf in sorted((ROOT / "paper" / "figs").glob("*.pdf")):
        png = out / (pdf.stem + ".png")
        if not png.exists() or png.stat().st_mtime < pdf.stat().st_mtime:
            d = fitz.open(str(pdf))
            d[0].get_pixmap(dpi=300).save(str(png))
    png = out / "fig_pipeline.png"
    main_pdf = ROOT / "paper" / "main.pdf"
    if not png.exists() or png.stat().st_mtime < main_pdf.stat().st_mtime:
        d = fitz.open(str(main_pdf))
        for page in d:
            hits = page.search_for("1. Data")
            cap = page.search_for("The five-stage pipeline")
            if hits and cap:
                top = hits[0]
                r = fitz.Rect(cap[0].x0 - 6, top.y0 - 8, cap[0].x0 + page.rect.width / 2 - 40, cap[0].y0 - 4)
                # widen to the column that holds the drawing
                drawings = [dr["rect"] for dr in page.get_drawings() if dr["rect"].intersects(r)]
                if drawings:
                    x0 = min(dd.x0 for dd in drawings) - 4
                    x1 = max(dd.x1 for dd in drawings) + 4
                    y0 = min(dd.y0 for dd in drawings) - 4
                    y1 = max(dd.y1 for dd in drawings) + 4
                    r = fitz.Rect(x0, y0, x1, y1)
                page.get_pixmap(dpi=400, clip=r).save(str(png))
                break


# ================================================================== Word export
def word_export(docx_path, pdf_path):
    """Open in Word, update every field (TOC, lists) twice so page numbers settle, save, export PDF."""
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(docx_path), ReadOnly=False, AddToRecentFiles=False)
        for _ in range(2):
            doc.Fields.Update()
            for toc in doc.TablesOfContents:
                toc.Update()
            doc.Repaginate()
        doc.Save()
        doc.Close(False)
        # export from a fresh open of the saved file, so the PDF uses the same layout Word shows
        doc = word.Documents.Open(str(docx_path), ReadOnly=True, AddToRecentFiles=False)
        doc.Repaginate()
        doc.ExportAsFixedFormat(str(pdf_path), 17, False, 0)  # wdExportFormatPDF, no open, optimize for print
        pages = doc.ComputeStatistics(2)  # wdStatisticPages
        doc.Close(False)
        return pages
    finally:
        word.Quit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--only", choices=["public", "submission"])
    args = ap.parse_args()
    prepare_figures()
    builds = [("public", REPORT / "XFed_Capstone_Report.docx", False),
              ("submission", PRIVATE / "XFed_Capstone_Report_SUBMISSION.docx", True)]
    for name, out, sub in builds:
        if args.only and args.only != name:
            continue
        rep = Report(submission=sub)
        rep.build(out)
        print(f"[{name}] wrote {out.relative_to(ROOT)}; {len(rep.cite_order)} references cited, "
              f"{len(rep.labels)} labels")
        if rep.uncited:
            print(f"[{name}] bib entries not cited: {', '.join(rep.uncited)}")
        if rep.missing_photos:
            print(f"[{name}] biodata photos missing (no photo printed): {'; '.join(rep.missing_photos)}")
        if not args.no_pdf:
            pages = word_export(out.resolve(), out.with_suffix(".pdf").resolve())
            print(f"[{name}] exported {out.with_suffix('.pdf').relative_to(ROOT)} through Word: {pages} pages")


if __name__ == "__main__":
    sys.exit(main())
