import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
import re
from collections import defaultdict
import yfinance as yf
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="📈 Smart Stock News Analyzer", layout="wide")

# Initialize session state to handle view switching
if 'view' not in st.session_state:
    st.session_state.view = 'news'

@st.cache_data
def load_stocks():
    df = pd.read_csv("nifty_stocks.csv", header=None)
    return df[0].str.strip().str.upper().tolist()

NEWS_SOURCES = {
    "Moneycontrol": "https://www.moneycontrol.com/news/business/stocks/",
    "Economic Times": "https://economictimes.indiatimes.com/markets/stocks/news",
    "Yahoo Finance": "https://in.finance.yahoo.com/",
    "BSE India": "https://www.bseindia.com/markets/MarketInfo/NoticesCirculars.aspx"
}

IMPACT_WEIGHTS = {
    "government": ("govt cabinet ministry policy change budget duty hike duty cut export tax import duty".split(), 0.9),
    "contract": ("bags order secures contract wins order award contract deal worth".split(), 0.85),
    "investment": ("FII DII bulk deal block deal stake bought stake acquired".split(), 0.8),
    "raw_material": ("input cost steel prices commodity price drop material cost raw material fall".split(), 0.75),
    "merger": ("merger acquires takeover M&A strategic acquisition".split(), 0.8),
    "broker_upgrade": ("buy rating target raised upgrade top pick rating upgrade".split(), 0.7),
    "profit": ("Q1 profit net profit rises PAT jumps quarterly earnings beats estimate".split(), 0.65)
}

def fetch_news(sources, stock_list):
    raw_news = []
    seen_headlines = defaultdict(list)
    for name, url in sources.items():
        try:
            r = requests.get(url, timeout=10)
            soup = BeautifulSoup(r.content, "html.parser")
            for tag in soup.find_all(['a', 'h1', 'h2', 'h3', 'p']):
                text = tag.get_text(strip=True)
                text_upper = text.upper()
                href = tag.get("href", "")
                full_link = href if href.startswith("http") else url
                for stock in stock_list:
                    pattern = r"\b" + re.escape(stock) + r"\b"
                    if re.search(pattern, text_upper):
                        seen_headlines[text].append((stock, name, full_link))
                        break
        except Exception as e:
            st.error(f"Error fetching from {name}: {e}")

    consolidated_news = []
    for headline, entries in seen_headlines.items():
        stock_sources = set(entry[1] for entry in entries)
        stock = entries[0][0]
        source = ", ".join(stock_sources)
        link = entries[0][2]
        consolidated_news.append((stock, headline, source, link, len(stock_sources)))
    return consolidated_news

def classify_impact(headline):
    headline_lower = headline.lower()
    for category, (keywords, weight) in IMPACT_WEIGHTS.items():
        if any(keyword in headline_lower for keyword in keywords):
            return category, weight
    return "generic", 0.4

def summarize_text(text):
    if '.' in text:
        return text.split('.')[0] + '.'
    else:
        return ' '.join(text.split()[:20]) + '...'

def analyze_news(news_items):
    results = []
    max_score_seen = 0

    for stock, headline, source, link, source_count in news_items:
        sentiment = TextBlob(headline).sentiment.polarity
        impact_cat, impact_weight = classify_impact(headline)
        adjusted_weight = min(impact_weight + (0.05 * (source_count - 1)), 1.0)
        raw_score = round(sentiment * 0.3 + adjusted_weight * 0.7, 4)
        max_score_seen = max(max_score_seen, raw_score)

        results.append({
            "Stock": stock,
            "Headline": headline,
            "Sentiment": round(sentiment, 2),
            "Impact Category": impact_cat,
            "Impact Weight": adjusted_weight,
            "Raw Score": raw_score,
            "Source": source,
            "Link": link,
            "Sources Count": source_count,
            "Summary": summarize_text(headline)
        })

    if max_score_seen > 0:
        for r in results:
            r["Impact Score"] = round((r["Raw Score"] / max_score_seen) * 10, 2)
    else:
        for r in results:
            r["Impact Score"] = 0.0

    return sorted(results, key=lambda x: x["Impact Score"], reverse=True)

stock_list = load_stocks()

st.sidebar.header("📌 Technical Analysis")
stock_input = st.sidebar.text_input("Enter stock symbol (e.g., INFY.NS):")
if st.sidebar.button("Generate Technical Analysis"):
    st.session_state.view = 'technical'

if st.session_state.view == 'technical':
    st.title("📉 Technical Analysis")
    if stock_input:
        try:
            data = yf.download(stock_input, period="6mo", interval="1d")
            if not data.empty:
                st.subheader(f"Last 6 Months Price Chart for {stock_input.upper()}")
                st.line_chart(data['Close'])

                data['20DMA'] = data['Close'].rolling(window=20).mean()
                data['50DMA'] = data['Close'].rolling(window=50).mean()
                st.line_chart(data[['Close', '20DMA', '50DMA']])

                # RSI
                delta = data['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                data['RSI'] = 100 - (100 / (1 + rs))
                st.line_chart(data['RSI'])
                st.write(f"**RSI (latest):** {round(data['RSI'].iloc[-1], 2)}")

                # MACD
                data['EMA12'] = data['Close'].ewm(span=12).mean()
                data['EMA26'] = data['Close'].ewm(span=26).mean()
                data['MACD'] = data['EMA12'] - data['EMA26']
                data['Signal'] = data['MACD'].ewm(span=9).mean()
                st.line_chart(data[['MACD', 'Signal']])

                st.write("**Latest Close:**", round(data['Close'].iloc[-1], 2))
                st.write("**20DMA:**", round(data['20DMA'].iloc[-1], 2))
                st.write("**50DMA:**", round(data['50DMA'].iloc[-1], 2))

                if data['20DMA'].iloc[-1] > data['50DMA'].iloc[-1]:
                    st.success("Bullish Crossover: 20DMA > 50DMA")
                else:
                    st.warning("Bearish Crossover: 20DMA < 50DMA")
            else:
                st.warning("No data found for symbol")
        except Exception as e:
            st.error(f"Error: {e}")
    st.button("🔙 Back to News", on_click=lambda: st.session_state.update({'view': 'news'}))

elif st.session_state.view == 'news':
    st.title("📊 Impact-Based Nifty Stock News Screener")
    if st.button("🔍 Analyze News (Impact & Sentiment)"):
        with st.spinner("Fetching and analyzing news..."):
            raw_news = fetch_news(NEWS_SOURCES, stock_list)
            analyzed = analyze_news(raw_news)

            if analyzed:
                st.success(f"{len(analyzed)} news items found.")
                for news in analyzed:
                    with st.expander(f"📌 {news['Stock']} — Impact Score: {news['Impact Score']}"):
                        st.write(f"**Headline:** {news['Headline']}")
                        st.write(f"**Summary:** {news['Summary']}")
                        st.write(f"**Sentiment Score:** {news['Sentiment']}")
                        st.write(f"**Impact Category:** {news['Impact Category']} (Weight: {news['Impact Weight']})")
                        st.write(f"**Reported By:** {news['Sources Count']} source(s): {news['Source']}")
                        st.write(f"**Scoring Formula:** `0.3 × Sentiment + 0.7 × Impact Weight = {news['Raw Score']}`")
                        st.write(f"**Source:** [{news['Source'].split(',')[0]}]({news['Link']})")
            else:
                st.warning("No impactful news found today.")
