"""Stock Alerts v5.4 - Stock Logos + Glowing Badges"""
import streamlit as st
import json, os, hashlib, time
import yfinance as yf
from datetime import datetime

# --- הגדרת עמוד ---
st.set_page_config(page_title="StockWatcher", page_icon="📈", layout="wide")

# ==========================================
#              ניהול THEME (יום/לילה)
# ==========================================

if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

def toggle_theme():
    if st.session_state.theme == 'dark':
        st.session_state.theme = 'light'
    else:
        st.session_state.theme = 'dark'

# הגדרת משתנים
if st.session_state.theme == 'dark':
    BG_COLOR = "#0e1117"
    CARD_BG = "#1e293b"
    TEXT_COLOR = "#ffffff"
    BTN_ICON = "☀️"
    BORDER_COLOR = "#333333"
else:
    BG_COLOR = "#f8f9fa"
    CARD_BG = "#ffffff"
    TEXT_COLOR = "#000000"
    BTN_ICON = "🌙"
    BORDER_COLOR = "#e0e0e0"

# CSS - עיצוב מתקדם לכרטיסים ותגיות
st.markdown(f"""
<style>
    .stApp {{
        background-color: {BG_COLOR};
        color: {TEXT_COLOR};
    }}
    
    /* Login Card */
    .login-container {{
        background-color: {CARD_BG};
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 1px solid {BORDER_COLOR};
        text-align: center;
        max-width: 400px;
        margin: 2rem auto;
    }}
    
    h1, h2, h3, p, div, span, label {{
        color: {TEXT_COLOR} !important;
    }}
    
    /* תגיות סטטוס זוהרות */
    .status-badge {{
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85em;
        color: white !important;
        display: inline-block;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }}
    .badge-green {{
        background-color: #00c853; /* ירוק בוהק */
    }}
    .badge-red {{
        background-color: #d50000; /* אדום בוהק */
    }}

    /* יישור תמונת לוגו */
    .stock-logo {{
        border-radius: 50%;
        vertical-align: middle;
        width: 30px;
        height: 30px;
        object-fit: contain;
        background-color: white; /* רקע לבן ללוגו כדי שיראה טוב בחושך */
        padding: 2px;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
#              לוגיקה (Backend)
# ==========================================

USERS_FILE = "users.json"

def load_users():
    return json.load(open(USERS_FILE)) if os.path.exists(USERS_FILE) else {}

def save_users(users):
    with open(USERS_FILE, 'w') as f: json.dump(users, f, indent=2)

def login_user(email, pw):
    users = load_users()
    if email in users and users[email]['password'] == hashlib.sha256(pw.encode()).hexdigest():
        return users[email]
    return None

def register_user(email, pw):
    users = load_users()
    if email in users: return False
    users[email] = {'password': hashlib.sha256(pw.encode()).hexdigest(), 'created': datetime.now().isoformat()}
    save_users(users)
    return True

# שליפת נתונים + לוגו
@st.cache_data(ttl=60)
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # מחירים
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        prev = info.get('previousClose')
        
        # לוגו (נסיון לשלוף)
        logo = info.get('logo_url', '')

        change = 0.0
        if price and prev:
            change = ((price - prev) / prev) * 100
            
        return {
            'price': round(price, 2), 
            'change': round(change, 2),
            'logo': logo
        } if price else None
    except: return None

# Session State
if 'user' not in st.session_state: st.session_state.user = None
if 'rules' not in st.session_state: st.session_state.rules = []

# ==========================================
#              UI - מסך כניסה
# ==========================================

if st.session_state.user is None:
    st.markdown(f"""
    <div class="login-container">
        <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" width="60">
        <h2 style="margin-top:10px;">Welcome to StockWatcher</h2>
        <p style="opacity:0.7; margin-bottom:20px;">Sign in to monitor your portfolio</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In", use_container_width=True):
                    user = login_user(email, password)
                    if user:
                        st.session_state.user = {'email': email}
                        st.rerun()
                    else: st.error("Login failed")
        with tab_signup:
            with st.form("signup_form"):
                new_email = st.text_input("Email")
                new_pass = st.text_input("Password", type="password")
                if st.form_submit_button("Create Account", use_container_width=True):
                    if register_user(new_email, new_pass):
                        st.success("Created! Please Login.")
                    else: st.error("User exists")

# ==========================================
#              UI - דשבורד ראשי
# ==========================================
else:
    # 1. Header
    top_col1, top_col2 = st.columns([8, 1])
    with top_col1:
        st.markdown(f"### 👋 Hello, {st.session_state.user['email']}")
    with top_col2:
        if st.button(BTN_ICON, help="Switch Theme"):
            toggle_theme()
            st.rerun()
            
    st.divider()

    # 2. Market Overview
    st.subheader("📊 Market Overview")
    m1, m2, m3 = st.columns(3)
    
    sp_data = get_stock_data("^GSPC")
    val_sp = f"${sp_data['price']:,}" if sp_data else "Loading..."
    delta_sp = f"{sp_data['change']}%" if sp_data else "0%"
    m1.metric("S&P 500", val_sp, delta_sp)
    
    nd_data = get_stock_data("^IXIC")
    val_nd = f"${nd_data['price']:,}" if nd_data else "Loading..."
    delta_nd = f"{nd_data['change']}%" if nd_data else "0%"
    m2.metric("NASDAQ", val_nd, delta_nd)
    
    btc_data = get_stock_data("BTC-USD")
    val_btc = f"${btc_data['price']:,}" if btc_data else "Loading..."
    delta_btc = f"{btc_data['change']}%" if btc_data else "0%"
    m3.metric("Bitcoin", val_btc, delta_btc)

    st.divider()

    # 3. Sidebar
    with st.sidebar:
        st.markdown("### Settings")
        if st.button("Logout", type="primary"):
            st.session_state.user = None
            st.rerun()

    # 4. Watchlist
    st.subheader("Your Watchlist")
    
    for i, rule in enumerate(st.session_state.rules):
        data = get_stock_data(rule['symbol'])
        if data:
            price = data['price']
            
            # בדיקת טווח וקביעת תגית
            in_range = rule['min'] <= price <= rule['max']
            if in_range:
                badge_html = '<span class="status-badge badge-green">IN RANGE</span>'
            else:
                badge_html = '<span class="status-badge badge-red">OUT</span>'
            
            # תצוגה
            with st.container():
                # חלוקה לעמודות: לוגו | שם | מחיר | טווח | סטטוס | מחיקה
                c_logo, c_sym, c_price, c_range, c_status, c_del = st.columns([0.5, 1, 1, 2, 1, 0.5])
                
                # לוגו
                with c_logo:
                    if data['logo']:
                        st.image(data['logo'], width=35)
                    else:
                        st.write("📈") # אייקון ברירת מחדל אם אין לוגו

                c_sym.markdown(f"**{rule['symbol']}**")
                c_price.write(f"${price}")
                c_range.markdown(f"${rule['min']} ➝ ${rule['max']}")
                
                # הזרקת התגית המעוצבת
                c_status.markdown(badge_html, unsafe_allow_html=True)
                
                if c_del.button("🗑️", key=f"del_{i}"):
                    st.session_state.rules.pop(i)
                    st.rerun()
            st.markdown("---")

    # Add New
    with st.expander("➕ Add New Alert"):
        with st.form("add_new"):
            c_sym, c_min, c_max = st.columns(3)
            sym = c_sym.text_input("Symbol (e.g. TSLA)")
            mi = c_min.number_input("Min Price", value=100.0)
            ma = c_max.number_input("Max Price", value=200.0)
            if st.form_submit_button("Add Watcher"):
                if sym:
                    st.session_state.rules.append({'symbol': sym.upper(), 'min': mi, 'max': ma})
                    st.rerun()
