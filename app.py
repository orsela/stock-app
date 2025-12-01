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
# 1. CONFIGURATION & PATHS
# ==========================================
st.set_page_config(
    page_title="StockPulse Terminal",
    layout="wide",
    page_icon="💹",
    initial_sidebar_state="collapsed"
)

# נתיבים קבועים (ודא שהם תואמים לנתיב ב-GitHub שלך!)
GITHUB_USER = "orsela" 
REPO_NAME = "stock-app"
BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/assets"
LOGO_LIGHT_BG_URL = f"{BASE_URL}/logo_light_bg.png"       # לוגו למסך כניסה
LOGO_DASHBOARD_URL = f"{BASE_URL}/logo_dashboard.png"     # לוגו לדאשבורד
DASHBOARD_BG_URL = f"{BASE_URL}/dashboard_background.png" # רקע ראשי

# ==========================================
# 2. DYNAMIC THEME CSS
# ==========================================
def apply_dynamic_css(dark_mode: bool):
    if dark_mode:
        css = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&family=Permanent+Marker&display=swap');
        
        /* --- GLOBAL BACKGROUND AND FADING EFFECT --- */
        .stApp {{ 
            background-image: url('{DASHBOARD_BG_URL}');
            background-size: cover;
            background-attachment: fixed; /* רקע קבוע גם בגלילה */
            position: relative;
            background-color: #000000;
            color: #FFFFFF; 
            font-family: 'Inter', sans-serif; 
        }}
        /* Overlay for fading effect (75% opacity black) */
        .stApp::before {{
            content: '';
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.75); /* שכבה שחורה חצי שקופה */
            z-index: -1; 
        }}
        
        /* --- FIXED HEADER (LOGO) --- */
        .fixed-logo-header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000; 
            background-color: rgba(0, 0, 0, 0.85); /* רקע כהה קבוע ללוגו */
            padding: 5px 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.4);
            display: flex;
            align-items: center;
            justify-content: flex-start;
        }}
        .main-content-padding {{
            padding-top: 60px; /* דוחף את התוכן מתחת ללוגו הקבוע */
            padding-left: 20px;
            padding-right: 20px;
            min-height: 100vh;
        }}
        .logo-small-img {{
            height: 40px;
            width: auto;
        }}
        
        /* --- General Streamlit & Login Styles (Kept short for focus) --- */
        #MainMenu, footer, header, .stDeployButton {{ visibility: hidden; }}
        h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel {{ color: #FFFFFF !important; opacity: 1 !important; }}
        .rtl {{ direction: rtl; text-align: right; font-family: 'Inter', sans-serif; }}
        
        .stButton > button {{ background-color: #FF7F50 !important; color: #000000 !important; border: none !important; font-weight: 800 !important; border-radius: 4px !important; }}

        /* Login Page Layout */
        .login-container {{ display: flex; flex-direction: row; width: 100%; height: 100vh; margin: -20px; }}
        .login-image-side {{ 
            flex: 1; 
            /* משתמש ברקע הראשי של הדף */
            display: flex; align-items: flex-end; justify-content: flex-start; 
            padding: 50px;
            position: relative;
            background: rgba(0, 0, 0, 0.2); /* רקע שקוף חלקית כדי לראות את ה-BG הראשי */
        }}
        .login-image-side::after {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.4);
        }}
        .login-form-side {{ flex: 1; background-color: #000000; padding: 80px 100px; color: #FFFFFF; display: flex; flex-direction: column; justify-content: center; }}
        .welcome-text {{ font-size: 2.2rem; font-weight: 900; color: #FFFFFF; line-height: 1.2; z-index: 10; }}
        
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
        #google_icon_in_btn {{ width: 20px; height: 20px; margin-left: 10px; }}
        
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
        """
        st.markdown(css, unsafe_allow_html=True)
    

def apply_terminal_css():
    if 'dark_mode' not in st.session_state: st.session_state.dark_mode = True
    apply_dynamic_css(st.session_state.dark_mode)

# ==========================================
# 3. STATE INITIALIZATION & AUTH
# ==========================================
if 'page' not in st.session_state: st.session_state['page'] = 'auth'
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

def login_user(email, password):
    # Test Backdoor
    if email == "admin" and password == "123": return True
    return False

def simulate_google_login_success():
    st.session_state['logged_in'] = True
    st.session_state['user_email'] = "google_user@stockpulse.com"
    st.rerun()

@st.cache_data(ttl=30)
def get_top_metrics():
    # Placeholder/Fallback Data
    return {"S&P 500": (5142.78, 0.63), "NASDAQ": (16173.61, 0.81), "BTC": (68490.1, -1.25), "VIX": (15.55, 3.1)}

# ==========================================
# 4. LOGIN PAGE
# ==========================================
def login_page():
    # --- Paths to Assets ---
    GOOGLE_ICON_URL = f"{BASE_URL}/google_icon.png"

    # --- Container for Split View ---
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # --- Image Side (Left Side) ---
    st.markdown(f"""
        <div class="login-image-side">
            <div style="z-index: 10;">
                <img src="{LOGO_LIGHT_BG_URL}" alt="StockPulse Logo" style="max-width: 250px; margin-bottom: 20px;">
                <div class="welcome-text">Welcome Back to Your Real-Time Edge</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # --- Form Side (Right Side) ---
    st.markdown('<div class="login-form-side">', unsafe_allow_html=True)
    
    # Tabs 
    st.markdown("""<div class="login-tabs"><div class="active">LOG IN</div><div>SIGN UP</div></div>""", unsafe_allow_html=True)
    
    # --- Standard Login Form ---
    with st.form("login_form", clear_on_submit=False):
        st.markdown('<div style="color: white; direction: rtl; text-align: right; margin-top: 10px;">אימייל</div>', unsafe_allow_html=True)
        email = st.text_input("אימייל", placeholder="הכנס אימייל", label_visibility="collapsed", key="email_input")
        
        st.markdown('<div style="color: white; direction: rtl; text-align: right; margin-top: 10px;">סיסמה</div>', unsafe_allow_html=True)
        password = st.text_input("סיסמה", type="password", placeholder="הכנס סיסמה", label_visibility="collapsed", key="password_input")
        
        st.markdown('<div style="text-align: right; margin-top: 15px; margin-bottom: 25px;"><a href="#" style="color: #AAAAAA; font-size: 0.9em;">Forgot Password?</a></div>', unsafe_allow_html=True)

        submitted = st.form_submit_button("LOG IN", use_container_width=True)
        
        if submitted:
            if login_user(email, password):
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("התחברות נכשלה. (רמז לבדיקה: admin/123)")
                
    st.write("---")
    
    # --- Social Login (Wide Google Button) ---
    st.markdown('<div style="text-align: center; color: #AAAAAA; margin-bottom: 15px;">OR LOG IN WITH</div>', unsafe_allow_html=True)
    
    st.markdown('<div id="google_wide_btn_container">', unsafe_allow_html=True)
    if st.button(f'<img src="{GOOGLE_ICON_URL}" id="google_icon_in_btn" alt="Google"> התחבר באמצעות גוגל', 
                 key="google_wide_btn", 
                 use_container_width=True,
                 unsafe_allow_html=True): 
        simulate_google_login_success()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div style="text-align: center; margin-top: 50px; color: #AAAAAA;">Don\'t have an account? <a href="#" style="color: #FF7F50;">Sign Up</a></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # Close login-form-side
    st.markdown('</div>', unsafe_allow_html=True) # Close login-container

# ==========================================
# 5. MAIN DASHBOARD
# ==========================================
def main_dashboard():
    # --- FIXED LOGO HEADER ---
    st.markdown(f"""
        <div class="fixed-logo-header">
            <img src="{LOGO_DASHBOARD_URL}" alt="StockPulse Logo" class="logo-small-img">
        </div>
    """, unsafe_allow_html=True)
    
    # --- MAIN CONTENT AREA ---
    # הוספת ריפוד כדי להתחיל את התוכן מתחת ללוגו הקבוע
    st.markdown('<div class="main-content-padding">', unsafe_allow_html=True)
    
    # --- 1. Top Metrics Row ---
    st.markdown('<h3 class="rtl">נתוני שוק חיים</h3>', unsafe_allow_html=True)
    
    metrics = get_top_metrics() 
    
    m1, m2, m3, m4 = st.columns(4)
    
    def show_metric(col, label, key_name):
        val, chg = metrics.get(key_name, (0, 0))
        col.metric(label=label, value=f"{val:,.2f}", delta=f"{chg:.2f}%")

    show_metric(m1, "S&P 500", "S&P 500")
    show_metric(m2, "NASDAQ 100", "NASDAQ")
    show_metric(m3, "BITCOIN", "BTC")
    show_metric(m4, "VIX Index", "VIX")

    st.write("---")

    # --- 2. Main Area (Alerts List vs Create Alert) ---
    col_list, col_create = st.columns([2, 1])

    with col_create:
        st.markdown('<div class="rtl" style="background: #111; padding: 20px; border-radius: 10px; border: 1px solid #444;">', unsafe_allow_html=True)
        st.markdown('<h4 class="rtl">צור התראה</h4>', unsafe_allow_html=True)
        
        with st.form("create_alert_form"):
            new_ticker = st.text_input("Ticker", value="NVDA", placeholder="סימול המניה")
            target_price = st.number_input("שינוי מחיר (%)", value=5.0, placeholder="יעד ב-%")
            min_vol = st.text_input("ווליום מינימלי", value="10M", placeholder="ווליום מינ' (למשל 10M)")
            whatsapp_notify = st.checkbox("התראה בווצאפ", value=True)
            alert_notes = st.text_area("הערות להתראה", height=70, placeholder="הוסף כאן הערות חשובות על התראה זו...")

            submitted = st.form_submit_button("הוסף התראה", use_container_width=True)
            if submitted: st.success(f"התראה ל-{new_ticker} נוצרה!") 
        
        st.markdown('</div>', unsafe_allow_html=True)

    with col_list:
        st.markdown('<h3 class="rtl">רשימת התראות</h3>', unsafe_allow_html=True)
        
        # Placeholder for the Sticky Note UI
        st.markdown("""
        <div style="color: #FFFFFF; background-color: rgba(17, 17, 17, 0.7); padding: 20px; border-radius: 10px;">
            <p><strong>פתקיות ההתראה (Sticky Notes) יופיעו כאן.</strong></p>
            <p>הקוד המלא כולל את ה-HTML/CSS של הפתקיות שהכנו קודם.</p>
            <p style='height: 200px;'> (שטח גלילה לדוגמה) </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="trash-can-area">
            <i class="fa-solid fa-trash-can trash-icon"></i>
            <p>גרור לכאן פתקיות התראה שהתממשו/בוטלו</p>
        </div>
        """, unsafe_allow_html=True)
        
    if st.button("יציאה", key="logout_btn", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True) # Close main-content-padding

# ==========================================
# 6. MAIN ROUTING LOGIC
# ==========================================

apply_terminal_css()

if not st.session_state['logged_in']:
    login_page()
else:
    main_dashboard()
