import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from telegram import Bot

st.set_page_config(page_title="📈 Stock News Sentiment Screener", layout="centered")
st.title("📈 Nifty Stock News Sentiment Analyzer")

# Load secrets (Telegram credentials)
TELEGRAM_TOKEN = st.secrets["TELEGRAM"]["TOKEN"]
CHAT_ID = st.secrets["TELEGRAM"]["CHAT_ID"]

# Load Nifty stocks list
@st.cache_data
def load_stock_list():
    df = pd.read_csv("nifty_stocks.csv", header=None)
    return df[0].str.upper().tolist()

# Scrape headlines
def fetch_news(stock_list):
    NEWS_URLS = [
        "https://www.moneycontrol.com/news/business/stocks/",
        "https://economictimes.indiatimes.com/markets/stocks/news"
    ]
    headlines = []
    for url in NEWS_URLS:
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.content, "html.parser")
            for tag in soup.find_all(['h2', 'h3']):
                text = tag.get_text(strip=True)
                if any(stock in text.upper() for stock in stock_list):
                    headlines.append(text)
        except Exception as e:
            st.error(f"Error fetching from {url}: {e}")
    return list(set(headlines))

# Analyze sentiment
def analyze_sentiment(news_list, stock_list):
    results = []
    for headline in news_list:
        sentiment = TextBlob(headline).sentiment.polarity
        if sentiment > 0.15:
            for stock in stock_list:
                if stock in headline.upper():
                    results.append((stock, headline, round(sentiment, 2)))
    return results

# Send to Telegram
def send_telegram(results):
    bot = Bot(token=TELEGRAM_TOKEN)
    if not results:
        bot.send_message(chat_id=CHAT_ID, text="📭 No positive news found today.")
        return

    msg = "📊 *Positive Stock News Today*\n\n"
    for stock, headline, score in results:
        msg += f"🔹 *{stock}*: {headline}\n_(Sentiment: {score})_\n\n"
    bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")

# UI
stock_list = load_stock_list()

if st.button("📰 Analyze Today's News"):
    with st.spinner("Fetching and analyzing news..."):
        news = fetch_news(stock_list)
        results = analyze_sentiment(news, stock_list)
        if results:
            st.success(f"{len(results)} positive news items found!")
            for stock, headline, score in results:
                st.markdown(f"**{stock}**: {headline} _(Sentiment: {score})_")
        else:
            st.info("No positive news found.")

    if st.button("📤 Send to Telegram"):
        send_telegram(results)
        st.success("Sent to Telegram!")
