import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import re
import yfinance as yf
import hashlib # חובה להצפנת סיסמאות

# ==========================================
# 1. הגדרות מערכת
# ==========================================
st.set_page_config(page_title="StockWatcher Elite", layout="wide", page_icon="🦁")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

# ==========================================
# 2. ניהול חיבור ו-DB (מעודכן לתמיכה בריבוי גיליונות)
# ==========================================
def get_client():
    """מחזיר את ה-Client של גוגל כדי שנוכל לבחור גיליון"""
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
    """פונקציה גנרית למשיכת גיליון ספציפי (Rules או USERS)"""
    client = get_client()
    if client:
        try:
            return client.open("StockWatcherDB").worksheet(sheet_name)
        except:
            st.error(f"לא נמצא גיליון בשם {sheet_name} בקובץ.")
            return None
    return None

# ==========================================
# 3. מודול הזדהות והרשמה (Auth Module)
# ==========================================
def make_hashes(password):
    """הצפנת סיסמה"""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    """בדיקת סיסמה מול ההצפנה"""
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

def add_user_to_db(email, password, phone):
    """רישום משתמש חדש"""
    sheet = get_worksheet("USERS") # וודא שיש לך גיליון כזה!
    if not sheet: return False

    # בדיקה אם המשתמש כבר קיים
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and email in df['email'].values:
            st.warning("המייל הזה כבר רשום במערכת.")
            return False
    except:
        pass # כנראה הגיליון ריק לגמרי

    hashed_pw = make_hashes(password)
    row = [email, hashed_pw, str(datetime.now()), phone]
    sheet.append_row(row)
    return True

def login_user(email, password):
    """בדיקת פרטי כניסה"""
    sheet = get_worksheet("USERS")
    if not sheet: return False
    
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty: return False
        
        # סינון לפי אימייל
        user_row = df[df['email'] == email]
        if user_row.empty: return False
        
        # בדיקת סיסמה
        stored_hash = user_row.iloc[0]['password']
        if check_hashes(password, stored_hash):
            return True
    except Exception as e:
        st.error(f"Login Error: {e}")
        
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
            else:
                data[name] = (0.0, 0.0)
        except:
            data[name] = (0.0, 0.0)
    return data

def get_real_time_price(symbol):
    if not symbol: return None
    try:
        return yf.Ticker(symbol).history(period="1d")['Close'].iloc[-1]
    except:
        return None

# ==========================================
# 5. רכיבי UI
# ==========================================
def show_metrics_bar():
    metrics = get_market_metrics()
    c1, c2, c3, c4 = st.columns(4)
    def d(col, lbl, k):
        v, c = metrics.get(k, (0,0))
        col.metric(lbl, f"{v:,.2f}", f"{c:+.2f}%")
    d(c1, "🇺🇸 S&P 500", "S&P 500")
    d(c2, "💾 NASDAQ", "NASDAQ")
    d(c3, "₿ Bitcoin", "Bitcoin")
    d(c4, "😨 VIX", "VIX")
    st.markdown("---")

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
# 6. מסכים (Login & Main)
# ==========================================
def login_screen_tabs():
    st.title("🦁 StockWatcher")
    
    tab1, tab2 = st.tabs(["🔐 כניסה (Login)", "📝 הרשמה (Sign Up)"])
    
    # --- Login Tab ---
    with tab1:
        with st.form("login_form"):
            email = st.text_input("אימייל").strip()
            password = st.text_input("סיסמה", type="password")
            
            if st.form_submit_button("התחבר"):
                if login_user(email, password):
                    st.success("התחברת בהצלחה!")
                    st.session_state.user_email = email
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("שם משתמש או סיסמה שגויים")

    # --- Sign Up Tab ---
    with tab2:
        st.markdown("### יצירת חשבון חדש")
        with st.form("signup_form"):
            new_email = st.text_input("אימייל להרשמה").strip()
            new_pass = st.text_input("בחר סיסמה", type="password")
            new_phone = st.text_input("מספר טלפון (עבור WhatsApp)")
            
            if st.form_submit_button("הרשם"):
                if new_email and new_pass:
                    if add_user_to_db(new_email, new_pass, new_phone):
                        st.success("החשבון נוצר בהצלחה! כעת ניתן להתחבר.")
                else:
                    st.warning("נא למלא אימייל וסיסמה")

def main_app():
    with st.sidebar:
        st.title("StockWatcher")
        st.caption(f"User: {st.session_state.user_email}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    
    show_metrics_bar()
    
    st.subheader("🔔 Create New Alert")
    with st.container(border=True):
        c_tick, c_curr = st.columns([3,2])
        tick = c_tick.text_input("Ticker").upper()
        curr_p = 0.0
        if tick:
            curr_p = get_real_time_price(tick) or 0.0
            if curr_p: c_curr.metric("Price", f"${curr_p:.2f}")
            else: c_curr.warning("Not Found")
            
        st.markdown("---")
        # Initialize UI with current price
        if 'last_ticker' not in st.session_state or st.session_state.last_ticker != tick:
            st.session_state.p_min = curr_p * 0.95 if curr_p else 0.0
            st.session_state.p_max = curr_p * 1.05 if curr_p else 0.0
            st.session_state.last_ticker = tick

        min_p = price_ui("Stop Price (Min)", "min")
        max_p = price_ui("Target Price (Max)", "max")
        
        st.markdown("---")
        c_vol, c_opt = st.columns(2)
        vol = c_vol.number_input("Min Vol", 1000000, step=500000)
        is_once = c_opt.checkbox("One Time?", True)
        
        if st.button("Set Alert", use_container_width=True):
            if tick: save_alert(tick, min_p, max_p, vol, is_once)

    # Watchlist
    st.subheader("📋 Watchlist")
    sh = get_worksheet("Rules")
    if sh:
        try:
            df = pd.DataFrame(sh.get_all_records())
            col = 'user_email' if 'user_email' in df.columns else 'email'
            if not df.empty and col in df.columns:
                my_df = df[df[col] == st.session_state.user_email]
                if not my_df.empty:
                    st.dataframe(my_df[['symbol','min_price','max_price','status']], use_container_width=True)
                else: st.info("Empty watchlist")
        except: st.write("No data")
    else: st.error("DB Error")

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen_tabs()

