## Investment Risk Dashboard

Python based portfolio analytics dashboard for S&P 500 Stocks.

## Features
- Real-time stock data via Yahoo Finance API
- Metrics:  Overview: Sector & Region Allocation 
            Performance Analysis: Realtive Price Performance, Jenses alpha (benchmark: S&P 500)
            Risk Analysis: Rolling Votility (30 Days, Annualised)
            Risk-Return Analysis: Sharpe Ratio


- Interactive visualizations
- Streamlit web dashboard

## Installation
pip install -r requirements.txt

## Usage
streamlit run app.py

## Tech Stack
- Python, Pandas, NumPy, Plotly, Streamlit

## Limitatations
- REGION_MAP only includes 14 countries which would lead to some entires beeing sorted into the "Other" section in the region chart if other indices are added (f.e. DAX)