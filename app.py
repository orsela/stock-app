"""Stock Alerts v7.1 - Production Stable (Google Sheets + Volume + Admin)"""
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import hashlib
import time

# --- הגדרת עמוד ---
st.set_page_config(page_title="StockWatcher", page_icon="📈", layout="wide")

# כתובת האדמין (רק מייל זה יראה את מסך האדמין)
ADMIN_EMAIL = "orsela@gmail.com"

# ==========================================
#              ניהול THEME (עיצוב)
# ==========================================
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

def toggle_theme():
    if st.session_state.theme == 'dark':
        st.session_state.theme = 'light'
    else:
        st.session_state.theme = 'dark'

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
        padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 0.75rem; color: white !important; display: inline-block;
    }}
    .bg-green {{background-color: #28a745;}}
    .bg-yellow {{background-color: #ffc107; color: black !important;}}
    .bg-red {{background-color: #dc3545;}}

    .stock-logo {{
        width: 35px; height: 35px; border-radius: 50%; object-fit: contain;
        background-color: #fff; padding: 2px; border: 1px solid #ccc;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
#              GOOGLE SHEETS DB
# ==========================================

@st.cache_resource
def init_connection():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        if "gcp_service_account" not in st.secrets:
            return None
        
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        return None

def get_db():
    client = init_connection()
    if not client:
        st.error("❌ Google Connection Failed. Check Secrets.")
        return None
    try:
        sheet = client.open("StockWatcherDB")
        return sheet
    except gspread.SpreadsheetNotFound:
        st.error("❌ Spreadsheet 'StockWatcherDB' not found.")
        return None
    except Exception as e:
        st.error(f"❌ DB Error: {e}")
        return None

# --- ניהול משתמשים ---
def login_user(email, pw):
    try:
        sh = get_db()
        if not sh: return None
        ws = sh.worksheet("users")
        records = ws.get_all_records()
        hashed_pw = hashlib.sha256(pw.encode()).hexdigest()
        
        for user in records:
            # המרת אימייל למחרוזת והשוואה
            if str(user['email']).strip().lower() == email.strip().lower() and str(user['password']) == hashed_pw:
                return user
        return None
    except Exception as e:
        st.error(f"Login Error: {e}")
        return None

def register_user(email, pw):
    try:
        sh = get_db()
        if not sh: return False
        
        ws = sh.worksheet("users")
        # בדיקה אם משתמש קיים
        try:
            existing = ws.find(email)
            if existing:
                st.warning("User already exists.")
                return False
        except:
            pass # אם לא נמצא, מצוין
        
        hashed_pw = hashlib.sha256(pw.encode()).hexdigest()
        ws.append_row([email, hashed_pw, datetime.now().isoformat()])
        return True
    except Exception as e:
        st.error(f"Registration Error: {e}")
        return False

# --- ניהול התראות ---
def load_rules_from_db(email):
    try:
        sh = get_db()
        if not sh: return []
        ws = sh.worksheet("rules")
        records = ws.get_all_records()
        return [r for r in records if str(r['user_email']).strip().lower() == email.strip().lower()]
    except:
        return []

def add_rule_to_db(email, symbol, min_p, max_p, min_vol):
    try:
        sh = get_db()
        ws = sh.worksheet("rules")
        # מבנה שורה: Email, Symbol, Min, Max, Vol, LastAlert
        ws.append_row([email, symbol, min_p, max_p, min_vol, ""])
    except Exception as e:
        st.error(f"Save Error: {e}")

def delete_rule_from_db(email, symbol):
    try:
        sh = get_db()
        ws = sh.worksheet("rules")
        records = ws.get_all_records()
        # סינון: שומרים את כל מה שלא תואם למחיקה
        new_records = [r for r in records if not (r['user_email'] == email and r['symbol'] == symbol)]
        
        ws.clear()
        if new_records:
            # החזרת הכותרות והנתונים
            headers = list(records[0].keys())
            rows = [list(r.values()) for r in new_records]
            ws.update([headers] + rows)
        else:
            # אם הכל נמחק, מחזירים רק כותרות (hardcoded כדי למנוע קריסה)
            ws.update([['user_email', 'symbol', 'min_price', 'max_price', 'min_vol', 'last_alert']])
            
    except Exception as e:
        st.error(f"Delete Error: {e}")

def update_last_alert_in_db(email, symbol):
    try:
        sh = get_db()
        ws = sh.worksheet("rules")
        cell = ws.find(symbol)
        if cell:
            # בדיקה גסה שזה השורה הנכונה (בגרסה מתקדמת צריך חיפוש מדויק יותר)
            # מעדכן את עמודה F (מספר 6) שהיא last_alert
            ws.update_cell(cell.row, 6, datetime.now().isoformat())
    except:
        pass

# ==========================================
#              EMAIL & DATA LOGIC
# ==========================================

def send_html_email(target_email, symbol, price, volume, min_p, max_p, min_vol):
    try:
        if "email" not in st.secrets: return False
        sender = st.secrets["email"]["sender_email"]
        password = st.secrets["email"]["sender_password"]
        
        is_positive = price >= max_p
        theme_color = "#00c853" if is_positive else "#d32f2f"
        header_text = "Target Hit! 🎯" if is_positive else "Price Drop ⚠️"
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = target_email
        msg['Subject'] = f"🔔 {symbol}: {header_text}"
        
        html_content = f"""
        <div dir="ltr" style="font-family:sans-serif; border:1px solid #ccc; border-radius:10px; overflow:hidden; max-width:600px; margin:auto;">
            <div style="background:{theme_color}; color:white; padding:20px; text-align:center;">
                <h1 style="margin:0;">{header_text}</h1>
            </div>
            <div style="padding:20px; background:#f9f9f9;">
                <h2 style="text-align:center; color:#333;">{symbol}</h2>
                <table style="width:100%; background:white; padding:10px; border-radius:8px;">
                    <tr><td>Price:</td><td style="color:{theme_color}; font-weight:bold; font-size:18px;">${price}</td></tr>
                    <tr><td>Volume:</td><td>{volume:,}</td></tr>
                    <tr><td>Target Range:</td><td>${min_p} - ${max_p}</td></tr>
                </table>
                <div style="text-align:center; margin-top:20px;">
                    <a href="https://finance.yahoo.com/quote/{symbol}" style="background:{theme_color}; color:white; padding:10px 20px; text-decoration:none; border-radius:20px;">View Chart</a>
                </div>
            </div>
        </div>
        """
        msg.attach(MIMEText(html_content, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Fail: {e}")
        return False

def send_whatsapp(phone, symbol, price, vol, min_p, max_p):
    try:
        if "twilio" not in st.secrets: return False
        sid = st.secrets["twilio"]["account_sid"]
        token = st.secrets["twilio"]["auth_token"]
        from_num = st.secrets["twilio"]["from_number"]
        
        if not sid: return False
        from twilio.rest import Client
        client = Client(sid, token)
        msg = f"🚀 {symbol} Alert\n💰 ${price}\n📊 Vol: {vol:,}\n🎯 ${min_p}-${max_p}"
        client.messages.create(body=msg, from_=f'whatsapp:{from_num}', to=f'whatsapp:{phone}')
        return True
    except: return False

@st.cache_data(ttl=60)
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        prev = info.get('previousClose')
        volume = info.get('volume', 0)
        
        website = info.get('website', '')
        logo_url = "https://cdn-icons-png.flaticon.com/512/666/666201.png"
        if website:
            domain = website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
            if domain:
                logo_url = f"https://logo.clearbit.com/{domain}"

        change = 0.0
        if price and prev:
            change = ((price - prev) / prev) * 100
            
        return {'price': round(price, 2), 'change': round(change, 2), 'volume': volume, 'logo': logo_url} if price else None
    except: return None

# ==========================================
#              ADMIN PANEL
# ==========================================
def admin_panel():
    st.markdown("## 🛡️ Admin Panel")
    sh = get_db()
    if sh:
        try:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 👥 Users")
                users = sh.worksheet("users").get_all_records()
                st.dataframe(pd.DataFrame(users))
            with col2:
                st.markdown("### 🔔 Alerts")
                rules = sh.worksheet("rules").get_all_records()
                st.dataframe(pd.DataFrame(rules))
        except Exception as e:
            st.error(f"Admin Error: {e}")

# ==========================================
#              MAIN APP FLOW
# ==========================================

if 'user' not in st.session_state:
    st.session_state.user = None

# --- LOGIN ---
if st.session_state.user is None:
    st.markdown(f"""
    <div style="display:flex;justify-content:center;margin-top:50px;">
        <div class="custom-card" style="width:400px;text-align:center;">
            <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" width="50">
            <h2>StockWatcher</h2>
            <p>Login to continue</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            with st.form("l"):
                e = st.text_input("Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In", use_container_width=True):
                    u = login_user(e, p)
                    if u:
                        st.session_state.user = u
                        st.rerun()
                    else:
                        st.error("Login Failed")
        with tab2:
            with st.form("r"):
                e = st.text_input("Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign Up", use_container_width=True):
                    if register_user(e, p):
                        st.success("Registered! Login now.")
                    else:
                        st.error("Error/Exists")

# --- DASHBOARD ---
else:
    # Admin Check
    user_email = str(st.session_state.user['email'])
    if user_email.strip().lower() == ADMIN_EMAIL.lower():
        with st.sidebar:
            st.divider()
            if st.checkbox("🛡️ Admin Mode"):
                admin_panel()
                st.stop()

    c_head, c_btn = st.columns
