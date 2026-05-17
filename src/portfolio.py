"""
portfolio.py
------------
Core analytics class for the Finance Risk Dashboard.
Handles data loading, KPI calculation, and metadata enrichment.

Integration:
    universe.py → supplies REGION_MAP (geographic classification logic)
                  and available tickers (S&P 500 universe) via app.py
    app.py      → user selects tickers from universe, passes them into Portfolio()

    Portfolio depends on universe.py only for REGION_MAP — a deliberate minimal
    dependency. Swapping universe.py only requires updating REGION_MAP there.
"""

import numpy as np
import pandas as pd
import yfinance as yf

from src.universe import REGION_MAP


# ── Constants ─────────────────────────────────────────────────────────────────
# Defined at module level so any change propagates everywhere automatically.

TRADING_DAYS   = 252        # Standard number of trading days per year
RISK_FREE_RATE = 0.05       # Fallback if dynamic fetch fails - see _get_risk_free_rate()
ROLLING_WINDOW = 30         # EWMA span in trading days (JPMorgan RiskMetrics standard)

# REGION_MAP is imported from universe.py — geographic classification because
# is universe-level domain logic, not portfolio analytics logic.


# ── Portfolio Class ───────────────────────────────────────────────────────────

class Portfolio:
    """
    Represents a stock portfolio and exposes risk & performance analytics.

    Typical usage in app.py:
        portfolio = Portfolio(["AAPL", "MSFT", "JPM"])

    Parameters
    ----------
    tickers : list[str]
        Ticker symbols selected by the user (sourced from universe.py).
    period : str
        yfinance period string. Default "2y" covers 2 years of trading data.
    benchmark : str
        Benchmark ticker for alpha calculation. Default is S&P 500 (^GSPC).
    """

    def __init__(self, tickers: list[str], period: str = "2y", benchmark: str = "^GSPC"):
        if not tickers:
            raise ValueError("Portfolio requires at least one ticker.")

        self.tickers          = tickers
        self.period           = period
        self.benchmark_ticker = benchmark

        # Eager loading: all data is fetched at init rather than lazily per method.
        # This means one loading phase upfront (visible in app.py as a spinner),
        # after which all KPI methods run instantly without repeated API calls.
        self.prices            = self._load_prices()
        self.benchmark_prices  = self._load_benchmark()
        self.returns           = self.prices.pct_change().dropna()
        self.benchmark_returns = self.benchmark_prices.pct_change().dropna()
        self.metadata          = self._load_metadata()
        self.risk_free_rate    = self._get_risk_free_rate()

    def __repr__(self) -> str:
        return f"Portfolio(tickers={self.tickers}, period='{self.period}', benchmark='{self.benchmark_ticker}')"

    # ── Private: Data Loading ─────────────────────────────────────────────────
    # Prefixed with _ to signal internal use only — not part of the public API.

    def _load_prices(self) -> pd.DataFrame:
        """Downloads adjusted closing prices for all tickers."""
        # auto_adjust=True corrects for dividends and stock splits,
        # ensuring returns are not distorted by corporate actions.
        prices = yf.download(self.tickers, period=self.period, auto_adjust=True)["Close"]

        # Validate that yfinance returned data for all requested tickers.
        # Missing tickers return empty columns which would silently corrupt KPIs.
        missing = [t for t in self.tickers if t not in prices.columns]
        if missing:
            raise ValueError(f"No price data returned for: {missing}. Check ticker symbols.")

        if prices.empty:
            raise ValueError("yfinance returned no price data. Check tickers and period.")

        return prices

    def _load_benchmark(self) -> pd.Series:
        """Downloads adjusted closing prices for the benchmark index."""
        # .squeeze() converts the single-column DataFrame to a Series,
        # which is required for np.polyfit in alpha().
        benchmark = yf.download(
            self.benchmark_ticker, period=self.period, auto_adjust=True
        )["Close"].squeeze()

        if benchmark.empty:
            raise ValueError(f"No data returned for benchmark '{self.benchmark_ticker}'.")

        return benchmark
    
    def _get_risk_free_rate() -> float:
        """
        Fetches the current 10-year US Treasury yield as risk-free rate.
        ^TNX is quoted in percent — divide by 100 to get decimal.
        Falls back to 0.05 (5%) if fetch fails.
        """
        try:
            rate = yf.Ticker("^TNX").fast_info["last_price"] / 100
            return rate
        except Exception:
            return 0.05

    def _load_metadata(self) -> pd.DataFrame:
        """
        Fetches sector, industry, country and region per ticker via yfinance.

        Known limitation: one API call per ticker — can be slow for large portfolios.
        Acceptable for the current use case (up to ~10 tickers via the dashboard).
        """
        records = {}
        for ticker in self.tickers:
            try:
                info = yf.Ticker(ticker).info
                country = info.get("country", "N/A")
                records[ticker] = {
                    "sector":   info.get("sector",   "N/A"),
                    "industry": info.get("industry", "N/A"),
                    "country":  country,
                    # Region derived from country via REGION_MAP.
                    # Falls back to "Other" for unmapped countries.
                    "region":   REGION_MAP.get(country, "Other"),
                }
            except Exception:
                # If metadata fetch fails for a ticker, populate with N/A
                # rather than crashing — price data is still valid.
                records[ticker] = {
                    "sector": "N/A", "industry": "N/A",
                    "country": "N/A", "region": "Other",
                }
        return pd.DataFrame(records).T

    def _aligned_excess_returns(self) -> tuple:
        """
        Returns daily excess returns for stocks and benchmark, aligned on index.

        Subtracts the daily risk-free rate from both before returning —
        used as shared input for alpha() and beta() to avoid code duplication.
        """
        returns_aligned, benchmark_aligned = self.returns.align(
            self.benchmark_returns, join="inner", axis=0
        )
        daily_rf = self.risk_free_rate / TRADING_DAYS
        return returns_aligned - daily_rf, benchmark_aligned - daily_rf

    def _regression(self) -> pd.DataFrame:
        """
        Runs CAPM regression per ticker vs. benchmark.
        Returns alpha (annualised) and beta in one DataFrame.
        Single regression call — avoids running polyfit twice for the same data.
        Relies on _aligned_excess_returns() for aligned, rf-adjusted inputs.
        """
        excess_returns, excess_benchmark = self._aligned_excess_returns()
        records = {}
        for ticker in self.tickers:
            b, a = np.polyfit(excess_benchmark, excess_returns[ticker], 1)
            records[ticker] = {
                "alpha_annualized": a * TRADING_DAYS,
                "beta":             b,
            }
        return pd.DataFrame(records).T

    # ── Public: Risk ──────────────────────────────────────────────────────────

    def annualised_returns(self) -> pd.Series:
        """
        Annualised return (CAGR) per ticker, in percent.

        Uses geometric compounding — industry standard for performance reporting.
        Formula: (1 + Total Return)^(252/n) - 1
        Consistent with max_drawdown() — both return percent values.
        """
        n = len(self.returns)
        return ((1 + self.returns).prod() ** (TRADING_DAYS / n) - 1) * 100

    def volatility(self) -> pd.Series:
        """
        Annualised volatility per ticker.

        Calculated as: daily_std * sqrt(252)
        Measures how much the asset price fluctuates over a year.
        """
        return self.returns.std() * np.sqrt(TRADING_DAYS)

    def rolling_volatility(self) -> pd.DataFrame:
        """
        EWMA (Exponentially Weighted Moving Average) volatility per ticker.

        Assigns more weight to recent observations — reacts faster to market
        changes than a simple rolling window. No NaN gap at the start.
        Industry standard: JPMorgan RiskMetrics model.

        span=30 is equivalent to a 30-day decay factor.
        """
        return self.returns.ewm(span=ROLLING_WINDOW).std() * np.sqrt(TRADING_DAYS)

    def sharpe_ratio(self) -> pd.Series:
        """
        Annualised Sharpe ratio per ticker.

        Formula: (annual_return - risk_free_rate) / volatility
        Measures risk-adjusted return. > 1.0 is good, > 2.0 is excellent.
        Risk-free rate is set to 5% (US Treasury) via RISK_FREE_RATE constant.
        """
        annual_returns = self.returns.mean() * TRADING_DAYS
        return (annual_returns - self.risk_free_rate) / self.volatility()

    def alpha(self) -> pd.Series:
        """
        Annualised Jensen's Alpha per ticker vs. the benchmark (S&P 500).

        Excess return generated independently of market movements.
        Derived from CAPM regression in _regression().
        """
        return self._regression()["alpha_annualized"]

    def beta(self) -> pd.Series:
        """
        Beta per ticker vs. the benchmark (S&P 500).

        Measures systematic market risk. Beta > 1: more volatile than market
        | Beta < 1: less volatile. Derived from CAPM regression in _regression().
        """
        return self._regression()["beta"]

    def max_drawdown(self) -> pd.Series:
        """
        Maximum Drawdown per ticker.

        Measures the largest peak-to-trough decline over the selected period.
        Answers: what is the worst loss an investor could have experienced?

        Formula: Min((Cumulative Return - Rolling Max) / Rolling Max)
        Industry standard risk metric — reported alongside VaR in most risk frameworks.
        """
        cumulative  = (1 + self.returns).cumprod()
        rolling_max = cumulative.cummax()
        drawdown    = (cumulative - rolling_max) / rolling_max
        return (drawdown.min() * 100).rename("max_drawdown")

    # ── Public: Summary ───────────────────────────────────────────────────────

    def summary(self) -> pd.DataFrame:
        """
        KPI summary per Ticker. Covers volatility, sharpe ratio, alpha & beta only.
        For metadata(sector, geography) use portfolio.metadata directly.

        Not used directly by app.py as each chart calls the individual methods.
        Provided as a convenience method for notebook usage and external consumers.
        """
        return pd.DataFrame({
            "annualised_return":    self.annulaised_returns(),
            "volatility":           self.volatility(),
            "sharpe_ratio":         self.sharpe_ratio(),
            "alpha_annualized":     self.alpha(),
            "beta":                 self.beta(),
            "max_drawdown":         self.max_drawdown(),
        })