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
# 1. עיצוב ו-CSS (שחור, כפתורים כתומים, טאבים)
# ==========================================
st.set_page_config(page_title="StockPulse", layout="wide", page_icon="📈")

def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700;900&display=swap');
        
        /* --- רקע כללי שחור --- */
        .stApp {
            background-color: #000000;
            font-family: 'Roboto', sans-serif;
            color: #FFFFFF;
        }
        
        /* --- עיצוב הטאבים (Tabs) --- */
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
            border: none; /* ביטול גבולות ברירת מחדל */
        }
        .stTabs [aria-selected="true"] {
            color: #FF7F50 !important;
            border-bottom: 3px solid #FF7F50; /* קו תחתון מודגש יותר */
        }
        
        /* --- שדות קלט (רקע בהיר, טקסט כהה) --- */
        div[data-testid="stTextInput"] > div > div {
            background-color: #F0F2F6 !important;
            border-radius: 8px;
            border: none;
            color: #333 !important;
        }
        input[type="text"], input[type="password"] {
            color: #333 !important;
        }
        
        /* --- כפתורים (כתום) --- */
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
            margin-bottom: 10px; /* ריווח בין כפתורים אנכיים */
        }
        div.stButton > button:hover {
            background-color: #FF6347;
            box-shadow: 0px 0px 15px rgba(255, 127, 80, 0.5);
        }
        
        /* --- טקסטים וכותרות --- */
        .main-title { font-size: 3.5rem; font-weight: 900; color: #fff; line-height: 1.1; }
        .sub-title { font-size: 1.2rem; color: #888; margin-bottom: 30px; }
        .divider-text { text-align: center; color: #888; font-size: 0.9rem; margin: 30px 0 20px 0; }
        
        /* הסתרת אלמנטים מיותרים */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# State Management
if 'page' not in st.session_state: st.session_state['page'] = 'auth'
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

# ==========================================
# 2. לוגיקה ו-DB (ללא שינוי)
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
    if make_hashes(password) == hashed_text: return hashed_text
    return False

def add_user_to_db(email, password, phone):
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and 'email' in df.columns and email in df['email'].values:
            st.warning("User already exists.")
            return False
    except: pass
    hashed_pw = make_hashes(password)
    row = [email, hashed_pw, str(datetime.now()), phone]
    sheet.append_row(row)
    return True

def login_user(email, password):
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return False
        user_row = df[df['email'] == email]
        if user_row.empty: return False
        stored_hash = user_row.iloc[0]['password']
        if check_hashes(password, stored_hash): return True
    except: pass
    return False

# ==========================================
# 3. נתוני שוק (ללא שינוי)
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
    if not sheet: return
    row = [st.session_state.user_email, ticker, min_p if min_p>0 else "", max_p if max_p>0 else "", vol, str(datetime.now()), "TRUE" if one_time else "FALSE", "Active"]
    try:
        sheet.append_row(row)
        st.toast(f"✅ Alert Set: {ticker}", icon="🔥")
        time.sleep(1)
        st.rerun()
    except Exception as e: st.error(f"Save Error: {e}")

def navigate_to(page):
    st.session_state['page'] = page
    st.rerun()

def show_chart(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1mo")
        fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
        fig.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except: st.caption("Chart unavailable")

# ==========================================
# 4. מסך התחברות והרשמה משולב (Split Screen)
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
        
        # --- TAB 1: LOG IN (מעודכן עם כפתורים חדשים) ---
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
            
            # --- כפתורי סושיאל מעודכנים ---
            st.markdown('<div class="divider-text">— OR CONTINUE WITH —</div>', unsafe_allow_html=True)
            
            # שימוש בכפתורים רחבים אחד מתחת לשני עם אימוג'י וטקסט ברור
            # ה-CSS הקיים כבר דואג שהם יהיו כתומים ולרוחב מלא
            st.button("🌐 Continue with Google", key="g_btn")
            st.button("🍎 Continue with Apple", key="a_btn")
            st.button("🔗 Continue with LinkedIn", key="l_btn")

        # --- TAB 2: SIGN UP (ללא שינוי) ---
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
            
# ==========================================
# 5. PAGE: DASHBOARD (ללא שינוי)
# ==========================================
def dashboard_page():
    c1, c2 = st.columns([6, 1])
    with c1: st.title("Dashboard")
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
            <div style="background:#111; padding:15px; border-radius:10px; text-align:center; border:1px solid #333;">
                <div style="color:#888; font-size:0.8rem;">{key}</div>
                <div style="font-size:1.5rem; font-weight:bold;">{val:,.2f}</div>
                <div style="color:{color}; font-weight:bold;">{chg:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("---")

    col_setup, col_list = st.columns([1, 2])
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
            input_val = st.number_input("Price Input", value=float(st.session_state.slider_price), label_visibility="collapsed")
            s_min = float(curr_price) * 0.5
            s_max = float(curr_price) * 1.5
            if s_max == 0: s_max = 100
            final_target = st.slider("Fine Tune", min_value=s_min, max_value=s_max, value=input_val)
            st.markdown("---")
            min_vol = st.number_input("Min Volume (M)", value=5, step=1)
            st.caption("✅ Alert sends to WhatsApp")
            if st.button("SET ALERT"):
                if tick:
                    min_p = final_target if final_target < curr_price else ""
                    max_p = final_target if final_target > curr_price else ""
                    save_alert(tick, min_p, max_p, min_vol*1000000, True)

    with col_list:
        h1, h2 = st.columns([4, 1])
        with h1: st.markdown("### 📋 Active Watchlist")
        with h2: 
            if st.button("Archive"): navigate_to('archive')

        sh = get_worksheet("Rules")
        if sh:
            try:
                df = pd.DataFrame(sh.get_all_records())
                user_col = 'user_email' if 'user_email' in df.columns else 'email'
                if not df.empty and user_col in df.columns:
                    my_df = df[(df[user_col] == st.session_state.user_email) & (df['status'] == 'Active')]
                    if my_df.empty: st.info("No active alerts.")
                    else:
                        grid = st.columns(2)
                        for i, (idx, row) in enumerate(my_df.iterrows()):
                            with grid[i % 2]:
                                target = row['max_price'] if row['max_price'] else row['min_price']
                                st.markdown(f"""
                                <div class="stock-card">
                                    <div style="display:flex; justify-content:space-between;">
                                        <h3 style="margin:0; color:#FF7F50;">{row['symbol']}</h3>
                                        <span style="color:#888;">{str(row['min_volume'])[:2]}M Vol</span>
                                    </div>
                                    <div style="font-size:1.2rem; margin-top:10px;">Target: <b>${target}</b></div>
                                </div>
                                """, unsafe_allow_html=True)
                                with st.expander("Chart"): show_chart(row['symbol'])
                else: st.info("No Data")
            except: st.error("DB Error")

# ==========================================
# 6. PAGE: ARCHIVE (ללא שינוי)
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
                        <b>{row['symbol']}</b> - {row['created_at']} <span style="float:right;">{row['status']}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else: st.info("Empty Archive")
        except: pass

# ==========================================
# 7. MAIN ROUTER
# ==========================================
apply_custom_css()

if st.session_state.logged_in:
    if st.session_state['page'] == 'archive': archive_page()
    else: dashboard_page()
else:
    auth_page()
