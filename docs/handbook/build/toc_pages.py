"""Read the rendered PDF's outline and write {heading title: page number} to toc_pages.json.

Used for a two-pass build: build_handbook.py -> render_pdf.mjs -> this -> build_handbook.py -> render_pdf.mjs.
Stdlib only; relies on Chromium writing the outline and page tree as plain (uncompressed) objects.
"""
import json
import re
from pathlib import Path

HB = Path(__file__).resolve().parents[1]
b = (HB / "XFed_Team_Handbook.pdf").read_bytes()

objs = {int(m.group(1)): m.group(2) for m in re.finditer(rb"\n(\d+) 0 obj\n(.*?)\nendobj", b, re.S)}


def kids(num):
    o = objs[num]
    if b"/Type /Pages" in o:
        out = []
        for k in re.findall(rb"(\d+) 0 R", re.search(rb"/Kids \[(.*?)\]", o, re.S).group(1)):
            out += kids(int(k))
        return out
    return [num]


root_pages = next(n for n, o in objs.items() if b"/Type /Pages" in o and b"/Parent" not in o)
order = {n: i + 1 for i, n in enumerate(kids(root_pages))}


def decode(raw: bytes) -> str:
    raw = raw.strip()
    if raw.startswith(b"<"):
        h = bytes.fromhex(raw[1:-1].decode())
        return h[2:].decode("utf-16-be") if h[:2] == b"\xfe\xff" else h.decode("latin-1")
    s = raw[1:-1]
    s = re.sub(rb"\\([0-7]{1,3})", lambda m: bytes([int(m.group(1), 8)]), s)
    s = re.sub(rb"\\(.)", rb"\1", s)
    return s[2:].decode("utf-16-be") if s[:2] == b"\xfe\xff" else s.decode("latin-1")


pages = {}
for n, o in objs.items():
    m = re.search(rb"/Title (\(.*?\)|<[0-9A-Fa-f]+>)\s*/Dest \[(\d+) 0 R", o, re.S)
    if m:
        title = re.sub(r"\s+", " ", decode(m.group(1))).strip()
        pages.setdefault(title, order.get(int(m.group(2))))
(HB / "build" / "toc_pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(pages), "outline entries;", len(order), "pages")
