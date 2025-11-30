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
# APP CONFIG
# ==========================================
st.set_page_config(
    page_title="StockPulse Terminal",
    layout="wide",
    page_icon="💹",
    initial_sidebar_state="collapsed"
)

# ==========================================
# BLOOMBERG / TERMINAL CSS
# ==========================================
def apply_terminal_css():
    st.markdown("""
        <style>
        /* יבוא פונטים: Inter לטקסט, JetBrains Mono למספרים */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
        
        :root {
            --primary-orange: #FF7F50;
            --terminal-bg: #000000;
            --card-bg: #121212;
            --border-color: #333333;
            --text-gray: #B0B0B0;
        }

        /* --- Global Reset --- */
        .stApp {
            background-color: var(--terminal-bg);
            color: #FFFFFF;
            font-family: 'Inter', sans-serif;
        }
        
        /* הסתרת אלמנטים של Streamlit */
        #MainMenu, footer, header, .stDeployButton, div[data-testid="stToolbar"] {visibility: hidden;}

        /* --- Typography --- */
        .logo-title {
            font-family: 'Inter', sans-serif;
            font-size: 3.5rem; 
            font-weight: 900;
            color: #FFFFFF;
            text-transform: uppercase;
            letter-spacing: -2px;
            margin-bottom: 0;
            line-height: 1;
        }
        .logo-subtitle {
            font-family: 'JetBrains Mono', monospace;
            color: var(--primary-orange);
            font-size: 0.9rem;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 40px;
        }
        
        /* מספרים בטרמינל תמיד בפונט מונוספייס */
        .metric-value, .stock-price, .input-number {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* --- Tabs (טרמינל סטייל - קווים חדים) --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            background: transparent;
            border: none;
            color: var(--text-gray);
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            border-radius: 0px; /* חדות */
        }
        .stTabs [aria-selected="true"] {
            color: var(--primary-orange) !important;
            border-bottom: 2px solid var(--primary-orange);
            background: rgba(255, 127, 80, 0.1);
        }

        /* --- Inputs (שדות קלט) --- */
        .stTextInput > div > div > input, .stNumberInput > div > div > input {
            background-color: #1A1A1A !important;
            border: 1px solid var(--border-color) !important;
            color: #FFF !important;
            border-radius: 4px !important; /* רדיוס קטן למראה מקצועי */
            font-family: 'JetBrains Mono', monospace !important; /* קלט כמספרים */
        }
        .stTextInput > div > div > input:focus {
            border-color: var(--primary-orange) !important;
        }

        /* --- Buttons (כתום חזק, פינות חדות) --- */
        .stButton > button {
            background-color: var(--primary-orange) !important;
            color: #000 !important; /* טקסט שחור על כתום לקריאות מקסימלית */
            border: none !important;
            border-radius: 4px !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 12px 0 !important;
            transition: all 0.2s;
        }
        .stButton > button:hover {
            filter: brightness(1.1);
            transform: translateY(-1px);
        }

        /* --- Social Buttons (עיצוב מיוחד מרובע) --- */
        /* Google - Col 2 */
        div[data-testid="column"]:nth-of-type(2) div.stButton > button {
            background-color: #FFF !important;
            border-radius: 6px !important;
            /* שימוש בטקסט גרדיאנט */
            background-image: -webkit-linear-gradient(45deg, #4285F4, #DB4437, #F4B400, #0F9D58) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            font-size: 24px !important; 
            font-weight: 900 !important;
            height: 55px !important;
        }
        /* Apple - Col 3 */
        div[data-testid="column"]:nth-of-type(3) div.stButton > button {
            background-color: #FFF !important;
            color: #000 !important;
            border-radius: 6px !important;
            font-size: 24px !important;
            height: 55px !important;
        }
        /* LinkedIn - Col 4 */
        div[data-testid="column"]:nth-of-type(4) div.stButton > button {
            background-color: #0077b5 !important; /* תכלת לינקדאין */
            color: #FFF !important;
            border-radius: 6px !important;
            font-size: 24px !important;
            height: 55px !important;
        }

        /* --- Cards & Dashboard Elements --- */
        .metric-box {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 15px;
            text-align: center;
            border-radius: 4px; /* חדות */
        }
        .metric-title { color: var(--text-gray); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; }
        .metric-val { font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: #fff; margin: 5px 0; }
        
        .stock-card {
            background-color: #0A0A0A;
            border-left: 3px solid var(--primary-orange);
            border-top: 1px solid #222;
            border-right: 1px solid #222;
            border-bottom: 1px solid #222;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 2px; /* כמעט ישר */
        }
        .divider-text { text-align: center; color: #555; font-size: 0.8rem; text-transform: uppercase; margin: 30px 0; }
        
        /* Ticker Tape Animation */
        .ticker-wrap {
            width: 100%;
            overflow: hidden;
            background-color: #111;
            border-bottom: 1px solid #333;
            padding: 8px 0;
            margin-bottom: 20px;
            white-space: nowrap;
        }
        .ticker-move { display: inline-block; animation: ticker 30s linear infinite; }
        .ticker-item { display: inline-block; padding: 0 2rem; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #888; }
        @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

        </style>
    """, unsafe_allow_html=True)

