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
def apply_dynamic_css(dark_mode: bool):
    # CSS content defining the dark/light mode styles and UI elements
    if dark_mode:
        css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&family=Permanent+Marker&display=swap');
        
        .stApp { background-color: #000000 !important; color: #FFFFFF !important; font-family: 'Inter', sans-serif; }
        #MainMenu, footer, header, .stDeployButton { visibility: hidden; }

        /* General Styling */
        h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel { color: #FFFFFF !important; opacity: 1 !important; }
        .rtl { direction: rtl; text-align: right; font-family: 'Inter', sans-serif; }
        
        /* Input & Button Styling */
        .stTextInput > div > div > input, .stNumberInput > div > div > input { background-color: #111 !important; border: 1px solid #333 !important; color: #FFFFFF !important; font-family: 'JetBrains Mono', monospace !important; }
        .stButton > button { background-color: #FF7F50 !important; color: #000000 !important; border: none !important; font-weight: 800 !important; border-radius: 4px !important; text-transform: uppercase; font-size: 1rem; transition: all 0.2s ease; }
        .stButton > button:hover { background-color: #FF6347 !important; transform: scale(1.02); }

        /* Login Page Layout */
        .login-container { display: flex; flex-direction: row; width: 100%; height: 100vh; margin: -20px; }
        .login-image-side { 
            flex: 1; 
            background: #111122; /* כחול כהה */
            background-image: url('https://upload.wikimedia.org/wikipedia/commons/b/b3/Candlestick_Chart_Example.png'); /* רקע דמוי גרף */
            background-size: cover;
            background-position: center;
            display: flex; align-items: flex-end; justify-content: flex-start; 
            padding: 50px;
            position: relative;
        }
        .login-image-side::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.4); /* שכבת כהה נוספת */
        }
        .login-form-side { flex: 1; background-color: #000000; padding: 80px 100px; color: #FFFFFF; display: flex; flex-direction: column; justify-content: center; }
        
        /* Image side text */
        .welcome-text { 
            font-size: 2.2rem; 
            font-weight: 900; 
            color: #FFFFFF; 
            line-height: 1.2;
            z-index: 10;
        }
        .login-form-side h2 { font-size: 2.5rem; font-weight: 900; color: #FF7F50; margin-bottom: 5px; text-align: right; direction: rtl; }
        
        /* Social Buttons */
        .social-buttons-container { display: flex; justify-content: center; gap: 15px; margin-top: 20px; margin-bottom: 30px; }
        .social-btn { height: 40px; width: 40px; background-color: #111; border: 1px solid #444; border-radius: 5px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: background-color 0.2s; }
        .social-btn:hover { background-color: #333; }
        .social-btn img { height: 20px; width: 20px; }
        
        /* Login Tabs */
        .login-tabs { display: flex; margin-bottom: 30px; }
        .login-tabs div { padding: 10px 20px; cursor: pointer; font-weight: 600; color: #AAAAAA; }
        .login-tabs .active { border-bottom: 3px solid #FF7F50; color: #FFFFFF; }

        /* Sticky Notes (CSS omitted for brevity, it's identical to previous version) */

        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
        """
        st.markdown(css, unsafe_allow_html=True)
    # ... (Light mode CSS omitted)

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
    # ... (Google Sheets connection logic) ...
    return None # Simplified return for placeholder

def get_worksheet(sheet_name):
    # ... (Google Sheets worksheet logic) ...
    return None # Simplified return for placeholder

def make_hashes(password):
    salt = "stockpulse_2025_salt"
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def check_hashes(password, hashed_text):
    salt = "stockpulse_2025_salt"
    return make_hashes(password) == hashed_text

def login_user(email, password):
    # DANGER: BACKDOOR for testing only! 
    if email == "admin" and password == "123": return True

    sheet = get_worksheet("USERS")
    if not sheet: return False # Fails if DB connection is broken

    # ... (Full DB login logic omitted for brevity, but assumes standard lookup) ...
    return False

# Placeholder function for Google Login simulation
def simulate_google_login_success():
    st.session_state['logged_in'] = True
    st.session_state['user_email'] = "google_user@stockpulse.com"
    st.rerun()

@st.cache_data(ttl=30)
def get_top_metrics():
    # ... (yfinance data fetching logic) ...
    return {"S&P 500": (6849.09, 0.54), "NASDAQ": (23365.0, 0.65), "BTC": (91427.0, 0.63), "VIX": (16.35, -4.89)}

def save_alert(email, symbol, target, notes):
    pass 

# ==========================================
# 5. UI COMPONENTS
# ==========================================

def login_page():
    # --- Paths to Assets (MUST BE UPDATED BY USER) ---
    GITHUB_USER = "YOUR_GITHUB_USERNAME" 
    REPO_NAME = "YOUR_REPO_NAME"
    
    logo_path = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/assets/logo_light_bg.png"
    google_icon = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/assets/google_icon.png"



    # --- 1. Container for Split View ---
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # --- 2. Image Side (Left Side - Static UI) ---
    st.markdown(f"""
        <div class="login-image-side">
            <div style="z-index: 10;">
                <img src="{logo_path}" alt="StockPulse Logo" style="max-width: 250px; margin-bottom: 20px;">
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
        # Input fields (RTL for labels, LTR for input content)
        email = st.text_input("אימייל", placeholder="הכנס אימייל", label_visibility="hidden", key="email_input")
        password = st.text_input("סיסמה", type="password", placeholder="הכנס סיסמה", label_visibility="hidden", key="password_input")
        
        # Use HTML to display the Hebrew labels correctly above the LTR input boxes
        st.markdown('<p style="position: relative; top: -50px; right: 0; color: white;">אימייל</p>', unsafe_allow_html=True)
        st.markdown('<p style="position: relative; top: -50px; right: 0; color: white;">סיסמה</p>', unsafe_allow_html=True)
        
        # Adjusting button position to be below the inputs correctly
        st.write("")
        st.write("")
        
        # Main Login Button
        submitted = st.form_submit_button("LOG IN", use_container_width=True)
        
        if submitted:
            if login_user(email, password):
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("התחברות נכשלה. אנא ודא שם משתמש וסיסמה.")
                
    # Forgot Password Link
    st.markdown('<div style="text-align: center; margin-top: -15px;"><a href="#" style="color: #AAAAAA;">Forgot Password?</a></div>', unsafe_allow_html=True)

    st.write("---")
    
    # --- Social Login ---
    st.markdown('<div style="text-align: center; color: #AAAAAA; margin-bottom: 10px;">OR LOG IN WITH</div>', unsafe_allow_html=True)
    
    # Social Buttons UI (Using Streamlit buttons with key for logic)
    col_g, col_a, col_l = st.columns([1, 1, 1])
    
    with col_g:
        if st.button(" ", key="google_btn", use_container_width=True): # Google Logic
            simulate_google_login_success()
            
    with col_a:
        st.button(" ", key="apple_btn", use_container_width=True) # Apple Placeholder
            
    with col_l:
        st.button(" ", key="linkedin_btn", use_container_width=True) # LinkedIn Placeholder


    # Social Button Icons (Overriding Streamlit buttons with CSS for icons)
    st.markdown(f"""
        <style>
        /* Override Streamlit button background to show icons */
        [data-testid="stButton"] button[kind="secondary"][data-testid^="stButton"]:has(span:empty) {{
            background-image: url('{google_icon}'); /* Google Button */
            background-size: 20px;
            background-repeat: no-repeat;
            background-position: center;
        }}
        [data-testid="stButton"] button[kind="secondary"][data-testid^="stButton"]:has(span:empty) {{
            background-image: url('{google_icon}'); /* Apply this CSS to the correct button based on layout structure */
            background-size: 20px;
            background-repeat: no-repeat;
            background-position: center;
        }}
        /* Since Streamlit button structure is complex, this is simplified. 
           In a real scenario, we would use st.columns with st.image + st.markdown 
           or target the buttons by their keys/position more precisely in CSS. 
           For this demo, we rely on the placeholder button structure.
        */
        </style>
    """, unsafe_allow_html=True)


    # Don't have an account link
    st.markdown('<div style="text-align: center; margin-top: 50px; color: #AAAAAA;">Don\'t have an account? <a href="#" style="color: #FF7F50;">Sign Up</a></div>', unsafe_allow_html=True)


    st.markdown('</div>', unsafe_allow_html=True) # Close login-form-side
    st.markdown('</div>', unsafe_allow_html=True) # Close login-container

def main_dashboard():
    # ... (Dashboard logic omitted for brevity in this response but included in full code) ...
    st.markdown('<h1 style="color: white; margin-top: 100px;">Dashboard Active! Welcome back.</h1>', unsafe_allow_html=True)
    
    if st.button("Logout"):
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
