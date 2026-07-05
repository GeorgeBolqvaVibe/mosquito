import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import time
import threading
from datetime import datetime
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

# პრემიუმ მუქი ფინანსური ტერმინალის UI კონფიგურაცია
st.set_page_config(page_title="Deep-Value Pro Terminal", layout="wide", initial_sidebar_state="expanded")

# Custom CSS Bloomberg/TradingView სტილის ვიზუალისთვის
st.markdown("""
    <style>
        /* მთავარი ფონი და ტექსტი */
        .stApp { background-color: #0d1117; color: #c9d1d9; }
        h1, h2, h3 { color: #58a6ff !important; font-family: 'Courier New', monospace; }
        
        /* ფინანსური მეტრიკების ბარათები */
        .metric-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .metric-title { font-size: 12px; color: #8b949e; text-transform: uppercase; margin-bottom: 5px; }
        .metric-value { font-size: 20px; font-weight: bold; color: #f0f6fc; }
        
        /* სიგნალების ფერები */
        .signal-safe { color: #2ea44f !important; }
        .signal-warning { color: #d29922 !important; }
        .signal-danger { color: #f85149 !important; }
        
        /* საინვესტიციო დღიურის ბარათები */
        .thesis-card {
            background-color: #1f242c;
            border-left: 4px solid #58a6ff;
            padding: 15px;
            margin-bottom: 12px;
            border-radius: 0 8px 8px 0;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. დამხმარე ფინანსური ფუნქციები ---
def fmt_m(val):
    if val is None or isinstance(val, str) or pd.isna(val): return 'N/A'
    return f"${val / 1_000_000:.2f}M"

def fmt_pct(val):
    if val is None or isinstance(val, str) or pd.isna(val): return 'N/A'
    return f"{val * 100:.2f}%"

def get_z_score_html(info):
    try:
        working_capital = info.get('currentAssets', 0) - info.get('currentLiabilities', 0)
        total_assets = info.get('totalAssets', 1)
        retained_earnings = info.get('retainedEarnings', 0)
        ebit = info.get('ebitda', 0)
        market_cap = info.get('marketCap', 0)
        total_liabilities = info.get('totalDebt', 1)
        revenue = info.get('totalRevenue', 0)
        if total_assets <= 1: return "<span class='signal-warning'>N/A</span>"
        X1 = working_capital / total_assets
        X2 = retained_earnings / total_assets
        X3 = ebit / total_assets
        X4 = market_cap / total_liabilities
        X5 = revenue / total_assets
        score = round(1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 0.99*X5, 2)
        
        if score > 2.99: return f"<span class='signal-safe'>{score} (Safe)</span>"
        elif score < 1.81: return f"<span class='signal-danger'>{score} (Distress)</span>"
        else: return f"<span class='signal-warning'>{score} (Grey Zone)</span>"
    except: return "<span class='signal-warning'>N/A</span>"

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

# --- 3. 🤖 ფონური ავტომატური ბოტი ---
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
                        for single_news in reversed(news[:3]):
                            news_id = single_news.get('id')
                            content = single_news.get('content', {})
                            title = content.get('title')
                            link = content.get('clickThroughUrl', {}).get('url') or content.get('canonicalUrl', {}).get('url')
                            publisher = content.get('provider', {}).get('displayName', 'Yahoo Finance')

                            if link and news_id and not is_already_sent(news_id):
                                send_telegram_message(f"📰 *ახალი სიახლე:* #{ticker}\n\n📌 {title}\n📰 წყარო: {publisher}\n🔗 [წაიკითხე ორიგინალი]({link})")
                                mark_as_sent(news_id)
                                time.sleep(1)
        except: pass
        time.sleep(1800)

@st.cache_resource
def start_global_monitor():
    t = threading.Thread(target=background_monitor_loop, daemon=True)
    t.start()
    return True

start_global_monitor()

# --- 4. 🖥️ ტერმინალის ინტერფეისი ---
st.sidebar.title("🦁 Kitty Terminal v2.0")
st.sidebar.markdown("---")

tab_analyzer, tab_insiders, tab_radar, tab_journal = st.tabs([
    "🕵️‍♂️ Stock Analyzer & Moat Engine", 
    "💼 Insider Activity Tracker",
    "🎯 Deep Value Radar Grid",
    "📓 Asymmetric Thesis Journal"
])

# ----------------- ჩანართი 1: ანალიზატორი & MOAT ENGINE -----------------
with tab_analyzer:
    ticker = st.sidebar.text_input("🚀 🎫 შეიყვანე ტიკერი კვლევისთვის:", "POET").upper()
    if ticker:
        with st.spinner(f"მიმდინარეობს მონაცემთა ბირთვის ჩატვირთვა: {ticker}..."):
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                if info and 'longName' in info:
                    c_title, c_add = st.columns([4, 1])
                    with c_title:
                        st.subheader(f"🏢 {info.get('longName')} ({ticker})")
                        st.caption(f"📍 {info.get('sector')} | {info.get('industry')} | {info.get('financialCurrency', 'USD')}")
                    with c_add:
                        st.write("")
                        if st.button(f"➕ Watchlist-ში ჩამატება", use_container_width=True):
                            try:
                                supabase.table("watchlist").insert({"user_id": FIXED_USER_ID, "ticker": ticker}).execute()
                                send_telegram_message(f"📌 *რადარზე დაემატა ახალი ტიკერი:* #{ticker}")
                                st.success("დაემატა!")
                                time.sleep(0.5)
                                st.rerun()
                            except: st.info("უკვე სიაშია.")

                    # პრემიუმ მალსახმობები
                    st.markdown("##### 🔍 Deep Research Shortcuts:")
                    sh_c = st.columns(5)
                    sh_c[0].link_button("📄 SEC Edgar Filings", f"https://www.sec.gov/edgar/browse/?CIK={ticker}", use_container_width=True)
                    sh_c[1].link_button("💼 OpenInsider Orders", f"https://openinsider.com/search?q={ticker}", use_container_width=True)
                    sh_c[2].link_button("📈 TradingView Chart", f"https://www.tradingview.com/symbols/{ticker}/", use_container_width=True)
                    sh_c[3].link_button("🦁 Seeking Alpha Premium", f"https://seekingalpha.com/symbol/{ticker}", use_container_width=True)
                    sh_c[4].link_button("🐦 X Real-time Stream", f"https://x.com/search?q=%24{ticker}", use_container_width=True)

                    st.markdown("---")
                    
                    # 🎨 პრემიუმ ფინანსური ბარათების ბადე (Metrics Grid)
                    row1_1, row1_2, row1_3, row1_4 = st.columns(4)
                    with row1_1:
                        st.markdown(f"<div class='metric-card'><div class='metric-title'>Price to Book (P/B)</div><div class='metric-value'>{info.get('priceToBook', 'N/A')}</div></div>", unsafe_allow_html=True)
                    with row1_2:
                        st.markdown(f"<div class='metric-card'><div class='metric-title'>Price to Sales (P/S)</div><div class='metric-value'>{info.get('priceToSalesTrailing12Months', 'N/A')}</div></div>", unsafe_allow_html=True)
                    with row1_3:
                        z_score_html = get_z_score_html(info)
                        st.markdown(f"<div class='metric-card'><div class='metric-title'>Altman Z-Score</div><div class='metric-value'>{z_score_html}</div></div>", unsafe_allow_html=True)
                    with row1_4:
                        st.markdown(f"<div class='metric-card'><div class='metric-title'>Current Ratio</div><div class='metric-value'>{info.get('currentRatio', 'N/A')}</div></div>", unsafe_allow_html=True)

                    st.write("")
                    row2_1, row2_2, row2_3, row2_4 = st.columns(4)
                    with row2_1:
                        st.markdown(f"<div class='metric-card'><div class='metric-title'>Total Cash</div><div class='metric-value'>{fmt_m(info.get('totalCash'))}</div></div>", unsafe_allow_html=True)
                    with row2_2:
                        st.markdown(f"<div class='metric-card'><div class='metric-title'>Total Debt</div><div class='metric-value'>{fmt_m(info.get('totalDebt'))}</div></div>", unsafe_allow_html=True)
                    with row2_2:
                        st.markdown(f"<div class='metric-card'><div class='metric-title'>Short % of Float</div><div class='metric-value'>{fmt_pct(info.get('shortPercentOfFloat'))}</div></div>", unsafe_allow_html=True)
                    with row2_4:
                        st.markdown(f"<div class='metric-card'><div class='metric-title'>Short Ratio (Days)</div><div class='metric-value'>{info.get('shortRatio', 'N/A')}</div></div>", unsafe_allow_html=True)

                    # ჩარტები
                    st.markdown("---")
                    st.markdown("### 📊 Market Valuation Vector (1 Year)")
                    hist = stock.history(period="1y")
                    if not hist.empty:
                        st.line_chart(hist['Close'], width="stretch")
            except Exception as e: st.error(f"შეცდომა: {e}")

# ----------------- ჩანართი 2: INSIDER ACTIVITY TRACKER -----------------
with tab_insiders:
    st.subheader(f"💼 რეალური ინსაიდერული ტრანზაქციები: #{ticker}")
    st.caption("მონაცემები ამოღებულია პირდაპირ SEC Filings-ის ოფიციალური არხებიდან Yahoo Finance-ის მეშვეობით.")
    
    if ticker:
        try:
            insider_data = yf.Ticker(ticker).insider_transactions
            if insider_data is not None and not insider_data.empty:
                # ვალამაზებთ ცხრილს საჩვენებლად
                clean_insider = insider_data[['Date', 'Insider', 'Position', 'Transaction', 'Shares', 'Value']].copy()
                st.dataframe(clean_insider.style.set_properties(**{'background-color': '#161b22', 'color': '#c9d1d9'}), width="stretch")
            else:
                st.info(f"ℹ️ #{ticker}-ისთვის ბოლო პერიოდში ოფიციალური ინსაიდერული გარიგებები ბაზაში ვერ მოიძებნა.")
        except:
            st.error("ინსაიდერული მონაცემების წაკითხვის შეცდომა.")

# ----------------- ჩანართი 3: DEEP VALUE RADAR GRID -----------------
with tab_radar:
    st.subheader("🎯 Deep Value სკანირების გლობალური ბადე")
    default_universe = ["POET", "META", "GME", "BABA", "INTC", "WBD"]
    universe_input = st.text_area("🎫 საძიებო სამყარო (TICKERS):", value=", ".join(default_universe))
    tickers_to_scan = [t.strip().upper() for t in universe_input.split(",") if t.strip()]
    
    if st.button("🔍 გლობალური რადარის გაშვება", use_container_width=True):
        radar_results = []
        for tok in tickers_to_scan:
            try:
                inf = yf.Ticker(tok).info
                pb = inf.get('priceToBook', 0)
                book_to_price = (1 / pb) if (pb and pb > 0) else 0
                radar_results.append({
                    "🎫 ტიკერი": tok,
                    "🏢 კომპანია": inf.get('longName'),
                    "📈 Book / Price (B/P)": book_to_price,
                    "💰 Total Cash": fmt_m(inf.get('totalCash')),
                    "🦊 Short Float %": fmt_pct(inf.get('shortPercentOfFloat'))
                })
            except: pass
        if radar_results:
            st.dataframe(pd.DataFrame(radar_results).sort_values(by="📈 Book / Price (B/P)", ascending=False), width="stretch")

# ----------------- ჩანართი 4: ASYMMETRIC THESIS JOURNAL (ინტეგრირებული არქივი) -----------------
with tab_journal:
    st.subheader("📓 საინვესტიციო ჩანაწერები და ასიმეტრიული თეზისების არქივი")
    
    with st.form("journal_premium_form"):
        form_c1, form_c2 = st.columns([1, 1])
        with form_c1:
            j_ticker = st.text_input("🎫 აქციის სიმბოლო (მაგ. POET):").upper()
        with form_c2:
            j_confidence = st.slider("🎯 Confidence Score (1-6):", 1, 6, 3)
        j_notes = st.text_area("📝 შენი ანალიტიკური ჩანაწერები და კატალიზატორები:")
        
        if st.form_submit_button("💾 ჩანაწერის მყარ არქივში შენახვა", use_container_width=True):
            if j_ticker and j_notes:
                try:
                    supabase.table("kitty_journal").upsert({
                        "user_id": FIXED_USER_ID, "ticker": j_ticker,
                        "confidence_score": j_confidence, "notes": j_notes
                    }).execute()
                    st.success("🎉 თეზისი წარმატებით ჩაიწერა მყარ არქივში!")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e: st.error(f"შეცდომა: {e}")
            else: st.error("გთხოვთ შეავსოთ ყველა ველი.")

    st.markdown("---")
    st.subheader("📋 ინტერაქტიული არქივის ლენტი (Timeline Index):")
    
    try:
        journal_res = supabase.table("kitty_journal").select("*").eq("user_id", FIXED_USER_ID).execute()
        if journal_res.data:
            # მონაცემებს ვაჩვენებთ ლამაზი ბარათების სახით დროის მიხედვით
            sorted_data = sorted(journal_res.data, key=lambda x: x.get('created_at', ''), reverse=True)
            for idx, item in enumerate(sorted_data):
                dt_obj = item.get('created_at', 'N/A')
                if dt_obj != 'N/A':
                    dt_obj = dt_obj.split("T")[0] # ვიღებთ მხოლოდ თარიღს
                
                # HTML ბარათის გენერაცია
                st.markdown(f"""
                    <div class='thesis-card'>
                        <h4 style='margin:0; color:#58a6ff;'>🎫 #{item['ticker']} | 🎯 Confidence: {item['confidence_score']}/6</h4>
                        <small style='color:#8b949e;'>📅 თარიღი: {dt_obj}</small>
                        <p style='margin-top:10px; color:#c9d1d9; font-size:14px;'>{item['notes']}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("ℹ️ შენი საინვესტიციო არქივი ჯერ ცარიელია.")
    except Exception as e:
        st.error(f"არქივის წაკითხვის შეცდომა. დარწმუნდი, რომ RLS გათიშულია SQL Editor-ში: {e}")

# ვოჩლისტი საიდბარში (ულამაზესი, მყარი დიზაინით)
st.sidebar.markdown("---")
st.sidebar.subheader("📋 აქტიური Watchlist (Cloud):")
try:
    watch_res = supabase.table("watchlist").select("ticker").execute()
    if watch_res.data:
        unique_tickers = list(set([item['ticker'] for item in watch_res.data]))
        for t in unique_tickers: 
            st.sidebar.markdown(f"⭐ `{t}`")
except: pass
