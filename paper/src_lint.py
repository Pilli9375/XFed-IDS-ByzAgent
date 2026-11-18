"""Flag "% src:" comments whose content is not a list of file paths.

A comment placed in the middle of a line would silently hide the rest of that line's
text from LaTeX. Run from the repository root: python paper/src_lint.py
"""
import re
import sys

bad = 0
for f in ("paper/main.tex", "paper/appendix.tex"):
    for i, line in enumerate(open(f, encoding="utf-8").read().split("\n"), 1):
        m = re.search(r"(?<!\\)%\s*src:\s*(.*)$", line)
        if not m:
            continue
        parts = [p.strip() for p in m.group(1).split(";")]
        wrong = [p for p in parts if not re.fullmatch(r"[\w./\-*{}]+", p)]
        if wrong:
            bad += 1
            print(f, i, "|", wrong)
print("bad src comments:", bad)
sys.exit(1 if bad else 0)
