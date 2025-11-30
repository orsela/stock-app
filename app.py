import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import re
import yfinance as yf # חובה לוודא שמותקן: pip install yfinance

# ==========================================
# 1. הגדרות מערכת
# ==========================================
st.set_page_config(page_title="StockWatcher Live", layout="wide", page_icon="⚡")
st.write("🔍 Debug Info:")
st.write("Available Keys in Secrets:", st.secrets.keys())
if "gcp_service_account" not in st.secrets:
    st.error("❌ המערכת לא מוצאת את הכותרת [gcp_service_account] ב-Secrets!")
else:
    st.success("✅ הכותרת נמצאה!")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

# ==========================================
# 2. מנוע נתונים חי (Yahoo Finance Engine)
# ==========================================
@st.cache_data(ttl=60) # שומר נתונים בזיכרון ל-60 שניות כדי לא להאט את האפליקציה
def get_market_metrics():
    """מושך נתונים בזמן אמת עבור המדדים המובילים"""
    tickers = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Bitcoin": "BTC-USD",
        "VIX": "^VIX"
    }
    data = {}
    for name, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            # משיכת היסטוריה של יומיים כדי לחשב שינוי יומי
            hist = ticker.history(period="5d") 
            if len(hist) >= 2:
                current_price = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                change_percent = ((current_price - prev_close) / prev_close) * 100
                data[name] = (current_price, change_percent)
            else:
                data[name] = (0.0, 0.0)
        except Exception:
            data[name] = (0.0, 0.0)
    return data

def get_real_time_price(symbol):
    """מושך מחיר למניה ספציפית שהמשתמש מקליד"""
    if not symbol: return None
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="1d")
        if not history.empty:
            return history['Close'].iloc[-1]
    except:
        return None
    return None

# ==========================================
# 3. ניהול חיבור (Secrets)
# ==========================================
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        client = gspread.authorize(creds)
        return client.open("StockWatcherDB").worksheet("Rules")
    except Exception as e:
        return None

# ==========================================
# 4. רכיבי UI
# ==========================================
def show_metrics_bar():
    st.markdown("### 🌍 Live Market Data (Yahoo Finance)")
    
    # טעינת הנתונים (עם Caching)
    metrics = get_market_metrics()
    
    c1, c2, c3, c4 = st.columns(4)
    
    # פונקציית עזר להצגה
    def display_metric(col, label, key):
        val, change = metrics.get(key, (0, 0))
        color = "normal"
        if change > 0: color = "normal" # ירוק כברירת מחדל בסטרימליט לערכים חיוביים
        col.metric(label, f"{val:,.2f}", f"{change:+.2f}%")

    display_metric(c1, "🇺🇸 S&P 500", "S&P 500")
    display_metric(c2, "💾 NASDAQ", "NASDAQ")
    display_metric(c3, "₿ Bitcoin", "Bitcoin")
    display_metric(c4, "😨 VIX", "VIX")
    st.markdown("---")

def price_adjustment_ui(label, key_prefix, default_val=0.0):
    """רכיב שליטה במחיר עם כפתורי אחוזים"""
    col_input, col_btns = st.columns([2, 3])
    
    state_key = f"price_{key_prefix}"
    if state_key not in st.session_state:
        st.session_state[state_key] = float(default_val)

    with col_btns:
        st.write("") 
        st.write("") 
        b1, b2, b3, b4 = st.columns(4)
        # עדכון המחיר בלחיצת כפתור
        if b1.button("-10%", key=f"{key_prefix}_m10"): st.session_state[state_key] *= 0.90
        if b2.button("-5%", key=f"{key_prefix}_m5"): st.session_state[state_key] *= 0.95
        if b3.button("+5%", key=f"{key_prefix}_p5"): st.session_state[state_key] *= 1.05
        if b4.button("+10%", key=f"{key_prefix}_p10"): st.session_state[state_key] *= 1.10

    with col_input:
        val = st.number_input(
            label, 
            value=float(st.session_state[state_key]), 
            step=0.5, 
            format="%.2f",
            key=f"input_{key_prefix}"
        )
        st.session_state[state_key] = val
        
    return val

