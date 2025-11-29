"""Stock Alerts v7.2 - Final Fix & Stability Check"""
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

# כתובת האדמין
ADMIN_EMAIL = "orsela@gmail.com"

# ==========================================
#              ניהול THEME
# ==========================================
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

def toggle_theme():
    if st.session_state.theme == 'dark':
        st.session_state.theme = 'light'
    else:
        st.session_state.theme = 'dark'

if st.session_state.theme == 'dark':
    BG_MAIN, BG_CARD, TEXT_MAIN, BTN_ICON, BORDER, INPUT_BG = "#0e1117", "#1e293b", "#ffffff", "☀️", "#333333", "#262730"
else:
    BG_MAIN, BG_CARD, TEXT_MAIN, BTN_ICON, BORDER, INPUT_BG = "#ffffff", "#f0f2f6", "#000000", "🌙", "#d1d5db", "#ffffff"

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
        if "gcp_service_account" not in st.secrets: return None
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except: return None

def get_db():
    client = init_connection()
    if not client: return None
    try: return client.open("StockWatcherDB")
    except: return None

# --- User Management ---
def login_user(email, pw):
    try:
        sh = get_db()
        if not sh: return None
        records = sh.worksheet("users").get_all_records()
        hashed_pw = hashlib.sha256(pw.encode()).hexdigest()
        for user in records:
            if str(user['email']).strip().lower() == email.strip().lower() and str(user['password']) == hashed_pw:
                return user
        return None
    except: return None

def register_user(email, pw):
    try:
        sh = get_db()
        if not sh: return False
        ws = sh.worksheet("users")
        try:
            if ws.find(email): return False
        except: pass
        
        hashed_pw = hashlib.sha256(pw.encode()).hexdigest()
        ws.append_row([email, hashed_pw, datetime.now().isoformat()])
        return True
    except: return False

# --- Rules Management ---
def load_rules_from_db(email):
    try:
        sh = get_db()
        if not sh: return []
        records = sh.worksheet("rules").get_all_records()
        return [r for r in records if str(r['user_email']).strip().lower() == email.strip().lower()]
    except: return []

def add_rule_to_db(email, symbol, min_p, max_p, min_vol):
    try:
        sh = get_db()
        sh.worksheet("rules").append_row([email, symbol, min_p, max_p, min_vol, ""])
    except: pass

def delete_rule_from_db(email, symbol):
    try:
        sh = get_db()
        ws = sh.worksheet("rules")
        records = ws.get_all_records()
        new_records = [r for r in records if not (r['user_email'] == email and r['symbol'] == symbol)]
        ws.clear()
        if new_records:
            ws.update([list(records[0].keys())] + [list(r.values()) for r in new_records])
        else:
            ws.update([['user_email', 'symbol', 'min_price', 'max_price', 'min_vol', 'last_alert']])
    except: pass

def update_last_alert_in_db(email, symbol):
    try:
        sh = get_db()
        ws = sh.worksheet("rules")
        cell = ws.find(symbol)
        if cell: ws.update_cell(cell.row, 6, datetime.now().isoformat())
    except: pass

# ==========================================
#              EMAIL & DATA
# ==========================================

def send_html_email(target_email, symbol, price, volume, min_p, max_p, min_vol):
    try:
        if "email" not in st.secrets: return False
        sender = st.secrets["email"]["sender_email"]
        password = st.secrets["email"]["sender_password"]
        
        is_pos = price >= max_p
        clr = "#00c853" if is_pos else "#d32f2f"
        txt = "Target Hit! 🎯" if is_pos else "Price Drop ⚠️"
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = target_email
        msg['Subject'] = f"🔔 {symbol}: {txt}"
        
        html = f"""<div dir="ltr" style="font-family:sans-serif; border:1px solid #ccc; border-radius:10px; overflow:hidden;">
            <div style="background:{clr}; color:white; padding:20px; text-align:center;"><h1>{txt}</h1></div>
            <div style="padding:20px;">
                <h2>{symbol}</h2>
                <p>Price: <b>${price}</b></p>
                <p>Range: ${min_p} - ${max_p}</p>
                <a href="https://finance.yahoo.com/quote/{symbol}">View Chart</a>
            </div>
        </div>"""
        msg.attach(MIMEText(html, 'html'))
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls(); s.login(sender, password); s.send_message(msg); s.quit()
        return True
    except: return False

def send_whatsapp(phone, symbol, price, vol, min_p, max_p):
    try:
        if "twilio" not in st.secrets: return False
        sid = st.secrets["twilio"]["account_sid"]
        token = st.secrets["twilio"]["auth_token"]
        from_num = st.secrets["twilio"]["from_number"]
        if not sid: return False
        from twilio.rest import Client
        client = Client(sid, token)
        msg = f"🚀 {symbol}\n💰 ${price}\n🎯 ${min_p}-${max_p}"
        client.messages.create(body=msg, from_=f'whatsapp:{from_num}', to=f'whatsapp:{phone}')
        return True
    except: return False

