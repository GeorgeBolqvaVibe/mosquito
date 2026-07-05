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

st.set_page_config(page_title="Kitty Deep-Value Terminal v3", layout="wide", initial_sidebar_state="expanded")

# Bloomberg / TradingView Premium Dark UI Style
st.markdown("""
    <style>
        .stApp { background-color: #0b0e14; color: #c9d1d9; }
        h1, h2, h3, h4 { color: #58a6ff !important; font-family: 'Courier New', monospace; }
        
        /* შეხსენების ბანერი დღიურიდან */
        .journal-alert {
            background-color: #1c1f26;
            border-left: 6px solid #d29922;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }
        
        /* ფინანსური ტერმინალის ბარათები */
        .metric-box {
            background-color: #12161f;
            border: 1px solid #21262d;
            border-radius: 6px;
            padding: 15px;
            text-align: center;
        }
        .metric-box-title { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
        .metric-box-value { font-size: 22px; font-weight: bold; color: #f0f6fc; margin-top: 5px; }
        
        /* შკრელის ეჭვების რადარის ბარათი */
        .skeptic-box {
            background-color: #1f1515;
            border: 1px solid #482323;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .signal-red { color: #f85149 !important; font-weight: bold; }
        .signal-green { color: #2ea44f !important; font-weight: bold; }
        .signal-amber { color: #d29922 !important; font-weight: bold; }
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
st.sidebar.title("🦁 Kitty Terminal v3.0")
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
                                    <h4 style="margin:0; color:#d29922;">⚠️ ჩანაწერი ნაპოვნია შენს პირად დღიურში!</h4>
                                    <p style="margin-top:8px; font-size:14px; color:#f0f6fc;"><b>შენი თეზისი:</b> {latest_note['notes']}</p>
                                    <small style="color:#8b949e;">🎯 Confidence Score: {latest_note['confidence_score']}/6</small>
                                </div>
                            """, unsafe_allow_html=True)
                    except: pass

                    # ჰედერი და ვოჩლისტი
                    c_h, c_b = st.columns([4, 1])
                    with c_h:
                        st.header(f"🏢 {info.get('longName')} ({ticker})")
                        st.caption(f"📍 {info.get('sector')} | {info.get('industry')} | Employees: {info.get('fullTimeEmployees', 'N/A')}")
                    with c_b:
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
                    with st.markdown("<div class='skeptic-box'>", unsafe_allow_html=True):
                        sk_c1, sk_c2, sk_c3 = st.columns(3)
                        
                        # ფილტრი 1: თანამშრომლების კრიტიკული რაოდენობა
                        emp = info.get('fullTimeEmployees', 0)
                        if emp == 0 or emp is None:
                            sk_c1.markdown(f"👥 **თანამშრომლები:** <span class='signal-red'>არ იძებნება (საეჭვოა)</span>", unsafe_allow_html=True)
                        elif emp < 10:
                            sk_c1.markdown(f"👥 **თანამშრომლები:** <span class='signal-red'>{emp} კაცი (ცარიელი 'კონტორა')</span>", unsafe_allow_html=True)
                        else:
                            sk_c1.markdown(f"👥 **თანამშრომლები:** <span class='signal-green'>{emp} თანამშრომელი</span>", unsafe_allow_html=True)
                        # ფილტრი 2: პროდუქტი და რეალური შემოსავალი
                        rev = info.get('totalRevenue', 0)
                        if rev == 0 or rev is None:
                            sk_c2.markdown(f"💰 **რეალური გაყიდვები:** <span class='signal-red'>$0 (პროდუქტი არ აქვთ)</span>", unsafe_allow_html=True)
                        else:
                            sk_c2.markdown(f"💰 **რეალური გაყიდვები:** <span class='signal-green'>{fmt_m(rev)}</span>", unsafe_allow_html=True)
                            
                        # ფილტრი 3: გაკოტრების და დილუაციის რისკი (Altman Z-Score)
                        z_val = calculate_z_score(info)
                        if z_val == 0:
                            sk_c3.markdown(f"🛡️ **Altman Z-Score:** <span class='signal-amber'>N/A (მონაცემები არასრულია)</span>", unsafe_allow_html=True)
                        elif z_val < 1.81:
                            sk_c3.markdown(f"🛡️ **Altman Z-Score:** <span class='signal-red'>{z_val} (გაკოტრების/დილუაციის რისკი)</span>", unsafe_allow_html=True)
                        else:
                            sk_c3.markdown(f"🛡️ **Altman Z-Score:** <span class='signal-green'>{z_val} (სტაბილურია)</span>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                    # ძირითადი ფინანსური მეტრიკები
                    st.markdown("### 📊 ძირითადი ფინანსური კოეფიციენტები")
                    m_c1, m_c2, m_c3, m_c4 = st.columns(4)
                    m_c1.markdown(f"<div class='metric-box'><div class='metric-box-title'>Price-to-Book (P/B)</div><div class='metric-box-value'>{info.get('priceToBook', 'N/A')}</div></div>", unsafe_allow_html=True)
                    m_c2.markdown(f"<div class='metric-box'><div class='metric-box-title'>Price-to-Sales (P/S)</div><div class='metric-box-value'>{info.get('priceToSalesTrailing12Months', 'N/A')}</div></div>", unsafe_allow_html=True)
                    m_c3.markdown(f"<div class='metric-box'><div class='metric-box-title'>Total Cash</div><div class='metric-box-value'>{fmt_m(info.get('totalCash'))}</div></div>", unsafe_allow_html=True)
                    m_c4.markdown(f"<div class='metric-box'><div class='metric-box-title'>Short % of Float</div><div class='metric-box-value'>{fmt_pct(info.get('shortPercentOfFloat'))}</div></div>", unsafe_allow_html=True)

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
                # ვასუფთავებთ ცხრილს
                holders.columns = ["ინსტიტუტი", "აქციები", "თარიღი", "წილი %", "ღირებულება"]
                st.dataframe(holders, width="stretch")
            else: st.info("მონაცემები მსხვილი ინვესტორების შესახებ ვერ მოიძებნა.")
        except: st.error("ინფორმაციის წაკითხვა ვერ მოხერხდა.")

# ----------------- ჩანართი 4: დღიურის არქივი -----------------
with tab_journal:
    st.subheader("📓 საინვესტიციო თეზისების მართვის პანელი")
    with st.form("journal_v3"):
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
