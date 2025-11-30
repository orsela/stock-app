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
# 1. APP CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="StockPulse Terminal",
    layout="wide",
    page_icon="💹",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. CSS STYLING (TERMINAL STYLE)
# ==========================================
def apply_terminal_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&display=swap');
        
        .stApp { background-color: #000000; color: #FFFFFF; font-family: 'Inter', sans-serif; }
        #MainMenu, footer, header, .stDeployButton {visibility: hidden;}

        /* Typography */
        h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel { color: #FFFFFF !important; opacity: 1 !important; }
        .logo-title { font-size: 3rem; font-weight: 900; text-align: center; margin-bottom: 5px; letter-spacing: -1px; }
        .logo-subtitle { font-family: 'JetBrains Mono', monospace; color: #FF7F50; font-size: 1rem; text-align: center; margin-bottom: 30px; letter-spacing: 1px; }
        
        /* Dashboard Logo */
        .dashboard-logo { font-size: 2.2rem; font-weight: 900; color: #FFFFFF; margin: 0; letter-spacing: -1px; line-height: 1; }
        .dashboard-sub { font-family: 'JetBrains Mono', monospace; color: #FF7F50; font-size: 0.8rem; letter-spacing: 1px; }

        /* Inputs */
        .stTextInput > div > div > input, .stNumberInput > div > div > input {
            background-color: #111 !important; border: 1px solid #333 !important; color: #FFFFFF !important;
            font-family: 'JetBrains Mono', monospace !important; font-weight: 700; font-size: 1.1rem;
        }
        
        /* Buttons */
        .stButton > button {
            background-color: #FF7F50 !important; color: #000000 !important; border: none !important;
            font-weight: 800 !important; border-radius: 4px !important; text-transform: uppercase; font-size: 1rem;
        }
        .stButton > button:hover { background-color: #FF6347 !important; transform: scale(1.02); }

        /* Social Buttons */
        div[data-testid="column"]:nth-of-type(2) div.stButton > button {
            background: #FFFFFF !important; border-radius: 8px !important;
            background-image: -webkit-linear-gradient(45deg, #4285F4, #DB4437, #F4B400, #0F9D58) !important;
            -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
            font-size: 26px !important; font-weight: 900 !important; height: 60px !important;
        }
        div[data-testid="column"]:nth-of-type(3) div.stButton > button {
            background: #FFFFFF !important; color: #000 !important; border-radius: 8px !important;
            font-size: 26px !important; height: 60px !important;
        }
        div[data-testid="column"]:nth-of-type(4) div.stButton > button {
            background: #0077b5 !important; color: #FFF !important; border-radius: 8px !important;
            font-size: 26px !important; height: 60px !important;
        }

        /* Ticker & Cards */
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
# 3. STATE MANAGEMENT
# ==========================================
if 'page' not in st.session_state: st.session_state['page'] = 'auth'
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None
if 'target_price' not in st.session_state: st.session_state['target_price'] = 0.0

# ==========================================
# 4. BACKEND FUNCTIONS
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

def save_alert(ticker, min_p, max_p, vol, one_time):
    sheet = get_worksheet("Rules")
    if not sheet: 
        st.error("DB Error")
        return
    row = [
        st.session_state.user_email, ticker, 
        min_p if min_p > 0 else "", max_p if max_p > 0 else "", 
        vol, str(datetime.now()), "TRUE" if one_time else "FALSE", "Active"
    ]
    try:
        sheet.append_row(row)
        st.toast(f"SAVED: {ticker}", icon="💾")
        time.sleep(1)
        st.rerun()
    except Exception as e: st.error(str(e))

def render_chart(hist, title):
    fig = go.Figure(data=[go.Candlestick(x=hist.index,
                open=hist['Open'], high=hist['High'],
                low=hist['Low'], close=hist['Close'])])
    fig.update_layout(
        title=dict(text=title, font=dict(color='white')),
        height=350, margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor='#000', plot_bgcolor='#000',
        font=dict(color='white'), xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. UI PAGES
# ==========================================
def auth_page():
    col_img, col_form = st.columns([1.5, 1])
    with col_img:
        try: st.image("login_image.png", use_container_width=True)
        except: st.warning("Missing login_image.png")

    with col_form:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="logo-title">STOCKPULSE</div>', unsafe_allow_html=True)
        st.markdown('<div class="logo-subtitle">TERMINAL ACCESS</div>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["LOG IN", "SIGN UP"])
        with tab1:
            e = st.text_input("EMAIL", key="le")
            p = st.text_input("PASSWORD", type="password", key="lp")
            if st.button("AUTHENTICATE"):
                if login_user(e, p):
                    st.session_state.user_email = e
                    st.session_state.logged_in = True
                    st.session_state.page = 'dashboard'
                    st.rerun()
                else: st.error("Access Denied")
            
            st.markdown('<div class="divider-text">OR CONNECT WITH</div>', unsafe_allow_html=True)
            c1, cg, ca, cl, c2 = st.columns([1, 1, 1, 1, 1])
            with cg: st.button("G", key="g")
            with ca: st.button("", key="a")
            with cl: st.button("in", key="l")

        with tab2:
            ne = st.text_input("EMAIL", key="se")
            np = st.text_input("PASSWORD", type="password", key="sp")
            ph = st.text_input("WHATSAPP", key="sph")
            if st.button("CREATE ID"):
                if add_user_to_db(ne, np, ph): st.success("Created.")
                else: st.error("Error")

def dashboard_page():
    metrics = get_top_metrics()
    tape_html = ""
    for k, v in metrics.items():
        color = "#00FF00" if v[1] >= 0 else "#FF0000"
        tape_html += f'<div class="ticker-item">{k}: <span style="color:{color}">{v[0]:,.2f} ({v[1]:+.2f}%)</span></div>'
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{tape_html * 3}</div></div>', unsafe_allow_html=True)

    # Header with LOGO
    c1, c2 = st.columns([8, 1])
    with c1:
        st.markdown("""
        <div>
            <div class="dashboard-logo">STOCKPULSE</div>
            <div class="dashboard-sub">LIVE TERMINAL</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2: 
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("LOGOUT"):
            st.session_state.logged_in = False
            st.session_state.page = 'auth'
            st.rerun()

    cols = st.columns(4)
    i = 0
    for k, v in metrics.items():
        with cols[i]:
            clr = "#10B981" if v[1] >= 0 else "#EF4444"
            st.markdown(f"""
            <div style="background:#111; padding:15px; border-radius:5px; text-align:center; border:1px solid #333;">
                <div style="color:#888; font-size:0.8rem;">{k}</div>
                <div style="font-family:'JetBrains Mono'; font-size:1.5rem; color:#fff;">{v[0]:,.2f}</div>
                <div style="color:{clr}; font-weight:bold;">{v[1]:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
        i += 1
    st.markdown("---")

    col_setup, col_list = st.columns([1.2, 1.8], gap="large")

    with col_setup:
        st.markdown("### ⚡ QUICK ACTION")
        with st.container(border=True):
            symbol = st.text_input("SEARCH TICKER", value="NVDA").upper()
            curr = 0.0
            
            if symbol:
                data = get_stock_analysis(symbol)
                if data:
                    curr = data['price']
                    ma150 = data['ma150']
                    
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h1 class="stock-header">{symbol}</h1>
                        <span class="stock-price-lg">${curr:,.2f}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    diff_ma = ((curr - ma150) / ma150) * 100 if ma150 else 0
                    ma_color = "#10B981" if diff_ma > 0 else "#EF4444"
                    st.markdown(f"""
                    <div class="ma-box">
                        <span style="color:#888;">MA 150:</span> 
                        <span style="font-family:'JetBrains Mono'; color:#fff; font-size:1.2rem;">${ma150:,.2f}</span>
                        <span style="color:{ma_color}; margin-left:10px;">({diff_ma:+.2f}%)</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    render_chart(data['hist'], "")
                    if st.session_state.target_price == 0:
                        st.session_state.target_price = curr
                else: st.error("Ticker Not Found")

            st.markdown("---")
            st.markdown("#### 🎯 SET TARGET")

            def update_from_input(): st.session_state.target_price = st.session_state.inp_val
            def update_from_slider(): st.session_state.target_price = st.session_state.sld_val

            s_max = curr * 3 if curr > 0 else 1000.0
            
            st.number_input("MANUAL PRICE ($)", value=float(st.session_state.target_price), step=0.5, key="inp_val", on_change=update_from_input)
            st.slider("FINE TUNE", min_value=0.0, max_value=s_max, value=float(st.session_state.target_price), step=0.1, key="sld_val", on_change=update_from_slider)
            
            final_target = st.session_state.target_price
            st.markdown(f"**ORDER PRICE:** <span style='color:#FF7F50; font-size:1.2rem; font-family:JetBrains Mono'>${final_target:.2f}</span>", unsafe_allow_html=True)
            
            vol = st.number_input("MIN VOL (M)", value=5, step=1)
            
            if st.button("ACTIVATE ALERT", use_container_width=True):
                if symbol and final_target > 0:
                    min_p = final_target if final_target < curr else 0
                    max_p = final_target if final_target > curr else 0
                    save_alert(symbol, min_p, max_p, vol*1000000, True)

    with col_list:
        h1, h2 = st.columns([3, 1])
        with h1: st.markdown("### 📋 WATCHLIST")
        with h2: 
            if st.button("ARCHIVE"): 
                st.session_state.page = 'archive'
                st.rerun()

        sh = get_worksheet("Rules")
        if sh:
            try:
                data = sh.get_all_records()
                if data:
                    df = pd.DataFrame(data)
                    uc = 'user_email' if 'user_email' in df.columns else 'email'
                    
                    if uc in df.columns and 'status' in df.columns:
                        my_df = df[(df[uc] == st.session_state.user_email) & (df['status'] == 'Active')]
                        
                        if my_df.empty:
                            st.info("NO ACTIVE ALERTS")
                        else:
                            for i, row in my_df.iterrows():
                                sym = row['symbol']
                                
                                # --- FLATTENED DATA EXTRACTION (NO SYNTAX ERROR) ---
                                t_max = safe_float(row.get('max_price'))
                                t_min = safe_float(row.get('min_price'))
                                
                                target = 0.0
                                if t_max > 0:
                                    target = t_max
                                else:
                                    target = t_min
                                
                                v_raw = safe_float(row.get('min_volume'))
                                vol_display = str(v_raw)[:2]

                                # Separated logic call
                                stock_info = get_stock_analysis(sym)
                                
                                cp = 0.0
                                ma = 0.0
                                if stock_info:
                                    cp = stock_info['price']
                                    ma = stock_info['ma150']
                                
                                with st.expander(f"{sym} | TGT: ${target} | NOW: ${cp:.2f}"):
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        st.write(f"MA150: **${ma:.2f}**")
                                        st.write(f"Vol: {vol_display}M")
                                    with c2:
                                        if ma > 0:
                                            d = ((cp - ma)/ma)*100
                                            clr = "green" if d>0 else "red"
                                            st.markdown(f"vs MA: :{clr}[{d:+.2f}%]")
                                    
                                    if stock_info:
                                        render_chart(stock_info['hist'], "")
                                        
            except Exception as e: st.error(f"List Error: {e}")

def archive_page():
    st.title("🗄️ ARCHIVE")
    if st.button("BACK"): 
        st.session_state.page = 'dashboard'
        st.rerun()
    st.markdown("---")
    sh = get_worksheet("Rules")
    if sh:
        try:
            df = pd.DataFrame(sh.get_all_records())
            if not df.empty and 'user_email' in df.columns:
                adf = df[(df['user_email'] == st.session_state.user_email) & (df['status'] != 'Active')]
                for i, row in adf.iterrows():
                    st.markdown(f"""
                    <div style="background:#111; padding:10px; border-bottom:1px solid #333; display:flex; justify-content:space-between;">
                        <span><b style="color:#FF7F50">{row['symbol']}</b> <span style="color:#666; font-size:0.8rem;">{row['created_at']}</span></span>
                        <span>{row['status']}</span>
                    </div>
                    """, unsafe_allow_html=True)
        except: pass

# ==========================================
# 6. RUN
# ==========================================
apply_terminal_css()

if st.session_state.logged_in:
    if st.session_state['page'] == 'archive': archive_page()
    else: dashboard_page()
else:
    auth_page()
