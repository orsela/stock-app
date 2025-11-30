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
# 1. הגדרות מערכת ועיצוב (UI Layer - StockPulse Theme)
# ==========================================
st.set_page_config(page_title="StockPulse", layout="wide", page_icon="📈")

def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700;900&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
            background-color: #0E1117;
            color: #FAFAFA;
        }
        
        /* --- כפתורים ראשיים (כתום StockPulse) --- */
        div.stButton > button:first-child {
            background-color: #FF7F50; 
            color: white;
            border-radius: 8px;
            border: none;
            padding: 10px 24px;
            font-weight: bold;
            transition: 0.3s;
            width: 100%;
        }
        div.stButton > button:first-child:hover {
            background-color: #FF6347;
            box-shadow: 0px 4px 15px rgba(255, 127, 80, 0.4);
        }
        
        /* כפתור משני (Outline) */
        button.secondary-btn {
            background-color: transparent !important;
            border: 1px solid #FF7F50 !important;
            color: #FF7F50 !important;
        }

        /* --- כרטיסי התראה (Active) --- */
        .stock-card {
            background-color: #262730;
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #FF7F50;
            margin-bottom: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            transition: transform 0.2s;
        }
        .stock-card:hover {
            transform: translateY(-2px);
        }

        /* --- כרטיסי ארכיון (Expired) --- */
        .archive-card {
            background-color: #1E1E1E;
            padding: 15px;
            border-radius: 12px;
            border-left: 4px solid #555;
            margin-bottom: 10px;
            color: #888;
        }

        /* --- טיפוגרפיה --- */
        h1, h2, h3 { font-weight: 700; letter-spacing: -0.5px; }
        .metric-label { font-size: 0.9rem; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
        .metric-value { font-size: 1.8rem; font-weight: 900; color: #fff; }
        .metric-delta-pos { color: #00CC96; font-weight: bold; font-size: 0.9rem; }
        .metric-delta-neg { color: #EF553B; font-weight: bold; font-size: 0.9rem; }
        
        /* הסתרת אלמנטים דיפולטיביים */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# ניהול State לניווט
if 'page' not in st.session_state: st.session_state['page'] = 'login'
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

# ==========================================
# 2. מודול חיבור ו-DB (ללא שינוי - הפונקציונליות המקורית)
# ==========================================
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        return gspread.authorize(creds)
    except Exception as e:
        return None

def get_worksheet(sheet_name):
    client = get_client()
    if client:
        try:
            return client.open("StockWatcherDB").worksheet(sheet_name)
        except:
            return None
    return None

# ==========================================
# 3. מודול הזדהות (ללא שינוי)
# ==========================================
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

def add_user_to_db(email, password, phone):
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and 'email' in df.columns and email in df['email'].values:
            st.warning("User already exists.")
            return False
    except: pass
    hashed_pw = make_hashes(password)
    row = [email, hashed_pw, str(datetime.now()), phone]
    sheet.append_row(row)
    return True

def login_user(email, password):
    sheet = get_worksheet("USERS")
    if not sheet: return False
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return False
        user_row = df[df['email'] == email]
        if user_row.empty: return False
        stored_hash = user_row.iloc[0]['password']
        if check_hashes(password, stored_hash):
            return True
    except: pass
    return False

# ==========================================
# 4. מנוע נתונים (Yahoo Finance)
# ==========================================
@st.cache_data(ttl=60)
def get_market_metrics():
    tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "Bitcoin": "BTC-USD", "VIX": "^VIX"}
    data = {}
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            h = t.history(period="5d")
            if len(h) >= 2:
                curr = h['Close'].iloc[-1]
                prev = h['Close'].iloc[-2]
                chg = ((curr - prev) / prev) * 100
                data[name] = (curr, chg)
            else: data[name] = (0.0, 0.0)
        except: data[name] = (0.0, 0.0)
    return data

def get_real_time_price(symbol):
    if not symbol: return None
    try:
        return yf.Ticker(symbol).history(period="1d")['Close'].iloc[-1]
    except: return None

def save_alert(ticker, min_p, max_p, vol, one_time):
    sheet = get_worksheet("Rules")
    if not sheet: return
    row = [st.session_state.user_email, ticker, min_p if min_p>0 else "", max_p if max_p>0 else "", vol, str(datetime.now()), "TRUE" if one_time else "FALSE", "Active"]
    try:
        sheet.append_row(row)
        st.toast(f"✅ Alert Set: {ticker}", icon="🔥")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Save Error: {e}")

# ==========================================
# 5. רכיבי UI חדשים (New Components)
# ==========================================
def navigate_to(page):
    st.session_state['page'] = page
    st.rerun()

def show_custom_metrics():
    """סרגל מדדים בעיצוב נקי"""
    metrics = get_market_metrics()
    cols = st.columns(4)
    keys = ["S&P 500", "NASDAQ", "Bitcoin", "VIX"]
    
    for i, key in enumerate(keys):
        val, chg = metrics.get(key, (0,0))
        color_class = "metric-delta-pos" if chg >= 0 else "metric-delta-neg"
        arrow = "▲" if chg >= 0 else "▼"
        with cols[i]:
            st.markdown(f"""
            <div style="background:#16171c; padding:15px; border-radius:10px; text-align:center;">
                <div class="metric-label">{key}</div>
                <div class="metric-value">{val:,.2f}</div>
                <div class="{color_class}">{arrow} {chg:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

def show_chart(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1mo")
        fig = go.Figure(data=[go.Candlestick(x=data.index,
                                open=data['Open'], high=data['High'],
                                low=data['Low'], close=data['Close'])])
        fig.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=0),
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.caption("Chart unavailble")

# ==========================================
# 6. מסכים (Pages)
# ==========================================

# --- מסך כניסה (Login) ---
def login_page():
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.title("STOCKPULSE")
        st.markdown("### Real-Time Market Intelligence.")
        st.markdown("Join the traders who never miss a beat.")
        
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.subheader("Log In")
            email = st.text_input("Email", placeholder="name@example.com")
            password = st.text_input("Password", type="password")
            
            if st.button("LOG IN"):
                if login_user(email, password):
                    st.session_state.user_email = email
                    st.session_state.logged_in = True
                    navigate_to('dashboard')
                else:
                    st.error("Invalid email or password")
            
            st.markdown("---")
            if st.button("Create New Account", key="goto_signup"):
                navigate_to('signup')

# --- מסך הרשמה (Sign Up) ---
def signup_page():
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.title("Join StockPulse")
        st.markdown("### Get Alerts Directly to WhatsApp.")
        
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.subheader("Sign Up")
            new_email = st.text_input("Email Address")
            new_pass = st.text_input("Create Password", type="password")
            phone = st.text_input("WhatsApp Number", placeholder="+97250...")
            
            if st.button("SIGN UP"):
                if add_user_to_db(new_email, new_pass, phone):
                    st.success("Account Created! Please Log In.")
                    time.sleep(1.5)
                    navigate_to('login')
                
            st.markdown("---")
            if st.button("Back to Login", key="goto_login"):
                navigate_to('login')

# --- מסך ארכיון (Archive) ---
def archive_page():
    st.title("🗄️ Alert Archive")
    if st.button("← Back to Dashboard"):
        navigate_to('dashboard')
    
    st.markdown("---")
    sh = get_worksheet("Rules")
    if sh:
        try:
            df = pd.DataFrame(sh.get_all_records())
            # סינון: רק המשתמש הנוכחי, ורק סטטוס שאינו Active
            if not df.empty and 'user_email' in df.columns:
                archive_df = df[(df['user_email'] == st.session_state.user_email) & (df['status'] != 'Active')]
                
                if archive_df.empty:
                    st.info("Archive is empty.")
                else:
                    for i, row in archive_df.iterrows():
                         st.markdown(f"""
                        <div class="archive-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div>
                                    <strong style="font-size:1.2rem;">{row['symbol']}</strong>
                                    <span style="margin-left:10px; font-size:0.9rem;">{row['created_at']}</span>
                                </div>
                                <div>
                                    <span style="background:#333; padding:5px 10px; border-radius:5px;">{row['status']}</span>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No data found.")
        except Exception as e:
            st.error(f"Error loading archive: {e}")

# --- מסך ראשי (Dashboard) ---
def dashboard_page():
    # כותרת עליונה
    c1, c2 = st.columns([5, 1])
    with c1: st.title("StockPulse Dashboard")
    with c2: 
        if st.button("Log Out"):
            st.session_state.logged_in = False
            navigate_to('login')
            
    show_custom_metrics()
    
    # חלוקה ראשית
    col_setup, col_list = st.columns([1, 2])
    
    # === צד שמאל: הגדרת התראה (עם גלגלת) ===
    with col_setup:
        st.markdown("### 🔔 Create Alert")
        with st.container(border=True):
            tick = st.text_input("Ticker Symbol", value="NVDA").upper()
            
            # שליפת מחיר בזמן אמת
            curr_price = 0.0
            if tick:
                curr_price = get_real_time_price(tick) or 0.0
                st.caption(f"Current Price: ${curr_price:.2f}")

            # === לוגיקה לגלגלת מחיר (Wheel) ===
            st.markdown("<strong>Target Price</strong>", unsafe_allow_html=True)
            
            # ברירת מחדל אם אין ערך
            if 'slider_price' not in st.session_state: st.session_state.slider_price = curr_price
            
            # אינפוט לכתיבה ידנית
            input_val = st.number_input("Input", value=float(st.session_state.slider_price), label_visibility="collapsed", key="num_input")
            
            # סליידר לכיוונון עדין (טווח דינמי סביב המחיר הנוכחי)
            slider_min = float(curr_price) * 0.5
            slider_max = float(curr_price) * 1.5
            if slider_max == 0: slider_max = 100 # Fallback
            
            slider_val = st.slider("Fine Tune", min_value=slider_min, max_value=slider_max, value=input_val, key="slider_input")
            
            # סינכרון: הסליידר הוא הקובע הסופי לתצוגה
            final_target_price = slider_val
            
            st.markdown("---")
            min_vol = st.number_input("Min Volume (Millions)", value=5, step=1)
            
            # חיווי ווטסאפ
            st.caption("✅ Alert sends to WhatsApp")
            
            if st.button("SET ALERT"):
                if tick:
                    # כאן נחליט אם זה Stop Loss או Take Profit לפי המחיר הנוכחי
                    min_p_limit = final_target_price if final_target_price < curr_price else ""
                    max_p_limit = final_target_price if final_target_price > curr_price else ""
                    
                    save_alert(tick, min_p_limit, max_p_limit, min_vol*1000000, True)

    # === צד ימין: רשימת מעקב ===
    with col_list:
        h1, h2 = st.columns([4, 1])
        with h1: st.markdown("### 📋 Active Watchlist")
        with h2: 
            if st.button("Archive"): navigate_to('archive')

        sh = get_worksheet("Rules")
        if sh:
            try:
                df = pd.DataFrame(sh.get_all_records())
                # טיפול בשמות עמודות (תאימות לאחור)
                user_col = 'user_email' if 'user_email' in df.columns else 'email'
                
                if not df.empty and user_col in df.columns:
                    # סינון
                    my_df = df[(df[user_col] == st.session_state.user_email) & (df['status'] == 'Active')]
                    
                    if my_df.empty:
                        st.info("No active alerts yet.")
                    else:
                        # תצוגת כרטיסים (Grid)
                        grid_cols = st.columns(2)
                        for i, (idx, row) in enumerate(my_df.iterrows()):
                            col = grid_cols[i % 2]
                            sym = row['symbol']
                            target = row['max_price'] if row['max_price'] else row['min_price']
                            
                            with col:
                                st.markdown(f"""
                                <div class="stock-card">
                                    <div style="display:flex; justify-content:space-between; align-items:center;">
                                        <div style="font-size:1.5rem; font-weight:bold; color:#FF7F50;">{sym}</div>
                                        <div style="font-size:0.8rem; color:#888;">Vol: {str(row['min_volume'])[:2]}M</div>
                                    </div>
                                    <div style="margin-top:10px; font-size:1.1rem;">
                                        Target: <b>${target}</b>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                with st.expander("View Chart"):
                                    show_chart(sym)
                else:
                    st.info("DB Empty or Column Mismatch")
            except Exception as e:
                st.error(f"Error: {e}")

# ==========================================
# 7. הרצת האפליקציה (Main Router)
# ==========================================
apply_custom_css()

# ניתוב לפי מצב
if st.session_state.logged_in:
    if st.session_state['page'] == 'archive':
        archive_page()
    else:
        st.session_state['page'] = 'dashboard'
        dashboard_page()
else:
    # אם לא מחובר, נווט בין לוגין להרשמה
    if st.session_state['page'] == 'signup':
        signup_page()
    else:
        login_page()
