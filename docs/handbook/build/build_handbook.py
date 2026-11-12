"""Assemble the handbook and render a single self-contained HTML file.

  docs/handbook/src/*.md            chapter sources, in file-name order
  -> docs/handbook/XFed_Team_Handbook.md     concatenated Markdown (the source of record)
  -> docs/handbook/XFed_Team_Handbook.html   self-contained HTML (SVG inlined, PNG base64)

Then render the PDF with:  node docs/handbook/build/render_pdf.mjs
Stdlib only; a deliberately small Markdown subset (headings with {#id}, paragraphs,
lists, tables, fenced code, blockquotes, standalone images, inline code/bold/italic/links).
"""
from __future__ import annotations

import base64
import html
import re
from pathlib import Path

HB = Path(__file__).resolve().parents[1]
SRC = HB / "src"
MD_OUT = HB / "XFed_Team_Handbook.md"
HTML_OUT = HB / "XFed_Team_Handbook.html"

TITLE = "XFed-IDS-ByzAgent Team Handbook"
SUBTITLE = "Everything you need to understand, explain and defend the project at the final review"


def assemble() -> str:
    parts = sorted(SRC.glob("*.md"))
    head = (f"# {TITLE}\n\n_{SUBTITLE}_\n\nVIT-AP University capstone project, 2026. "
            "V Naga Adithya (23BCE9062) · T Shaun (23BCE9916) · P Sampath (23BCE8614) · D Tharun (23BCE8818).\n\n"
            "Generated from `docs/handbook/src/` by `docs/handbook/build/build_handbook.py`. "
            "Every number cites the file it comes from.\n\n")
    body = "\n\n".join(p.read_text(encoding="utf-8").strip() for p in parts)
    return head + body + "\n"


