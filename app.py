"""Stock Alerts v3.2 - Twilio WhatsApp + After-Hours Close Price"""
import streamlit as st
import json, os, hashlib, time
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Stock Alerts", page_icon="📈", layout="wide")

USERS_FILE, RULES_FILE = "users.json", "rules.json"

def load_users():
    return json.load(open(USERS_FILE)) if os.path.exists(USERS_FILE) else {}

def save_users(users):
    with open(USERS_FILE, 'w') as f: json.dump(users, f, indent=2)

def login(email, pw):
    users = load_users()
    if email in users and users[email]['password'] == hashlib.sha256(pw.encode()).hexdigest():
        return users[email]
    return None

def register(email, pw):
    users = load_users()
    if email in users: return False
    users[email] = {'password': hashlib.sha256(pw.encode()).hexdigest(), 'created': datetime.now().isoformat()}
    save_users(users)
    return True

@st.cache_data(ttl=60)
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if not current_price:
            current_price = info.get('previousClose')
        
        prev_close = info.get('previousClose')
        volume = info.get('volume', 0)
        
        if current_price and prev_close:
            change = ((current_price - prev_close) / prev_close * 100)
            market_state = info.get('marketState', 'CLOSED')
            is_after_hours = market_state in ['CLOSED', 'PRE', 'POST']
            
            return {
                'price': round(current_price, 2), 
                'change': round(change, 2), 
                'volume': int(volume),
                'is_after_hours': is_after_hours,
                'market_state': market_state
            }
    except:
        pass
    return None

def send_whatsapp_alert(phone, symbol, price, rule_min, rule_max, twilio_sid, twilio_token, twilio_from):
    try:
        from twilio.rest import Client
        client = Client(twilio_sid, twilio_token)
        message = f"אזהרת מחיר 📈\n\nסימול: {symbol}\nמחיר נוכחי: ${price}\nטווח: ${rule_min}-${rule_max}"
        msg = client.messages.create(
            from_=f'whatsapp:{twilio_from}',
            body=message,
            to=f'whatsapp:{phone}'
        )
        return True
    except Exception as e:
        st.error(f"שגיאה בשליחת WhatsApp: {str(e)}")
        return False

def check_alerts_and_notify():
    if 'twilio_sid' not in st.session_state or not st.session_state.twilio_sid:
        return
    
    for rule in st.session_state.rules:
        if 'phone' not in rule or not rule['phone']:
            continue
            
        data = get_stock_data(rule['symbol'])
        if data and data['price']:
            price = data['price']
            if price < rule['min'] or price > rule['max']:
                if 'last_alert' not in rule or (datetime.now() - datetime.fromisoformat(rule.get('last_alert', '2000-01-01'))).seconds > 3600:
                    if send_whatsapp_alert(
                        rule['phone'], rule['symbol'], price, rule['min'], rule['max'],
                        st.session_state.twilio_sid, st.session_state.twilio_token, st.session_state.twilio_from
                    ):
                        rule['last_alert'] = datetime.now().isoformat()
                        save_rules(st.session_state.user['email'], st.session_state.rules)

def load_rules(email):
    if os.path.exists(RULES_FILE):
        all_rules = json.load(open(RULES_FILE))
        if isinstance(all_rules, list): return []
        if isinstance(all_rules, dict): return all_rules.get(email, [])
    return []

def save_rules(email, rules):
    all_rules = json.load(open(RULES_FILE)) if os.path.exists(RULES_FILE) else {}
    if not isinstance(all_rules, dict): all_rules = {}
    all_rules[email] = rules
    with open(RULES_FILE, 'w') as f: json.dump(all_rules, f, indent=2)

if 'user' not in st.session_state: st.session_state.user = None
if 'rules' not in st.session_state: st.session_state.rules = []
if 'twilio_sid' not in st.session_state: st.session_state.twilio_sid = ""
if 'twilio_token' not in st.session_state: st.session_state.twilio_token = ""
if 'twilio_from' not in st.session_state: st.session_state.twilio_from = ""

