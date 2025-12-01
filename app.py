import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import yfinance as yf
import hashlib
import plotly.graph_objects as go
import os
from urllib.parse import quote

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

# נתיבים קבועים (משתמש בנתיב המאושר שלך)
GITHUB_USER = "orsela" 
REPO_NAME = "stock-app"
LOGO_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/assets/logo_light_bg.png"
GOOGLE_ICON_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/assets/google_icon.png"

def apply_dynamic_css(dark_mode: bool):
    # CSS content defining the dark/light mode styles and UI elements
    
    if dark_mode:
        css = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&family=Permanent+Marker&display=swap');
        
        .stApp {{ background-color: #000000 !important; color: #FFFFFF !important; font-family: 'Inter', sans-serif; }}
        #MainMenu, footer, header, .stDeployButton {{ visibility: hidden; }}

        /* General Styling */
        h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel {{ color: #FFFFFF !important; opacity: 1 !important; }}
        .rtl {{ direction: rtl; text-align: right; font-family: 'Inter', sans-serif; }}
        
        /* Input & Button Styling */
        .stTextInput > div > div > input, .stNumberInput > div > div > input {{ background-color: #111 !important; border: 1px solid #333 !important; color: #FFFFFF !important; font-family: 'JetBrains Mono', monospace !important; }}
        .stButton > button {{ background-color: #FF7F50 !important; color: #000000 !important; border: none !important; font-weight: 800 !important; border-radius: 4px !important; text-transform: uppercase; font-size: 1rem; transition: all 0.2s ease; }}
        .stButton > button:hover {{ background-color: #FF6347 !important; transform: scale(1.02); }}

        /* Login Page Layout */
        .login-container {{ display: flex; flex-direction: row; width: 100%; height: 100vh; margin: -20px; }}
        .login-image-side {{ 
            flex: 1; 
            background: #111122;
            background-image: url('https://upload.wikimedia.org/wikipedia/commons/b/b3/Candlestick_Chart_Example.png');
            background-size: cover;
            background-position: center;
            display: flex; align-items: flex-end; justify-content: flex-start; 
            padding: 50px;
            position: relative;
        }}
        .login-image-side::after {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.4);
        }}
        .login-form-side {{ flex: 1; background-color: #000000; padding: 80px 100px; color: #FFFFFF; display: flex; flex-direction: column; justify-content: center; }}
        
        /* Image side text */
        .welcome-text {{ font-size: 2.2rem; font-weight: 900; color: #FFFFFF; line-height: 1.2; z-index: 10; }}
        .login-form-side h2 {{ font-size: 2.5rem; font-weight: 900; color: #FF7F50; margin-bottom: 5px; text-align: right; direction: rtl; }}
        
        /* Wide Google Button Styling */
        #google_wide_btn_container button {{
            background-color: #111 !important;
            color: #FFFFFF !important;
            border: 1px solid #444 !important;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 10px 20px !important;
            font-weight: 600 !important;
            font-size: 1em !important;
        }}
        #google_wide_btn_container button:hover {{
            background-color: #222 !important;
        }}
        #google_icon_in_btn {{
            width: 20px;
            height: 20px;
            margin-left: 10px; /* רווח לימין הטקסט בעברית */
        }}

        /* Login Tabs */
        .login-tabs {{ display: flex; margin-bottom: 30px; }}
        .login-tabs div {{ padding: 10px 20px; cursor: pointer; font-weight: 600; color: #AAAAAA; }}
        .login-tabs .active {{ border-bottom: 3px solid #FF7F50; color: #FFFFFF; }}

        /* Dashboard Specific Styles */
        .dashboard-logo-img-container {{ text-align: center; margin-bottom: 30px; padding-top: 20px; }}
        .dashboard-logo-img {{ max-width: 300px; height: auto; display: block; margin-left: auto; margin-right: auto; }}
        
        /* Sticky Note Styling */
        .sticky-note {{
            background-color: #FFFFAA; border: 1px solid #CCCC00; padding: 15px; border-radius: 5px;
            margin-bottom: 20px; box-shadow: 3px 3px 5px rgba(0,0,0,0.3); position: relative;
            transform: rotate(1deg); font-family: 'Permanent Marker', cursive; color: #333; text-align: left;
        }}
        .sticky-note-header {{
            font-size: 1.5em; font-weight: bold; margin-bottom: 5px; color: #333; border-bottom: 1px dashed #CCC;
            padding-bottom: 5px; display: flex; justify-content: space-between; align-items: center;
        }}
        .sticky-note-header .icons .icon-btn {{ cursor: pointer; margin-left: 8px; color: #555; }}
        .sticky-note-header .icons .icon-btn:hover {{ color: #000; }}
        .sticky-note-body {{ font-size: 1em; margin-bottom: 10px; }}
        .sticky-note-footer {{ display: flex; justify-content: space-between; align-items: center; padding-top: 10px; border-top: 1px dashed #CCC; }}
        .stCheckbox p {{ color: #333 !important; }}
        .trash-can-area {{ background-color: #222; border: 2px dashed #444; border-radius: 10px; padding: 30px; margin-top: 50px; text-align: center; color: #aaa; font-size: 1.2em; }}
        .trash-can-area .trash-icon {{ font-size: 3em; color: #aaa; margin-bottom: 10px; }}

        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
        """
        st.markdown(css, unsafe_allow_html=True)
    

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
def get_client(): return None
def get_worksheet(sheet_name): return None
def make_hashes(password): return hashlib.sha256(password.encode()).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

def login_user(email, password):
    # DANGER: BACKDOOR for testing only! 
    if email == "admin" and password == "123": return True
    # Placeholder for actual login logic
    return False

def simulate_google_login_success():
    st.session_state['logged_in'] = True
    st.session_state['user_email'] = "google_user@stockpulse.com"
    st.rerun()

@st.cache_data(ttl=30)
def get_top_metrics():
    # Placeholder for real data fetching from yfinance
    try:
        tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "BTC": "BTC-USD", "VIX": "^VIX"}
        data = {}
        for name, symbol in tickers.items():
            t = yf.Ticker(symbol)
            h = t.history(period="2d")
            if len(h) >= 2:
                curr = h['Close'].iloc[-1]
                prev = h['Close'].iloc[-2]
                chg = ((curr - prev) / prev) * 100
                data[name] = (curr, chg)
            else: data[name] = (0,0)
        return data
    except Exception:
        # Fallback hardcoded data if yfinance fails (common in streamlit cloud free tier)
        return {"S&P 500": (5142.78, 0.63), "NASDAQ": (16173.61, 0.81), "BTC": (68490.1, -1.25), "VIX": (15.55, 3.1)}


def save_alert(email, symbol, target, notes):
    pass 

# ==========================================
# 5. UI COMPONENTS
# ==========================================

def login_page():
    
    # --- 1. Container for Split View ---
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # --- 2. Image Side (Left Side - Static UI) ---
    st.markdown(f"""
        <div class="login-image-side">
            <div style="z-index: 10;">
                <img src="{LOGO_URL}" alt="StockPulse Logo" style="max-width: 250px; margin-bottom: 20px;">
                <div class="welcome-text">Welcome Back to Your Real-Time Edge</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # --- 3. Form Side (Right Side - Streamlit Components) ---
    st.markdown('<div class="login-form-side">', unsafe_allow_html=True)
    
    # Tabs (Login / Sign Up) - Placeholder UI
    st.markdown("""
        <div class="login-tabs">
            <div class="active">LOG IN</div>
            <div>SIGN UP</div>
        </div>
    """, unsafe_allow_html=True)
    
    # --- Standard Login Form ---
    with st.form("login_form", clear_on_submit=False):
        
        # Input: Email
        st.markdown('<div style="color: white; direction: rtl; text-align: right; margin-top: 10px;">אימייל</div>', unsafe_allow_html=True)
        email = st.text_input("אימייל", placeholder="הכנס אימייל", label_visibility="collapsed", key="email_input")
        
        # Input: Password
        st.markdown('<div style="color: white; direction: rtl; text-align: right; margin-top: 10px;">סיסמה</div>', unsafe_allow_html=True)
        password = st.text_input("סיסמה", type="password", placeholder="הכנס סיסמה", label_visibility="collapsed", key="password_input")
        
        # Forgot Password Link
        st.markdown('<div style="text-align: right; margin-top: 15px; margin-bottom: 25px;"><a href="#" style="color: #AAAAAA; font-size: 0.9em;">Forgot Password?</a></div>', unsafe_allow_html=True)

        # Main Login Button
        submitted = st.form_submit_button("LOG IN", use_container_width=True)
        
        if submitted:
            if login_user(email, password):
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("התחברות נכשלה. אנא ודא שם משתמש וסיסמה. (רמז: admin/123)")
                
    st.write("---")
    
    # --- Social Login (Wide Google Button) ---
    st.markdown('<div style="text-align: center; color: #AAAAAA; margin-bottom: 15px;">OR LOG IN WITH</div>', unsafe_allow_html=True)
    
    # Hack to create a wide button with an image inside and simulate click
    st.markdown('<div id="google_wide_btn_container">', unsafe_allow_html=True)
    
    # The actual Streamlit button that captures the click
    if st.button(f'<img src="{GOOGLE_ICON_URL}" id="google_icon_in_btn" alt="Google"> התחבר באמצעות גוגל', 
                 key="google_wide_btn", 
                 use_container_width=True,
                 unsafe_allow_html=True): 
        simulate_google_login_success()
        
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Don't have an account link
    st.markdown('<div style="text-align: center; margin-top: 50px; color: #AAAAAA;">Don\'t have an account? <a href="#" style="color: #FF7F50;">Sign Up</a></div>', unsafe_allow_html=True)


    st.markdown('</div>', unsafe_allow_html=True) # Close login-form-side
    st.markdown('</div>', unsafe_allow_html=True) # Close login-container

def main_dashboard():
    # --- 0. Logo at the Top ---
    st.markdown(f"""
        <div class="dashboard-logo-img-container">
            <img src="{LOGO_URL}" alt="StockPulse Logo" class="dashboard-logo-img">
        </div>
    """, unsafe_allow_html=True)

    # --- 1. Top Metrics Row (נתוני שוק חיים) ---
    st.markdown('<h3 class="rtl">נתוני שוק חיים</h3>', unsafe_allow_html=True)
    
    metrics = get_top_metrics() 
    
    m1, m2, m3, m4 = st.columns(4)
    
    def show_metric(col, label, key_name):
        val, chg = metrics.get(key_name, (0, 0))
        # Logic to determine color for delta text (Streamlit handles this normally, but custom is better)
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
            # Note: RTL inputs are complex in Streamlit. Using LTR placeholders for stability.
            new_ticker = st.text_input("Ticker", value="NVDA", placeholder="סימול המניה")
            target_price = st.number_input("שינוי מחיר (%)", value=5.0, placeholder="יעד ב-%")
            min_vol = st.text_input("ווליום מינימלי", value="10M", placeholder="ווליום מינ' (למשל 10M)")
            whatsapp_notify = st.checkbox("התראה בווצאפ", value=True)
            alert_notes = st.text_area("הערות להתראה", height=70, placeholder="הוסף כאן הערות חשובות על התראה זו...")

            submitted = st.form_submit_button("הוסף התראה", use_container_width=True)
            if submitted:
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
        
    if st.button("יציאה", key="logout_btn", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

# ==========================================
# 6. MAIN ROUTING LOGIC
# ==========================================

apply_terminal_css()

if not st.session_state['logged_in']:
    login_page()
else:
    main_dashboard()
