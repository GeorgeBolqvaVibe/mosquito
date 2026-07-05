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

st.set_page_config(page_title="Deep-Value Pro", layout="wide")

# --- 2. დამხმარე ფინანსური ფუნქციები ---
def fmt_m(val):
    if val is None or isinstance(val, str) or pd.isna(val): return 'N/A'
    return f"${val / 1_000_000:.2f}M"

def fmt_pct(val):
    if val is None or isinstance(val, str) or pd.isna(val): return 'N/A'
    return f"{val * 100:.2f}%"

def calculate_crude_z_score(info):
    try:
        working_capital = info.get('currentAssets', 0) - info.get('currentLiabilities', 0)
        total_assets = info.get('totalAssets', 1)
        retained_earnings = info.get('retainedEarnings', 0)
        ebit = info.get('ebitda', 0)
        market_cap = info.get('marketCap', 0)
        total_liabilities = info.get('totalDebt', 1)
        revenue = info.get('totalRevenue', 0)
        if total_assets <= 1: return "N/A"
        X1 = working_capital / total_assets
        X2 = retained_earnings / total_assets
        X3 = ebit / total_assets
        X4 = market_cap / total_liabilities
        X5 = revenue / total_assets
        return round(1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 0.99*X5, 2)
    except: return "N/A"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
    except: pass

def is_already_sent(alert_id):
    import os
    if not os.path.exists(SENT_ALERTS_FILE): return False
    with open(SENT_ALERTS_FILE, "r") as f:
        return alert_id in [line.strip() for line in f.readlines()]

def mark_as_sent(alert_id):
    with open(SENT_ALERTS_FILE, "a") as f: f.write(f"{alert_id}\n")

# --- 3. 🤖 100%-ით ავტონომიური ფონური ბოტი (სერვერული რეჟიმი) ---
def background_monitor_loop():
    while True:
        try:
            # სუფთა მოთხოვნა ბაზიდან ყოველგვარი იუზერ კონტექსტის გარეშე
            res = supabase.table("watchlist").select("ticker").execute()
            if res.data:
                watchlist = list(set([item['ticker'] for item in res.data]))
                for ticker in watchlist:
                    stock = yf.Ticker(ticker)
                    news = stock.news
                    if news:
                        # ვამოწმებთ ბოლო 5 სიახლეს
                        for single_news in reversed(news[:5]):
                            news_id = single_news.get('id')
                            content = single_news.get('content', {})
                            title = content.get('title')
                            link = content.get('clickThroughUrl', {}).get('url') or content.get('canonicalUrl', {}).get('url')
                            publisher = content.get('provider', {}).get('displayName', 'Yahoo Finance')

                            if link and news_id and not is_already_sent(news_id):
                                send_telegram_message(f"📰 *ახალი სიახლე:* #{ticker}\n\n📌 {title}\n📰 წყარო: {publisher}\n🔗 [წაიკითხე ორიგინალი]({link})")
                                mark_as_sent(news_id)
                                time.sleep(1)
        except:
            pass
        time.sleep(1800) # ყოველ 30 წუთში ერთხელ სრულიად ავტომატურად

@st.cache_resource
def start_global_monitor():
    t = threading.Thread(target=background_monitor_loop, daemon=True)
    t.start()
    return True

# ვრთავთ ფონურ ძრავს სერვერზე
start_global_monitor()

# --- 4. 🖥️ ვიზუალური ინტერფეისი ---
st.sidebar.title("🦁 Kitty's Command Center")
st.sidebar.success("⚡ ავტომატური რადარი აქტიურია 24/7-ზე")

tab_analyzer, tab_sectors, tab_radar, tab_journal = st.tabs([
    "🕵️‍♂️ Individual Stock Analyzer", 
    "📊 Market Sector Rotation", 
    "🎯 Deep Value Radar",
    "📓 Kitty's Journal & Portfolio"
])

# ----------------- ჩანართი 1: ანალიზატორი -----------------
with tab_analyzer:
    ticker = st.sidebar.text_input("🚀 ჩაწერე სტოკის სიმბოლო:", "POET").upper()
    if ticker:
        with st.spinner(f"მიმდინარეობს ანალიზი: {ticker}..."):
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                if info and 'longName' in info:
                    col_name, col_btn = st.columns([4, 1])
                    with col_name:
                        st.header(f"🏢 {info.get('longName')}")
                        st.subheader(f"📍 სექტორი: {info.get('sector')} | ინდუსტრია: {info.get('industry')}")
                    with col_btn:
                        st.write("")
                        if st.button(f"➕ Add {ticker} to Watchlist"):
                            try:
                                supabase.table("watchlist").insert({"user_id": FIXED_USER_ID, "ticker": ticker}).execute()
                                send_telegram_message(f"📌 *აქცია ჩაემატა რადარზე:* #{ticker}\n🤖 ფონური მონიტორინგი დაწყებულია.")
                                st.success(f"{ticker} დაემატა ბაზაში!")
                                time.sleep(0.5)
                                st.rerun()
                            except: 
                                st.info(f"{ticker} უკვე სათვალთვალო სიაშია.")

                    st.markdown("#### 🔗 გარე კვლევის მალსახმობები:")
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.link_button("📄 SEC Edgar", f"https://www.sec.gov/edgar/browse/?CIK={ticker}", use_container_width=True)
                    c2.link_button("💼 OpenInsider", f"https://openinsider.com/search?q={ticker}", use_container_width=True)
                    c3.link_button("📈 TradingView", f"https://www.tradingview.com/symbols/{ticker}/", use_container_width=True)
                    c4.link_button("🦁 Seeking Alpha", f"https://seekingalpha.com/symbol/{ticker}", use_container_width=True)
                    c5.link_button("🐦 X/Twitter", f"https://x.com/search?q=%24{ticker}", use_container_width=True)

                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Price-to-Book (P/B)", f"{info.get('priceToBook', 'N/A')}")
                    col1.metric("Price-to-Sales (P/S)", f"{info.get('priceToSalesTrailing12Months', 'N/A'):,.2f}")
                    col1.metric("Altman Z-Score", f"{calculate_crude_z_score(info)}")
                    
                    col2.metric("Current Ratio", f"{info.get('currentRatio', 'N/A')}")
                    col2.metric("ნაღდი ფული (Cash)", fmt_m(info.get('totalCash')))
                    col2.metric("მთლიანი ვალი (Debt)", fmt_m(info.get('totalDebt')))
                    
                    col3.metric("Short % of Float", fmt_pct(info.get('shortPercentOfFloat')))
                    col3.metric("Short Ratio (Days)", f"{info.get('shortRatio', 'N/A')}")
                    col3.metric("ინსტიტუციები", fmt_pct(info.get('heldPercentInstitutions')))

                    st.markdown("---")
                    st.markdown("### 📈 ჩარტები (1 წელი)")
                    hist = stock.history(period="1y")
                    if not hist.empty:
                        st.line_chart(hist['Close'], width="stretch")
                        st.bar_chart(hist['Volume'], width="stretch")
            except Exception as e: st.error(f"შეცდომა: {e}")

