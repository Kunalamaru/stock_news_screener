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

st.set_page_config(page_title="📈 Smart Stock News Analyzer", layout="wide")

# Self-learning model state
WEIGHTS_FILE = "weights_state.json"

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
        return pd.read_csv("performance_log.csv")
    except:
        return pd.DataFrame(columns=["Stock", "Impact Category", "Predicted", "Actual"])

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

# Then integrate this logic into your main flow after predictions
# performance_log = load_performance_log()
# self_learn_model(performance_log)

# You must also update this log when new actual values become known
# and adjust weights accordingly

# The rest of the code remains unchanged...
