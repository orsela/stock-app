import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import re

# ==========================================
# 1. הגדרות מערכת ועיצוב (Version 7.9)
# ==========================================
st.set_page_config(page_title="StockWatcher v7.9", layout="wide", page_icon="📈")

# ניהול State
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

def apply_theme():
    """מנהל את מצב יום/לילה"""
    theme_mode = st.sidebar.toggle("🌙 מצב לילה / ☀️ יום", value=True)
    if theme_mode:
        st.markdown("""<style>.stApp { background-color: #0e1117; color: white; } 
        .stMetric { background-color: #262730; border-radius: 5px; padding: 10px; border: 1px solid #444; }</style>""", unsafe_allow_html=True)
    else:
        st.markdown("""<style>.stApp { background-color: #ffffff; color: black; } 
        .stMetric { background-color: #f0f2f6; border-radius: 5px; padding: 10px; border: 1px solid #ddd; }</style>""", unsafe_allow_html=True)

# ==========================================
# 2. מודול אבטחה (Security Layer)
# ==========================================
def validate_ticker_security(ticker_input):
    if not ticker_input: return False, "שדה ריק"
    clean = ticker_input.strip().upper()
    if len(clean) > 6: return False, "טיקר ארוך מדי"
    if not re.match(r'^[A-Z]+$', clean): return False, "תווים אסורים (רק באנגלית)"
    return True, clean

def check_rate_limit():
    if 'last_sub' in st.session_state and time.time() - st.session_state.last_sub < 2.0:
        return False
    st.session_state.last_sub = time.time()
    return True

# ==========================================
# 3. חיבור לנתונים (Database Layer)
# ==========================================
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # וודא שקובץ secrets.json נמצא בתיקייה
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        client = gspread.authorize(creds)
        return client.open("StockWatcherDB").worksheet("Rules")
    except Exception as e:
        st.error(f"שגיאת חיבור למסד נתונים: {e}")
        return None

# ==========================================
# 4. רכיבי ליבה ולוגיקה (Business Logic)
# ==========================================
def show_metrics():
    """המדדים בראש העמוד"""
    st.markdown("### 📊 Market Overview (Live Mock)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("S&P 500", "4,567.80", "+1.2%")
    c2.metric("NASDAQ", "14,220.50", "+0.8%")
    c3.metric("VIX (Fear)", "12.45", "-5.2%")
    c4.metric("Gold", "2,045.10", "+0.3%")
    st.markdown("---")

def save_alert(ticker, min_p, max_p, one_time):
    """שמירה לגיליון (תואם 8 עמודות)"""
    sheet = init_connection()
    if sheet:
        row = [
            st.session_state.user_email,           # A: Email
            ticker,                                # B: Symbol
            min_p if min_p else "",                # C: Min
            max_p if max_p else "",                # D: Max
            1000000,                               # E: Vol (Default)
            str(datetime.now()),                   # F: Created At
            "TRUE" if one_time else "FALSE",       # G: One Time
            "Active"                               # H: Status
        ]
        try:
            sheet.append_row(row)
            st.toast(f"✅ ההתראה ל-{ticker} נשמרה בהצלחה!")
            time.sleep(1) # השהייה קטנה כדי שהמשתמש יראה את הטוסט
            st.rerun()    # רענון המסך כדי לראות את ההתראה בטבלה מיד
        except Exception as e:
            st.error(f"שגיאה בשמירה: {e}")

def show_management_table():
    """הצגת טבלת ההתראות (פעיל/ארכיון)"""
    sheet = init_connection()
    if not sheet: return

    st.subheader("📋 My Alerts Console")
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # זיהוי דינמי של שם עמודת האימייל (למקרה של שינויים בגיליון)
        email_col = 'user_email' if 'user_email' in df.columns else 'email'
        
        if not df.empty and email_col in df.columns:
             # סינון לפי המשתמש המחובר
             my_alerts = df[df[email_col] == st.session_state.user_email]
        else:
            my_alerts = pd.DataFrame()

        if my_alerts.empty:
            st.info("עדיין לא יצרת התראות.")
            return

        # חלוקה לטאבים: פעיל מול היסטוריה
        tab1, tab2 = st.tabs(["🟢 Active Alerts", "🗄️ Archive History"])
        
        with tab1:
            if 'status' in my_alerts.columns:
                active = my_alerts[my_alerts['status'] == 'Active']
                if not active.empty:
                    # בחירת עמודות רלוונטיות להצגה
                    display_cols = ['symbol', 'min_price', 'max_price', 'is_one_time', 'created_at']
                    # סינון עמודות שקיימות בפועל למניעת שגיאות
                    final_cols = [c for c in display_cols if c in active.columns]
                    st.dataframe(active[final_cols], use_container_width=True)
                else:
                    st.caption("אין התראות פעילות כרגע.")
            else:
                st.error("חסרה עמודת 'status' בגיליון.")

        with tab2:
            if 'status' in my_alerts.columns:
                archive = my_alerts[my_alerts['status'] != 'Active']
                if not archive.empty:
                    st.dataframe(archive, use_container_width=True)
                else:
                    st.caption("הארכיון ריק.")

    except Exception as e:
        st.warning(f"טעינת נתונים נכשלה: {e}")

# ==========================================
# 5. האפליקציה הראשית (Main App Logic)
# ==========================================
def main_app():
    apply_theme()
    
    # --- Sidebar (Form) ---
    with st.sidebar:
        st.title("StockWatcher v7.9")
        st.write(f"Connected: `{st.session_state.user_email}`")
        if st.button("Logout", type="primary"):
            st.session_state.logged_in = False
            st.rerun()
        
        st.divider()
        st.subheader("🔔 Create Alert")
        
        with st.form("new_alert"):
            ticker = st.text_input("Ticker").upper()
            c1, c2 = st.columns(2)
            min_v = c1.number_input("Min Price ($)", step=0.5, value=None)
            max_v = c2.number_input("Max Price ($)", step=0.5, value=None)
            is_one_time = st.checkbox("One Time Alert?", value=True)
            
            if st.form_submit_button("Save Alert"):
                if check_rate_limit():
                    valid, clean_ticker = validate_ticker_security(ticker)
                    if valid:
                        if min_v is None and max_v is None:
                            st.warning("Must set at least Min or Max price.")
                        else:
                            save_alert(clean_ticker, min_v, max_v, is_one_time)
                    else:
                        st.error(clean_ticker)
                else:
                    st.warning("Please wait a few seconds...")

    # --- Main Content (Dashboard + Table) ---
    show_metrics()          
    show_management_table() 

def login_screen():
    st.title("StockWatcher Login 🔒")
    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Enter System"):
            # כאן המקום לחבר את בדיקת הסיסמה האמיתית מגיליון USERS
            if email:
                st.session_state.user_email = email
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Please enter email.")

# ==========================================
# 6. Entry Point
# ==========================================
if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