# ----------------- ჩანართი 2: სექტორები -----------------
with tab_sectors:
    st.header("📊 ამერიკული ბაზრის სექტორული როტაცია")
    sectors_dict = {"Technology": "XLK", "Financials": "XLF", "Energy": "XLE", "Healthcare": "XLV"}
    if st.button("🔄 სექტორების სკანირება"):
        sector_data = []
        for name, etf in sectors_dict.items():
            try:
                s_hist = yf.Ticker(etf).history(period="3mo")
                perf = ((s_hist['Close'].iloc[-1] - s_hist['Close'].iloc[0]) / s_hist['Close'].iloc[0]) * 100
                sector_data.append({"სექტორი": name, "ბოლო 3 თვის ტრენდი": perf})
            except: pass
        if sector_data:
            df = pd.DataFrame(sector_data).sort_values(by="ბოლო 3 თვის ტრენდი", ascending=False)
            st.dataframe(df, width="stretch")

# ----------------- ჩანართი 3: რადარი -----------------
with tab_radar:
    st.header("🎯 Deep Value რადარი (Inverted Engine)")
    default_universe = ["POET", "META", "GME", "BABA"]
    universe_input = st.text_area("🎫 საძიებო აქციები:", value=", ".join(default_universe))
    tickers_to_scan = [t.strip().upper() for t in universe_input.split(",") if t.strip()]
    
    if st.button("🔍 რადარის გაშვება"):
        radar_results = []
        for tok in tickers_to_scan:
            try:
                inf = yf.Ticker(tok).info
                pb = inf.get('priceToBook', 0)
                book_to_price = (1 / pb) if (pb and pb > 0) else 0
                radar_results.append({
                    "🎫 ტიკერი": tok, "🏢 კომპანია": inf.get('longName'),
                    "📈 Book / Price (B/P)": book_to_price, "🛡️ Altman Z-Score": calculate_crude_z_score(inf)
                })
            except: pass
        if radar_results:
            df_radar = pd.DataFrame(radar_results).sort_values(by="📈 Book / Price (B/P)", ascending=False)
            st.dataframe(df_radar, width="stretch")

# ----------------- ჩანართი 4: KITTY'S JOURNAL -----------------
with tab_journal:
    st.header("📓 პირადი საინვესტიციო დღიური და პორტფოლიო")
    with st.form("journal_form"):
        j_ticker = st.text_input("🎫 აქციის ტიკერი (მაგ. GME):").upper()
        j_confidence = st.slider("🎯 Confidence Score:", 1, 6, 3)
        j_notes = st.text_area("📝 შენი ანალიტიკური ჩანაწერები (Notes):")
        if st.form_submit_button("💾 ჩანაწერის ბაზაში შენახვა"):
            if j_ticker:
                try:
                    supabase.table("kitty_journal").upsert({
                        "user_id": FIXED_USER_ID, "ticker": j_ticker,
                        "confidence_score": j_confidence, "notes": j_notes
                    }).execute()
                    st.success(f"📓 თეზისი #{j_ticker}-ზე შენახულია!")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e: st.error(f"შეცდომა: {e}")

    st.markdown("---")
    st.subheader("📋 შენი მიმდინარე ჩანაწერები:")
    try:
        journal_res = supabase.table("kitty_journal").select("*").eq("user_id", FIXED_USER_ID).execute()
        if journal_res.data:
            st.dataframe(pd.DataFrame(journal_res.data)[["ticker", "confidence_score", "notes", "created_at"]], width="stretch")
    except: pass

# ვოჩლისტი საიდბარში (სრულიად მყარი)
st.sidebar.markdown("---")
st.sidebar.subheader("📋 შენი Watchlist (Cloud):")
try:
    watch_res = supabase.table("watchlist").select("ticker").execute()
    if watch_res.data:
        unique_tickers = list(set([item['ticker'] for item in watch_res.data]))
        for t in unique_tickers: 
            st.sidebar.text(f"• {t}")
except: pass
