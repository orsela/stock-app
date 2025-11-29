"""Stock Alerts v5.5 - Fixed Logos (Clearbit) + Stronger Theme Engine"""
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
    TEXT_SEC = "#b0b0b0"
    BTN_ICON = "☀️"
    BORDER = "#333333"
    INPUT_BG = "#262730"
else:
    BG_MAIN = "#ffffff"
    BG_CARD = "#f0f2f6"
    TEXT_MAIN = "#000000"
    TEXT_SEC = "#555555"
    BTN_ICON = "🌙"
    BORDER = "#d1d5db"
    INPUT_BG = "#ffffff"

# CSS אגרסיבי שדורס את ברירת המחדל של סטרימליט
st.markdown(f"""
<style>
    /* צבע רקע ראשי */
    .stApp {{
        background-color: {BG_MAIN};
    }}
    
    /* טקסטים גלובליים */
    h1, h2, h3, h4, h5, h6, p, label, span, div {{
        color: {TEXT_MAIN} !important;
    }}
    
    /* תיקון צבעי קלט (Input Fields) כדי שיראו טוב בשני המצבים */
    .stTextInput input, .stNumberInput input {{
        color: {TEXT_MAIN} !important;
        background-color: {INPUT_BG} !important;
        border-color: {BORDER} !important;
    }}
    
    /* Login/Card Container */
    .custom-card {{
        background-color: {BG_CARD};
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        border: 1px solid {BORDER};
        margin-bottom: 20px;
    }}
    
    /* Badges */
    .badge {{
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 0.8rem;
        color: white !important;
    }}
    .bg-green {{background-color: #28a745;}}
    .bg-red {{background-color: #dc3545;}}

    /* תמונת לוגו */
    .stock-logo {{
        width: 35px;
        height: 35px;
        border-radius: 50%;
        object-fit: contain;
        background-color: #fff; /* רקע לבן תמיד ללוגו */
        padding: 2px;
        border: 1px solid #ccc;
    }}
    
    /* מדדים למעלה - תיקון רקע */
    div[data-testid="metric-container"] {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER};
        padding: 10px;
        border-radius: 8px;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
#              לוגיקה (Backend)
# ==========================================

USERS_FILE = "users.json"
RULES_FILE = "rules.json"

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

def send_whatsapp(phone, symbol, price, min_p, max_p):
    try:
        if "twilio" not in st.secrets: return False
        sid = st.secrets["twilio"]["account_sid"]
        token = st.secrets["twilio"]["auth_token"]
        from_num = st.secrets["twilio"]["from_number"]
        if not sid or not token: return False
        from twilio.rest import Client
        client = Client(sid, token)
        msg = f"🚀 *Stock Alert*\n\n📈 *{symbol}*\n💰 Price: ${price}\n🎯 Range: ${min_p} - ${max_p}"
        client.messages.create(body=msg, from_=f'whatsapp:{from_num}', to=f'whatsapp:{phone}')
        return True
    except: return False

@st.cache_data(ttl=60)
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 1. מחיר
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        prev = info.get('previousClose')
        
        # 2. לוגו (שיטה חדשה: דרך Clearbit)
        # אנחנו לוקחים את הדומיין של החברה ומבקשים לוגו
        website = info.get('website', '')
        logo_url = "https://cdn-icons-png.flaticon.com/512/666/666201.png" # ברירת מחדל
        
        if website:
            # ניקוי ה-URL כדי לקבל רק domain.com
            domain = website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
            if domain:
                logo_url = f"https://logo.clearbit.com/{domain}"

        change = 0.0
        if price and prev:
            change = ((price - prev) / prev) * 100
            
        return {
            'price': round(price, 2), 
            'change': round(change, 2),
            'logo': logo_url
        } if price else None
    except: return None

# Session State
if 'user' not in st.session_state: st.session_state.user = None
if 'rules' not in st.session_state: st.session_state.rules = []

# ==========================================
#              UI - מסך כניסה
# ==========================================

if st.session_state.user is None:
    # Login Card Container
    st.markdown(f"""
    <div style="display: flex; justify-content: center; margin-top: 50px;">
        <div class="custom-card" style="width: 400px; text-align: center;">
            <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" width="60">
            <h2 style="margin-top:10px;">Welcome Back</h2>
            <p style="opacity: 0.7;">Sign in to monitor your portfolio</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Forms (מוזרקים מתחת לכרטיס ויזואלית)
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

# ==========================================
#              UI - דשבורד
# ==========================================
else:
    # Header
    c_title, c_theme = st.columns([9, 1])
    with c_title:
