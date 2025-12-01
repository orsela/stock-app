import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import threading

# הגדרות
st.set_page_config(page_title="StockPulse Pro 💹", layout="wide")

# מצב
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'alerts' not in st.session_state: st.session_state.alerts = []
if 'prices' not in st.session_state: st.session_state.prices = {}
if 'last_check' not in st.session_state: st.session_state.last_check = None

def get_live_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d", interval="5m")
        if len(data) > 0:
            return data['Close'][-1]
    except:
        return None
    return None

def check_alerts():
    if not st.session_state.alerts:
        return
    
    now = datetime.now()
    for alert in st.session_state.alerts[:]:  # Copy to avoid modification during iteration
        price = get_live_price(alert['ticker'])
        if price:
            prev_price = st.session_state.prices.get(alert['ticker'])
            if prev_price:
                change = ((price - prev_price) / prev_price) * 100
                if abs(change) >= alert['target']:
                    st.session_state.alerts.remove(alert)
                    st.session_state.prices[alert['ticker']] = price
                    st.success(f"🚨 **התראה!** {alert['ticker']} שינוי {change:.1f}% - מחיר: ${price:.2f}")
            st.session_state.prices[alert['ticker']] = price

@st.cache_data(ttl=30)
def get_market_data():
    tickers = {'^GSPC': 'S&P 500', '^IXIC': 'NASDAQ', 'BTC-USD': 'Bitcoin', '^VIX': 'VIX'}
    data = {}
    for sym, name in tickers.items():
        try:
            stock = yf.Ticker(sym)
            hist = stock.history(period="2d")
            if len(hist) > 1:
                current, prev = hist['Close'][-1], hist['Close'][-2]
                change = ((current - prev) / prev) * 100
                data[name] = (current, change)
        except:
            pass
    return data

# דף כניסה
def login_page():
    st.title("💹 StockPulse Pro")
    st.markdown("### מסוף התראות מניות **בזמן אמת**")
    
    with st.form("login"):
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("אימייל", value="admin")
            password = st.text_input("סיסמה", type="password", value="123")
        with col2:
            if st.form_submit_button("🚀 התחבר"):
                if email == "admin" and password == "123":
                    st.session_state.logged_in = True
                    st.rerun()
            if st.form_submit_button("🎯 דמו"):
                st.session_state.logged_in = True
                st.rerun()

# דאשבורד ראשי
def dashboard():
    # בדיקת התראות כל 30 שניות
    if st.session_state.last_check is None or (datetime.now() - st.session_state.last_check).seconds > 30:
        check_alerts()
        st.session_state.last_check = datetime.now()
    
    st.markdown(f"## 💹 שלום! מערכת פעילה - בדיקה אחרונה: {st.session_state.last_check.strftime('%H:%M:%S')}")
    
    # מדדי שוק
    st.markdown("### 📊 נתוני שוק חיים")
    data = get_market_data()
    cols = st.columns(4)
    for i, (name, (val, chg)) in enumerate(data.items()):
        with cols[i]:
            st.metric(name, f"{val:,.0f}", f"{chg:.2f}%")
    
    # התראות
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown("### ➕ התראה חדשה")
        with st.form("new_alert"):
            ticker = st.text_input("סימול", value="NVDA", help="AAPL, TSLA, BTC-USD, ^GSPC")
            target_pct = st.number_input("שינוי %", value=2.0, min_value=0.1, step=0.1)
            notes = st.text_input("הערות")
            
            if st.form_submit_button("➕ הוסף", use_container_width=True):
                alert = {
                    'ticker': ticker.upper(),
                    'target': target_pct,
                    'notes': notes,
                    'created': datetime.now().strftime("%H:%M"),
                    'status': 'פעיל'
                }
                st.session_state.alerts.append(alert)
                st.success(f"✅ {ticker} נוספה!")
                st.rerun()
    
    with col1:
        st.markdown("### 📋 התראות פעילות")
        if st.session_state.alerts:
            for i, alert in enumerate(st.session_state.alerts):
                current_price = st.session_state.prices.get(alert['ticker'])
                status = f"💰 {current_price:.2f}" if current_price else "⏳"
                st.write(f"**{alert['ticker']}** | {alert['target']}% | {status} | {alert['notes']}")
            
            if st.button("🗑️ נקה הכל"):
                st.session_state.alerts = []
                st.rerun()
        else:
            st.info("➕ אין התראות - הוסף ראשונה!")
    
    # כפתור יציאה
    if st.button("🚪 יציאה", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# הרצה
if not st.session_state.logged_in:
    login_page()
else:
    dashboard()
