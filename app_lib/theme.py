"""Design system: tokens, CSS, and reusable UI components.

Deliberately separated from sections.py so visual changes never touch code
that reads or computes a number. If deleting this file changed a displayed
value, that would be a bug.

FONTS: system stack only, no webfont import. The demo must run offline --
a Google Fonts <link> blocks first paint until it times out on a network
with no route to the CDN. Segoe UI Variable (Windows 11 default) is the
practical target and is a strong UI face on its own.

CHARTS: all charts are Plotly, built in plots.py. This module supplies
the color tokens and font stack they use, so a palette change here
propagates to every figure automatically.
"""
from __future__ import annotations

import streamlit as st

# --- Design tokens ---------------------------------------------------------
# One cool accent, one warm alert accent, a neutral ramp. Restraint is the
# point: saturated color is reserved for things that carry meaning.

BG            = "#0d1117"
SURFACE       = "#151b23"
SURFACE_HI    = "#1c232c"
BORDER        = "#2a323d"
BORDER_HI     = "#3a4553"

TEXT          = "#e6edf3"
TEXT_MUTED    = "#8b98a5"
TEXT_FAINT    = "#6b7681"

ACCENT        = "#4cc9f0"
ACCENT_DIM    = "#2a7f9e"
ALERT         = "#f2726f"
WARN          = "#e8b339"
POSITIVE      = "#5bc0a0"
VIOLET        = "#a78bfa"

# Chart series palette -- colorblind-safer than a rainbow, holds up when a
# projector crushes saturation.
SERIES = [ACCENT, VIOLET, POSITIVE, WARN, ALERT, "#7aa2f7", "#e08fc4", "#9ca7b3"]

# Semantic color per attack family. Benign reads calm; attack families get
# distinct hues so the same family is the same color everywhere in the app.
FAMILY_COLORS = {
    "Benign":       POSITIVE,
    "Bot":          VIOLET,
    "BruteForce":   WARN,
    "DDoS":         ALERT,
    "DoS":          "#e0895f",
    "Heartbleed":   "#d16ba5",
    "Infiltration": "#c77dff",
    "PortScan":     ACCENT,
    "WebAttack":    "#7aa2f7",
}


def family_color(name: str) -> str:
    return FAMILY_COLORS.get(name, TEXT_MUTED)


FONT_STACK = (
    '"Segoe UI Variable Display", "Segoe UI Variable", "Segoe UI", '
    "-apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif"
)
MONO_STACK = '"Cascadia Code", "JetBrains Mono", Consolas, "SF Mono", Menlo, monospace'

# Plotly needs a plain comma list, not CSS-quoted families.
PLOTLY_FONT = "Segoe UI Variable Display, Segoe UI, -apple-system, Roboto, Helvetica, Arial, sans-serif"

# Spacing scale -- 4px base. Every margin/padding in the CSS below is a
# multiple of this, so vertical rhythm stays consistent instead of drifting.
SP = {"xs": "0.25rem", "sm": "0.5rem", "md": "1rem",
      "lg": "1.5rem", "xl": "2.25rem", "2xl": "3.5rem"}

