# Financial Dashboard

Interactive financial dashboard for multi-asset analysis — equities, crypto, ETFs, indices and macro indicators.

Built as a personal project to explore quantitative finance concepts through hands-on development.

![Dashboard Overview](screenshots/overview.png)

## Features

### Portfolio & Market Analysis
- Real-time multi-asset portfolio tracking with customizable watchlists
- Sector rotation analysis with monthly heatmaps
- Macro dashboard covering VIX, yield curves, forex, and commodities

### Technical Analysis
- Moving averages (SMA/EMA), RSI, MACD, Bollinger Bands
- Screener with combined filters (RSI, Sharpe, volatility, drawdown)
- Quantitative scoring system (rated /20) based on Sharpe, volatility, drawdown and trend

### Risk & Valuation
- Sharpe and Sortino ratios, Value at Risk (VaR 95%/99%), Conditional VaR
- Maximum drawdown tracking and analysis
- Simplified DCF model (Free Cash Flow and Graham valuation)
- Analyst consensus integration (price targets, recommendations)

### Simulation
- DCA (Dollar Cost Averaging) backtesting
- Strategy backtester with customizable parameters
- Annual and monthly return heatmaps

![Technical Analysis](screenshots/technical.png)

## Tech Stack

| Layer | Tools |
|-------|-------|
| **Language** | Python |
| **Framework** | Streamlit |
| **Data** | yfinance (Yahoo Finance API) |
| **Visualization** | Plotly (interactive charts) |
| **Computation** | Pandas, NumPy |

## Getting Started

```bash
# Clone the repository
git clone https://github.com/Florian-KOVACEVIC/financial-dashboard.git
cd financial-dashboard

# Create virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Launch the app
python -m streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Disclaimer

This tool is for educational and personal use only. It does not constitute financial advice. Market data is provided by Yahoo Finance with potential delays.
