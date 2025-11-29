"""Stock Alerts v5.7 - Edit Feature (Pop-up Dialog)"""
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
    BG_MAIN = "#0e1117"
    BG_CARD = "#1e293b"
    TEXT_MAIN = "#ffffff"
    BTN_ICON = "☀️"
    BORDER = "#333333"
    INPUT_BG = "#262730"
else:
    BG_MAIN = "#ffffff"
    BG_CARD = "#f0f2f6"
    TEXT_MAIN = "#000000"
    BTN_ICON = "🌙"
    BORDER = "#d1d5db"
    INPUT_BG = "#ffffff"

# CSS
st.markdown(f"""
<style>
    .stApp {{ background-color: {BG_MAIN}; }}
    h1, h2, h3, h4, h5, h6, p, label, span, div {{ color: {TEXT_MAIN} !important; }}
    
    .stTextInput input, .stNumberInput input {{
        color: {TEXT_MAIN} !important;
        background-color: {INPUT_BG} !important;
        border-color: {BORDER} !important;
    }}
    
    .custom-card {{
        background-color: {BG_CARD};
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid {BORDER};
        margin-bottom: 10px;
    }}
    
    .badge {{
        padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 0.8rem; color: white !important;
    }}
    .bg-green {{background-color: #28a745;}}
    .bg-red {{background-color: #dc3545;}}

    .stock-logo {{
        width: 35px; height: 35px; border-radius: 50%; object-fit: contain;
        background-color: #fff; padding: 2px; border: 1px solid #ccc;
    }}
    
    /* כפתורי פעולה קטנים */
    button[kind="secondary"] {{
        padding: 0px 10px;
        height: auto;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
#              BACKEND
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

@st.cache_data(ttl=60)
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        prev = info.get('previousClose')
        
        # Logo Logic
        website = info.get('website', '')
        logo_url = "https://cdn-icons-png.flaticon.com/512/666/666201.png"
        if website:
            domain = website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
            if domain: logo_url = f"https://logo.clearbit.com/{domain}"

        change = 0.0
        if price and prev:
            change = ((price - prev) / prev) * 100
            
        return {'price': round(price, 2), 'change': round(change, 2), 'logo': logo_url} if price else None
    except: return None

if 'user' not in st.session_state: st.session_state.user = None
if 'rules' not in st.session_state: st.session_state.rules = []

# ==========================================
#              DIALOGS (חלונות קופצים)
# ==========================================

@st.dialog("Edit Alert ✏️")
def edit_dialog(index, current_rule):
    st.write(f"Editing settings for **{current_rule['symbol']}**")
    
    col_min, col_max = st.columns(2)
    new_min = col_min.number_input("Min Price", value=float(current_rule['min']))
    new_max = col_max.number_input("Max Price", value=float(current_rule['max']))
    
    if st.button("Save Changes", type="primary"):
        # עדכון הכלל בזיכרון
        st.session_state.rules[index]['min'] = new_min
        st.session_state.rules[index]['max'] = new_max
        st.rerun()

# ==========================================
#              UI LOGIC
# ==========================================

# --- LOGIN SCREEN ---
if st.session_state.user is None:
    st.markdown(f"""
    <div style="display: flex; justify-content: center; margin-top: 50px;">
        <div class="custom-card" style="width: 400px; text-align: center;">
            <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" width="60">
            <h2 style="margin-top:10px;">Welcome Back</h2>
            <p style="opacity: 0.7;">Sign in to monitor your portfolio</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
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

# --- DASHBOARD SCREEN ---
else:
    c_title, c_theme = st.columns([9, 1])
    c_title.markdown(f"### 👋 Hello, {st.session_state.user['email']}")
    if c_theme.button(BTN_ICON, help="Switch Theme"):
        toggle_theme()
        st.rerun()
    
    st.divider()

    # Market Overview
    st.markdown("##### 📊 Market Status")
    m1, m2, m3 = st.columns(3)
    
    d_sp = get_stock_data("^GSPC")
    m1.metric("S&P 500", f"${d_sp['price']:,}" if d_sp else "--", f"{d_sp['change']}%" if d_sp else "--")
    
    d_nd = get_stock_data("^IXIC")
    m2.metric("NASDAQ", f"${d_nd['price']:,}" if d_nd else "--", f"{d_nd['change']}%" if d_nd else "--")
    
    d_btc = get_stock_data("BTC-USD")
    m3.metric("Bitcoin", f"${d_btc['price']:,}" if d_btc else "--", f"{d_btc['change']}%" if d_btc else "--")

    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.markdown("### Settings")
        whatsapp_num = st.text_input("WhatsApp Number", placeholder="+972...", key="wa")
        if st.button("Logout", type="primary"):
            st.session_state.user = None
            st.rerun()

    # Watchlist
    st.markdown("##### 📜 Your Watchlist")
    
    for i, rule in enumerate(st.session_state.rules):
        data = get_stock_data(rule['symbol'])
        
        # Start Card Wrapper
        st.markdown(f'<div class="custom-card" style="padding: 1rem;">', unsafe_allow_html=True)
        
        # Columns: Logo | Symbol | Price | Range | Status | Actions (Edit/Del)
        cols = st.columns([0.5, 1, 1, 2, 1, 1])
        
        if data:
            price = data['price']
            
            # 1. Logo
            cols[0].markdown(f'<img src="{data["logo"]}" class="stock-logo">', unsafe_allow_html=True)
            
            # 2. Symbol
            cols[1].markdown(f"**{rule['symbol']}**")
            
            # 3. Price
            cols[2].write(f"${price}")
            
            # 4. Range
            cols[3].write(f"${rule['min']} ➝ ${rule['max']}")
            
            # 5. Status Badge
            in_range = rule['min'] <= price <= rule['max']
            badge_class = "bg-green" if in_range else "bg-red"
            badge_text = "IN RANGE" if in_range else "OUT"
            cols[4].markdown(f'<span class="badge {badge_class}">{badge_text}</span>', unsafe_allow_html=True)
            
            # 6. Actions (Edit & Delete)
            with cols[5]:
                col_edit, col_del = st.columns(2)
                # כפתור עריכה
                if col_edit.button("✏️", key=f"edit_{i}", help="Edit Alert"):
                    edit_dialog(i, rule)
                
                # כפתור מחיקה
                if col_del.button("🗑️", key=f"del_{i}", help="Delete Alert"):
                    st.session_state.rules.pop(i)
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True) # End Card

    # Add New
    with st.expander("➕ Add Stock"):
        with st.form("new_stock"):
            c1, c2, c3 = st.columns(3)
            s = c1.text_input("Symbol", "TSLA")
            mn = c2.number_input("Min", 100.0)
            mx = c3.number_input("Max", 300.0)
            if st.form_submit_button("Add"):
                if s:
                    st.session_state.rules.append({'symbol': s.upper(), 'min': mn, 'max': mx})
                    st.rerun()
