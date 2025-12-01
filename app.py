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
        #MainMenu, footer, header, .stDeployButton {
            visibility: hidden;
        }
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
        .ticker-move {
            display: inline-block;
            animation: ticker 45s linear infinite;
            font-family: 'JetBrains Mono', monospace;
            font-size: 1rem;
            color: #00FF00;
        }
        .ticker-item {
            display: inline-block;
            padding: 0 2rem;
        }
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
        # Light mode CSS adjustments 
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
        .ticker-move {
            display: inline-block;
            animation: ticker 45s linear infinite;
            font-family: 'JetBrains Mono', monospace;
            font-size: 1rem;
            color: #006400;
        }
        .ticker-item {
            display: inline-block;
            padding: 0 2rem;
        }
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

# ... (כל שאר פונקציות ה-backend נשמרות כפי שהן כולל login_user עם backdoor)

def apply_terminal_css():
    # תאימות לאחור: אם אין מצב שמור, ברירת מחדל מצב לילה
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = True
    apply_dynamic_css(st.session_state.dark_mode)


def auth_page():
    apply_terminal_css()
    col_img, col_form = st.columns([1.5, 1])
    with col_img:
        try:
            st.image("https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME/main/assets/logo.png", use_container_width=True)
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
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = True

    toggle = st.sidebar.checkbox("מצב לילה / יום", value=st.session_state.dark_mode, help="החלף בין מצב יום ומצב לילה")
    st.session_state.dark_mode = toggle

    apply_terminal_css()  # במקום apply_dynamic_css(...)


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

        # דוגמאות התראות עבור המחשה
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

def test_yahoo_connection_cached() -> bool:
    try:
        data = yf.download("NVDA", period="1d", progress=False)
        if data.empty:
            return False
        return True
    except:
        return False

# ==========================================
# 5. MAIN EXECUTION
# ==========================================
apply_terminal_css()

if not st.session_state.get('logged_in', False):
    auth_page()
else:
    page = st.session_state.get('page', 'dashboard')
    if page == 'archive':
        # ארכיון תוכן יכול להתווסף בהתאם, כרגע בדושבורד בלבד
        st.markdown("דף ארכיון יבוא בהמשך…")
    else:
        dashboard_page()

