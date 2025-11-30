# קובץ: scheduler.py
# מנוע בדיקת התראות - גרסה 8.2 (עם Yahoo Finance)

import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import yfinance as yf # חובה לוודא שמותקן

def init_connection():
    """חיבור לגיליון - משתמש בקובץ ה-JSON המקומי"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # כאן המנוע רץ מקומית, אז הוא משתמש בקובץ JSON
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        client = gspread.authorize(creds)
        return client.open("StockWatcherDB").worksheet("Rules")
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return None

def get_live_price(ticker):
    """משיכת מחיר בזמן אמת"""
    try:
        # שימוש ב-yfinance כדי לקבל מחיר עדכני
        ticker_obj = yf.Ticker(ticker)
        # fast_info הוא המהיר ביותר, או history אם רוצים דיוק של סגירה
        price = ticker_obj.fast_info['last_price']
        return price
    except:
        # גיבוי למקרה של כישלון במשיכה מהירה
        try:
            return yf.Ticker(ticker).history(period='1d')['Close'].iloc[-1]
        except:
            return None

def check_alerts():
    print(f"\n--- 🔄 Starting Scan: {datetime.now().strftime('%H:%M:%S')} ---")
    sheet = init_connection()
    if not sheet:
        return

    try:
        # משיכת כל הנתונים
        rows = sheet.get_all_records()
    except Exception as e:
        print(f"Error reading rows: {e}")
        return
    
    for i, row in enumerate(rows):
        # אינדקס שורה אמיתי בגיליון (מתחיל ב-2 כי 1 זה כותרת)
        real_row_index = i + 2
        
        # 1. דילוג על מה שלא פעיל
        if str(row.get('status')) != 'Active':
            continue
            
        ticker = row.get('symbol')
        min_p = row.get('min_price')
        max_p = row.get('max_price')
        is_one_time = str(row.get('is_one_time')).upper() == 'TRUE'
        
        if not ticker: continue

        # 2. בדיקת מחיר חי
        current_price = get_live_price(ticker)
        if current_price is None:
            print(f"⚠️ Could not fetch price for {ticker}")
            continue
            
        print(f"Checking {ticker}: ${current_price:.2f} (Min: {min_p}, Max: {max_p})")

        triggered = False
        msg = ""

        # 3. לוגיקת בדיקה
        # המרה למספרים בזהירות
        try:
            if min_p and current_price <= float(min_p):
                msg = f"📉 {ticker} dropped below {min_p} (Price: {current_price:.2f})"
                triggered = True
            elif max_p and current_price >= float(max_p):
                msg = f"🚀 {ticker} broke above {max_p} (Price: {current_price:.2f})"
                triggered = True
        except ValueError:
            continue # נתונים לא תקינים בשורה

        # 4. ביצוע פעולה
        if triggered:
            print(f"🔥 ALERT TRIGGERED: {msg}")
            
            # א. כאן תהיה שליחת הוואטסאפ בעתיד
            # send_whatsapp_message(row['phone'], msg)
            
            # ב. עדכון זמן שליחה אחרון (עמודה F - created_at/last_alert)
            # אנחנו נעדכן את זה כדי שנדע מתי נשלח
            # שים לב: זה תלוי במיקום העמודות שלך. בקוד ההוספה שלנו זה עמודה 6.
            
            # ג. טיפול ב-One Time
            if is_one_time:
                # עדכון סטטוס ל-Archived (עמודה H - עמודה מס' 8)
                sheet.update_cell(real_row_index, 8, "Archived")
                print(f"-> {ticker} moved to Archive.")
            else:
                print("-> Recurring alert (remains Active).")

if __name__ == "__main__":
    print("🚀 Scheduler Engine v8.2 Started...")
    while True:
        try:
            check_alerts()
        except Exception as e:
            print(f"Critical Engine Error: {e}")
        
        # המתנה של 60 שניות בין סריקות
        time.sleep(60)
