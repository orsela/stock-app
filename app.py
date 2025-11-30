import streamlit as st
import re
import time
from datetime import datetime

# ==========================================
# 1. תצורת אפליקציה ו-State (ניהול פיתוח)
# ==========================================
st.set_page_config(page_title="StockWatcher Pro", layout="centered", page_icon="📈")

# אתחול משתנים גלובליים בזיכרון (Session State)
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = None

# ==========================================
# 2. מודול אבטחה (ארכיטקט Security)
# ==========================================
def validate_ticker_security(ticker_input):
    """
    בדיקת קלט קפדנית: מונע SQL Injection, XSS והזרקת נוסחאות.
    """
    if not ticker_input:
        return False, "שדה המניה ריק."

    # הלבנה: רווחים ואותיות גדולות
    clean_ticker = ticker_input.strip().upper()

    # בדיקת אורך (Buffer Overflow Prevention)
    if len(clean_ticker) > 6:
        return False, "שגיאת אבטחה: סימול מניה לא יכול לעלות על 6 תווים."

    # Whitelist: אך ורק אותיות A-Z (חוסם תווים כמו = + < >)
    if not re.match(r'^[A-Z]+$', clean_ticker):
        return False, "קלט לא חוקי: סימול מניה חייב להכיל אותיות אנגליות בלבד."

    return True, clean_ticker

def check_rate_limit():
    """
    מניעת הצפה (DoS) - מחייב המתנה של 2 שניות בין פעולות.
    """
    current_time = time.time()
    if 'last_submission_time' in st.session_state:
        time_passed = current_time - st.session_state.last_submission_time
        if time_passed < 2.0:
            return False
    
    st.session_state.last_submission_time = current_time
    return True

# ==========================================
# 3. מודול דאטה (חיבור ל-Google Sheets)
# ==========================================
def get_db_connection():
    """
    פונקציה זו אחראית על החיבור לגיליון.
    עליך לוודא שהחיבור שלך (Client) מוגדר כאן.
    """
    # ---------------------------------------------------------
    # TODO: הדבק כאן את שורות החיבור שלך ל-Google Sheets
    # דוגמה נפוצה (התאם לקוד הקיים שלך):
    # import gspread
    # service_account = gspread.service_account(filename='secrets.json')
    # sheet = service_account.open("StockWatcherDB").worksheet("Rules")
    # return sheet
    # ---------------------------------------------------------
    
    # לצורך הדגמה שהקוד רץ (כדי שלא יקרוס לך עכשיו), אני מחזיר None.
    # ברגע שתחבר את ה-Client האמיתי, הכל יעבוד.
    return None 

def save_alert_to_db(ticker, min_price, max_price, is_one_time, status):
    """
    שמירה לגיליון לפי המבנה שאושר:
    A: email | B: symbol | C: min | D: max | E: vol | F: last | G: one_time | H: status
    """
    sheet = get_db_connection()
    
    user_email = st.session_state.get('user_email', 'unknown@user.com')
    
    # טיפול בערכים ריקים
    final_min = min_price if min_price is not None else ""
    final_max = max_price if max_price is not None else ""
    default_min_vol = 1000000 # ערך ברירת מחדל לווליום
    
    # הכנת השורה לפי הסדר המדויק בגיליון
    row_to_append = [
        user_email,                          # A
        ticker,                              # B
        final_min,                           # C
        final_max,                           # D
        default_min_vol,                     # E
        "",                                  # F (Last Alert - ריק)
        "TRUE" if is_one_time else "FALSE",  # G
        status                               # H
    ]
    
    # --- ביצוע השמירה בפועל ---
    if sheet:
        try:
            sheet.append_row(row_to_append)
            st.success(f"✅ ההתראה עבור {ticker} נשמרה בהצלחה בבסיס הנתונים!")
        except Exception as e:
            st.error(f"שגיאה בשמירה לגיליון: {e}")
    else:
        # מצב DEBUG (אם עדיין לא חיברת את הגיליון)
        st.warning("⚠️ מצב סימולציה (DB לא מחובר). הנתונים שהיו נשמרים:")
        st.code(row_to_append)

# ==========================================
# 4. ממשק משתמש (UI/UX)
# ==========================================

def login_screen():
    """מסך התחברות מדמה - שומר את האימייל ב-Session"""
    st.header("🔐 כניסה למערכת")
    with st.form("login_form"):
        email = st.text_input("אימייל", placeholder="user@example.com")
        password = st.text_input("סיסמה", type="password")
        submitted = st.form_submit_button("התחבר")
        
        if submitted:
            # כאן תהיה בדיקת הסיסמה האמיתית שלך מול גיליון USERS
            if email and password: 
                st.session_state['user_email'] = email
                st.session_state['logged_in'] = True
                st.rerun() # רענון כדי לעבור למסך הבא
            else:
                st.error("נא להזין אימייל וסיסמה")

def app_screen():
    """המסך הראשי של האפליקציה"""
    # הצגת פרטי המשתמש המחובר (לצורך בקרה)
    st.sidebar.markdown(f"מחובר כ: **{st.session_state['user_email']}**")
    if st.sidebar.button("התנתק"):
        st.session_state['logged_in'] = False
        st.session_state['user_email'] = None
        st.rerun()

    st.title("StockWatcher 🚀")
    st.markdown("### הגדרת התראות מתקדמת")

    # --- טופס ההתראה המאובטח ---
    with st.form("secure_alert_form"):
        col_ticker, col_mock_price = st.columns([2, 1])
        with col_ticker:
            ticker_raw = st.text_input("סימול מניה (Ticker)", placeholder="NVDA").strip()
        with col_mock_price:
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption("מחיר שוק (Live): $145.30") # Placeholder

        st.markdown("---")
        st.markdown("#### הגדרת גבולות (Trigger)")
        
        # לוגיקת מחירים היברידית (מספרים + צעדים)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📉 גבול תחתון (Stop)**")
            min_val = st.number_input("מתחת ל ($):", min_value=0.0, step=0.5, value=None, key="min_input")
        with c2:
            st.markdown("**📈 גבול עליון (Target)**")
            max_val = st.number_input("מעל ל ($):", min_value=0.0, step=0.5, value=None, key="max_input")

        st.markdown("---")
        
        # הגדרות מתקדמות (One Time)
        is_one_time = st.checkbox("התראה חד-פעמית (מחק לאחר ביצוע)", value=True)
        
        # כפתור הפעולה
        submitted = st.form_submit_button("צור התראה חדשה", use_container_width=True)

        if submitted:
            # 1. שכבת הגנה - Rate Limit
            if not check_rate_limit():
                st.error("✋ נא להמתין מספר שניות בין פעולות.")
                return

            # 2. שכבת הגנה - Input Validation
            is_valid, ticker_clean = validate_ticker_security(ticker_raw)
            if not is_valid:
                st.error(f"⛔ {ticker_clean}")
                return

            # 3. בדיקת לוגיקה עסקית
            if min_val is None and max_val is None:
                st.warning("⚠️ חובה להגדיר לפחות גבול מחיר אחד.")
                return

            # 4. שמירה
            save_alert_to_db(ticker_clean, min_val, max_val, is_one_time, "Active")

# ==========================================
# 5. ריצה ראשית (Main Loop)
# ==========================================
if __name__ == "__main__":
    if st.session_state['logged_in']:
        app_screen()
    else:
        login_screen()
