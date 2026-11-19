"""Build the Capstone Final Review deck on top of the university template.

Run from the repository root (after docs/ppt/make_ppt_figs.py):
    python docs/ppt/build_ppt.py

Input:  docs/ppt/template/Capstone_PPT_Template.pptx (16 slides, 16:9)
Output: docs/ppt/XFed_Capstone_Final_Review.pptx
        docs/ppt/slide_sources.json   (per slide: source files for every number on it)
        docs/ppt/speaker_script.md    (all notes grouped by speaker, timing, demo script)

Every output slide is a clone of one template slide, so the title style, logo,
page-number dot and fonts are the template's own. Page numbers are the template's
slide-number fields, so they run in order by themselves. The original 16 slides are
removed at the end. Numbers are typed exactly as they appear in the source files
named for each slide; docs/ppt/number_check.py verifies them.
"""
import copy
import json
import os
import re

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PPT = os.path.join(ROOT, "docs", "ppt")
FIG = os.path.join(PPT, "figs")
TEMPLATE = os.path.join(PPT, "template", "Capstone_PPT_Template.pptx")
OUT = os.path.join(PPT, "XFed_Capstone_Final_Review.pptx")

# Template colours and fonts (read from the template XML)
MAROON = RGBColor(0x57, 0x23, 0x14)   # slide titles
BLUE = RGBColor(0x38, 0x91, 0xA7)     # square bullets
BLACK = RGBColor(0, 0, 0)
GREY = RGBColor(0x59, 0x59, 0x59)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TINT_M = RGBColor(0xF7, 0xEF, 0xEC)   # light maroon tint for boxes / table rows
TINT_B = RGBColor(0xEA, 0xF3, 0xF6)   # light blue tint
BODY_FONT = "Gill Sans MT"
BULLET_CHAR = ""                # Wingdings square, as in the template

# Template slide indices (0-based)
T_TITLE, T_OUTLINE, T_OVERVIEW, T_PROBLEM, T_OBJ, T_RELATED, T_IMPROVE, T_ARCH, T_MODULES, \
    T_TOOLS, T_DATASET, T_PARAMS, T_RESULTS, T_SUMMARY, T_BIB, T_THANKS = range(16)


# ----------------------------------------------------------------------------- cloning
def clone_slide(prs, src):
    new = prs.slides.add_slide(src.slide_layout)
    for shp in list(new.shapes):
        shp._element.getparent().remove(shp._element)
    rid_map = {}
    for rel in src.part.rels.values():
        if rel.reltype.endswith("/slideLayout") or rel.reltype.endswith("/notesSlide"):
            continue
        if rel.is_external:
            rid_map[rel.rId] = new.part.rels.get_or_add_ext_rel(rel.reltype, rel.target_ref)
        else:
            rid_map[rel.rId] = new.part.rels.get_or_add(rel.reltype, rel._target)
    tree = new.shapes._spTree
    for el in src.shapes._spTree.iterchildren():
        if el.tag in (qn("p:nvGrpSpPr"), qn("p:grpSpPr")):
            continue
        el2 = copy.deepcopy(el)
        for node in el2.iter():
            for attr in list(node.attrib):
                if attr in (qn("r:embed"), qn("r:id"), qn("r:link")) and node.attrib[attr] in rid_map:
                    node.attrib[attr] = rid_map[node.attrib[attr]]
        tree.append(el2)
    return new


def delete_slide(prs, slide):
    lst = prs.slides._sldIdLst
    for sid in list(lst):
        if int(sid.get("id")) == slide.slide_id:
            prs.part.drop_rel(sid.get(qn("r:id")))
            lst.remove(sid)
            return


def shape(slide, name):
    for s in slide.shapes:
        if s.name == name:
            return s
    raise KeyError(name)


def set_title(slide, text):
    """Replace the visible words of the template title, keeping its runs and line breaks."""
    tf = shape(slide, "TextShape 1").text_frame
    runs = [r for p in tf.paragraphs for r in p.runs if r.text.strip()]
    runs[0].text = text
    for r in runs[1:]:
        r.text = ""


def set_heading(slide, text):
    """Keep the template's blue-square sub-heading, drop its empty placeholder lines."""
    sh = shape(slide, "TextShape 2")
    paras = sh.text_frame.paragraphs
    first = paras[0]
    runs = first.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)
    for p in paras[1:]:
        p._p.getparent().remove(p._p)
    sh.height = Inches(0.45)
    return sh.top + Inches(0.45)


