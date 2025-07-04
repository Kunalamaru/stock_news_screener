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

# Keywords and weights
IMPACT_WEIGHTS = {
    "government": (["govt", "cabinet", "ministry", "policy change", "budget", "duty hike", "duty cut", "export tax", "import duty"], 0.9),
    "contract": (["bags order", "secures contract", "wins order", "award contract", "deal worth"], 0.85),
    "investment": (["FII", "DII", "bulk deal", "block deal", "stake bought", "stake acquired"], 0.8),
    "raw_material": (["input cost", "steel prices", "commodity price drop", "material cost", "raw material fall"], 0.75),
    "merger": (["merger", "acquires", "takeover", "M&A", "strategic acquisition"], 0.8),
    "broker_upgrade": (["buy rating", "target raised", "upgrade", "top pick", "rating upgrade"], 0.7),
    "profit": (["Q1 profit", "net profit rises", "PAT jumps", "quarterly earnings", "beats estimate"], 0.65)
}

# News fetching
def fetch_news(sources, stock_list):
    all_news = []
    for name, url in sources.items():
        try:
            r = requests.get(url, timeout=10)
            soup = BeautifulSoup(r.content, "html.parser")
            for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'a']):
                text = tag.get_text(strip=True)
                text_upper = text.upper()
                for stock in stock_list:
                    pattern = r"\b" + re.escape(stock) + r"\b"
                    if re.search(pattern, text_upper):
                        link = tag.get("href", "")
                        if not link.startswith("http"):
                            link = url  # fallback to site URL
                        all_news.append((stock, text, name, link))
                        break
        except Exception as e:
            st.error(f"Error fetching from {name}: {e}")
    return list(set(all_news))

# Classify and score
def classify_impact(headline):
    headline_lower = headline.lower()
    for category, (keywords, weight) in IMPACT_WEIGHTS.items():
        if any(keyword in headline_lower for keyword in keywords):
            return category, weight
    return "generic", 0.4

# Analyze with explanation
def analyze_news(news_items):
    results = []
    max_score = 0

    for stock, headline, source, link in news_items:
        sentiment = TextBlob(headline).sentiment.polarity
        impact_cat, impact_weight = classify_impact(headline)
        raw_score = round(0.3 * sentiment + 0.7 * impact_weight, 4)
        max_score = max(max_score, raw_score)

        summary = TextBlob(headline).noun_phrases[:3]
        summary_text = ", ".join(summary) if summary else headline[:100] + "..."

        results.append({
            "Stock": stock,
            "Headline": headline,
            "Sentiment": round(sentiment, 2),
            "Impact Category": impact_cat,
            "Impact Weight": impact_weight,
            "Raw Score": raw_score,
            "Source": source,
            "Summary": summary_text,
            "Link": link
        })

    # Normalize scores
    for r in results:
        r["Impact Score"] = round((r["Raw Score"] / max_score) * 10, 2) if max_score > 0 else 0.0

    return sorted(results, key=lambda x: x["Impact Score"], reverse=True)

# Load stocks
stock_list = load_stocks()

if st.button("🔍 Analyze News"):
    with st.spinner("Scanning headlines and analyzing..."):
        raw_news = fetch_news(NEWS_SOURCES, stock_list)
        analyzed = analyze_news(raw_news)

        if analyzed:
            st.success(f"{len(analyzed)} impactful news items found.")
            for row in analyzed:
                with st.expander(f"{row['Stock']} | Score: {row['Impact Score']}/10"):
                    st.markdown(f"**📰 Headline**: {row['Headline']}")
                    st.markdown(f"**📌 Summary**: {row['Summary']}")
                    st.markdown(f"**📊 Sentiment**: `{row['Sentiment']}`")
                    st.markdown(f"**📂 Impact Category**: `{row['Impact Category']}`")
                    st.markdown(f"**📈 Impact Weight**: `{row['Impact Weight']}`")
                    st.markdown(f"**🧮 Score Formula**: `0.3 × Sentiment + 0.7 × Impact Weight = {row['Raw Score']}`")
                    st.markdown(f"**🔗 [Read Full Article]({row['Link']})**")
        else:
            st.warning("No impactful news found.")
