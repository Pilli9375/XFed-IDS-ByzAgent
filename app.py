"""XFed-IDS Streamlit demo -- Phase 1.

Run from the project root (same folder as configs/, data/, results/,
federated/):

    streamlit run app.py

Reads precomputed artifacts only. Never retrains, and never computes SHAP
on demand -- explanations come from the .npz files written by
tools/centralized_shap_floor.py and tools/local_shap_pipeline.py. See
app_lib/loaders.py for the exact source of every number shown.
"""
from __future__ import annotations

import streamlit as st

from app_lib import theme
from app_lib.sections import (
    render_agreement,
    render_detect,
    render_explain,
    render_faithfulness,
    render_federation_status,
    render_methods,
)
from app_lib.trust_monitor import render_trust_monitor

st.set_page_config(
    page_title="XFed-IDS",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

theme.apply_theme()

SECTIONS = {
    "Federation Status": render_federation_status,
    "Detect": render_detect,
    "Explain": render_explain,
    "Explanation Agreement": render_agreement,
    "Faithfulness": render_faithfulness,
    "Methods & Limits": render_methods,
    "Client Trust Monitor": render_trust_monitor,
}

theme.sidebar_brand()
choice = st.sidebar.radio(
    "Section", list(SECTIONS.keys()), label_visibility="collapsed"
)
theme.sidebar_footer()

try:
    SECTIONS[choice]()
except FileNotFoundError as e:
    st.error(f"Missing artifact: {e}")
    st.info(
        "This section expects a file that isn't where the app looked for "
        "it. Check the path in app_lib/loaders.py against what's actually "
        "on disk, or send the real path back and it'll get fixed."
    )

theme.render_footer()
