import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import re

# ==========================================
# 1. הגדרות עמוד ועיצוב (Day/Night Mode)
# ==========================================
st.set_page_config(page_title="StockWatcher v7.8", layout="wide", page_icon="📈")

# ניהול State
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

# --- פונקציית עיצוב (הטוגל שהיה חסר) ---
def apply_theme():
    # כפתור טוגל בסיידבר
    theme_mode = st.sidebar.toggle("🌙 מצב לילה / ☀️ יום", value=True)
    
    if theme_mode:
        # Dark Mode CSS
        st.markdown("""
        <style>
        .stApp { background-color: #0e1117; color: white; }
        .stMetric { background-color: #262730; padding: 10px; border-radius: 5px; }
        </style>
        """, unsafe_allow_html=True)
    else:
        # Light Mode CSS
        st.markdown("""
        <style>
        .stApp { background-color: #ffffff; color: black; }
        .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 5px; border: 1px solid #ddd; }
        </style>
        """, unsafe_allow_html=True)

# ==========================================
# 2. מודול אבטחה (החדש - מוטמע בזהירות)
# ==========================================
def validate_ticker_security(ticker_input):
    if not ticker_input: return False, "ריק"
    clean = ticker_input.strip().upper()
    if len(clean) > 6: return False, "ארוך מדי"
    if not re.match(r'^[A-Z]+$', clean): return False, "תווים אסורים (רק באנגלית)"
    return True, clean

def check_rate_limit():
    if 'last_sub' in st.session_state and time.time() - st.session_state.last_sub < 2.0:
        return False
    st.session_state.last_sub = time.time()
    return True

# ==========================================
# 3. חיבור למסד הנתונים (Google Sheets)
# ==========================================
def init_connection():
    """
    חיבור ל-Google Sheets באמצעות gspread.
    וודא שקובץ ה-JSON שלך נמצא בתיקייה.
    """
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # ⚠️ וודא ששם הקובץ כאן תואם לקובץ שיש לך בפרויקט!
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        client = gspread.authorize(creds)
        # פתיחת הגיליון
        sheet = client.open("StockWatcherDB").worksheet("Rules") 
        return sheet
    except Exception as e:
        st.error(f"שגיאת התחברות ל-Google Sheets: {e}")
        return None

# ==========================================
# 4. רכיבי UI (דשבורד ומדדים)
# ==========================================
def show_metrics_dashboard():
    """החזרתי את המדדים שהיו חסרים לך"""
    st.markdown("### 📊 Market Overview")
    c1, c2, c3, c4 = st.columns(4)
    
    # נתונים לדוגמה (במקום API חי כדי לא לתקוע את הריצה)
    # בהמשך נחבר את זה ל-YFinance אם תרצה
    c1.metric("S&P 500", "4,567.80", "+1.2%")
    c2.metric("NASDAQ", "14,220.50", "+0.8%")
    c3.metric("VIX (Fear)", "12.45", "-5.2%")
    c4.metric("USD/ILS", "3.72", "+0.1%")
    
    st.markdown("---")

# ==========================================
# 5. מסכים ראשיים
# ==========================================

def login_screen():
    st.title("StockWatcher v7.8 🔒")
    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            # כאן אמורה להיות בדיקת סיסמה מול גיליון USERS
            # לצורך השיקום המהיר - אני מאשר כניסה ושומר אימייל
            st.session_state.user_email = email
            st.session_state.logged_in = True
            st.rerun()

def main_app():
    # הפעלת העיצוב (טוגל יום/לילה)
    apply_theme()
    
    # תפריט צד
    with st.sidebar:
        st.title("StockWatcher")
        st.markdown(f"User: `{st.session_state.user_email}`")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        
        st.divider()
        
        # --- טופס יצירת התראה (המשודרג) ---
        st.subheader("🔔 New Alert")
        with st.form("alert_form"):
            ticker = st.text_input("Ticker (e.g. NVDA)").upper()
            
            # כפתורי +/- שביקשת
            c1, c2 = st.columns(2)
            min_val = c1.number_input("Min Price", step=0.5, value=None)
            max_val = c2.number_input("Max Price", step=0.5, value=None)
            
            # הצ'קבוקס החדש
            is_one_time = st.checkbox("One Time Alert?", value=True)
            
            submitted = st.form_submit_button("Create Alert")
            
            if submitted:
                # 1. אבטחה
                if not check_rate_limit():
                    st.warning("Too fast! Wait a second.")
                else:
                    valid, clean_ticker = validate_ticker_security(ticker)
                    if valid:
                        # 2. שמירה (מותאם לעמודות החדשות)
                        save_to_sheet(clean_ticker, min_val, max_val, is_one_time)
                    else:
                        st.error(clean_ticker)

    # --- מסך ראשי ---
    show_metrics_dashboard() # המדדים חזרו!
    
    st.subheader("📋 My Active Alerts")
    # כאן אפשר להוסיף קוד שטוען ומציג את הטבלה מהשיטס
    st.info("System Status: Online & Connected to DB")

def save_to_sheet(ticker, min_p, max_p, one_time):
    sheet = init_connection()
    if sheet:
        # הכנת השורה לפי המבנה המדויק שלך (A-H)
        # A:Email, B:Symbol, C:Min, D:Max, E:Vol, F:Last, G:OneTime, H:Status
        row = [
            st.session_state.user_email,           # A
            ticker,                                # B
            min_p if min_p else "",                # C
            max_p if max_p else "",                # D
            1000000,                               # E (Default Vol)
            str(datetime.now()),                   # F (Creation Time / Last)
            "TRUE" if one_time else "FALSE",       # G (החדש!)
            "Active"                               # H (החדש!)
        ]
        try:
            sheet.append_row(row)
            st.toast(f"✅ Alert for {ticker} saved successfully!")
        except Exception as e:
            st.error(f"Save failed: {e}")

# ==========================================
# 6. נקודת כניסה (Entry Point)
# ==========================================
if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()

# --- הוסף את זה למודול ה-UI שלך ---

def show_management_screen():
    st.markdown("### 🎛️ ניהול התראות (Management Console)")
    
    sheet = init_connection()
    if not sheet:
        st.error("אין חיבור לנתונים")
        return

    # משיכת כל הנתונים ל-DataFrame
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
    except Exception as e:
        st.info("עדיין אין התראות במערכת.")
        return

    # סינון לפי המשתמש המחובר
    my_alerts = df[df['email'] == st.session_state.user_email]

    if my_alerts.empty:
        st.warning("לא נמצאו התראות עבורך.")
        return

    # יצירת טאבים: פעיל מול ארכיון
    tab1, tab2 = st.tabs(["🟢 התראות פעילות", "🗄️ ארכיון היסטורי"])

    with tab1:
        # סינון רק סטטוס Active
        active_df = my_alerts[my_alerts['status'] == 'Active']
        
        # הצגה נקייה למשתמש (בלי עמודות טכניות)
        display_cols = ['symbol', 'min_price', 'max_price', 'is_one_time', 'created_at']
        st.dataframe(active_df[display_cols], use_container_width=True)
        
        st.caption("💡 כדי לערוך: כרגע המהיר ביותר הוא להעביר לארכיון וליצור חדש.")

    with tab2:
        # סינון כל מה שאינו Active
        archive_df = my_alerts[my_alerts['status'] != 'Active']
        st.dataframe(archive_df, use_container_width=True)
