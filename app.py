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
# CONFIG & SETUP
# ==========================================
st.set_page_config(page_title="StockPulse", page_icon="📈", layout="wide")

# ==========================================
# CUSTOM CSS - ORIGINAL WORKING VERSION
# ==========================================
def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700;900&display=swap');
        
        .stApp {
            background-color: #000000;
            font-family: 'Roboto', sans-serif;
            color: #FFFFFF;
        }
        
        .main-title {
            font-size: 3.5rem;
            font-weight: 900;
            color: #FFFFFF !important;
            opacity: 1 !important;
            line-height: 1.1;
            text-shadow: 0px 0px 10px rgba(0,0,0,0.5);
        }
        
        .sub-title {
            font-size: 1.2rem;
            color: #E0E0E0 !important;
            font-weight: 400;
            margin-bottom: 30px;
        }
        
        .divider-text {
            text-align: center;
            color: #BBBBBB;
            font-size: 0.9rem;
            margin: 30px 0 20px 0;
        }

        div[data-testid="stTextInput"] > div > div {
            background-color: #F0F2F6 !important;
            border-radius: 8px;
            border: none;
            color: #333 !important;
        }
        
        input[type="text"], input[type="password"] {
            color: #333 !important;
        }
        
        div.stButton > button {
            background-color: #FF7F50; 
            color: white;
            border-radius: 8px;
            border: none;
            padding: 12px 0;
            font-weight: bold;
            font-size: 16px;
            width: 100%;
            transition: 0.3s;
        }
        
        div.stButton > button:hover {
            background-color: #FF6347;
            box-shadow: 0px 0px 15px rgba(255, 127, 80, 0.5);
        }

        .stTabs [data-baseweb="tab-list"] { 
            gap: 20px; 
            margin-bottom: 20px; 
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px; 
            white-space: pre-wrap; 
            background-color: transparent;
            border-radius: 0px; 
            color: #888; 
            font-size: 1.2rem; 
            font-weight: 700; 
            border: none;
        }
        
        .stTabs [aria-selected="true"] {
            color: #FF7F50 !important; 
            border-bottom: 3px solid #FF7F50;
        }

        .stock-card {
            background: linear-gradient(135deg, rgba(40, 40, 60, 0.6) 0%, rgba(30, 30, 45, 0.6) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
            transition: all 0.3s ease;
        }
        
        .stock-card:hover {
            border-color: #FF6B6B;
            transform: translateX(4px);
            box-shadow: -4px 0 20px rgba(255, 107, 107, 0.2);
        }
        
        .archive-card {
            background: rgba(30, 30, 45, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s ease;
        }
        
        .archive-card:hover {
            background: rgba(40, 40, 60, 0.6);
            border-color: rgba(255, 107, 107, 0.3);
        }
        
        .version-badge {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(15, 20, 30, 0.95);
            border: 1px solid rgba(255, 107, 107, 0.3);
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 0.7rem;
            font-weight: 600;
            color: #FF6B6B;
            z-index: 9999;
        }

        #MainMenu {visibility: hidden;} 
        footer {visibility: hidden;} 
        header {visibility: hidden;}
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
    if make_hashes(password) == hashed_text: 
        return hashed_text
    return False

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
    row = [st.session_state.user_email, ticker, min_p if min_p>0 else "", max_p if max_p>0 else "", vol, str(datetime.now()), "TRUE" if one_time else "FALSE", "Active"]
    try:
        sheet.append_row(row)
        st.toast(f"✅ Alert Set: {ticker}", icon="🔥")
        time.sleep(1)
        st.rerun()
    except Exception as e: 
        st.error(f"Save Error: {e}")

def navigate_to(page):
    st.session_state['page'] = page
    st.rerun()

def show_chart(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1mo")
        fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
        fig.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except: 
        st.caption("Chart unavailable")

# ==========================================
# AUTH PAGE
# ==========================================
def auth_page():
    col_img, col_form = st.columns([1.5, 1])
    
    with col_img:
        try: 
            st.image("login_image.png", use_container_width=True)
        except: 
            st.warning("Image 'login_image.png' not found.")

    with col_form:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="main-title">STOCKPULSE</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-title">Real-Time Market Alerts</div>', unsafe_allow_html=True)
        
        tab_login, tab_signup = st.tabs(["LOG IN", "SIGN UP"])
        
        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            l_email = st.text_input("Email Address", key="l_email")
            l_pass = st.text_input("Password", type="password", key="l_pass")
            
            st.markdown('<div style="text-align:right; color:#888; font-size:0.9rem; cursor:pointer;">Forgot Password?</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("LOG IN"):
                if login_user(l_email, l_pass):
                    st.session_state.user_email = l_email
                    st.session_state.logged_in = True
                    navigate_to('dashboard')
                else:
                    st.error("Invalid Credentials")
            
            st.markdown('<div class="divider-text">— OR CONTINUE WITH —</div>', unsafe_allow_html=True)
            
            gap1, col_g, col_a, col_l, gap2 = st.columns([2, 1, 1, 1, 2])
            
            with col_g: 
                st.button("G", key="social_g", help="Google")
            with col_a: 
                st.button("🍎", key="social_a", help="Apple")
            with col_l: 
                st.button("in", key="social_l", help="LinkedIn")

        with tab_signup:
            st.markdown("<br>", unsafe_allow_html=True)
            s_email = st.text_input("New Email", key="s_email")
            s_pass = st.text_input("Create Password", type="password", key="s_pass")
            s_phone = st.text_input("WhatsApp Number", placeholder="+972...", key="s_phone")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("CREATE ACCOUNT"):
                if add_user_to_db(s_email, s_pass, s_phone):
                    st.success("Account created successfully!")
                    time.sleep(1)
                    st.balloons()
        
        # VERSION INFO
        st.markdown(f'<div style="text-align:center; margin-top:24px; color:#6B7280; font-size:0.75rem;">{APP_VERSION} • {APP_BUILD_DATE}</div>', unsafe_allow_html=True)

# ==========================================
# DASHBOARD PAGE
# ==========================================
def dashboard_page():
    c1, c2 = st.columns([6, 1])
    with c1: 
        st.title("Dashboard")
    with c2: 
        if st.button("Log Out"):
            st.session_state.logged_in = False
            navigate_to('auth')
            
    metrics = get_market_metrics()
    m_cols = st.columns(4)
    keys = ["S&P 500", "NASDAQ", "Bitcoin", "VIX"]
    for i, key in enumerate(keys):
        val, chg = metrics.get(key, (0,0))
        color = "#00CC96" if chg >= 0 else "#EF553B"
        with m_cols[i]:
            st.markdown(f"""
            <div style="background:#111; padding:15px; border-radius:10px; text-align:center;
