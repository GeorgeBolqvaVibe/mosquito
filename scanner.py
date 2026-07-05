import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import time
import threading
from supabase import create_client, Client

# --- 1. ბექენდ კონფიგურაცია ---
SUPABASE_URL = "https://gvgszdnnfbbyyvnyvnwu.supabase.co" 
SUPABASE_KEY = "sb_publishable_QS9xHLeep1KjOwz_137QGA_d2DYKku-"

TELEGRAM_TOKEN = "8787917755:AAFtwhMzhELVX2zoSwNv36D5xiME-5KE73w"
CHAT_ID = "5814652490"
SENT_ALERTS_FILE = "sent_alerts.txt"
FIXED_USER_ID = "00000000-0000-0000-0000-000000000001"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.set_page_config(page_title="Kitty Deep-Value Terminal v4.0", layout="wide", initial_sidebar_state="expanded")

# Bloomberg / TradingView Premium Dark UI Style
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        .stApp {
            background-color: #090d16;
            color: #c9d1d9;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
        }
        
        h1, h2, h3, h4, h5 {
            color: #ffffff !important;
            font-family: 'Inter', system-ui, sans-serif !important;
            font-weight: 600;
            letter-spacing: -0.5px;
        }

        /* Ticker Header Node Style */
        .ticker-header {
            background: linear-gradient(135deg, #111625 0%, #161b2c 100%);
            border: 1px solid #222735;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }
        
        /* შეხსენების ბანერი დღიურიდან */
        .journal-alert {
            background-color: #1c1810;
            border: 1px solid #ffb74d;
            border-left: 4px solid #ffb74d;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        
        /* ფინანსური ტერმინალის ბარათები */
        .metric-box {
            background-color: #111625;
            border: 1px solid #222735;
            border-radius: 8px;
            padding: 18px;
            text-align: center;
            transition: all 0.2s ease-in-out;
        }
        .metric-box:hover {
            border-color: #3b4257;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .metric-box-title {
            font-size: 11px;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            font-weight: 500;
        }
        .metric-box-value {
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
            margin-top: 6px;
            font-family: 'Courier New', monospace;
        }
        
        /* შკრელის ეჭვების რადარის ბარათები */
        .skeptic-card-danger {
            background-color: #1a0f0f;
            border: 1px solid #ef5350;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            min-height: 120px;
            box-shadow: 0 0 10px rgba(239, 83, 80, 0.05);
        }
        .skeptic-card-safe {
            background-color: #0c1512;
            border: 1px solid #26a69a;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            min-height: 120px;
            box-shadow: 0 0 10px rgba(38, 166, 154, 0.05);
        }
        .skeptic-card-warning {
            background-color: #18130e;
            border: 1px solid #ffb74d;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            min-height: 120px;
            box-shadow: 0 0 10px rgba(255, 183, 77, 0.05);
        }
        
        .signal-red { color: #ef5350 !important; font-weight: 600; }
        .signal-green { color: #26a69a !important; font-weight: 600; }
        .signal-amber { color: #ffb74d !important; font-weight: 600; }

        /* Modern Matrix & Tables styling */
        table {
            width: 100% !important;
            border-collapse: collapse !important;
            font-family: 'Inter', system-ui, sans-serif !important;
            background-color: #111625 !important;
            border-radius: 8px !important;
            overflow: hidden !important;
            border: 1px solid #222735 !important;
        }
        th {
            background-color: #161b2c !important;
            color: #8b949e !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.8px !important;
            font-size: 11px !important;
            padding: 12px 16px !important;
            border-bottom: 1px solid #222735 !important;
            text-align: left !important;
        }
        td {
            padding: 12px 16px !important;
            border-bottom: 1px solid #222735 !important;
            color: #ffffff !important;
            font-family: 'Courier New', monospace !important;
            font-size: 14px !important;
            text-align: left !important;
        }
        tr:nth-child(even) {
            background-color: #161b2c !important;
        }
        tr:hover {
            background-color: #1e2439 !important;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #090d16 !important;
            border-right: 1px solid #222735 !important;
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #ffffff !important;
            font-family: 'Inter', system-ui, sans-serif !important;
        }

        /* Input Fields Styling */
        div[data-baseweb="input"] {
            background-color: #111625 !important;
            border: 1px solid #222735 !important;
            border-radius: 8px !important;
            transition: all 0.2s ease-in-out !important;
        }
        div[data-baseweb="input"]:focus-within {
            border-color: #58a6ff !important;
            box-shadow: 0 0 0 1px #58a6ff !important;
        }
        input {
            color: #ffffff !important;
            font-family: 'Inter', system-ui, sans-serif !important;
        }
        textarea {
            color: #ffffff !important;
            background-color: #111625 !important;
            border: 1px solid #222735 !important;
            border-radius: 8px !important;
        }

        /* Buttons Styling */
        button[kind="secondary"] {
            background-color: #111625 !important;
            border: 1px solid #222735 !important;
            border-radius: 8px !important;
            color: #ffffff !important;
            font-weight: 500 !important;
            transition: all 0.2s ease-in-out !important;
        }
        button[kind="secondary"]:hover {
            border-color: #58a6ff !important;
            background-color: #161b2c !important;
            color: #58a6ff !important;
            box-shadow: 0 0 10px rgba(88, 166, 255, 0.1);
        }

        /* Tabs Styling */
        button[role="tab"] {
            font-family: 'Inter', system-ui, sans-serif !important;
            color: #8b949e !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            background-color: transparent !important;
            border: none !important;
        }
        button[role="tab"][aria-selected="true"] {
            color: #ffffff !important;
            border-bottom: 2px solid #58a6ff !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. დამხმარე ფუნქციები ---
def fmt_m(val):
    if val is None or isinstance(val, str) or pd.isna(val): return 'N/A'
    return f"${val / 1_000_000:.2f}M"

def fmt_pct(val):
    if val is None or isinstance(val, str) or pd.isna(val): return 'N/A'
    return f"{val * 100:.2f}%"

def calculate_z_score(info):
    try:
        working_capital = info.get('currentAssets', 0) - info.get('currentLiabilities', 0)
        total_assets = info.get('totalAssets', 1)
        retained_earnings = info.get('retainedEarnings', 0)
        ebit = info.get('ebitda', 0)
        market_cap = info.get('marketCap', 0)
        total_liabilities = info.get('totalDebt', 1)
        revenue = info.get('totalRevenue', 0)
        if total_assets <= 1: return 0
        X1 = working_capital / total_assets
        X2 = retained_earnings / total_assets
        X3 = ebit / total_assets
        X4 = market_cap / total_liabilities
        X5 = revenue / total_assets
        return round(1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 0.99*X5, 2)
    except: return 0

def fmt_financial_val(val):
    if val is None or isinstance(val, str) or pd.isna(val): return 'N/A'
    try:
        val_float = float(val)
        abs_val = abs(val_float)
        sign = "-" if val_float < 0 else ""
        if abs_val >= 1_000_000_000:
            return f"{sign}${abs_val / 1_000_000_000:.2f}B"
        elif abs_val >= 1_000_000:
            return f"{sign}${abs_val / 1_000_000:.2f}M"
        elif abs_val >= 1_000:
            return f"{sign}${abs_val / 1_000:.2f}K"
        else:
            return f"{sign}${abs_val:.2f}"
    except:
        return 'N/A'

def fetch_multi_year_financial_matrix(stock):
    try:
        fin = stock.financials
        bs = stock.balance_sheet
        cf = stock.cashflow
        
        if (fin is None or fin.empty) and (bs is None or bs.empty) and (cf is None or cf.empty):
            return None
            
        rows_to_extract = {
            "Revenue": ("Total Revenue", fin),
            "Gross Profit": ("Gross Profit", fin),
            "Total Cash": ("Cash Cash Equivalents And Short Term Investments", bs),
            "Total Debt": ("Total Debt", bs),
            "Free Cash Flow": ("Free Cash Flow", cf)
        }
        
        dates = []
        for df in [fin, bs, cf]:
            if df is not None and not df.empty:
                dates.extend(df.columns.tolist())
                
        if not dates:
            return None
            
        unique_dates = sorted(list(set(dates)), reverse=True)
        unique_dates = unique_dates[:4] # Keep up to 4 years
        
        data = {}
        for label, (row_name, df) in rows_to_extract.items():
            row_vals = {}
            for d in unique_dates:
                val = None
                if df is not None and not df.empty:
                    matching_cols = [c for c in df.columns if c == d]
                    if matching_cols:
                        col = matching_cols[0]
                        if row_name in df.index:
                            val = df.loc[row_name, col]
                            if isinstance(val, pd.Series):
                                val = val.iloc[0]
                        elif label == "Total Cash":
                            # Fallback for Total Cash
                            for fallback in ["Cash And Cash Equivalents", "Cash Financial"]:
                                if fallback in df.index:
                                    val = df.loc[fallback, col]
                                    if isinstance(val, pd.Series):
                                        val = val.iloc[0]
                                    break
                row_vals[d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)] = val
            data[label] = row_vals
            
        df_result = pd.DataFrame(data).T
        return df_result
    except:
        return None

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
    except: pass

# --- 3. 🤖 ფონური ბოტი ---
def background_monitor_loop():
    while True:
        try:
            res = supabase.table("watchlist").select("ticker").execute()
            if res.data:
                watchlist = list(set([item['ticker'] for item in res.data]))
                for ticker in watchlist:
                    stock = yf.Ticker(ticker)
                    news = stock.news
                    if news:
                        for single_news in reversed(news[:2]):
                            news_id = single_news.get('id')
                            content = single_news.get('content', {})
                            title = content.get('title')
                            link = content.get('clickThroughUrl', {}).get('url') or content.get('canonicalUrl', {}).get('url')
                            if link and news_id:
                                # უბრალო ფაილური დაზღვევა დუბლიკატებზე
                                import os
                                if not os.path.exists(SENT_ALERTS_FILE): open(SENT_ALERTS_FILE, "w").close()
                                with open(SENT_ALERTS_FILE, "r") as f: lines = f.read().splitlines()
                                if news_id not in lines:
                                    send_telegram_message(f"📰 *ავტომატური განახლება:* #{ticker}\n📌 {title}\n🔗 [ბმული]({link})")
                                    with open(SENT_ALERTS_FILE, "a") as f: f.write(f"{news_id}\n")
                                    time.sleep(1)
        except: pass
        time.sleep(1800)

@st.cache_resource
def start_global_monitor():
    t = threading.Thread(target=background_monitor_loop, daemon=True)
    t.start()
    return True

start_global_monitor()

# --- 4. ინტერფეისის სტრუქტურა ---
st.sidebar.title("🦁 Kitty Terminal v4.0")
ticker = st.sidebar.text_input("🚀 შეიყვანე აქციის ტიკერი:", "POET").upper()

tab_analyzer, tab_insiders, tab_whales, tab_journal = st.tabs([
    "🕵️‍♂️ Individual Analyzer & Skeptic Radar", 
    "💼 Insider Transactions",
    "🐋 Institutional Whales & Funds",
    "📓 Research Thesis Journal"
])

# ----------------- ჩანართი 1: ანალიზატორი & ეჭვების რადარი -----------------
with tab_analyzer:
    if ticker:
        with st.spinner(f"მიმდინარეობს გლობალური მონაცემების სინქრონიზაცია..."):
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                if info and 'longName' in info:
                    # 🔥 ინტეგრირებული შეხსენება დღიურიდან (Cross-Reference)
                    try:
                        j_check = supabase.table("kitty_journal").select("*").eq("ticker", ticker).execute()
                        if j_check.data:
                            latest_note = j_check.data[-1]
                            st.markdown(f"""
                                <div class="journal-alert">
                                    <h4 style="margin:0; color:#ffb74d;">⚠️ ჩანაწერი ნაპოვნია შენს პირად დღიურში!</h4>
                                    <p style="margin-top:8px; font-size:14px; color:#f0f6fc;"><b>შენი თეზისი:</b> {latest_note['notes']}</p>
                                    <small style="color:#8b949e;">🎯 Confidence Score: {latest_note['confidence_score']}/6</small>
                                </div>
                            """, unsafe_allow_html=True)
                    except: pass

                    # ჰედერი და ვოჩლისტი
                    c_h, c_b = st.columns([4, 1])
                    with c_h:
                        st.markdown(f"""
                            <div class="ticker-header">
                                <h2 style="margin:0; font-size: 24px; color: #ffffff;">🏢 {info.get('longName')} ({ticker})</h2>
                                <p style="margin: 8px 0 0 0; font-size: 13px; color: #8b949e;">
                                    📍 {info.get('sector')} | {info.get('industry')} | Employees: {info.get('fullTimeEmployees', 'N/A')}
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
                    with c_b:
                        st.write("")
                        st.write("")
                        if st.button("➕ Add to Watchlist", use_container_width=True):
                            try:
                                supabase.table("watchlist").insert({"user_id": FIXED_USER_ID, "ticker": ticker}).execute()
                                st.success("დაემატა!")
                                time.sleep(0.3)
                                st.rerun()
                            except: st.info("უკვე ვოჩლისტშია.")

                    # 🔗 100%-ით გასწორებული და სამუშაო როარინგ კიტის მალსახმობები
                    st.markdown("##### 🔗 საძიებო რობოტები (One-Click Research):")
                    c_lnk = st.columns(5)
                    # SEC ბრაუზერი პირდაპირ ტიკერით მუშაობს ამ ფორმატით
                    c_lnk[0].link_button("📄 SEC Edgar Filings", f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={ticker}&action=getcompany", use_container_width=True)
                    # OpenInsider მუშაობს სკრინერის რეჟიმში პირდაპირ ტიკერზე
                    c_lnk[1].link_button("💼 OpenInsider Activity", f"http://openinsider.com/screener?s={ticker}", use_container_width=True)
                    c_lnk[2].link_button("📈 TradingView Terminal", f"https://www.tradingview.com/symbols/{ticker}/", use_container_width=True)
                    c_lnk[3].link_button("🦁 Seeking Alpha", f"https://seekingalpha.com/symbol/{ticker}", use_container_width=True)
                    c_lnk[4].link_button("🐦 X Stream", f"https://x.com/search?q=%24{ticker}", use_container_width=True)

                    st.markdown("---")

                    # ☠️ მარტინ შკრელის ეჭვების რადარი (Skepticism Radar)
                    st.markdown("### ☠️ Skepticism & Fraud Radar (შკრელის მეთოდოლოგია)")
                    
                    emp = info.get('fullTimeEmployees', 0)
                    rev = info.get('totalRevenue', 0)
                    z_val = calculate_z_score(info)
                    
                    # Triggers
                    emp_danger = (emp is None or emp == 0 or emp < 10)
                    rev_danger = (rev is None or rev == 0)
                    z_danger = (z_val is not None and z_val != 0 and z_val < 1.81)
                    z_na = (z_val is None or z_val == 0)
                    
                    # Define individual box styles and classes
                    if emp_danger:
                        emp_desc = f"{emp or 0} თანამშრომელი (ცარიელი კონტორა)"
                        emp_box_class = "skeptic-card-danger"
                        emp_class = "signal-red"
                    else:
                        emp_desc = f"{emp} თანამშრომელი"
                        emp_box_class = "skeptic-card-safe"
                        emp_class = "signal-green"
                        
                    if rev_danger:
                        rev_desc = "$0 (პროდუქტი არ აქვთ)"
                        rev_box_class = "skeptic-card-danger"
                        rev_class = "signal-red"
                    else:
                        rev_desc = fmt_m(rev)
                        rev_box_class = "skeptic-card-safe"
                        rev_class = "signal-green"
                        
                    if z_na:
                        z_desc = "N/A (არასრული მონაცემები)"
                        z_box_class = "skeptic-card-warning"
                        z_class = "signal-amber"
                    elif z_danger:
                        z_desc = f"{z_val} (გაკოტრების/დილუაციის რისკი)"
                        z_box_class = "skeptic-card-danger"
                        z_class = "signal-red"
                    else:
                        z_desc = f"{z_val} (სტაბილურია)"
                        z_box_class = "skeptic-card-safe"
                        z_class = "signal-green"
                    
                    # Layout
                    sk_c1, sk_c2, sk_c3 = st.columns(3)
                    sk_c1.markdown(f"""
                        <div class="{emp_box_class}">
                            <div style="font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">👥 თანამშრომლები / Employees</div>
                            <div class="{emp_class}" style="font-size: 16px; font-weight: bold; margin-top: 10px;">{emp_desc}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    sk_c2.markdown(f"""
                        <div class="{rev_box_class}">
                            <div style="font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">💰 რეალური გაყიდვები / Revenue</div>
                            <div class="{rev_class}" style="font-size: 16px; font-weight: bold; margin-top: 10px;">{rev_desc}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    sk_c3.markdown(f"""
                        <div class="{z_box_class}">
                            <div style="font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">🛡️ Altman Z-Score</div>
                            <div class="{z_class}" style="font-size: 16px; font-weight: bold; margin-top: 10px;">{z_desc}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if emp_danger or rev_danger or z_danger:
                        st.markdown(f"""
                            <div style="background-color: #1a0f0f; border: 1px solid #ef5350; border-radius: 8px; padding: 12px; margin-top: 15px; margin-bottom: 15px; box-shadow: 0 0 10px rgba(239, 83, 80, 0.05);">
                                <span class="signal-red" style="font-size: 14px;">⚠️ <b>შკრელის მეთოდოლოგიის გაფრთხილება:</b> აღმოჩენილია პოტენციური ფინანსური ან ოპერაციული რისკი!</span>
                            </div>
                        """, unsafe_allow_html=True)

                    # ძირითადი ფინანსური მეტრიკები
                    st.markdown("### 📊 ძირითადი ფინანსური კოეფიციენტები")
                    m_c1, m_c2, m_c3, m_c4 = st.columns(4)
                    m_c1.markdown(f"<div class='metric-box'><div class='metric-box-title'>Price-to-Book (P/B)</div><div class='metric-box-value'>{info.get('priceToBook', 'N/A')}</div></div>", unsafe_allow_html=True)
                    m_c2.markdown(f"<div class='metric-box'><div class='metric-box-title'>Price-to-Sales (P/S)</div><div class='metric-box-value'>{info.get('priceToSalesTrailing12Months', 'N/A')}</div></div>", unsafe_allow_html=True)
                    m_c3.markdown(f"<div class='metric-box'><div class='metric-box-title'>Total Cash</div><div class='metric-box-value'>{fmt_m(info.get('totalCash'))}</div></div>", unsafe_allow_html=True)
                    m_c4.markdown(f"<div class='metric-box'><div class='metric-box-title'>Short % of Float</div><div class='metric-box-value'>{fmt_pct(info.get('shortPercentOfFloat'))}</div></div>", unsafe_allow_html=True)

                    # 📅 Multi-Year Financial Matrix (Roaring Kitty Style)
                    st.markdown("---")
                    st.markdown("### 📅 Multi-Year Financial Matrix (Roaring Kitty Style)")
                    with st.spinner("ფინანსური ისტორიის სინქრონიზაცია..."):
                        fin_matrix = fetch_multi_year_financial_matrix(stock)
                        if fin_matrix is not None and not fin_matrix.empty:
                            if hasattr(fin_matrix, 'map'):
                                formatted_matrix = fin_matrix.map(fmt_financial_val)
                            else:
                                formatted_matrix = fin_matrix.applymap(fmt_financial_val)
                            st.table(formatted_matrix)
                        else:
                            st.info("ფინანსური ისტორიის მონაცემები ვერ მოიძებნა ამ ტიკერისთვის.")

                    # გაფართოებული ჩარტების სექცია
                    st.markdown("---")
                    st.markdown("### 📈 გაფართოებული ინტერაქტიული ჩარტი")
                    time_frame = st.selectbox("შეცვალე ჩარტის დროის ინტერვალი:", ["1mo", "3mo", "6mo", "1y", "5y", "max"], index=3)
                    hist = stock.history(period=time_frame)
                    if not hist.empty:
                        st.line_chart(hist['Close'], width="stretch")
            except Exception as e: st.error(f"შეცდომა ანალიზისას: {e}")

# ----------------- ჩანართი 2: ინსაიდერები -----------------
with tab_insiders:
    st.subheader(f"💼 ინსაიდერების ოფიციალური შესყიდვები და გაყიდვები: #{ticker}")
    if ticker:
        try:
            insiders = yf.Ticker(ticker).insider_transactions
            if insiders is not None and not insiders.empty:
                st.dataframe(insiders[['Date', 'Insider', 'Position', 'Transaction', 'Shares', 'Value']], width="stretch")
            else: st.info("ბოლო პერიოდში ოფიციალური ინსაიდერული აქტივობა არ ფიქსირდება.")
        except: st.error("მონაცემები დროებით მიუწვდომელია.")

# ----------------- ჩანართი 3: WHALES & FUNDS (მსხვილი ფონდები) -----------------
with tab_whales:
    st.subheader(f"🐋 ვინ ფლობს #{ticker}-ს? (მსხვილი ინსტიტუციონალური ინვესტორები)")
    st.caption("ეს სექცია გიჩვენებთ, რომელი ჰეჯ-ფონდები და დიდი ინსტიტუტები დგანან ამ აქციის უკან და რა წილი აქვთ ნაყიდი.")
    if ticker:
        try:
            holders = yf.Ticker(ticker).institutional_holders
            if holders is not None and not holders.empty:
                # Safe column cleaning and mapping
                columns_to_keep = {
                    'Holder': 'ინსტიტუტი',
                    'Shares': 'აქციები',
                    'Date Reported': 'თარიღი',
                    'pctHeld': 'წილი %',
                    'Value': 'ღირებულება'
                }
                existing_cols = [c for c in columns_to_keep.keys() if c in holders.columns]
                holders_cleaned = holders[existing_cols].rename(columns=columns_to_keep)
                
                # Analytics metrics calculations
                total_shares = holders_cleaned["აქციები"].sum() if "აქციები" in holders_cleaned.columns else 0
                total_value = holders_cleaned["ღირებულება"].sum() if "ღირებულება" in holders_cleaned.columns else 0
                
                st.markdown("#### 📊 მსხვილი მფლობელების ანალიტიკა / Whales Analytics")
                c_an1, c_an2, c_an3 = st.columns(3)
                
                if "ღირებულება" in holders_cleaned.columns:
                    c_an1.markdown(f"<div class='metric-box'><div class='metric-box-title'>ჯამური ღირებულება / Total Value</div><div class='metric-box-value'>{fmt_financial_val(total_value)}</div></div>", unsafe_allow_html=True)
                if "აქციები" in holders_cleaned.columns:
                    c_an2.markdown(f"<div class='metric-box'><div class='metric-box-title'>ჯამური აქციები / Total Shares</div><div class='metric-box-value'>{total_shares:,}</div></div>", unsafe_allow_html=True)
                if not holders_cleaned.empty and "ინსტიტუტი" in holders_cleaned.columns:
                    top_holder = holders_cleaned.iloc[0]["ინსტიტუტი"]
                    top_pct = holders_cleaned.iloc[0]["წილი %"] if "წილი %" in holders_cleaned.columns else None
                    pct_str = fmt_pct(top_pct) if top_pct is not None else "N/A"
                    c_an3.markdown(f"<div class='metric-box'><div class='metric-box-title'>უმსხვილესი ინვესტორი / Top Whale</div><div class='metric-box-value' style='font-size: 14px;'>{top_holder}<br><span style='color: #2ea44f;'>({pct_str})</span></div></div>", unsafe_allow_html=True)
                
                st.markdown("##### 📁 დეტალური ცხრილი / Detailed Holders Table")
                st.dataframe(holders_cleaned, use_container_width=True)
            else: st.info("მონაცემები მსხვილი ინვესტორების შესახებ ვერ მოიძებნა.")
        except: st.error("ინფორმაციის წაკითხვა ვერ მოხერხდა.")
        
        # Placeholder for Network Sentiments
        st.markdown("---")
        st.markdown("### 🕸️ Analyst/Fund Network Sentiments")
        st.caption("ფონდების და ანალიტიკოსების ქსელური სენტიმენტები (ამჟამად დამუშავების პროცესშია)")
        st.markdown("""
            <div style="background-color: #12161f; border: 1px solid #21262d; border-radius: 8px; padding: 20px;">
                <h5 style="color: #58a6ff; margin: 0 0 10px 0;">🎙️ სოციალური და ქსელური რადარი (Value Investors Sentiment Tracker)</h5>
                <p style="font-size: 14px; color: #8b949e; margin-bottom: 15px;">
                    მალე: აქ გამოჩნდება Twitter/X, Substack და ცნობილი Value ინვესტორების (Mohnish Pabrai, Guy Spier, Li Lu და სხვები) აზრები და პოზიციები ამ აქტივზე.
                </p>
                <div style="display: flex; gap: 10px;">
                    <span style="background-color: #21262d; color: #8b949e; padding: 4px 10px; border-radius: 12px; font-size: 12px;">📊 Wall Street Consensus: N/A</span>
                    <span style="background-color: #21262d; color: #8b949e; padding: 4px 10px; border-radius: 12px; font-size: 12px;">💬 Social Volume: Low</span>
                    <span style="background-color: #21262d; color: #8b949e; padding: 4px 10px; border-radius: 12px; font-size: 12px;">📈 Value Investor Sentiment: Neutral</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

# ----------------- ჩანართი 4: დღიურის არქივი -----------------
with tab_journal:
    st.subheader("📓 საინვესტიციო თეზისების მართვის პანელი")
    with st.form("journal_v4"):
        j_ticker = st.text_input("🎫 აქციის სიმბოლო:").upper()
        j_confidence = st.slider("🎯 Confidence Score (1-6):", 1, 6, 3)
        j_notes = st.text_area("📝 ჩაწერე შენი ანალიზი, ეჭვები, ან 10-K რეპორტის მიგნებები:")
        if st.form_submit_button("💾 ჩაწერა მყარ ბაზაში"):
            if j_ticker and j_notes:
                try:
                    supabase.table("kitty_journal").upsert({"user_id": FIXED_USER_ID, "ticker": j_ticker, "confidence_score": j_confidence, "notes": j_notes}).execute()
                    st.success("წარმატებით შეინახა!")
                    time.sleep(0.3)
                    st.rerun()
                except Exception as e: st.error(f"შეცდომა: {e}")

    st.markdown("---")
    st.subheader("📋 ჩანაწერების ქრონოლოგიური არქივი:")
    try:
        j_data = supabase.table("kitty_journal").select("*").execute()
        if j_data.data:
            for item in reversed(j_data.data):
                st.markdown(f"""
                    <div class="journal-alert" style="border-left-color: #58a6ff;">
                        <h4 style="margin:0;">🎫 #{item['ticker']} | Score: {item['confidence_score']}/6</h4>
                        <p style="margin-top:5px; color:#c9d1d9;">{item['notes']}</p>
                    </div>
                """, unsafe_allow_html=True)
    except: pass

# გვერდითა მენიუს ვოჩლისტი
st.sidebar.markdown("---")
st.sidebar.subheader("📋 აქტიური Watchlist (Cloud):")
try:
    w_res = supabase.table("watchlist").select("ticker").execute()
    if w_res.data:
        for t in list(set([x['ticker'] for x in w_res.data])):
            st.sidebar.markdown(f"⭐ `{t}`")
except: pass
