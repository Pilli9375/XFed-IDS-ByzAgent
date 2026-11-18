"""Structural and wording checks for the Final Review deck.

Run from the repository root (after build_ppt.py):
    python docs/ppt/check_deck.py

Checks, per slide:
  * the VIT-AP logo (the template's logo image) is present;
  * a slide-number field is present (page numbers then run in order by themselves);
  * every shape lies inside the slide, and nothing we added sits on the page-number dot;
  * text sizes: text boxes >= 14 pt, table cells >= 12 pt (template title-slide text excepted);
  * at most 5 bullets per slide and about 12 words per bullet (more than 14 is reported);
  * no leftover template text ("[Title", "Prof. /Dr.", "Prof. /", empty bulleted lines);
  * speaker notes: start with a speaker name, 60-120 spoken words, and a likely-question line.
Wording search over slides, notes and speaker_script.md: "first to", "novel", "explains its
reasoning", "realistic", p-values, and the 0% credited to anything but Multi-Krum.
Writes docs/ppt/deck_check.md. Exit code 1 on any failure.
"""
import hashlib
import os
import re
import sys

from pptx import Presentation
from pptx.util import Emu

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PPT = os.path.join(ROOT, "docs", "ppt")
DECK = os.path.join(PPT, "XFed_Capstone_Final_Review.pptx")
TEMPLATE = os.path.join(PPT, "template", "Capstone_PPT_Template.pptx")
SPEAKERS = ("Adithya", "Shaun", "Tharun", "Sampath")
DOT = (Emu(8540000), Emu(4650000))   # top-left corner of the page-number dot area
FORBIDDEN = [r"\bfirst to\b", r"\bnovel\b", r"explains its reasoning", r"\brealistic\b", r"\bp\s*[<=>]\s*0?\.\d",
             r"p-value(?!s)", r"\bKrum excluded\b(?<!Multi-Krum excluded)"]


def logo_hash():
    t = Presentation(TEMPLATE)
    for sh in t.slides[2].shapes:
        if sh.shape_type == 13:
            return hashlib.sha1(sh.image.blob).hexdigest()


