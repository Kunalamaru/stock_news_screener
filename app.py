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

# Update weights based on real performance
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

# Auto-fetch actual prices and update performance log
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

def run_main_app():
    st.title("📊 Stock News and Technical Analysis")
    st.write("This is where your main app logic (news analysis, technical charts, etc.) goes.")

    # Update performance log with actual gains
    performance_log = fetch_actual_gains()

    # Trigger self-learning
    self_learn_model(performance_log)

    # Your main logic would be added here
    # Sample UI: View performance log and impact weights

    with st.expander("📊 View Performance Log"):
        st.dataframe(performance_log.sort_values(by='Date', ascending=False))
        csv = performance_log.to_csv(index=False).encode('utf-8')
        st.download_button("Download Performance Log CSV", csv, "performance_log.csv", "text/csv")

    with st.expander("📈 Current Impact Weights"):
        weights_df = pd.DataFrame.from_dict(IMPACT_WEIGHTS, orient='index', columns=['Weight']).sort_values(by='Weight', ascending=False)
        st.bar_chart(weights_df)
        st.dataframe(weights_df)

    st.info("✅ Your self-learning model is live. Predictions will improve as more data is gathered.")

# Run the main app
run_main_app()
