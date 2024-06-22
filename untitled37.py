# -*- coding: utf-8 -*-
"""Untitled37.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1YbN7KPkjp7nAkzcT2Vlgg_JXl4olNRF8
"""

!pip install ta-py
!pip install yfinance
!pip install ta
! pip install streamlit -q

import yfinance as yf
import numpy as np
import pandas as pd
from ta import add_all_ta_features
from ta.utils import dropna
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import r2_score, mean_squared_error
import xgboost as xgb
import streamlit as st

# 1. Data Loading and Preprocessing
def load_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)
    if data.empty:
        raise ValueError("No data returned for this ticker and date range.")
    data = data.interpolate(method='linear')
    data['logreturn'] = np.log(data['Adj Close'] / data['Adj Close'].shift(1))
    data = dropna(data)
    data = add_all_ta_features(data, open="Open", high="High", low="Low", close="Adj Close", volume="Volume", fillna=True)
    return data

# Streamlit interface for user interaction
st.title("Stock Price Prediction using Machine Learning and GBM")

# Inputs before simulation
default_ticker = "GOTO.JK"
ticker = st.sidebar.text_input("Enter stock ticker:", default_ticker)
start_date = st.sidebar.date_input("Start date:", pd.to_datetime("2021-01-01"))
end_date = st.sidebar.date_input("End date:", pd.to_datetime("2023-12-31"))
features = st.sidebar.multiselect("Select features", options=['volume_adi', 'momentum_rsi', 'trend_sma_fast', 'trend_ema_fast', 'volatility_bbh'], default=['momentum_rsi'])

# Define the run simulation button
simulate = st.sidebar.button("Run Simulation")

if simulate:
    data = load_data(ticker, start_date, end_date)
    if data is not None:
        # 2. Feature Selection and Scaling
        def prepare_features(data, selected_features):
            scaler = MinMaxScaler()
            data[selected_features] = scaler.fit_transform(data[selected_features])
            return data, scaler

        data, scaler = prepare_features(data, features)

        # 3. XGBoost Model Training
        def train_xgb(data, features, target):
            data_matrix = xgb.DMatrix(data[features], label=data[target])
            params = {'max_depth': 3, 'eta': 0.1, 'objective': 'reg:squarederror', 'eval_metric': 'rmse'}
            model = xgb.train(params, data_matrix, num_boost_round=100)
            return model

        model = train_xgb(data, features, 'logreturn')

        # 4. GBM Simulation with Machine Learning Predicted Drift using XGBoost
        def gbm_sim_xgb(spot_price, volatility, steps, model, features, data):
            data_matrix = xgb.DMatrix(data[features])
            drift = model.predict(data_matrix)
            paths = [spot_price]
            for i in range(1, len(drift)):
                paths.append(paths[-1] * np.exp((drift[i-1] - 0.5 * (volatility/252)**2) + (volatility/252) * np.random.normal()))
            return paths, drift

        spot_price = data["Adj Close"].iloc[-1]
        volatility = data['logreturn'].std() * np.sqrt(252)
        simulated_paths, drifts = gbm_sim_xgb(spot_price, volatility, len(data), model, features, data)

        st.line_chart(data["Adj Close"].rename('Actual Price'))
        st.line_chart(pd.Series(simulated_paths, index=data.index).rename('Simulated Price'))

        abs_error = [abs(i-j) for (i, j) in zip(simulated_paths, data['Adj Close'].values)]
        rel_error = [abs(i-j)/j*100 for (i, j) in zip(simulated_paths, data['Adj Close'].values)]

        st.line_chart(pd.DataFrame({'Absolute Error': abs_error, 'Relative Error (%)': rel_error}, index=data.index))

        y_true = data['logreturn'].values
        y_pred = drifts
        r2 = r2_score(y_true, y_pred)
        mse = mean_squared_error(y_true, y_pred)

        st.write(f"R² score: {r2}")
        st.write(f"Mean Squared Error (MSE): {mse}")

#untuk mendapatkan alamat IP publik dari perangkat yang menjalankan kodingan ini
!wget -q -O - ipv4.icanhazip.com

! streamlit run app.py & npx localtunnel --port 8501