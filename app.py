"""Stock Alerts v6.1 - Volume Logic Restored"""
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
    BG_MAIN, BG_CARD, TEXT_MAIN, BTN_ICON, BORDER, INPUT_BG = "#0e1117", "#1e293b", "#ffffff", "☀️", "#333333", "#262730"
else:
    BG_MAIN, BG_CARD, TEXT_MAIN, BTN_ICON, BORDER, INPUT_BG = "#ffffff", "#f0f2f6", "#000000", "🌙", "#d1d5db", "#ffffff"

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
        padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 0.75rem; color: white !important; display: inline-block;
    }}
    .bg-green {{background-color: #28a745;}}
    .bg-yellow {{background-color: #ffc107; color: black !important;}} /* ווליום נמוך */
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
    if os.path.exists(USERS_FILE): return json.load(open(USERS_FILE))
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f: json.dump(users, f, indent=2)

def login_user(email, pw):
    users = load_users()
    if email in users and users[email]['password'] == hashlib.sha256(pw.encode()).hexdigest():
        return users[email]
    return None

def register_user(email, pw):
    users = load_users()
    if email in users: return False
    users[email] = {
        'password': hashlib.sha256(pw.encode()).hexdigest(),
        'created': datetime.now().isoformat()
    }
    save_users(users)
    return True

# --- פונקציית המייל (כולל ווליום) ---
def send_html_email(target_email, symbol, price, volume, min_p, max_p, min_vol):
    try:
        if "email" not in st.secrets: return False
        sender = st.secrets["email"]["sender_email"]
        password = st.secrets["email"]["sender_password"]
        
        is_positive = price >= max_p
        
        if is_positive:
            header_text = "מחיר יעד הושג! 🎯"
            theme_color = "#00c853"
            alert_status = "פריצת גבול עליון + ווליום תקין"
        else:
            header_text = "התראת גבול תחתון ⚠️"
            theme_color = "#d32f2f"
            alert_status = "ירידה מתחת למינימום + ווליום תקין"

        subject = f"🔔 {symbol}: {header_text}"
        alert_time = datetime.now().strftime('%d/%m/%Y | %H:%M')

        html_content = f"""
        <div dir="rtl" style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
            <div style="background-color: {theme_color}; padding: 25px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">{header_text}</h1>
            </div>
            <div style="padding: 20px; background-color: #f9f9f9;">
                <h2 style="margin: 0; font-size: 36px; color: #333; text-align: center;">{symbol}</h2>
                <table style="width: 100%; margin-top: 20px; background: #fff; border-radius: 8px; padding: 10px;">
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">מחיר:</td>
                        <td style="padding: 10px; color: {theme_color}; font-size: 18px;">${price}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">ווליום נוכחי:</td>
                        <td style="padding: 10px;">{volume:,}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">דרישת ווליום:</td>
                        <td style="padding: 10px;">מעל {min_vol:,}</td>
                    </tr>
                </table>
                <div style="margin-top: 30px; text-align: center;">
                    <a href="https://finance.yahoo.com/quote/{symbol}" style="background-color: {theme_color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 50px;">צפה בגרף</a>
                </div>
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

def send_whatsapp(phone, symbol, price, vol, min_p, max_p):
    try:
        if "twilio" not in st.secrets: return False
        sid = st.secrets["twilio"]["account_sid"]
        token = st.secrets["twilio"]["auth_token"]
        from_num = st.secrets["twilio"]["from_number"]
        if not sid: return False
        
        from twilio.rest import Client
        client = Client(sid, token)
        msg = f"🚀 *{symbol} Alert*\n💰 Price: ${price}\n📊 Vol: {vol:,}\n🎯 Range: ${min_p}-${max_p}"
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
        volume = info.get('volume', 0) # שליפת ווליום
        
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

if 'user' not in st.session_state: st.session_state.user = None
if 'rules' not in st.session_state: st.session_state.rules = []

# ==========================================
#              DIALOGS (עריכה)
# ==========================================
@st.dialog("Edit Alert ✏️")
def edit_dialog(index, current_rule):
    st.write(f"Editing **{current_rule['symbol']}**")
    c1, c2 = st.columns(2)
    new_min = c1.number_input("Min Price", value=float(current_rule['min']))
    new_max = c2.number_input("Max Price", value=float(current_rule['max']))
    # טיפול תאימות לאחור (אם אין ווליום שמור בהתראה ישנה)
    old_vol = float(current_rule.get('min_vol', 1000000))
    new_vol = st.number_input("Min Volume", value=old_vol, step=100000.0)
    
    if st.button("Save", type="primary"):
        st.session_state.rules[index]['min'] = new_min
        st.session_state.rules[index]['max'] = new_max
        st.session_state.rules[index]['min_vol'] = new_vol
        st.rerun()

# ==========================================
#              UI LOGIC
# ==========================================

# --- LOGIN ---
if st.session_state.user is None:
    st.markdown(f"""
    <div style="display: flex; justify-content: center; margin-top: 50px;">
        <div class="custom-card" style="width: 400px; text-align: center;">
            <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" width="60">
            <h2 style="margin-top:10px;">StockWatcher</h2>
            <p style="opacity: 0.7;">Sign in to monitor your portfolio</p>
        </div>
    </div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        tab_l, tab_s = st.tabs(["Login", "Sign Up"])
        with tab_l:
            with st.form("l"):
                e = st.text_input("Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In", use_container_width=True):
                    u = login_user(e, p)
                    if u: st.session_state.user = {'email': e}; st.rerun()
                    else: st.error("Failed")
        with tab_s:
            with st.form("s"):
                e = st.text_input("Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign Up", use_container_width=True):
                    if register_user(e, p): st.success("Created!");
                    else: st.error("Exists")

# --- DASHBOARD ---
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

    with st.sidebar:
        st.markdown("### Settings")
        whatsapp_num = st.text_input("WhatsApp Number", placeholder="+972...", key="wa")
        if st.button("Logout", type="primary"): st.session_state.user = None; st.rerun()

    st.markdown("##### 📜 Your Watchlist")
    
    for i, rule in enumerate(st.session_state.rules):
        data = get_stock_data(rule['symbol'])
        
        st.markdown(f'<div class="custom-card" style="padding: 1rem;">', unsafe_allow_html=True)
        # Logo | Symbol | Price | Vol | Range | Status | Actions
        cols = st.columns([0.5, 1, 1, 1, 1.5, 1, 1])
        
        if data:
            price = data['price']
            vol = data['volume']
            # תאימות לאחור
            target_vol = rule.get('min_vol', 0)
            
            # 1. Logo
            cols[0].markdown(f'<img src="{data["logo"]}" class="stock-logo">', unsafe_allow_html=True)
            # 2. Symbol
            cols[1].markdown(f"**{rule['symbol']}**")
            # 3. Price
            cols[2].write(f"${price}")
            # 4. Volume (New!)
            cols[3].caption(f"Vol: {vol/1000000:.1f}M")
            # 5. Range
            cols[4].write(f"${rule['min']} ➝ ${rule['max']}")
            
            # 6. Status Logic (Price AND Volume)
            price_in_range = rule['min'] <= price <= rule['max']
            vol_ok = vol >= target_vol
            
            if price_in_range and vol_ok:
                badge = ("bg-green", "IN RANGE")
                should_check_alert = True
            elif price_in_range and not vol_ok:
                badge = ("bg-yellow", "LOW VOL")
                should_check_alert = False
            else:
                badge = ("bg-red", "OUT")
                should_check_alert = False
                
            cols[5].markdown(f'<span class="badge {badge[0]}">{badge[1]}</span>', unsafe_allow_html=True)
            
            # Alert Trigger
            if should_check_alert:
                last_alert = rule.get('last_alert')
                send_now = False
                if not last_alert: send_now = True
                else:
                    try:
                        if (datetime.now() - datetime.fromisoformat(last_alert)).seconds > 3600: send_now = True
                    except: send_now = True
                
                if send_now:
                    email_sent = send_html_email(
                        st.session_state.user['email'], 
                        rule['symbol'], price, vol, rule['min'], rule['max'], target_vol
                    )
                    wa_sent = False
                    if whatsapp_num:
                        wa_sent = send_whatsapp(whatsapp_num, rule['symbol'], price, vol, rule['min'], rule['max'])
                    
                    if email_sent or wa_sent:
                        rule['last_alert'] = datetime.now().isoformat()
                        st.toast(f"🚨 Alert Sent for {rule['symbol']}!", icon="📧")

            # 7. Actions
            with cols[6]:
                ce, cd = st.columns(2)
                if ce.button("✏️", key=f"e_{i}"): edit_dialog(i, rule)
                if cd.button("🗑️", key=f"d_{i}"): st.session_state.rules.pop(i); st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("➕ Add Stock"):
        with st.form("new_stock"):
            c1, c2, c3, c4 = st.columns(4)
            s = c1.text_input("Symbol", "TSLA")
            mn = c2.number_input("Min Price", 100.0)
            mx = c3.number_input("Max Price", 300.0)
            mv = c4.number_input("Min Volume", value=1000000)
            if st.form_submit_button("Add"):
                if s:
                    st.session_state.rules.append({'symbol': s.upper(), 'min': mn, 'max': mx, 'min_vol': mv})
                    st.rerun()
