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
# PREMIUM CSS
# ==========================================
def apply_premium_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
        
        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        .stApp {
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
            color: #FFFFFF;
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
        div[data-testid="stToolbar"] {display: none;}
        
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
        }
        
        .auth-version {
            text-align: center;
            margin-top: 24px;
            color: #6B7280;
            font-size: 0.75rem;
            font-weight: 500;
            letter-spacing: 1px;
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
        
        .social-divider {
            text-align: center;
            color: #9CA3AF;
            font-size: 12px;
            font-weight: 600;
            margin: 32px 0 24px 0;
            position: relative;
            letter-spacing: 1px;
        }
        
        .social-divider::before, .social-divider::after {
            content: "";
            position: absolute;
            top: 50%;
            width: 40%;
            height: 1px;
            background: rgba(255, 255, 255, 0.12);
        }
        
        .social-divider::before { left: 0; }
        .social-divider::after { right: 0; }
        
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
        
        .metric-change { font-size: 0.95rem; font-weight: 700; }
        .metric-positive { color: #10B981; }
        .metric-negative { color: #EF4444; }
        
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
        }
        
        .stock-symbol {
            font-size: 1.4rem;
            font-weight: 900;
            color: #FF6B6B;
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
        }
        
        .stSlider > label {
            color: #E5E7EB !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }
        
        .archive-card {
            background: rgba(25, 30, 45, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 20px 24px;
            margin-bottom: 16px;
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
# GOOGLE SHEETS
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
            return client.open("StockWatcherDB").worksheet(sheet_name)
        except: 
            return None
    return None

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def add_user_to_db(email, password, phone):
    sheet = get_worksheet("USERS")
    if not sheet: 
        return False
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and 'email' in df.columns and email in df['email'].values:
            st.warning("User already exists.")
            return False
    except: 
        pass
    hashed_pw = make_hashes(password)
    row = [email, hashed_pw, str(datetime.now()), phone]
    sheet.append_row(row)
    return True

def login_user(email, password):
    sheet = get_worksheet("USERS")
    if not sheet: 
        return False
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: 
            return False
        user_row = df[df['email'] == email]
        if user_row.empty: 
            return False
        stored_hash = user_row.iloc[0]['password']
        if check_hashes(password, stored_hash): 
            return True
    except: 
        pass
    return False

# ==========================================
# MARKET DATA
# ==========================================
@st.cache_data(ttl=60)
def get_market_metrics():
    tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "Bitcoin": "BTC-USD", "VIX": "^VIX"}
    data = {}
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            h = t.history(period="5d")
            if len(h) >= 2:
                curr = h['Close'].iloc[-1]
                prev = h['Close'].iloc[-2]
                chg = ((curr - prev) / prev) * 100
                data[name] = (curr, chg)
            else: 
                data[name] = (0.0, 0.0)
        except: 
            data[name] = (0.0, 0.0)
    return data

def get_real_time_price(symbol):
    if not symbol: 
        return None
    try: 
        return yf.Ticker(symbol).history(period="1d")['Close'].iloc[-1]
    except: 
        return None

def save_alert(ticker, min_p, max_p, vol, one_time):
    sheet = get_worksheet("Rules")
    if not sheet: 
        return
    row = [
        st.session_state.user_email, 
        ticker, 
        min_p if min_p>0 else "", 
        max_p if max_p>0 else "", 
        vol, 
        str(datetime.now()), 
        "TRUE" if one_time else "FALSE", 
        "Active"
    ]
