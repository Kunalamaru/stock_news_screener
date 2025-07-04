import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from telegram import Bot

st.set_page_config(page_title="Stock News Analyzer", layout="centered")

st.title("📈 Nifty Stock News Sentiment Analyzer")

# Load Telegram credentials securely
TELEGRAM_TOKEN = st.secrets["TELEGRAM"]["TOKEN"]
CHAT_ID = st.secrets["TELEGRAM"]["CHAT_ID"]

@st.cache_data
def load_stocks():
    return pd.read_csv("nifty_stocks.csv", header=None)[0].str.upper().tolist()

@st.cache_data
def fetch_news(stock_list):
    NEWS_SITES = [
        "https://www.moneycontrol.com/news/business/stocks/",
        "https://economictimes.indiatimes.com/markets/stocks/news"
    ]
    headlines = []
    for site in NEWS_SITES:
        try:
            resp = requests.get(site, timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for tag in soup.find_all(['h2', 'h3']):
                text = tag.text.strip()
                if any(stock in text.upper() for stock in stock_list):
                    headlines.append(text)
        except Exception:
            continue
    return list(set(headlines))

def analyze_sentiment(news_list, stock_list):
    results = []
    for news in news_list:
        sentiment = TextBlob(news).sentiment.polarity
        if sentiment > 0.15:
            for stock in stock_list:
                if stock in news.upper():
                    results.append((stock, news, round(sentiment, 2)))
    return results

def send_telegram(results):
    bot = Bot(token=TELEGRAM_TOKEN)
    if not results:
        bot.send_message(chat_id=CHAT_ID, text="No positive stock news found today.")
        return

    msg = "📊 *Positive Stock News*\n\n"
    for stock, headline, score in results:
        msg += f"🔹 *{stock}*: {headline}\n_(Sentiment: {score})_\n\n"

    bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

# --- UI ---
stocks = load_stocks()

if st.button("📰 Analyze News"):
    with st.spinner("Fetching and analyzing..."):
        news = fetch_news(stocks)
        results = analyze_sentiment(news, stocks)

        if results:
            st.success(f"Found {len(results)} positive news items.")
            for stock, headline, score in results:
                st.markdown(f"**{stock}**: {headline} _(Sentiment: {score})_")
        else:
            st.info("No positive news found.")

        if st.button("📤 Send to Telegram"):
            send_telegram(results)
            st.success("Report sent to Telegram!")
