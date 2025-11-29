"""Stock Alerts v5.8 - Professional HTML Emails"""
import streamlit as st
import json, os, hashlib, time
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- הגדרת עמוד ---
st.set_page_config(page_title="StockWatcher", page_icon="📈", layout="wide")

# ==========================================
#              ניהול THEME
# ==========================================
if 'theme' not in st.session_state: st.session_state.theme = 'dark'

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
    .stTextInput input, .stNumberInput input {{ color: {TEXT_MAIN} !important; background-color: {INPUT_BG} !important; border-color: {BORDER} !important; }}
    .custom-card {{ background-color: {BG_CARD}; padding: 1.5rem; border-radius: 12px; border: 1px solid {BORDER}; margin-bottom: 10px; }}
    .badge {{ padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 0.8rem; color: white !important; }}
    .bg-green {{background-color: #28a745;}} .bg-red {{background-color: #dc3545;}}
    .stock-logo {{ width: 35px; height: 35px; border-radius: 50%; object-fit: contain; background-color: #fff; padding: 2px; border: 1px solid #ccc; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
#              BACKEND
# ==========================================
USERS_FILE = "users.json"

def load_users(): return json.load(open(USERS_FILE)) if os.path.exists(USERS_FILE) else {}
def save_users(users): with open(USERS_FILE, 'w') as f: json.dump(users, f, indent=2)

def login_user(email, pw):
    users = load_users()
    if email in users and users[email]['password'] == hashlib.sha256(pw.encode()).hexdigest(): return users[email]
    return None

def register_user(email, pw):
    users = load_users()
    if email in users: return False
    users[email] = {'password': hashlib.sha256(pw.encode()).hexdigest(), 'created': datetime.now().isoformat()}
    save_users(users)
    return True

# --- פונקציית מייל מעוצבת ---
def send_html_email(target_email, symbol, price, min_p, max_p, is_whatsapp_enabled=False):
    try:
        if "email" not in st.secrets: return False
        
        sender = st.secrets["email"]["sender_email"]
        password = st.secrets["email"]["sender_password"]
        
        # בניית המייל ב-HTML
        subject = f"🔔 התראה: {symbol} בטווח היעד!"
        
        html_content = f"""
        <div dir="rtl" style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
            <div style="background-color: #28a745; padding: 20px; text-align: center; color: white;">
                <h1 style="margin: 0;">🚀 הזדמנות אותרה!</h1>
                <p style="margin: 5px 0 0 0; font-size: 18px;">המניה {symbol} נכנסה לטווח.</p>
            </div>
            
            <div style="padding: 20px; background-color: #f9f9f9;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">מחיר נוכחי:</td>
                        <td style="padding: 10px; font-size: 20px; color: #28a745;">${price}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">טווח שהגדרת:</td>
                        <td style="padding: 10px;">${min_p} - ${max_p}</td>
                    </tr>
                </table>
                
                <div style="margin-top: 30px; text-align: center;">
                    <a href="https://finance.yahoo.com/quote/{symbol}" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">צפה בגרף המניה</a>
                </div>
            </div>
            
            <div style="background-color: #eee; padding: 10px; text-align: center; font-size: 12px; color: #666;">
                נשלח ע"י StockWatcher • {datetime.now().strftime('%Y-%m-%d %H:%M')}
                {'<br>נשלחה גם הודעת WhatsApp' if is_whatsapp_enabled else ''}
            </div>
        </div>
        """

        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = target_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

# --- פונקציית וואטסאפ (נשארה זהה) ---
def send_whatsapp(phone, symbol, price, min_p, max_p):
    try:
        if "twilio" not in st.secrets: return False
        sid, token, from_num = st.secrets["twilio"]["account_sid"], st.secrets["twilio"]["auth_token"], st.secrets["twilio"]["from_number"]
        if not sid: return False
        from twilio.rest import Client
        client = Client(sid, token)
        msg = f"🚀 *Stock Alert*\n\n📈 *{symbol}*\n💰 Price: ${price}\n🎯 Range: ${min_p} - ${max_p}"
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
        
        website = info.get('website', '')
        logo_url = "https://cdn-icons-png.flaticon.com/512/666/666201.png"
        if website:
            domain = website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
            if domain: logo_url = f"https://logo.clearbit.com/{domain}"

        change = 0.0
        if price and prev: change = ((price - prev) / prev) * 100
        return {'price': round(price, 2), 'change': round(change, 2), 'logo': logo_url} if price else None
    except: return None

if 'user' not in st.session_state: st.session_state.user = None
if 'rules' not in st.session_state: st.session_state.rules = []

# ==========================================
#              DIALOGS
# ==========================================
@st.dialog("Edit Alert ✏️")
def edit_dialog(index, current_rule):
    st.write(f"Editing settings for **{current_rule['symbol']}**")
    col_min, col_max = st.columns(2)
    new_min = col_min.number_input("Min Price", value=float(current_rule['min']))
    new_max = col_max.number_input("Max Price", value=float(current_rule['max']))
    if st.button("Save Changes", type="primary"):
        st.session_state.rules[index]['min'] = new_min
        st.session_state.rules[index]['max'] = new_max
        st.rerun()

# ==========================================
#              UI LOGIC
# ==========================================
if st.session_state.user is None:
    # Login Screen (אותו קוד קודם)
    st.markdown(f"""
    <div style="display: flex; justify-content: center; margin-top: 50px;">
        <div class="custom-card" style="width: 400px; text-align: center;">
            <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" width="60">
            <h2 style="margin-top:10px;">Welcome Back</h2>
            <p style="opacity: 0.7;">Sign in to monitor your portfolio</p>
        </div>
    </div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In", use_container_width=True):
                    user = login_user(email, password)
                    if user: st.session_state.user = {'email': email}; st.rerun()
                    else: st.error("Login failed")
        with tab_signup:
            with st.form("signup_form"):
                new_email = st.text_input("Email")
                new_pass = st.text_input("Password", type="password")
                if st.form_submit_button("Create Account", use_container_width=True):
                    if register_user(new_email, new_pass): st.success("Created! Please Login.");
                    else: st.error("User exists")

else:
    # Dashboard
    c_title, c_theme = st.columns([9, 1])
    c_title.markdown(f"### 👋 Hello, {st.session_state.user['email']}")
    if c_theme.button(BTN_ICON, help="Switch Theme"): toggle_theme(); st.rerun()
    st.divider()

    # Market Overview
    st.markdown("##### 📊 Market Status")
    m1, m2, m3 = st.columns(3)
    d_sp = get_stock_data("^GSPC")
    m1.metric("S&P 500", f"${d_sp['price']:,}" if d_sp else "--", f"{d_sp['change']}%" if d_sp else "--")
    d_nd = get_stock_data("^IXIC")
    m2.metric("NASDAQ", f"${d_nd['price']:,}" if d_nd else "--", f"{d_nd['change']}%" if d_nd else "--")
    d_btc = get_stock_data("BTC-USD")
    m3.metric("Bitcoin", f"${d_btc['price']:,}" if d_btc else "--", f"{d_btc['change']}%" if d_btc else "--")
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.markdown("### Settings")
        whatsapp_num = st.text_input("WhatsApp Number", placeholder="+972...", key="wa")
        st.info("ℹ️ Email alerts are active by default.")
        if st.button("Logout", type="primary"): st.session_state.user = None; st.rerun()

    # Watchlist
    st.markdown("##### 📜 Your Watchlist")
    for i, rule in enumerate(st.session_state.rules):
        data = get_stock_data(rule['symbol'])
        st.markdown(f'<div class="custom-card" style="padding: 1rem;">', unsafe_allow_html=True)
        cols = st.columns([0.5, 1, 1, 2, 1, 1])
        if data:
            price = data['price']
            cols[0].markdown(f'<img src="{data["logo"]}" class="stock-logo">', unsafe_allow_html=True)
            cols[1].markdown(f"**{rule['symbol']}**")
            cols[2].write(f"${price}")
            cols[3].write(f"${rule['min']} ➝ ${rule['max']}")
            
            in_range = rule['min'] <= price <= rule['max']
            badge_class, badge_text = ("bg-green", "IN RANGE") if in_range else ("bg-red", "OUT")
            cols[4].markdown(f'<span class="badge {badge_class}">{badge_text}</span>', unsafe_allow_html=True)
            
            # --- לוגיקת שליחת התראות (מייל + וואטסאפ) ---
            if in_range:
                last_alert = rule.get('last_alert')
                should_alert = False
                
                # בדיקת קולדאון (האם עברה שעה?)
                if not last_alert: 
                    should_alert = True
                else:
                    try:
                        time_diff = (datetime.now() - datetime.fromisoformat(last_alert)).seconds
                        if time_diff > 3600: should_alert = True
                    except: should_alert = True
                
                if should_alert:
                    # 1. שליחת מייל (חובה)
                    email_sent = send_html_email(
                        st.session_state.user['email'], 
                        rule['symbol'], price, rule['min'], rule['max'],
                        is_whatsapp_enabled=bool(whatsapp_num)
                    )
                    
                    # 2. שליחת וואטסאפ (אם הוגדר)
                    wa_sent = False
                    if whatsapp_num:
                        wa_sent = send_whatsapp(whatsapp_num, rule['symbol'], price, rule['min'], rule['max'])
                    
                    if email_sent or wa_sent:
                        rule['last_alert'] = datetime.now().isoformat()
                        # הודעה קופצת למשתמש שההתראה יצאה
                        st.toast(f"🚨 Alert Sent for {rule['symbol']}!", icon="📧")

            with cols[5]:
                col_edit, col_del = st.columns(2)
                if col_edit.button("✏️", key=f"edit_{i}"): edit_dialog(i, rule)
                if col_del.button("🗑️", key=f"del_{i}"): st.session_state.rules.pop(i); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("➕ Add Stock"):
        with st.form("new_stock"):
            c1, c2, c3 = st.columns(3)
            s = c1.text_input("Symbol", "TSLA")
            mn = c2.number_input("Min", 100.0)
            mx = c3.number_input("Max", 300.0)
            if st.form_submit_button("Add"):
                if s: st.session_state.rules.append({'symbol': s.upper(), 'min': mn, 'max': mx}); st.rerun()
