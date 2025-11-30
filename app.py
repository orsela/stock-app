import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import yfinance as yf
import hashlib
import plotly.graph_objects as go

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="StockPulse - Real-Time Market Alerts",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="collapsed"
)

# ==========================================
# PREMIUM CSS - TRADINGVIEW INSPIRED
# ==========================================
def apply_premium_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
        
        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        /* ========================================
           GLOBAL STYLES
        ======================================== */
        .stApp {
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
            color: #FFFFFF;
        }
        
        /* REMOVE STREAMLIT ELEMENTS */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
        div[data-testid="stToolbar"] {display: none;}
        
        /* ========================================
           AUTH PAGE (LOGIN/SIGNUP)
        ======================================== */
        .auth-container {
            max-width: 440px;
            margin: 60px auto;
            padding: 48px 40px;
            background: rgba(20, 25, 35, 0.95);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 
                0 20px 60px rgba(0, 0, 0, 0.5),
                0 0 100px rgba(255, 107, 107, 0.1);
            backdrop-filter: blur(20px);
        }
        
        .logo-container {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .logo-title {
            font-size: 2.8rem;
            font-weight: 900;
            background: linear-gradient(135deg, #FF6B6B 0%, #FFB88C 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1.5px;
            margin-bottom: 8px;
        }
        
        .logo-subtitle {
            color: #8B92A7;
            font-size: 0.95rem;
            font-weight: 500;
            letter-spacing: 0.5px;
        }
        
        /* TABS */
        .stTabs {
            margin-bottom: 32px;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 4px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 48px;
            background: transparent;
            border-radius: 10px;
            color: #6B7280;
            font-size: 15px;
            font-weight: 600;
            border: none;
            padding: 0 28px;
            transition: all 0.3s ease;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            color: #FF6B6B;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(255, 107, 107, 0.15) 0%, rgba(255, 184, 140, 0.15) 100%) !important;
            color: #FF6B6B !important;
            box-shadow: 0 4px 12px rgba(255, 107, 107, 0.2);
        }
        
        /* INPUT FIELDS */
        .stTextInput > label {
            color: #D1D5DB !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            margin-bottom: 8px !important;
            letter-spacing: 0.3px !important;
        }
        
        .stTextInput > div > div > input {
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1.5px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            color: #FFFFFF !important;
            padding: 14px 16px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
        }
        
        .stTextInput > div > div > input:focus {
            border: 1.5px solid #FF6B6B !important;
            background: rgba(255, 107, 107, 0.05) !important;
            box-shadow: 0 0 0 3px rgba(255, 107, 107, 0.1) !important;
        }
        
        .stTextInput > div > div > input::placeholder {
            color: #6B7280 !important;
        }
        
        /* PRIMARY BUTTON */
        .stButton > button {
            background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 16px 0 !important;
            font-weight: 700 !important;
            font-size: 15px !important;
            width: 100% !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 8px 20px rgba(255, 107, 107, 0.3) !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 12px 28px rgba(255, 107, 107, 0.4) !important;
        }
        
        .stButton > button:active {
            transform: translateY(0) !important;
        }
        
        /* SOCIAL DIVIDER */
        .social-divider {
            text-align: center;
            color: #4B5563;
            font-size: 12px;
            font-weight: 600;
            margin: 32px 0 24px 0;
            position: relative;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .social-divider::before,
        .social-divider::after {
            content: "";
            position: absolute;
            top: 50%;
            width: 42%;
            height: 1px;
            background: rgba(255, 255, 255, 0.08);
        }
        
        .social-divider::before { left: 0; }
        .social-divider::after { right: 0; }
        
        /* SOCIAL BUTTONS */
        div[data-testid="column"] .stButton > button[key*="social"] {
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1.5px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            padding: 14px !important;
            color: #FFFFFF !important;
            font-size: 20px !important;
            font-weight: 700 !important;
            box-shadow: none !important;
            text-transform: none !important;
            letter-spacing: 0 !important;
        }
        
        div[data-testid="column"] .stButton > button[key*="social"]:hover {
            background: rgba(255, 255, 255, 0.08) !important;
            border-color: rgba(255, 107, 107, 0.3) !important;
            transform: translateY(-2px) !important;
        }
        
        /* ========================================
           DASHBOARD PAGE
        ======================================== */
        .dashboard-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 24px 0;
            margin-bottom: 32px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        
        .dashboard-title {
            font-size: 2.2rem;
            font-weight: 900;
            color: #FFFFFF;
            letter-spacing: -1px;
        }
        
        /* MARKET METRICS */
        .metric-card {
            background: linear-gradient(135deg, rgba(30, 35, 50, 0.8) 0%, rgba(20, 25, 35, 0.9) 100%);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 20px;
            padding: 24px 20px;
            text-align: center;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        
        .metric-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #FF6B6B, #FFB88C);
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-6px);
            border-color: rgba(255, 107, 107, 0.3);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        }
        
        .metric-card:hover::before {
            opacity: 1;
        }
        
        .metric-label {
            color: #8B92A7;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 12px;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 900;
            color: #FFFFFF;
            margin: 8px 0;
            letter-spacing: -0.5px;
        }
        
        .metric-change {
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        
        .metric-positive { 
            color: #10B981;
            text-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
        }
        
        .metric-negative { 
            color: #EF4444;
            text-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
        }
        
        /* ALERT PANEL */
        .alert-panel {
            background: linear-gradient(135deg, rgba(30, 35, 50, 0.9) 0%, rgba(20, 25, 35, 0.95) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            padding: 32px 28px;
            height: 100%;
            backdrop-filter: blur(10px);
        }
        
        .panel-title {
            font-size: 1.4rem;
            font-weight: 800;
            color: #FFFFFF;
            margin-bottom: 28px;
            display: flex;
            align-items: center;
            gap: 12px;
            letter-spacing: -0.5px;
        }
        
        .panel-title::before {
            content: "";
            width: 4px;
            height: 24px;
            background: linear-gradient(180deg, #FF6B6B, #FFB88C);
            border-radius: 2px;
        }
        
        /* NUMBER INPUT */
        .stNumberInput > label {
            color: #D1D5DB !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            margin-bottom: 8px !important;
        }
        
        .stNumberInput > div > div > input {
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1.5px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }
        
        /* SLIDER */
        .stSlider > label {
            color: #D1D5DB !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }
        
        .stSlider > div > div > div > div {
            background: linear-gradient(90deg, #FF6B6B, #FFB88C) !important;
        }
        
        .stSlider > div > div > div > div > div {
            background: #FFFFFF !important;
            box-shadow: 0 4px 12px rgba(255, 107, 107, 0.4) !important;
        }
        
        /* STOCK CARD */
        .stock-card {
            background: linear-gradient(135deg, rgba(40, 45, 65, 0.6) 0%, rgba(30, 35, 50, 0.8) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 20px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        
        .stock-card::after {
            content: "";
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            width: 4px;
            background: linear-gradient(180deg, #FF6B6B, #FFB88C);
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .stock-card:hover {
            border-color:
