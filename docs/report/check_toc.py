"""Check that every entry of the TOC, List of Tables and List of Figures points to the right page.

    python docs/report/check_toc.py docs/report/XFed_Capstone_Report.pdf

Reads the printed page number at the foot of each PDF page, parses the three lists, and confirms
that each entry's text (its first words) appears on the page the list gives. Also searches for
leftover template text.
"""
import re
import sys

import pymupdf

LEFTOVER = ["automobile", "raspberry", "arduino", "yyyyy", "xxxx", "name1", "name of the"]


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def main():
    doc = pymupdf.open(sys.argv[1])
    printed = {}
    texts = []
    for i, page in enumerate(doc):
        t = page.get_text()
        texts.append(t)
        lines = [l.strip() for l in t.split("\n") if l.strip()]
        nums = [l for l in lines[:3] + lines[-3:] if re.fullmatch(r"\d{1,3}", l)]
        if nums:
            printed[int(nums[0])] = i
    entries = []
    for i, t in enumerate(texts[:40]):
        for m in re.finditer(r"^(.{3,}?)\s*\.{4,}\s*(\d{1,3})\s*$", t, re.M):
            entries.append((m.group(1).strip(), int(m.group(2))))
    joined = [norm(t) for t in texts]
    bad = []
    for title, pg in entries:
        idx = printed.get(pg)
        key = norm(title)
        key = " ".join(key.split()[:6])
        if idx is None or key not in joined[idx]:
            bad.append((title, pg))
    print(f"list entries checked: {len(entries)}; wrong or not found: {len(bad)}")
    for title, pg in bad[:40]:
        print("  ", pg, title[:90])
    body = "\n".join(texts).lower()
    for w in LEFTOVER:
        n = body.count(w)
        print(f"leftover '{w}': {n}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
