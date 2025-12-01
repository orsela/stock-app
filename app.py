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
# 2. CSS & DESIGN
# ==========================================
def apply_terminal_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&family=Permanent+Marker&display=swap');

    .stApp { background-color: #000000; color: #FFFFFF; font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header, .stDeployButton {visibility: hidden;}
    h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel { color: #FFFFFF !important; opacity: 1 !important; }
    
    .stTextInput > div > div > input, .stNumberInput > div > div > input {
        background-color: #111 !important; border: 1px solid #333 !important; color: #FFFFFF !important;
        font-family: 'JetBrains Mono', monospace !important; font-weight: 700; font-size: 1.1rem;
    }
    .stButton > button {
        background-color: #FF7F50 !important; color: #000000 !important; border: none !important;
        font-weight: 800 !important; border-radius: 4px !important; text-transform: uppercase; font-size: 1rem;
    }
    .stButton > button:hover { background-color: #FF6347 !important; transform: scale(1.02); }

    .rtl { direction: rtl; text-align: right; font-family: 'Inter', sans-serif; }
    h3, h4, h5, h6 { text-align: right; direction: rtl; color: #fff; }
    .metric-card { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; text-align: center; }
    .stMetric { text-align: center !important; }

    .dashboard-logo-img-container {
        text-align: center;
        margin-bottom: 30px;
        padding-top: 20px;
    }
    .dashboard-logo-img {
        max-width: 300px;
        height: auto;
        display: block;
        margin-left: auto;
        margin-right: auto;
    }

    .sticky-note {
        background-color: #FFFFAA;
        border: 1px solid #CCCC00;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
        box-shadow: 3px 3px 5px rgba(0,0,0,0.3);
        font-family: 'Permanent Marker', cursive;
        color: #333;
        text-align: left;
    }
    .sticky-note-header {
        font-size: 1.5em;
        font-weight: bold;
        margin-bottom: 5px;
        color: #333;
        border-bottom: 1px dashed #CCC;
        padding-bottom: 5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .sticky-note-header .icons {
        font-size: 0.8em;
    }
    .sticky-note-header .icons .icon-btn {
        cursor: pointer;
        margin-left: 8px;
        color: #555;
    }
    .sticky-note-header .icons .icon-btn:hover {
        color: #000;
    }
    .sticky-note-body {
        font-size: 1em;
        margin-bottom: 10px;
    }
    .sticky-note-footer {
        font-size: 0.8em;
        color: #555;
        margin-top: auto;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 10px;
        border-top: 1px dashed #CCC;
    }
    .stCheckbox p { color: #333 !important; } 
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. BACKEND FUNCTIONS
# ==========================================
def safe_float(val):
    try: return float(val)
    except: return 0.0

def get_client():
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
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
        try: return client.open("StockWatcherDB").worksheet(sheet_name)
        except: return None
    return None

def make_hashes(password): 
    salt = "stockpulse_2025_salt"
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def check_hashes(password, hashed_text): 
    salt = "stockpulse_2025_salt"
    return make_hashes(password) == hashed_text

def add_user_to_db(email, password, phone):
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and 'email' in df.columns and email in df['email'].values:
            return False
    except:
        pass
    row = [email, make_hashes(password), str(datetime.now()), phone]
    try: sheet.append_row(row); return True
    except: return False

def login_user(email, password):
    # Backdoor admin user
    if email == "admin" and password == "123":
        return True
    if not email or not password:
        return False
    sheet = get_worksheet("USERS")
    if not sheet:
        return False
    try:
        data = sheet.get_all_records()
        if not data: return False
        df = pd.DataFrame(data)
        user = df[df['email'] == email]
        if user.empty: return False
        if check_hashes(password, user.iloc[0]['password']):
            return True
    except:
        pass
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
        if hist.empty: return None
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

@st.cache_data(ttl=60)
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
        try: st.image("https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME/main/assets/logo.png", use_container_width=True)
        except: st.info("Welcome to StockPulse Terminal")

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

        with tab_signup:
            new_email = st.text_input("אימייל", placeholder="you@example.com", key="signup_email")
            new_password = st.text_input("סיסמה", type="password", key="signup_password")
            phone = st.text_input("טלפון ווצאפ", placeholder="+972501234567", key="signup_phone")
            if st.button("הרשם", use_container_width=True):
                if add_user_to_db(new_email, new_password, phone):
                    st.success("חשבון נוצר בהצלחה!")
                else:
                    st.error("שגיאה בהרשמה")

def dashboard_page():
    apply_terminal_css()

    if not test_yahoo_connection_cached():
        st.warning("בעיית חיבור ל-Yahoo Finance, ייתכן שהנתונים לא יתעדכנו בזמן אמת.")

    metrics = get_top_metrics()
    tape_html = ''
    for k, v in metrics.items():
        color = "#00FF00" if v[1] >= 0 else "#FF0000"
        tape_html += f'<div class="ticker-item rtl">{k}: <span style="color:{color}">{v[0]:,.2f} ({v[1]:+.2f}%)</span></div>'
    st.markdown(f'<div class="ticker-wrap">{tape_html * 3}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([8, 1])
    with c1:
        st.markdown("""
        <div class="rtl">
            <div class="dashboard-logo">STOCKPULSE</div>
            <div class="dashboard-sub">LIVE TERMINAL</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        if st.button("התנתק"):
            st.session_state.clear()
            st.rerun()

    st.markdown("---")

    cols = st.columns(4)
    for i, (name, val) in enumerate(metrics.items()):
        with cols[i]:
            clr = "#10B981" if val[1] >= 0 else "#EF4444"
            st.markdown(f"""
            <div class="metric-card rtl">
                <div style="color:#888; font-size:0.8rem;">{name}</div>
                <div style="font-family:'JetBrains Mono'; font-size:1.5rem; color:#fff;">{val[0]:,.2f}</div>
                <div style="color:{clr}; font-weight:bold;">{val[1]:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    col_watchlist, col_quick_action = st.columns([3, 1])

    with col_quick_action:
        st.markdown("### ⚡ פעולה מהירה")
        symbol = st.text_input("חיפוש מניה", value="NVDA").upper()
        if not symbol:
            st.info("הקלד מניה להצגה")
            return

        data = get_stock_analysis(symbol)
        if data is None:
            st.error("המניה לא נמצאה או אין נתונים זמינים")
            return

        price = data['price']
        ma150 = data['ma150']

        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h1 class="stock-header rtl">{symbol}</h1>
            <span class="stock-price-lg">${price:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)

        diff_ma = ((price - ma150) / ma150) * 100 if ma150 else 0
        ma_color = "#10B981" if diff_ma > 0 else "#EF4444"
        st.markdown(f"""
        <div class="ma-box rtl">
            <span style="color:#888;">MA 150:</span> 
            <span style="font-family:'JetBrains Mono'; color:#fff; font-size:1.2rem;">${ma150:,.2f}</span>
            <span style="color:{ma_color}; margin-left:10px;">({diff_ma:+.2f}%)</span>
        </div>
        """, unsafe_allow_html=True)

        render_chart(data['hist'], f"{symbol} - שנה")

        if 'target_price' not in st.session_state or st.session_state['target_price'] == 0:
            st.session_state['target_price'] = price

        def update_from_input():
            st.session_state.target_price = st.session_state.n_input

        def update_from_slider():
            st.session_state.target_price = st.session_state.n_slider

        max_slider = price * 3 if price > 0 else 1000.0

        st.number_input("מחיר יעד ידני ($)", value=float(st.session_state.target_price),
                        step=0.5, key='n_input', on_change=update_from_input)
        st.slider("כוונון מחיר יעד", min_value=0.0, max_value=max_slider,
                  value=float(st.session_state.target_price), step=0.1,
                  key='n_slider', on_change=update_from_slider)

        final_target = st.session_state.target_price
        direction = "קנה מתחת" if final_target < price else "מכור מעל"
        st.markdown(f"**{direction}:** <span style='color:#FF7F50; font-family:JetBrains Mono; font-size:1.2rem;'>${final_target:.2f}</span>", unsafe_allow_html=True)

        vol = st.number_input("ווליום מינימלי (מיליונים)", value=5.0, step=1.0, format="%.1f")

        if st.button("הפעל התראה", use_container_width=True):
            min_price = final_target if final_target < price else 0
            max_price = final_target if final_target > price else 0
            save_alert(symbol, min_price, max_price, vol*1_000_000, True)

    with col_watchlist:
        st.markdown("### 📋 רשימת התראות")

        # הדגמה של התראות (תחליף בלולאה על נתוני DB אמיתיים בעתיד)
        sample_alerts = [
            {"symbol": "NVDA", "chg": 5.0, "price": 180.0, "vol": 10_000_000, "ma_dist": 5.0, "notes": "לבדוק דוחות", "active": True},
            {"symbol": "TSLA", "chg": -2.3, "price": 240.0, "vol": 5_200_000, "ma_dist": -1.2, "notes": "פוזיציה סודית", "active": True},
        ]

        for alert in sample_alerts:
            border_color = "#4CAF50" if alert["chg"] >= 0 else "#FF5555"
            active_text = "✅ פעיל" if alert["active"] else "❌ לא פעיל"
            st.markdown(f"""
            <div class="sticky-note rtl" style="border-color: {border_color};">
                <div class="sticky-note-header">{alert["symbol"]} | {active_text}</div>
                <div class="sticky-note-body">
                    <p><b>מחיר יעד:</b> {alert["chg"]:+.2f}% ({alert["price"]:.2f}$)</p>
                    <p><b>ווליום מינימלי:</b> {alert["vol"]:,}</p>
                    <p><b>מרחק ממוצע 150:</b> {alert["ma_dist"]:+.2f}%</p>
                    <p><b>הערות:</b> {alert["notes"]}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# RUN APP
# ==========================================
apply_terminal_css()

if not st.session_state.get('logged_in', False):
    auth_page()
else:
    dashboard_page()
