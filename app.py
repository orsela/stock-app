"""Stock Alerts v5.0 - Ultimate UI + WhatsApp + Theme Toggle"""
import streamlit as st
import json, os, hashlib, time
import yfinance as yf
from datetime import datetime

# --- הגדרת עמוד בסיסית ---
st.set_page_config(page_title="StockWatcher", page_icon="📈", layout="wide")

# ==========================================
#              ניהול THEME (יום/לילה)
# ==========================================

if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'  # ברירת מחדל

# פונקציה להחלפת מצב
def toggle_theme():
    if st.session_state.theme == 'dark':
        st.session_state.theme = 'light'
    else:
        st.session_state.theme = 'dark'

# הגדרת צבעים לפי המצב הנוכחי
if st.session_state.theme == 'dark':
    BG_COLOR = "#0e1117"
    CARD_BG = "#1e293b"
    TEXT_COLOR = "white"
    BTN_ICON = "☀️"  # כפתור למעבר ליום
else:
    BG_COLOR = "#f8f9fa"
    CARD_BG = "#ffffff"
    TEXT_COLOR = "#111111"
    BTN_ICON = "🌙"  # כפתור למעבר ללילה

# הזרקת CSS דינמית בהתאם לבחירה
st.markdown(f"""
<style>
    .stApp {{
        background-color: {BG_COLOR};
        color: {TEXT_COLOR};
    }}
    /* עיצוב כרטיס הכניסה */
    div.login-card {{
        background-color: {CARD_BG};
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
        max-width: 400px;
        margin: 50px auto;
        border: 1px solid {'#333' if st.session_state.theme == 'dark' else '#eee'};
    }}
    h1, h2, h3, p {{ color: {TEXT_COLOR} !important; }}
    
    /* כפתור גוגל */
    .google-btn {{
        display: flex; align-items: center; justify-content: center;
        background-color: white; border: 1px solid #dadce0;
        border-radius: 40px; height: 50px; width: 100%;
        color: #3c4043; font-weight: 500; cursor: pointer;
        text-decoration: none; margin-bottom: 20px;
    }}
    
    /* כפתור טוגל ערכת נושא */
    .theme-btn {{
        border: 1px solid {TEXT_COLOR};
        border-radius: 50%;
        padding: 5px 10px;
        text-decoration: none;
        font-size: 20px;
        cursor: pointer;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
#              לוגיקה (Backend)
# ==========================================

USERS_FILE, RULES_FILE = "users.json", "rules.json"

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
    """שליחת הודעה אמיתית דרך Twilio"""
    try:
        # שליפת סודות
        sid = st.secrets["twilio"]["account_sid"]
        token = st.secrets["twilio"]["auth_token"]
        from_num = st.secrets["twilio"]["from_number"]
        
        from twilio.rest import Client
        client = Client(sid, token)
        
        msg_body = f"🚀 *Stock Alert*\n\n📈 *{symbol}*\n💰 מחיר: ${price}\n🎯 טווח: ${min_p} - ${max_p}"
        
        client.messages.create(
            body=msg_body,
            from_=f'whatsapp:{from_num}',
            to=f'whatsapp:{phone}'
        )
        return True
    except Exception as e:
        print(f"Twilio Error: {e}") # לוג פנימי
        return False

@st.cache_data(ttl=60)
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        return {'price': round(price, 2)} if price else None
    except: return None

# ניהול Session
if 'user' not in st.session_state: st.session_state.user = None
if 'rules' not in st.session_state: st.session_state.rules = []

# ==========================================
#              UI - מסך כניסה
# ==========================================

if st.session_state.user is None:
    # כותרת עליונה ריקה כדי לדחוף את התוכן למרכז
    st.write("") 
    st.markdown(f"""
    <div class="login-card">
        <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" width="60" style="margin-bottom:15px;">
        <h2 style="margin:0;">Welcome to StockWatcher</h2>
        <p style="opacity:0.7; margin-bottom:25px;">Sign in to monitor your portfolio</p>
        
        <a href="#" class="google-btn">
            <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" width="20" style="margin-right:10px;">
            Continue with Google
        </a>
        
        <div style="display:flex; align-items:center; margin: 20px 0; opacity:0.5; font-size:12px;">
            <div style="flex:1; height:1px; background:{TEXT_COLOR};"></div>
            <div style="padding:0 10px;">OR</div>
            <div style="flex:1; height:1px; background:{TEXT_COLOR};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # טופס סטרימליט רגיל שמוזרק ויזואלית לתוך הכרטיס
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
    # Header עם כפתור מצב לילה
    top_col1, top_col2 = st.columns([8, 1])
    with top_col1:
        st.markdown(f"### 👋 Hello, {st.session_state.user['email']}")
    with top_col2:
        if st.button(BTN_ICON, help="Switch Theme"):
            toggle_theme()
            st.rerun()
            
    st.divider()

    # סרגל צד
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2991/2991148.png", width=50)
        st.markdown("### Settings")
        whatsapp_num = st.text_input("WhatsApp Number", placeholder="+97250...", key="wa_num")
        st.caption("Required for alerts. Format: +972...")
        
        if st.button("Logout", type="primary"):
            st.session_state.user = None
            st.rerun()

    # טבלת מניות
    st.subheader("Your Watchlist")
    
    # הצגת התראות קיימות
    for i, rule in enumerate(st.session_state.rules):
        data = get_stock_data(rule['symbol'])
        if data:
            price = data['price']
            
            # בדיקת טווח ושליחת וואטסאפ
            status_color = "🟢"
            if price < rule['min'] or price > rule['max']:
                status_color = "🔴"
                # בדיקת קולדאון (פעם בשעה)
                last_alert = rule.get('last_alert')
                should_alert = False
                if not last_alert: should_alert = True
                else:
                    time_diff = (datetime.now() - datetime.fromisoformat(last_alert)).seconds
                    if time_diff > 3600: should_alert = True
                
                if should_alert and whatsapp_num:
                    if send_whatsapp(whatsapp_num, rule['symbol'], price, rule['min'], rule['max']):
                        rule['last_alert'] = datetime.now().isoformat()
                        # שמירה (דמה - כאן צריך לשמור לקובץ)
            
            # עיצוב השורה
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
                c1.markdown(f"**{rule['symbol']}**")
                c2.write(f"${price}")
                c3.caption(f"Range: ${rule['min']} - ${rule['max']}")
                c4.write(status_color)
                if c5.button("🗑️", key=f"del_{i}"):
                    st.session_state.rules.pop(i)
                    st.rerun()
            st.markdown("---")

    # הוספת חדש
    with st.expander("➕ Add New Alert"):
        with st.form("add_new"):
            c_sym, c_min, c_max = st.columns(3)
            sym = c_sym.text_input("Symbol (e.g. TSLA)")
            mi = c_min.number_input("Min Price", value=100.0)
            ma = c_max.number_input("Max Price", value=200.0)
            if st.form_submit_button("Add Watcher"):
                st.session_state.rules.append({'symbol': sym.upper(), 'min': mi, 'max': ma})
                st.rerun()
