"""Stock Alerts v6.0 - Professional Dynamic HTML Emails"""
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
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

def toggle_theme():
    if st.session_state.theme == 'dark':
        st.session_state.theme = 'light'
    else:
        st.session_state.theme = 'dark'

# הגדרת משתנים
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

# CSS
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
        padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 0.8rem; color: white !important;
    }}
    .bg-green {{background-color: #28a745;}}
    .bg-red {{background-color: #dc3545;}}

    .stock-logo {{
        width: 35px; height: 35px; border-radius: 50%; object-fit: contain;
        background-color: #fff; padding: 2px; border: 1px solid #ccc;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
#              BACKEND
# ==========================================
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        return json.load(open(USERS_FILE))
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def login_user(email, pw):
    users = load_users()
    if email in users and users[email]['password'] == hashlib.sha256(pw.encode()).hexdigest():
        return users[email]
    return None

def register_user(email, pw):
    users = load_users()
    if email in users:
        return False
    users[email] = {
        'password': hashlib.sha256(pw.encode()).hexdigest(),
        'created': datetime.now().isoformat()
    }
    save_users(users)
    return True

# --- פונקציית המייל החדשה והמעוצבת ---
def send_html_email(target_email, symbol, price, min_p, max_p):
    try:
        if "email" not in st.secrets: return False
        sender = st.secrets["email"]["sender_email"]
        password = st.secrets["email"]["sender_password"]
        
        # קביעת סוג ההתראה (חיובי/שלילי) לצורך עיצוב
        is_positive = price >= max_p
        
        if is_positive:
            header_text = "מחיר יעד עליון הושג! 🎯"
            theme_color = "#00c853" # ירוק
            alert_status = "המניה פרצה את הגבול העליון"
        else:
            header_text = "התראת גבול תחתון ⚠️"
            theme_color = "#d32f2f" # אדום
            alert_status = "המניה ירדה מתחת לגבול התחתון"

        subject = f"🔔 התראה: {symbol} - {header_text}"
        alert_time = datetime.now().strftime('%d/%m/%Y | %H:%M')

        # תבנית ה-HTML הדינמית
        html_content = f"""
        <!DOCTYPE html>
        <html lang="he" dir="rtl">
        <head>
        <meta charset="UTF-8">
        <style>
            body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
            table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
            img {{ -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }}
            table {{ border-collapse: collapse !important; }}
            body {{ height: 100% !important; margin: 0 !important; padding: 0 !important; width: 100% !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f7; }}
        </style>
        </head>
        <body style="margin: 0; padding: 0; background-color: #f4f4f7;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                    <td align="center" style="padding: 20px 0;">
                        <table border="0" cellpadding="0" cellspacing="0" width="600" style="max-width: 600px; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                            <tr>
                                <td align="center" style="padding: 25px; background-color: {theme_color};">
                                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: bold;">
                                        {header_text}
                                    </h1>
                                </td>
                            </tr>
                            <tr>
                                <td align="center" style="padding: 30px 20px;">
                                    <h2 style="margin: 0; font-size: 36px; color: #333333;">{symbol}</h2>
                                    <p style="margin: 5px 0 20px 0; color: #777777; font-size: 16px;">
                                        סטטוס: <span style="font-weight: bold;">{alert_status}</span>
                                    </p>
                                    <table border="0" cellpadding="0" cellspacing="0" width="80%" style="background-color: #f9f9f9; border-radius: 8px; margin: 20px 0;">
                                        <tr>
                                            <td align="center" style="padding: 20px;">
                                                <p style="margin: 0; color: #777777; font-size: 14px; font-weight: bold;">מחיר נוכחי בשוק</p>
                                                <h3 style="margin: 5px 0 0 0; font-size: 42px; color: {theme_color}; font-weight: 800;">
                                                    ${price}
                                                </h3>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td align="center" style="border-top: 2px solid #eeeeee; padding: 15px;">
                                                <p style="margin: 0; font-size: 14px; color: #555555;">
                                                    טווח היעד שהגדרת: 
                                                    <span style="font-weight: bold; direction: ltr; unicode-bidi: embed;">${min_p} - ${max_p}</span>
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                    <p style="margin: 20px 0 30px 0; color: #999999; font-size: 12px;">זמן התראה: {alert_time}</p>
                                    <table border="0" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td align="center" style="border-radius: 50px; background-color: {theme_color};">
                                                <a href="https://finance.yahoo.com/quote/{symbol}" target="_blank" style="display: inline-block; padding: 14px 30px; font-size: 16px; color: #ffffff; text-decoration: none; font-weight: bold; border-radius: 50px;">
                                                    צפה בגרף המניה
                                                </a>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td align="center" style="padding: 20px; background-color: #f4f4f7; color: #888888; font-size: 12px;">
                                    <p style="margin: 0;">נשלח ע"י מערכת StockWatcher</p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
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

# --- פונקציית וואטסאפ ---
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
            if domain:
                logo_url = f"https://logo.clearbit.com/{domain}"

        change = 0.0
        if price and prev:
            change = ((price - prev) / prev) * 100
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

# --- LOGIN SCREEN ---
if st.session_state.user is None:
    st.markdown(f"""
    <div style="display: flex; justify-content: center; margin-top: 50px;">
        <div class="custom-card" style="width: 400px; text-align: center;">
            <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" width="60">
            <h2 style="margin-top:10px;">Welcome Back</h2>
            <p style="opacity: 0.7;">Sign in to monitor your portfolio</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In", use_container_width=True):
                    user = login_user(email, password)
                    if user:
                        st.session_state.user = {'email': email}
                        st.rerun()
                    else: st.error("Login failed")
        with tab_signup:
            with st.form("signup_form"):
                new_email = st.text_input("Email")
                new_pass = st.text_input("Password", type="password")
                if st.form_submit_button("Create Account", use_container_width=True):
                    if register_user(new_email, new_pass):
                        st.success("Created! Please Login.")
                    else: st.error("User exists")

# --- DASHBOARD SCREEN ---
else:
    c_title, c_theme = st.columns([9, 1])
    c_title.markdown(f"### 👋 Hello, {st.session_state.user['email']}")
    if c_theme.button(BTN_ICON, help="Switch Theme"):
        toggle_theme()
        st.rerun()
    
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
        
        if st.button("Logout", type="primary"):
            st.session_state.user = None
            st.rerun()

    # Watchlist
    st.markdown("##### 📜 Your Watchlist")
    
    for i, rule in enumerate(st.session_state.rules):
        data = get_stock_data(rule['symbol'])
        
        st.markdown(f'<div class="custom-card" style="padding: 1rem;">', unsafe_allow_html=True)
        
        cols = st.columns([0.5, 1, 1, 2, 1, 1])
        
        if data:
            price = data['price']
            
            # 1. Logo
            cols[0].markdown(f'<img src="{data["logo"]}" class="stock-logo">', unsafe_allow_html=True)
            
            # 2. Symbol
            cols[1].markdown(f"**{rule['symbol']}**")
            
            # 3. Price
            cols[2].write(f"${price}")
            
            # 4. Range
            cols[3].write(f"${rule['min']} ➝ ${rule['max']}")
            
            # 5. Status Badge & Alert Logic
            in_range = rule['min'] <= price <= rule['max']
            badge_class, badge_text = ("bg-green", "IN RANGE") if in_range else ("bg-red", "OUT")
            cols[4].markdown(f'<span class="badge {badge_class}">{badge_text}</span>', unsafe_allow_html=True)
            
            if in_range:
                last_alert = rule.get('last_alert')
                should_alert = False
                
                if not last_alert: 
                    should_alert = True
                else:
                    try:
                        time_diff = (datetime.now() - datetime.fromisoformat(last_alert)).seconds
                        if time_diff > 3600: should_alert = True
                    except: should_alert = True
                
                if should_alert:
                    # כאן נקראת הפונקציה החדשה
                    email_sent = send_html_email(
                        st.session_state.user['email'], 
                        rule['symbol'], price, rule['min'], rule['max']
                    )
                    
                    wa_sent = False
                    if whatsapp_num:
                        wa_sent = send_whatsapp(whatsapp_num, rule['symbol'], price, rule['min'], rule['max'])
                    
                    if email_sent or wa_sent:
                        rule['last_alert'] = datetime.now().isoformat()
                        st.toast(f"🚨 Alert Sent for {rule['symbol']}!", icon="📧")

            # 6. Actions
            with cols[5]:
                col_edit, col_del = st.columns(2)
                if col_edit.button("✏️", key=f"edit_{i}"):
                    edit_dialog(i, rule)
                if col_del.button("🗑️", key=f"del_{i}"):
                    st.session_state.rules.pop(i)
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Add New
    with st.expander("➕ Add Stock"):
        with st.form("new_stock"):
            c1, c2, c3 = st.columns(3)
            s = c1.text_input("Symbol", "TSLA")
            mn = c2.number_input("Min", 100.0)
            mx = c3.number_input("Max", 300.0)
            if st.form_submit_button("Add"):
                if s:
                    st.session_state.rules.append({'symbol': s.upper(), 'min': mn, 'max': mx})
                    st.rerun()