# ------------------------------------------------------------------ inline
def slug(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "sec"


def inline(s: str) -> str:
    codes: list[str] = []

    def keep(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    s = re.sub(r"`([^`]+)`", keep, s)
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"(?<![\w])_(?!\s)(.+?)(?<!\s)_(?![\w])", r"<em>\1</em>", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{html.escape(codes[int(m.group(1))], quote=False)}</code>", s)
    # (source: ...) -> small citation text; allow nested code/parentheses-free content
    s = re.sub(r"\(source: (.+?)\)(?=[\s.,;:|]|$)", r'<span class="src">(source: \1)</span>', s)
    s = s.replace("[to verify in lit review]", '<span class="verify">[to verify in lit review]</span>')
    return s


# ------------------------------------------------------------------ images
def image_html(cap: str, src: str) -> str:
    path = (HB / src).resolve()
    cap_html = inline(cap)
    if not path.exists():
        return f'<figure class="missing"><figcaption>MISSING IMAGE {html.escape(src)}</figcaption></figure>'
    if path.suffix == ".svg":
        svg = path.read_text(encoding="utf-8")
        svg = re.sub(r'\swidth="\d+" height="\d+"', "", svg, count=1)
        inner = svg.replace("<svg ", '<svg class="fig" role="img" ', 1)
        # make marker ids unique per figure
        uid = slug(path.stem)
        inner = inner.replace('id="ar"', f'id="ar-{uid}"').replace("url(#ar)", f"url(#ar-{uid})")
    else:
        b64 = base64.b64encode(path.read_bytes()).decode()
        cls = "shot" if ("screens" in src or "crop" in src) else "png"
        inner = f'<img class="{cls}" alt="{html.escape(cap)}" src="data:image/png;base64,{b64}">'
    return f'<figure>{inner}<figcaption>{cap_html}</figcaption></figure>'


# ------------------------------------------------------------------ blocks
def convert(md: str) -> tuple[str, list[tuple[int, str, str]]]:
    lines = md.split("\n")
    out: list[str] = []
    toc: list[tuple[int, str, str]] = []
    i = 0
    in_exam = False
    used: set[str] = set()
    part = ""
    h2_in_part = 0

    def close_exam():
        nonlocal in_exam
        if in_exam:
            out.append("</section>")
            in_exam = False

    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*?)\s*(\{#([\w-]+)\})?\s*$", ln)
        if m:
            lvl, text, hid = len(m.group(1)), m.group(2), m.group(4)
            if lvl <= 2:
                close_exam()
            hid = hid or slug(text)
            base, n = hid, 2
            while hid in used:
                hid = f"{base}-{n}"; n += 1
            used.add(hid)
            cls = ""
            if lvl == 1:
                cls = (' class="part flow"' if text.startswith("Part 1 ") else ' class="part"') if text.startswith("Part") else ' class="doc-title"'
                part, h2_in_part = text, 0
            elif lvl == 2:
                h2_in_part += 1
                newpage = h2_in_part > 1 and part.startswith(("Part 2", "Part 3", "Part 6", "Part 7"))
                cls = ' class="chapter newpage"' if newpage else ' class="chapter"'
            elif lvl == 3 and text.startswith("Questions an examiner might ask"):
                close_exam()
                out.append('<section class="exam">')
                in_exam = True
                cls = ' class="exam-h"'
            elif lvl == 3 and text.startswith("In one line"):
                cls = ' class="oneline"'
            elif lvl == 3 and text.startswith("The plain version"):
                cls = ' class="plain"'
            if lvl <= 2 and not (lvl == 1 and not text.startswith("Part")):
                toc.append((lvl, hid, text))
            out.append(f"<h{lvl} id=\"{hid}\"{cls}>{inline(text)}</h{lvl}>")
            i += 1
            continue
        if ln.startswith("```"):
            j = i + 1
            buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j]); j += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            i = j + 1
            continue
        mi = re.match(r"^!\[(.*)\]\((\S+)\)\s*$", ln)
        if mi:
            out.append(image_html(mi.group(1), mi.group(2)))
            i += 1
            continue
        if ln.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i][1:].strip()); i += 1
            paras = " ".join(buf).split("  ")
            out.append("<blockquote>" + "".join(f"<p>{inline(p)}</p>" for p in [" ".join(buf)]) + "</blockquote>")
            continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            hdr, body = cells[0], [r for r in cells[2:]]
            h = "".join(f"<th>{inline(c)}</th>" for c in hdr)
            b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append(f'<div class="tw"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>')
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", ln):
            ordered = bool(re.match(r"^\s*\d+\.", ln))
            items: list[str] = []
            while i < len(lines) and (re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]) or (lines[i].startswith("  ") and lines[i].strip() and items)):
                l2 = lines[i]
                mm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", l2)
                if mm and len(mm.group(1)) < 2:
                    items.append(mm.group(3))
                elif mm:  # nested item: keep as indented line in parent
                    items[-1] += "<br>&nbsp;&nbsp;– " + mm.group(3)
                else:
                    items[-1] += " " + l2.strip()
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(it) if '<br>' not in it else inline(it.split('<br>')[0]) + ''.join('<br>' + inline(x) for x in it.split('<br>')[1:])}</li>" for it in items) + f"</{tag}>")
            continue
        if ln.strip() == "---":
            out.append("<hr>")
            i += 1
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,4}\s|```|\||>|!\[|\s*([-*]|\d+\.)\s)", lines[i]):
            buf.append(lines[i].strip()); i += 1
        if buf:
            out.append(f"<p>{inline(' '.join(buf))}</p>")
        else:
            i += 1
    close_exam()
    return "\n".join(out), toc


CSS = r"""
@page { size: A4; margin: 18mm 18mm 18mm 18mm; }
@page :first { margin-top: 0; margin-bottom: 0; }
:root { --ink:#1f2937; --mute:#6b7280; --line:#e5e7eb; --blue:#1d4ed8; --tint:#f8fafc; --exam:#fff7ed; --examline:#ea580c; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Inter, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: var(--ink); margin: 0; }
main { max-width: 820px; margin: 0 auto; padding: 0 16px 40px; }
a { color: var(--blue); text-decoration: none; }
code { font-family: "Cascadia Mono", Consolas, "JetBrains Mono", monospace; font-size: 0.88em; background: #f3f4f6; padding: 0 3px; border-radius: 3px; word-break: break-word; }
pre { background: #111827; color: #f9fafb; padding: 10px 12px; border-radius: 6px; overflow-x: auto; break-inside: avoid; }
pre code { background: none; color: inherit; font-size: 9pt; }
h1, h2, h3, h4 { line-height: 1.25; break-after: avoid; page-break-after: avoid; }
h1.part { font-size: 26pt; color: #fff; background: #1e3a8a; padding: 28mm 12mm 12mm; margin: 0 -16px 18px; break-before: page; page-break-before: always; border-radius: 0; }
h2.chapter { font-size: 17pt; color: #1e3a8a; border-bottom: 3px solid #1e3a8a; padding-bottom: 4px; margin-top: 28px; }
h1.part + h2.chapter { break-before: avoid; page-break-before: avoid; }
h1.part.flow { break-before: auto; page-break-before: auto; margin-top: 22px; }
h2.newpage { break-before: page; page-break-before: always; }
h3 { font-size: 13pt; margin: 20px 0 6px; color: #111827; }
h3.oneline { color: #1e3a8a; }
h3.oneline + p { font-size: 12pt; background: #eff6ff; border-left: 4px solid #1d4ed8; padding: 8px 12px; border-radius: 4px; }
h3.plain { color: #166534; margin-top: 14px; }
h3.plain + p { background: #f0fdf4; border: 1px solid #bbf7d0; border-left: 4px solid #16a34a; padding: 9px 13px; border-radius: 4px; break-inside: avoid; }
h4 { font-size: 11.5pt; }
p { margin: 6px 0 9px; orphans: 3; widows: 3; }
ul, ol { padding-left: 22px; margin: 6px 0 10px; }
li { margin: 3px 0; }
blockquote { margin: 10px 0; padding: 8px 14px; border-left: 4px solid #7c3aed; background: #faf5ff; font-style: italic; break-inside: avoid; }
.tw { overflow-x: auto; margin: 8px 0 12px; }
table { border-collapse: collapse; width: 100%; font-size: 9.2pt; }
th, td { border: 1px solid var(--line); padding: 4px 6px; vertical-align: top; text-align: left; overflow-wrap: anywhere; }
th { background: #f1f5f9; }
tr { break-inside: avoid; page-break-inside: avoid; }
td code, th code { font-size: 8.4pt; }
figure { margin: 12px 0 16px; text-align: center; break-inside: avoid; page-break-inside: avoid; }
figure svg.fig { width: 100%; height: auto; max-height: 120mm; }
figure img.png { max-width: 100%; max-height: 105mm; }
figure img.shot { max-width: 100%; max-height: 200mm; border: 1px solid var(--line); }
figcaption { font-size: 9pt; color: var(--mute); margin-top: 4px; text-align: left; }
.src { font-size: 8.2pt; color: var(--mute); white-space: normal; }
.src code { font-size: 7.8pt; background: none; padding: 0; color: #4b5563; }
.verify { font-size: 8.5pt; color: #b45309; font-weight: 600; }
section.exam { background: var(--exam); border: 1px solid #fed7aa; border-left: 5px solid var(--examline); border-radius: 6px; padding: 4px 14px 8px; margin: 18px 0; }
section.exam h3.exam-h { color: #9a3412; }
section.exam p { break-inside: avoid; }
section.exam p strong:first-child { color: #9a3412; }
hr { border: 0; border-top: 1px solid var(--line); margin: 20px 0; }
.cover { height: 293mm; padding-top: 48mm !important; display: flex; flex-direction: column; justify-content: space-between; padding: 30mm 6mm 10mm; break-after: page; page-break-after: always; }
.cover .band { background: #1e3a8a; color: #fff; padding: 18mm 12mm; border-radius: 6px; }
.cover h1 { font-size: 30pt; margin: 0 0 8px; color: #fff; }
.cover .sub { font-size: 14pt; opacity: .9; }
.cover .pitch { font-size: 13pt; font-style: italic; color: #1e3a8a; border-left: 4px solid #1e3a8a; padding-left: 12px; }
.cover .meta { font-size: 10pt; color: var(--mute); }
nav.toc { break-after: page; page-break-after: always; }
nav.toc h1 { font-size: 22pt; color: #1e3a8a; }
nav.toc ol { list-style: none; padding-left: 0; }
nav.toc li.l1 { font-weight: 700; margin-top: 7px; font-size: 11pt; }
nav.toc li.l2 { padding-left: 18px; font-size: 10pt; margin: 0; }
nav.toc a { display: flex; align-items: baseline; gap: 6px; }
nav.toc .tt { flex: 0 1 auto; }
nav.toc .pg { flex: 1 0 auto; text-align: right; color: var(--ink); border-bottom: 1px dotted #9ca3af; min-width: 30px; }
h1.doc-title { display: none; }
.doc-title + p, .doc-title + p + p, .doc-title + p + p + p { display: none; }
@media print { main { max-width: none; padding: 0; } h1.part { margin: 0 0 18px; } }
@media screen { body { background: #f3f4f6; } main { background: #fff; padding: 20px 40px 60px; box-shadow: 0 0 12px rgba(0,0,0,.08); } h1.part { padding: 24px 16px; margin: 40px -40px 18px; } .cover { height: auto; min-height: 60vh; } }
"""


def build():
    md = assemble()
    MD_OUT.write_text(md, encoding="utf-8")
    body, toc = convert(md)
    import json
    tp = HB / "build" / "toc_pages.json"
    pages = {re.sub(r"\s+", "", k): v for k, v in json.loads(tp.read_text(encoding="utf-8")).items()} if tp.exists() else {}
    toc_html = ['<nav class="toc"><h1>Contents</h1><ol>']
    for lvl, hid, text in toc:
        plain = re.sub(r"\s+", " ", re.sub(r"[`*]", "", text)).strip()
        pg = pages.get(re.sub(r"\s+", "", plain), "")
        if pg == "":
            num = re.match(r"^(Part \d+|\d+(?:\.\d+)+)", plain)
            if num:
                key = re.sub(r"\s+", "", num.group(1))
                pg = next((v for k, v in pages.items() if k.startswith(key) and not k[len(key):len(key) + 1].isdigit()
                           and not k[len(key):len(key) + 2].startswith(".")), "")
        toc_html.append(f'<li class="l{lvl}"><a href="#{hid}"><span class="tt">{inline(text)}</span><span class="pg">{pg}</span></a></li>')
    toc_html.append("</ol></nav>")
    cover = f"""<section class="cover">
<div class="band"><h1>{TITLE}</h1><div class="sub">{SUBTITLE}</div></div>
<p class="pitch">A federated IDS that doesn't just detect attacks, but checks whether its own explanations and its own participants can be trusted.</p>
<div class="meta">VIT-AP University capstone project, 2026 · V Naga Adithya (23BCE9062) · T Shaun (23BCE9916) · P Sampath (23BCE8614) · D Tharun (23BCE8818)<br>
Teaching document, not a paper. Every number cites the file it comes from. Canonical results: <code>docs/contribution_a_results.md</code> (explanation check) and <code>docs/contribution_b_results.md</code> (trust check); where anything here disagrees with them, they win.</div>
</section>"""
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE}</title><style>{CSS}</style></head>
<body><main>{cover}{''.join(toc_html)}{body}</main></body></html>"""
    HTML_OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {MD_OUT.name} ({len(md):,} chars), {HTML_OUT.name} ({len(doc)/1e6:.1f} MB), toc entries {len(toc)}")


if __name__ == "__main__":
    build()
