import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import yfinance as yf
import hashlib
import plotly.graph_objects as go
import re

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="StockPulse Terminal",
    layout="wide",
    page_icon="💹",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. CSS & DESIGN
# ==========================================
def apply_terminal_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&family=Permanent+Marker&display=swap');

    .stApp { background-color: #000000; color: #FFFFFF; font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header, .stDeployButton {visibility: hidden;}
    h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel { color: #FFFFFF !important; opacity: 1 !important; }
    
    .stTextInput > div > div > input, .stNumberInput > div > div > input {
        background-color: #111 !important; border: 1px solid #333 !important; color: #FFFFFF !important;
        font-family: 'JetBrains Mono', monospace !important; font-weight: 700; font-size: 1.1rem;
    }
    .stButton > button {
        background-color: #FF7F50 !important; color: #000000 !important; border: none !important;
        font-weight: 800 !important; border-radius: 4px !important; text-transform: uppercase; font-size: 1rem;
    }
    .stButton > button:hover { background-color: #FF6347 !important; transform: scale(1.02); }

    .rtl { direction
