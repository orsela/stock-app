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
# 1. CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="StockPulse Terminal",
    layout="wide",
    page_icon="💹",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. TERMINAL CSS (The Design Layer)
# ==========================================
def apply_terminal_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&display=swap');
        
        .stApp { background-color: #000000; color: #FFFFFF; font-family: 'Inter', sans-serif; }
        #MainMenu, footer, header, .stDeployButton {visibility: hidden;}

        h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel { color: #FFFFFF !important; opacity: 1 !important; }
        
        /* Logo Styling */
        .dashboard-logo { font-size: 2.2rem; font-weight: 900; color: #FFFFFF; margin: 0; letter-spacing: -1px; line-height: 1; }
        .dashboard-sub { font-family: 'JetBrains Mono', monospace; color: #FF7F50; font-size: 0.8rem; letter-spacing: 1px; }
        .logo-title { font-size: 3rem; font-weight: 900; text-align: center; margin-bottom: 5px; }
        
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

        /* Widgets */
        .ticker-wrap { width: 100%; overflow: hidden; background-color: #111; border-bottom: 1px solid #333; padding: 10px 0; margin-bottom: 20px; white-space: nowrap; }
        .ticker-move { display: inline-block; animation: ticker 35s linear infinite; }
        .ticker-item { display: inline-block; padding: 0 2rem; font-family: 'JetBrains Mono', monospace; font-size: 1rem; color: #00FF00; }
        @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

        .stock-header { font-size: 2.5rem; font-weight: 900; color: #FF7F50; margin: 0; }
        .stock-price-lg { font-size: 2rem; font-family: 'JetBrains Mono'; font-weight: 700; }
        .ma-box { background: #222; border: 1px solid #444; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. STATE INITIALIZATION
# ==========================================
if 'page' not in st.session_state: st.session_state['page'] = 'auth'
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None
if 'target_price' not in st.session_state: st.session_state['target_price'] = 0.0

# ==========================================
# 4. BACKEND INTEGRATION
# ==========================================
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # Fallback for local testing if secrets.toml isn't set up
            try:
                creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
            except:
                return None
        return gspread.authorize(creds)
    except: return None

def get_worksheet(sheet_name):
    client = get_client()
    if client:
        try: return client.open("StockWatcherDB").worksheet(sheet_name)
        except: return None
    return None

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

def add_user_to_db(email, password, phone):
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and 'email' in df.columns and email in df['email'].values:
            return False
    except: pass
    row = [email, make_hashes(password), str(datetime.now()), phone]
    try: sheet.append_row(row); return True
    except: return False

def login_user(email, password):
    # Dummy login for testing if DB fails - REMOVE IN PRODUCTION IF DB IS STABLE
    if email == "admin" and password == "admin": return True 
    
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        data = sheet.get_all_records()
        if not data: return False
        df = pd.DataFrame(data)
        if 'email' not in df.columns: return False
        user = df[df['email'] == email]
        if user.empty: return False
        if check_hashes(password, user.iloc[0]['password']): return True
    except: pass
    return False

# --- Helper for safe data extraction ---
def safe_float(val):
    try: return float(val)
    except: return 0.0

@st.cache_data(ttl=30)
def get_top_metrics():
    tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "BTC": "BTC-USD", "VIX": "^VIX"}
    data = {}
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            h = t.history(period="2d")
            if len(h) >= 2:
                curr = h['Close'].iloc[-1]
                prev = h['Close'].iloc[-2]
                chg = ((curr - prev) / prev) * 100
                data[name] = (curr, chg)
            else: data[name] = (0,0)
        except: data[name] = (0,0)
    return data

@st.cache_data(ttl=60)
def get_stock_analysis(symbol):
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="1y")
        if hist.empty: return None
        current = hist['Close'].iloc[-1]
        ma150 = 0.0
        if len(hist) >= 150:
            ma150 = hist['Close'].rolling(window=150).mean().iloc[-1]
        return {"price": current, "ma150": ma150, "hist": hist, "symbol": symbol}
    except: return None

# פונקציה מנוטרלת זמנית (Stub)
def save_alert(email, symbol, target):
    # TODO: Implement full logic later
    pass 

# ==========================================
# 5. UI & MAIN LOGIC (Clean Version)
# ==========================================

def login_page():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="logo-title">StockPulse</div>', unsafe_allow_html=True)
        st.write("---")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if login_user(email, password):
                st.session_state['logged_in'] = True
                st.session_state['user_email'] = email
                st.rerun()
            else:
                st.error("Login Failed")
 
def main_dashboard():
    # --- CSS להתאמה לעברית ועיצוב כהה ---
    st.markdown("""
        <style>
        .rtl { direction: rtl; text-align: right; font-family: 'Inter', sans-serif; }
        .metric-card { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; text-align: center; }
        .stMetric { text-align: center !important; }
        /* התאמת כותרות לעברית */
        h3 { text-align: right; direction: rtl; color: #fff; }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. Top Metrics Row (נתוני שוק חיים) ---
    st.markdown('<h3 class="rtl">נתוני שוק חיים</h3>', unsafe_allow_html=True)
    
    # שליפת נתונים אמיתיים (או 0 אם אין חיבור)
    metrics = get_top_metrics() 
    
    # יצירת 4 עמודות למדדים
    m1, m2, m3, m4 = st.columns(4)
    
    # פונקציית עזר להצגת מדד יפה
    def show_metric(col, label, key_name):
        val, chg = metrics.get(key_name, (0, 0))
        color = "normal"
        if chg > 0: color = "normal" # ירוק בברירת מחדל של סטרימליט
        if chg < 0: color = "inverse" # אדום
        col.metric(label=label, value=f"{val:,.2f}", delta=f"{chg:.2f}%")

    show_metric(m1, "S&P 500", "S&P 500")
    show_metric(m2, "NASDAQ 100", "NASDAQ")
    show_metric(m3, "BITCOIN", "BTC")
    show_metric(m4, "VIX Index", "VIX")

    st.write("---")

    # --- 2. Main Area (Split: Alerts List vs Create Alert) ---
    # יחס של 1:2 (רשימה רחבה משמאל, יצירה צרה מימין)
    col_list, col_create = st.columns([2, 1])

    # --- צד ימין: צור התראה (Create Alert) ---
    with col_create:
        st.markdown('<div class="rtl" style="background: #111; padding: 20px; border-radius: 10px; border: 1px solid #444;">', unsafe_allow_html=True)
        st.markdown('<h4 class="rtl">צור התראה</h4>', unsafe_allow_html=True)
        
        with st.form("create_alert_form"):
            new_ticker = st.text_input("Ticker", value="NVDA")
            target_price = st.number_input("שינוי מחיר (%)", value=5.0)
            min_vol = st.text_input("ווליום מינימלי", value="10M")
            whatsapp_notify = st.checkbox("התראה בווצאפ", value=True)
            
            submitted = st.form_submit_button("הוסף התראה", use_container_width=True)
            if submitted:
                # כאן נחבר אחר כך את הוספת ההתראה לדאטהבייס
                st.success(f"התראה ל-{new_ticker} נוצרה!")
        
        st.markdown('</div>', unsafe_allow_html=True)

    # --- צד שמאל: רשימת התראות (Alert List) ---
    with col_list:
        st.markdown('<h3 class="rtl">רשימת התראות</h3>', unsafe_allow_html=True)
        
        # --- דוגמה לכרטיס התראה (Hardcoded בינתיים, כמו בתמונה) ---
        # בעתיד נחליף את זה בלולאה שרצה על הנתונים מה-DB
        
        st.markdown("""
        <div style="background-color: #262730; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-right: 5px solid #4CAF50;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin:0; color: white;">NVDA</h2>
                    <span style="color: #4CAF50; font-weight: bold;">+5.00%</span> | $180.00
                </div>
                <div style="text-align: right; color: #aaa; font-size: 0.8em;">
                    ווליום: 10,000,000<br>
                    מרחק ממוצע 150: +5.00%
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # כפתורים מתחת לכרטיס (בתוך עמודות פנימיות ליישור)
        b1, b2 = st.columns([1, 4])
        with b1:
            st.toggle("פעיל", value=True, key="toggle_nvda_1")
        with b2:
            st.button("📊 גרף NVDA", key="btn_nvda_1", use_container_width=True)

        # --- כרטיס דוגמה שני ---
        st.markdown("""
        <div style="background-color: #262730; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-right: 5px solid #4CAF50;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin:0; color: white;">TSLA</h2>
                    <span style="color: #FF5555; font-weight: bold;">-2.30%</span> | $240.00
                </div>
                <div style="text-align: right; color: #aaa; font-size: 0.8em;">
                    ווליום: 5,200,000<br>
                    מרחק ממוצע 150: -1.20%
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        b3, b4 = st.columns([1, 4])
        with b3:
            st.toggle("פעיל", value=True, key="toggle_tsla_1")
        with b4:
            st.button("📊 גרף TSLA", key="btn_tsla_1", use_container_width=True)
# --- Main Execution Block ---
apply_terminal_css()

if not st.session_state['logged_in']:
    login_page()
else:
    main_dashboard()


