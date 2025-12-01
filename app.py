import streamlit as st
import yfinance as yf
from datetime import datetime

# הגדרות בסיסיות
st.set_page_config(page_title="StockPulse 💹", layout="wide")

# ניהול מצב
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'alerts' not in st.session_state:
    st.session_state.alerts = []

# ==========================================
# דף כניסה
# ==========================================
def login_page():
    st.title("💹 StockPulse Terminal")
    st.markdown("### המסוף המתקדם להתראות מניות")
    
    with st.form("login"):
        email = st.text_input("📧 אימייל", value="admin")
        password = st.text_input("🔒 סיסמה", type="password", value="123")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("🚀 התחבר"):
                if email == "admin" and password == "123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("❌ שגוי! נסה admin/123")
        
        with col2:
            if st.form_submit_button("🎯 דמו מהיר"):
                st.session_state.logged_in = True
                st.rerun()

# ==========================================
# דאשבורד
# ==========================================
@st.cache_data(ttl=300)
def get_data():
    try:
        sp500 = yf.Ticker("^GSPC").history(period="2d")
        nasdaq = yf.Ticker("^IXIC").history(period="2d")
        btc = yf.Ticker("BTC-USD").history(period="2d")
        
        return {
            "S&P 500": (sp500['Close'][-1], ((sp500['Close'][-1]-sp500['Close'][-2])/sp500['Close'][-2]*100)),
            "NASDAQ": (nasdaq['Close'][-1], ((nasdaq['Close'][-1]-nasdaq['Close'][-2])/nasdaq['Close'][-2]*100)),
            "Bitcoin": (btc['Close'][-1], ((btc['Close'][-1]-btc['Close'][-2])/btc['Close'][-2]*100))
        }
    except:
        return {"S&P 500": (5200, 0.5), "NASDAQ": (18500, 1.2), "Bitcoin": (95000, -0.8)}

def dashboard():
    st.markdown("## 💹 נתוני שוק חיים")
    
    # מדדים
    data = get_data()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        val, change = data["S&P 500"]
        st.metric("S&P 500", f"{val:,.0f}", f"{change:.2f}%")
    
    with col2:
        val, change = data["NASDAQ"]
        st.metric("NASDAQ", f"{val:,.0f}", f"{change:.2f}%")
    
    with col3:
        val, change = data["Bitcoin"]
        st.metric("Bitcoin", f"${val:,.0f}", f"{change:.2f}%")
    
    # התראות
    col_left, col_right = st.columns([2,1])
    
    with col_right:
        st.markdown("### ➕ התראה חדשה")
        with st.form("alert_form"):
            ticker = st.text_input("מניה", value="NVDA")
            target = st.number_input("שינוי %", value=5.0)
            if st.form_submit_button("הוסף"):
                st.session_state.alerts.append({"ticker": ticker, "target": target})
                st.success("✅ נוספה!")
                st.rerun()
    
    with col_left:
        st.markdown("### 📋 התראות פעילות")
        if st.session_state.alerts:
            for alert in st.session_state.alerts:
                st.write(f"**{alert['ticker']}** - {alert['target']}%")
        else:
            st.info("אין התראות")
    
    # יציאה
    if st.button("🚪 יציאה"):
        st.session_state.logged_in = False
        st.rerun()

# ==========================================
# הרצה ראשית
# ==========================================
if not st.session_state.logged_in:
    login_page()
else:
    dashboard()