# ----------------------------------------------------------------------------- text helpers
def _bullet(p, on, level=0):
    pPr = p._p.get_or_add_pPr()
    for tag in ("a:buNone", "a:buChar", "a:buClr", "a:buFont", "a:buAutoNum"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    if on:
        pPr.set("marL", str(237240 + level * 228600))
        pPr.set("indent", "-237240")
        clr = etree.SubElement(pPr, qn("a:buClr"))
        etree.SubElement(clr, qn("a:srgbClr")).set("val", "3891A7")
        etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Wingdings")
        etree.SubElement(pPr, qn("a:buChar")).set("char", BULLET_CHAR)
    else:
        etree.SubElement(pPr, qn("a:buNone"))


def _run(p, text, size, bold=False, italic=False, color=BLACK, font=BODY_FONT):
    r = p.add_run()
    r.text = text
    f = r.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.name = font
    f.color.rgb = color
    return r


def add_text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, margin=0.05):
    """paras: list of dicts: text | runs[(text, bold)], size, bullet, bold, italic, color, align, space."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{side}", Inches(margin))
    for i, spec in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        size = spec.get("size", 16)
        runs = spec.get("runs") or [(spec["text"], spec.get("bold", False))]
        for text, bold in runs:
            _run(p, text, size, bold=bold, italic=spec.get("italic", False), color=spec.get("color", BLACK))
        _bullet(p, spec.get("bullet", False), spec.get("level", 0))
        p.alignment = spec.get("align", PP_ALIGN.LEFT)
        p.space_before = Pt(spec.get("space", 6 if i else 0))
    return tb


def bullets(items, size=16, space=8):
    out = []
    for it in items:
        runs = it if isinstance(it, list) else [(it, False)]
        out.append({"runs": runs, "size": size, "bullet": True, "space": space})
    return out


def add_table(slide, x, y, w, rows, col_w, size=14, row_h=0.32, header=True, bold_first_col=False,
              align=None, merge=None):
    nr, nc = len(rows), len(rows[0])
    gs = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr))
    tbl = gs.table
    tblPr = tbl._tbl.tblPr
    for attr in ("bandRow", "firstRow"):
        tblPr.set(attr, "0")
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i in range(nr):
        tbl.rows[i].height = Inches(row_h)
        for j in range(nc):
            cell = tbl.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.025)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            is_head = header and i == 0
            cell.fill.solid()
            cell.fill.fore_color.rgb = MAROON if is_head else (TINT_M if i % 2 == 0 else WHITE)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            for r in list(p.runs):
                r._r.getparent().remove(r._r)
            val = rows[i][j]
            _run(p, "" if val is None else str(val), size, bold=is_head or (bold_first_col and j == 0),
                 color=WHITE if is_head else BLACK)
            if align and align[j]:
                p.alignment = align[j]
    for (r0, c0, r1, c1) in (merge or []):
        tbl.cell(r0, c0).merge(tbl.cell(r1, c1))
        p = tbl.cell(r0, c0).text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        for extra in tbl.cell(r0, c0).text_frame.paragraphs[1:]:
            extra._p.getparent().remove(extra._p)
    return gs


def add_picture(slide, path, x, y, w=None, h=None, border=False):
    """Place an image inside the box (x, y, w, h) without stretching it; centred in the box."""
    from PIL import Image
    with Image.open(path) as im:
        pw, ph = im.size
    ar = pw / ph
    if w and h:
        if w / h > ar:
            nw, nh = h * ar, h
        else:
            nw, nh = w, w / ar
        x, y = x + (w - nw) / 2, y + (h - nh) / 2
    elif w:
        nw, nh = w, w / ar
    else:
        nw, nh = h * ar, h
    pic = slide.shapes.add_picture(path, Inches(x), Inches(y), Inches(nw), Inches(nh))
    if border:
        pic.line.color.rgb = MAROON
        pic.line.width = Pt(0.75)
    return pic


def box(slide, x, y, w, h, lines, fill=TINT_M, line=MAROON, size=14, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE,
        bold_first=True, align=PP_ALIGN.CENTER, line_w=1.25):
    s = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape_type == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.12
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    s.line.color.rgb = line
    s.line.width = Pt(line_w)
    s.shadow.inherit = False
    tf = s.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for side in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{side}", Inches(0.05))
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _run(p, ln, size, bold=(bold_first and i == 0), color=MAROON if (bold_first and i == 0) else BLACK)
        p.alignment = align
        _bullet(p, False)
    return s


def arrow(slide, x1, y1, x2, y2, color=BLUE, width=2.0):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    ln = c.line._get_or_add_ln()
    tail = etree.SubElement(ln, qn("a:tailEnd"))
    tail.set("type", "triangle")
    tail.set("w", "med")
    tail.set("len", "med")
    return c


def label(slide, x, y, w, h, text, size=14, color=BLUE, bold=False, italic=True, align=PP_ALIGN.CENTER):
    return add_text(slide, x, y, w, h, [{"text": text, "size": size, "color": color, "bold": bold,
                                          "italic": italic, "align": align}], margin=0.02)


def notes(slide, speaker, speech, question, answer):
    text = f"{speaker}: {speech}\n\nLikely question: {question}\nShort answer: {answer}"
    slide.notes_slide.notes_text_frame.text = text


# ============================================================================= the deck
SLIDES = []   # (template index, builder function, speaker, sources) in final order


def slide(t_index, speaker, sources):
    def deco(fn):
        SLIDES.append((t_index, fn, speaker, sources))
        return fn
    return deco


PI = "PROJECT_INSTRUCTIONS.md"
CA = "docs/contribution_a_results.md"
CB = "docs/contribution_b_results.md"
EFF = "docs/efficiency_results.md"
PRE = "docs/preregistration_accuracy.md"
AUD = "docs/test_set_exposure_audit.md"
DATA = "data/README.md"
PAPER = "paper/main.tex"


# 1 ---------------------------------------------------------------------------- title
@slide(T_TITLE, "Adithya", [PAPER])
def s_title(s):
    tf = shape(s, "TextShape 1").text_frame
    title_run = tf.paragraphs[1].runs[0]
    title_run.text = "XFed-IDS-ByzAgent: Explainable and Trust-Aware Federated Intrusion Detection"
    sup = shape(s, "TextShape 2").text_frame.paragraphs[0].runs
    # runs: "Supervised By:", " ", "Prof. /", "Dr.", " "
    sup[2].text = "Prof. Gargi Madala"
    for r in sup[3:]:
        r.text = ""
    team = shape(s, "CustomShape 3").text_frame
    paras = team.paragraphs
    # paras[0] = "SDP Id:" (left blank to write by hand), paras[1] = "Name of the Student(s) with Regd. No.:"
    names = ["V Naga Adithya (23BCE9062)", "T Shaun (23BCE9916)", "P Sampath (23BCE8614)",
             "D Tharun (23BCE8818)"]
    for p, name in zip(paras[2:6], names):
        _run(p, name, 14)
    for p in paras[6:]:
        p._p.getparent().remove(p._p)
    scope = shape(s, "CustomShape 4").text_frame
    for p in scope.paragraphs:
        for r in p.runs:
            if "Amravati" in r.text:
                r.text = r.text.replace("Amravati", "Amaravati")
    notes(s, "Adithya",
          "Good morning. We are V Naga Adithya, T Shaun, P Sampath and D Tharun, supervised by Prof. Gargi "
          "Madala. Our project is XFed-IDS-ByzAgent: explainable and trust-aware federated intrusion detection. "
          "In one line, it is a federated intrusion detection system that doesn't just detect attacks, but checks "
          "whether its own explanations and its own participants can be trusted. I give the overview and the system "
          "design; Shaun the problem, objectives and data; Tharun related work and the explanation check; Sampath "
          "the trust check, efficiency and our summary. I also run the live demo.",
          "Who built which part?",
          "Each of us presents the part we worked on; the report lists every member's contribution.")


# 2 ---------------------------------------------------------------------------- outline
@slide(T_OUTLINE, "Adithya", [])
def s_outline(s):
    notes(s, "Adithya",
          "This is the university outline, and we follow it in order. First the introduction: the project, the "
          "problem and our objectives. Then related work and how our work differs. Then the proposed solution: "
          "architecture, modules, methods and tools. Then implementation and results: the dataset, the parameters "
          "and the experimental outcomes, where the explanation check and the trust check each get their own "
          "slides, because they are separate experiments. The live demo sits inside the results, at the "
          "dashboard slide. We end with the summary, references and backup slides for questions.",
          "How long is the demo?",
          "About five minutes, at the dashboard slide; the screenshots on that slide are the fallback.")


# 3 ---------------------------------------------------------------------------- overview
def pipeline_row(s, y, h=1.25):
    """Five stages in a row, template colours. Stages 3 and 4 are visibly separate."""
    stages = [("Data", "CICIDS2017 V4", "8 families + Benign"),
              ("Federated training", "10 silos", "Dirichlet α"),
              ("Explanation check", "client-side SHAP", "Jaccard@10, τ"),
              ("Trust check", "ByzAgent vs", "Krum family"),
              ("Dashboard", "alerts, SHAP,", "trust decisions")]
    x, w, gap = 0.3, 1.62, 0.3
    fills = [TINT_M, TINT_B, TINT_M, TINT_B, TINT_M]
    for i, (a, b, c) in enumerate(stages):
        box(s, x + i * (w + gap), y, w, h, [f"{i + 1}  {a}", b, c], fill=fills[i], size=14)
        if i < 4:
            arrow(s, x + i * (w + gap) + w + 0.03, y + h / 2, x + (i + 1) * (w + gap) - 0.03, y + h / 2)


@slide(T_OVERVIEW, "Adithya", [PI])
def s_overview(s):
    top = set_heading(s, "Project Overview")
    add_text(s, 0.5, 1.2, 9.0, 0.9, [{
        "text": "A federated IDS that doesn't just detect attacks, but checks whether its own "
                "explanations and its own participants can be trusted.",
        "size": 20, "italic": True, "color": MAROON, "align": PP_ALIGN.CENTER}])
    pipeline_row(s, 2.35)
    add_text(s, 0.3, 3.85, 8.2, 0.9, bullets([
        "Ten organisations train one detector; traffic never leaves an organisation",
        "Stages 3 and 4 are separate experiments, reported separately",
    ], size=16))
    notes(s, "Adithya",
          "An intrusion detection system learns what attacks look like from labelled network flows. No single "
          "organisation sees every attack, but organisations cannot pool their traffic, because flow records "
          "describe internal hosts, users and services. Federated learning lets ten organisations, which we call "
          "silos, train one shared detector while their traffic stays at home. Our system has five stages: data, "
          "federated training, an explanation check, a trust check, and a dashboard. Stages three and four are "
          "separate experiments with separate evidence, and we report them separately throughout. Shaun now sets "
          "out the problem.",
          "Why not just share anonymised traffic?",
          "Flow records still reveal internal hosts and services; in federated learning only weights and small "
          "summaries leave a silo.")


# 4 ---------------------------------------------------------------------------- problem
@slide(T_PROBLEM, "Shaun", [PAPER])
def s_problem(s):
    set_heading(s, "Problem Statement & Motivations")
    add_text(s, 0.3, 1.2, 9.2, 1.6, bullets([
        "Organisations cannot pool flow records: hosts, users, contracts",
        "Federated learning shares model weights, not traffic",
        "Most federated IDS studies stop at detection accuracy",
    ], size=18))
    box(s, 0.5, 3.0, 4.2, 1.45, ["Do the participants agree on why?",
                                 "Same attack, same features, in every silo's model?"],
        fill=TINT_M, size=16)
    box(s, 5.1, 3.0, 4.2, 1.45, ["Is anyone poisoning the model?",
                                 "The server sees only weights; a silo can relabel its data"],
        fill=TINT_B, line=BLUE, size=16)
    notes(s, "Shaun",
          "Thank you, Adithya. Most federated IDS papers stop at accuracy. We think two more questions matter to anyone who would run "
          "one. First, do the participants' models detect attacks for the same reasons? An analyst reads an "
          "explanation, and if each silo's model relies on different features, that explanation depends on whose "
          "model was asked. Second, is anyone poisoning the shared model? The server only sees weight updates, so "
          "a silo that relabels its own data can bend the model, and an honest silo with unusual traffic can look "
          "suspicious too. Those two questions are our two checks.",
          "Why would explanations differ if accuracy is the same?",
          "Each silo trains on its own skewed slice of traffic; the same accuracy can rest on different features, "
          "and that is what we measure.")


# 5 ---------------------------------------------------------------------------- objectives
@slide(T_OBJ, "Shaun", [PI])
def s_objectives(s):
    set_heading(s, "Objectives & Expected Impact")
    add_text(s, 0.3, 1.15, 4.6, 0.4, [{"text": "Objectives", "size": 18, "bold": True, "color": MAROON}])
    add_text(s, 0.3, 1.6, 4.6, 3.0, bullets([
        "Train one federated detector across ten silos, three skew levels",
        "Measure silo-vs-global explanation agreement against a seed-noise floor",
        "Test whether a local LLM agent flags poisoned silos",
    ], size=18, space=14))
    add_text(s, 5.2, 1.15, 4.4, 0.4, [{"text": "Expected impact", "size": 18, "bold": True, "color": MAROON}])
    add_text(s, 5.2, 1.6, 4.4, 3.0, bullets([
        "Analysts learn when federated explanations can be trusted",
        "An auditable protocol: validation selection, one preregistered test read",
    ], size=18, space=14))
    notes(s, "Shaun",
          "We set three objectives. One: train a federated detector across ten silos at three levels of label "
          "skew. Two: measure how far each silo's explanations agree with the global model, against a seed-noise "
          "floor, so that a difference can be told apart from randomness. Three: test whether a local LLM agent can "
          "flag poisoned silos, compared with classical robust rules. The impact is practical. An analyst learns "
          "when federated explanations can be trusted, and the evaluation is auditable, with every model chosen "
          "on validation data. Tharun will now place this against related work.",
          "Is the LLM agent meant to replace Krum?",
          "No. We compare it with Krum, Multi-Krum and trimmed mean and report where each one fails.")


# 6 ---------------------------------------------------------------------------- related work
@slide(T_RELATED, "Tharun", [PAPER, "paper/refs.bib"])
def s_related(s):
    set_heading(s, "Related Work & Their Limitations")
    Y = "✓"
    rows = [["Work", "FL", "IDS", "XAI", "Cons.", "Seed", "Byz.", "LLM"],
            ["DÏoT (2019)", Y, Y, "", "", "", "", ""],
            ["Nguyen et al. (2020)", Y, Y, "", "", "", Y, ""],
            ["FLTrust (2021)", Y, "", "", "", "", Y, ""],
            ["FEDFOREST (2022)", Y, Y, Y, "", "", "", ""],
            ["Oki et al. (2024)", Y, Y, Y, Y, "", "", ""],
            ["Bilal et al. (2025)", Y, Y, Y, "", "", "", ""],
            ["Watson et al. (2022)", "", "", Y, Y, Y, "", ""],
            ["PentestGPT (2024)", "", "", "", "", "", "", Y],
            ["This work", Y, Y, Y, Y, Y, Y, Y]]
    C = PP_ALIGN.CENTER
    t = add_table(s, 0.3, 1.15, 5.85, rows, [1.92] + [0.5614] * 7, size=12, row_h=0.3, bold_first_col=False,
                  align=[None] + [C] * 7)
    for j in range(8):
        t.table.cell(len(rows) - 1, j).text_frame.paragraphs[0].runs[0].font.bold = True
    add_text(s, 0.3, 4.3, 5.85, 0.5, [{"text": "Compact form of Table I in our paper. Cons. = explanation-consistency "
                                              "metric; Seed = seed-noise control; Byz. = Byzantine defence.",
                                      "size": 14, "italic": True, "color": GREY}])
    add_text(s, 6.3, 1.15, 3.4, 0.4, [{"text": "What prior work leaves open", "size": 16, "bold": True,
                                        "color": MAROON}])
    add_text(s, 6.3, 1.6, 3.4, 3.2, bullets([
        "Oki et al.: FL pulls explanations together; how far under skew?",
        "Gholizade et al.: no standard metric for federated explanation consistency",
        "No seed-noise reference in federated IDS agreement numbers",
        "Robust rules assume honest clients look alike",
    ], size=14, space=8))
    notes(s, "Tharun",
          "Thank you, Shaun. This table is a compact version of Table I in our paper. Several systems already combine federated "
          "learning, intrusion detection and explanations, such as FEDFOREST and Bilal et al., so we do not claim "
          "that combination. Oki et al. are the closest: they showed that federated training pulls explanations "
          "closer to a centralized model. The survey by Gholizade et al. lists explanation consistency under "
          "non-IID data as an open challenge with no agreed metric. What stays open is how far Oki's result holds "
          "as skew grows, how much seeds alone move rankings, and whether robust rules cope with honest but "
          "unusual silos.",
          "Which paper is closest to yours?",
          "Oki et al. (IEEE Networking Letters, 2024); we extend their question across label skew and add a "
          "seed-noise reference.")


# 7 ---------------------------------------------------------------------------- improvements
@slide(T_IMPROVE, "Tharun", [PI])
def s_improve(s):
    set_heading(s, "Improvements over Existing Solutions")
    add_text(s, 0.3, 1.25, 9.2, 3.4, bullets([
        "Builds on Oki et al.: where convergence breaks down as skew grows",
        "Adds a null control: centralized models differing only by seed",
        "Tests Krum and its variants with 10 clients and an oracle attacker count",
        "Audits how often the agent's own explanations are accurate",
        "Not claimed: the FL + IDS + XAI combination itself",
    ], size=18, space=14))
    notes(s, "Tharun",
          "Here is how our work differs, stated carefully. We build on Oki et al. and characterise where their "
          "reduction in explanation distance breaks down as client data becomes more heterogeneous. We add a null "
          "control: centralized models that differ only by random seed, so a federated gap can be compared with "
          "seed noise. In the trust check we test the Krum family with ten clients and hand it the true attacker "
          "count. And we audit how often our agent's written reasons match the numbers it was shown. We do not "
          "claim the combination of federated learning, IDS and explainability. Adithya now shows the "
          "architecture.",
          "Isn't a seed control standard practice?",
          "Watson et al. showed seeds change explanations; we did not find a seed reference reported in the "
          "federated IDS papers we read.")


# 8 ---------------------------------------------------------------------------- architecture
@slide(T_ARCH, "Adithya", [PI, PAPER])
def s_arch(s):
    set_heading(s, "System Architecture / Data Flow")
    # stage 1
    box(s, 0.25, 2.1, 1.4, 1.6, ["1  Data", "CICIDS2017 V4", "cleaned once,", "split once"], size=14)
    arrow(s, 1.67, 2.9, 1.98, 2.9)
    # stage 2: the silos
    box(s, 2.0, 1.12, 2.4, 3.55, [""], fill=TINT_B, line=BLUE, bold_first=False)
    label(s, 2.05, 1.15, 2.3, 0.35, "2  Ten silos", size=14, color=MAROON, bold=True, italic=False)
    for i, name in enumerate(["Silo 1", "Silo 2", "Silo 10"]):
        yy = 1.55 + i * 0.92 if i < 2 else 3.75
        box(s, 2.12, yy, 2.16, 0.78, [name, "train MLP · run SHAP"], fill=WHITE, line=BLUE, size=14)
    label(s, 2.12, 3.27, 2.16, 0.42, "⋮", size=18, color=BLUE, italic=False)
    # server
    box(s, 5.6, 1.12, 1.95, 1.0, ["Server", "FedAvg · best round", "on validation"], size=14)
    arrow(s, 4.42, 1.42, 5.58, 1.42)
    label(s, 4.42, 1.08, 1.16, 0.33, "weights", size=14)
    arrow(s, 5.58, 1.86, 4.42, 1.86, color=MAROON)
    label(s, 4.42, 1.87, 1.16, 0.33, "global model", size=14, color=MAROON)
    # stage 3
    box(s, 5.6, 2.42, 1.95, 1.1, ["3  Explanation check", "Jaccard@10,", "weighted τ"], size=14)
    arrow(s, 4.42, 2.97, 5.58, 2.97)
    label(s, 4.42, 2.62, 1.16, 0.33, "top-k only", size=14)
    # stage 4
    box(s, 5.6, 3.72, 1.95, 1.0, ["4  Trust check", "ByzAgent vs", "Krum family"], fill=TINT_B, line=BLUE,
        size=14)
    arrow(s, 4.42, 4.22, 5.58, 4.22)
    label(s, 4.42, 3.87, 1.16, 0.33, "statistics", size=14)
    # stage 5
    box(s, 7.95, 1.12, 1.75, 3.0, ["5  Dashboard", "FastAPI + React", "live alerts", "SHAP", "trust decisions",
                                  "hot-swap"], size=14)
    arrow(s, 7.57, 1.62, 7.93, 1.62)
    arrow(s, 7.57, 2.97, 7.93, 2.97)
    arrow(s, 7.57, 3.98, 7.93, 3.78)
    add_text(s, 0.25, 4.8, 8.2, 0.35, [{
        "runs": [("Stays in a silo: ", True), ("raw flows, SHAP values.   ", False),
                 ("Leaves: ", True), ("weights, top-k indices, statistics.", False)],
        "size": 14}])
    notes(s, "Adithya",
          "Thanks, Tharun. This is the architecture. The data is cleaned once and split once, then spread over ten silos. Each "
          "silo trains the shared MLP locally and sends only weights to the server, which averages them with "
          "FedAvg and keeps the round that is best on validation. For the explanation check, each silo runs SHAP "
          "on its own copy and sends only its top-k feature indices; no raw flows and no SHAP values leave a "
          "silo. For the trust check, the server logs five statistics per silo per round. The dashboard serves "
          "the selected model, its explanations and the trust decisions.",
          "What exactly crosses the client-to-server boundary?",
          "Model weights, top-k feature indices and the per-silo statistics; never raw flows or SHAP magnitudes.")


# 9 ---------------------------------------------------------------------------- modules
@slide(T_MODULES, "Adithya", [PI])
def s_modules(s):
    set_heading(s, "Key Components / Features & Modules")
    rows = [["Module", "What it does", "Code"],
            ["Data", "Cleans CICIDS2017 V4; hash-checked silo partitions", "src/, configs/data.yaml"],
            ["Federated training", "Flower harness; 10 silos; best round on validation",
             "federated/xfed_federated/"],
            ["Explanation check", "Client-side SHAP; top-k agreement vs global model", "tools/, results/shap/"],
            ["Trust check (ByzAgent)", "Attack, statistics, Krum baselines, LLM agent",
             "src/attacks/, src/agents/"],
            ["Dashboard", "Live alerts, SHAP, trust panel, gated hot-swap", "backend/, frontend/"]]
    add_table(s, 0.3, 1.25, 9.3, rows, [2.25, 4.6, 2.45], size=14, row_h=0.5, bold_first_col=True)
    add_text(s, 0.3, 4.4, 8.2, 0.4, [{"text": "Every parameter lives in a YAML file under configs/; nothing is "
                                              "hard-coded.", "size": 14, "italic": True, "color": GREY}])
    notes(s, "Adithya",
          "Five modules, one per stage. The data module cleans the corrected CICIDS2017 flows and writes the silo "
          "partitions with a hash manifest that is checked every time they load. Federated training is a Flower "
          "harness. The explanation check computes client-side SHAP and the agreement metrics. The trust check "
          "holds the attack, the statistics logger, the classical baselines and ByzAgent. The dashboard is a "
          "FastAPI backend with a React front end, including a model hot-swap that only goes live if it passes a "
          "validation gate.",
          "Can someone else reproduce a run?",
          "Yes: partitions are hash-checked at load, seeds are fixed, and every parameter is in a YAML config.")


# 10 --------------------------------------------------------------------------- algorithms & tools
@slide(T_TOOLS, "Adithya", [PAPER, "docs/env_versions_2026-11-18.txt", "requirements.txt",
                            "federated/pyproject.toml", "frontend/package-lock.json", PI])
def s_tools(s):
    set_heading(s, "Algorithms Used / Technologies, Frameworks, and Tools Used")
    rows = [["Method", "Role"],
            ["FedAvg · FedProx · FedAvgM", "aggregate silo weights"],
            ["SHAP GradientExplainer", "per-silo feature attributions"],
            ["Jaccard@10 · weighted Kendall's τ", "compare top-10 sets · full rankings"],
            ["Krum · Multi-Krum · trimmed mean", "classical robust baselines"],
            ["ByzAgent (local LLM agent)", "trust / downweight / quarantine"]]
    add_table(s, 0.3, 1.2, 5.3, rows, [2.75, 2.55], size=13, row_h=0.52, bold_first_col=True)
    tools = [["Tool", "Version"],
             ["Python", "3.11.15"],
             ["PyTorch (FL, CPU)", "2.13.0"],
             ["PyTorch (GPU)", "2.6.0+cu124"],
             ["Flower", "1.33.0"],
             ["SHAP", "0.51.0"],
             ["XGBoost", "3.2.0"],
             ["ONNX Runtime", "1.31.0"],
             ["FastAPI", "0.138.2"],
             ["Ollama", "0.40.16"],
             ["React", "19.2.8"]]
    add_table(s, 5.85, 1.2, 3.75, tools, [2.1, 1.65], size=12, row_h=0.3, bold_first_col=False)
    add_text(s, 0.3, 4.45, 5.3, 0.4, [{"text": "Agent model: llama3.1:8b-instruct-q4_K_M via Ollama",
                                       "size": 14, "italic": True, "color": GREY}])
    notes(s, "Adithya",
          "On the method side: FedAvg as the default aggregator, FedProx with a small proximal term, and FedAvgM "
          "with server momentum, which we tested in a preregistered comparison. SHAP's GradientExplainer, because "
          "DeepExplainer fails on LayerNorm. Jaccard at ten compares top-ten feature sets; weighted Kendall's tau "
          "compares whole rankings with more weight at the top. Krum, Multi-Krum and trimmed mean are the "
          "classical baselines, and ByzAgent is Llama 3.1 run locally through Ollama. The versions are the ones "
          "we ran. Shaun will now describe the data.",
          "Why run the LLM locally instead of a cloud API?",
          "Sending silo statistics to a cloud API would undercut the privacy premise; local also fixes the model "
          "version and costs nothing.")


# 11a -------------------------------------------------------------------------- dataset
@slide(T_DATASET, "Shaun", [DATA, EFF, PI])
def s_dataset(s):
    set_heading(s, "Dataset Description: Distrinet CICIDS2017 V4")
    clean = [["Cleaning step", "Rows"],
             ["Raw flows (5 capture days)", "2,099,976"],
             ["Non-finite values", "−5"],
             ["Same features, different family", "−44,005"],
             ["Cross-day duplicates", "−142,464"],
             ["Retained", "1,913,502"],
             ["Train / test (group-aware)", "1,435,126 / 478,376"],
             ["Validation (from train pool)", "143,513"]]
    R = PP_ALIGN.RIGHT
    add_table(s, 0.3, 1.2, 5.0, clean, [3.05, 1.95], size=13, row_h=0.36, align=[None, R])
    fam = [["Family", "Flows"],
           ["Benign", "1,440,899"], ["PortScan", "186,160"], ["DoS", "177,491"], ["DDoS", "95,144"],
           ["BruteForce", "6,972"], ["Bot", "4,703"], ["WebAttack", "2,056"],
           ["Infiltration *", "66"], ["Heartbleed *", "11"]]
    add_table(s, 5.65, 1.2, 3.95, fam, [2.25, 1.7], size=12, row_h=0.3, align=[None, R])
    add_text(s, 5.65, 4.22, 3.95, 0.4, [{"text": "* below the 1,000-flow floor: per class only",
                                         "size": 14, "italic": True, "color": GREY}])
    add_text(s, 0.3, 4.2, 5.1, 0.6, bullets(["82 numeric features; 8 attack families + Benign"], size=16))
    notes(s, "Shaun",
          "Thank you. We use the Distrinet release of CICIDS2017, version 4, from Liu et al., which builds on "
          "Engelen et al.'s corrections of the original dataset. The raw files hold 2,099,976 flows. We removed 5 "
          "rows with non-finite values, 44,005 rows whose identical features carry different families, and "
          "142,464 duplicates that span capture days, keeping 1,913,502 flows in eight attack families plus "
          "Benign. The split is group-aware, so identical feature vectors never sit on both sides of train and "
          "test. Infiltration and Heartbleed fall under the 1,000-flow floor, so they are reported per class only.",
          "Why not the original CICIDS2017?",
          "It has documented labelling and flow-construction errors; Engelen et al. and Liu et al. corrected "
          "them, and version 4 is that corrected release.")


# 11b -------------------------------------------------------------------------- partitioning
@slide(T_DATASET, "Shaun", [PI, DATA, "results/partition_check.json", "docs/ppt/figs/alpha_silo_counts.csv"])
def s_partition(s):
    set_heading(s, "Input Description: Ten Silos with Dirichlet α")
    add_text(s, 0.3, 1.1, 9.2, 0.4, bullets([
        "Each family split over 10 silos by Dir(α); seeds 42, 1337, 2024"], size=16))
    add_picture(s, os.path.join(FIG, "fig_alpha_silos.png"), 0.6, 1.55, w=8.0, h=3.15)
    notes(s, "Shaun",
          "To simulate ten organisations, we split the training pool with a Dirichlet distribution, family by "
          "family, and alpha is the slider. At alpha 0.1, on the left, a family usually lands almost whole in "
          "one silo, and silo sizes range from 143 to 636,676 rows. At alpha 5.0, on the right, every silo looks "
          "much like the whole dataset; this is our near-IID control. Alpha 0.5 sits in between. Each alpha uses "
          "three seeds, 42, 1337 and 2024, giving nine partitions, stored on disk with a SHA256 manifest that is "
          "checked at load.",
          "Why include alpha 5.0 at all?",
          "It separates 'federation costs accuracy' from 'non-IID data costs accuracy', which are different "
          "claims.")


# 12 --------------------------------------------------------------------------- parameters
@slide(T_PARAMS, "Shaun", [PI, "configs/model.yaml", "configs/agent.yaml", "docs/measurement_protocol.md", PRE])
def s_params(s):
    set_heading(s, "Parameters Descriptions")
    left = [["Setting", "Value"],
            ["Scaler", "StandardScaler (per silo)"],
            ["Class weights", "effective-number, β = 0.999"],
            ["MLP", "[128, 64], dropout 0.1"],
            ["Normalisation", "LayerNorm"],
            ["Optimizer (local)", "AdamW, lr 1.0e-3, wd 1.0e-4"],
            ["Batch size", "1024"],
            ["Local epochs / rounds", "3 / 20"],
            ["Round kept", "best on validation"]]
    right = [["Setting", "Value"],
             ["Silos", "10, all train every round"],
             ["Dirichlet α", "0.1, 0.5, 5.0"],
             ["Seeds", "42, 1337, 2024"],
             ["FedProx μ", "0.0005"],
             ["FedAvgM momentum β", "0.9"],
             ["Top-k (Jaccard)", "k = 10"],
             ["SHAP background / samples", "200 rows / 4000"],
             ["Agent model, temperature", "llama3.1:8b (4-bit), 0.2"]]
    add_table(s, 0.3, 1.2, 4.55, left, [1.85, 2.7], size=12, row_h=0.37, bold_first_col=True)
    add_table(s, 5.05, 1.2, 4.6, right, [2.05, 2.55], size=12, row_h=0.37, bold_first_col=True)
    notes(s, "Shaun",
          "These are the locked settings. StandardScaler, because RobustScaler degenerates on 28 of 82 features "
          "whose interquartile range is zero. Effective-number class weights with beta 0.999, for the class "
          "imbalance. A small MLP of 128 and 64 units with dropout 0.1 and LayerNorm, because BatchNorm statistics "
          "do not aggregate across silos. Three local epochs, twenty rounds, and we keep the round that is best "
          "on validation. The agent runs at temperature 0.2. Adithya will now show the accuracy results.",
          "Why LayerNorm and not BatchNorm?",
          "BatchNorm keeps running statistics of each silo's data, and averaging those is meaningless; LayerNorm "
          "has no such state.")


# 13a -------------------------------------------------------------------------- accuracy
def results_slide(heading):
    def deco(fn):
        def wrapped(s):
            set_heading(s, "Experimental Outcomes: " + heading)
            fn(s)
        wrapped.__name__ = fn.__name__
        return wrapped
    return deco


@slide(T_RESULTS, "Adithya", [PI, DATA, PRE])
@results_slide("Detection Accuracy (test macro-F1)")
def s_accuracy(s):
    rows = [["Model", "α = 0.1", "α = 0.5", "α = 5.0"],
            ["Centralized MLP", "0.9900 ± 0.0022", "", ""],
            ["XGBoost", "0.9946 ± 0.0001", "", ""],
            ["FedAvg", "0.516 ± 0.048", "0.941 ± 0.057", "0.990 ± 0.001"],
            ["FedAvgM β=0.9 (preregistered, test once)", "0.5930 ± 0.0632", "0.9852 ± 0.0005",
             "0.9911 ± 0.0005"]]
    C = PP_ALIGN.CENTER
    add_table(s, 0.3, 1.2, 9.3, rows, [3.6, 1.9, 1.9, 1.9], size=14, row_h=0.42, bold_first_col=True,
              align=[None, C, C, C], merge=[(1, 1, 1, 3), (2, 1, 2, 3)])
    add_text(s, 0.3, 3.45, 9.3, 1.3, bullets([
        "Macro-F1, not accuracy: Benign is 75% of all flows",
        "α=5.0 matches centralized; the drop comes from non-IID data",
        "Served demo model: fedavg_a0.5_s42, round 18, val macro-F1 0.9760",
    ], size=16, space=6))
    notes(s, "Adithya",
          "Detection first. We report macro-F1, not accuracy, because Benign is 75% of the flows, so a model that "
          "always says Benign would look good on accuracy. At alpha 5.0, FedAvg matches the centralized MLP. At "
          "0.5 it drops a little, with one weak seed, and at 0.1 whole families collapse. So the drop comes from "
          "non-IID data, not from federation itself. FedAvgM with server momentum 0.9 was chosen on validation "
          "alone, then its nine sealed checkpoints were scored on the test set once. It stabilises alpha 0.5, but "
          "alpha 0.1 stays far below centralized. Tharun will now ask whether these models agree on why.",
          "Is FedAvgM your headline model?",
          "No. The explanation and trust results use the published FedAvg runs; FedAvgM is our one preregistered "
          "test evaluation.")


# 13b -------------------------------------------------------------------------- explanation check
@slide(T_RESULTS, "Tharun", [PI, CA, "results/inspection/centralized_instability_floor.csv"])
@results_slide("Explanation Check: Agreement vs α")
def s_expl(s):
    add_picture(s, os.path.join(FIG, "fig_agreement_alpha.png"), 0.25, 1.15, w=5.75, h=3.3)
    add_text(s, 6.15, 1.15, 3.55, 3.6, bullets([
        "Jaccard@10: 0.333 → 0.538 → 0.667",
        "Weighted τ: 0.592 → 0.787 → 0.844",
        "Chance 0.065: every α is 5.1×–10.3× chance",
        "Seed-noise floor: median 0.429, range [0.429, 0.484]",
        "α=0.1 below the floor: directional, not significant",
    ], size=14, space=9))
    add_text(s, 0.3, 4.5, 5.7, 0.35, [{"text": "Hatched band: seed-noise floor · dashed line: chance",
                                       "size": 14, "italic": True, "color": GREY}])
    notes(s, "Tharun",
          "Thank you. Each silo explains the same 14 rows with SHAP on its own model, and we compare its top ten "
          "features with the global model's. Median Jaccard at ten rises from 0.333 at alpha 0.1 to 0.538 and "
          "0.667, and weighted tau from 0.592 to 0.844. Every level is 5.1 to 10.3 times chance. The real "
          "yardstick is the hatched band: centralized models that differ only by seed agree at 0.429. At alpha 0.1 "
          "we fall below that floor while accuracy is still 0.516. The bootstrap interval overlaps the floor, so "
          "this is directional, not significant.",
          "Is 0.333 versus 0.429 significant?",
          "No. The cluster-bootstrap interval [0.250, 0.429] overlaps the floor range [0.429, 0.484]; we call it "
          "directional, not significant.")


# 13c -------------------------------------------------------------------------- explanation robustness
@slide(T_RESULTS, "Tharun", [PI, CA, "results/inspection/residual_sensitivity.json"])
@results_slide("Explanation Check: Robustness")
def s_expl_rob(s):
    add_picture(s, os.path.join(FIG, "fig_kl_scatter.png"), 0.25, 1.15, w=5.4, h=2.45)
    rows = [["α=0.1 headline", "All silos", "Flagged silos excluded"],
            ["Jaccard@10", "0.333", "0.333"],
            ["Weighted τ", "0.592", "0.597"]]
    C = PP_ALIGN.CENTER
    add_table(s, 0.3, 3.75, 5.35, rows, [1.85, 1.4, 2.1], size=13, row_h=0.32, bold_first_col=True,
              align=[None, C, C])
    add_text(s, 5.85, 1.15, 3.8, 3.6, bullets([
        "Silo size and skew are tied under Dirichlet partitioning",
        "Entropy tried first: failed after conditioning on log(size)",
        "KL still predicts agreement: partial r = −0.57 (α=0.1, n=29)",
        "At α=0.5: r = −0.82 / −0.87 (n=30); r and n only",
        "SHAP residual check: α=0.1 result unchanged",
    ], size=14, space=9))
    notes(s, "Tharun",
          "Two robustness checks. First, silo size and skew are tied under Dirichlet partitioning, so small silos "
          "are also skewed ones. We planned label entropy as the skew measure; after conditioning on log size it "
          "failed and its sign flipped. We then tried KL divergence from the global label mix, and it still "
          "predicts agreement: partial r of minus 0.57 at alpha 0.1, and minus 0.82 and minus 0.87 at alpha 0.5. "
          "We report r and n only, because silos in one run are not independent. Second, excluding silos with "
          "large SHAP residuals, by a pre-specified rule, leaves alpha 0.1 at 0.333. Sampath now takes the trust "
          "check, a separate experiment.",
          "Isn't switching from entropy to KL p-hacking?",
          "We state the order: entropy was planned and failed, KL came afterwards, so the result is "
          "observational.")


# 13d -------------------------------------------------------------------------- trust check: signals, baselines
@slide(T_RESULTS, "Sampath", [PI, CB, PAPER])
@results_slide("Trust Check: Signals, Baselines")
def s_trust1(s):
    add_text(s, 0.3, 1.1, 9.3, 1.75, bullets([
        "Worst-case attack: 3 silos relabel 40% of attack rows as Benign",
        "Multi-Krum excluded a malicious silo 0% of the time (chance 0.30)",
        "Classical Krum keeps 1 of 10 updates: its exclusions are chance-level",
        "Baselines got the true attacker count; ByzAgent did not",
    ], size=16, space=6))
    sig = [["Statistic", "Separates attackers?"],
           ["train_loss", "strong: 33.8×–154.3× (seed 42)"],
           ["update norm, two cosines", "weak to null"],
           ["val_accuracy", "inverts: attackers look better"]]
    add_table(s, 0.3, 3.0, 5.2, sig, [2.25, 2.95], size=13, row_h=0.4, bold_first_col=True)
    cost = [["No attack: defence cost", "Test macro-F1"],
            ["Krum", "−22.7 pp"],
            ["Multi-Krum", "−4.9 pp"],
            ["Trimmed mean", "−1.6 pp"]]
    add_table(s, 5.75, 3.0, 3.85, cost, [2.35, 1.5], size=13, row_h=0.4, bold_first_col=True,
              align=[None, PP_ALIGN.CENTER])
    notes(s, "Sampath",
          "Thank you. The trust check is a separate experiment. At alpha 0.5, three silos relabel 40% of their "
          "attack rows as Benign. The attackers were chosen with full knowledge of every silo's label mix, so this "
          "is a worst-case attack, not a model of an ordinary adversary. Of five statistics, only training loss "
          "separates attackers; the geometric ones are weak, and validation accuracy points the wrong way. The "
          "classical rules did not find the attackers: Multi-Krum excluded a malicious silo 0% of the time, "
          "against a chance rate of 0.30, even with the true attacker count. And defending costs accuracy when "
          "nobody attacks.",
          "Why did Krum fail?",
          "Under non-IID data, honest silos with unusual traffic also stand out; Multi-Krum excluded the same "
          "large Benign-heavy silos every round.")


# 13e -------------------------------------------------------------------------- trust check: ByzAgent
@slide(T_RESULTS, "Sampath", [PI, CB, "configs/agent.yaml"])
@results_slide("Trust Check: ByzAgent")
def s_trust2(s):
    add_picture(s, os.path.join(FIG, "fig_byzagent_lift.png"), 0.2, 1.1, w=5.3, h=2.75)
    q = box(s, 5.6, 1.15, 4.1, 2.65, [
        "“Both effects are present. A real compositional confound saturates some silos' flag rates "
        "independent of any attack; real attack-responsive detection is also present and becomes visible where "
        "silos are not already saturated. Seed 42's apparent null was partly a ceiling artifact of that seed's "
        "unusually bimodal composition.”"], fill=TINT_M, size=14, bold_first=False, align=PP_ALIGN.LEFT)
    for p in q.text_frame.paragraphs:
        for r in p.runs:
            r.font.italic = True
    add_text(s, 0.3, 3.92, 8.2, 0.95, bullets([
        "Produces decisions plus a rationale of measured fidelity",
        "Citation error 11.7% (seed 42) → 22.5% (seeds 1337, 2024)",
        "Decision stability: 27/30 exact repeats; 30/30 on trust vs flagged",
    ], size=15, space=4))
    notes(s, "Sampath",
          "ByzAgent is a local Llama 3.1 model. Each round it reads the five statistics for all ten silos and "
          "answers trust, downweight or quarantine for each one; it is never told the attacker count. The figure "
          "shows each malicious silo's flag rate in a clean run, open marker, and under attack, filled. Our locked "
          "conclusion is on the right; I'll read it. [Read the quote.] We describe the agent as producing "
          "decisions plus a rationale of measured fidelity: its citation error rose from 11.7% to 22.5% at the "
          "other seeds. Repeat calls agreed exactly 27 of 30 times. I'll continue with efficiency.",
          "So does ByzAgent detect attacks?",
          "Partly: attack-responsive flags appear where silos are not already saturated by composition, as the "
          "locked claim says.")


# 13f -------------------------------------------------------------------------- efficiency
@slide(T_RESULTS, "Sampath", [PI, EFF, PAPER])
@results_slide("Efficiency")
def s_eff(s):
    rows = [["Quantity (CPU, one laptop)", "Value"],
            ["Latency p50 per flow, ONNX fp32 / PyTorch", "45.7 / 186.5 µs"],
            ["Throughput at batch 1024, ONNX fp32 / PyTorch", "1,071,700 / 1,482,368 rows/s"],
            ["Bytes per round (10 silos, fp32, up + down)", "1,587,920 (793,960 each way)"],
            ["Uplink saving, fp16 / int8 updates", "50.0% / 74.9%"],
            ["Best-validation change, fp16 / int8 (3 seeds)", "−0.0007 / −0.0011"]]
    add_table(s, 0.3, 1.2, 9.3, rows, [5.3, 4.0], size=14, row_h=0.4, bold_first_col=False)
    add_text(s, 0.3, 3.75, 9.2, 1.1, bullets([
        "ONNX fp32 is the default: identical predictions on 143,513 validation rows",
        "Compression: no detectable effect at n=3; int8 serving dropped",
    ], size=16, space=6))
    notes(s, "Sampath",
          "Next, serving and communication, measured on one laptop CPU. ONNX Runtime in fp32 gives "
          "identical predictions to PyTorch on all 143,513 validation rows and cuts per-flow latency from 186.5 to "
          "45.7 microseconds, so it is our default. At batch 1024, PyTorch has the higher throughput, and we say "
          "so. A round moves 1,587,920 bytes for ten silos. Compressing updates saves 50.0% or 74.9% of upload, "
          "with no detectable effect at three seeds. int8 quantization for serving was dropped because validation "
          "macro-F1 fell by 0.1428. Adithya will now show the live dashboard.",
          "Why not int8 for serving?",
          "Validation macro-F1 fell by 0.1428, with the losses in the small classes, so we kept fp32.")


# 13g -------------------------------------------------------------------------- dashboard + demo
@slide(T_RESULTS, "Adithya", [])
@results_slide("Dashboard (live demo)")
def s_dash(s):
    y_cap, y_img, h = 1.08, 1.45, 3.28
    items = [("dash_live_alert.png", "Live alert + SHAP"), ("dash_trust.png", "Trust panel"),
             ("dash_hotswap_gate.png", "Hot-swap gate")]
    from PIL import Image
    widths = []
    for f, _ in items:
        with Image.open(os.path.join(FIG, f)) as im:
            widths.append(h * im.size[0] / im.size[1])
    gap = (9.3 - sum(widths)) / 2
    x = 0.3
    for (f, cap), w in zip(items, widths):
        label(s, x, y_cap, w, 0.35, cap, size=14, color=MAROON, bold=True, italic=False)
        add_picture(s, os.path.join(FIG, f), x, y_img, w=w, h=h, border=True)
        x += w + gap
    add_text(s, 0.3, 4.8, 8.2, 0.35, [{"text": "Replays validation rows only · LLM summaries are a usability "
                                              "feature, not a research claim", "size": 14, "italic": True,
                                      "color": GREY}])
    notes(s, "Adithya",
          "Thanks, Sampath. Now the live dashboard; I'll switch to the browser for about five minutes and follow the demo script. "
          "These three screenshots are the fallback if the demo fails. Left: a live alert with its SHAP "
          "contributions and an LLM summary labelled 'not a research result'; those sentences are a usability "
          "feature, not a research claim. Middle: the trust panel, clean run against attack run for each "
          "organisation. Right: the hot-swap gate, which retrains from the base model and replaces the served "
          "model only if it is at least as good on validation. The stream replays validation rows, never test "
          "rows. Sampath will then cover what we checked and what failed.",
          "Is the dashboard showing test data?",
          "No. It replays validation rows; only the key-figure row shows the preregistered test number, scored "
          "once.")


# 13h -------------------------------------------------------------------------- honesty
@slide(T_RESULTS, "Sampath", [PI, AUD, "paper/number_check.md", "docs/report/number_check.md",
                              "paper/citation_check.md", "paper/overlap_check.md", EFF, CB])
@results_slide("What We Checked, and What Failed")
def s_honesty(s):
    rows = [["Test set", "Negative results", "Checks we ran"],
            ["Every model and round chosen on validation", "Rolling history failed its preregistered test",
             "Paper: 2,279 of 2,279 numbers matched"],
            ["Three early choices cited test; validation picks the same", "Pre-screen threshold did not "
             "transfer across seeds", "Report: 4,038 of 4,038 numbers matched"],
            ["Since 2026-10-12: one preregistered test read", "int8 serving dropped (−0.1428 val macro-F1)",
             "58 references verified; overlap: 0 counted"]]
    add_table(s, 0.3, 1.2, 9.3, rows, [3.1, 3.1, 3.1], size=14, row_h=0.78)
    add_text(s, 0.3, 4.45, 8.2, 0.4, [{"text": "Full list of test-set reads: docs/test_set_exposure_audit.md",
                                       "size": 14, "italic": True, "color": GREY}])
    notes(s, "Sampath",
          "Thanks, Adithya. We want to be clear about the test set. Every model and round was chosen on validation. Three early "
          "choices were first justified with test numbers; re-checked on validation, the same values win, and we "
          "disclose it. Since 12 October, only the preregistered FedAvgM checkpoints were scored on test, once. We "
          "also report what failed: the rolling-history agent failed its preregistered test, the pre-screen "
          "threshold did not transfer across seeds, and int8 was dropped. Every number in the paper and the "
          "report was checked against its source file, and all 58 references were verified.",
          "Did you touch the test set?",
          "Yes, in documented ways: the audit lists every read, and nothing was selected from it.")


# 14 --------------------------------------------------------------------------- summary
@slide(T_SUMMARY, "Sampath", [PAPER, PI])
def s_summary(s):
    sh = shape(s, "TextShape 2")
    tf = sh.text_frame
    heads = [p for p in tf.paragraphs if p.text.strip()]
    content = {
        "Key Findings": ["FedAvg matches centralized at α=5.0; loses most at α=0.1",
                         "Explanation check: agreement falls with skew; α=0.1 directional",
                         "Trust check: all rules track composition; agent also responds to attack"],
        "Limitations": ["Three seeds; the floor rests on three seed pairs",
                        "Worst-case attacker rides the composition axis",
                        "Agent rationale partly unfaithful; decisions vary between calls"],
        "Future Directions": ["Partitions that vary size and skew independently",
                              "Seeded multi-draw SHAP; more seeds for the floor",
                              "Attackers off the composition axis; FedAvgM and explanations"],
    }
    # rebuild: keep each template heading paragraph, replace the empty lines under it
    for p in list(tf.paragraphs):
        if not p.text.strip():
            p._p.getparent().remove(p._p)
    for hp in heads:
        key = hp.text.strip()
        for r in hp.runs:
            r.font.size = Pt(18)
        hp.space_before = Pt(4)
        anchor = hp._p
        for line in content[key]:
            new_p = copy.deepcopy(hp._p)
            for r in new_p.findall(qn("a:r"))[1:]:
                new_p.remove(r)
            anchor.addnext(new_p)
            anchor = new_p
            from pptx.text.text import _Paragraph
            np_ = _Paragraph(new_p, tf)
            np_.runs[0].text = line
            np_.runs[0].font.bold = False
            np_.runs[0].font.size = Pt(15)
            _bullet(np_, False)
            np_._p.get_or_add_pPr().set("marL", "411480")
            np_.space_before = Pt(2)
    sh.top = Inches(0.55)
    sh.height = Inches(4.15)
    notes(s, "Sampath",
          "To summarise. FedAvg holds centralized accuracy at mild skew and loses it at strong skew. In the "
          "explanation check, agreement falls with skew, and at alpha 0.1 it reaches the level seeds alone "
          "produce, which we report as directional. In the separate trust check, the classical rules and the agent "
          "all reacted to silo composition; only the agent also responded to the attack, where silos were not "
          "saturated. Our limits: three seeds, a worst-case attacker on the composition axis, and a partly "
          "unfaithful agent rationale. Detect the attack, then check the detector. Adithya will close.",
          "What would you do with three more months?",
          "More seeds for the floor and the baselines, seeded multi-draw SHAP, and a partition design that varies "
          "size and skew independently.")


# 15 --------------------------------------------------------------------------- bibliography (2 slides)
REFS = [
    "H. B. McMahan, E. Moore, D. Ramage, S. Hampson and B. Agüera y Arcas, “Communication-efficient learning "
    "of deep networks from decentralized data,” in Proc. AISTATS, 2017, pp. 1273–1282.",
    "T. Li, A. K. Sahu, M. Zaheer, M. Sanjabi, A. Talwalkar and V. Smith, “Federated optimization in "
    "heterogeneous networks,” in Proc. MLSys, vol. 2, 2020, pp. 429–450.",
    "T.-M. H. Hsu, H. Qi and M. Brown, “Measuring the effects of non-identical data distribution for federated "
    "visual classification,” arXiv:1909.06335, 2019.",
    "S. M. Lundberg and S.-I. Lee, “A unified approach to interpreting model predictions,” in Proc. NIPS, "
    "2017, pp. 4765–4774.",
    "S. Vigna, “A weighted correlation index for rankings with ties,” in Proc. WWW, 2015, pp. 1166–1176.",
    "M. Watson, B. Awwad Shiekh Hasan and N. Al Moubayed, “Agree to disagree: When deep learning models with "
    "identical architectures produce distinct explanations,” in Proc. WACV, 2022, pp. 1524–1533.",
    "A. Oki, Y. Ogawa, K. Ota and M. Dong, “Evaluation of applying federated learning to distributed intrusion "
    "detection systems through explainable AI,” IEEE Netw. Lett., vol. 6, no. 3, pp. 198–202, 2024.",
    "M. Gholizade, F. Ruffini, P. Ducange and F. Marcelloni, “Federated explainable artificial intelligence: "
    "Roles, architectures, evaluation, and open challenges,” Expert Syst. Appl., 2026, arXiv:2607.13045.",
    "P. Blanchard, E. M. El Mhamdi, R. Guerraoui and J. Stainer, “Machine learning with adversaries: Byzantine "
    "tolerant gradient descent,” in Proc. NIPS, 2017, pp. 118–128.",
    "D. Yin, Y. Chen, K. Ramchandran and P. Bartlett, “Byzantine-robust distributed learning: Towards optimal "
    "statistical rates,” in Proc. ICML, 2018, pp. 5650–5659.",
    "G. Engelen, V. Rimmer and W. Joosen, “Troubleshooting an intrusion detection dataset: the CICIDS2017 case "
    "study,” in Proc. IEEE SPW, 2021, pp. 7–12.",
    "L. Liu, G. Engelen, T. Lynar, D. Essam and W. Joosen, “Error prevalence in NIDS datasets: A case study on "
    "CIC-IDS-2017 and CSE-CIC-IDS-2018,” in Proc. IEEE CNS, 2022, pp. 254–262.",
]


def bib_slide(first, last):
    def build(s):
        body = None
        for sh in s.shapes:
            if sh.is_placeholder and sh.placeholder_format.idx == 1:
                body = sh
        tf = body.text_frame
        tf.word_wrap = True
        for i, ref in enumerate(REFS[first:last], start=first + 1):
            p = tf.paragraphs[0] if i == first + 1 else tf.add_paragraph()
            for r in list(p.runs):
                r._r.getparent().remove(r._r)
            _run(p, f"[{i}]  ", 14, bold=True, color=MAROON)
            _run(p, ref, 14)
            _bullet(p, False)
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", "365760")
            pPr.set("indent", "-365760")
            p.space_before = Pt(6)
            p.alignment = PP_ALIGN.LEFT
        body.left, body.top, body.width, body.height = Inches(0.3), Inches(0.85), Inches(9.3), Inches(3.9)
        # the template's Bibliography slide has no page number: copy the template's own number box
        num = copy.deepcopy(shape(PRS.slides[T_RESULTS], "TextShape 3")._element)
        s.shapes._spTree.append(num)
        notes(s, "Adithya",
              "This slide is not presented; it stays up only if asked. These are the main references behind the "
              "talk, in IEEE style. The federated learning methods are McMahan, Li and Hsu; the explanation methods "
              "are Lundberg, Vigna and Watson; the closest work is Oki et al. and the survey by Gholizade et al.; "
              "the robust baselines are Blanchard and Yin; and the dataset is Engelen and Liu. Our paper cites "
              "every one of its references after checking each one exists with the title and venue given.",
              "Did you verify your references?",
              "Yes: every entry of paper/refs.bib was looked up and confirmed; see paper/citation_check.md.")
    return build


slide(T_BIB, "Adithya", ["paper/refs.bib"])(bib_slide(0, 6))
slide(T_BIB, "Adithya", ["paper/refs.bib"])(bib_slide(6, 12))


# 16 --------------------------------------------------------------------------- thank you
@slide(T_THANKS, "Adithya", [])
def s_thanks(s):
    # the template's Thank-you slide has no logo: copy the template's own logo picture
    src = PRS.slides[T_RESULTS]
    logo = shape(src, "Picture 2")
    image_part = src.part.related_part(logo._element.blip_rId)
    rid = s.part.relate_to(image_part, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
    el = copy.deepcopy(logo._element)
    el.blipFill.blip.set(qn("r:embed"), rid)
    el.nvPicPr.cNvPr.set("id", "900")
    s.shapes._spTree.append(el)
    notes(s, "Adithya",
          "Thank you for listening. We are happy to take questions. Whoever owns a section answers first: Shaun "
          "for the problem and the data, Tharun for related work and the explanation check, Sampath for the trust "
          "check, efficiency and our checks, and me for the system, accuracy and the demo. Anyone may add the limitation that goes with an answer. We never combine the two checks into "
          "one claim, and if we did not measure something, we say so rather than guess.",
          "Can you show the demo again?",
          "Yes; the dashboard is still running, and the backup slides cover the hardest questions.")


# Backup slides ---------------------------------------------------------------------
def backup(question, answer, items, speaker, sources, speech, q, a, table=None):
    def build(s):
        set_title(s, "Backup")
        set_heading(s, question)
        add_text(s, 0.3, 1.12, 9.3, 0.55, [{"text": answer, "size": 18, "bold": True, "color": MAROON}])
        y = 1.75
        if table:
            rows, cw = table
            add_table(s, 0.3, y, sum(cw), rows, cw, size=13, row_h=0.34, bold_first_col=True,
                      align=[None] + [PP_ALIGN.CENTER] * (len(cw) - 1))
            y += 0.34 * len(rows) + 0.15
        add_text(s, 0.3, y, 9.3, 4.75 - y, bullets(items, size=17, space=8))
        notes(s, speaker, speech, q, a)
    slide(T_RESULTS, speaker, sources)(build)


backup("Did you touch the test set?",
       "Yes, in documented ways; nothing was selected from it.",
       ["All model and round selection used validation data",
        "Three early choices cited test; validation picks the same values",
        "3 vs 1 local epochs on validation: 0.9425 vs 0.8602 (α=0.5)",
        "Other reads: legacy logging, 14 SHAP input rows, display rows, pilots",
        "Since 2026-10-12: only the preregistered FedAvgM checkpoints, scored once"],
       "Adithya", [PI, AUD, PRE],
       "Yes, and we publish the full audit. Every model and every round was selected on validation. Three early "
       "choices, three local epochs, FedProx mu and the StandardScaler, were first recorded with test numbers as "
       "their justification; re-checked on validation, the same values win, for example 0.9425 against 0.8602 "
       "for three epochs over one. The test set was also read for legacy logging, 14 SHAP input rows, display rows "
       "and pilot runs, and nothing was chosen from those. Since 12 October only one preregistered configuration "
       "may ever be scored on test.",
       "Could the three test-cited choices have biased the headline?",
       "Validation selects the same three values, so the headline would not change; we disclose it anyway.")

backup("Is 0.333 vs 0.429 significant?",
       "No: directional, not significant.",
       ["The intervals overlap at 0.429",
        "Robust: agreement rises with α; every α is 5.1×–10.3× chance",
        "No p-values: silos in one run share one training trajectory"],
       "Tharun", [PI, CA],
       "No, and we say so on the slide. At alpha 0.1 the median Jaccard at ten is 0.333 and its cluster-bootstrap "
       "interval is 0.250 to 0.429. The seed-noise floor has median 0.429 and its pair medians range from 0.429 to "
       "0.484. The two touch, so we call the gap directional, not significant. What is robust is the trend: "
       "agreement rises with alpha, and every level is 5.1 to 10.3 times chance. We give no p-values, because "
       "silos in one run follow one sequence of global models and are not independent.",
       "Why not more seeds to settle it?",
       "Each seed is a full set of federated runs plus SHAP; more seeds for the floor are our first next step.",
       table=([["Quantity", "Median", "Interval / range"],
               ["Agreement at α=0.1 (Jaccard@10)", "0.333", "[0.250, 0.429]"],
               ["Seed-noise floor", "0.429", "[0.429, 0.484]"]], [4.3, 1.6, 2.6]))

backup("Why did Krum fail?",
       "Under non-IID data, honest but unusual silos look like outliers.",
       ["Multi-Krum excluded the same two large Benign-heavy silos every round",
        "Multi-Krum excluded a malicious silo 0% of the time (chance 0.30)",
        "f=2 recovery fraction 1.3490: a compositional artifact, not detection",
        "Given the true attacker count, yet still failed",
        "Classical Krum keeps 1 of 10: exclusions are chance-level"],
       "Sampath", [CB, PI],
       "Krum assumes honest updates cluster together and attackers stand out. Under non-IID data, honest "
       "organisations with unusual traffic stand out too. In our runs, Multi-Krum's choices were driven by silo "
       "size and composition: it excluded the same two large, Benign-heavy silos in every round, attack or not, "
       "and Multi-Krum excluded a malicious silo 0% of the time, against a chance rate of 0.30, although it was "
       "told the true number of attackers. Its apparent recovery at two attackers, 1.3490, is a compositional artifact, not "
       "detection.",
       "Wasn't giving the baselines the true f unfair?",
       "Unfair in their favour, on purpose; they still failed, so the failure is not from guessing f wrong.")

backup("Why trust an LLM?",
       "We don't take it on trust; we measure it.",
       ["Citation error 11.7% (seed 42) → 22.5% (seeds 1337, 2024)",
        "Rolling history: about 35–45% of trend claims contradicted the data",
        "Stability: 27/30 exact repeats; 30/30 on trust vs flagged",
        "Local model, temperature 0.2, never told the attacker count",
        "Wording: decisions plus a rationale of measured fidelity"],
       "Sampath", [CB, PI, "configs/agent.yaml"],
       "We don't, blindly. We measure it. The agent's strict citation error was 11.7% at seed 42 and 22.5% at the "
       "other two seeds. When given five-round histories, about 35 to 45% of its trend claims contradicted the "
       "sequence it was shown. Repeat calls on the same round agreed exactly 27 times out of 30, and 30 out of 30 "
       "on trust versus flagged. It runs locally at temperature 0.2 and is never told the attacker count. That is "
       "why our wording is: it produces decisions plus a rationale of measured fidelity.",
       "Why not a bigger model?",
       "It has to fit our 6 GB GPU and run locally; llama3.1 8B beat the other two candidates we tested.")

backup("Why is federated accuracy lower at α=0.1?",
       "Strong label skew, not federation itself.",
       ["α=5.0: FedAvg 0.990 ± 0.001 vs centralized 0.9900 ± 0.0022",
        "α=0.1: per-class F1 for Bot 0.1253, WebAttack 0.0490",
        "Silo sizes 143 to 636,676 rows; FedAvg weights by size",
        "Preregistered FedAvgM: 0.5930 ± 0.0632, still far below centralized"],
       "Adithya", [PI, PAPER, "results/aggregated/federated_per_family.csv", "results/partition_check.json"],
       "Because of label skew, not federation itself. At alpha 5.0 FedAvg scores 0.990 against 0.9900 for the "
       "centralized model, so federation alone costs nothing measurable. At alpha 0.1 a family usually sits almost "
       "whole in one silo, and whole families collapse: per-class F1 is 0.1253 for Bot and 0.0490 for WebAttack. "
       "Silo sizes run from 143 to 636,676 rows, and FedAvg weights updates by size, so small silos barely count. "
       "Our preregistered FedAvgM helps, to 0.5930, but stays far below centralized.",
       "Would more rounds fix it?",
       "Not reliably: under skew the global model jumps between rounds, which is why every model is its "
       "best-by-validation round.")

backup("What's new here?",
       "Not the FL + IDS + XAI combination; recent papers cover it.",
       ["A seed-noise null control for explanation agreement",
        "Where Oki et al.'s convergence breaks down as α falls",
        "Krum family at 10 silos with an oracle attacker count",
        "An audit of the agent's own rationale against its data",
        "Validation-only selection and one preregistered test read"],
       "Tharun", [PI],
       "Not the combination of federated learning, intrusion detection and explainability; several recent papers "
       "cover that. What we add is a seed-noise null control for explanation agreement, which we did not find "
       "reported in the federated IDS work we read; a characterisation of where Oki et al.'s convergence breaks "
       "down as alpha falls; a test of the Krum family at ten silos with an oracle attacker count; and an audit "
       "of how often the agent's written reasons match its data. All of it sits inside a protocol with "
       "validation-only selection.",
       "Couldn't someone have done the seed control before?",
       "Possibly; we say we did not find it in the federated IDS papers we read, and we do not claim to be first.")



# ============================================================================= demo script
# Taken from the team handbook (docs/handbook/XFed_Team_Handbook.md, section 5.2) and checked against
# the current dashboard screenshots (docs/dashboard_v2/screens/, recaptured 2026-10-14; the frontend has
# not changed since). Each line names the files its numbers come from; number_check.py verifies them.
DEMO = [
    ("0:00", "Open the Live route (Deep Sea theme).",
     "This is XFed-IDS. Ten organisations trained this detector together without sharing traffic. The flows "
     "on the left are validation rows replayed as live traffic, never test rows.",
     [PI]),
    ("0:30", "Point at the four key figures; click one source link under a figure.",
     "Top row: our preregistered FedAvgM model's test macro-F1, 0.9852 at α=0.5, scored once. Per-flow latency "
     "45.7 µs with ONNX. Upload per round falls 50% with fp16 updates. Each number links to the file it came "
     "from.",
     ["results/federated_methods/test_once/result.json", "results/efficiency/inference_speed_summary.json",
      EFF, PI]),
    ("1:00", "Click a DoS flow in the stream.",
     "The model says DoS. On the right is why: SHAP shows which features pushed it there, here packet-length "
     "statistics. Base value, output and residual are shown, because SHAP's sums aren't exact and we measured "
     "that.", []),
    ("1:30", "Point at the LLM summary above the SHAP bars.",
     "This sentence is an LLM summary for the analyst. It is labelled 'not a research result': a usability "
     "feature, not a research claim.", []),
    ("1:50", "Click the Misses filter, then Next miss.",
     "We don't hide mistakes. Here is a flow the model got wrong.", []),
    ("2:15", "Point at the Trust check panel (α=0.5, seed 1337, f=3 sudden).",
     "This is the trust check, a separate experiment. Open circle: how often our agent flagged each "
     "organisation with no attack. Filled: under attack. At seed 1337, org 5 goes from 0.00 to 0.95: real "
     "detection. But some orgs are flagged in almost every round with no attack at all; the note under the "
     "chart names them. That is the compositional confound.", [CB]),
    ("3:00", "Open Investigate; the first question is 'Is anyone poisoning it?'.",
     "Investigate answers four questions, trust first. Multi-Krum excluded a poisoned org 0% of the time. "
     "ByzAgent's result, in our locked words: [read the quote on screen].", [CB, PI]),
    ("3:40", "Scroll to 'Do the orgs agree on why?'.",
     "Explanation check. Chance is 0.065, the seed-noise floor is 0.429. At α=5.0 agreement is 0.667; at "
     "α=0.1 it is 0.333, below the floor: directional, not significant, the intervals overlap.", [CA, PI]),
    ("4:20", "Scroll to 'What does it cost to run?'.",
     "1,587,920 bytes per round; compression saves up to 74.9% of upload with no detectable effect at n=3; "
     "and two ideas we tested and dropped.", ["results/efficiency/communication.json", EFF, PI]),
    ("4:40", "Open the Limits route.",
     "Finally, Limits shows our claims and limitations verbatim from the project instructions. We'd rather "
     "you read them here than find them yourself.", []),
    ("5:00", "Switch back to the slides.", "Back to the slides for what we checked and what failed.", []),
]
DEMO_OPTIONAL = ("Optional hot-swap, about two more minutes, only if time allows: on Live select an alert, "
                 "click Hot-swap model, confirm. Say: \"This retrains for two rounds from the base model in a "
                 "separate process. It replaces the served model only if it is at least as good on validation; "
                 "otherwise it is rejected, and that happens often, because of the round lottery.\" Then revert.")
DEMO_FALLBACK = ("If the live demo fails: stay on the Dashboard slide and talk through its three screenshots, then "
                 "the full-page screenshots in docs/dashboard_v2/screens/.")

WPM = 140   # speaking rate used for the timing estimate


def speech_of(note):
    body = note.split("\n\nLikely question:")[0]
    return body.split(":", 1)[1].strip()


def fmt_min(m):
    sec = int(round(m * 60))
    return f"{sec // 60}:{sec % 60:02d}"


def write_speaker_script(built):
    order = ["Adithya", "Shaun", "Tharun", "Sampath"]
    n_main = next(i for i, b in enumerate(built, start=1) if b[1] == "s_thanks")
    rows = []
    for n, (s, name, speaker, sources) in enumerate(built, start=1):
        note = s.notes_slide.notes_text_frame.text
        heading, title = "", ""
        for sh in s.shapes:
            if sh.name == "TextShape 2" and sh.has_text_frame:
                heading = sh.text_frame.paragraphs[0].text.strip()
            if sh.name in ("TextShape 1", "Title 1") and sh.has_text_frame:
                title = " ".join(sh.text_frame.text.split())
        if name == "s_title":
            heading = "Title"
        presented = n < n_main and not title.lower().startswith("bibliography")
        rows.append((n, speaker, title, heading, note, n > n_main, presented))
    words = {k: 0 for k in order}
    nums = {k: [] for k in order}
    for n, sp, title, heading, note, is_backup, presented in rows:
        if presented:
            words[sp] += len(speech_of(note).split())
            nums[sp].append(str(n))
    total = sum(words.values())
    L = ["# Speaker script: Capstone Final Review\n",
         "Generated by `python docs/ppt/build_ppt.py` from the speaker notes in "
         "`docs/ppt/XFed_Capstone_Final_Review.pptx`. Each note starts with the speaker's name and ends with "
         "the likely question for that slide and a short answer. Every number here is checked by "
         "`python docs/ppt/number_check.py` against the files named in `docs/ppt/slide_sources.json`.\n",
         f"Deck: {n_main} main slides (Thank-you is slide {n_main}) and {len(rows) - n_main} backup slides.\n",
         "## Timing estimate\n",
         f"Speaking rate assumed: {WPM} words per minute, applied to the spoken part of each note (the likely "
         "question and answer are not counted). The two Bibliography slides and the Thank-you slide are not "
         "presented; backup slides are used only in questions. The live demo adds about 5 minutes for Adithya "
         "(script below). Target: 15 minutes of slides plus a 5-minute demo.\n",
         "| Speaker | Slides presented | Words | Estimated time |", "|---|---|---:|---:|"]
    for sp in order:
        extra = " + about 5:00 demo" if sp == "Adithya" else ""
        L.append(f"| {sp} | {', '.join(nums[sp])} | {words[sp]} | {fmt_min(words[sp] / WPM)}{extra} |")
    L.append(f"| **Total** | | {total} | {fmt_min(total / WPM)} + about 5:00 demo |\n")
    L.append("Split (team decision, 2026-11-19): Adithya: title, outline, overview, architecture, modules, "
             "tools, detection accuracy, dashboard and live demo, Thank-you. Shaun: problem, objectives, dataset, "
             "partitioning, parameters. Tharun: related work, improvements, both explanation-check slides. "
             "Sampath: both trust-check slides, efficiency, what we checked, summary.\n")
    L.append("Hand-offs, in order (the hand-off line ends the outgoing speaker's note, and the next note "
             "opens with a thank-you): Adithya to Shaun (slide 3 to 4), Shaun to Tharun (5 to 6), Tharun to "
             "Adithya (7 to 8), Adithya to Shaun (10 to 11), Shaun to Adithya (13 to 14), Adithya to Tharun "
             "(14 to 15), Tharun to Sampath (16 to 17), Sampath to Adithya (19 to 20), Adithya to Sampath "
             "(20 to 21), Sampath to Adithya (22 to 25).\n")
    L.append("Backup answers: test set and accuracy at α=0.1: Adithya. Significance of 0.333 vs 0.429 and "
             "\"what's new\": Tharun. Krum and the LLM: Sampath. The Bibliography slides are not presented; their "
             "notes stay with Adithya.\n")
    for sp in order:
        L.append(f"## {sp}\n")
        for n, s2, title, heading, note, is_backup, presented in rows:
            if s2 != sp:
                continue
            tag = "backup: " if is_backup else ("not presented: " if not presented else "")
            L.append(f"### Slide {n} ({tag}{heading or title})\n")
            body, qa = note.split("\n\nLikely question:")
            L.append(body.strip() + "\n")
            q, a = qa.split("\nShort answer:")
            L.append(f"- *Likely question:* {q.strip()}")
            L.append(f"- *Short answer:* {a.strip()}\n")
    L.append("## Demo script (about 5 minutes, Adithya, at the Dashboard slide)\n")
    L.append("Taken from the team handbook (section 5.2) and checked against the current dashboard. Before the "
             "review, double-click `APP.bat` in the repo root: it starts the backend, waits for its health check "
             "(about a minute), then starts the simulator and the frontend at http://localhost:5173/. Ollama "
             "does not need to run; the LLM summaries are stored.\n")
    L.append("| Time | Click | Say |")
    L.append("|---|---|---|")
    for t, click, say, _src in DEMO:
        L.append(f"| {t} | {click} | \"{say}\" |")
    L.append("")
    L.append(DEMO_OPTIONAL + "\n")
    L.append(DEMO_FALLBACK + "\n")
    L.append("Sources for the numbers spoken in the demo: " + "; ".join(
        f"{t}: {', '.join(src)}" for t, _c, _s, src in DEMO if src) + ".\n")
    with open(os.path.join(PPT, "speaker_script.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return words



# ============================================================================= build
PRS = None


def speaker_of(note_text):
    return note_text.split(":", 1)[0]


def main():
    global PRS
    PRS = Presentation(TEMPLATE)
    originals = list(PRS.slides)
    built = []
    for t_index, fn, speaker, sources in SLIDES:
        s = clone_slide(PRS, originals[t_index])
        fn(s)
        built.append((s, fn.__name__, speaker, sources))
    for s in originals:
        delete_slide(PRS, s)
    PRS.save(OUT)

    meta = []
    for n, (s, name, speaker, sources) in enumerate(built, start=1):
        meta.append({"slide": n, "builder": name, "speaker": speaker, "sources": sources})
    demo_meta = [{"time": t, "text": say, "sources": src} for t, _c, say, src in DEMO]
    with open(os.path.join(PPT, "slide_sources.json"), "w", encoding="utf-8") as f:
        json.dump({"slides": meta, "demo": demo_meta}, f, indent=1, ensure_ascii=False)
    words = write_speaker_script(built)
    print(f"wrote {OUT}: {len(built)} slides; words per speaker {words}")


if __name__ == "__main__":
    main()
