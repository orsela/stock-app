import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import yfinance as yf
import hashlib
import plotly.graph_objects as go

# ==========================================
# APP CONFIG
# ==========================================
st.set_page_config(
    page_title="StockPulse Terminal",
    layout="wide",
    page_icon="💹",
    initial_sidebar_state="collapsed"
)

# ==========================================
# TERMINAL CSS (High Contrast, Readable)
# ==========================================
def apply_terminal_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&display=swap');
        
        /* --- GLOBAL RESET --- */
        .stApp {
            background-color: #000000;
            color: #FFFFFF;
            font-family: 'Inter', sans-serif;
        }
        
        /* הסתרת אלמנטים מיותרים */
        #MainMenu, footer, header, .stDeployButton {visibility: hidden;}

        /* --- TYPOGRAPHY (NO TRANSPARENCY) --- */
        h1, h2, h3, h4, h5, h6, .stMarkdown, p {
            color: #FFFFFF !important;
            opacity: 1 !important;
        }
        
        .logo-title {
            font-size: 3rem; font-weight: 900; color: #FFFFFF;
            text-align: center; margin-bottom: 5px; letter-spacing: -1px;
        }
        .logo-subtitle {
            font-family: 'JetBrains Mono', monospace; color: #FF7F50;
            font-size: 1rem; text-align: center; margin-bottom: 30px; letter-spacing: 1px;
        }

        /* --- INPUTS & SLIDERS --- */
        /* שדות קלט עם רקע כהה וטקסט לבן בוהק */
        .stTextInput > div > div > input, .stNumberInput > div > div > input {
            background-color: #1A1A1A !important;
            border: 1px solid #444 !important;
            color: #FFFFFF !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-weight: 700;
        }
        /* תוויות מעל שדות */
        .stTextInput label, .stNumberInput label, .stSlider label {
            color: #FFFFFF !important;
            font-weight: 600;
            font-size: 0.9rem;
        }

        /* --- BUTTONS --- */
        .stButton > button {
            background-color: #FF7F50 !important;
            color: #000000 !important; /* טקסט שחור על כתום לקריאות */
            border: none !important;
            font-weight: 800 !important;
            border-radius: 4px !important;
            text-transform: uppercase;
        }
        .stButton > button:hover {
            background-color: #FF6347 !important;
        }

        /* --- SOCIAL BUTTONS (SQUARES) --- */
        /* Google */
        div[data-testid="column"]:nth-of-type(2) div.stButton > button {
            background-color: #FFFFFF !important;
            border-radius: 8px !important;
            background-image: -webkit-linear-gradient(45deg, #4285F4, #DB4437, #F4B400, #0F9D58) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            font-size: 26px !important; font-weight: 900 !important;
            height: 60px !important;
        }
        /* Apple */
        div[data-testid="column"]:nth-of-type(3) div.stButton > button {
            background-color: #FFFFFF !important;
            color: #000 !important;
            border-radius: 8px !important;
            font-size: 26px !important;
            height: 60px !important;
        }
        /* LinkedIn */
        div[data-testid="column"]:nth-of-type(4) div.stButton > button {
            background-color: #0077b5 !important;
            color: #FFF !important;
            border-radius: 8px !important;
            font-size: 26px !important;
            height: 60px !important;
        }

        /* --- CARDS & METRICS --- */
        .stock-data-box {
            background-color: #111;
            border: 1px solid #333;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
        }
        .ma-badge {
            background-color: #333;
            color: #FF7F50;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'JetBrains Mono';
            font-size: 0.8rem;
            margin-left: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# SESSION & AUTH
# ==========================================
if 'page' not in st.session_state: st.session_state['page'] = 'auth'
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

# חיבור לגוגל שיטס
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        return gspread.authorize(creds)
    except: return None

def get_worksheet(sheet_name):
    client = get_client()
    if client:
        try: return client.open("StockWatcherDB").worksheet(sheet_name)
        except: return None
    return None

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

def add_user_to_db(email, password, phone):
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and 'email' in df.columns:
            if email in df['email'].values:
                st.warning("משתמש קיים במערכת")
                return False
    except: pass
    row = [email, make_hashes(password), str(datetime.now()), phone]
    try: sheet.append_row(row); return True
    except: return False

def login_user(email, password):
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        data = sheet.get_all_records()
        if not data: return False
        df = pd.DataFrame(data)
        if 'email' not in df.columns: return False
        user = df[df['email'] == email]
        if user.empty: return False
        if check_hashes(password, user.iloc[0]['password']): return True
    except: pass
    return False

# ==========================================
# DATA LOGIC (WITH MA150)
# ==========================================
@st.cache_data(ttl=60)
def get_stock_data_full(symbol):
    """שואב נתונים + היסטוריה לגרף + MA150"""
    try:
        t = yf.Ticker(symbol)
        # שואבים שנה אחורה כדי שיהיה מספיק ל-150 יום
        hist = t.history(period="1y")
        
        if hist.empty: return None
        
        current_price = hist['Close'].iloc[-1]
        
        # חישוב MA150
        ma150 = 0.0
        if len(hist) >= 150:
            ma150 = hist['Close'].rolling(window=150).mean().iloc[-1]
            
        return {
            "price": current_price,
            "ma150": ma150,
            "hist": hist,
            "symbol": symbol
        }
    except: return None

def save_alert(ticker, min_p, max_p, vol, one_time):
    sheet = get_worksheet("Rules")
    if not sheet: 
        st.error("שגיאת חיבור למסד נתונים")
        return
    row = [
        st.session_state.user_email, ticker, 
        min_p if min_p > 0 else "", max_p if max_p > 0 else "", 
        vol, str(datetime.now()), "TRUE" if one_time else "FALSE", "Active"
    ]
    try:
        sheet.append_row(row)
        st.toast(f"התראה נוצרה עבור {ticker}", icon="✅")
        time.sleep(1)
        st.rerun()
    except Exception as e: st.error(f"Error: {e}")

def navigate_to(page): st.session_state['page'] = page; st.rerun()

# פונקציה לציור גרף
def render_chart(hist_data, title):
    fig = go.Figure(data=[go.Candlestick(x=hist_data.index,
                open=hist_data['Open'], high=hist_data['High'],
                low=hist_data['Low'], close=hist_data['Close'])])
    fig.update_layout(
        title=dict(text=title, font=dict(color="white")),
        height=300, 
        margin=dict(l=0, r=0, t=30, b=0), 
        paper_bgcolor='#111', 
        plot_bgcolor='#111', 
        xaxis_rangeslider_visible=False,
        font=dict(color="white")
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# AUTH PAGE
# ==========================================
def auth_page():
    col_img, col_form = st.columns([1.5, 1])
    with col_img:
        try: st.image("login_image.png", use_container_width=True)
        except: st.warning("Missing login_image.png")

    with col_form:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="logo-title">STOCKPULSE</div>', unsafe_allow_html=True)
        st.markdown('<div class="logo-subtitle">TERMINAL ACCESS</div>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["LOG IN", "SIGN UP"])
        
        with tab1:
            email = st.text_input("EMAIL", key="l_e")
            pwd = st.text_input("PASSWORD", type="password", key="l_p")
            if st.button("LOG IN"):
                if login_user(email, pwd):
                    st.session_state.user_email = email
                    st.session_state.logged_in = True
                    navigate_to('dashboard')
                else: st.error("פרטים שגויים")
            
            st.markdown('<div style="text-align:center; margin:20px 0; color:#888;">— OR —</div>', unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns([0.5, 1, 1, 1, 0.5])
            with c2: st.button("G", key="g")
            with c3: st.button("", key="a")
            with c4: st.button("in", key="i")

        with tab2:
            ne = st.text_input("EMAIL", key="s_e")
            np = st.text_input("PASSWORD", type="password", key="s_p")
            ph = st.text_input("WHATSAPP", key="s_ph")
            if st.button("CREATE ACCOUNT"):
                if add_user_to_db(ne, np, ph): st.success("נוצר בהצלחה")
                else: st.error("שגיאה ביצירה")

# ==========================================
# DASHBOARD PAGE
# ==========================================
def dashboard_page():
    # Header
    c1, c2 = st.columns([8, 1])
    with c1: st.title("MARKET DASHBOARD")
    with c2: 
        if st.button("LOGOUT"):
            st.session_state.logged_in = False
            navigate_to('auth')
    st.markdown("---")

    col_alert, col_list = st.columns([1, 1.5], gap="large")

    # --- צד ימין: יצירת התראה (עם גרף ו-MA150) ---
    with col_alert:
        st.subheader("📟 Create Alert")
        with st.container(border=True):
            tick = st.text_input("SYMBOL", value="NVDA").upper()
            
            # משתני ברירת מחדל
            current_p = 0.0
            ma150_val = 0.0
            
            if tick:
                data = get_stock_data_full(tick)
                if data:
                    current_p = data['price']
                    ma150_val = data['ma150']
                    
                    # הצגת נתונים בולטים
                    m1, m2 = st.columns(2)
                    with m1: st.metric("Current Price", f"${current_p:.2f}")
                    with m2: 
                        delta = current_p - ma150_val
                        st.metric("MA 150", f"${ma150_val:.2f}", f"{delta:.2f} diff")
                    
                    # הצגת גרף מידית למניה שנבחרה
                    render_chart(data['hist'], f"{tick} Price Action")
                    
                else:
                    st.error("Symbol not found")

            st.markdown("---")
            st.markdown("#### 🎯 Set Target Price")
            
            # --- לוגיקה חכמה לחיבור סליידר ואינפוט ---
            # אם אין מחיר ב-session, נאתחל אותו למחיר הנוכחי
            if 'target_price' not in st.session_state:
                st.session_state.target_price = current_p

            # חישוב טווח דינמי לסליידר (כדי לא להגביל את המשתמש)
            # הטווח יהיה בין 0 ל-פי 3 מהמחיר הנוכחי (או מהמחיר שהוקלד)
            dynamic_max = max(float(current_p) * 3, float(st.session_state.target_price) * 2, 500.0)
            
            # 1. קודם מציגים את האינפוט (לדיוק)
            manual_input = st.number_input(
                "Manual Input ($)", 
                value=float(st.session_state.target_price),
                step=0.5,
                key="manual_input"
            )
            
            # עדכון הסטייט אם האינפוט השתנה
            if manual_input != st.session_state.target_price:
                st.session_state.target_price = manual_input
            
            # 2. מציגים את הסליידר (Fine Tune) המחובר לאותו משתנה
            slider_val = st.slider(
                "Fine Tune Slider", 
                min_value=0.0, 
                max_value=dynamic_max, 
                value=float(st.session_state.target_price),
                step=0.1,
                key="slider_input"
            )
            
            # סנכרון דו-כיווני: אם הסליידר זז, הוא מעדכן את האינפוט בריצה הבאה
            if slider_val != st.session_state.target_price:
                 st.session_state.target_price = slider_val
                 st.rerun() # רענון כדי שהאינפוט יתעדכן ויזואלית
                 
            st.markdown(f"Selected Target: **${st.session_state.target_price:.2f}**")
            
            vol = st.number_input("Min Volume (M)", value=5, step=1)
            
            if st.button("ACTIVATE ALERT", use_container_width=True):
                target = st.session_state.target_price
                if tick and target > 0:
                    min_p = target if target < current_p else 0
                    max_p = target if target > current_p else 0
                    save_alert(tick, min_p, max_p, vol*1000000, True)

    # --- צד שמאל: רשימת מעקב ---
    with col_list:
        h_col1, h_col2 = st.columns([3, 1])
        with h_col1: st.subheader("📋 Watchlist")
        with h_col2: 
            if st.button("Archive"): navigate_to('archive')

        # טעינת התראות
        sh = get_worksheet("Rules")
        if sh:
            try:
                raw_data = sh.get_all_records()
                if raw_data:
                    df = pd.DataFrame(raw_data)
                    # סינון לפי משתמש וסטטוס
                    col_u = 'user_email' if 'user_email' in df.columns else 'email'
                    if col_u in df.columns:
                        my_alerts = df[(df[col_u] == st.session_state.user_email) & (df['status'] == 'Active')]
                        
                        if my_alerts.empty:
                            st.info("No active alerts")
                        else:
                            for i, row in my_alerts.iterrows():
                                sym = row['symbol']
                                # שליפת נתונים עדכניים לכרטיסייה (כולל MA150)
                                live_data = get_stock_data_full(sym)
                                current_p_card = live_data['price'] if live_data else 0
                                ma150_card = live_data['ma150'] if live_data else 0
                                
                                target = row['max_price'] if row['max_price'] else row['min_price']
                                
                                # עיצוב כרטיסייה
                                with st.expander(f"{sym} | Target: ${target} | Curr: ${current_p_card:.2f}"):
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        st.write(f"**MA 150:** ${ma150_card:.2f}")
                                        st.write(f"**Vol:** {str(row['min_volume'])[:2]}M")
                                    with c2:
                                        diff = ((current_p_card - ma150_card) / ma150_card) * 100 if ma150_card else 0
                                        st.write(f"**vs MA150:** {diff:+.2f}%")
                                    
                                    # גרף בתוך האקספנדר
                                    if live_data:
                                        render_chart(live_data['hist'], "")
                                        
            except Exception as e:
                st.error(f"Error loading list: {e}")

# ==========================================
# ARCHIVE PAGE
# ==========================================
def archive_page():
    st.title("🗄️ LOGS")
    if st.button("BACK"): navigate_to('dashboard')
    st.markdown("---")
    sh = get_worksheet("Rules")
    if sh:
        try:
            df = pd.DataFrame(sh.get_all_records())
            if not df.empty and 'user_email' in df.columns:
                adf = df[(df['user_email'] == st.session_state.user_email) & (df['status'] != 'Active')]
                for i, row in adf.iterrows():
                    st.markdown(f"""
                    <div style="border-bottom:1px solid #333; padding:10px;">
                        <span style="color:#FF7F50; font-weight:bold;">{row['symbol']}</span> 
                        <span style="color:#AAA;"> | {row['created_at']}</span>
                        <span style="float:right;">{row['status']}</span>
                    </div>
                    """, unsafe_allow_html=True)
        except: pass

# ==========================================
# MAIN RUN
# ==========================================
apply_terminal_css()

if st.session_state.logged_in:
    if st.session_state['page'] == 'archive': archive_page()
    else: dashboard_page()
else:
    auth_page()
