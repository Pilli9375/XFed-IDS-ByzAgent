# Building the handbook

From the repo root (stdlib Python + the Playwright Chromium installed for `film/`):

```powershell
python docs/handbook/build/make_figures.py      # SVG diagrams + copies of results/figures PNGs -> img/
python docs/handbook/build/build_handbook.py    # src/*.md -> XFed_Team_Handbook.md + .html
node   docs/handbook/build/render_pdf.mjs       # .html -> .pdf (A4, outline, page numbers)
python docs/handbook/build/toc_pages.py         # read page numbers from the PDF outline
python docs/handbook/build/build_handbook.py    # second pass: TOC with page numbers
node   docs/handbook/build/render_pdf.mjs
```

Edit chapters in `src/`; `XFed_Team_Handbook.md` is regenerated from them.