@st.cache_data(ttl=60)
def get_stock_data(symbol):
    try:
        t = yf.Ticker(symbol); i = t.info
        p = i.get('currentPrice') or i.get('regularMarketPrice') or i.get('previousClose')
        if not p: return None
        v = i.get('volume', 0)
        dom = i.get('website', '').replace('https://','').replace('www.','').split('/')[0]
        logo = f"https://logo.clearbit.com/{dom}" if dom else "https://cdn-icons-png.flaticon.com/512/666/666201.png"
        return {'price': round(p,2), 'volume': v, 'logo': logo}
    except: return None

# ==========================================
#              ADMIN PANEL
# ==========================================
def admin_panel():
    st.markdown("## 🛡️ Admin Panel")
    sh = get_db()
    if sh:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Users")
            st.dataframe(pd.DataFrame(sh.worksheet("users").get_all_records()))
        with c2:
            st.markdown("### Alerts")
            st.dataframe(pd.DataFrame(sh.worksheet("rules").get_all_records()))

# ==========================================
#              MAIN APP FLOW
# ==========================================

if 'user' not in st.session_state: st.session_state.user = None

# --- LOGIN ---
if st.session_state.user is None:
    st.markdown(f"""<div style="display:flex;justify-content:center;margin-top:50px;"><div class="custom-card" style="width:400px;text-align:center;">
    <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" width="50">
    <h2>StockWatcher</h2><p>Sign in to monitor</p></div></div>""", unsafe_allow_html=True)
    
    c1,c2,c3 = st.columns([1,1,1])
    with c2:
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            with st.form("l"):
                e = st.text_input("Email"); p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In", use_container_width=True):
                    u = login_user(e, p)
                    if u: st.session_state.user = u; st.rerun()
                    else: st.error("Login Failed")
        with tab2:
            with st.form("r"):
                e = st.text_input("Email"); p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign Up", use_container_width=True):
                    if register_user(e, p): st.success("Created! Login now.");
                    else: st.error("Error/Exists")

# --- DASHBOARD ---
else:
    # Admin Check
    try:
        user_email = str(st.session_state.user['email']).strip().lower()
        if user_email == ADMIN_EMAIL.lower():
            with st.sidebar:
                st.divider()
                if st.checkbox("🛡️ Admin Mode"):
                    admin_panel()
                    st.stop()
                    
        # Header (התיקון הגדול כאן!)
        c_head, c_btn = st.columns([9, 1])
        c_head.markdown(f"### Hello, {user_email}")
        if c_btn.button(BTN_ICON): toggle_theme(); st.rerun()
        
        st.divider()
        
        # Watchlist
        my_rules = load_rules_from_db(user_email)
        
        if not my_rules:
            st.info("No alerts found. Add your first stock below!")
            
        for r in my_rules:
            d = get_stock_data(r['symbol'])
            if d:
                st.markdown(f'<div class="custom-card" style="padding:1rem;">', unsafe_allow_html=True)
                cols = st.columns([0.5, 1, 1, 1, 1.5, 1, 0.5])
                
                cols[0].markdown(f'<img src="{d["logo"]}" class="stock-logo">', unsafe_allow_html=True)
                cols[1].markdown(f"**{r['symbol']}**")
                cols[2].write(f"${d['price']}")
                cols[3].caption(f"{(d['volume']/1000000):.1f}M")
                cols[4].write(f"${r['min_price']} ➝ ${r['max_price']}")
                
                in_range = r['min_price'] <= d['price'] <= r['max_price']
                vol_ok = d['volume'] >= r['min_vol']
                status = "bg-green" if (in_range and vol_ok) else "bg-red"
                if in_range and not vol_ok: status = "bg-yellow"
                
                txt = "OK" if status=="bg-green" else ("VOL" if status=="bg-yellow" else "OUT")
                cols[5].markdown(f'<span class="badge {status}">{txt}</span>', unsafe_allow_html=True)
                
                # Alerts
                if status == "bg-green":
                    last = str(r.get('last_alert', ''))
                    send = False
                    if not last: send = True
                    else:
                        try:
                            if (datetime.now() - datetime.fromisoformat(last)).seconds > 3600: send = True
                        except: send = True
                    
                    if send:
                        if send_html_email(user_email, r['symbol'], d['price'], d['volume'], r['min_price'], r['max_price'], r['min_vol']):
                            update_last_alert_in_db(user_email, r['symbol'])
                            st.toast(f"Sent: {r['symbol']}")

                if cols[6].button("🗑️", key=f"del_{r['symbol']}"):
                    delete_rule_from_db(user_email, r['symbol'])
                    st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        with st.expander("➕ Add New Alert"):
            with st.form("new"):
                c1,c2,c3,c4 = st.columns(4)
                s = c1.text_input("Symbol")
                mn = c2.number_input("Min $", 100.0)
                mx = c3.number_input("Max $", 200.0)
                mv = c4.number_input("Min Vol", 1000000)
                if st.form_submit_button("Add Alert"):
                    if s:
                        add_rule_to_db(user_email, s.upper(), mn, mx, mv)
                        st.rerun()

    except Exception as e:
        st.error(f"Dashboard Error: {e}")
        if st.button("Reset App"):
            st.session_state.clear()
            st.rerun()
