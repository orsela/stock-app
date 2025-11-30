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
# APP VERSION & CONFIG
# ==========================================
APP_VERSION = "v2.1.0"
APP_BUILD_DATE = "30-Nov-2025"

st.set_page_config(
    page_title="StockPulse",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="collapsed"
)

# ==========================================
# PREMIUM CSS (כולל כפתורי סושיאל מתוקנים)
# ==========================================
def apply_premium_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
        
        * { font-family: 'Inter', sans-serif; }
        
        .stApp {
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
            color: #FFFFFF;
        }
        
        #MainMenu, footer, header, .stDeployButton, div[data-testid="stToolbar"] {visibility: hidden;}
        
        /* כותרות */
        .logo-title {
            font-size: 3rem; font-weight: 900;
            background: linear-gradient(135deg, #FF6B6B 0%, #FFB88C 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            text-align: center; letter-spacing: -1.5px; margin-bottom: 8px;
        }
        .logo-subtitle {
            text-align: center; color: #B8BCC8; font-size: 1rem;
            font-weight: 500; letter-spacing: 0.5px; margin-bottom: 40px;
        }
        
        /* טאבים */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0; background: rgba(255, 255, 255, 0.05);
            border-radius: 12px; padding: 4px; margin-bottom: 32px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 48px; background: transparent; border-radius: 10px;
            color: #9CA3AF; font-size: 15px; font-weight: 700; border: none; padding: 0 28px;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(255, 107, 107, 0.2) 0%, rgba(255, 184, 140, 0.2) 100%) !important;
            color: #FFFFFF !important;
            box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);
        }
        
        /* שדות קלט */
        .stTextInput > div > div > input {
            background: rgba(255, 255, 255, 0.06) !important;
            border: 2px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 12px !important; color: #FFFFFF !important;
        }
        
        /* כפתורים ראשיים (כתום) */
        .stButton > button {
            background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%) !important;
            color: #FFFFFF !important; border: none !important; border-radius: 12px !important;
            padding: 16px 0 !important; font-weight: 700 !important; font-size: 15px !important;
            width: 100% !important; text-transform: uppercase !important;
            box-shadow: 0 8px 20px rgba(255, 107, 107, 0.35) !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 12px 28px rgba(255, 107, 107, 0.45) !important;
        }

        /* --- עיצוב מיוחד לכפתורי סושיאל (מרובעים) --- */
        /* Google Button - 2nd Column */
        div[data-testid="column"]:nth-of-type(2) div.stButton > button {
            background: #FFFFFF !important;
            border: 1px solid #ddd !important;
            background-image: -webkit-linear-gradient(45deg, #4285F4, #DB4437, #F4B400, #0F9D58) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            font-size: 28px !important; font-weight: 900 !important;
            box-shadow: none !important; padding: 0 !important; height: 60px !important;
        }
        /* Apple Button - 3rd Column */
        div[data-testid="column"]:nth-of-type(3) div.stButton > button {
            background: #FFFFFF !important; color: #000000 !important;
            border: 1px solid #ddd !important; font-size: 28px !important;
            box-shadow: none !important; padding: 0 !important; height: 60px !important;
        }
        /* LinkedIn Button - 4th Column */
        div[data-testid="column"]:nth-of-type(4) div.stButton > button {
            background: #0077b5 !important; color: #FFFFFF !important;
            font-size: 28px !important; box-shadow: none !important;
            padding: 0 !important; height: 60px !important;
        }

        /* כרטיסי מידע */
        .stock-card {
            background: linear-gradient(135deg, rgba(35, 40, 60, 0.7) 0%, rgba(25, 30, 45, 0.9) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 24px;
            margin-bottom: 20px; transition: all 0.3s ease;
        }
        .archive-card {
            background: rgba(25, 30, 45, 0.8); border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px; padding: 20px 24px; margin-bottom: 16px;
        }
        .divider-text { text-align: center; color: #888; margin: 30px 0; font-size: 0.9rem; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# SESSION STATE
# ==========================================
if 'page' not in st.session_state: st.session_state['page'] = 'auth'
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

# ==========================================
# GOOGLE SHEETS CONNECTION
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
    except: return None

def get_worksheet(sheet_name):
    client = get_client()
    if client:
        try: return client.open("StockWatcherDB").worksheet(sheet_name)
        except: return None
    return None

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def add_user_to_db(email, password, phone):
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        df = pd.DataFrame(sheet.get_all_records())
        # הגנה מפני קריסה אם הגיליון ריק
        if not df.empty and 'email' in df.columns:
            if email in df['email'].values:
                st.warning("User already exists.")
                return False
    except: pass
    
    hashed_pw = make_hashes(password)
    row = [email, hashed_pw, str(datetime.now()), phone]
    try:
        sheet.append_row(row)
        return True
    except: return False

def login_user(email, password):
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        data = sheet.get_all_records()
        if not data: return False
        
        df = pd.DataFrame(data)
        if 'email' not in df.columns: return False
        
        user_row = df[df['email'] == email]
        if user_row.empty: return False
        
        stored_hash = user_row.iloc[0]['password']
        if check_hashes(password, stored_hash): return True
    except: pass
    return False

# ==========================================
# MARKET DATA & LOGIC
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
            else: data[name] = (0.0, 0.0)
        except: data[name] = (0.0, 0.0)
    return data

def get_real_time_price(symbol):
    if not symbol: return None
    try: return yf.Ticker(symbol).history(period="1d")['Close'].iloc[-1]
    except: return None

def save_alert(ticker, min_p, max_p, vol, one_time):
    sheet = get_worksheet("Rules")
    if not sheet: 
        st.error("Database connection failed")
        return
    
    # המרת ערכים לסטרינג רק בשמירה, ושימוש ב-0 בלוגיקה
    row = [
        st.session_state.user_email, 
        ticker, 
        min_p if min_p > 0 else "", 
        max_p if max_p > 0 else "", 
        vol, 
        str(datetime.now()), 
        "TRUE" if one_time else "FALSE", 
        "Active"
    ]
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
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except: st.caption("Chart unavailable")

# ==========================================
# PAGE: AUTH (Login/Signup)
# ==========================================
def auth_page():
    col_img, col_form = st.columns([1.5, 1])
    
    with col_img:
        try: st.image("login_image.png", use_container_width=True)
        except: st.warning("Please upload 'login_image.png'")

    with col_form:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="logo-title">STOCKPULSE</div>', unsafe_allow_html=True)
        st.markdown('<div class="logo-subtitle">Real-Time Market Alerts</div>', unsafe_allow_html=True)
        
        tab_login, tab_signup = st.tabs(["LOG IN", "SIGN UP"])
        
        # --- TAB LOGIN ---
        with tab_login:
            l_email = st.text_input("Email Address", key="l_email")
            l_pass = st.text_input("Password", type="password", key="l_pass")
            
            st.markdown('<div style="text-align:right; color:#888; font-size:0.8rem; margin-bottom:20px;">Forgot Password?</div>', unsafe_allow_html=True)
            
            if st.button("LOG IN"):
                if login_user(l_email, l_pass):
                    st.session_state.user_email = l_email
                    st.session_state.logged_in = True
                    navigate_to('dashboard')
                else:
                    st.error("Invalid credentials or user not found")
            
            st.markdown('<div class="divider-text">— OR CONTINUE WITH —</div>', unsafe_allow_html=True)
            
            # כפתורי סושיאל (מרובעים באמצעות CSS)
            gap1, col_g, col_a, col_l, gap2 = st.columns([2, 1, 1, 1, 2])
            with col_g: st.button("G", key="g_login", help="Google")
            with col_a: st.button("", key="a_login", help="Apple")
            with col_l: st.button("in", key="l_login", help="LinkedIn")

        # --- TAB SIGNUP ---
        with tab_signup:
            s_email = st.text_input("Email Address", key="s_email")
            s_pass = st.text_input("Create Password", type="password", key="s_pass")
            s_phone = st.text_input("WhatsApp Number", placeholder="+972...", key="s_phone")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("CREATE ACCOUNT"):
                if add_user_to_db(s_email, s_pass, s_phone):
                    st.success("Account created! Please log in.")
                else:
                    st.error("User already exists or DB error")

# ==========================================
# PAGE: DASHBOARD
# ==========================================
def dashboard_page():
    c1, c2 = st.columns([6, 1])
    with c1: st.title("Dashboard")
    with c2: 
        if st.button("Log Out"):
            st.session_state.logged_in = False
            navigate_to('auth')
            
    # Metrics
    metrics = get_market_metrics()
    m_cols = st.columns(4)
    keys = ["S&P 500", "NASDAQ", "Bitcoin", "VIX"]
    for i, key in enumerate(keys):
        val, chg = metrics.get(key, (0,0))
        color = "#10B981" if chg >= 0 else "#EF4444"
        with m_cols[i]:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; text-align:center;">
                <div style="color:#888; font-size:0.75rem; text-transform:uppercase;">{key}</div>
                <div style="font-size:1.5rem; font-weight:900; margin:5px 0;">{val:,.2f}</div>
                <div style="color:{color}; font-weight:700; font-size:0.9rem;">{chg:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("---")

    # Main Area
    col_setup, col_list = st.columns([1, 2])
    
    # Left: Alert Setup
    with col_setup:
        st.markdown("### 🔔 Create Alert")
        with st.container(border=True):
            tick = st.text_input("Ticker Symbol", value="NVDA").upper()
            curr_price = 0.0
            if tick:
                curr_price = get_real_time_price(tick) or 0.0
                st.caption(f"Current Price: ${curr_price:.2f}")

            st.markdown("<strong>Target Price</strong>", unsafe_allow_html=True)
            if 'slider_price' not in st.session_state: st.session_state.slider_price = curr_price
            
            # Input + Slider Logic
            input_val = st.number_input("Price", value=float(st.session_state.slider_price), label_visibility="collapsed")
            s_min = float(curr_price) * 0.5
            s_max = float(curr_price) * 1.5
            if s_max == 0: s_max = 100.0
            
            final_target = st.slider("Fine Tune", min_value=s_min, max_value=s_max, value=input_val)
            
            st.markdown("---")
            min_vol = st.number_input("Min Volume (M)", value=5, step=1)
            st.caption("✅ Alert sends to WhatsApp")
            
            if st.button("SET ALERT"):
                if tick:
                    min_p = final_target if final_target < curr_price else 0
                    max_p = final_target if final_target > curr_price else 0
                    save_alert(tick, min_p, max_p, min_vol*1000000, True)

    # Right: Watchlist
    with col_list:
        h1, h2 = st.columns([4, 1])
        with h1: st.markdown("### 📋 Active Watchlist")
        with h2: 
            if st.button("Archive"): navigate_to('archive')

        sh = get_worksheet("Rules")
        if sh:
            try:
                data = sh.get_all_records()
                if not data:
                    st.info("No alerts found.")
                else:
                    df = pd.DataFrame(data)
                    user_col = 'user_email' if 'user_email' in df.columns else 'email'
                    
                    if user_col in df.columns and 'status' in df.columns:
                        my_df = df[(df[user_col] == st.session_state.user_email) & (df['status'] == 'Active')]
                        
                        if my_df.empty:
                            st.info("No active alerts.")
                        else:
                            grid = st.columns(2)
                            for i, (idx, row) in enumerate(my_df.iterrows()):
                                with grid[i % 2]:
                                    # בדיקה למניעת קריסה אם שדות ריקים
                                    mp = row.get('max_price')
                                    mnp = row.get('min_price')
                                    # המרה בטוחה למספר
                                    try: target = float(mp) if mp else float(mnp)
                                    except: target = 0
                                    
                                    vol_display = str(row.get('min_volume', 0))[:2]
                                    
                                    st.markdown(f"""
                                    <div class="stock-card">
                                        <div style="display:flex; justify-content:space-between;">
                                            <h3 style="margin:0; color:#FF6B6B;">{row['symbol']}</h3>
                                            <span style="color:#888;">{vol_display}M Vol</span>
                                        </div>
                                        <div style="font-size:1.2rem; margin-top:10px; color:#fff;">Target: <b>${target}</b></div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    with st.expander("Chart"): show_chart(row['symbol'])
            except Exception as e: st.error(f"Data Error: {e}")

# ==========================================
# PAGE: ARCHIVE
# ==========================================
def archive_page():
    st.title("🗄️ Archive")
    if st.button("← Back"): navigate_to('dashboard')
    st.markdown("---")
    
    sh = get_worksheet("Rules")
    if sh:
        try:
            df = pd.DataFrame(sh.get_all_records())
            if not df.empty and 'user_email' in df.columns:
                adf = df[(df['user_email'] == st.session_state.user_email) & (df['status'] != 'Active')]
                for i, row in adf.iterrows():
                    st.markdown(f"""
                    <div class="archive-card">
                        <b style="color:#FF6B6B">{row['symbol']}</b> <span style="color:#888">| {row['created_at']}</span>
                        <span style="float:right; color:#fff;">{row['status']}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else: st.info("Empty Archive")
        except: pass

# ==========================================
# MAIN EXECUTION
# ==========================================
apply_premium_css()

if st.session_state.logged_in:
    if st.session_state['page'] == 'archive': archive_page()
    else: dashboard_page()
else:
    auth_page()