# ==========================================
# SESSION & AUTH
# ==========================================
if 'page' not in st.session_state: st.session_state['page'] = 'auth'
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

# --- Google Sheets ---
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
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
        if not df.empty and 'email' in df.columns:
            if email in df['email'].values:
                st.warning("User exists")
                return False
    except: pass
    row = [email, make_hashes(password), str(datetime.now()), phone]
    try: sheet.append_row(row); return True
    except: return False

def login_user(email, password):
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

# ==========================================
# DATA & LOGIC
# ==========================================
@st.cache_data(ttl=60)
def get_market_metrics():
    tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "BTC": "BTC-USD", "VIX": "^VIX"}
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
            else: data[name] = (0.0, 0.0)
        except: data[name] = (0.0, 0.0)
    return data

def get_real_time_price(symbol):
    try: return yf.Ticker(symbol).history(period="1d")['Close'].iloc[-1]
    except: return None

def save_alert(ticker, min_p, max_p, vol, one_time):
    sheet = get_worksheet("Rules")
    if not sheet: 
        st.error("Connection Lost")
        return
    row = [
        st.session_state.user_email, ticker, 
        min_p if min_p > 0 else "", max_p if max_p > 0 else "", 
        vol, str(datetime.now()), "TRUE" if one_time else "FALSE", "Active"
    ]
    try:
        sheet.append_row(row)
        st.toast(f"Order Placed: {ticker}", icon="📟")
        time.sleep(1)
        st.rerun()
    except Exception as e: st.error(f"Error: {e}")

def navigate_to(page): st.session_state['page'] = page; st.rerun()

