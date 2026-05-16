"""
universe.py
-----------
Provides the S&P 500 stock universe for the Finance Risk Dashboard.
Also owns REGION_MAP — geographic classification is universe-level domain logic.
"""

import pandas as pd


# ── Constants ─────────────────────────────────────────────────────────────────
# Centralised here so portfolio.py and app.py both import from one source of truth.

REGION_MAP = {
    "United States": "North America", "Canada": "North America", "Mexico": "North America",
    "Germany": "Europe", "France": "Europe", "United Kingdom": "Europe",
    "Switzerland": "Europe", "Netherlands": "Europe",
    "Japan": "Asia", "China": "Asia", "South Korea": "Asia",
    "India": "Emerging Markets", "Brazil": "Emerging Markets", "Taiwan": "Emerging Markets",
}


def get_sp500_universe() -> pd.DataFrame:
    """
    Fetches the current S&P 500 constituents from Wikipedia.
    User-Agent header required — Wikipedia blocks requests without it.
    """
    header = {"User-Agent": "Mozilla/5.0"}
    url    = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    table  = pd.read_html(url, storage_options={"User-Agent": header["User-Agent"]})[0]
    return (
        table[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry", "Headquarters Location"]]
        .rename(columns={
            "Symbol":                "symbol",
            "Security":              "name",
            "GICS Sector":           "sector",
            "GICS Sub-Industry":     "sub_industry",
            "Headquarters Location": "headquarters",
        })
        .reset_index(drop=True)
    )