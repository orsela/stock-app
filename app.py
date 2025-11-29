"""Stock Alerts v5.1 - Fixed HTML Rendering"""
import streamlit as st
import json, os, hashlib, time
import yfinance as yf
from datetime import datetime

# --- הגדרת עמוד ---
st.set_page_config(page_title="StockWatcher", page_icon="📈", layout="wide")

# ==========================================
#              ניהול THEME (יום/לילה)
# ==========================================

if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

def toggle_theme():
    st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'

# הגדרת צבעים
if st.session_state.theme == 'dark':
    BG_COLOR = "#0e1117"
    CARD_BG = "#1e293b"
    TEXT_COLOR = "#ffffff"
    BTN_ICON = "☀️"
    BORDER_COLOR = "#333333"
else:
    BG_COLOR = "#f8f9fa"
    CARD_BG = "#ffffff"
    TEXT_COLOR = "#000000"
    BTN_ICON = "🌙"
    BORDER_COLOR = "#e0e0e0"

# CSS מתוקן ומהודק
st.markdown(f"""
<style>
    .stApp {{
        background-color: {BG_COLOR};
        color: {TEXT_COLOR};
    }}
    
    /* Login Card Container */
    .login-container {{
        background-color: {CARD_BG};
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 1px solid {BORDER_COLOR};
        text-align: center;
        max-width: 400px;
        margin: 2rem auto;
    }}
    
    /* Headers */
    .login-header {{
        color: {TEXT_COLOR};
        font-family: sans-serif;
        font-weight: 700;
        margin-top: 10px;
        font-size: 1.5rem;
    }}
    
    .login-sub {{
        color: {TEXT_COLOR};
        opacity: 0.7;
        margin-bottom: 20px;
        font-size: 0.9rem;
    }}

    /* Google Button Fake */
    .google-btn-link {{
        text-decoration: none; 
    }}
    
    .google-btn-style {{
        display: flex;
        align-items: center;
        justify-content: center;
