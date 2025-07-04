import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
import re

st.set_page_config(page_title="📈 Smart Stock News Impact Screener", layout="centered")
st.title("📈 Smart Nifty Stock News Impact Analyzer")

# Load stock list
@st.cache_data
def load_stocks():
    df = pd.read_csv("nifty_stocks.csv", header=None)
    return df[0].str.strip().str.upper().tolist()

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
                text_upper = text.upper()
                for stock in stock_list:
                    pattern = r"\b" + re.escape(stock) + r"\b"
                    if re.search(pattern, text_upper):
                        all_news.append((stock, text, name))
                        break
        except Exception as e:
            st.error(f"Error fetching from {name}: {e}")
    return list(set(all_news))

def classify_impact(headline):
    headline_lower = headline.lower()
    for category, (keywords, weight) in IMPACT_WEIGHTS.items():
        if any(keyword in headline_lower for keyword in keywords):
            return category, weight
    return "generic", 0.4  # fallback

def analyze_news(news_items):
    results = []
    max_score_seen = 0

    for stock, headline, source in news_items:
        sentiment = TextBlob(headline).sentiment.polarity
        impact_cat, impact_weight = classify_impact(headline)
        raw_score = round(sentiment * 0.3 + impact_weight * 0.7, 4)
        max_score_seen = max(max_score_seen, raw_score)

        results.append({
            "Stock": stock,
            "Headline": headline,
            "Sentiment": round(sentiment, 2),
            "Impact Category": impact_cat,
            "Impact Weight": impact_weight,
            "Raw Score": raw_score,
            "Source": source
        })

    # Normalize raw score to 0–10 scale
    if max_score_seen > 0:
        for r in results:
            r["Impact Score"] = round((r["Raw Score"] / max_score_seen) * 10, 2)
    else:
        for r in results:
            r["Impact Score"] = 0.0

    return results

# Load stock list
stock_list = load_stocks()

if st.button("🔍 Analyze News (Impact & Sentiment)"):
    with st.spinner("Scanning headlines and analyzing..."):
        raw_news = fetch_news(NEWS_SOURCES, stock_list)
        analyzed = analyze_news(raw_news)

        if analyzed:
            df = pd.DataFrame(analyzed).drop(columns=["Raw Score"])
            df_sorted = df.sort_values("Impact Score", ascending=False)
            st.success(f"{len(df_sorted)} impactful news items found.")
            st.dataframe(df_sorted, use_container_width=True)
        else:
            st.warning("No impactful news found.")
