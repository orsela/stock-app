import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.graph_objects as go
import hashlib
import time

# ==========================================
# CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="StockPulse Terminal 💹",
    layout="wide",
    page_icon="💹",
    initial_sidebar_state="collapsed"
)

# ==========================================
# STATE INITIALIZATION
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 'auth'
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_email' not in st.session_state: st.session_state.user_email = None
if 'alerts' not in st.session_state: st.session_state.alerts = []

# ==========================================
# CSS & THEME
# ==========================================
def apply_css():
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&display=swap');
    
    .stApp { 
        background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%);
        color: #FFFFFF; 
        font-family: 'Inter', sans-serif; 
    }
    
    #MainMenu, footer, header { visibility: hidden; }
    h1, h2, h3, h4, h5, h6 { color: #FFFFFF !important; }
    .stMetric { background: rgba(255,255,255,0.1); border-radius: 12px; padding: 1rem; }
    .metric-card { background: rgba(0,0,0,0.5); border: 1px solid #333; border-radius: 12px; padding: 1.5rem; margin: 0.5rem 0; }
    .alert-card { background: linear-gradient(45deg, #1e3c72, #2a5298); border: 1px solid #4a90e2; border-radius: 12px; padding: 1rem; margin: 0.5rem 0; cursor: grab; }
    .trash-zone { background: #2d1b1b; border: 3px dashed #ff4444; border-radius: 12px; height: 100px; display: flex; align-items: center; justify-content: center; color: #ff6666; text-align: center; }
    .rtl { direction: rtl; text-align: right; }
    .login-container { display: flex; height: 100vh; }
    .login-form { background: rgba(0,0,0,0.9); padding: 3rem; border-radius: 20px; border: 1px solid #333; max-width: 400px; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ==========================================
# DATA FUNCTIONS
# ==========================================
@st.cache_data(ttl=60)
def get_market_data():
    tickers = ['^GSPC', '^IXIC', 'BTC-USD', '^VIX']
    data = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='2d')
            if len(hist) > 1:
                current = hist['Close'][-1]
                prev = hist['Close'][-2]
                change = ((current - prev) / prev) * 100
                data[ticker] = (current, change)
        except:
            pass
    return data

def login_user(email, password):
    # Simple demo login
    if email == "admin" and password == "123":
        return True
    return False

# ==========================================
# LOGIN PAGE
# ==========================================
def login_page():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1,1])
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h1>💹 StockPulse</h1>
            <h3>המסוף המתקדם להתראות מניות</h3>
            <p style="color: #aaa; font-size: 1.1rem;">קבל יתרון תחרותי בזמן אמת</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="login-form rtl">', unsafe_allow_html=True)
        st.markdown('<h3>כניסה</h3>')
        
        with st.form("login_form"):
            email = st.text_input("📧 אימייל", placeholder="admin@stockpulse.com")
            password = st.text_input("🔒 סיסמה", type="password", placeholder="123")
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.form_submit_button("🚀 התחבר", use_container_width=True):
                    if login_user(email, password):
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.session_state.page = 'dashboard'
                        st.rerun()
                    else:
                        st.error("❌ אימייל או סיסמה שגויים")
            
            with col_btn2:
                if st.form_submit_button("🎯 דמו מהיר", use_container_width=True):
                    st.session_state.logged_in = True
                    st.session_state.user_email = "demo@stockpulse.com"
                    st.session_state.page = 'dashboard'
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# DASHBOARD
# ==========================================
def dashboard():
    # Header
    st.markdown("### 💹 נתוני שוק חיים")
    
    # Market Metrics
    data = get_market_data()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        val, chg = data.get('^GSPC', (0, 0))
        st.metric("S&P 500", f"{val:,.0f}", f"{chg:.2f}%")
    
    with col2:
        val, chg = data.get('^IXIC', (0, 0))
        st.metric("NASDAQ", f"{val:,.0f}", f"{chg:.2f}%")
    
    with col3:
        val, chg = data.get('BTC-USD', (0, 0))
        st.metric("Bitcoin", f"${val:,.0f}", f"{chg:.2f}%")
    
    with col4:
        val, chg = data.get('^VIX', (0, 0))
        st.metric("VIX", f"{val:.1f}", f"{chg:.2f}%")
    
    st.markdown("---")
    
    # Main Content
    col_left, col_right = st.columns([2, 1])
    
    # Alerts List
    with col_left:
        st.markdown("### 📋 רשימת התראות פעילות")
        
        if st.session_state.alerts:
            for i, alert in enumerate(st.session_state.alerts):
                st.markdown(f"""
                <div class="alert-card">
                    <div><strong>{alert['ticker']}</strong> | {alert['target']}% | ווליום: {alert['volume']}</div>
                    <div style="font-size: 0.9rem; color: #aaa;">{alert.get('notes', 'ללא הערות')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("אין התראות פעילות. צור התראה ראשונה!")
        
        # Trash Zone
        st.markdown('<div class="trash-zone rtl">🗑️ גרור התראות שהתממשו לכאן</div>', unsafe_allow_html=True)
    
    # Create Alert
    with col_right:
        st.markdown("### ➕ צור התראה חדשה")
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        
        with st.form("create_alert"):
            ticker = st.text_input("סימול", value="NVDA", help="למשל: AAPL, TSLA, BTC-USD")
            target = st.number_input("יעד שינוי (%)", value=5.0, min_value=0.1, step=0.5)
            volume = st.text_input("ווליום מינימלי", value="10M", placeholder="10M, 1B")
            whatsapp = st.checkbox("🔔 התראת וואטסאפ")
            notes = st.text_area("הערות", height=80, placeholder="הערות חשובות להתראה...")
            
            if st.form_submit_button("➕ הוסף התראה", use_container_width=True):
                new_alert = {
                    'id': len(st.session_state.alerts) + 1,
                    'ticker': ticker,
                    'target': target,
                    'volume': volume,
                    'whatsapp': whatsapp,
                    'notes': notes,
                    'created': datetime.now().strftime("%H:%M")
                }
                st.session_state.alerts.append(new_alert)
                st.success(f"✅ התראה ל-{ticker} נוספה!")
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Logout
    st.markdown("---")
    if st.button("🚪 יציאה", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ==========================================
# MAIN
# ==========================================
apply_css()

if not st.session_state.logged_in:
    login_page()
else:
    st.markdown(f"### שלום {st.session_state.user_email}")
    dashboard()
