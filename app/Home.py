from pathlib import Path
import sys

import streamlit as st


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from components import render_dashboard


st.set_page_config(
    page_title="BTS Song Atlas",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_dashboard()
