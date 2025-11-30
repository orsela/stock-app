import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import re
import yfinance as yf
import hashlib
import plotly.graph_objects as go # הספרייה החדשה לגרפים

# ==========================================
# 1. הגדרות מערכת ועיצוב (UI Layer)
# ==========================================
st.set_page_config(page_title="StockWatcher Pro", layout="wide", page_icon="🦁")

# הזרקת CSS לעיצוב כרטיסים ופונטים
def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;700;900&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Heebo', sans-serif;
        }
        
        /* --- כותרות --- */
        h1 { font-size: 3rem !important; font-weight: 900; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
        h2 { border-bottom: 2px solid #FF4B4B; padding-bottom: 5px; margin-top: 20px; }
        
        /* --- עיצוב המדדים (Metrics) - התיקון לכותרות --- */
        
        div[data-testid="stMetric"] {
            background-color: #1E1E1E;
            border: 1px solid #333;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            text-align: center;
            transition: 0.3s;
        }
        div[data-testid="stMetric"]:hover {
            border-color: #FF4B4B;
            transform: translateY(-2px);
        }

        /* >>> כאן השינוי הגדול: עיצוב שם המדד <<< */
        div[data-testid="stMetricLabel"] {
            display: flex;
            justify-content: center;
            align-items: center;
        }
        div[data-testid="stMetricLabel"] p {
            font-size: 1.3rem !important;  /* הגדלנו משמעותית */
            font-weight: 700 !important;   /* מודגש */
            color: #FF4B4B !important;     /* צבע אדום-כתום (המותג שלנו) */
            text-transform: uppercase;     /* אותיות גדולות */
            letter-spacing: 1px;           /* ריווח בין אותיות */
            margin-bottom: 5px !important;
        }

        /* הערך (המספר) */
        div[data-testid="stMetricValue"] div {
            font-size: 2rem !important;
            font-weight: 900 !important;
            color: #FFF !important;
        }

        /* האחוזים */
        div[data-testid="stMetricDelta"] div {
            font-size: 1rem !important;
            font-weight: bold;
        }

        /* --- כרטיסי מניות --- */
        div.stock-card {
            background-color: #262730;
            border: 1px solid #444;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .symbol-text { color: #FF4B4B; font-weight: 900; font-size: 1.8rem; }
        .status-badge { background: #444; padding: 4px 10px; border-radius: 6px; font-weight: bold; color: #fff; }
        .card-metric { font-size: 1rem; color: #bbb; }
        .card-value { font-size: 1.4em; font-weight: bold; color: #fff; }
        </style>
    """, unsafe_allow_html=True)
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

# ==========================================
# 2. מודול חיבור ו-DB (ללא שינוי מ-v8.2!)
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
# 3. מודול הזדהות (ללא שינוי מ-v8.2!)
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
        if not df.empty and email in df['email'].values:
            st.warning("המייל הזה כבר רשום במערכת.")
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

# ==========================================
# 5. רכיבי UI חדשים (New Components)
# ==========================================
def show_metrics_bar():
    st.markdown("### 🌍 Live Market Data")
    metrics = get_market_metrics()
    c1, c2, c3, c4 = st.columns(4)
    
    # השמות כאן (פרמטר שני) הם אלו שיוצגו בגדול ובאדום
    def d(col, lbl, k):
        v, c = metrics.get(k, (0,0))
        col.metric(lbl, f"{v:,.2f}", f"{c:+.2f}%")

    d(c1, "S&P 500", "S&P 500")       # שם נקי וברור
    d(c2, "NASDAQ 100", "NASDAQ")     # שם מלא
    d(c3, "BITCOIN", "Bitcoin")       # אותיות גדולות
    d(c4, "VIX Index", "VIX")         # שם מקצועי
    
    st.markdown("---")

def show_chart(ticker):
    """מציג גרף נרות יפניים בתוך כרטיס"""
    try:
        data = yf.Ticker(ticker).history(period="1mo")
        fig = go.Figure(data=[go.Candlestick(x=data.index,
                        open=data['Open'], high=data['High'],
                        low=data['Low'], close=data['Close'])])
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=20, b=0),
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.caption("לא ניתן לטעון גרף")

def show_alert_cards(df):
    """מחליף את הטבלה הישנה בכרטיסים מעוצבים - גרסה עם פונטים גדולים"""
    if df.empty:
        st.info("אין התראות פעילות להצגה.")
        return

    cols = st.columns(2)
    for i, (index, row) in enumerate(df.iterrows()):
        col = cols[i % 2]
        symbol = row['symbol']
        min_p = row['min_price']
        max_p = row['max_price']
        
        with col:
            # שימוש ב-Classים החדשים מה-CSS
            st.markdown(f"""
            <div class="stock-card">
                <div class="card-header">
                    <span class="symbol-text">{symbol}</span>
                    <span class="status-badge">Active</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <div><div class="card-metric">Stop Loss</div><div class="card-value">${min_p if min_p else '---'}</div></div>
                    <div style="text-align:right;"><div class="card-metric">Take Profit</div><div class="card-value">${max_p if max_p else '---'}</div></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"📊 גרף {symbol}"):
                show_chart(symbol)

def price_ui(label, key, default=0.0):
    c_in, c_btn = st.columns([2, 3])
    k_state = f"p_{key}"
    if k_state not in st.session_state: st.session_state[k_state] = float(default)
    with c_btn:
        st.write("")
        st.write("")
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("-10%", key=f"{key}_1"): st.session_state[k_state] *= 0.90
        if b2.button("-5%", key=f"{key}_2"): st.session_state[k_state] *= 0.95
        if b3.button("+5%", key=f"{key}_3"): st.session_state[k_state] *= 1.05
        if b4.button("+10%", key=f"{key}_4"): st.session_state[k_state] *= 1.10
    with c_in:
        val = st.number_input(label, value=float(st.session_state[k_state]), step=0.5, format="%.2f", key=f"in_{key}")
        st.session_state[k_state] = val
    return val

def save_alert(ticker, min_p, max_p, vol, one_time):
    sheet = get_worksheet("Rules")
    if not sheet: return
    row = [st.session_state.user_email, ticker, min_p if min_p>0 else "", max_p if max_p>0 else "", vol, str(datetime.now()), "TRUE" if one_time else "FALSE", "Active"]
    try:
        sheet.append_row(row)
        st.toast(f"✅ Saved alert for {ticker}")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Save Error: {e}")

# ==========================================
# 6. מסכים ראשיים
# ==========================================
def main_app():
    apply_custom_css() # הפעלת העיצוב החדש
    
    with st.sidebar:
        st.title("🦁 StockWatcher")
        st.caption(f"User: {st.session_state.user_email}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    
    show_metrics_bar()
    
    # חלוקת המסך: שמאל (תיק מעקב) - ימין (יצירת התראה)
    col_watchlist, col_form = st.columns([2, 1])
    
    # --- צד ימין: טופס יצירה ---
    with col_form:
        st.subheader("🔔 Create Alert")
        with st.container(border=True):
            tick = st.text_input("Ticker").upper()
            curr_p = 0.0
            if tick:
                curr_p = get_real_time_price(tick) or 0.0
                if curr_p: st.metric("Price", f"${curr_p:.2f}")
                
            if 'last_ticker' not in st.session_state or st.session_state.last_ticker != tick:
                st.session_state.p_min = curr_p * 0.95 if curr_p else 0.0
                st.session_state.p_max = curr_p * 1.05 if curr_p else 0.0
                st.session_state.last_ticker = tick

            min_p = price_ui("Stop Price", "min")
            max_p = price_ui("Target Price", "max")
            vol = st.number_input("Min Vol", 1000000, step=500000)
            is_once = st.checkbox("One Time?", True)
            
            if st.button("Set Alert", use_container_width=True):
                if tick: save_alert(tick, min_p, max_p, vol, is_once)

    # --- צד שמאל: כרטיסים וגרפים ---
    with col_watchlist:
        st.subheader("📋 Watchlist & Charts")
        sh = get_worksheet("Rules")
        if sh:
            try:
                df = pd.DataFrame(sh.get_all_records())
                col = 'user_email' if 'user_email' in df.columns else 'email'
                if not df.empty and col in df.columns:
                    my_df = df[(df[col] == st.session_state.user_email) & (df['status'] == 'Active')]
                    # קריאה לפונקציית הכרטיסים החדשה במקום הטבלה הישנה
                    show_alert_cards(my_df)
                else: st.info("No active alerts")
            except Exception as e: st.error(f"Data Error: {e}")
        else: st.error("DB Error")

def login_screen_tabs():
    st.title("🦁 StockWatcher")
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    with tab1:
        with st.form("l"):
            e = st.text_input("Email").strip()
            p = st.text_input("Pass", type="password")
            if st.form_submit_button("Go"):
                if login_user(e, p):
                    st.session_state.user_email = e
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("Failed")
    with tab2:
        with st.form("s"):
            ne = st.text_input("New Email").strip()
            np = st.text_input("New Pass", type="password")
            nph = st.text_input("Phone")
            if st.form_submit_button("Register"):
                if add_user_to_db(ne, np, nph): st.success("Created! Please Login.")

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen_tabs()



