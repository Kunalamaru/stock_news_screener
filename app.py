import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob

st.set_page_config(page_title="📈 Stock News Analyzer", layout="centered")
st.title("📈 Nifty Stock News Sentiment Analyzer")

# Load Telegram credentials from secrets
TELEGRAM_TOKEN = st.secrets["TELEGRAM"]["TOKEN"]
CHAT_ID = st.secrets["TELEGRAM"]["CHAT_ID"]

# Load stock list
@st.cache_data
def load_stocks():
    df = pd.read_csv("nifty_stocks.csv", header=None)
    return df[0].str.upper().tolist()

# Fetch stock news
def fetch_news(stock_list):
    urls = [
        "https://www.moneycontrol.com/news/business/stocks/",
        "https://economictimes.indiatimes.com/markets/stocks/news"
    ]
    headlines = []
    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            soup = BeautifulSoup(r.content, "html.parser")
            for tag in soup.find_all(['h2', 'h3']):
                text = tag.get_text(strip=True)
                if any(stock in text.upper() for stock in stock_list):
                    headlines.append(text)
        except Exception as e:
            st.error(f"Failed to fetch from {url}: {e}")
    return list(set(headlines))

# Analyze sentiment
def analyze(news, stock_list):
    results = []
    for headline in news:
        score = TextBlob(headline).sentiment.polarity
        if score > 0.15:
            for stock in stock_list:
                if stock in headline.upper():
                    results.append((stock, headline, round(score, 2)))
    return results

# Send Telegram message via HTTP
def send_to_telegram(results):
    if not results:
        message = "📭 No positive news today."
    else:
        message = "📊 *Positive Stock News Today*\n\n"
        for stock, headline, score in results:
            message += f"🔹 *{stock}*: {headline}\n_(Sentiment: {score})_\n\n"

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=payload)
    return response.ok

# UI
stock_list = load_stocks()

if st.button("📰 Analyze Today's News"):
    with st.spinner("Fetching and analyzing news..."):
        news = fetch_news(stock_list)
        results = analyze(news, stock_list)
        if results:
            st.success(f"Found {len(results)} positive news items.")
            for stock, headline, score in results:
                st.markdown(f"**{stock}**: {headline} _(Sentiment: {score})_")
        else:
            st.info("No positive news found.")

    if st.button("📤 Send to Telegram"):
        if send_to_telegram(results):
            st.success("✅ Sent to Telegram!")
        else:
            st.error("❌ Failed to send Telegram message.")
