"""Streamlit multipage entry for Analysis (handover 2.0).

Prefer the live app's Analytics → Analysis tab; this page is the drop-in map target.
"""

from pathlib import Path

import streamlit as st

from ovadue.analysis_ui import render_analysis

ROOT = Path(__file__).resolve().parent.parent

st.set_page_config(page_title="Analysis · OvaDue", layout="wide")
render_analysis(ROOT)
