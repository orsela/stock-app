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
# CONFIGURATION, CSS & BACKEND FUNCTIONS
# ==========================================
st.set_page_config(
    page_title="StockPulse Terminal",
    layout="wide",
    page_icon="💹",
    initial_sidebar_state="collapsed"
)

def apply_terminal_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&family=Permanent+Marker&display=swap');

    .stApp { background-color: #000000; color: #FFFFFF; font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header, .stDeployButton {visibility: hidden;}
    h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel { color: #FFFFFF !important; opacity: 1 !important; }
    
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

    /* Widgets & Layout */
    .rtl { direction: rtl; text-align: right; font-family: 'Inter', sans-serif; }
    h3, h4, h5, h6 { text-align: right; direction: rtl; color: #fff; }
    .metric-card { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; text-align: center; }
    .stMetric { text-align: center !important; }

    /* Logo Styling */
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

    /* Sticky Notes */
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

    /* Trash Can Styling for future */
    .trash-can-area {
        background-color: #222;
        border: 2px dashed #444;
        border-radius: 10px;
        padding: 30px;
        margin-top: 50px;
        text-align: center;
        color: #aaa;
        font-size: 1.2em;
        transition: background-color 0.3s ease;
    }
    .trash-can-area.drag-over {
        background-color: #333;
        border-color: #FF7F50;
    }
    .trash-can-area .trash-icon {
        font-size: 3em;
        color: #aaa;
        margin-bottom: 10px;
    }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    """, unsafe_allow_html=True)

# המשך פונקציות backend כפי בקוד המלא הקודם, כולל login_user, add_user_to_db, get_stock_analysis, etc.

# דוגמת מסך הדשבורד שמשלבת עיצוב sticky-note למקטעי ההתראות
def dashboard_page():
    apply_terminal_css()

    # לוגו גרפי למעלה - אפשר לשנות src אם יש לך לוגו משלך
    st.markdown("""
    <div class="dashboard-logo-img-container">
        <img src="https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME/main/assets/logo.png" class="dashboard-logo-img" alt="StockPulse Logo">
    </div>
    """, unsafe_allow_html=True)

    # נתונים ראשיים - show market metrics
    metrics = get_top_metrics()
    m1, m2, m3, m4 = st.columns(4)
    def show_metric(col, label, key_name):
        val, chg = metrics.get(key_name, (0,0))
        color = "#10B981" if chg > 0 else "#EF4444"
        col.markdown(f"""
        <div class="metric-card">
            <div style="color:#888; font-size:0.8rem;">{label}</div>
            <div style="font-family:'JetBrains Mono'; font-size:1.5rem; color:#fff;">{val:,.2f}</div>
            <div style="color:{color}; font-weight:bold;">{chg:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    show_metric(m1, "S&P 500", "S&P 500")
    show_metric(m2, "NASDAQ 100", "NASDAQ")
    show_metric(m3, "BITCOIN", "BTC")
    show_metric(m4, "VIX Index", "VIX")

    st.markdown("---")

    col_alerts, col_create = st.columns([2,1])

    with col_create:
        st.markdown('<div class="rtl" style="background:#111; padding:20px; border-radius:10px; border:1px solid #444;">', unsafe_allow_html=True)
        st.markdown('<h4 class="rtl">צור התראה חדשה</h4>', unsafe_allow_html=True)
        with st.form("create_alert_form"):
            new_ticker = st.text_input("Ticker", value="NVDA")
            target_change = st.number_input("שינוי מחיר יעד (%)", value=5.0)
            min_vol = st.text_input("ווליום מינימלי", value="10M")
            whatsapp_notify = st.checkbox("קבלת התראה בוואצאפ", value=True)
            notes = st.text_area("הערות להתראה", height=80, placeholder="הוסף כאן מידע חשוב...")

            submitted = st.form_submit_button("צור התראה")
            if submitted:
                # כאן תוכל לקרוא לsave_alert או לשמור בהתראות
                st.success(f"ההתראה ל-{new_ticker} נוצרה בהצלחה!")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_alerts:
        st.markdown('<h3 class="rtl">רשימת התראות</h3>', unsafe_allow_html=True)

        # דוגמאות מעוצבות של התראות (במקום לולאה על התראות אמיתיות)
        alerts = [
            {"symbol": "NVDA", "target": "+5.00%", "price": "$180.00", "vol": "10,000,000", "ma_dist": "+5.00%", "notes": "לבדוק דוחות", "active": True},
            {"symbol": "TSLA", "target": "-2.30%", "price": "$240.00", "vol": "5,200,000", "ma_dist": "-1.20%", "notes": "פוזיציה סודית", "active": True}
        ]

        for alert in alerts:
            style_rot = "transform: rotate(1deg);" if alert["symbol"]=="NVDA" else "transform: rotate(-2deg); margin-left:20px;"
            border_color = "#4CAF50" if not alert["target"].startswith("-") else "#FF5555"
            active_text = "✅ פעיל" if alert["active"] else "❌ לא פעיל"

            st.markdown(f"""
            <div class="sticky-note" style="{style_rot} border-color: {border_color};">
                <div class="sticky-note-header rtl">
                    {alert["symbol"]} | {active_text}
                </div>
                <div class="sticky-note-body rtl">
                    <p><b>מחיר יעד:</b> {alert["target"]} ({alert["price"]})</p>
                    <p><b>ווליום מינימלי:</b> {alert["vol"]}</p>
                    <p><b>מרחק ממוצע 150:</b> {alert["ma_dist"]}</p>
                    <p><b>הערות:</b> {alert["notes"]}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ==========================================
# 6. RUN APP
# ==========================================
apply_terminal_css()

if not st.session_state.get('logged_in', False):
    # דף כניסה פשוט
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="logo-title">StockPulse</div>', unsafe_allow_html=True)
        st.write("---")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Authenticate", use_container_width=True):
            if login_user(email, password):
                st.session_state['user_email'] = email
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("Access Denied")
else:
    dashboard_page()