# Section icons. Inline SVG rather than emoji: emoji render differently on
# every OS and look toy-like on a projector.
NAV_ICONS = {
    "Federation Status": "M3 3h6v6H3zM11 3h6v6h-6zM3 11h6v6H3zM11 11h6v6h-6z",
    "Detect": "M10 2a8 8 0 105.3 14l3.4 3.4 1.4-1.4-3.4-3.4A8 8 0 0010 2zm0 2a6 6 0 110 12 6 6 0 010-12z",
    "Explain": "M3 17h3V9H3v8zm5.5 0h3V3h-3v14zm5.5 0h3v-6h-3v6z",
    "Explanation Agreement": "M3 15l4-5 3 3 4-6 3 4v3H3z M3 4h14v1.5H3z",
    "Faithfulness": "M10 2l7 3v5c0 4.4-3 8.3-7 9-4-0.7-7-4.6-7-9V5l7-3zm0 2.2L5 6.3V10c0 3.3 2.1 6.3 5 7 2.9-0.7 5-3.7 5-7V6.3l-5-2.1z",
    "Methods & Limits": "M10 2a8 8 0 100 16 8 8 0 000-16zm0 3.2a1.2 1.2 0 110 2.4 1.2 1.2 0 010-2.4zM9 9h2v6H9V9z",
    "Client Trust Monitor": "M3 4h11v2H3V4zm0 5h8v2H3V9zm0 5h5v2H3v-2zm13-6l1.4 1.4L13 13.8l-2.4-2.4L12 10l1 1 3-3z",
}


