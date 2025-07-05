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
import json
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="📈 Smart Stock News Analyzer", layout="wide")

# Self-learning model state
WEIGHTS_FILE = "weights_state.json"
PERFORMANCE_LOG = "performance_log.csv"

# Load or initialize weights
if os.path.exists(WEIGHTS_FILE):
    with open(WEIGHTS_FILE, 'r') as f:
        IMPACT_WEIGHTS = json.load(f)
else:
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
def load_performance_log():
    try:
        return pd.read_csv(PERFORMANCE_LOG)
    except:
        return pd.DataFrame(columns=["Stock", "Impact Category", "Predicted", "Actual", "Date"])

def save_weights():
    with open(WEIGHTS_FILE, 'w') as f:
        json.dump(IMPACT_WEIGHTS, f)

def self_learn_model(performance_log):
    if len(performance_log) >= 20:
        grouped = performance_log.groupby("Impact Category")
        for cat, group in grouped:
            avg_delta = (group['Actual'] - group['Predicted']).mean()
            if cat in IMPACT_WEIGHTS:
                IMPACT_WEIGHTS[cat] = max(4, min(10, round(IMPACT_WEIGHTS[cat] + avg_delta, 1)))
        save_weights()

@st.cache_data
def fetch_actual_gains():
    df = load_performance_log()
    updated = False
    for i, row in df.iterrows():
        if pd.isna(row['Actual']) and pd.notna(row['Stock']) and pd.notna(row['Date']):
            try:
                stock = row['Stock']
                date = pd.to_datetime(row['Date'])
                next_day = date + timedelta(days=1)
                data = yf.download(stock + ".NS", start=next_day.strftime('%Y-%m-%d'), end=(next_day + timedelta(days=2)).strftime('%Y-%m-%d'))
                if not data.empty:
                    actual_gain = round(((data['Close'][-1] - data['Open'][0]) / data['Open'][0]) * 100, 2)
                    df.at[i, 'Actual'] = actual_gain
                    updated = True
            except:
                continue
    if updated:
        df.to_csv(PERFORMANCE_LOG, index=False)
    return df

def fetch_news(stock_list):
    # This should be replaced with your actual scraper logic
    # For now, we simulate
    return [
        {
            'Stock': 'INFY',
            'Headline': 'Infosys bags $1 billion contract from US firm',
            'Source': 'Economic Times',
            'Link': 'https://economictimes.indiatimes.com',
            'Summary': 'Infosys wins large contract',
            'Score': 9.5,
            'Category': 'contracts',
            'RSI': 54.35,
            'Predicted Gain': 5.6,
            'Buy Calls': 3,
            'Hold Calls': 1,
            'Sell Calls': 0,
            'Sentiment': 'Bullish'
        }
    ]

def display_news_cards(news_items):
    for news in sorted(news_items, key=lambda x: -x['Score']):
        score = news['Score']
        rsi = news['RSI']
        predicted = news['Predicted Gain']
        font_color = 'green' if predicted >= 3 else 'yellow'
        border_style = f'1px solid black'

        with st.expander(f"**{news['Stock']}** — Impact Score: {score} — RSI: {rsi}"):
            st.markdown(f"**News:** {news['Headline']}")
            st.markdown(f"**Summary:** {news['Summary']}")
            st.markdown(f"**Source:** [{news['Source']}]({news['Link']})")
            st.markdown(f"**Category:** {news['Category']}")
            st.markdown(f"**Predicted Gain:** {predicted}%")
            st.markdown(f"**Buy Calls:** {news['Buy Calls']} | Hold: {news['Hold Calls']} | Sell: {news['Sell Calls']}")
            icon = "🐂" if news['Sentiment'] == 'Bullish' else "🐻" if news['Sentiment'] == 'Bearish' else "🐐"
            st.markdown(f"**Market View:** {icon} {news['Sentiment']}")

def technical_analysis_ui():
    st.subheader("🔍 Technical Analysis")
    stock_input = st.text_input("Enter stock name (e.g., INFY)")
    if st.button("Generate Technical Analysis") and stock_input:
        try:
            data = yf.download(stock_input + ".NS", period='1d', interval='1m')
            if not data.empty:
                fig, ax = plt.subplots()
                ax.plot(data['Close'], label='Price')
                ax.set_title(f'{stock_input} Intraday Price')
                ax.legend()
                st.pyplot(fig)

                rsi = compute_rsi(data['Close'])
                st.metric("Current RSI", f"{rsi:.2f}")

                macd_line, signal_line = compute_macd(data['Close'])
                fig2, ax2 = plt.subplots()
                ax2.plot(macd_line, label='MACD')
                ax2.plot(signal_line, label='Signal')
                ax2.set_title("MACD")
                ax2.legend()
                st.pyplot(fig2)
        except:
            st.warning("Could not retrieve data.")

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def compute_macd(series):
    exp1 = series.ewm(span=12, adjust=False).mean()
    exp2 = series.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def run_main_app():
    st.title("📊 Stock News and Technical Analysis")

    performance_log = fetch_actual_gains()
    self_learn_model(performance_log)

    stock_list = []  # Load actual Nifty 100 + Next 50 list
    news = fetch_news(stock_list)
    display_news_cards(news)
    st.divider()
    technical_analysis_ui()

    with st.expander("📊 View Performance Log"):
        st.dataframe(performance_log.sort_values(by='Date', ascending=False))
        csv = performance_log.to_csv(index=False).encode('utf-8')
        st.download_button("Download Performance Log CSV", csv, "performance_log.csv", "text/csv")

    with st.expander("📈 Current Impact Weights"):
        weights_df = pd.DataFrame.from_dict(IMPACT_WEIGHTS, orient='index', columns=['Weight']).sort_values(by='Weight', ascending=False)
        st.bar_chart(weights_df)
        st.dataframe(weights_df)

    st.info("✅ Self-learning model active. News-based predictions improve daily.")

run_main_app()
