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
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

st.set_page_config(page_title="📈 Smart Stock News Analyzer", layout="wide")

# Initialize session state to handle view switching
if 'view' not in st.session_state:
    st.session_state.view = 'news'
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if 'analyzed_news' not in st.session_state:
    st.session_state.analyzed_news = []
if 'trigger_transition' not in st.session_state:
    st.session_state.trigger_transition = False

page_turn_css = """
<style>
.book-transition {
  animation: book-flip 0.6s ease-in-out;
}
@keyframes book-flip {
  0% {transform: rotateY(0); opacity: 1;}
  100% {transform: rotateY(-180deg); opacity: 0.3;}
}
</style>
"""

@st.cache_data
def load_stocks():
    df = pd.read_csv("nifty_stocks.csv", header=None)
    return df[0].str.strip().str.upper().tolist()

# Define news sources and impact weights
NEWS_SOURCES = [
    "https://economictimes.indiatimes.com/markets/stocks/news",
    "https://www.moneycontrol.com/news/business/stocks/",
    "https://in.finance.yahoo.com/",
    "https://www.bseindia.com/markets/MarketInfo/NoticesCirculars.aspx"
]

IMPACT_WEIGHTS = {
    "contracts": 10,
    "government": 9,
    "investment": 9,
    "merger": 9,
    "profit": 8,
    "upgrade": 8,
    "record high": 7,
    "raw material": 7,
    "tariff": 7,
    "bulk deal": 7,
    "misc": 4
}

@st.cache_data
def load_historical_data():
    try:
        df = pd.read_csv("news_impact_history.csv")
        return df
    except:
        return pd.DataFrame(columns=["impact_category", "actual_change"])

def tune_weights(historical_df):
    if len(historical_df) > 10:
        means = historical_df.groupby("impact_category")["actual_change"].mean().to_dict()
        for key in IMPACT_WEIGHTS:
            if key in means:
                IMPACT_WEIGHTS[key] = round(np.interp(means[key], [-5, 5], [4, 10]), 1)


def fetch_news(sources, stock_names):
    headlines = []
    for url in sources:
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup.find_all(['a', 'h2', 'h3']):
                text = tag.get_text(strip=True)
                if any(stock in text.upper() for stock in stock_names):
                    link = tag.get('href') or url
                    headlines.append({
                        "headline": text,
                        "link": link,
                        "source": url
                    })
        except Exception:
            continue
    return headlines

def classify_impact(text):
    impact = "misc"
    for key in IMPACT_WEIGHTS:
        if key in text.lower():
            impact = key
            break
    return impact, IMPACT_WEIGHTS[impact]

def get_rsi(symbol):
    try:
        df = yf.download(symbol, period='1mo')
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi.iloc[-1], 2)
    except:
        return 50

def analyze_news(raw):
    results = []
    seen = set()
    for item in raw:
        headline = item['headline']
        source = item['source']
        link = item['link']
        for stock in stock_list:
            if stock in headline.upper() and (headline, stock) not in seen:
                seen.add((headline, stock))
                sentiment = TextBlob(headline).sentiment.polarity
                impact_cat, weight = classify_impact(headline)
                rsi = get_rsi(stock + ".NS")
                score = round(0.3 * sentiment + 0.7 * weight, 2)
                color = '🟢' if score >= 8 else '🟡' if score >= 6 else '🔴'
                results.append({
                    "Stock": stock,
                    "Color": color,
                    "Headline": headline,
                    "Summary": headline[:100] + "...",
                    "Sentiment": round(sentiment, 2),
                    "Impact Category": impact_cat,
                    "Impact Weight": weight,
                    "RSI": rsi,
                    "Impact Score": score,
                    "Raw Score": score,
                    "Link": link,
                    "Source": source,
                    "Sources Count": 1
                })
    results.sort(key=lambda x: x['Impact Score'], reverse=True)
    return results
# Keep all functions like classify_impact, summarize_text, get_rsi, analyze_news unchanged

stock_list = load_stocks()

st.sidebar.header("📌 Technical Analysis")
stock_input = st.sidebar.text_input("Enter stock symbol (e.g., INFY.NS):")
st.session_state.auto_refresh = st.sidebar.toggle("⟳ Auto Refresh (1 min)", value=st.session_state.auto_refresh)
if st.sidebar.button("Generate Technical Analysis"):
    st.session_state.trigger_transition = True
    st.session_state.view = 'technical'

if st.session_state.trigger_transition:
    st.markdown(page_turn_css, unsafe_allow_html=True)
    components.html("""<div class='book-transition'></div>""", height=0)
    st.session_state.trigger_transition = False

if st.session_state.view == 'technical':
    if st.session_state.auto_refresh:
        st_autorefresh(interval=60000, key="autorefresh")

    st.title("📉 Technical Analysis")
    if stock_input:
        try:
            data = yf.download(stock_input, period="1d", interval="1m")
            if not data.empty:
                st.subheader(f"1-Day Intraday Price Chart for {stock_input.upper()}")
                st.line_chart(data['Close'])

                delta = data['Close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.rolling(14).mean()
                avg_loss = loss.rolling(14).mean()
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = round(rsi.iloc[-1], 2)
                st.write(f"**RSI (latest):** {current_rsi}")

                data['EMA12'] = data['Close'].ewm(span=12, adjust=False).mean()
                data['EMA26'] = data['Close'].ewm(span=26, adjust=False).mean()
                data['MACD'] = data['EMA12'] - data['EMA26']
                data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
                macd_chart = pd.DataFrame({"MACD": data['MACD'], "Signal": data['Signal']})
                st.line_chart(macd_chart.dropna())

                latest_macd = data['MACD'].dropna().iloc[-1]
                latest_signal = data['Signal'].dropna().iloc[-1]
                if latest_macd > latest_signal:
                    st.success("MACD Bullish Crossover Detected")
                else:
                    st.warning("MACD Bearish Crossover Detected")
            else:
                st.warning("No data found for symbol")
        except Exception as e:
            st.error(f"Error: {e}")
    if st.button("🔙 Back to News"):
        st.session_state.trigger_transition = True
        st.session_state.view = 'news'

elif st.session_state.view == 'news':
    st.title("📊 Impact-Based Nifty Stock News Screener")
    if st.session_state.analyzed_news:
        analyzed = st.session_state.analyzed_news
    elif st.button("🔍 Analyze News (Impact & Sentiment)"):
        with st.spinner("Fetching and analyzing news..."):
            history_df = load_historical_data()
            tune_weights(history_df)
            raw_news = fetch_news(NEWS_SOURCES, stock_list)
            analyzed = analyze_news(raw_news)
            st.session_state.analyzed_news = analyzed
    else:
        analyzed = []

    if analyzed:
        st.success(f"{len(analyzed)} news items found.")
        for news in analyzed:
            label = f"{news['Color']} {news['Stock']} — Impact Score: {news['Impact Score']} — RSI: {news['RSI']}"
            with st.expander(label):
                st.write(f"**Headline:** {news['Headline']}")
                st.write(f"**Summary:** {news['Summary']}")
                st.write(f"**Sentiment Score:** {news['Sentiment']}")
                st.write(f"**Impact Category:** {news['Impact Category']} (Weight: {news['Impact Weight']})")
                st.write(f"**Reported By:** {news['Sources Count']} source(s): {news['Source']}")
                st.write(f"**Scoring Formula:** `0.3 × Sentiment + 0.7 × Impact Weight = {news['Raw Score']}`")
                st.write(f"**Source:** [{news['Source'].split(',')[0]}]({news['Link']})")
    else:
        st.warning("No impactful news found today.")
