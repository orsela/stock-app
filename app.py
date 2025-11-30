import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import yfinance as yf
import hashlib
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(page_title="StockPulse", layout="wide", page_icon="💹", initial_sidebar_state="collapsed")

# -----------------------------------------------------------------------------
# 2. CSS STYLING
# -----------------------------------------------------------------------------
def apply_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&display=swap');
        .stApp { background-color: #000000; color: #FFFFFF; font-family: 'Inter', sans-serif; }
        #MainMenu, footer, header, .stDeployButton {visibility: hidden;}
        
        h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel { color: #FFFFFF !important; opacity: 1 !important; }
        
        .logo-text { font-size: 2.2rem; font-weight: 900; color: #FFFFFF; margin: 0; line-height: 1; }
        .logo-sub { font-family: 'JetBrains Mono'; color: #FF7F50; font-size: 0.8rem; letter-spacing: 1px; }
        
        .stTextInput>div>div>input, .stNumberInput>div>div>input {
            background-color: #111 !important; border: 1px solid #333 !important; color: #FFF !important; font-family: 'JetBrains Mono';
        }
        .stButton>button {
            background-color: #FF7F50 !important; color: #000 !important; border: none; font-weight: 800; border-radius: 4px;
        }
        .stButton>button:hover { background-color: #FF6347 !important; transform: scale(1.02); }
        
        /* Social Buttons */
        div[data-testid="column"]:nth-of-type(2) div.stButton > button {
            background: #FFF !important; background-image: linear-gradient(45deg, #4285F4, #DB4437, #F4B400, #0F9D58) !important;
            -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
            font-size: 26px !important; font-weight: 900 !important; height: 60px !important; border-radius: 8px !important;
        }
        div[data-testid="column"]:nth-of-type(3) div.stButton > button {
            background: #FFF !important; color: #000 !important; font-size: 26px !important; height: 60px !important; border-radius: 8px !important;
        }
        div[data-testid="column"]:nth-of-type(4) div.stButton > button {
            background: #0077b5 !important; color: #FFF !important; font-size: 26px !important; height: 60px !important; border-radius: 8px !important;
        }

        .stock-val { font-family: 'JetBrains Mono'; font-size: 2rem; font-weight: 700; }
        .ticker-wrap { width: 100%; overflow: hidden; background-color: #111; border-bottom: 1px solid #333; padding: 10px 0; margin-bottom: 20px; white-space: nowrap; }
        .ticker-move { display: inline-block; animation: ticker 35s linear infinite; }
        .ticker-item { display: inline-block; padding: 0 2rem; font-family: 'JetBrains Mono'; color: #00FF00; }
        @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }
        </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. STATE & HELPERS
# -----------------------------------------------------------------------------
if 'page' not in st.session_state: st.session_state['page'] = 'auth'
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None
if 'target_price' not in st.session_state: st.session_state['target_price'] = 0.0

def safe_float(v):
    try: return float(v)
    except: return 0.0

# -----------------------------------------------------------------------------
# 4. BACKEND
# -----------------------------------------------------------------------------
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        return gspread.authorize(creds)
    except: return None

def get_worksheet(name):
    c = get_client()
    if c:
        try: return c.open("StockWatcherDB").worksheet(name)
        except: return None
    return None

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def db_login(email, password):
    sh = get_worksheet("USERS")
    if not sh: return False
    try:
        data = sh.get_all_records()
        if not data: return False
        df = pd.DataFrame(data)
        if 'email' not in df.columns: return False
        user = df[df['email'] == email]
        if user.empty: return False
        if hash_pw(password) == user.iloc[0]['password']: return True
    except: pass
    return False

def db_signup(email, password, phone):
    sh = get_worksheet("USERS")
    if not sh: return False
    try:
        df = pd.DataFrame(sh.get_all_records())
        if not df.empty and 'email' in df.columns and email in df['email'].values: return False
    except: pass
    try:
        sh.append_row([email, hash_pw(password), str(datetime.now()), phone])
        return True
    except: return False

@st.cache_data(ttl=30)
def get_metrics():
    tickers = {"S&P500":"^GSPC", "NASDAQ":"^IXIC", "BTC":"BTC-USD", "VIX":"^VIX"}
    res = {}
    for k,v in tickers.items():
        try:
            h = yf.Ticker(v).history(period="2d")
            if len(h)>=2:
                c = h['Close'].iloc[-1]
                p = h['Close'].iloc[-2]
                res[k] = (c, ((c-p)/p)*100)
            else: res[k] = (0,0)
        except: res[k] = (0,0)
    return res

@st.cache_data(ttl=60)
def get_analysis(sym):
    try:
        t = yf.Ticker(sym)
        h = t.history(period="1y")
        if h.empty: return None
        curr = h['Close'].iloc[-1]
        ma = h['Close'].rolling(150).mean().iloc[-1] if len(h)>=150 else 0
        return {"p": curr, "ma": ma, "h": h}
    except: return None

def save_rule(tick, mn, mx, vol, ot):
    sh = get_worksheet("Rules")
    if not sh: st.error("DB Error"); return
    try:
        sh.append_row([st.session_state.user_email, tick, mn if mn>0 else "", mx if mx>0 else "", vol, str(datetime.now()), str(ot).upper(), "Active"])
        st.toast("Saved!", icon="💾")
        time.sleep(1)
        st.rerun()
    except Exception as e: st.error(str(e))

def draw_chart(h):
    fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'])])
    fig.update_layout(height=300, margin=dict(l=0,r=0,t=20,b=0), paper_bgcolor='#000', plot_bgcolor='#000', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 5. UI PAGES
# -----------------------------------------------------------------------------
def page_auth():
    c1, c2 = st.columns([1.5, 1])
    with c1:
        try: st.image("login_image.png", use_container_width=True)
        except: st.warning("No Image")
    with c2:
        st.markdown("<br><br><h1 style='text-align:center'>STOCKPULSE</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["LOG IN", "SIGN UP"])
        with t1:
            e = st.text_input("EMAIL", key="1")
            p = st.text_input("PASSWORD", type="password", key="2")
            if st.button("LOGIN"):
                if db_login(e, p):
                    st.session_state.user_email = e
                    st.session_state.logged_in = True
                    st.session_state.page = 'dash'
                    st.rerun()
                else: st.error("Error")
            st.markdown("<div style='text-align:center;margin:20px'>OR</div>", unsafe_allow_html=True)
            sc1, sc2, sc3, sc4, sc5 = st.columns([1,1,1,1,1])
            with sc2: st.button("G", key="g")
            with sc3: st.button("", key="a")
            with sc4: st.button("in", key="i")
        with t2:
            ne = st.text_input("EMAIL", key="3")
            np = st.text_input("PASSWORD", type="password", key="4")
            ph = st.text_input("PHONE", key="5")
            if st.button("CREATE"):
                if db_signup(ne, np, ph): st.success("Created")
                else: st.error("Error")

def page_dash():
    # Ticker
    mets = get_metrics()
    txt = ""
    for k,v in mets.items():
        c = "#0f0" if v[1]>=0 else "#f00"
        txt += f'<div class="ticker-item">{k} <span style="color:{c}">{v[0]:.2f}</span></div>'
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{txt*5}</div></div>', unsafe_allow_html=True)

    # Header
    c1, c2 = st.columns([8,1])
    with c1: st.markdown('<div class="logo-text">STOCKPULSE</div><div class="logo-sub">TERMINAL</div>', unsafe_allow_html=True)
    with c2: 
        if st.button("LOGOUT"):
            st.session_state.logged_in = False
            st.session_state.page = 'auth'
            st.rerun()
    st.markdown("---")

    # Body
    cl, cr = st.columns([1.2, 1.8], gap="large")
    
    with cl:
        st.markdown("### ⚡ ACTION")
        with st.container(border=True):
            sym = st.text_input("SYMBOL", value="NVDA").upper()
            curr = 0.0
            
            if sym:
                d = get_analysis(sym)
                if d:
                    curr = d['p']
                    ma = d['ma']
                    st.markdown(f"<div class='stock-val'>${curr:.2f}</div>", unsafe_allow_html=True)
                    if ma:
                        diff = ((curr-ma)/ma)*100
                        clr = "green" if diff>0 else "red"
                        st.markdown(f"MA150: {ma:.2f} (:{clr}[{diff:+.2f}%])")
                    draw_chart(d['h'])
                    if st.session_state.target_price == 0: st.session_state.target_price = curr
                else: st.error("Not Found")
            
            st.markdown("---")
            
            def upd_inp(): st.session_state.target_price = st.session_state.iv
            def upd_sld(): st.session_state.target_price = st.session_state.sv
            
            mx = curr*3 if curr>0 else 500.0
            st.number_input("PRICE", value=float(st.session_state.target_price), step=0.5, key="iv", on_change=upd_inp)
            st.slider("FINE TUNE", 0.0, mx, float(st.session_state.target_price), 0.1, key="sv", on_change=upd_sld)
            
            final_p = st.session_state.target_price
            st.markdown(f"**ORDER:** :orange[${final_p:.2f}]")
            
            vol = st.number_input("VOL (M)", 1, step=1)
            
            if st.button("ACTIVATE", use_container_width=True):
                if sym and final_p > 0:
                    mn = final_p if final_p < curr else 0
                    mx_p = final_p if final_p > curr else 0
                    save_rule(sym, mn, mx_p, vol*1000000, True)

    with cr:
        h1, h2 = st.columns([3,1])
        with h1: st.markdown("### 📋 WATCHLIST")
        with h2: 
            if st.button("ARCHIVE"): 
                st.session_state.page = 'arch'
                st.rerun()
        
        sh = get_worksheet("Rules")
        if sh:
            try:
                raw = sh.get_all_records()
                if raw:
                    df = pd.DataFrame(raw)
                    uc = 'user_email' if 'user_email' in df.columns else 'email'
                    if uc in df.columns and 'status' in df.columns:
                        my = df[(df[uc] == st.session_state.user_email) & (df['status'] == 'Active')]
                        if my.empty: st.info("Empty")
                        else:
                            for i, row in my.iterrows():
                                s = row['symbol']
                                # SAFE EXTRACTION START
                                try: t_mx = float(row.get('max_price', 0))
                                except: t_mx = 0
                                try: t_mn = float(row.get('min_price', 0))
                                except: t_mn = 0
                                tgt = t_mx if t_mx > 0 else t_mn
                                v = row.get('min_volume', 0)
                                # SAFE EXTRACTION END
                                
                                analysis = get_analysis(s)
                                cp = analysis['p'] if analysis else 0
                                ma_val = analysis['ma'] if analysis else 0
                                
                                with st.expander(f"{s} | TGT ${tgt} | NOW ${cp:.2f}"):
                                    c1, c2 = st.columns(2)
                                    c1.write(f"MA150: {ma_val:.2f}")
                                    c1.write(f"Vol: {str(v)[:2]}M")
                                    if analysis: draw_chart(analysis['h'])
            except Exception as e: st.error(str(e))

def page_arch():
    st.title("ARCHIVE")
    if st.button("BACK"): 
        st.session_state.page = 'dash'
        st.rerun()
    sh = get_worksheet("Rules")
    if sh:
        try:
            df = pd.DataFrame(sh.get_all_records())
            uc = 'user_email' if 'user_email' in df.columns else 'email'
            if not df.empty:
                my = df[(df[uc] == st.session_state.user_email) & (df['status'] != 'Active')]
                for i, r in my.iterrows():
                    st.write(f"{r['symbol']} | {r['created_at']} | {r['status']}")
        except: pass

# -----------------------------------------------------------------------------
# 6. RUN
# -----------------------------------------------------------------------------
apply_css()

if st.session_state.logged_in:
    if st.session_state.page == 'arch': page_arch()
    else: page_dash()
else:
    page_auth()