CUSTOM_CSS = f"""
<style>
  /* ---- Remove Streamlit chrome -------------------------------------
     The Deploy button, hamburger, and "Made with Streamlit" footer make
     a demo read as somebody's dev tool rather than a system.          */
  #MainMenu, header[data-testid="stHeader"], footer,
  div[data-testid="stToolbar"], div[data-testid="stDecoration"] {{
    display: none !important;
  }}

  .stApp {{
    background: {BG};
    font-family: {FONT_STACK};
  }}

  /* Reclaim the vertical space the hidden header used to occupy */
  div[data-testid="stAppViewContainer"] > section.main div.block-container {{
    padding-top: 2.2rem;
    padding-bottom: 4rem;
    max-width: 1500px;
  }}

  /* ---- Typography scale --------------------------------------------- */
  h1, h2, h3, h4 {{ font-family: {FONT_STACK}; color: {TEXT}; }}
  h1 {{ font-size: 2.1rem !important; font-weight: 700 !important;
        letter-spacing: -0.025em; line-height: 1.15; margin-bottom: 0.1rem !important; }}
  h2 {{ font-size: 1.28rem !important; font-weight: 650 !important;
        letter-spacing: -0.012em; margin-top: 0 !important; }}
  h3 {{ font-size: 1.05rem !important; font-weight: 600 !important; }}
  p, li, span, label {{ color: {TEXT}; }}
  code {{ font-family: {MONO_STACK}; font-size: 0.86em;
          background: {SURFACE_HI} !important; color: {ACCENT} !important;
          padding: 0.12em 0.4em; border-radius: 4px; }}

  /* ---- Section header ------------------------------------------------ */
  .xf-eyebrow {{
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: {ACCENT}; margin-bottom: 0.35rem;
  }}
  .xf-lede {{
    color: {TEXT_MUTED}; font-size: 0.95rem; line-height: 1.62;
    max-width: 78ch; margin-top: 0.55rem;
  }}
  .xf-rule {{
    height: 1px; border: 0; margin: 2.1rem 0 1.5rem 0;
    background: linear-gradient(90deg, {BORDER_HI} 0%, {BORDER} 45%, transparent 100%);
  }}
  .xf-subhead {{
    font-size: 1.28rem; font-weight: 650; letter-spacing: -0.012em;
    color: {TEXT}; margin: 0 0 0.15rem 0;
  }}

  /* ---- Stat cards ---------------------------------------------------- */
  .xf-stat {{
    background: linear-gradient(160deg, {SURFACE_HI} 0%, {SURFACE} 100%);
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1rem 1.15rem 1.05rem 1.15rem;
    height: 100%;
    position: relative;
    overflow: hidden;
  }}
  .xf-stat::before {{
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    background: var(--tone, {ACCENT});
  }}
  .xf-stat-label {{
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.07em;
    text-transform: uppercase; color: {TEXT_FAINT}; margin-bottom: 0.45rem;
  }}
  .xf-stat-value {{
    font-size: 1.85rem; font-weight: 700; line-height: 1.05;
    letter-spacing: -0.03em; color: {TEXT}; font-variant-numeric: tabular-nums;
  }}
  .xf-stat-value.sm {{ font-size: 1.25rem; letter-spacing: -0.015em; }}
  .xf-stat-sub {{
    font-size: 0.78rem; color: {TEXT_MUTED}; margin-top: 0.4rem; line-height: 1.45;
  }}

  /* ---- Pills / badges ------------------------------------------------ */
  .xf-pill {{
    display: inline-block; padding: 0.2rem 0.62rem; border-radius: 999px;
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.01em;
    border: 1px solid; margin-right: 0.35rem; white-space: nowrap;
  }}

  /* ---- Callouts ------------------------------------------------------ */
  .xf-callout {{
    border-radius: 10px; padding: 0.9rem 1.05rem; margin: 0.5rem 0;
    border: 1px solid; border-left-width: 3px;
    font-size: 0.88rem; line-height: 1.6;
  }}
  .xf-callout b {{ font-weight: 650; }}

  /* ---- Verdict block (big prediction readout) ------------------------ */
  .xf-verdict {{
    background: linear-gradient(160deg, {SURFACE_HI} 0%, {SURFACE} 100%);
    border: 1px solid {BORDER}; border-radius: 14px;
    padding: 1.35rem 1.5rem; position: relative; overflow: hidden;
  }}
  .xf-verdict::before {{
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
    background: var(--tone, {ACCENT});
  }}
  .xf-verdict-name {{
    font-size: 2.15rem; font-weight: 700; letter-spacing: -0.03em;
    line-height: 1.1; color: var(--tone, {TEXT});
  }}
  .xf-verdict-meta {{
    font-size: 0.86rem; color: {TEXT_MUTED}; margin-top: 0.5rem; line-height: 1.55;
  }}

  /* ---- Sidebar ------------------------------------------------------- */
  section[data-testid="stSidebar"] {{
    background: {SURFACE};
    border-right: 1px solid {BORDER};
  }}
  section[data-testid="stSidebar"] div.block-container {{ padding-top: 1.6rem; }}
  .xf-brand {{
    font-size: 1.32rem; font-weight: 700; letter-spacing: -0.02em; color: {TEXT};
  }}
  .xf-brand span {{ color: {ACCENT}; }}
  .xf-brand-sub {{
    font-size: 0.76rem; color: {TEXT_FAINT}; line-height: 1.5;
    margin-top: 0.2rem; margin-bottom: 1.1rem;
  }}
  .xf-navlabel {{
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.13em;
    text-transform: uppercase; color: {TEXT_FAINT}; margin-bottom: 0.5rem;
  }}
  /* Radio nav -> menu items */
  section[data-testid="stSidebar"] div[role="radiogroup"] {{ gap: 0.15rem; }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label {{
    padding: 0.55rem 0.7rem; border-radius: 8px; width: 100%;
    transition: background 180ms ease, color 180ms ease, border-color 180ms ease;
    border: 1px solid transparent;
  }}
  /* Hide the radio dot -- the icon + highlight carry the state instead */
  section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {{
    display: none !important;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:last-child {{
    display: flex; align-items: center;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {{
    background: {SURFACE_HI};
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {{
    background: {SURFACE_HI}; border-color: {BORDER_HI};
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {{
    color: {ACCENT} !important; font-weight: 600;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] p {{
    font-size: 0.92rem; color: {TEXT_MUTED};
  }}

  /* ---- Nav icons: CSS-masked SVG data URIs. Streamlit radio labels do
     NOT render HTML, so inline <svg> in the label would print as literal
     text -- masked pseudo-elements are the reliable route. ------------- */
  section[data-testid="stSidebar"] div[role="radiogroup"] > label::before {{
    content: ""; width: 15px; height: 15px; flex-shrink: 0;
    margin-right: 10px; background-color: {TEXT_FAINT};
    -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat;
    -webkit-mask-size: contain; mask-size: contain;
    -webkit-mask-position: center; mask-position: center;
    transition: background-color 180ms ease;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked)::before {{
    background-color: {ACCENT};
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label {{
    display: flex !important; align-items: center;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(1)::before {{
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M3%203h6v6H3zM11%203h6v6h-6zM3%2011h6v6H3zM11%2011h6v6h-6z%22%2F%3E%3C%2Fsvg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M3%203h6v6H3zM11%203h6v6h-6zM3%2011h6v6H3zM11%2011h6v6h-6z%22%2F%3E%3C%2Fsvg%3E");
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(2)::before {{
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M10%202a8%208%200%20105.3%2014l3.4%203.4%201.4-1.4-3.4-3.4A8%208%200%200010%202zm0%202a6%206%200%20110%2012%206%206%200%20010-12z%22%2F%3E%3C%2Fsvg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M10%202a8%208%200%20105.3%2014l3.4%203.4%201.4-1.4-3.4-3.4A8%208%200%200010%202zm0%202a6%206%200%20110%2012%206%206%200%20010-12z%22%2F%3E%3C%2Fsvg%3E");
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(3)::before {{
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M3%2017h3V9H3v8zm5.5%200h3V3h-3v14zm5.5%200h3v-6h-3v6z%22%2F%3E%3C%2Fsvg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M3%2017h3V9H3v8zm5.5%200h3V3h-3v14zm5.5%200h3v-6h-3v6z%22%2F%3E%3C%2Fsvg%3E");
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(4)::before {{
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M3%2015l4-5%203%203%204-6%203%204v3H3z%22%2F%3E%3C%2Fsvg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M3%2015l4-5%203%203%204-6%203%204v3H3z%22%2F%3E%3C%2Fsvg%3E");
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(5)::before {{
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M10%202l7%203v5c0%204.4-3%208.3-7%209-4-.7-7-4.6-7-9V5l7-3zm0%202.2L5%206.3V10c0%203.3%202.1%206.3%205%207%202.9-.7%205-3.7%205-7V6.3l-5-2.1z%22%2F%3E%3C%2Fsvg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M10%202l7%203v5c0%204.4-3%208.3-7%209-4-.7-7-4.6-7-9V5l7-3zm0%202.2L5%206.3V10c0%203.3%202.1%206.3%205%207%202.9-.7%205-3.7%205-7V6.3l-5-2.1z%22%2F%3E%3C%2Fsvg%3E");
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(6)::before {{
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M10%202a8%208%200%20100%2016%208%208%200%20000-16zm0%203.2a1.2%201.2%200%20110%202.4%201.2%201.2%200%20010-2.4zM9%209h2v6H9V9z%22%2F%3E%3C%2Fsvg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M10%202a8%208%200%20100%2016%208%208%200%20000-16zm0%203.2a1.2%201.2%200%20110%202.4%201.2%201.2%200%20010-2.4zM9%209h2v6H9V9z%22%2F%3E%3C%2Fsvg%3E");
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(7)::before {{
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M3%204h11v2H3V4zm0%205h8v2H3V9zm0%205h5v2H3v-2zm13-6l1.4%201.4L13%2013.8l-2.4-2.4L12%2010l1%201%203-3z%22%2F%3E%3C%2Fsvg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20d%3D%22M3%204h11v2H3V4zm0%205h8v2H3V9zm0%205h5v2H3v-2zm13-6l1.4%201.4L13%2013.8l-2.4-2.4L12%2010l1%201%203-3z%22%2F%3E%3C%2Fsvg%3E");
  }}

  /* ---- Inputs -------------------------------------------------------- */
  div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
  .stTextArea textarea {{
    background: {SURFACE_HI} !important;
    border-color: {BORDER} !important;
    border-radius: 8px !important;
  }}
  div[data-baseweb="select"] > div:hover {{ border-color: {BORDER_HI} !important; }}
  .stTextArea textarea {{ font-family: {MONO_STACK}; font-size: 0.82rem; }}
  div[data-testid="stFileUploader"] section {{
    background: {SURFACE_HI}; border: 1px dashed {BORDER_HI}; border-radius: 10px;
  }}

  /* ---- Tables -------------------------------------------------------- */
  div[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER}; border-radius: 10px; overflow: hidden;
  }}

  /* ---- Expanders ----------------------------------------------------- */
  div[data-testid="stExpander"] {{
    border: 1px solid {BORDER}; border-radius: 10px; background: {SURFACE};
  }}
  div[data-testid="stExpander"] summary:hover {{ color: {ACCENT}; }}

  /* ---- Radio / checkbox in main body --------------------------------- */
  div[data-testid="stAppViewContainer"] div[role="radiogroup"] {{ gap: 0.4rem; }}

  /* ---- Native captions ------------------------------------------------ */
  div[data-testid="stCaptionContainer"] {{
    color: {TEXT_MUTED} !important; line-height: 1.6; font-size: 0.86rem;
  }}

  /* ---- Footer -------------------------------------------------------- */
  .xf-footer {{
    color: {TEXT_FAINT}; font-size: 0.78rem; line-height: 1.7;
    border-top: 1px solid {BORDER}; padding-top: 1.1rem; margin-top: 3.5rem;
  }}
  .xf-footer b {{ color: {TEXT_MUTED}; font-weight: 600; }}

  /* ---- Motion: fast enough to feel responsive, slow enough to read ---- */
  .xf-stat, .xf-verdict, div[data-testid="stExpander"],
  div[data-baseweb="select"] > div, .stTextArea textarea {{
    transition: border-color 180ms ease, background 180ms ease,
                transform 180ms ease, box-shadow 180ms ease;
  }}
  .xf-stat:hover {{
    border-color: {BORDER_HI};
    transform: translateY(-2px);
    box-shadow: 0 6px 20px -8px rgba(0,0,0,0.65);
  }}
  div[data-testid="stExpander"]:hover {{ border-color: {BORDER_HI}; }}

  @media (prefers-reduced-motion: reduce) {{
    * {{ transition: none !important; animation: none !important; }}
    .xf-stat:hover {{ transform: none; }}
  }}

  /* ---- Focus visibility (keyboard nav) -------------------------------- */
  *:focus-visible {{
    outline: 2px solid {ACCENT} !important;
    outline-offset: 2px;
    border-radius: 4px;
  }}

  /* ---- Plotly containers ---------------------------------------------- */
  .js-plotly-plot .plotly .modebar {{
    background: transparent !important;
  }}
  .js-plotly-plot .plotly .modebar-btn path {{ fill: {TEXT_FAINT}; }}
  .js-plotly-plot .plotly .modebar-btn:hover path {{ fill: {ACCENT}; }}
  div[data-testid="stPlotlyChart"] {{
    border: 1px solid {BORDER};
    border-radius: 12px;
    background: {SURFACE};
    padding: 0.75rem 0.6rem 0.4rem 0.6rem;
  }}

  /* ---- Tabs ------------------------------------------------------------ */
  button[data-baseweb="tab"] {{
    font-size: 0.9rem !important;
    font-weight: 550 !important;
  }}
  div[data-baseweb="tab-highlight"] {{ background: {ACCENT} !important; }}

  /* ---- Scrollbar ----------------------------------------------------- */
  ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
  ::-webkit-scrollbar-track {{ background: {BG}; }}
  ::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 5px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: {BORDER_HI}; }}
</style>
"""