def show_chart(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1mo")
        fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except: st.caption("No Data")

# ==========================================
# PAGES
# ==========================================
def auth_page():
    col_img, col_form = st.columns([1.5, 1])
    
    with col_img:
        try: st.image("login_image.png", use_container_width=True)
        except: st.warning("Missing: login_image.png")

    with col_form:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="logo-title">STOCKPULSE</div>', unsafe_allow_html=True)
        st.markdown('<div class="logo-subtitle">TERMINAL ACCESS v2.0</div>', unsafe_allow_html=True)
        
        tab_login, tab_signup = st.tabs(["LOG IN", "REQUEST ACCESS"])
        
        with tab_login:
            l_email = st.text_input("USER ID (EMAIL)", key="l_email")
            l_pass = st.text_input("PASSWORD", type="password", key="l_pass")
            st.markdown('<div style="text-align:right; color:#666; font-size:0.7rem; cursor:pointer; margin-bottom:15px;">RECOVER PASSWORD</div>', unsafe_allow_html=True)
            
            if st.button("AUTHENTICATE"):
                if login_user(l_email, l_pass):
                    st.session_state.user_email = l_email
                    st.session_state.logged_in = True
                    navigate_to('dashboard')
                else: st.error("ACCESS DENIED")
            
            st.markdown('<div class="divider-text">ALTERNATIVE LOGIN</div>', unsafe_allow_html=True)
            gap1, col_g, col_a, col_l, gap2 = st.columns([2, 1, 1, 1, 2])
            with col_g: st.button("G", key="g_btn")
            with col_a: st.button("", key="a_btn")
            with col_l: st.button("in", key="l_btn")

        with tab_signup:
            s_email = st.text_input("EMAIL", key="s_email")
            s_pass = st.text_input("PASSWORD", type="password", key="s_pass")
            s_phone = st.text_input("WHATSAPP (INTL FORMAT)", placeholder="+972...", key="s_phone")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("SUBMIT APPLICATION"):
                if add_user_to_db(s_email, s_pass, s_phone):
                    st.success("ID Created.")
                else: st.error("Error")

def dashboard_page():
    # Ticker Tape Effect
    st.markdown("""
    <div class="ticker-wrap">
    <div class="ticker-move">
    <div class="ticker-item">NASDAQ +0.65%</div><div class="ticker-item">S&P 500 +0.54%</div><div class="ticker-item">BTC $91,427</div><div class="ticker-item">NVDA $135.20</div><div class="ticker-item">TSLA $350.10</div><div class="ticker-item">EUR/USD 1.05</div>
    </div></div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([6, 1])
    with c1: st.title("MARKET DASHBOARD")
    with c2: 
        if st.button("LOGOUT"):
            st.session_state.logged_in = False
            navigate_to('auth')
            
    metrics = get_market_metrics()
    m_cols = st.columns(4)
    keys = ["S&P 500", "NASDAQ", "BTC", "VIX"]
    for i, key in enumerate(keys):
        val, chg = metrics.get(key, (0,0))
        color = "#10B981" if chg >= 0 else "#FF4444"
        with m_cols[i]:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-title">{key}</div>
                <div class="metric-val">{val:,.2f}</div>
                <div style="color:{color}; font-family:'JetBrains Mono'; font-size:0.9rem;">{chg:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("---")

    col_setup, col_list = st.columns([1, 2])
    with col_setup:
        st.markdown("### 📟 NEW ALERT")
        with st.container(border=True):
            tick = st.text_input("SYMBOL", value="NVDA").upper()
            curr_price = 0.0
            if tick:
                curr_price = get_real_time_price(tick) or 0.0
                st.caption(f"LAST: ${curr_price:.2f}")

            st.markdown("<strong>TARGET</strong>", unsafe_allow_html=True)
            if 'slider_price' not in st.session_state: st.session_state.slider_price = curr_price
            
            input_val = st.number_input("PRICE", value=float(st.session_state.slider_price), label_visibility="collapsed")
            s_min = float(curr_price) * 0.5
            s_max = float(curr_price) * 1.5
            if s_max == 0: s_max = 100.0
            final_target = st.slider("FINE TUNE", min_value=s_min, max_value=s_max, value=input_val)
            
            st.markdown("---")
            min_vol = st.number_input("MIN VOL (M)", value=5, step=1)
            
            if st.button("ACTIVATE ALERT"):
                if tick:
                    min_p = final_target if final_target < curr_price else 0
                    max_p = final_target if final_target > curr_price else 0
                    save_alert(tick, min_p, max_p, min_vol*1000000, True)

    with col_list:
        h1, h2 = st.columns([4, 1])
        with h1: st.markdown("### 📋 WATCHLIST")
        with h2: 
            if st.button("ARCHIVE"): navigate_to('archive')

        sh = get_worksheet("Rules")
        if sh:
            try:
                data = sh.get_all_records()
                if data:
                    df = pd.DataFrame(data)
                    uc = 'user_email' if 'user_email' in df.columns else 'email'
                    if uc in df.columns and 'status' in df.columns:
                        my_df = df[(df[uc] == st.session_state.user_email) & (df['status'] == 'Active')]
                        if not my_df.empty:
                            grid = st.columns(2)
                            for i, (idx, row) in enumerate(my_df.iterrows()):
                                with grid[i % 2]:
                                    mp = row.get('max_price'); mnp = row.get('min_price')
                                    try: target = float(mp) if mp else float(mnp)
                                    except: target = 0
                                    vol = str(row.get('min_volume', 0))[:2]
                                    
                                    st.markdown(f"""
                                    <div class="stock-card">
                                        <div style="display:flex; justify-content:space-between;">
                                            <span style="font-weight:900; font-size:1.2rem; color:#FF7F50;">{row['symbol']}</span>
                                            <span style="font-family:'JetBrains Mono'; color:#666;">VOL {vol}M</span>
                                        </div>
                                        <div style="font-family:'JetBrains Mono'; font-size:1.1rem; margin-top:5px;">${target}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    with st.expander("CHART"): show_chart(row['symbol'])
                        else: st.info("NO ACTIVE ALERTS")
            except Exception as e: st.error(str(e))

def archive_page():
    st.title("🗄️ LOGS")
    if st.button("BACK"): navigate_to('dashboard')
    st.markdown("---")
    sh = get_worksheet("Rules")
    if sh:
        try:
            df = pd.DataFrame(sh.get_all_records())
            if not df.empty and 'user_email' in df.columns:
                adf = df[(df['user_email'] == st.session_state.user_email) & (df['status'] != 'Active')]
                for i, row in adf.iterrows():
                    st.markdown(f"""
                    <div style="border-bottom:1px solid #333; padding:10px;">
                        <span style="color:#FF7F50; font-weight:bold;">{row['symbol']}</span> 
                        <span style="color:#666; font-size:0.8rem; margin-left:10px;">{row['created_at']}</span>
                        <span style="float:right; font-family:'JetBrains Mono';">{row['status']}</span>
                    </div>
                    """, unsafe_allow_html=True)
        except: pass

# ==========================================
# RUN
# ==========================================
apply_terminal_css()

if st.session_state.logged_in:
    if st.session_state['page'] == 'archive': archive_page()
    else: dashboard_page()
else:
    auth_page()
