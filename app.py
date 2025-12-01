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
# 2. DYNAMIC THEME CSS (Dark/Light mode)
# ==========================================
def apply_dynamic_css(dark_mode: bool):
    if dark_mode:
        css = """
        <style>
        .stApp {
            background-color: #000000 !important; 
            color: #FFFFFF !important;
            font-family: 'Inter', sans-serif;
        }
        #MainMenu, footer, header, .stDeployButton { visibility: hidden; }
        h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel {
            color: #FFFFFF !important;
            opacity: 1 !important;
        }
        .stTextInput > div > div > input, .stNumberInput > div > div > input {
            background-color: #111 !important; 
            border: 1px solid #333 !important; 
            color: #FFFFFF !important;
            font-family: 'JetBrains Mono', monospace !important; 
            font-weight: 700; 
            font-size: 1.1rem;
        }
        .stButton > button {
            background-color: #FF7F50 !important; 
            color: #000000 !important; 
            border: none !important;
            font-weight: 800 !important; 
            border-radius: 4px !important; 
            text-transform: uppercase;
            font-size: 1rem;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            background-color: #FF6347 !important;
            transform: scale(1.02);
        }
        .ticker-wrap {
            width: 100%;
            overflow: hidden;
            background-color: #111;
            border-bottom: 1px solid #333;
            padding: 10px 0;
            margin-bottom: 20px;
            white-space: nowrap;
        }
        .ticker-item { display: inline-block; padding: 0 2rem; }
        @keyframes ticker {
            0% { transform: translate3d(0,0,0);}
            100% { transform: translate3d(-100%,0,0);}
        }
        .metric-card {
            background-color: #1e1e1e;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #333;
            text-align: center;
            font-family: 'JetBrains Mono', monospace;
        }
        .sticky-note {
            background-color: #FFFFAA;
            border: 1px solid #CCCC00;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            box-shadow: 3px 3px 5px rgba(0,0,0,0.3);
            font-family: 'Permanent Marker', cursive;
            color: #003366;
            text-align: left;
        }
        .sticky-note-header {
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 5px;
            color: #003366;
            border-bottom: 1px dashed #003366;
            padding-bottom: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .sticky-note-footer {
            font-size: 0.8em;
            color: #003366;
            margin-top: auto;
            padding-top: 10px;
            border-top: 1px dashed #003366;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .rtl {
            direction: rtl;
            text-align: right;
            font-family: 'Inter', sans-serif;
        }
        </style>
        """
    else:
        css = """
        <style>
        .stApp {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            font-family: 'Inter', sans-serif;
        }
        h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel {
            color: #000000 !important;
            opacity: 1 !important;
        }
        .stTextInput > div > div > input, .stNumberInput > div > div > input {
            background-color: #FFF !important;
            border: 1px solid #CCC !important;
            color: #000 !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-weight: 700;
            font-size: 1.1rem;
        }
        .stButton > button {
            background-color: #FF7F50 !important;
            color: #000000 !important;
            border: none !important;
            font-weight: 800 !important;
            border-radius: 4px !important;
            text-transform: uppercase;
            font-size: 1rem;
        }
        .stButton > button:hover {
            background-color: #FF6347 !important;
            transform: scale(1.02);
        }
        .ticker-wrap {
            width: 100%;
            overflow: hidden;
            background-color: #EEE;
            border-bottom: 1px solid #AAA;
            padding: 10px 0;
            margin-bottom: 20px;
            white-space: nowrap;
        }
        .ticker-item { display: inline-block; padding: 0 2rem; }
        @keyframes ticker {
            0% { transform: translate3d(0,0,0);}
            100% { transform: translate3d(-100%,0,0);}
        }
        .metric-card {
            background-color: #eee;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #ccc;
            text-align: center;
            font-family: 'JetBrains Mono', monospace;
            color: #000;
        }
        .sticky-note {
            background-color: #FFFFCC;
            border: 1px solid #CCCC00;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-family: 'Permanent Marker', cursive;
            color: #004080;
            text-align: left;
            box-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .sticky-note-header {
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 5px;
            color: #004080;
            border-bottom: 1px dashed #004080;
            padding-bottom: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .sticky-note-footer {
            font-size: 0.8em;
            color: #004080;
            margin-top: auto;
            padding-top: 10px;
            border-top: 1px dashed #004080;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .rtl {
            direction: rtl;
            text-align: right;
            font-family: 'Inter', sans-serif;
        }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)

def apply_terminal_css():
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = True
    apply_dynamic_css(st.session_state.dark_mode)

# ==========================================
# 3. BACKEND HELPERS (DB + AUTH + DATA)
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
    salt = "stockpulse_2025_salt"
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def check_hashes(password, hashed_text):
    salt = "stockpulse_2025_salt"
    return make_hashes(password) == hashed_text

def add_user_to_db(email, password, phone):
    sheet = get_worksheet("USERS")
    if not sheet:
        return False
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and 'email' in df.columns and email in df['email'].values:
            return False
    except:
        pass
    row = [email, make_hashes(password), str(datetime.now()), phone]
    try:
        sheet.append_row(row)
        return True
    except:
        return False

def login_user(email, password):
    # BACKDOOR – כניסה ללא DB
    if email == "admin" and password == "123":
        return True
    if not email or not password:
        return False
    sheet = get_worksheet("USERS")
    if not sheet:
        return False
    try:
        data = sheet.get_all_records()
        if not data:
            return False
        df = pd.DataFrame(data)
        if 'email' not in df.columns:
            return False
        user = df[df['email'] == email]
        if user.empty:
            return False
        if check_hashes(password, user.iloc[0]['password']):
            return True
    except:
        return False

@st.cache_data(ttl=30)
def get_top_metrics():
    tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "BTC": "BTC-USD", "VIX": "^VIX"}
    data = {}
    try:
        all_data = yf.download(list(tickers.values()), period="2d", progress=False)
        for name, symbol in tickers.items():
            closes = all_data['Close'].get(symbol)
            if closes is not None and len(closes) >= 2:
                curr, prev = closes.iloc[-1], closes.iloc[-2]
                chg = ((curr - prev) / prev) * 100
                data[name] = (curr, chg)
            else:
                data[name] = (0, 0)
    except:
        for name in tickers:
            data[name] = (0, 0)
    return data

@st.cache_data(ttl=60)
def get_stock_analysis(symbol):
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="1y")
        if hist.empty:
            return None
        current = hist['Close'].iloc[-1]
        ma150 = hist['Close'].rolling(window=150).mean().iloc[-1] if len(hist) >= 150 else 0.0
        return {"price": current, "ma150": ma150, "hist": hist, "symbol": symbol}
    except:
        return None

def save_alert(ticker, min_p, max_p, vol, one_time):
    sheet = get_worksheet("Rules")
    if not sheet:
        st.error("DB Error")
        return
    row = [
        st.session_state.user_email, ticker,
        min_p if min_p > 0 else "",
        max_p if max_p > 0 else "",
        vol, str(datetime.now()), "TRUE" if one_time else "FALSE", "Active"
    ]
    try:
        sheet.append_row(row)
        st.toast(f"💾 Alert for {ticker} saved", icon="✅")
        st.rerun()
    except Exception as e:
        st.error(f"Save error: {str(e)[:100]}")

def render_chart(hist, title):
    if hist is None or hist.empty:
        st.warning("No chart data available")
        return
    fig = go.Figure(data=[go.Candlestick(
        x=hist.index,
        open=hist['Open'], high=hist['High'],
        low=hist['Low'], close=hist['Close']
    )])
    fig.update_layout(
        title=dict(text=title, font=dict(color='white')),
        height=350,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor='#000',
        plot_bgcolor='#000',
        font=dict(color='white'),
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

def test_yahoo_connection_cached() -> bool:
    try:
        data = yf.download("NVDA", period="1d", progress=False)
        if data.empty:
            return False
        return True
    except:
        return False

# ==========================================
# 4. UI PAGES
# ==========================================
def auth_page():
    apply_terminal_css()
    col_img, col_form = st.columns([1.5, 1])
    with col_img:
        try:
            st.image("https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME/main/assets/logo.png",
                     use_container_width=True)
        except:
            st.info("Welcome to StockPulse Terminal")

    with col_form:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="logo-title rtl">STOCKPULSE</div>', unsafe_allow_html=True)
        st.markdown('<div class="dashboard-sub rtl">TERMINAL ACCESS</div>', unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["כניסה", "הרשמה"])

        with tab_login:
            email = st.text_input("אימייל", placeholder="you@example.com", key="login_email")
            password = st.text_input("סיסמה", type="password", key="login_password")
            if st.button("התחבר", use_container_width=True):
                if login_user(email, password):
                    st.session_state['user_email'] = email
                    st.session_state['logged_in'] = True
                    st.session_state['page'] = 'dashboard'
                    st.rerun()
                else:
                    st.error("שם משתמש או סיסמה שגויים")
