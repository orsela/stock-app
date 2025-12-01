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
# 1. CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="StockPulse Terminal",
    layout="wide",
    page_icon="💹",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. TERMINAL CSS (The Design Layer)
# ==========================================
def apply_terminal_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&display=swap');
        
        .stApp { background-color: #000000; color: #FFFFFF; font-family: 'Inter', sans-serif; }
        #MainMenu, footer, header, .stDeployButton {visibility: hidden;}

        h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel { color: #FFFFFF !important; opacity: 1 !important; }
        
        /* Logo Styling */
        .dashboard-logo { font-size: 2.2rem; font-weight: 900; color: #FFFFFF; margin: 0; letter-spacing: -1px; line-height: 1; }
        .dashboard-sub { font-family: 'JetBrains Mono', monospace; color: #FF7F50; font-size: 0.8rem; letter-spacing: 1px; }
        .logo-title { font-size: 3rem; font-weight: 900; text-align: center; margin-bottom: 5px; }
        
        /* Inputs & Buttons */
        .stTextInput > div > div > input, .stNumberInput > div > div > input {
            background-color: #111 !important; border: 1px solid #333 !important; color: #FFFFFF !important;
            font-family: 'JetBrains Mono', monospace !important; font-weight: 700; font-size: 1.1rem;
        }
        .stButton > button {
            background-color: #FF7F50 !important; color: #000000 !important; border: none !important;
            font-weight: 800 !important; border-radius: 4px !important; text-transform: uppercase; font-size: 1rem;
        }
        .stButton > button:hover { background-color: #FF6347 !important; transform: scale(1.02); }

        /* Widgets */
        .ticker-wrap { width: 100%; overflow: hidden; background-color: #111; border-bottom: 1px solid #333; padding: 10px 0; margin-bottom: 20px; white-space: nowrap; }
        .ticker-move { display: inline-block; animation: ticker 35s linear infinite; }
        .ticker-item { display: inline-block; padding: 0 2rem; font-family: 'JetBrains Mono', monospace; font-size: 1rem; color: #00FF00; }
        @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

        .stock-header { font-size: 2.5rem; font-weight: 900; color: #FF7F50; margin: 0; }
        .stock-price-lg { font-size: 2rem; font-family: 'JetBrains Mono'; font-weight: 700; }
        .ma-box { background: #222; border: 1px solid #444; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. STATE INITIALIZATION
# ==========================================
if 'page' not in st.session_state: st.session_state['page'] = 'auth'
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None
if 'target_price' not in st.session_state: st.session_state['target_price'] = 0.0

# ==========================================
# 4. BACKEND INTEGRATION
# ==========================================
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # Fallback for local testing if secrets.toml isn't set up
            try:
                creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
            except:
                return None
        return gspread.authorize(creds)
    except: return None

def get_worksheet(sheet_name):
    client = get_client()
    if client:
        try: return client.open("StockWatcherDB").worksheet(sheet_name)
        except: return None
    return None

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

def add_user_to_db(email, password, phone):
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and 'email' in df.columns and email in df['email'].values:
            return False
    except: pass
    row = [email, make_hashes(password), str(datetime.now()), phone]
    try: sheet.append_row(row); return True
    except: return False

def login_user(email, password):
    # Dummy login for testing if DB fails - REMOVE IN PRODUCTION IF DB IS STABLE
    if email == "admin" and password == "admin": return True 
    
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        data = sheet.get_all_records()
        if not data: return False
        df = pd.DataFrame(data)
        if 'email' not in df.columns: return False
        user = df[df['email'] == email]
        if user.empty: return False
        if check_hashes(password, user.iloc[0]['password']): return True
    except: pass
    return False

# --- Helper for safe data extraction ---
def safe_float(val):
    try: return float(val)
    except: return 0.0

@st.cache_data(ttl=30)
def get_top_metrics():
    tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "BTC": "BTC-USD", "VIX": "^VIX"}
    data = {}
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            h = t.history(period="2d")
            if len(h) >= 2:
                curr = h['Close'].iloc[-1]
                prev = h['Close'].iloc[-2]
                chg = ((curr - prev) / prev) * 100
                data[name] = (curr, chg)
            else: data[name] = (0,0)
        except: data[name] = (0,0)
    return data

@st.cache_data(ttl=60)
def get_stock_analysis(symbol):
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="1y")
        if hist.empty: return None
        current = hist['Close'].iloc[-1]
        ma150 = 0.0
        if len(hist) >= 150:
            ma150 = hist['Close'].rolling(window=150).mean().iloc[-1]
        return {"price": current, "ma150": ma150, "hist": hist, "symbol": symbol}
    except: return None

# פונקציה מנוטרלת זמנית (Stub)
def save_alert(email, symbol, target):
    # TODO: Implement full logic later
    pass 

# ==========================================
# 5. UI & MAIN LOGIC (Clean Version)
# ==========================================

def login_page():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="logo-title">StockPulse</div>', unsafe_allow_html=True)
        st.write("---")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if login_user(email, password):
                st.session_state['logged_in'] = True
                st.session_state['user_email'] = email
                st.rerun()
            else:
                st.error("Login Failed")
 
def main_dashboard():
    # --- 1. Top Ticker Animation ---
    # רשימת מניות לדוגמה שרצה למעלה
    st.markdown("""
        <div class="ticker-wrap">
        <div class="ticker-move">
            <div class="ticker-item">AAPL 185.92 (+1.2%)</div>
            <div class="ticker-item">TSLA 240.50 (-0.8%)</div>
            <div class="ticker-item">NVDA 490.10 (+2.1%)</div>
            <div class="ticker-item">GOOGL 138.40 (+0.5%)</div>
            <div class="ticker-item">AMZN 152.12 (-0.3%)</div>
            <div class="ticker-item">MSFT 380.20 (+1.1%)</div>
            <div class="ticker-item">BTC-USD 42,500 (+3.5%)</div>
        </div>
        </div>
    """, unsafe_allow_html=True)

    # --- 2. Main Layout ---
    st.markdown('<div class="logo-title">StockPulse Terminal</div>', unsafe_allow_html=True)
    
    # שורת חיפוש
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        symbol = st.text_input("SYMBOL SEARCH (e.g. TSLA, NVDA)", value="SPY").upper()
    
    # --- 3. Data Fetching & Visualization ---
    if symbol:
        data = get_stock_analysis(symbol)
        
        if data:
            # תצוגת מחיר ראשית
            st.markdown(f"""
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: #FF7F50; margin:0;">{symbol}</h2>
                <div class="stock-price-lg">${data['price']:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # גרף נרות (Candlestick)
            fig = go.Figure(data=[go.Candlestick(
                x=data['hist'].index,
                open=data['hist']['Open'],
                high=data['hist']['High'],
                low=data['hist']['Low'],
                close=data['hist']['Close'],
                name=symbol
            )])
            
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=500,
                margin=dict(l=0, r=0, t=20, b=0),
                xaxis_rangeslider_visible=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # --- 4. Trading Controls (Buy/Sell Simulation) ---
            st.write("---")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.info(f"MA150: ${data['ma150']:.2f}")
            with c2:
                # כפתור שמירת התראה (כרגע רק ויזואלי)
                if st.button(f"SET ALERT FOR {symbol}"):
                    st.success(f"Alert set for {symbol} (Simulation)")
            with c3:
                st.metric("Volume", f"{data['hist']['Volume'].iloc[-1]:,}")

        else:
            st.error(f"Could not find data for {symbol}. Check spelling.")

# --- Main Execution Block ---
apply_terminal_css()

if not st.session_state['logged_in']:
    login_page()
else:
    main_dashboard()

