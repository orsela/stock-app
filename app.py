def apply_dynamic_css(dark_mode: bool):
    # נתיבים קבועים (צריך לשמור אותם גלובלית בראש הקובץ)
    BASE_URL = "https://raw.githubusercontent.com/orsela/stock-app/main/assets"
    DASHBOARD_BG_URL = f"{BASE_URL}/dashboard_background.png" 

    if dark_mode:
        css = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&family=JetBrains+Mono:wght@400;700&family=Permanent+Marker&display=swap');
        
        /* --- GLOBAL BACKGROUND (TEMPORARILY COMMENTED OUT FOR STABILITY) --- */
        .stApp {{ 
            /* 🛑 נטרול הרקע הקבוע והשקוף שגרם לקריסה */
            background-color: #000000 !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', sans-serif; 
            position: relative;
        }}
        .stApp::before {{
            content: none; /* מנטרל את שכבת הרקע */
        }}
        
        /* --- FIXED HEADER (TEMPORARILY COMMENTED OUT) --- */
        .fixed-logo-header {{
            position: static; /* משבית את המיקום הקבוע */
            padding: 0;
            background-color: transparent;
            box-shadow: none;
        }}
        .main-content-padding {{
            padding-top: 10px; /* הפחתת הריפוד */
            padding-left: 20px;
            padding-right: 20px;
            min-height: 100vh;
        }}
        .logo-small-img {{
            height: 40px;
            width: auto;
        }}
        
        /* --- General Streamlit & Login Styles --- */
        #MainMenu, footer, header, .stDeployButton {{ visibility: hidden; }}
        h1, h2, h3, h4, h5, h6, p, label, .stMetricLabel {{ color: #FFFFFF !important; opacity: 1 !important; }}
        .rtl {{ direction: rtl; text-align: right; font-family: 'Inter', sans-serif; }}
        .stButton > button {{ background-color: #FF7F50 !important; color: #000000 !important; border: none !important; font-weight: 800 !important; border-radius: 4px !important; }}
        
        /* Login Page Layout */
        .login-container {{ display: flex; flex-direction: row; width: 100%; height: 100vh; margin: -20px; }}
        .login-image-side {{ 
            flex: 1; background: #111122; /* רקע כחול כהה */
            background-size: cover; background-position: center; display: flex; align-items: flex-end; justify-content: flex-start; 
            padding: 50px; position: relative;
        }}
        .login-image-side::after {{
            content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.4); 
        }}
        .login-form-side {{ flex: 1; background-color: #000000; padding: 80px 100px; color: #FFFFFF; display: flex; flex-direction: column; justify-content: center; }}
        
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
        """
        st.markdown(css, unsafe_allow_html=True)