if st.session_state.user is None:
    st.title("📈 Stock Alerts")
    tab1, tab2 = st.tabs(["כניסה", "הרשמה"])
    with tab1:
        with st.form("login"):
            email = st.text_input("אימייל", placeholder="example@gmail.com")
            pw = st.text_input("סיסמה", type="password")
            if st.form_submit_button("התחבר"):
                profile = login(email, pw)
                if profile:
                    st.session_state.user = {'email': email, **profile}
                    st.session_state.rules = load_rules(email)
                    st.rerun()
                else: st.error("שגיאה")
    with tab2:
        with st.form("reg"):
            email = st.text_input("אימייל")
            pw = st.text_input("סיסמה", type="password")
            pw2 = st.text_input("אימות", type="password")
            if st.form_submit_button("הרשם"):
                if pw != pw2: st.error("סיסמאות לא זהות")
                elif register(email, pw): st.success("הצלחה!")
                else: st.error("תפוס")
else:
    with st.sidebar:
        st.caption(st.session_state.user['email'])
        with st.expander("⚙️ הגדרות Twilio WhatsApp"):
            st.info("💡 להתראות WhatsApp - צריך חשבון Twilio")
            st.session_state.twilio_sid = st.text_input("Account SID", value=st.session_state.twilio_sid, type="password")
            st.session_state.twilio_token = st.text_input("Auth Token", value=st.session_state.twilio_token, type="password")
            st.session_state.twilio_from = st.text_input("Twilio WhatsApp Number", value=st.session_state.twilio_from, placeholder="+14155238886")
        if st.button("יציאה"):
            st.session_state.user = None
            st.rerun()
    
    st.title("📈 לוח בקרה")
    check_alerts_and_notify()
    
    indices = {'^GSPC': 'S&P 500', '^IXIC': 'NASDAQ', 'BTC-USD': 'BITCOIN'}
    cols = st.columns(3)
    for col, (sym, name) in zip(cols, indices.items()):
        with col:
            data = get_stock_data(sym)
            if data:
                label = f"{name} {'🌙 (סגירה)' if data.get('is_after_hours') else ''}"
                col.metric(label, f"${data['price']:,.2f}", f"{data['change']:+.2f}%")
            else: col.metric(name, "--", "--")
    
    st.divider()
    st.subheader("התראות שלי")
    for i, rule in enumerate(st.session_state.rules):
        data = get_stock_data(rule['symbol'])
        if data:
            c1,c2,c3,c4,c5,c6 = st.columns([1,2,2,2,1,1])
            symbol_display = f"**{rule['symbol']}** {'🌙' if data.get('is_after_hours') else ''}"
            c1.write(symbol_display)
            price_label = "סגירה" if data.get('is_after_hours') else "מחיר"
            c2.metric(price_label, f"${data['price']}")
            c3.caption(f"ווליום: {data['volume']:,}")
            c4.caption(f"טווח: ${rule['min']}-${rule['max']}")
            if data['price'] < rule['min'] or data['price'] > rule['max']: c5.write("🔴")
            else: c5.write("🟢")
            if c6.button("✖️", key=f"del_{i}"):
                st.session_state.rules.pop(i)
                save_rules(st.session_state.user['email'], st.session_state.rules)
                st.rerun()
    
    st.divider()
    if st.button("➕ הוסף התראה"):
        st.session_state.show_add = True
        st.rerun()
    
    if st.session_state.get('show_add'):
        with st.form("add_alert"):
            sym = st.text_input("סימול", placeholder="AAPL, TSLA, NVDA...")
            price_range = st.slider("טווח מחיר", 0.0, 5000.0, (100.0, 500.0))
            phone = st.text_input("מספר WhatsApp (אופציונלי)", placeholder="+972501234567")
            st.caption("💡 להתראות WhatsApp - הגדר את Twilio בסיידבר")
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("שמור"):
                    st.session_state.rules.append({'symbol': sym.upper(), 'min': price_range[0], 'max': price_range[1], 'phone': phone if phone else None})
                    save_rules(st.session_state.user['email'], st.session_state.rules)
                    st.session_state.show_add = False
                    st.rerun()
            with col2:
                if st.form_submit_button("ביטול"):
                    st.session_state.show_add = False
                    st.rerun()
    st.caption(f"v3.2 | {datetime.now().strftime('%H:%M:%S')}")