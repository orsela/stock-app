"""Stock Alerts v7.4 - DEMO DAY FINAL (With Market Data & Delta)"""
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

# --- Theme Management ---
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

def toggle_theme():
    st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'

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
    /* Metric container styling */
    div[data-testid="metric-container"] {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER};
        padding: 10px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }}
</style>
""", unsafe_allow_html=True)

# --- Google Sheets Connection ---
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
    if not client:
        st.error("⚠️ Connection Failed. Check Secrets.")
        return None
    try:
        return client.open("StockWatcherDB")
    except:
        st.error("⚠️ Database 'StockWatcherDB' not found.")
        return None

# --- Logic ---
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

def load_rules(email):
    try:
        sh = get_db()
        if not sh: return []
        records = sh.worksheet("rules").get_all_records()
        return [r for r in records if str(r['user_email']).strip().lower() == email.strip().lower()]
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
        new_data = [r for r in records if not (r['user_email'] == email and r['symbol'] == symbol)]
        ws.clear()
        if new_data:
            ws.update([list(records[0].keys())] + [list(r.values()) for r in new_data])
        else:
            ws.update([['user_email', 'symbol', 'min_price', 'max_price', 'min_vol', 'last_alert']])
    except: pass

def update_last_alert(email, symbol):
    try:
        sh = get_db()
        ws = sh.worksheet("rules")
        cell = ws.find(symbol)
        if cell: ws.update_cell(cell.row, 6, datetime.now().isoformat())
    except: pass

# --- Notifications ---
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
        <a href="https://finance.yahoo.com/quote/{symbol}" style="background:{color}; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">View Chart</a></div>"""
        
        msg = MIMEMultipart()
        msg['Subject'] = f"🔔 {symbol}: {title}"
        msg['From'] = sender
        msg['To'] = to_email
        msg.attach(MIMEText(html, 'html'))
        
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls(); s.login(sender, password); s.send_message(msg); s.quit()
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
        
        # חישוב אחוז שינוי (חשוב לדשבורד!)
        change = 0.0
        if p and prev:
            change = ((p - prev) / prev) * 100
            
        dom = i.get('website', '').replace('https://','').replace('www.','').split('/')[0]
        logo = f"https://logo.clearbit.com/{dom}" if dom else "https://cdn-icons-png.flaticon.com/512/666/666201.png"
        return {'price': round(p,2), 'change': round(change, 2), 'volume': v, 'logo': logo}
    except: return None

# --- Main App ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    # Login View
    st.markdown("""<div style="display:flex;justify-content:center;margin-top:50px;">
    <div class="custom-card" style="width:400px;text-align:center;">
    <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" width="60">
    <h2>StockWatcher</h2><p>Login to continue</p></div></div>""", unsafe_allow_html=True)
    
    c1,c2,c3 = st.columns([1,1,1])
    with c2:
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            with st.form("l"):
                e = st.text_input("Email"); p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In", use_container_width=True):
                    u = login_user(e, p)
                    if u: st.session_state.user = u; st.rerun()
                    else: st.error("Failed")
        with tab2:
            with st.form("r"):
                e = st.text_input("Email"); p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign Up", use_container_width=True):
                    if register_user(e, p): st.success("Created!");
                    else: st.error("Error")

else:
    # Dashboard View
    u_email = str(st.session_state.user['email'])
    
    # Admin Panel
    if u_email.strip().lower() == ADMIN_EMAIL.lower():
        with st.sidebar:
            st.divider()
            if st.checkbox("🛡️ Admin Panel"):
                st.markdown("## Admin Database View")
                sh = get_db()
                if sh:
                    st.write("Users:"); st.dataframe(pd.DataFrame(sh.worksheet("users").get_all_records()))
                    st.write("Alerts:"); st.dataframe(pd.DataFrame(sh.worksheet("rules").get_all_records()))
                st.stop()

    # Top Bar
    c_head, c_btn = st.columns([9, 1])
    c_head.markdown(f"### Hello, {u_email}")
    if c_btn.button(BTN_ICON): toggle_theme(); st.rerun()
    st.divider()

    # Market Ticker (With Delta!)
    st.markdown("##### 📊 Market Overview")
    m1, m2, m3 = st.columns(3)
    
    # פונקציית עזר להצגת מטריקה
    def show_metric(col, label, symbol):
        d = get_data(symbol)
        if d:
            col.metric(label, f"${d['price']:,}", f"{d['change']}%")
        else:
            col.metric(label, "Loading...", "0%")

    show_metric(m1, "S&P 500", "^GSPC")
    show_metric(m2, "NASDAQ", "^IXIC")
    show_metric(m3, "Bitcoin", "BTC-USD")
    
    st.markdown("---")

    # Watchlist
    st.markdown("##### 📜 Your Alerts")
    rules = load_rules(u_email)
    
    if not rules:
        st.info("Your watchlist is empty. Add a stock below.")

    for r in rules:
        d = get_data(r['symbol'])
        if d:
            st.markdown('<div class="custom-card" style="padding:1rem;">', unsafe_allow_html=True)
            cols = st.columns([0.5, 1, 1, 1, 1.5, 1, 0.5])
            
            cols[0].markdown(f'<img src="{d["logo"]}" class="stock-logo">', unsafe_allow_html=True)
            cols[1].markdown(f"**{r['symbol']}**")
            cols[2].write(f"${d['price']}")
            cols[3].caption(f"{(d['volume']/1000000):.1f}M")
            cols[4].write(f"${r['min_price']} ➝ ${r['max_price']}")
            
            in_range = r['min_price'] <= d['price'] <= r['max_price']
            vol_ok = d['volume'] >= r['min_vol']
            
            # Status Logic
            if in_range and vol_ok:
                status = "bg-green"; txt = "READY"
            elif in_range and not vol_ok:
                status = "bg-yellow"; txt = "LOW VOL"
            else:
                status = "bg-red"; txt = "OUT"
            
            cols[5].markdown(f'<span class="badge {status}">{txt}</span>', unsafe_allow_html=True)
            
            # Alert Logic
            if status == "bg-green":
                last = str(r.get('last_alert', ''))
                send = False
                if not last or last == "":
                    send = True
                else:
                    try:
                        if (datetime.now() - datetime.fromisoformat(last)).seconds > 3600: send = True
                    except: send = True
                
                if send:
                    if send_email(u_email, r['symbol'], d['price'], d['volume'], r['min_price'], r['max_price']):
                        update_last_alert(u_email, r['symbol'])
                        st.toast(f"Alert Sent: {r['symbol']}", icon="🚀")

            if cols[6].button("🗑️", key=f"del_{r['symbol']}"):
                delete_rule(u_email, r['symbol'])
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
    
    with st.sidebar:
        st.divider()
        if st.button("Logout", type="primary"): st.session_state.user = None; st.rerun()
