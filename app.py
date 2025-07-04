import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob

# Load Telegram credentials
TELEGRAM_TOKEN = st.secrets["TELEGRAM"]["TOKEN"]
CHAT_ID = st.secrets["TELEGRAM"]["CHAT_ID"]

st.set_page_config(page_title="📈 Smart Stock News Impact Screener", layout="centered")
st.title("📈 Smart Nifty Stock News Impact Analyzer")

# Load stock list
@st.cache_data
def load_stocks():
    df = pd.read_csv("nifty_stocks.csv", header=None)
    return df[0].str.upper().tolist()

# News sources
NEWS_SOURCES = {
    "Moneycontrol": "https://www.moneycontrol.com/news/business/stocks/",
    "Economic Times": "https://economictimes.indiatimes.com/markets/stocks/news",
    "Yahoo Finance": "https://in.finance.yahoo.com/",
    "BSE India": "https://www.bseindia.com/markets/MarketInfo/NoticesCirculars.aspx"
}

# Impact categories with keywords and weights
IMPACT_WEIGHTS = {
    "government": (["govt", "cabinet", "ministry", "policy change", "budget", "duty hike", "duty cut", "export tax", "import duty"], 0.9),
    "contract": (["bags order", "secures contract", "wins order", "award contract", "deal worth"], 0.85),
    "investment": (["FII", "DII", "bulk deal", "block deal", "stake bought", "stake acquired"], 0.8),
    "raw_material": (["input cost", "steel prices", "commodity price drop", "material cost", "raw material fall"], 0.75),
    "merger": (["merger", "acquires", "takeover", "M&A", "strategic acquisition"], 0.8),
    "broker_upgrade": (["buy rating", "target raised", "upgrade", "top pick", "rating upgrade"], 0.7),
    "profit": (["Q1 profit", "net profit rises", "PAT jumps", "quarterly earnings", "beats estimate"], 0.65)
}

def fetch_news(sources, stock_list):
    all_news = []
    for name, url in sources.items():
        try:
            r = requests.get(url, timeout=10)
            soup = BeautifulSoup(r.content, "html.parser")
            for tag in soup.find_all(['h1', 'h2', 'h3', 'p']):
                text = tag.get_text(strip=True)
                if any(stock in text.upper() for stock in stock_list):
                    all_news.append((text, name))
        except Exception as e:
            st.error(f"Error fetching from {name}: {e}")
    return list(set(all_news))

def classify_impact(headline):
    headline_lower = headline.lower()
    for category, (keywords, weight) in IMPACT_WEIGHTS.items():
        if any(keyword in headline_lower for keyword in keywords):
            return category, weight
    return "generic", 0.4  # fallback

def analyze_news(news_items, stock_list):
    results = []
    for headline, source in news_items:
        sentiment = TextBlob(headline).sentiment.polarity
        impact_cat, impact_weight = classify_impact(headline)
        impact_score = round(sentiment * 0.3 + impact_weight * 0.7, 3)
        for stock in stock_list:
            if stock in headline.upper():
                results.append({
                    "Stock": stock,
                    "Headline": headline,
                    "Sentiment": round(sentiment, 2),
                    "Impact Category": impact_cat,
                    "Impact Weight": impact_weight,
                    "Impact Score": impact_score,
                    "Source": source
                })
    return results

def send_to_telegram(top_news):
    if not top_news:
        msg = "📭 No highly impactful stock news today."
    else:
        msg = "*📈 Top 10 Impactful Stocks from News*\n\n"
        for row in top_news[:10]:
            msg += f"🔹 *{row['Stock']}* — Impact Score: `{row['Impact Score']}`\n_{row['Headline']}_\n(Source: {row['Source']})\n\n"

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    res = requests.post(url, data=payload)
    return res.ok

# Load stocks
stock_list = load_stocks()

if st.button("🔍 Analyze News (Impact & Sentiment)"):
    with st.spinner("Scanning headlines and analyzing..."):
        raw_news = fetch_news(NEWS_SOURCES, stock_list)
        analyzed = analyze_news(raw_news, stock_list)
        if analyzed:
            df = pd.DataFrame(analyzed)
            df_sorted = df.sort_values("Impact Score", ascending=False)
            st.success(f"{len(df_sorted)} impactful news items found.")
            st.dataframe(df_sorted, use_container_width=True)
            st.session_state["df_top10"] = df_sorted.head(10).to_dict("records")
        else:
            st.warning("No impactful news found.")

if "df_top10" in st.session_state:
    if st.button("📤 Send Top 10 to Telegram"):
        sent = send_to_telegram(st.session_state["df_top10"])
        if sent:
            st.success("✅ Report sent to Telegram.")
        else:
            st.error("❌ Failed to send message.")