# ==========================================
# 5. שמירה למסד הנתונים
# ==========================================
def save_alert_to_db(ticker, min_p, max_p, min_vol, is_one_time):
    sheet = init_connection()
    if not sheet:
        st.error("⚠️ שגיאת חיבור: בדוק את קובץ ה-secrets.json או הגדרות הענן.")
        return

    row = [
        st.session_state.user_email,
        ticker,
        min_p if min_p > 0 else "",
        max_p if max_p > 0 else "",
        min_vol,
        str(datetime.now()),
        "TRUE" if is_one_time else "FALSE",
        "Active"
    ]
    
    try:
        sheet.append_row(row)
        st.success(f"✅ Alert for {ticker} saved!")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Save Error: {e}")

# ==========================================
# 6. אפליקציה ראשית
# ==========================================
def main_app():
    with st.sidebar:
        st.title("🦁 StockWatcher")
        st.caption(f"Connected: {st.session_state.user_email}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()

    # 1. הצגת המדדים החיים
    show_metrics_bar()

    # 2. טופס יצירה
    st.subheader("🔔 Create New Alert")
    
    with st.container(border=True):
        c_ticker, c_info = st.columns([3, 2])
        with c_ticker:
            ticker_input = st.text_input("Ticker Symbol", placeholder="NVDA").upper()
        
        # זיהוי מחיר בזמן אמת ברגע שמקלידים
        current_price = 0.0
        with c_info:
            if ticker_input:
                live_price = get_real_time_price(ticker_input)
                if live_price:
                    current_price = live_price
                    st.metric("Current Price", f"${live_price:,.2f}")
                else:
                    st.warning("Ticker not found")
            else:
                st.write("")

        st.markdown("---")
        
        # אם יש מחיר נוכחי, נשתמש בו כברירת מחדל בתיבות
        base_min = current_price * 0.95 if current_price > 0 else 0.0
        base_max = current_price * 1.05 if current_price > 0 else 0.0
        
        # שימוש ברכיבי המחיר המשודרגים
        # שים לב: אנחנו מאתחלים אותם פעם אחת. אם רוצים שיתעדכנו דינמית לפי הטיקר, 
        # צריך לוגיקה מורכבת יותר של Session State Callback, אבל לגרסה הזו זה יציב.
        min_price = price_adjustment_ui("📉 Stop Price (Min)", "min", base_min)
        max_price = price_adjustment_ui("📈 Target Price (Max)", "max", base_max)
        
        st.markdown("---")
        
        vol_c, opt_c = st.columns(2)
        with vol_c:
            min_vol = st.number_input("Min Volume", value=1000000, step=100000)
        with opt_c:
            st.write("")
            is_one_time = st.checkbox("One Time Alert?", value=True)

        if st.button("🚀 Set Alert", use_container_width=True):
            if ticker_input:
                save_alert_to_db(ticker_input, min_price, max_price, min_vol, is_one_time)
            else:
                st.error("Please enter a ticker symbol.")

    # 3. טבלת ניהול
    st.subheader("📋 Active Watchlist")
    sheet = init_connection()
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            col_email = 'user_email' if 'user_email' in df.columns else 'email'
            
            if not df.empty and col_email in df.columns:
                my_alerts = df[df[col_email] == st.session_state.user_email]
                if not my_alerts.empty:
                    # מציג את העמודות החשובות למשקיעים
                    st.dataframe(
                        my_alerts[['symbol', 'min_price', 'max_price', 'min_vol', 'status']], 
                        use_container_width=True
                    )
                else:
                    st.info("Your watchlist is empty.")
        except Exception as e:
            st.warning("Loading data...")
    else:
        st.error("Database connection failed. Check Secrets.")

# --- Login ---
def login_screen():
    st.title("StockWatcher Login")
    with st.form("login"):
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Enter"):
            st.session_state.user_email = email
            st.session_state.logged_in = True
            st.rerun()

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()

