"""Render selected PDF pages of the report to PNG for visual review.

    python docs/report/render_pages.py <pdf> <out_dir> <page> [<page> ...]   (1-based pages)
    python docs/report/render_pages.py <pdf> <out_dir> --sheet <first> <last> (contact sheet)
"""
import sys
from pathlib import Path

import pymupdf
from PIL import Image


def main():
    pdf, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf)
    if sys.argv[3] == "--sheet":
        first, last = int(sys.argv[4]), int(sys.argv[5])
        thumbs = []
        for i in range(first - 1, min(last, doc.page_count)):
            pix = doc[i].get_pixmap(dpi=40)
            thumbs.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
        w, h = thumbs[0].size
        cols = 6
        rows = (len(thumbs) + cols - 1) // cols
        sheet = Image.new("RGB", (w * cols, h * rows), "white")
        for k, t in enumerate(thumbs):
            sheet.paste(t, ((k % cols) * w, (k // cols) * h))
        path = out / f"sheet_{first}_{last}.jpg"
        sheet.save(path, quality=70)
        print(path)
        return
    for p in sys.argv[3:]:
        pix = doc[int(p) - 1].get_pixmap(dpi=80)
        path = out / f"page_{int(p):03d}.png"
        pix.save(str(path))
        print(path)


if __name__ == "__main__":
    main()
