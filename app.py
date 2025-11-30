import streamlit as st
import re
import time
from datetime import datetime

# --- 🛡️ SECURITY MODULE (ארכיטקט אבטחת מידע) ---

def validate_ticker_security(ticker_input):
    """
    מבצע בדיקת אבטחה קפדנית על הקלט של המניה.
    מונע SQL Injection, Formula Injection ו-XSS.
    """
    if not ticker_input:
        return False, "שדה המניה ריק."

    # 1. הלבנה: הסרת רווחים והמרה לאותיות גדולות
    clean_ticker = ticker_input.strip().upper()

    # 2. בדיקת אורך: מניעת Buffer Overflow / Spam
    if len(clean_ticker) > 6:
        return False, "שגיאת אבטחה: סימול מניה לא יכול לעלות על 6 תווים."

    # 3. Whitelist: אך ורק אותיות A-Z. 
    # חוסם ב-100% תווים מסוכנים כמו =, +, @, <, >
    if not re.match(r'^[A-Z]+$', clean_ticker):
        return False, "קלט לא חוקי: סימול מניה חייב להכיל אותיות אנגליות בלבד."

    return True, clean_ticker

def check_rate_limit():
    """
    מונע מבוטים או משתמשים להציף את המערכת בבקשות (DoS Prevention).
    """
    current_time = time.time()
    if 'last_submission_time' in st.session_state:
        time_passed = current_time - st.session_state.last_submission_time
        if time_passed < 2.0:  # חסימה של 2 שניות בין פעולות
            return False
    
    st.session_state.last_submission_time = current_time
    return True

# --- 🎨 UI HELPER COMPONENTS ---

def quick_price_buttons(base_price, key_prefix):
    """
    רכיב עזר ליצירת כפתורי אחוזים מהירים.
    מחזיר את המחיר המחושב אם נלחץ כפתור, או None.
    """
    cols = st.columns(5)
    percentages = [-10, -5, 0, 5, 10]
    
    selected_val = None
    for i, p in enumerate(percentages):
        label = f"{p}%" if p <= 0 else f"+{p}%"
        if cols[i].button(label, key=f"{key_prefix}_{p}"):
            selected_val = base_price * (1 + p/100)
            
    return selected_val

# --- 🚀 MAIN FORM COMPONENT ---

def show_secure_alert_form():
    st.markdown("### 🔔 יצירת התראה חדשה (מאובטח)")
    
    # הדמיה של מחיר נוכחי (במערכת האמיתית זה מגיע מה-API)
    # הערב נחבר את זה לקריאה אמיתית ל-YFinance לפי הטיקר
    current_price_mock = 100.00 

    with st.form("secure_alert_form"):
        # 1. קלט מניה
        ticker_raw = st.text_input("סימול מניה (Ticker)", placeholder="למשל: NVDA")
        
        st.info(f"מחיר שוק נוכחי (להדגמה): ${current_price_mock}")
        st.markdown("---")

        # 2. הגדרת מחירים (לוגיקה משופרת: UI היברידי)
        # שימוש ב-Session State כדי לאפשר לכפתורים לעדכן את המספרים
        
        col_min, col_max = st.columns(2)
        
        with col_min:
            st.markdown("**גבול תחתון (Stop Loss)**")
            min_val = st.number_input("מתחת ל-$:", min_value=0.0, step=0.5, value=None, key="input_min")
            st.caption("קיצורי דרך:")
            # כאן יהיו כפתורים חיצוניים (מחוץ ל-Form בדרך כלל, אך בסטרימליט זה טריקי בתוך Form.
            # לכן נשאיר את ה-Number Input עם ה-Step בתור הפתרון המרכזי בתוך הטופס)
            
        with col_max:
            st.markdown("**גבול עליון (Take Profit)**")
            max_val = st.number_input("מעל ל-$:", min_value=0.0, step=0.5, value=None, key="input_max")

        st.markdown("---")
        
        # 3. הגדרות נוספות (סעיפים 5, 6 מהמשקיעים)
        is_one_time = st.checkbox("התראה חד-פעמית (One-Time)", value=True, help="ההתראה תימחק/תעבור לארכיון לאחר שתשלח פעם אחת")
        
        # כפתור שליחה
        submitted = st.form_submit_button("צור התראה 🚀")

        if submitted:
            # שלב א': בדיקת Rate Limit (הגנה מפני הצפה)
            if not check_rate_limit():
                st.error("✋ נא להמתין מספר שניות בין בקשות.")
                return

            # שלב ב': סניטציה של הטיקר (הגנה מפני הזרקות)
            is_valid_ticker, ticker_clean = validate_ticker_security(ticker_raw)
            if not is_valid_ticker:
                st.error(f"⛔ {ticker_clean}") # כאן 'ticker_clean' מכיל את הודעת השגיאה
                return

            # שלב ג': בדיקת לוגיקה עסקית (חובה לפחות ערך אחד)
            if min_val is None and max_val is None:
                st.warning("⚠️ חובה להגדיר לפחות גבול תחתון אחד או גבול עליון.")
                return

            # שלב ד': הצלחה - הכנה לשמירה
            save_alert_to_db(
                ticker=ticker_clean,
                min_price=min_val,
                max_price=max_val,
                is_one_time=is_one_time,
                status="Active" # סטטוס התחלתי
            )

def save_alert_to_db(ticker, min_price, max_price, is_one_time, status):
    """
    פונקציית השמירה ל-Google Sheets.
    הערב נחליף את ה-Print בשורת הוספה ל-Sheet.
    """
    # המרת None למחרוזת ריקה עבור השיטס, או שמירה כ-None
    min_final = min_price if min_price is not None else ""
    max_final = max_price if max_price is not None else ""
    
    # יצירת מבנה הנתונים לשמירה
    new_row_data = [
        str(datetime.now()), # Timestamp
        ticker,              # Ticker (Sanitized)
        min_final,           # Min Price
        max_final,           # Max Price
        "TRUE" if is_one_time else "FALSE", # OneTime Column (New!)
        status,              # Status Column (New!)
        ""                   # Last Sent (Empty initially)
    ]
    
    # --- כאן תבוא הפקודה: sheet.append_row(new_row_data) ---
    st.success(f"✅ ההתראה עבור {ticker} נשמרה בהצלחה!")
    st.json({
        "Ticker": ticker,
        "Min": min_final,
        "Max": max_final,
        "Type": "One-Time" if is_one_time else "Recurring",
        "Status": status
    })

# --- הרצת האפליקציה ---
if __name__ == "__main__":
    st.set_page_config(page_title="StockWatcher Secure", layout="centered")
    show_secure_alert_form()