def apply_theme() -> None:
    """Inject the design system CSS. Call once, early, in app.py."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def section_header(eyebrow: str, title: str, lede: str = "") -> None:
    """Eyebrow + title + optional lede. Replaces bare st.title/st.caption so
    every section opens with the same visual rhythm."""
    html = f'<div class="xf-eyebrow">{eyebrow}</div><h1>{title}</h1>'
    if lede:
        html += f'<div class="xf-lede">{lede}</div>'
    st.markdown(html, unsafe_allow_html=True)


def subhead(title: str, lede: str = "") -> None:
    html = f'<div class="xf-subhead">{title}</div>'
    if lede:
        html += f'<div class="xf-lede">{lede}</div>'
    st.markdown(html, unsafe_allow_html=True)


def rule() -> None:
    st.markdown('<hr class="xf-rule">', unsafe_allow_html=True)


def stat(label: str, value: str, sub: str = "", tone: str = ACCENT, small: bool = False) -> None:
    """Custom metric card. Used instead of st.metric, which gives no control
    over the accent bar, value sizing, or sublabel."""
    cls = "xf-stat-value sm" if small else "xf-stat-value"
    sub_html = f'<div class="xf-stat-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="xf-stat" style="--tone:{tone}">'
        f'<div class="xf-stat-label">{label}</div>'
        f'<div class="{cls}">{value}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def pill_html(text: str, tone: str = ACCENT) -> str:
    return (
        f'<span class="xf-pill" style="color:{tone};border-color:{tone}55;'
        f'background:{tone}14">{text}</span>'
    )


def pills(items: list[tuple[str, str]]) -> None:
    st.markdown("".join(pill_html(t, c) for t, c in items), unsafe_allow_html=True)


def callout(body: str, tone: str = ACCENT) -> None:
    st.markdown(
        f'<div class="xf-callout" style="color:{TEXT};border-color:{tone}44;'
        f'border-left-color:{tone};background:{tone}0f">{body}</div>',
        unsafe_allow_html=True,
    )


def verdict(name: str, meta: str, tone: str) -> None:
    st.markdown(
        f'<div class="xf-verdict" style="--tone:{tone}">'
        f'<div class="xf-verdict-name">{name}</div>'
        f'<div class="xf-verdict-meta">{meta}</div></div>',
        unsafe_allow_html=True,
    )


def sidebar_brand() -> None:
    st.sidebar.markdown(
        '<div class="xf-brand">XFed<span>·</span>IDS</div>'
        '<div class="xf-brand-sub">Explainable Federated<br>Intrusion Detection</div>'
        '<div class="xf-navlabel">Sections</div>',
        unsafe_allow_html=True,
    )


def sidebar_footer() -> None:
    st.sidebar.markdown(
        f'<div style="margin-top:1.4rem;padding-top:1rem;'
        f'border-top:1px solid {BORDER};font-size:0.74rem;color:{TEXT_FAINT};'
        f'line-height:1.6">'
        f'<b style="color:{TEXT_MUTED}">Phase 1 demo</b><br>'
        f'Precomputed artifacts only. No live training, no SHAP computed '
        f'on demand.</div>',
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        '<div class="xf-footer">'
        "<b>XFed-IDS</b> — Explainable Federated Intrusion Detection with "
        "Cross-Domain Generalization &nbsp;·&nbsp; VIT-AP capstone<br>"
        "<b>Data</b> Distrinet corrected CIC-IDS2017 v4 (Liu et al., IEEE CNS "
        "2022; extending Engelen et al., WTMC 2021) &nbsp;·&nbsp; "
        "<b>Model</b> XFedMLP [128, 64], LayerNorm, StandardScaler, "
        "effective-number weighting β=0.999<br>"
        "<b>Federation</b> Flower · FedAvg · 10 silos · Dirichlet α ∈ "
        "{0.1, 0.5, 5.0} × 3 seeds &nbsp;·&nbsp; "
        "<b>Explanations</b> SHAP GradientExplainer, client-side<br>"
        "All figures read precomputed artifacts. See <b>Methods &amp; "
        "Limits</b> for stated limitations."
        "</div>",
        unsafe_allow_html=True,
    )
