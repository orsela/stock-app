import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import yfinance as yf
import hashlib
import plotly.graph_objects as go

# ==========================================
# APP VERSION
# ==========================================
APP_VERSION = "v2.1.0"
APP_BUILD_DATE = "30-Nov-2025"

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="StockPulse",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="collapsed"
)

# ==========================================
# PREMIUM CSS - COMPLETE & FIXED
# ==========================================
def apply_premium_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
        
        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* GLOBAL */
        .stApp {
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
            color: #FFFFFF;
        }
        
        /* REMOVE STREAMLIT BRANDING */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
        div[data-testid="stToolbar"] {display: none;}
        
        /* VERSION BADGE */
        .version-badge {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(15, 20, 30, 0.95);
            border: 1px solid rgba(255, 107, 107, 0.3);
            border-radius: 12px;
            padding: 8px 16px;
            font-size: 0.75rem;
            font-weight: 600;
            color: #FF6B6B;
            letter-spacing: 0.5px;
            z-index: 9999;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(10px);
        }
        
        .version-badge:hover {
            background: rgba(255, 107, 107, 0.1);
            border-color: #FF6B6B;
        }
        
        /* AUTH PAGE VERSION */
        .auth-version {
            text-align: center;
            margin-top: 24px;
            color: #6B7280;
            font-size: 0.75rem;
            font-weight: 500;
            letter-spacing: 1px;
        }
        
        /* ========================================
           AUTH PAGE - HIGH CONTRAST
        ======================================== */
        .auth-container {
            max-width: 440px;
            margin: 60px auto;
            padding: 48px 40px;
            background: rgba(15, 20, 30, 0.98);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(20px);
        }
        
        .logo-title {
            font-size: 3rem;
            font-weight: 900;
            background: linear-gradient(135deg, #FF6B6B 0%, #FFB88C 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            letter-spacing: -1.5px;
            margin-bottom: 8px;
        }
        
        .logo-subtitle {
            text-align: center;
            color: #B8BCC8;
            font-size: 1rem;
            font-weight: 500;
            letter-spacing: 0.5px;
            margin-bottom: 40px;
        }
        
        /* TABS - BETTER CONTRAST */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 4px;
            margin-bottom: 32px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 48px;
            background: transparent;
            border-radius: 10px;
            color: #9CA3AF;
            font-size: 15px;
            font-weight: 700;
            border: none;
            padding: 0 28px;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(255, 107, 107, 0.2) 0%, rgba(255, 184, 140, 0.2) 100%) !important;
            color: #FFFFFF !important;
            box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);
        }
        
        /* INPUT FIELDS - HIGH CONTRAST */
        .stTextInput > label {
            color: #E5E7EB !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            margin-bottom: 8px !important;
        }
        
        .stTextInput > div > div > input {
            background: rgba(255, 255, 255, 0.06) !important;
            border: 2px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 12px !important;
            color: #FFFFFF !important;
            padding: 14px 16px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
        }
        
        .stTextInput > div > div > input:focus {
            border: 2px solid #FF6B6B !important;
            background: rgba(255, 107, 107, 0.08) !important;
            box-shadow: 0 0 0 3px rgba(255, 107, 107, 0.15) !important;
        }
        
        /* PRIMARY BUTTON */
        .stButton > button {
            background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 16px 0 !important;
            font-weight: 700 !important;
            font-size: 15px !important;
            width: 100% !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            box-shadow: 0 8px 20px rgba(255, 107, 107, 0.35) !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 12px 28px rgba(255, 107, 107, 0.45) !important;
        }
        
        /* SOCIAL DIVIDER - HIGH CONTRAST */
        .social-divider {
            text-align: center;
            color: #9CA3AF;
            font-size: 12px;
            font-weight: 600;
            margin: 32px 0 24px 0;
            position: relative;
            letter-spacing: 1px;
        }
        
        .social-divider::before,
        .social-divider::after {
            content: "";
            position: absolute;
            top: 50%;
            width: 40%;
            height: 1px;
            background: rgba(255, 255, 255, 0.12);
        }
        
        .social-divider::before { left: 0; }
        .social-divider::after { right: 0; }
        
        /* ========================================
           DASHBOARD
        ======================================== */
        .dashboard-title {
            font-size: 2.2rem;
            font-weight: 900;
            color: #FFFFFF;
            letter-spacing: -1px;
        }
        
        /* METRIC CARDS */
        .metric-card {
            background: linear-gradient(135deg, rgba(25, 30, 45, 0.9) 0%, rgba(15, 20, 30, 0.95) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 24px 20px;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-6px);
            border-color: rgba(255, 107, 107, 0.4);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
        }
        
        .metric-label {
            color: #9CA3AF;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 12px;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 900;
            color: #FFFFFF;
            margin: 8px 0;
        }
        
        .metric-change {
            font-size: 0.95rem;
            font-weight: 700;
        }
        
        .metric-positive { color: #10B981; }
        .metric-negative { color: #EF4444; }
        
        /* ALERT PANEL */
        .alert-panel {
            background: linear-gradient(135deg, rgba(25, 30, 45, 0.95) 0%, rgba(15, 20, 30, 0.98) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 32px 28px;
            height: 100%;
        }
        
        .panel-title {
            font-size: 1.4rem;
            font-weight: 800;
            color: #FFFFFF;
            margin-bottom: 28px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        /* STOCK CARD */
        .stock-card {
            background: linear-gradient(135deg, rgba(35, 40, 60, 0.7) 0%, rgba(25, 30, 45, 0.9) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }
        
        .stock-card:hover {
            border-color: #FF6B6B;
            transform: translateX(4px);
            box-shadow: -4px 0 20px rgba(255, 107, 107, 0.25);
        }
        
        .stock-symbol {
            font-size: 1.4rem;
            font-weight: 900;
            color: #FF6B6B;
            margin: 0;
        }
        
        .stock-target {
            font-size: 1.1rem;
            color: #E5E7EB;
            margin-top: 8px;
        }
        
        .stock-volume {
            color: #9CA3AF;
            font-size: 0.85rem;
        }
        
        /* NUMBER INPUT */
        .stNumberInput > label {
            color: #E5E7EB !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }
        
        .stNumberInput > div > div > input {
            background: rgba(255, 255, 255, 0.06) !important;
            border: 2px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 12px !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }
        
        /* SLIDER */
        .stSlider > label {
            color: #E5E7EB !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }
        
        .stSlider > div > div > div > div {
            background: linear-gradient(90deg, #FF6B6B, #FFB88C) !important;
        }
        
        /* ARCHIVE CARD */
        .archive-card {
            background: rgba(25, 30, 45, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 20px 24px;
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .status-badge {
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        
        .status-triggered {
            background: rgba(16, 185, 129, 0.2);
            color: #10B981;
        }
        
        .status-expired {
            background: rgba(251, 146, 60, 0.2);
            color: #FB923C;
        }
        
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# SESSION STATE
# ==========================================
if 'page' not in st.session_state: 
    st.session_state['page'] = 'auth'
if 'logged_in' not in st.session_state: 
    st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: 
    st.session_state['user_email'] = None

# ==========================================
# GOOGLE SHEETS FUNCTIONS
# ==========================================
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        return gspread.authorize(creds)
    except: 
        return None

def get_worksheet(sheet_name):
    client = get_client()
    if client:
        try:
