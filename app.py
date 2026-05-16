"""
app.py
------
Streamlit dashboard for the Finance Risk Dashboard.

Structure:
    Sidebar         → ticker selection via S&P 500 universe (universe.py)
    Main area       → four sections:
                      0. Portfolio Overview   (sector, geography)
                      1. Performance Analysis (relative price performance, alpha)
                      2. Risk Analysis        (rolling volatility, beta)
                      3. Risk-Return Analysis (sharpe ratio)

Usage:
    streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.portfolio import Portfolio
from src.universe import get_sp500_universe


# ── Page Config ───────────────────────────────────────────────────────────────
# Must be the first Streamlit call in the script.

st.set_page_config(page_title="Finance Risk Dashboard", layout="wide")
st.title("Finance Risk Dashboard")
st.caption("By Luca Polinski")


# ── Helpers ───────────────────────────────────────────────────────────────────
# Isolated chart-building functions keep the main layout readable
# and make individual charts easy to test or reuse.

def chart_price(portfolio: Portfolio):
    data = portfolio.prices.copy()
    data["S&P 500"] = portfolio.benchmark_prices

    # Convert to percentage change from inception — comparable across stocks.
    data = (data / data.iloc[0] - 1) * 100

    fig = px.line(data, title="Relative Price Performance (%)", subtitle="Tracks the percentage price change of each stock relative to its " \
    "starting price over the selected period, benchmarked against the S&P 500. Relative Price Performance = (Price / Price₀ - 1) × 100.")
    fig.update_layout(yaxis_title="Performance (%)")
    fig.update_yaxes(ticksuffix="%")

    # S&P 500 styled distinctly as benchmark — thicker black line.
    fig.update_traces(
        selector={"name": "S&P 500"},
        line={"color": "black", "width": 3},
    )

    return fig

def chart_annualised_returns(portfolio: Portfolio):
    data = (
        portfolio.annualised_returns()
        .rename_axis("Ticker")
        .reset_index(name="Annualised Return (%)")
    )
    fig = px.bar(
        data, x="Ticker", y="Annualised Return (%)",
        title    = "Annualised Return (CAGR)",
        subtitle = "Geometric compounding of daily returns, annualised over the selected period. Annualised Returns = (1 + Total Return)^(252/n) - 1.",
    )
    fig.add_hline(y=0, line_dash="dash", line_color="black")
    return fig

def chart_alpha(portfolio: Portfolio):
    data = (
        portfolio.alpha()
        .rename_axis("Ticker")
        .reset_index(name="Alpha (Annualised)")
    )
    return px.bar(data, x="Ticker", y="Alpha (Annualised)", title="Alpha vs. S&P 500", subtitle="Measures the excess return of each stock " \
    "beyond what is explained by market movements, adjusted for the risk-free rate (5% Government Bonds). <br>" \
    "Jensens Alpha = (Stock Return - Risk-Free Rate) = α + β × (S&P 500 Return - Risk-Free Rate), α annualised × 252.")

def chart_beta(portfolio: Portfolio):
    data = (
        portfolio.beta()
        .rename_axis("Ticker")
        .reset_index(name="Beta")
    )
    return px.bar(
        data, x="Ticker", y="Beta",
        title="Beta vs. S&P 500",
        subtitle="Measures systematic market risk. Beta > 1: more volatile than market | Beta = 1: moves with market "
        "| Beta < 1: less volatile than market. <br>" \
        "Beta = Covariance(Stock, Market) / Variance(Market)"
    )

def chart_max_drawdown(portfolio: Portfolio):
    data = (
        portfolio.max_drawdown()
        .rename_axis("Ticker")
        .reset_index(name="Max Drawdown (%)")
    )
    return px.bar(
        data, x="Ticker", y="Max Drawdown (%)",
        title="Maximum Drawdown",
        subtitle="Largest peak-to-trough loss over the selected period. Maximum Drawdown = Min((Cumulative Return - Rolling Max) / Rolling Max)."
    )

def chart_rolling_volatility(portfolio: Portfolio):
    return px.line(
        portfolio.rolling_volatility(),
        title    = "EWMA Volatility (30-Day Span, Annualised)",
        subtitle = "Exponentially weighted volatility — recent returns carry more weight than older ones. Industry standard: JPMorgan RiskMetrics. EWMA Volatillity = EWMA Std(Daily Returns) × √252.",
    )

def chart_sharpe_ratio(portfolio: Portfolio):
    data = (
        portfolio.sharpe_ratio()
        .rename_axis("Ticker")
        .reset_index(name="Sharpe Ratio")
    )
    return px.bar(data, x="Ticker", y="Sharpe Ratio", title="Sharpe Ratio", subtitle="Evaluates return per unit of risk taken. Sharpe Ratio = "
    "(Annual Return - 5% Risk-Free Rate) / Volatility. > 1.0 is good | > 2.0 is excellent | < 0 underperforms a government bond.")

def chart_sector(portfolio: Portfolio):
    # Sector distribution as pie chart — uses metadata loaded in Portfolio.__init__.
    return px.pie(
        portfolio.metadata,
        names="sector",
        title="Sector Allocation (not weighted by market share!)",
        subtitle="Breakdown of portfolio composition by sector."
    )

def chart_geography(portfolio: Portfolio):
    # Geography uses all_regions to guarantee every region appears on the chart,
    # even if no ticker maps to it — consistent layout regardless of selection.
    all_regions = ["North America", "Europe", "Asia", "Emerging Markets", "Other"]

    geo_data = (
        pd.DataFrame({"region": all_regions})
        .merge(
            portfolio.metadata["region"]
            .value_counts()
            .rename("count")
            .reset_index(),
            on="region", how="left",
        )
        .fillna(0)
        .assign(**{"Allocation in %": lambda x: (x["count"] / x["count"].sum() * 100).round(1)})
    )

    return px.bar(
        geo_data,
        x="Allocation in %", y="region",
        orientation="h",
        title="Country & Region Allocation (%)",
        subtitle="Breakdown of portfolio composition by geographic sector."
    )


# ── Sidebar: Ticker Selection ─────────────────────────────────────────────────

st.sidebar.header("Portfolio Settings")

# universe.py consumed here — decoupled from portfolio.py by design.
# No spinner in sidebar: st.spinner does not render reliably inside st.sidebar.
# Cached to avoid re-scraping Wikipedia on every Streamlit rerun.
@st.cache_data(show_spinner=False)
def load_universe():
    return get_sp500_universe()

universe = load_universe()
name_map = universe.set_index("symbol")["name"].to_dict()

selected = st.sidebar.multiselect(
    label       = "Select Tickers",
    options     = universe["symbol"].tolist(),
    default     = ["ABNB", "MSFT", "JPM"],
    format_func = lambda x: f"{x} - {name_map.get(x, x)}",
)

period = st.sidebar.selectbox(
    label   = "Period",
    options = ["1mo", "3mo", "6mo","1y", "2y", "5y"],
    index   = 3,    # default: 1y
)


# ── Guard: No Tickers Selected ────────────────────────────────────────────────

if not selected:
    st.warning("Please select at least one ticker from the sidebar.")
    st.stop()


# ── Data Loading ──────────────────────────────────────────────────────────────
# st.cache_data is correct for API responses and DataFrames (per-user cache).
# st.cache_resource is for shared resources like DB connections — not used here.

@st.cache_data(show_spinner=False)
def load_portfolio(tickers: tuple, period: str) -> Portfolio:
    # tickers is a tuple (not list) because cache keys must be hashable.
    return Portfolio(list(tickers), period=period)

with st.spinner("Fetching market data..."):
    try:
        portfolio = load_portfolio(tuple(selected), period)
    except ValueError as e:
        st.error(f"Failed to load portfolio: {e}")
        st.stop()


# ── Section 0: Portfolio Overview ─────────────────────────────────────────────

st.header("Portfolio Overview")

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(chart_sector(portfolio), use_container_width=True)
with col2:
    st.plotly_chart(chart_geography(portfolio), use_container_width=True)


# ── Section 1: Performance Analysis ──────────────────────────────────────────

st.header("Performance Analysis")
st.plotly_chart(chart_price(portfolio), use_container_width=True)
st.plotly_chart(chart_annualised_returns(portfolio), use_container_width=True)
st.plotly_chart(chart_alpha(portfolio), use_container_width=True)


# ── Section 2: Risk Analysis ──────────────────────────────────────────────────

st.header("Risk Analysis")
st.plotly_chart(chart_rolling_volatility(portfolio), use_container_width=True)
st.plotly_chart(chart_beta(portfolio), use_container_width=True)
st.plotly_chart(chart_max_drawdown(portfolio), use_container_width=True)

# ── Section 3: Risk-Return Analysis ──────────────────────────────────────────

st.header("Risk-Return Analysis")
st.plotly_chart(chart_sharpe_ratio(portfolio), use_container_width=True)