import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import yfinance as yf
import hashlib
import plotly.graph_objects as go
import os # For checking local secrets file

# ==========================================
# 1. CONFIGURATION & PAGE SETUP
# ==========================================
st.set_page_config(
    page_title="StockPulse Terminal",
    layout="wide",
    page_icon="💹",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. DYNAMIC THEME CSS
# ==========================================
def apply_dynamic_css(dark_mode: bool):
    # CSS content defining the dark/light mode styles and UI elements (Logo, Sticky Notes, Trash Can)
    # NOTE: Only Dark Mode CSS is shown here for brevity and design consistency
    if dark_mode:
        css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&family=Permanent+Marker&display=swap');
        
        .stApp { background-color: #000000 !important; color: #FFFFFF !important; font-family: 'Inter', sans-serif; }
        #MainMenu, footer, header, .stDeployButton { visibility: hidden; }
        
        /* Logo Styling */
        .dashboard-logo-img-container { text-align: center; margin-bottom: 30px; padding-top: 20px; }
        .dashboard-logo-img { max-width: 300px; height: auto; display: block; margin-left: auto; margin-right: auto; }

        /* Sticky Note Styling */
        .sticky-note {
            background-color: #FFFFAA; border: 1px solid #CCCC00; padding: 15px; border-radius: 5px;
            margin-bottom: 20px; box-shadow: 3px 3px 5px rgba(0,0,0,0.3); position: relative;
            transform: rotate(1deg); font-family: 'Permanent Marker', cursive; color: #333; text-align: left;
        }
        .sticky-note-header {
            font-size: 1.5em; font-weight: bold; margin-bottom: 5px; color: #333; border-bottom: 1px dashed #CCC;
            padding-bottom: 5px; display: flex; justify-content: space-between; align-items: center;
        }
        .sticky-note-header .icons .icon-btn { cursor: pointer; margin-left: 8px; color: #555; }
        .sticky-note-header .icons .icon-btn:hover { color: #000; }
        .sticky-note-body { font-size: 1em; margin-bottom: 10px; }
        .sticky-note-footer { display: flex; justify-content: space-between; align-items: center; padding-top: 10px; border-top: 1px dashed #CCC; }
        .stCheckbox p { color: #333 !important; }
        
        /* Trash Can Styling */
        .trash-can-area {
            background-color: #222; border: 2px dashed #444; border-radius: 10px; padding: 30px; margin-top: 50px;
            text-align: center; color: #aaa; font-size: 1.2em;
        }
        .trash-can-area .trash-icon { font-size: 3em; color: #aaa; margin-bottom: 10px; }

        /* General Streamlit/RTL Overrides */
        .rtl { direction: rtl; text-align: right; font-family: 'Inter', sans-serif; }
        h3, h4, h5, h6 { text-align: right; direction: rtl; color: #fff; }
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
        """
        st.markdown(css, unsafe_allow_html=True)
    # ... (Light mode CSS omitted for brevity)

def apply_terminal_css():
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = True
    apply_dynamic_css(st.session_state.dark_mode)

# ==========================================
# 3. STATE INITIALIZATION
# ==========================================
if 'page' not in st.session_state: st.session_state['page'] = 'auth'
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

# ==========================================
# 4. BACKEND HELPERS (DB + AUTH + DATA)
# ==========================================
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # Fallback for local testing (requires secrets.json)
            if os.path.exists("secrets.json"):
                 creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
            else:
                 return None
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
    salt = "stockpulse_2025_salt" # Security Risk: Should be per-user, but okay for this context
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def check_hashes(password, hashed_text):
    salt = "stockpulse_2025_salt"
    return make_hashes(password) == hashed_text

def login_user(email, password):
    # DANGER: BACKDOOR for testing only! REMOVE IN PRODUCTION
    if email == "admin" and password == "123":
        return True

    if not email or not password:
        return False

    sheet = get_worksheet("USERS")
    if not sheet:
        # If DB connection fails, only the backdoor works
        return False

    try:
        data = sheet.get_all_records()
        if not data: return False
        df = pd.DataFrame(data)
        if 'email' not in df.columns or 'password' not in df.columns: return False
        user = df[df['email'] == email]
        if user.empty: return False

        stored_hash = user.iloc[0]['password']
        if check_hashes(password, stored_hash):
            return True
        return False
    except:
        # Catch any unexpected errors during DB lookup
        return False 
    
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

def save_alert(email, symbol, target, notes):
    # TODO: Implement full logic here
    pass 

# ==========================================
# 5. UI COMPONENTS
# ==========================================

def login_page():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        # Logo on Login Page
        st.markdown("""
            <div class="dashboard-logo-img-container">
                <img src="https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME/main/assets/logo.png" alt="StockPulse Logo" class="dashboard-logo-img" style="max-width: 250px;">
            </div>
        """, unsafe_allow_html=True)
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
    # --- 0. Logo at the Top ---
    # MUST update this path in YOUR live app!
    logo_path = "https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME/main/assets/logo.png"
    st.markdown(f"""
        <div class="dashboard-logo-img-container">
            <img src="{logo_path}" alt="StockPulse Logo" class="dashboard-logo-img">
        </div>
    """, unsafe_allow_html=True)

    # --- 1. Top Metrics Row (נתוני שוק חיים) ---
    st.markdown('<h3 class="rtl">נתוני שוק חיים</h3>', unsafe_allow_html=True)
    
    metrics = get_top_metrics() 
    
    m1, m2, m3, m4 = st.columns(4)
    
    def show_metric(col, label, key_name):
        val, chg = metrics.get(key_name, (0, 0))
        color = "normal"
        if chg > 0: color = "normal" 
        if chg < 0: color = "inverse" 
        col.metric(label=label, value=f"{val:,.2f}", delta=f"{chg:.2f}%")

    show_metric(m1, "S&P 500", "S&P 500")
    show_metric(m2, "NASDAQ 100", "NASDAQ")
    show_metric(m3, "BITCOIN", "BTC")
    show_metric(m4, "VIX Index", "VIX")

    st.write("---")

    # --- 2. Main Area (Split: Alerts List vs Create Alert) ---
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
            alert_notes = st.text_area("הערות להתראה", height=70, placeholder="הוסף כאן הערות חשובות על התראה זו...")

            submitted = st.form_submit_button("הוסף התראה", use_container_width=True)
            if submitted:
                # Placeholder success message
                st.success(f"התראה ל-{new_ticker} נוצרה!") 
        
        st.markdown('</div>', unsafe_allow_html=True)

    # --- צד שמאל: רשימת התראות (Alert List) ---
    with col_list:
        st.markdown('<h3 class="rtl">רשימת התראות</h3>', unsafe_allow_html=True)
        
        # --- פתקית התראה לדוגמה 1 (NVDA) ---
        st.markdown("""
        <div class="sticky-note">
            <div class="sticky-note-header">
                NVDA 
                <div class="icons">
                    <i class="fa-solid fa-pen-to-square icon-btn" title="ערוך התראה"></i>
                    <i class="fa-solid fa-trash-can icon-btn" title="מחק התראה"></i>
                </div>
            </div>
            <div class="sticky-note-body">
                <p><strong>מחיר יעד:</strong> +5.00% ($180.00)</p>
                <p><strong>ווליום מינ':</strong> 10,000,000</p>
                <p><strong>מרחק MA150:</strong> +5.00%</p>
                <p style="font-size:0.9em; margin-top: 10px; border-top: 1px dashed #CCC; padding-top: 5px;">
                    <em>"לבדוק את הדוחות הכספיים לפני כניסה לפוזיציה."</em>
                </p>
            </div>
            <div class="sticky-note-footer">
                <input type="checkbox" id="nvda_active" checked> <label for="nvda_active" style="color:#333;">פעיל</label>
                <button onclick="alert('גרף NVDA יציג כאן')" style="background-color: #4CAF50; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">📊 גרף NVDA</button>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- פתקית התראה לדוגמה 2 (TSLA) ---
        st.markdown("""
        <div class="sticky-note" style="transform: rotate(-2deg); margin-left: 20px;">
            <div class="sticky-note-header">
                TSLA
                <div class="icons">
                    <i class="fa-solid fa-pen-to-square icon-btn" title="ערוך התראה"></i>
                    <i class="fa-solid fa-trash-can icon-btn" title="מחק התראה"></i>
                </div>
            </div>
            <div class="sticky-note-body">
                <p><strong>מחיר יעד:</strong> -2.30% ($240.00)</p>
                <p><strong>ווליום מינ':</strong> 5,200,000</p>
                <p><strong>מרחק MA150:</strong> -1.20%</p>
                <p style="font-size:0.9em; margin-top: 10px; border-top: 1px dashed #CCC; padding-top: 5px;">
                    <em>"לשים לב להודעות של מאסק בטוויטר, יכול להשפיע."</em>
                </p>
            </div>
            <div class="sticky-note-footer">
                <input type="checkbox" id="tsla_active" checked> <label for="tsla_active" style="color:#333;">פעיל</label>
                <button onclick="alert('גרף TSLA יציג כאן')" style="background-color: #4CAF50; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">📊 גרף TSLA</button>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- פח אשפה בתחתית רשימת ההתראות ---
        st.markdown("""
        <div class="trash-can-area">
            <i class="fa-solid fa-trash-can trash-icon"></i>
            <p>גרור לכאן פתקיות התראה שהתממשו/בוטלו</p>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 6. MAIN ROUTING LOGIC
# ==========================================

apply_terminal_css()

if not st.session_state['logged_in']:
    login_page()
else:
    main_dashboard()
