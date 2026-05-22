# Financial Dashboard

Tableau de bord financier interactif pour l'analyse d'actifs (actions, crypto, ETF, indices).

## Fonctionnalites

- Suivi en temps reel de portefeuilles multi-actifs
- Analyse technique : moyennes mobiles, RSI, MACD, Bollinger
- Simulation DCA (Dollar Cost Averaging)
- Backtesting de strategies
- Matrice de correlation et analyse de drawdowns
- Scoring quantitatif et rendements mensuels
- Analyse sectorielle et macroeconomique

## Stack technique

- **Python** - Streamlit, Pandas, NumPy
- **Data** - yfinance (Yahoo Finance API)
- **Visualisation** - Plotly

## Installation et lancement

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run app.py
```
