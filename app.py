import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import re

# ==========================================
# 1. הגדרות מערכת
# ==========================================
st.set_page_config(page_title="StockWatcher Elite", layout="wide", page_icon="🦁")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

# ==========================================
# 2. ניהול חיבור (Cloud + Local Compatible)
# ==========================================
def init_connection():
    """
    פתרון חכם: בודק קודם אם יש secrets בענן של Streamlit.
    אם לא - מנסה לטעון קובץ מקומי. זה פותר את השגיאה האדומה.
    """
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        # ניסיון 1: חיבור דרך הענן (Streamlit Secrets)
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        # ניסיון 2: חיבור מקומי (קובץ JSON)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
            
        client = gspread.authorize(creds)
        return client.open("StockWatcherDB").worksheet("Rules")
        
    except Exception as e:
        # לא מציג שגיאה מיד כדי לא להפחיד משתמשים, אלא מחזיר None
        print(f"Connection Error: {e}") 
        return None

# ==========================================
# 3. רכיבי UI למשקיעים (הפיצ'רים שביקשת)
# ==========================================

def show_metrics_bar():
    """שורת המדדים כולל ביטקוין"""
    st.markdown("### 🌍 Global Markets Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    
    # עיצוב מותאם אישית למדדים
    c1.metric("🇺🇸 S&P 500", "4,567.80", "+1.2%")
    c2.metric("💾 NASDAQ", "14,220.50", "+0.8%")
    c3.metric("₿ Bitcoin", "37,850.00", "+2.4%") # הנה הביטקוין!
    c4.metric("😨 VIX", "12.45", "-5.2%")
    st.markdown("---")

def price_adjustment_ui(label, key_prefix):
    """
    רכיב שליטה במחיר: כפתורי אחוזים + הזנה ידנית.
    זה מחליף את הסליידר הרגיל למשהו מקצועי יותר.
    """
    col_input, col_btns = st.columns([2, 3])
    
    # נתונים התחלתיים ב-Session State לכל שדה בנפרד
    state_key = f"price_{key_prefix}"
    if state_key not in st.session_state:
        st.session_state[state_key] = 0.0

    with col_btns:
        st.write("") # ריווח
        st.write("") 
        # כפתורי אחוזים מהירים
        b1, b2, b3, b4 = st.columns(4)
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
        # עדכון הסטייט מהקלט הידני
        st.session_state[state_key] = val
        
    return val

# ==========================================
# 4. שמירה ולוגיקה
# ==========================================
def save_alert_to_db(ticker, min_p, max_p, min_vol, is_one_time):
    sheet = init_connection()
    if not sheet:
        st.error("⚠️ שגיאת חיבור לענן (Secrets לא מוגדרים).")
        return

    row = [
        st.session_state.user_email,
        ticker,
        min_p if min_p > 0 else "",
        max_p if max_p > 0 else "",
        min_vol,                            # הוספת הווליום
        str(datetime.now()),
        "TRUE" if is_one_time else "FALSE",
        "Active"
    ]
    
    try:
        sheet.append_row(row)
        st.success(f"✅ ההתראה עבור {ticker} נקלטה בהצלחה!")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"שגיאה בשמירה: {e}")

# ==========================================
# 5. האפליקציה הראשית
# ==========================================
def main_app():
    # סרגל צד עם פרופיל
    with st.sidebar:
        st.title("🦁 StockWatcher")
        st.info(f"מחובר: {st.session_state.user_email}")
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
            
        st.divider()
        st.caption("v8.0 - Investor Edition")

    # חלק עליון: מדדים
    show_metrics_bar()

    # חלק מרכזי: טופס יצירה (בעיצוב המעודכן)
    st.subheader("🔔 יצירת התראה חדשה (Investor Mode)")
    
    with st.container(border=True):
        col_ticker, col_icon = st.columns([4, 1])
        with col_ticker:
            ticker = st.text_input("סימול מניה (Ticker)", placeholder="למשל: NVDA, TSLA").upper()
        with col_icon:
            # אייקון דינמי (Placeholder)
            if ticker:
                st.markdown(f"<h1 style='text-align: center;'>🏦</h1>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # רכיבי המחיר המשודרגים (כפתורים + קלט)
        min_price = price_adjustment_ui("📉 מחיר מינימום (Stop)", "min")
        max_price = price_adjustment_ui("📈 מחיר מקסימום (Target)", "max")
        
        st.markdown("---")
        
        # ווליום (חדש!)
        vol_col, opt_col = st.columns(2)
        with vol_col:
            min_volume = st.number_input("🔊 ווליום מינימלי (Millions)", min_value=0, value=1000000, step=500000)
        with opt_col:
            st.write("")
            st.write("")
            is_one_time = st.checkbox("התראה חד-פעמית (One Time)", value=True)

        if st.button("🚀 צור התראה", use_container_width=True):
            if not ticker:
                st.warning("חובה להזין שם מניה")
            elif min_price == 0 and max_price == 0:
                st.warning("חובה להגדיר לפחות גבול מחיר אחד")
            else:
                save_alert_to_db(ticker, min_price, max_price, min_volume, is_one_time)

    # טבלת ניהול
    st.subheader("📋 ההתראות שלי")
    sheet = init_connection()
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            # סינון לפי משתמש
            col_email = 'user_email' if 'user_email' in df.columns else 'email'
            if not df.empty and col_email in df.columns:
                my_alerts = df[df[col_email] == st.session_state.user_email]
                if not my_alerts.empty:
                    # מציג עמודות רלוונטיות כולל ווליום
                    st.dataframe(my_alerts[['symbol', 'min_price', 'max_price', 'min_vol', 'status']], use_container_width=True)
                else:
                    st.info("אין התראות פעילות.")
        except:
            st.write("ממתין לנתונים...")
    else:
        st.warning("הגדר את ה-Secrets ב-Streamlit Cloud כדי לראות נתונים.")

# --- Login Mock ---
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