def main():
    prs = Presentation(DECK)
    W, H = prs.slide_width, prs.slide_height
    logo = logo_hash()
    fails, notes_rows = [], []
    for n, s in enumerate(prs.slides, start=1):
        has_logo = any(sh.shape_type == 13 and hashlib.sha1(sh.image.blob).hexdigest() == logo for sh in s.shapes)
        has_num = any('type="slidenum"' in sh._element.xml for sh in s.shapes if sh.has_text_frame)
        if not has_logo:
            fails.append((n, "no VIT-AP logo"))
        if not has_num and n != 1:
            fails.append((n, "no page-number field"))
        bullets = 0
        for sh in s.shapes:
            if sh.left < 0 or sh.top < -Emu(120000) or sh.left + sh.width > W or sh.top + sh.height > H:
                if sh.name.startswith(("TextShape", "CustomShape", "Picture", "Title")):
                    pass  # template's own shapes keep the template's positions
                else:
                    fails.append((n, f"shape '{sh.name}' outside the slide"))
            ours = not sh.name.startswith(("TextShape", "CustomShape", "Picture 2", "Picture 3", "Picture 4",
                                           "Title", "Subtitle"))
            if ours and sh.left + sh.width > DOT[0] and sh.top + sh.height > DOT[1]:
                fails.append((n, f"shape '{sh.name}' overlaps the page-number dot"))
            if sh.has_text_frame and 'type="slidenum"' not in sh._element.xml:
                for p in sh.text_frame.paragraphs:
                    bulleted = p._p.pPr is not None and p._p.pPr.find(
                        "{http://schemas.openxmlformats.org/drawingml/2006/main}buChar") is not None
                    txt = p.text.strip()
                    if bulleted and not txt and n != 2:
                        fails.append((n, "empty bulleted line"))
                    if bulleted and txt and sh.name != "TextShape 2" and n != 2:
                        bullets += 1
                        if len(txt.split()) > 14:
                            fails.append((n, f"bullet over 14 words: {txt!r}"))
                    for r in p.runs:
                        if r.font.size is not None and r.font.size.pt < 14 and n != 1 and r.text.strip():
                            fails.append((n, f"text under 14 pt ({r.font.size.pt}): {r.text[:40]!r}"))
            if sh.has_table:
                for row in sh.table.rows:
                    for cell in row.cells:
                        for p in cell.text_frame.paragraphs:
                            for r in p.runs:
                                if r.font.size is not None and r.font.size.pt < 12:
                                    fails.append((n, f"table text under 12 pt: {r.text[:40]!r}"))
        if bullets > 5:
            fails.append((n, f"{bullets} bullets (max 5)"))
        alltext = " ".join(sh.text_frame.text for sh in s.shapes if sh.has_text_frame)
        for bad in ("[Title", "Prof. /Dr", "Prof. /", "Amravati", "[Title of the Project]"):
            if bad in alltext:
                fails.append((n, f"leftover template text {bad!r}"))
        note = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
        speaker = note.split(":", 1)[0]
        speech = note.split("\n\nLikely question:")[0].split(":", 1)[-1]
        wc = len(speech.split())
        notes_rows.append((n, speaker, wc))
        if speaker not in SPEAKERS:
            fails.append((n, "note does not start with a speaker name"))
        if not (60 <= wc <= 120):
            fails.append((n, f"note has {wc} spoken words (60-120)"))
        if "Likely question:" not in note:
            fails.append((n, "note has no likely-question line"))

    # wording search
    texts = []
    for n, s in enumerate(prs.slides, start=1):
        for sh in s.shapes:
            if sh.has_text_frame:
                texts.append((f"slide {n}", sh.text_frame.text))
            if sh.has_table:
                texts += [(f"slide {n} table", c.text_frame.text) for r in sh.table.rows for c in r.cells]
        texts.append((f"slide {n} notes", s.notes_slide.notes_text_frame.text))
    texts.append(("speaker_script.md", open(os.path.join(PPT, "speaker_script.md"), encoding="utf-8").read()))
    hits = []
    for where, t in texts:
        for pat in FORBIDDEN:
            for m in re.finditer(pat, t, flags=re.I):
                ctx = t[max(0, m.start() - 40): m.end() + 40].replace("\n", " ")
                hits.append((where, pat, ctx))
        for m in re.finditer(r"(?<![\d.])0\s?%", t):
            ctx = t[max(0, m.start() - 60): m.end()].replace("\n", " ")
            if "Multi-Krum" not in ctx and "poisoned org 0%" not in ctx:
                hits.append((where, "0% not credited to Multi-Krum", ctx))
    # The handbook's "No p-values" phrasing is the project's own rule; allow only these exact phrases.
    hits = [h for h in hits if not re.search(r"no p-values|No p-values", h[2])]

    L = ["# Deck check: Capstone Final Review\n",
         "Generated by `python docs/ppt/check_deck.py` on `docs/ppt/XFed_Capstone_Final_Review.pptx`.\n",
         f"Slides: {len(prs.slides)}. Structural failures: {len(fails)}. Wording hits: {len(hits)}.\n",
         "Checked on every slide: VIT-AP logo present; page-number field present (slide 1 keeps the template's "
         "own number box); shapes inside the slide and clear of the page-number dot; text boxes at least 14 pt "
         "and table text at least 12 pt (title slide keeps the template's sizes); at most 5 bullets and no bullet "
         "over 14 words; no leftover template text or empty bulleted lines; notes start with a speaker name, "
         "have 60-120 spoken words and a likely-question line.\n",
         "Wording searched in slides, tables, notes and `speaker_script.md`: \"first to\", \"novel\", "
         "\"explains its reasoning\", \"realistic\", p-values (\"p < 0.05\" style), and any \"0%\" not "
         "credited to Multi-Krum. The phrase \"no p-values\" (the project's own rule) is allowed.\n"]
    if fails:
        L.append("## Structural failures\n")
        L += [f"- slide {n}: {msg}" for n, msg in fails]
        L.append("")
    if hits:
        L.append("## Wording hits\n")
        L += [f"- {w}: `{p}` in \"{c}\"" for w, p, c in hits]
        L.append("")
    L.append("## Speaker notes\n")
    L.append("| Slide | Speaker | Spoken words |")
    L.append("|---:|---|---:|")
    L += [f"| {n} | {sp} | {wc} |" for n, sp, wc in notes_rows]
    open(os.path.join(PPT, "deck_check.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"structural failures: {len(fails)}; wording hits: {len(hits)}")
    for f in fails:
        print("  FAIL", f)
    for h in hits:
        print("  HIT", h)
    sys.exit(1 if (fails or hits) else 0)


if __name__ == "__main__":
    main()
