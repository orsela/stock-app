# קובץ: scheduler.py
# מטרת הקובץ: לרוץ ברקע, לבדוק מניות, לשלוח הודעות ולנקות את הטבלה

import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import yfinance as yf  # וודא שהתקנת: pip install yfinance

# --- הגדרות חיבור (אותו דבר כמו באפליקציה) ---
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        client = gspread.authorize(creds)
        return client.open("StockWatcherDB").worksheet("Rules")
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return None

# --- פונקציית עזר למחיר ---
def get_live_price(ticker):
    try:
        # משיכת מחיר אמיתי
        stock = yf.Ticker(ticker)
        # מנסה לקחת מחיר אחרון, אם השוק סגור לוקח מחיר סגירה
        data = stock.history(period="1d")
        if not data.empty:
            return data['Close'].iloc[-1]
        return 0
    except:
        return 0

# --- המנוע הראשי ---
def check_prices_and_alert():
    print(f"--- Starting Scan: {datetime.now()} ---")
    sheet = init_connection()
    if not sheet:
        return

    # משיכת כל הנתונים
    all_records = sheet.get_all_records()
    
    # מעבר על כל שורה
    # i הוא האינדקס (מתחיל ב-0), row הוא התוכן
    for i, row in enumerate(all_records):
        
        # 1. דילוג על מה שכבר טופל או בארכיון
        if row['status'] != 'Active':
            continue
            
        ticker = row['symbol']
        min_price = row['min_price']
        max_price = row['max_price']
        
        # 2. השגת מחיר
        current_price = get_live_price(ticker)
        print(f"Checking {ticker}: ${current_price:.2f}")

        triggered = False
        message = ""

        # 3. בדיקת תנאים
        # המרה ל-float רק אם יש ערך
        if min_price and current_price > 0 and current_price <= float(min_price):
            message = f"🚨 {ticker} ירד מתחת ל-${min_price} (מחיר: {current_price:.2f})"
            triggered = True
            
        elif max_price and current_price > 0 and current_price >= float(max_price):
            message = f"🚀 {ticker} פרץ מעל ${max_price} (מחיר: {current_price:.2f})"
            triggered = True
            
        # 4. ביצוע פעולות אם הופעל
        if triggered:
            print(f"--- ALERT: {message} ---")
            
            # א. כאן תבוא השליחה לווטסאפ/מייל (כרגע הדפסה)
            # send_whatsapp(row['phone'], message) 
            
            # ב. עדכון זמן שליחה אחרון בגיליון
            # הערה: ב-gspread שורות מתחילות ב-2 (כי 1 זה כותרת)
            real_row_index = i + 2 
            
            # עדכון עמודה F (Last Alert) - נניח שהיא עמודה 6
            sheet.update_cell(real_row_index, 6, str(datetime.now()))
            
            # ג. בדיקת One Time - העברה לארכיון
            # שים לב שזה מחפש את המחרוזת "TRUE" כפי שנשמרה מהאפליקציה
            if str(row['is_one_time']).upper() == 'TRUE':
                sheet.update_cell(real_row_index, 8, "Archived") # עמודה H
                print(f"Moved {ticker} to Archive.")

# --- לולאת ההרצה ---
if __name__ == "__main__":
    print("Monalisa Engine Started...")
    while True:
        try:
            check_prices_and_alert()
        except Exception as e:
            print(f"Crash detected: {e}")
        
        print("Sleeping for 60 seconds...")
        time.sleep(60) # רץ כל דקה