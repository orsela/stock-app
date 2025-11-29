"""Stock Alerts v7.8 - Registration with Phone Sync"""
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

# --- Page Setup ---
st.set_page_config(page_title="StockWatcher", page_icon="📈", layout="wide")

ADMIN_EMAIL = "orsela@gmail.com"

# ==========================================
#              ניהול THEME
# ==========================================
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

BG_MAIN, BG_CARD, TEXT_MAIN, BORDER, INPUT_BG = "#0e1117", "#1e293b", "#ffffff", "#333333", "#262730"
if st.session_state.theme == 'light':
    BG_MAIN, BG_CARD, TEXT_MAIN, BORDER, INPUT_BG = "#ffffff", "#f0f2f6", "#000000", "#d1d5db", "#ffffff"

def toggle_theme():
    st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'

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
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    
    /* Login Button Fix */
    [data-testid="stFormSubmitButton"] > button {{
        background-color: #ff4b4b !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        width: 100%;
    }}
    [data-testid="stFormSubmitButton"] > button:hover {{
        background-color: #ff6b6b !important;
    }}

    button[kind="secondary"] {{
        background-color: transparent !important;
        border: 1px solid {BORDER} !important;
        color: {TEXT_MAIN} !important;
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

# --- User Logic ---
def login_user(email, pw):
    try:
        sh = get_db()
        if not sh: return None
        records = sh.worksheet("users").get_all_records()
        hashed_pw = hashlib.sha256(pw.encode()).hexdigest()
        for user in records:
            if str(user.get('email', '')).strip().lower() == email.strip().lower() and str(user.get('password', '')) == hashed_pw:
                return user
        return None
    except: return None

# פונקציית הרשמה מעודכנת - מקבלת טלפון
def register_user(email, pw, phone):
    try:
        sh = get_db()
        if not sh: return False
        ws = sh.worksheet("users")
        try:
            if ws.find(email): return False
        except: pass
        
        hashed_pw = hashlib.sha256(pw.encode()).hexdigest()
        # שמירה עם 4 עמודות: אימייל, סיסמה, תאריך, טלפון
        ws.append_row([email, hashed_pw, datetime.now().isoformat(), phone])
        return True
    except: return False

# --- Rules Logic ---
def load_rules(email):
    try:
        sh = get_db()
        if not sh: return []
        records = sh.worksheet("rules").get_all_records()
        return [r for r in records if str(r.get('user_email', '')).strip().lower() == email.strip().lower()]
    except: return []

def add_rule(email, symbol, mn, mx, mv):
    try:
        sh = get_db()
        sh.worksheet("rules").append_row([email, symbol, mn, mx, mv, ""])
    except: pass

def delete_rule(email, symbol):
    try:
        sh = get_db()
        ws = sh.worksheet("rules")
        records = ws.get_all_records()
        new_data = [r for r in records if not (r.get('user_email') == email and r.get('symbol') == symbol)]
        ws.clear()
        if new_data:
            ws.update([list(records[0].keys())] + [list(r.values()) for r in new_data])
        else:
            ws.update([['user_email', 'symbol', 'min_price', 'max_price', 'min_vol', 'last_alert']])
    except: pass

def update_rule(email, symbol, new_min, new_max, new_vol):
    try:
        sh = get_db()
        ws = sh.worksheet("rules")
        delete_rule(email, symbol)
        ws.append_row([email, symbol, new_min, new_max, new_vol, ""])
        return True
    except: return False

def update_last_alert(email, symbol):
    try:
        sh = get_db()
        ws = sh.worksheet("rules")
        cell = ws.find(symbol)
        if cell: ws.update_cell(cell.row, 6, datetime.now().isoformat())
    except: pass

# ==========================================
#              EMAIL & DATA
# ==========================================
def send_email(to_email, symbol, price, vol, mn, mx):
    try:
        if "email" not in st.secrets: return False
        sender = st.secrets["email"]["sender_email"]
        password = st.secrets["email"]["sender_password"]
        
        is_good = price >= mx
        color = "#00c853" if is_good else "#d32f2f"
        title = "Target Hit 🎯" if is_good else "Price Drop ⚠️"
        
        html = f"""<div dir="ltr" style="font-family:sans-serif; border:1px solid #ddd; border-radius:10px; padding:20px;">
        <h2 style="color:{color}">{title}</h2>
        <h3>{symbol}</h3>
        <p>Price: <b>${price}</b></p>
        <p>Volume: {vol:,}</p>
        <p>Range: ${mn} - ${mx}</p>
        <a href="https://finance.yahoo.com/quote/{symbol}">View Chart</a></div>"""
        
        msg = MIMEMultipart()
        msg['Subject'] = f"🔔 {symbol}: {title}"
        msg['From'] = sender
        msg['To'] = to_email
        msg.attach(MIMEText(html, 'html'))
        
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls(); s.login(sender, password); s.send_message(msg); s.quit()
        return True
    except: return False

def send_whatsapp(phone, symbol, price, vol, mn, mx):
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
def get_data(symbol):
    try:
        t = yf.Ticker(symbol); i = t.info
        p = i.get('currentPrice') or i.get('regularMarketPrice') or i.get('previousClose')
        prev = i.get('previousClose')
        if not p: return None
        v = i.get('volume', 0)
        change = 0.0
        if p and prev: change = ((p - prev) / prev) * 100
        dom = i.get('website', '').replace('https://','').replace('www.','').split('/')[0]
        logo = f"https://logo.clearbit.com/{dom}" if dom else "https://cdn-icons-png.flaticon.com/512/666/666201.png"
        return {'price': round(p,2), 'change': round(change, 2), 'volume': v, 'logo': logo}
    except: return None

# ==========================================
#              DIALOGS
# ==========================================
@st.dialog("Edit Alert ✏️")
def edit_dialog(current_rule, user_email):
    st.write(f"Editing **{current_rule['symbol']}**")
    try:
        old_min = float(current_rule.get('min_price', 0))
        old_max = float(current_rule.get('max_price', 0))
        old_vol = float(current_rule.get('min_vol', 1000000))
    except:
        old_min, old_max, old_vol = 0.0, 0.0, 1000000.0

    c1, c2 = st.columns(2)
    new_min = c1.number_input("Min Price", value=old_min)
    new_max = c2.number_input("Max Price", value=old_max)
    new_vol = st.number_input("Min Volume", value=old_vol, step=100000.0)
    
    if st.button("Save Changes", type="primary"):
        update_rule(user_email, current_rule['symbol'], new_min, new_max, new_vol)
        st.rerun()

# ==========================================
#              MAIN APP FLOW
# ==========================================

if 'user' not in st.session_state: st.session_state.user = None

# --- LOGIN / REGISTER ---
if st.session_state.user is None:
    st.markdown("""<div style="display:flex;justify-content:center;margin-top:50px;">
    <div class="custom-card" style="width:400px;text-align:center;">
    <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" width="60">
    <h2>StockWatcher</h2><p>Login to continue</p></div></div>""", unsafe_allow_html=True)
    
    c1,c2,c3 = st.columns([1,1,1])
    with c2:
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        # טאב כניסה
        with tab1:
            with st.form("l"):
                e = st.text_input("Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In"):
                    u = login_user(e, p)
                    if u: st.session_state.user = u; st.rerun()
                    else: st.error("Failed")
        
        # טאב הרשמה מעודכן
        with tab2:
            with st.form("r"):
                e = st.text_input("Email")
                p = st.text_input("Password", type="password")
                # שדה טלפון חדש
                ph = st.text_input("WhatsApp Phone", placeholder="+97250...", help="For alerts")
                
                if st.form_submit_button("Sign Up"):
                    if register_user(e, p, ph):
                        st.success("Created! Login now.")
                    else: st.error("Error or Exists")

# --- DASHBOARD ---
else:
    u_email = str(st.session_state.user.get('email', 'User'))
    
    # טעינת הטלפון השמור מהגוגל שיטס
    saved_phone = str(st.session_state.user.get('phone', ''))
    
    # Sidebar
    with st.sidebar:
        st.header("Settings")
        
        # שדה טלפון - מוזן אוטומטית אם קיים ביוזר
        wa_num = st.text_input("Phone Number", value=saved_phone, placeholder="+972...", help="Synced with account")
        
        st.divider()
        if st.button("Logout"): st.session_state.user = None; st.rerun()
        
        if u_email.strip().lower() == ADMIN_EMAIL.lower():
            st.divider()
            if st.checkbox("🛡️ Admin Panel"):
                sh = get_db()
                if sh:
                    st.write("Users:"); st.dataframe(pd.DataFrame(sh.worksheet("users").get_all_records()))
                    st.write("Alerts:"); st.dataframe(pd.DataFrame(sh.worksheet("rules").get_all_records()))
                st.stop()

    # Top Bar
    c_head, c_tog = st.columns([8, 2])
    c_head.markdown(f"### Hello, {u_email}")
    
    is_dark = st.toggle("🌙 Dark Mode", value=(st.session_state.theme == 'dark'))
    if is_dark and st.session_state.theme != 'dark':
        st.session_state.theme = 'dark'
        st.rerun()
    elif not is_dark and st.session_state.theme != 'light':
        st.session_state.theme = 'light'
        st.rerun()

    st.divider()

    # Market Ticker
    m1, m2, m3 = st.columns(3)
    def show_metric(col, label, symbol):
        d = get_data(symbol)
        if d: col.metric(label, f"${d['price']:,}", f"{d['change']}%")
        else: col.metric(label, "Loading...", "0%")

    show_metric(m1, "S&P 500", "^GSPC")
    show_metric(m2, "NASDAQ", "^IXIC")
    show_metric(m3, "Bitcoin", "BTC-USD")
    st.markdown("---")

    # Watchlist
    rules = load_rules(u_email)
    if not rules: st.info("Your watchlist is empty. Add a stock below.")

    for r in rules:
        d = get_data(r.get('symbol'))
        if d:
            st.markdown('<div class="custom-card" style="padding:1rem;">', unsafe_allow_html=True)
            cols = st.columns([0.5, 1, 1, 1, 1.5, 1, 1])
            
            sym = r.get('symbol', 'N/A')
            mn = r.get('min_price', 0)
            mx = r.get('max_price', 0)
            mv = r.get('min_vol', 0)
            
            cols[0].markdown(f'<img src="{d["logo"]}" class="stock-logo">', unsafe_allow_html=True)
            cols[1].markdown(f"**{sym}**")
            cols[2].write(f"${d['price']}")
            cols[3].caption(f"{(d['volume']/1000000):.1f}M")
            cols[4].write(f"${mn} ➝ ${mx}")
            
            in_range = mn <= d['price'] <= mx
            vol_ok = d['volume'] >= mv
            status = "bg-green" if (in_range and vol_ok) else ("bg-yellow" if in_range else "bg-red")
            txt = "READY" if status=="bg-green" else ("VOL" if status=="bg-yellow" else "OUT")
            
            cols[5].markdown(f'<span class="badge {status}">{txt}</span>', unsafe_allow_html=True)
            
            if status == "bg-green":
                last = str(r.get('last_alert', ''))
                send = False
                if not last or last == "": send = True
                else:
                    try:
                        if (datetime.now() - datetime.fromisoformat(last)).seconds > 3600: send = True
                    except: send = True
                
                if send:
                    email_sent = send_email(u_email, sym, d['price'], d['volume'], mn, mx)
                    wa_sent = False
                    # שימוש במספר מהסרגל או מהיוזר
                    final_phone = wa_num if wa_num else saved_phone
                    if final_phone:
                        wa_sent = send_whatsapp(final_phone, sym, d['price'], d['volume'], mn, mx)
                        
                    if email_sent or wa_sent:
                        update_last_alert(u_email, sym)
                        st.toast(f"Alert Sent: {sym}", icon="🚀")

            with cols[6]:
                ce, cd = st.columns(2)
                if ce.button("✏️", key=f"ed_{sym}"):
                    edit_dialog(r, u_email)
                
                if cd.button("🗑️", key=f"del_{sym}"):
                    delete_rule(u_email, sym)
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
                    add_rule(u_email, s.upper(), mn, mx, mv)
                    st.rerun()
