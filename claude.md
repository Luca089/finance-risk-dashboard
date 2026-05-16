📊 Finance Risk Dashboard
A Python-based risk analytics dashboard for analyzing stock portfolios.
Built as a portfolio project targeting FinTech Risk Analytics roles.
Projektstruktur
finance_dashboard/
├── data/
│   ├── alpha_metrics.csv          ← Alpha (annualisiert) pro Ticker
│   ├── benchmark.csv              ← S&P 500 Kursdaten (^GSPC, 2 Jahre)
│   ├── cumulative_returns.csv     ← Kumulative Performance (Basis 100)
│   ├── metadata.csv               ← Sector, Country, Industry pro Ticker
│   ├── rolling_volatility.csv     ← 30-Tage Rolling Volatilität (Zeitreihe)
│   ├── sharpe_ratio.csv           ← Sharpe Ratio pro Ticker
│   ├── stock_data.csv             ← Rohdaten (AAPL, MSFT, JPM – 2 Jahre)
│   └── volatility.csv             ← Annualisierte Volatilität pro Ticker
├── notebooks/
│   ├── 01_data_loading.ipynb      ✅ fertig
│   ├── 02_risk_metric_calcu...    ✅ fertig
│   └── 03_visualization.ipynb     🔄 in Arbeit
├── src/
│   └── portfolio.py               ⬜ nächster Schritt
├── app.py                         ⬜ Streamlit Dashboard
├── claude.md
├── README.md
└── requirements.txt
Tech Stack

yfinance – Aktienkurse & Benchmark via Yahoo Finance API
pandas – Datenverarbeitung & CSV Management
numpy – mathematische Berechnungen (inkl. Regressionen via np.polyfit)
plotly – interaktive Visualisierungen (px und go)
streamlit – Web Dashboard

⚠️ Kein scipy, kein sklearn — nur obiger Stack wird verwendet.
Analysierte Aktien (alle im S&P 500)
TickerUnternehmenSektorAAPLAppleTechnologyMSFTMicrosoftTechnologyJPMJP MorganFinancials
Benchmark

^GSPC (S&P 500) – geladen via yf.download("^GSPC", period="2y")
Wird für Alpha-Berechnung verwendet

Berechnete KPIs
Performance

Kumulative Returns – (1 + returns).cumprod() * 100, Basis 100 am Starttag

Risk

Volatilität (annualisiert) – returns.std() * sqrt(252)
Rolling Volatilität (30 Tage) – returns.rolling(30).std() * sqrt(252)

Risk-Adjusted Returns

Sharpe Ratio – (Jahresrendite - 0.05) / Volatilität

Risikofreier Zinssatz: 5% (US Treasury)


1.0 = gut | > 2.0 = sehr gut | < 0 = schlechter als Staatsanleihen





Alpha & Beta (CAPM)

Alpha (annualisiert) – via np.polyfit(benchmark_returns, stock_returns, 1)

_, alpha = np.polyfit(...) → alpha * 252 für Jahresbasis


Beta – Steigung der Regression gegen S&P 500

Stammdaten (yfinance ticker.info)

Sector – z.B. Technology, Financials
Country – Heimatland des Unternehmens
Industry – z.B. Consumer Electronics

Datenstruktur Konventionen

Zeitreihen (ein Wert pro Tag pro Ticker) → separate CSVs

cumulative_returns.csv, rolling_volatility.csv


Einzelwerte pro Ticker → separate CSVs pro Metrik

volatility.csv, sharpe_ratio.csv, alpha_metrics.csv


Stammdaten → metadata.csv

Notebook Struktur & Verantwortlichkeiten
NotebookAufgabe01_data_loadingKursdaten, Benchmark & Stammdaten laden, als CSV speichern02_risk_metric_calcu...Alle KPIs berechnen, als CSV speichern03_visualizationAlle CSVs laden, Visualisierungen erstellen
Visualisierungen (Notebook 3)
ChartTypBeschreibungKursverlaufLinienchartPreisentwicklung aller Aktien über 2 JahreSektorverteilungKuchendiagrammVerteilung nach SektorGeographischer BreakdownHorizontales BalkendiagrammAllokation nach Region in %Performance (absolut)Plotly TabelleReturns über verschiedene ZeiträumeAlphaBalkendiagrammAnnualisiertes Alpha pro TickerRolling VolatilitätLinienchart30-Tage Rolling VolatilitätSharpe RatioBalkendiagrammSharpe Ratio pro Ticker
Geographisches Mapping
Länder werden Regionen zugeordnet via region_map dict:

North America: United States, Canada, Mexico
Europe: Germany, France, United Kingdom, Switzerland, Netherlands
Asia: Japan, China, South Korea
Emerging Markets: India, Brazil, Taiwan
Other: alle nicht gemappten Länder (via .fillna("Other"))

Claude Verhaltensrichtlinien
Code Style

Code immer kompakt und modular schreiben
Keine hardgecodeten Werte wo vermeidbar
Funktionen nur wenn sie echten Mehrwert bringen
Variablen aus vorherigen Zellen werden direkt weiterverwendet, kein erneutes Laden

Schrittweise Vorgehen

Immer nur den explizit angefragten Schritt implementieren
Nicht vorausgreifen oder zusätzliche Metriken/Features hinzufügen ohne Anfrage
Bei Unklarheiten kurz nachfragen bevor Code geschrieben wird (z.B. Diagrammtyp)

Visualisierungen

Charts auf Englisch
Relative Zahlen (%) bevorzugt gegenüber absoluten Counts
Diagrammtyp immer kurz bestätigen wenn nicht eindeutig

Tech Stack

Nur pandas, numpy, plotly, yfinance verwenden
Keine externen Libraries vorschlagen die nicht im Stack sind

Nächste Schritte

03_visualization.ipynb – Visualisierungen fertigstellen
src/portfolio.py – OOP Klasse mit allen KPI Berechnungen
app.py – interaktives Streamlit Dashboard
GitHub – Projekt veröffentlichen

Installation
pip install -r requirements.txt
Usage
streamlit run app.py