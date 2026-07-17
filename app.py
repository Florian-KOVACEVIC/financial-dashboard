"""
Financial Dashboard - Application Tableau de Bord Multi-Actifs
--------------------------------------------------------------
Auteur  : FloKov
Stack   : Streamlit · yfinance · Pandas · NumPy · Plotly
Usage   : streamlit run app.py  
"""
 
# Application tableau de bord financier
import json
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta
import calendar as cal_mod

st.set_page_config(page_title="Tableau de Bord Financier", layout="wide", page_icon="📈")

DEFAUT = {"TTWO"}

EVENEMENTS = [
    # ── Années 2000 ──────────────────────────────────────────
    {"date": "2000-03-10", "label": "Pic bulle dot-com",              "couleur": "#FF4444"},
    {"date": "2001-09-11", "label": "Attentats 11 septembre",         "couleur": "#FF4444"},
    {"date": "2002-07-01", "label": "Krach dot-com fond",             "couleur": "#FF8C00"},
    {"date": "2003-03-20", "label": "Guerre en Irak",                 "couleur": "#FF8C00"},
    # ── Crise financière 2008 ────────────────────────────────
    {"date": "2007-07-01", "label": "Crise subprimes",                "couleur": "#FF8C00"},
    {"date": "2008-09-15", "label": "Faillite Lehman Brothers",       "couleur": "#FF4444"},
    # ── Crise dette euro ─────────────────────────────────────
    {"date": "2010-05-01", "label": "Crise dette Grèce",              "couleur": "#FF8C00"},
    {"date": "2011-08-05", "label": "Dégradation USA (S&P)",          "couleur": "#FF8C00"},
    {"date": "2012-06-26", "label": "Draghi : Whatever it takes",     "couleur": "#FFD700"},
    # ── 2015–2019 ────────────────────────────────────────────
    {"date": "2015-08-24", "label": "Flash Crash Chine",              "couleur": "#FF8C00"},
    {"date": "2016-06-24", "label": "Brexit",                         "couleur": "#FFD700"},
    {"date": "2018-12-24", "label": "Krach Noël 2018",                "couleur": "#FF8C00"},
    # ── COVID ────────────────────────────────────────────────
    {"date": "2020-02-20", "label": "Krach COVID",                    "couleur": "#FF4444"},
    {"date": "2020-11-09", "label": "Vaccin Pfizer annoncé",          "couleur": "#FFD700"},
    # ── Guerre & inflation 2022 ──────────────────────────────
    {"date": "2022-02-24", "label": "Invasion Ukraine",               "couleur": "#FF4444"},
    {"date": "2022-06-15", "label": "Pic inflation / taux Fed",       "couleur": "#FF8C00"},
    # ── 2023–2025 ────────────────────────────────────────────
    {"date": "2023-03-10", "label": "Faillite SVB",                   "couleur": "#FF8C00"},
    {"date": "2024-08-05", "label": "Flash Crash Nikkei",             "couleur": "#FF8C00"},
    {"date": "2025-04-02", "label": "Tarifs douaniers Trump",         "couleur": "#FF4444"},
]

_SEUIL_JOURS = 90

def filtrer_evenements_proches(events, seuil_jours=_SEUIL_JOURS):
    """Garde un événement par tranche de seuil_jours pour éviter les labels collés."""
    result = []
    last_dt = None
    for ev in sorted(events, key=lambda x: x["date"]):
        dt = datetime.strptime(ev["date"], "%Y-%m-%d")
        if last_dt is None or (dt - last_dt).days >= seuil_jours:
            result.append(ev)
            last_dt = dt
    return result

    
# JS détection de l'ouverture/fermeture du volet latéral
st.html("""
<script>
(function() {
    const obs = new MutationObserver(() => {
        window.dispatchEvent(new Event('resize'));
    });
    const sidebar = document.querySelector('[data-testid="stSidebar"]');
    if (sidebar) obs.observe(sidebar, { attributes: true, attributeFilter: ['style', 'class'] });
    // Fallback : observe le body pour détecter l'ajout de la classe collapsed
    obs.observe(document.body, { attributes: true, subtree: true, attributeFilter: ['style', 'class'] });
})();
</script>
""")

TICKERS_APP = {
    "Actions":  ["NVDA", "AAPL", "MSFT", "GOOGL", "TSLA", "META", "AMZN"],
    "Crypto":   ["BTC-USD", "ETH-USD", "SOL-USD"],
    "Indices":  ["^GSPC", "^IXIC", "^FCHI", "^N225"],
}

# ════════════════════════════════════════════════════════════
#  PERSISTANCE TICKERS CUSTOM (JSON local)
# ════════════════════════════════════════════════════════════
TICKERS_JSON = "custom_tickers.json"
ALERTES_JSON = "alertes.json"

def charger_tickers_json() -> list:
    try:
        if os.path.exists(TICKERS_JSON):
            with open(TICKERS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [t for t in data if isinstance(t, str)]
    except Exception:
        pass
    return []

def sauvegarder_tickers_json(tickers: list):
    try:
        with open(TICKERS_JSON, "w", encoding="utf-8") as f:
            json.dump(tickers, f)
    except Exception:
        pass

def charger_alertes_json() -> dict:
    try:
        if os.path.exists(ALERTES_JSON):
            with open(ALERTES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}

def sauvegarder_alertes_json(alertes: dict):
    try:
        with open(ALERTES_JSON, "w", encoding="utf-8") as f:
            json.dump(alertes, f, indent=2)
    except Exception:
        pass

if "custom_tickers"   not in st.session_state:
    st.session_state.custom_tickers = charger_tickers_json()
if "custom_input_val" not in st.session_state:
    st.session_state.custom_input_val = ""
if "alertes" not in st.session_state:
    st.session_state.alertes = charger_alertes_json()
if "activated_tickers" not in st.session_state:
    st.session_state.activated_tickers = set()
if "deactivated_tickers" not in st.session_state:
    st.session_state.deactivated_tickers = set()


# ════════════════════════════════════════════════════════════
#  FONCTIONS DATA
# ════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def get_data_and_volume(tickers: tuple, debut: str, fin: str) -> tuple:
    """Télécharge close + volume en un seul appel yfinance. Retourne (df_close, df_volume)."""
    if not tickers:
        return pd.DataFrame(), pd.DataFrame()
    try:
        raw = yf.download(list(tickers), start=debut, end=fin,
                          auto_adjust=True, progress=False, group_by="ticker", threads=True)
        multi = isinstance(raw.columns, pd.MultiIndex)
        close = (raw.xs("Close", axis=1, level=1) if multi
                 else raw[["Close"]].rename(columns={"Close": tickers[0]}))
        volume = (raw.xs("Volume", axis=1, level=1) if multi
                  else raw[["Volume"]].rename(columns={"Volume": tickers[0]}))
        return close.dropna(how="all"), volume.dropna(how="all")
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_fiche(ticker: str) -> dict:
    try:
        tk   = yf.Ticker(ticker)
        info = tk.info
        # ── Consensus analyste ────────────────────────────────
        nb_achat     = info.get("numberOfAnalystOpinions")
        objectif_moy = info.get("targetMeanPrice")
        objectif_bas = info.get("targetLowPrice")
        objectif_haut= info.get("targetHighPrice")
        reco_raw     = info.get("recommendationKey", "")   # "buy","hold","sell","strong_buy"...
        RECO_LABELS  = {
            "strong_buy":  ("🟢 Achat fort",  "#2d9e5f"),
            "buy":         ("🟢 Achat",        "#2d9e5f"),
            "outperform":  ("🟢 Surperformance","#2d9e5f"),
            "hold":        ("🟡 Conserver",    "#FFD700"),
            "neutral":     ("🟡 Neutre",       "#FFD700"),
            "underperform":("🔴 Sous-perf",    "#e05252"),
            "sell":        ("🔴 Vendre",       "#e05252"),
            "strong_sell": ("🔴 Vente forte",  "#e05252"),
        }
        reco_label, reco_color = RECO_LABELS.get(reco_raw, ("—", "#888"))

        # ── Dates importantes ─────────────────────────────────
        # Prochain dividende ex-date
        ex_div_raw   = info.get("exDividendDate")
        ex_div_dt    = None
        if ex_div_raw:
            try: ex_div_dt = datetime.utcfromtimestamp(ex_div_raw).date()
            except Exception: pass

        # Prochaine publication de résultats
        earnings_dt  = None
        try:
            cal = tk.calendar
            if isinstance(cal, dict):
                e = cal.get("Earnings Date") or cal.get("earningsDate")
                if e:
                    earnings_dt = pd.to_datetime(e[0] if isinstance(e, list) else e).date()
            elif isinstance(cal, pd.DataFrame) and not cal.empty:
                if "Earnings Date" in cal.index:
                    earnings_dt = pd.to_datetime(cal.loc["Earnings Date"].iloc[0]).date()
        except Exception: pass

        return {
            "Nom":              info.get("longName") or info.get("shortName", ticker),
            "Secteur":          info.get("sector", "—"),
            "Industrie":        info.get("industry", "—"),
            "Pays":             info.get("country", "—"),
            "Capitalisation":   info.get("marketCap"),
            "Prix actuel":      info.get("currentPrice") or info.get("regularMarketPrice"),
            "Variation jour":   info.get("regularMarketChangePercent"),
            "P/E ratio":        info.get("trailingPE"),
            "P/E forward":      info.get("forwardPE"),
            "Dividende %":      info.get("dividendYield"),
            "52w Haut":         info.get("fiftyTwoWeekHigh"),
            "52w Bas":          info.get("fiftyTwoWeekLow"),
            "Devise":           info.get("currency", ""),
            # Consensus
            "Nb analystes":     nb_achat,
            "Objectif moyen":   objectif_moy,
            "Objectif bas":     objectif_bas,
            "Objectif haut":    objectif_haut,
            "Reco label":       reco_label,
            "Reco color":       reco_color,
            # Dates
            "Ex-dividende":     ex_div_dt,
            "Résultats":        earnings_dt,
            # ── Champs DCF ────────────────────────────────────
            "FCF":              info.get("freeCashflow"),           # Free Cash Flow annuel
            "FCF_per_share":    info.get("freeCashflow") / info.get("sharesOutstanding", 1)
                                if info.get("freeCashflow") and info.get("sharesOutstanding") else None,
            "EPS":              info.get("trailingEps"),            # Bénéfice par action (trailing)
            "EPS_forward":      info.get("forwardEps"),             # BPA prévisionnel
            "Croissance_BPA":   info.get("earningsGrowth"),         # Croissance BPA (décimal)
            "Croissance_rev":   info.get("revenueGrowth"),          # Croissance CA
            "Beta":             info.get("beta"),                   # Risque vs marché
            "Shares":           info.get("sharesOutstanding"),
            "Total_debt":       info.get("totalDebt"),
            "Cash":             info.get("totalCash"),
            "EBITDA":           info.get("ebitda"),
            "PB_ratio":         info.get("priceToBook"),
            "PS_ratio":         info.get("priceToSalesTrailing12Months"),
            "ROE":              info.get("returnOnEquity"),
            "ROA":              info.get("returnOnAssets"),
            "Marge_nette":      info.get("profitMargins"),
            "Quick_ratio":      info.get("quickRatio"),
        }
    except Exception: return {}

@st.cache_data(ttl=600, show_spinner=False)
def get_news(ticker: str) -> list:
    try:
        raw = yf.Ticker(ticker).news or []
        result = []
        for item in raw[:15]:
            content = item.get("content", {})
            title   = content.get("title", "") or item.get("title", "")
            summary = content.get("summary", "") or item.get("summary", "")
            pub_raw = content.get("pubDate", "") or item.get("providerPublishTime", "")
            click_url = content.get("clickThroughUrl", {})
            url = (click_url.get("url", "") if isinstance(click_url, dict) else "") \
                  or content.get("canonicalUrl", {}).get("url", "") \
                  or item.get("link", "")
            provider = content.get("provider", {})
            source   = (provider.get("displayName", "") if isinstance(provider, dict) else "") \
                       or item.get("publisher", "")
            thumb = ""
            tm = content.get("thumbnail", {})
            if isinstance(tm, dict):
                resolutions = tm.get("resolutions", [])
                if resolutions:
                    thumb = resolutions[0].get("url", "")
            pub_dt = None
            if isinstance(pub_raw, str) and pub_raw:
                try: pub_dt = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
                except Exception: pass
            elif isinstance(pub_raw, (int, float)) and pub_raw:
                try: pub_dt = datetime.utcfromtimestamp(pub_raw)
                except Exception: pass
            if title:
                result.append({"title": title, "summary": summary, "url": url,
                                "source": source, "thumb": thumb, "date": pub_dt})
        return result
    except Exception:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def verifier_ticker(ticker: str) -> bool:
    try: return not yf.download(ticker, period="5d", progress=False).empty
    except Exception: return False

@st.cache_data(ttl=600, show_spinner=False)
def rechercher_tickers(query: str) -> list:
    try:
        quotes = yf.Search(query, max_results=10).quotes
        return [{"symbol": q.get("symbol",""), "name": q.get("longname") or q.get("shortname",""),
                 "exchange": q.get("exchange",""), "type": q.get("quoteType","")}
                for q in (quotes or []) if q.get("symbol")]
    except Exception: return []

@st.cache_data(ttl=900, show_spinner=False)
def get_macro_quote(ticker: str) -> dict:
    """Retourne prix actuel + variation 1j + historique 1 an pour un ticker macro."""
    try:
        tk  = yf.Ticker(ticker)
        inf = tk.info
        hist = tk.history(period="1y", interval="1d")["Close"].dropna()
        prix    = inf.get("regularMarketPrice") or inf.get("currentPrice") or (float(hist.iloc[-1]) if not hist.empty else None)
        prev    = inf.get("regularMarketPreviousClose")
        var_pct = ((prix - prev) / prev * 100) if prix and prev else None
        var_52  = ((prix - float(hist.iloc[0])) / float(hist.iloc[0]) * 100) if prix and not hist.empty else None
        return {"prix": prix, "var_pct": var_pct, "var_52": var_52, "hist": hist}
    except Exception:
        return {"prix": None, "var_pct": None, "var_52": None, "hist": pd.Series(dtype=float)}

# ════════════════════════════════════════════════════════════
#  CALENDRIER ÉCONOMIQUE — GÉNÉRATION DYNAMIQUE
# ════════════════════════════════════════════════════════════

# Dates FOMC publiées par la Fed (à mettre à jour 1×/an depuis federalreserve.gov/monetarypolicy/fomccalendars.htm)
_FOMC_DATES = {
    2025: ["01-29", "03-19", "05-07", "06-18", "07-30", "09-17", "10-29", "12-17"],
    2026: ["01-28", "03-18", "05-06", "06-17", "07-29", "09-16", "10-28", "12-16"],
}

# Dates BCE publiées par la BCE (à mettre à jour 1×/an depuis ecb.europa.eu)
_BCE_DATES = {
    2025: ["01-30", "03-06", "04-17", "06-05", "07-17", "09-11", "10-30", "12-18"],
    2026: ["01-22", "03-05", "04-16", "06-10", "07-16", "09-10", "10-29", "12-17"],
}

def _nieme_jour_semaine(annee, mois, jour_semaine, n):
    """Retourne la date du n-ième jour_semaine (0=lundi, 4=vendredi) du mois."""
    premier = date(annee, mois, 1)
    decalage = (jour_semaine - premier.weekday()) % 7
    d = premier + timedelta(days=decalage + 7 * (n - 1))
    return d if d.month == mois else None

def _dernier_jour_semaine(annee, mois, jour_semaine):
    """Retourne la date du dernier jour_semaine du mois."""
    dernier_jour = cal_mod.monthrange(annee, mois)[1]
    d = date(annee, mois, dernier_jour)
    while d.weekday() != jour_semaine:
        d -= timedelta(days=1)
    return d

def generer_calendrier_macro(horizon_mois=6):
    """Génère automatiquement le calendrier économique pour les prochains mois."""
    today = date.today()
    debut = today - timedelta(days=30)
    fin = today + timedelta(days=horizon_mois * 31)
    events = []

    # ── FOMC ──────────────────────────────────────────────────
    for annee in range(debut.year, fin.year + 1):
        for md in _FOMC_DATES.get(annee, []):
            d = date.fromisoformat(f"{annee}-{md}")
            if debut <= d <= fin:
                events.append({
                    "date": d.isoformat(), "heure": "19h00", "zone": "🇺🇸",
                    "evenement": "Réunion FOMC (Fed)",
                    "categorie": "Banque centrale", "impact": "🔴 Élevé",
                    "description": "Décision sur les taux directeurs américains. Conférence de presse du président de la Fed.",
                    "historique": "En moyenne ±1,2 % sur le S&P 500 le jour J. Volatilité accrue sur USD, obligations et actions tech.",
                    "actifs_cles": ["^GSPC", "^IXIC", "GLD"],
                })

    # ── BCE ───────────────────────────────────────────────────
    for annee in range(debut.year, fin.year + 1):
        for md in _BCE_DATES.get(annee, []):
            d = date.fromisoformat(f"{annee}-{md}")
            if debut <= d <= fin:
                events.append({
                    "date": d.isoformat(), "heure": "14h15", "zone": "🇪🇺",
                    "evenement": "Réunion BCE",
                    "categorie": "Banque centrale", "impact": "🔴 Élevé",
                    "description": "Décision de taux de la Banque Centrale Européenne.",
                    "historique": "Impact moyen ±0,8 % sur l'Euro Stoxx 50. Forte réaction sur EUR/USD.",
                    "actifs_cles": ["^FCHI", "EURUSD=X"],
                })

    # ── NFP — 1er vendredi de chaque mois ─────────────────────
    for annee in range(debut.year, fin.year + 1):
        for mois in range(1, 13):
            d = _nieme_jour_semaine(annee, mois, 4, 1)  # 4 = vendredi
            if d and debut <= d <= fin:
                mois_ref = (mois - 2) % 12 + 1
                events.append({
                    "date": d.isoformat(), "heure": "14h30", "zone": "🇺🇸",
                    "evenement": f"NFP (Non-Farm Payrolls) — {cal_mod.month_abbr[mois_ref]}",
                    "categorie": "Emploi", "impact": "🔴 Élevé",
                    "description": "Rapport mensuel sur l'emploi US. Créations de postes, taux de chômage, salaires horaires.",
                    "historique": "2ème publication la plus impactante après la Fed. Surprise >50k → USD fort.",
                    "actifs_cles": ["^GSPC", "EURUSD=X", "GLD"],
                })

    # ── CPI — ~2ème mercredi de chaque mois ───────────────────
    for annee in range(debut.year, fin.year + 1):
        for mois in range(1, 13):
            d = _nieme_jour_semaine(annee, mois, 2, 2)  # 2 = mercredi, 2ème
            if d and debut <= d <= fin:
                mois_ref = (mois - 2) % 12 + 1
                events.append({
                    "date": d.isoformat(), "heure": "14h30", "zone": "🇺🇸",
                    "evenement": f"CPI USA ({cal_mod.month_abbr[mois_ref]})",
                    "categorie": "Inflation", "impact": "🔴 Élevé",
                    "description": "Indice des prix à la consommation américain. Indicateur clé pour la trajectoire des taux Fed.",
                    "historique": "Surprises à la hausse → chute du Nasdaq (-1,5 % moy.). Surprises à la baisse → rally obligataire.",
                    "actifs_cles": ["^GSPC", "^IXIC", "GLD", "BTC-USD"],
                })

    # ── PPI — lendemain du CPI (jeudi) ────────────────────────
    for annee in range(debut.year, fin.year + 1):
        for mois in range(1, 13):
            d_cpi = _nieme_jour_semaine(annee, mois, 2, 2)
            if d_cpi:
                d = d_cpi + timedelta(days=1)  # jeudi
                if debut <= d <= fin:
                    mois_ref = (mois - 2) % 12 + 1
                    events.append({
                        "date": d.isoformat(), "heure": "14h30", "zone": "🇺🇸",
                        "evenement": f"PPI USA ({cal_mod.month_abbr[mois_ref]})",
                        "categorie": "Inflation", "impact": "🟠 Moyen",
                        "description": "Prix à la production américains. Indicateur avancé des pressions inflationnistes.",
                        "historique": "Impact modéré, surtout utilisé pour affiner les prévisions CPI du mois suivant.",
                        "actifs_cles": ["^GSPC", "GLD"],
                    })

    # ── PCE Core — dernier vendredi du mois ───────────────────
    for annee in range(debut.year, fin.year + 1):
        for mois in range(1, 13):
            d = _dernier_jour_semaine(annee, mois, 4)  # 4 = vendredi
            if debut <= d <= fin:
                mois_ref = (mois - 2) % 12 + 1
                events.append({
                    "date": d.isoformat(), "heure": "14h30", "zone": "🇺🇸",
                    "evenement": f"PCE Core ({cal_mod.month_abbr[mois_ref]})",
                    "categorie": "Inflation", "impact": "🔴 Élevé",
                    "description": "Indicateur d'inflation privilégié par la Fed (Personal Consumption Expenditures).",
                    "historique": "Très suivi par les marchés obligataires. Surprise → réévaluation rapide des anticipations de taux.",
                    "actifs_cles": ["^GSPC", "GLD", "BTC-USD"],
                })

    # ── PIB US — dernière semaine des mois de publication ─────
    for annee in range(debut.year, fin.year + 1):
        for mois, trimestre, revision in [
            (1, "T4", "1ère estim."), (2, "T4", "2ème estim."), (3, "T4", "3ème estim."),
            (4, "T1", "1ère estim."), (5, "T1", "2ème estim."), (6, "T1", "3ème estim."),
            (7, "T2", "1ère estim."), (8, "T2", "2ème estim."), (9, "T2", "3ème estim."),
            (10, "T3", "1ère estim."), (11, "T3", "2ème estim."), (12, "T3", "3ème estim."),
        ]:
            d = _dernier_jour_semaine(annee, mois, 3)  # dernier jeudi
            if debut <= d <= fin:
                impact = "🔴 Élevé" if "1ère" in revision else "🟠 Moyen"
                events.append({
                    "date": d.isoformat(), "heure": "14h30", "zone": "🇺🇸",
                    "evenement": f"PIB USA {trimestre} {annee if '1ère' in revision else annee} ({revision})",
                    "categorie": "Croissance", "impact": impact,
                    "description": f"{revision} du PIB américain du {trimestre}.",
                    "historique": "Surprise négative → forte réaction obligataire et baisse USD.",
                    "actifs_cles": ["^GSPC", "^IXIC", "GLD"],
                })

    events.sort(key=lambda x: x["date"])
    return events


@st.cache_data(ttl=86400, show_spinner=False)
def get_earnings_calendar(tickers: tuple) -> list:
    """Récupère les prochaines dates de résultats via yfinance pour les tickers donnés."""
    events = []
    for tk_str in tickers:
        try:
            tk = yf.Ticker(tk_str)
            cal = tk.calendar
            earnings_dt = None
            if isinstance(cal, dict):
                e = cal.get("Earnings Date") or cal.get("earningsDate")
                if e:
                    earnings_dt = pd.to_datetime(e[0] if isinstance(e, list) else e).date()
            elif isinstance(cal, pd.DataFrame) and not cal.empty:
                if "Earnings Date" in cal.index:
                    earnings_dt = pd.to_datetime(cal.loc["Earnings Date"].iloc[0]).date()
            if earnings_dt and earnings_dt >= date.today() - timedelta(days=30):
                nom = tk.info.get("longName") or tk.info.get("shortName") or tk_str
                events.append({
                    "date": earnings_dt.isoformat(),
                    "heure": "Après clôture",
                    "zone": "🇺🇸",
                    "evenement": f"Résultats {nom} ({tk_str})",
                    "categorie": "Résultats",
                    "impact": "🔴 Élevé",
                    "description": f"Publication des résultats trimestriels de {nom}.",
                    "historique": f"Forte volatilité attendue sur {tk_str} en after-hours.",
                    "actifs_cles": [tk_str, "^IXIC"],
                })
        except Exception:
            pass
    events.sort(key=lambda x: x["date"])
    return events


# Catalogue complet des instruments macro
MACRO_CATALOGUE = {
    "🧭 Indices de peur & sentiment": [
        {"ticker": "^VIX",   "label": "VIX (peur US)",        "unite": "",     "inverse": True,
         "info": "Volatilité implicite du S&P 500. > 30 = panique, < 15 = complaisance."},
        {"ticker": "^VXN",   "label": "VXN (peur Nasdaq)",     "unite": "",     "inverse": True,
         "info": "Équivalent VIX pour le Nasdaq 100."},
        {"ticker": "^MOVE",  "label": "MOVE (peur obligations)","unite": "",    "inverse": True,
         "info": "Volatilité implicite des bons du Trésor US. Souvent précurseur du VIX."},
    ],
    "📈 Actions — Indices majeurs": [
        {"ticker": "^GSPC",  "label": "S&P 500",               "unite": "pts",  "inverse": False,
         "info": "Les 500 plus grandes capitalisations américaines. Référence mondiale."},
        {"ticker": "^IXIC",  "label": "Nasdaq Composite",       "unite": "pts",  "inverse": False,
         "info": "Indice tech US. Très sensible aux taux d'intérêt."},
        {"ticker": "^DJI",   "label": "Dow Jones",              "unite": "pts",  "inverse": False,
         "info": "30 grandes entreprises US. Plus conservateur que le S&P 500."},
        {"ticker": "^FCHI",  "label": "CAC 40",                 "unite": "pts",  "inverse": False,
         "info": "40 premières capitalisations françaises."},
        {"ticker": "^GDAXI", "label": "DAX 40",                 "unite": "pts",  "inverse": False,
         "info": "30 plus grandes capitalisations allemandes."},
        {"ticker": "^STOXX50E","label": "Euro Stoxx 50",        "unite": "pts",  "inverse": False,
         "info": "50 leaders européens de la zone euro."},
        {"ticker": "^N225",  "label": "Nikkei 225",             "unite": "pts",  "inverse": False,
         "info": "225 plus grandes entreprises japonaises."},
        {"ticker": "^HSI",   "label": "Hang Seng",              "unite": "pts",  "inverse": False,
         "info": "Indice de Hong Kong, baromètre de l'Asie."},
    ],
    "💱 Forex — Grandes paires": [
        {"ticker": "EURUSD=X","label": "EUR/USD",               "unite": "",     "inverse": False,
         "info": "Paire la plus échangée au monde. Indicateur de l'appétit pour le risque euro vs dollar."},
        {"ticker": "GBPUSD=X","label": "GBP/USD",               "unite": "",     "inverse": False,
         "info": "Livre sterling vs dollar. Très sensible aux données UK et Brexit."},
        {"ticker": "USDJPY=X","label": "USD/JPY",               "unite": "",     "inverse": False,
         "info": "Yen = valeur refuge. Monte en période de stress, baisse quand tout va bien."},
        {"ticker": "USDCHF=X","label": "USD/CHF",               "unite": "",     "inverse": False,
         "info": "Franc suisse = valeur refuge. Baisse du CHF = appétit pour le risque."},
        {"ticker": "DX-Y.NYB","label": "Dollar Index (DXY)",    "unite": "",     "inverse": False,
         "info": "Force du dollar vs panier de 6 devises. Détermine les prix des matières premières."},
        {"ticker": "AUDUSD=X","label": "AUD/USD",               "unite": "",     "inverse": False,
         "info": "Dollar australien = proxy des matières premières et de la Chine."},
    ],
    "🛢️ Matières premières": [
        {"ticker": "GC=F",   "label": "Or (Gold)",              "unite": "$/oz", "inverse": False,
         "info": "Valeur refuge absolue. Monte quand l'incertitude ou l'inflation augmente."},
        {"ticker": "SI=F",   "label": "Argent (Silver)",        "unite": "$/oz", "inverse": False,
         "info": "À la fois valeur refuge et métal industriel (solaire, électronique)."},
        {"ticker": "CL=F",   "label": "Pétrole WTI",            "unite": "$/b",  "inverse": False,
         "info": "Référence pétrole américain. Baromètre de l'activité économique mondiale."},
        {"ticker": "BZ=F",   "label": "Pétrole Brent",          "unite": "$/b",  "inverse": False,
         "info": "Référence pétrole européen. Plus représentatif du marché mondial."},
        {"ticker": "NG=F",   "label": "Gaz naturel",            "unite": "$/MBTU","inverse": False,
         "info": "Très volatile. Très lié aux stocks US, météo et géopolitique."},
        {"ticker": "HG=F",   "label": "Cuivre",                 "unite": "$/lb", "inverse": False,
         "info": "Surnommé 'Dr Copper' — excellent indicateur avancé de la croissance mondiale."},
        {"ticker": "ZW=F",   "label": "Blé",                    "unite": "cts/bu","inverse": False,
         "info": "Indicateur de tensions géopolitiques et de sécurité alimentaire mondiale."},
    ],
    "🏦 Taux & Obligations": [
        {"ticker": "^TNX",   "label": "Taux 10 ans US",         "unite": "%",    "inverse": False,
         "info": "Référence mondiale. Monte = conditions financières se resserrent, dollar se renforce."},
        {"ticker": "^TYX",   "label": "Taux 30 ans US",         "unite": "%",    "inverse": False,
         "info": "Taux long terme US. Reflète les anticipations d'inflation sur le très long terme."},
        {"ticker": "^IRX",   "label": "Taux 3 mois US (T-Bill)","unite": "%",    "inverse": False,
         "info": "Proxy du taux directeur de la Fed. Quand > 10 ans = courbe inversée = signal de récession."},
        {"ticker": "TLT",    "label": "ETF Obligations 20 ans", "unite": "$",    "inverse": True,
         "info": "Prix inversé au taux long. Baisse quand les taux montent."},
        {"ticker": "LQD",    "label": "ETF Crédit Investment Grade","unite": "$","inverse": False,
         "info": "Santé du crédit des entreprises solides. Baisse = stress sur les marchés du crédit."},
        {"ticker": "HYG",    "label": "ETF High Yield (Junk)",  "unite": "$",    "inverse": False,
         "info": "Obligations risquées. Baisse agressive = signal d'alerte sur l'économie réelle."},
    ],
    "🔑 Indicateurs avancés": [
        {"ticker": "^GSPC",  "label": "S&P 500 (référence)",    "unite": "pts",  "inverse": False,
         "info": "Rappel de référence pour les corrélations ci-dessous."},
        {"ticker": "BTC-USD","label": "Bitcoin",                 "unite": "$",    "inverse": False,
         "info": "Actif très corrélé au Nasdaq en période de stress. Indicateur d'appétit spéculatif."},
        {"ticker": "XLE",    "label": "ETF Énergie (XLE)",       "unite": "$",    "inverse": False,
         "info": "Secteur énergie US. Corrélé au pétrole."},
        {"ticker": "XLF",    "label": "ETF Finance (XLF)",       "unite": "$",    "inverse": False,
         "info": "Banques US. Monte quand les taux montent et l'économie va bien."},
        {"ticker": "XLU",    "label": "ETF Utilities (XLU)",     "unite": "$",    "inverse": False,
         "info": "Secteur défensif. Monte quand les investisseurs fuient le risque."},
        {"ticker": "GLD",    "label": "ETF Or (GLD)",            "unite": "$",    "inverse": False,
         "info": "Proxy de l'or physique. Valeur refuge contre l'inflation et l'incertitude."},
    ],
}


# ════════════════════════════════════════════════════════════
#  FONCTIONS CALCUL
# ════════════════════════════════════════════════════════════
def base100(df):
    result = {}
    for col in df.columns:
        s = df[col].dropna()
        if len(s): result[col] = (df[col] / s.iloc[0]) * 100
    return pd.DataFrame(result)

def calcul_volatilite(df):
    return (df.pct_change().dropna().std() * np.sqrt(252) * 100).round(2)

def calcul_drawdown_max(df):
    result = {}
    for col in df.columns:
        s = df[col].dropna()
        result[col] = round(((s - s.cummax()) / s.cummax() * 100).min(), 2)
    return pd.Series(result)

def calcul_bollinger(serie, fenetre=20):
    ma = serie.rolling(fenetre).mean()
    std = serie.rolling(fenetre).std()
    return ma, ma + 2*std, ma - 2*std

def calcul_rsi(serie, periode=14):
    delta = serie.diff()
    gain  = delta.clip(lower=0).rolling(periode).mean()
    perte = (-delta.clip(upper=0)).rolling(periode).mean()
    rs    = gain / perte.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calcul_macd(serie, rapide=12, lent=26, signal=9):
    ema_r  = serie.ewm(span=rapide, adjust=False).mean()
    ema_l  = serie.ewm(span=lent,   adjust=False).mean()
    macd   = ema_r - ema_l
    sig    = macd.ewm(span=signal,  adjust=False).mean()
    histo  = macd - sig
    return macd, sig, histo

def calcul_score_global(df, rf=0.03):
    """
    Score global /20 par actif, combinant 4 critères financiers :
      - Sharpe   (40%) : rendement ajusté du risque
      - Volatilité (25%) : pénalise l'instabilité excessive
      - Drawdown  (25%) : pénalise les chutes profondes
      - Tendance  (10%) : performance récente 6 mois vs 1 an
    Chaque critère est noté de 0 à 5, puis pondéré.
    """
    r       = df.pct_change().dropna()
    sharpes = ((r - rf/252).mean() / r.std() * np.sqrt(252))
    vols    = r.std() * np.sqrt(252) * 100
    scores  = {}
    details = {}

    for t in df.columns:
        s = df[t].dropna()
        if len(s) < 30:
            continue

        # ── Sharpe (0–5) ─────────────────────────────────────
        sh = float(sharpes.get(t, 0))
        if   sh >= 1.5: s_sharpe = 5.0
        elif sh >= 1.0: s_sharpe = 4.0
        elif sh >= 0.6: s_sharpe = 3.0
        elif sh >= 0.2: s_sharpe = 2.0
        elif sh >= 0.0: s_sharpe = 1.0
        else:           s_sharpe = 0.0

        # ── Volatilité (0–5) — moins c'est mieux ────────────
        vol = float(vols.get(t, 999))
        if   vol < 15:  s_vol = 5.0
        elif vol < 25:  s_vol = 4.0
        elif vol < 40:  s_vol = 3.0
        elif vol < 60:  s_vol = 2.0
        elif vol < 90:  s_vol = 1.0
        else:           s_vol = 0.0

        # ── Drawdown max (0–5) — moins c'est mieux ───────────
        dd = float(((s - s.cummax()) / s.cummax() * 100).min())
        if   dd > -8:   s_dd = 5.0
        elif dd > -15:  s_dd = 4.0
        elif dd > -25:  s_dd = 3.0
        elif dd > -40:  s_dd = 2.0
        elif dd > -60:  s_dd = 1.0
        else:           s_dd = 0.0

        # ── Tendance 6 mois (0–5) ────────────────────────────
        n6  = min(126, len(s)-1)
        n12 = min(252, len(s)-1)
        perf6  = (s.iloc[-1] / s.iloc[-n6]  - 1) * 100 if n6  > 0 else 0
        perf12 = (s.iloc[-1] / s.iloc[-n12] - 1) * 100 if n12 > 0 else 0
        tendance = (perf6 + perf12) / 2
        if   tendance > 25:  s_tend = 5.0
        elif tendance > 10:  s_tend = 4.0
        elif tendance > 0:   s_tend = 3.0
        elif tendance > -10: s_tend = 2.0
        elif tendance > -25: s_tend = 1.0
        else:                s_tend = 0.0

        # ── Score pondéré /20 ────────────────────────────────
        score_brut = (s_sharpe * 0.40 + s_vol * 0.25 + s_dd * 0.25 + s_tend * 0.10)
        score_20   = round(score_brut * 4, 1)   # max = 5 × 4 = 20

        scores[t]  = score_20
        details[t] = {
            "sharpe":    round(sh, 2),
            "s_sharpe":  s_sharpe,
            "vol":       round(vol, 1),
            "s_vol":     s_vol,
            "dd":        round(dd, 1),
            "s_dd":      s_dd,
            "tendance":  round(tendance, 1),
            "s_tend":    s_tend,
            "score":     score_20,
        }
    return scores, details

def calcul_sharpe(df, rf=0.03):
    r = df.pct_change().dropna()
    return ((r - rf/252).mean() / r.std() * np.sqrt(252)).round(2)

def calcul_rendements_annuels(df):
    r = df.resample("YE").last().pct_change().dropna() * 100
    r.index = r.index.year
    return r.round(1)

def calcul_meilleur_pire_mois(df):
    dm = df.resample("ME").last().pct_change().dropna() * 100
    result = {}
    for col in dm.columns:
        s = dm[col].dropna()
        if not len(s): continue
        result[col] = {"meilleur_val": round(s.max(),1), "meilleur_date": s.idxmax().strftime("%b %Y"),
                       "pire_val":     round(s.min(),1), "pire_date":     s.idxmin().strftime("%b %Y")}
    return result

def fmt_cap(v):
    if v is None: return "—"
    if v >= 1e12: return f"{v/1e12:.2f} T$"
    if v >= 1e9:  return f"{v/1e9:.1f} Md$"
    if v >= 1e6:  return f"{v/1e6:.1f} M$"
    return str(v)

def ajouter_ticker(ticker: str):
    ticker = ticker.strip().upper()
    if not ticker: return
    if ticker in st.session_state.custom_tickers:
        # 2e passage après rerun (champ encore rempli) → silence total
        if st.session_state.get("_last_added") == ticker:
            return
        st.session_state._add_msg = ("warning", f"⚠️ {ticker} est déjà dans la liste.")
        return
    with st.spinner(f"Vérification {ticker}..."):
        if verifier_ticker(ticker):
            st.session_state.custom_tickers.append(ticker)
            sauvegarder_tickers_json(st.session_state.custom_tickers)
            st.session_state._add_msg    = ("success", f"✅ {ticker} ajouté !")
            st.session_state._last_added = ticker
        else:
            st.session_state._add_msg    = ("error", f"❌ {ticker} introuvable sur Yahoo Finance.")
            st.session_state._last_added = None

TYPE_LABELS = {
    "EQUITY": "Action", "ETF": "ETF", "MUTUALFUND": "Fonds",
    "CRYPTOCURRENCY": "Crypto", "INDEX": "Indice",
    "FUTURE": "Future", "CURRENCY": "Devise",
}


# ════════════════════════════════════════════════════════════
#  GRAPHIQUE PRINCIPAL
# ════════════════════════════════════════════════════════════
def tracer_graphique_principal(affichage, df_raw, df_vol, echelle_log,
                                show_volume, show_rsi, show_macd,
                                evenements_affiches, date_debut):
    # Calcul des sous-graphes nécessaires
    ticker_tech = affichage.columns[0].split(" ")[0]  # premier actif (sans suffixe MA/BB)
    # Récupère la série prix brute du premier actif pour RSI/MACD
    prix_raw = df_raw[ticker_tech].dropna() if ticker_tech in df_raw.columns else pd.Series(dtype=float)

    rsi_serie   = calcul_rsi(prix_raw) if show_rsi and not prix_raw.empty else None
    macd_l, sig_l, histo_l = (calcul_macd(prix_raw) if show_macd and not prix_raw.empty
                               else (None, None, None))

    # Construction du layout avec subplots
    n_sous = sum([show_volume, show_rsi, show_macd])
    if n_sous == 0:
        fig = go.Figure()
        row_main = None
    else:
        hauteurs = [0.55] + [round(0.45 / n_sous, 2)] * n_sous
        specs    = [[{"secondary_y": False}]] * (1 + n_sous)
        fig = make_subplots(rows=1 + n_sous, cols=1, shared_xaxes=True,
                            row_heights=hauteurs, vertical_spacing=0.03,
                            specs=specs)
        row_main = 1

    def add(trace, row=None):
        if row is None: fig.add_trace(trace)
        else:           fig.add_trace(trace, row=row, col=1)

    # ── Courbes principales ───────────────────────────────────
    for col in affichage.columns:
        is_ma = "MA50" in col or "MA200" in col
        is_bb = "BB" in col
        trace = go.Scatter(x=affichage.index, y=affichage[col], name=col, mode="lines",
                           line=dict(width=1.5 if (is_ma or is_bb) else 2,
                                     dash="dash" if is_ma else ("dot" if is_bb else "solid")),
                           opacity=0.7 if (is_ma or is_bb) else 1.0)
        add(trace, row_main)

    # ── Événements ───────────────────────────────────────────
    for ev in evenements_affiches:
        ev_dt = datetime.strptime(ev["date"], "%Y-%m-%d")
        if ev_dt >= datetime.combine(date_debut, datetime.min.time()):
            fig.add_vline(x=ev["date"], line_color=ev["couleur"], line_width=1.5, line_dash="dot")
            fig.add_annotation(x=ev["date"], y=1.02, yref="paper", text=ev["label"],
                               showarrow=False, font=dict(size=9, color=ev["couleur"]),
                               textangle=-45, xanchor="left")

    # ── Sous-graphes dynamiques ───────────────────────────────
    row_idx = 2
    ax_sous = {}  # pour configurer les axes

    if show_volume and not df_vol.empty:
        for col in df_vol.columns:
            fig.add_trace(go.Bar(x=df_vol.index, y=df_vol[col], name=f"Vol {col}",
                                 opacity=0.4, showlegend=False,
                                 marker_color="rgba(100,160,255,0.5)"), row=row_idx, col=1)
        ax_sous[f"yaxis{row_idx}"] = dict(showgrid=False, tickformat=".2s", title_text="Volume")
        row_idx += 1

    if show_rsi and rsi_serie is not None:
        fig.add_trace(go.Scatter(x=rsi_serie.index, y=rsi_serie.values,
                                 name="RSI(14)", mode="lines",
                                 line=dict(width=1.5, color="#FFD700"),
                                 showlegend=True), row=row_idx, col=1)
        # Zones sur-acheté / sur-vendu
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(224,82,82,0.08)",
                      line_width=0, row=row_idx, col=1)
        fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(45,158,95,0.08)",
                      line_width=0, row=row_idx, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="rgba(224,82,82,0.4)",
                      line_width=1, row=row_idx, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="rgba(45,158,95,0.4)",
                      line_width=1, row=row_idx, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="rgba(255,255,255,0.15)",
                      line_width=1, row=row_idx, col=1)
        ax_sous[f"yaxis{row_idx}"] = dict(showgrid=False, range=[0, 100],
                                          tickvals=[30, 50, 70], title_text="RSI")
        row_idx += 1

    if show_macd and macd_l is not None:
        colors_histo = ["#2d9e5f" if v >= 0 else "#e05252" for v in histo_l.fillna(0)]
        fig.add_trace(go.Bar(x=histo_l.index, y=histo_l.values,
                             name="Histogramme MACD", marker_color=colors_histo,
                             opacity=0.7, showlegend=True), row=row_idx, col=1)
        fig.add_trace(go.Scatter(x=macd_l.index, y=macd_l.values,
                                 name="MACD", mode="lines",
                                 line=dict(width=1.5, color="#00D4AA")), row=row_idx, col=1)
        fig.add_trace(go.Scatter(x=sig_l.index, y=sig_l.values,
                                 name="Signal MACD", mode="lines",
                                 line=dict(width=1.2, color="#FF8C00", dash="dash")), row=row_idx, col=1)
        fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.2)",
                      line_width=1, row=row_idx, col=1)
        ax_sous[f"yaxis{row_idx}"] = dict(showgrid=False, title_text="MACD")
        row_idx += 1

    # ── Layout global ─────────────────────────────────────────
    total_h = 520 + n_sous * 120
    layout = dict(
        height=total_h, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FAFAFA"),
    )
    ax_std = dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)",
                  tickformat="%Y", dtick="M12", ticklabelmode="period")
    ay_std = dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)",
                  type="log" if echelle_log else "linear", tickformat=".0f")

    if n_sous == 0:
        layout.update(xaxis=ax_std, yaxis=ay_std)
    else:
        layout["xaxis"]  = ax_std
        layout["yaxis"]  = ay_std
        # axes sous-graphes
        for last_row in range(2, row_idx):
            xk = f"xaxis{last_row}" if last_row > 1 else "xaxis"
            layout[xk] = dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                               tickformat="%Y", dtick="M12")
        layout.update(ax_sous)

    fig.update_layout(**layout)
    return fig


# ════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════
selection = []
with st.sidebar:
    st.header("Paramètres")
    st.subheader("Période")
    date_debut = st.date_input("Date de début", value=datetime(2016, 1, 1),
                               min_value=datetime(2000, 1, 1), max_value=date.today())
    date_fin = date.today()
    st.divider()

    st.subheader("Graphique")
    echelle_log    = st.toggle("Échelle logarithmique", value=False,
        help="En échelle normale, une hausse de +1000€ prend autant de place qu'elle parte de 100€ ou 10 000€.\n\n"
             "En échelle log, c'est le % de variation qui compte : +10% occupe toujours la même hauteur.\n\n"
             "👉 Utile pour comparer des actifs très différents sur le long terme.")
    show_ma50      = st.toggle("MA50",  value=False,
        help="Moyenne mobile sur les 50 derniers jours.\n\n"
             "• Prix au-dessus → tendance haussière\n• Prix en dessous → tendance baissière\n\n"
             "👉 Utilisée pour décider d'acheter ou vendre à court terme.")
    show_ma200     = st.toggle("MA200", value=False,
        help="Moyenne mobile sur 200 jours (≈ 9-10 mois).\n\n"
             "• 📈 Golden Cross : MA50 passe AU-DESSUS de MA200 → signal haussier\n"
             "• 📉 Death Cross : MA50 passe EN DESSOUS → signal baissier\n\n"
             "👉 L'indicateur long terme le plus suivi au monde.")
    show_bollinger = st.toggle("Bandes de Bollinger",  value=False,
        help="Zone haute/basse autour du prix (moyenne 20j ± 2 écarts-types).\n\n"
             "• Prix touche la bande HAUTE → potentiellement sur-acheté\n"
             "• Prix touche la bande BASSE → potentiellement sur-vendu\n"
             "• Bandes resserrées → explosion de volatilité imminente\n\n"
             "👉 Utile pour repérer les points d'entrée/sortie.")
    show_volume    = st.toggle("Volume des échanges",  value=False,
        help="Nombre de titres échangés chaque jour.\n\n"
             "• Hausse + fort volume → mouvement crédible\n"
             "• Hausse + faible volume → mouvement fragile\n\n"
             "👉 Le volume confirme la force d'une tendance.")
    show_rsi       = st.toggle("RSI (14)",  value=False,
        help="Relative Strength Index sur 14 jours. Oscillateur de momentum entre 0 et 100.\n\n"
             "• > 70 → sur-acheté (risque de correction)\n"
             "• < 30 → sur-vendu (rebond possible)\n"
             "• 50 = ligne neutre\n\n"
             "👉 S'applique au premier actif sélectionné.")
    show_macd      = st.toggle("MACD (12/26/9)", value=False,
        help="Moving Average Convergence Divergence.\n\n"
             "• MACD passe AU-DESSUS du signal → achat\n"
             "• MACD passe EN DESSOUS du signal → vente\n"
             "• Histogramme positif → momentum haussier\n\n"
             "👉 S'applique au premier actif sélectionné.")
    show_events    = st.toggle("Événements historiques", value=False,
        help="Lignes verticales sur les grands événements financiers.\n\n"
             "Seuls les événements après ta date de début sont affichés.\n\n"
             "Visualise comment tes actifs ont réagi aux crises passées.")
    st.divider()

    # Construire le set des tickers pré-définis pour référence
    _all_predefined = set()
    for cat, liste in TICKERS_APP.items():
        _all_predefined.update(liste)
        st.subheader(cat)
        for t in liste:
            cb_key = f"cb_{t}"
            # Activer/désactiver la checkbox si demandé depuis le glossaire
            if t in st.session_state.activated_tickers:
                st.session_state[cb_key] = True
                st.session_state.activated_tickers.discard(t)
            if t in st.session_state.deactivated_tickers:
                st.session_state[cb_key] = False
                st.session_state.deactivated_tickers.discard(t)
            if st.checkbox(t, value=t in DEFAUT, key=cb_key):
                selection.append(t)

    st.divider()
    st.subheader("Ajouter un actif")
    st.caption("Tape un symbole ou un nom d'entreprise")
    custom_input = st.text_input("Recherche", key="custom_input_field",
                                 placeholder="Ex : TTWO, IBM, Total, bitcoin...",
                                 label_visibility="collapsed").strip()
    if custom_input and custom_input != st.session_state.custom_input_val:
        st.session_state.custom_input_val = custom_input
        # Essayer d'abord comme symbole exact
        ticker_upper = custom_input.upper()
        if verifier_ticker(ticker_upper):
            ajouter_ticker(ticker_upper)
            st.rerun()
        else:
            # Sinon rechercher par nom
            resultats = rechercher_tickers(custom_input)
            if resultats and len(resultats) == 1:
                ajouter_ticker(resultats[0]["symbol"])
                st.rerun()
            elif resultats:
                st.session_state._sidebar_results = resultats
            else:
                st.session_state._add_msg = ("error", f"Aucun résultat pour '{custom_input}'.")
                st.rerun()
    if hasattr(st.session_state, "_add_msg"):
        lv, msg = st.session_state._add_msg
        getattr(st, lv)(msg)
        del st.session_state._add_msg
    if hasattr(st.session_state, "_sidebar_results"):
        for r in st.session_state._sidebar_results[:5]:
            c1, c2 = st.columns([3, 1])
            c1.caption(f"**{r['symbol']}** — {r['name']}")
            if c2.button("+", key=f"sbadd_{r['symbol']}"):
                ajouter_ticker(r["symbol"])
                del st.session_state._sidebar_results
                st.rerun()
        if st.button("Fermer", key="sb_close_results"):
            del st.session_state._sidebar_results
            st.rerun()
    if st.session_state.custom_tickers:
        st.markdown("**Tickers ajoutés :**")
        for t in st.session_state.custom_tickers.copy():
            c1, c2 = st.columns([3,1])
            c1.markdown(f"`{t}`")
            if c2.button("✕", key=f"del_{t}"):
                st.session_state.custom_tickers.remove(t)
                sauvegarder_tickers_json(st.session_state.custom_tickers)
                st.rerun()
            else: selection.append(t)

    # (navigation gérée par st.tabs dans le contenu principal)


# ── Chargement données ────────────────────────────────────────
debut_str = date_debut.strftime("%Y-%m-%d")
fin_str   = date_fin.strftime("%Y-%m-%d")
if selection:
    with st.spinner("⏳ Chargement..."):
        df, df_vol = get_data_and_volume(tuple(sorted(selection)), debut_str, fin_str)
        if not show_volume:
            df_vol = pd.DataFrame()
else:
    df = df_vol = pd.DataFrame()
evenements_affiches = filtrer_evenements_proches([
    e for e in EVENEMENTS if show_events
    and datetime.strptime(e["date"], "%Y-%m-%d") >= datetime.combine(date_debut, datetime.min.time())
])

# ── Onglets ───────────────────────────────────────────────────
(onglet1, onglet_pf, onglet2, onglet3, onglet4, onglet5,
 onglet_screener, onglet_bt, onglet6, onglet_macro,
 onglet_news, onglet_alertes, onglet_cal, onglet_heat, onglet7) = st.tabs([
    "Graphique",
    "Portefeuille",
    "Comparaison",
    "Corrélations",
    "Drawdown",
    "Analyses",
    "Screener",
    "Backtest",
    "Fiches",
    "Macro",
    "Actualités",
    "Alertes",
    "Calendrier",
    "Heatmap",
    "Recherche",
])


# ════════════════════════════════════════════════════════════
#  ONGLET 1 — GRAPHIQUE
# ════════════════════════════════════════════════════════════
with onglet1:
    st.title("Tableau de Bord Financier — Base 100")
    st.caption("Base 100 : tous les actifs démarrent à 100. Affiche 250 = +150% depuis le départ.")
    if df.empty:
        st.info("👈 Sélectionne au moins un actif.")
    else:
        b = base100(df); affichage = b.copy()
        if (show_ma50 or show_ma200) and len(b.columns):
            tm = b.columns[0]
            if show_ma50:  affichage[f"{tm} MA50"]  = b[tm].rolling(50).mean()
            if show_ma200: affichage[f"{tm} MA200"] = b[tm].rolling(200).mean()
        if show_bollinger and len(b.columns):
            tb = b.columns[0]
            _, bh, bl = calcul_bollinger(b[tb])
            affichage[f"{tb} BB Haute"] = bh; affichage[f"{tb} BB Basse"] = bl
        st.plotly_chart(tracer_graphique_principal(
            affichage, df, df_vol, echelle_log,
            show_volume, show_rsi, show_macd,
            evenements_affiches, date_debut
        ), width="stretch")

        st.subheader("Performances")
        cols = st.columns(min(len(b.columns), 4))
        for i, t in enumerate(b.columns):
            with cols[i % len(cols)]:
                val = b[t].dropna().iloc[-1]
                st.metric(t, f"{val:.1f}", f"{val-100:+.1f}%",
                          help=f"1 000€ investis au départ = {1000*val/100:.0f}€ aujourd'hui.")

        st.subheader("Volatilité annualisée")
        vol = calcul_volatilite(df)
        cols2 = st.columns(min(len(vol), 4))
        for i, t in enumerate(vol.index):
            with cols2[i % len(cols2)]:
                niv = "🟢 Faible" if vol[t] < 20 else ("🟡 Modérée" if vol[t] < 40 else "🔴 Élevée")
                st.metric(t, f"{vol[t]:.1f}%", niv)

        csv = b.round(2).to_csv().encode("utf-8")
        st.download_button("⬇️ Télécharger CSV", data=csv,
                           file_name=f"finance_{debut_str}_{fin_str}.csv", mime="text/csv")


# ════════════════════════════════════════════════════════════
#  ONGLET PORTEFEUILLE
# ════════════════════════════════════════════════════════════
with onglet_pf:
    st.title("Simulateur de Portefeuille")
    st.caption("Construis un portefeuille en attribuant un pourcentage à chaque actif sélectionné.")

    if df.empty or len(df.columns) == 0:
        st.info("👈 Sélectionne au moins un actif dans le panneau latéral.")
    else:
        actifs_dispo = list(df.columns)
        n = len(actifs_dispo)

        def poids_equitables(actifs):
            base  = round(100.0 / len(actifs), 2)
            reste = round(100.0 - base * len(actifs), 2)
            return [round(base + (reste if i == 0 else 0), 2) for i in range(len(actifs))]

        if "_pf_version" not in st.session_state:
            st.session_state["_pf_version"] = 0

        cle = "_".join(sorted(actifs_dispo))
        if st.session_state.get("_pf_cle") != cle:
            st.session_state["_pf_cle"]     = cle
            st.session_state["_pf_version"] += 1
            st.session_state["_pf_df"] = pd.DataFrame({
                "Actif":     actifs_dispo,
                "Poids (%)": poids_equitables(actifs_dispo),
            })

        # ── Tabs internes : Portefeuille classique / DCA / Comparateur ──
        tab_pf, tab_dca, tab_cmp = st.tabs([
            "📊 Portefeuille classique",
            "📅 Simulation DCA",
            "⚖️ Comparateur de stratégies",
        ])

        # ════════════════════════════════════════════════════
        #  TAB PORTEFEUILLE CLASSIQUE
        # ════════════════════════════════════════════════════
        with tab_pf:
            st.subheader("1.  Allocation du portefeuille")
            st.caption("Modifie directement les valeurs dans le tableau. Le total doit faire 100%.")

            if st.button(
                f"⚖️ Équipondérer ({round(100/n, 2)}% chacun)",
                help=f"Répartit 100% équitablement sur les {n} actifs.\n\n"
                     f"Si la division n'est pas exacte, la différence est ajustée sur "
                     f"**{actifs_dispo[0]}**."
            ):
                st.session_state["_pf_df"] = pd.DataFrame({
                    "Actif":     actifs_dispo,
                    "Poids (%)": poids_equitables(actifs_dispo),
                })
                st.session_state["_pf_version"] += 1
                st.rerun()

            editor_key = f"pf_editor_{st.session_state['_pf_version']}"
            df_edit = st.data_editor(
                st.session_state["_pf_df"],
                width="stretch",
                hide_index=True,
                column_config={
                    "Actif":     st.column_config.TextColumn("Actif", disabled=True),
                    "Poids (%)": st.column_config.NumberColumn(
                        "Poids (%)", min_value=0.0, max_value=100.0, step=0.01, format="%.2f"),
                },
                key=editor_key,
            )

            poids = dict(zip(df_edit["Actif"], df_edit["Poids (%)"].round(2)))
            total = round(sum(poids.values()), 2)

            col_tot1, col_tot2 = st.columns([3, 1])
            with col_tot1:
                st.progress(min(total / 100, 1.0))
            with col_tot2:
                if abs(total - 100) < 0.01:
                    st.success(f"✅ **{total:.2f}%**")
                elif total > 100:
                    st.error(f"❌ **{total:.2f}%** (+{total-100:.2f}%)")
                else:
                    st.warning(f"⚠️ **{total:.2f}%** (-{100-total:.2f}%)")

            st.divider()
            st.subheader("2.  Mise de départ")
            mise_depart = st.number_input(
                "Montant investi (€)", min_value=100, max_value=10_000_000,
                value=10_000, step=100, format="%d", key="mise_classique"
            )
            st.divider()

            if abs(total - 100) < 0.01:
                st.subheader("3.  Évolution du portefeuille")

                poids_norm    = {t: poids[t] / 100 for t in actifs_dispo if poids[t] > 0}
                actifs_actifs = list(poids_norm.keys())
                df_pf         = df[actifs_actifs].dropna(how="all")
                b_pf          = base100(df_pf)

                pf_valeur     = sum(b_pf[t] * poids_norm[t] for t in actifs_actifs) / 100 * mise_depart
                rendements_pf = pf_valeur.pct_change().dropna()
                vol_pf        = float(rendements_pf.std() * np.sqrt(252) * 100)
                perf_totale   = (pf_valeur.iloc[-1] - mise_depart) / mise_depart * 100
                gain_euros    = pf_valeur.iloc[-1] - mise_depart

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Mise de départ",      f"{mise_depart:,.0f} €")
                m2.metric("Valeur actuelle",     f"{pf_valeur.iloc[-1]:,.0f} €", f"{perf_totale:+.1f}%")
                m3.metric("Gain / Perte",        f"{gain_euros:+,.0f} €")
                m4.metric("Volatilité annuelle", f"{vol_pf:.1f}%",
                          help="Volatilité annualisée du portefeuille.\n\n"
                               "• 🟢 < 10% : stable\n• 🟡 10–20% : modéré\n• 🔴 > 20% : risqué")

                fig_pf = go.Figure()
                fig_pf.add_trace(go.Scatter(
                    x=pf_valeur.index, y=pf_valeur,
                    name="💼 Portefeuille", mode="lines",
                    line=dict(width=3, color="#00D4AA"),
                    fill="tozeroy", fillcolor="rgba(0,212,170,0.06)",
                ))
                for t in actifs_actifs:
                    fig_pf.add_trace(go.Scatter(
                        x=df_pf.index, y=b_pf[t] / 100 * mise_depart,
                        name=f"{t} ({poids[t]:.2f}%)",
                        mode="lines", line=dict(width=1.5), opacity=0.6,
                    ))
                fig_pf.add_hline(y=mise_depart, line_dash="dash",
                                 line_color="rgba(255,255,255,0.3)",
                                 annotation_text="Mise initiale",
                                 annotation_font_color="rgba(255,255,255,0.5)")
                fig_pf.update_layout(
                    height=520, margin=dict(l=10, r=10, t=40, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
                    hovermode="x unified",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#FAFAFA"),
                    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)",
                               tickformat="%Y", dtick="M12", ticklabelmode="period"),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)",
                               tickformat=",.0f", ticksuffix=" €"),
                )
                st.plotly_chart(fig_pf, width="stretch")

                st.subheader("Répartition du portefeuille")
                col_pie1, col_pie2 = st.columns([1, 1])
                with col_pie1:
                    fig_pie = go.Figure(go.Pie(
                        labels=actifs_actifs,
                        values=[poids[t] for t in actifs_actifs],
                        hole=0.45, textinfo="label+percent",
                        hovertemplate="%{label} : %{value:.2f}%<extra></extra>",
                    ))
                    fig_pie.update_layout(
                        height=350, margin=dict(l=10, r=10, t=10, b=10),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#FAFAFA"), showlegend=False
                    )
                    st.plotly_chart(fig_pie, width="stretch")
                with col_pie2:
                    contribs = []
                    for t in actifs_actifs:
                        val_init = mise_depart * poids_norm[t]
                        val_fin  = b_pf[t].dropna().iloc[-1] / 100 * val_init
                        contribs.append({
                            "Actif":       t,
                            "Allocation":  f"{poids[t]:.2f}%",
                            "Investi (€)": f"{val_init:,.0f}",
                            "Valeur (€)":  f"{val_fin:,.0f}",
                            "Perf (%)":    f"{(val_fin - val_init) / val_init * 100:+.1f}%",
                        })
                    st.dataframe(pd.DataFrame(contribs).set_index("Actif"), width="stretch")

                st.subheader("Rendements annuels du portefeuille")
                pf_annuel = pf_valeur.resample("YE").last().pct_change().dropna() * 100
                pf_annuel.index = pf_annuel.index.year
                fig_bar = go.Figure(go.Bar(
                    x=pf_annuel.index.astype(str), y=pf_annuel.values,
                    marker_color=["#2d9e5f" if v >= 0 else "#e05252" for v in pf_annuel.values],
                    text=[f"{v:+.1f}%" for v in pf_annuel.values], textposition="outside",
                ))
                fig_bar.update_layout(
                    height=350, margin=dict(l=10, r=10, t=20, b=10),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#FAFAFA"),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.08)", ticksuffix="%"),
                    showlegend=False
                )
                st.plotly_chart(fig_bar, width="stretch")

                st.subheader("Drawdown du portefeuille")
                dd_pf = (pf_valeur - pf_valeur.cummax()) / pf_valeur.cummax() * 100
                fig_dd = go.Figure(go.Scatter(
                    x=dd_pf.index, y=dd_pf.values, fill="tozeroy",
                    line=dict(color="#e05252"), fillcolor="rgba(224,82,82,0.3)"
                ))
                fig_dd.update_layout(
                    height=300, margin=dict(l=10, r=10, t=10, b=10),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#FAFAFA"),
                    xaxis=dict(tickformat="%Y", dtick="M12", gridcolor="rgba(255,255,255,0.08)"),
                    yaxis=dict(tickformat=".0f", ticksuffix="%", gridcolor="rgba(255,255,255,0.08)")
                )
                st.plotly_chart(fig_dd, width="stretch")
                st.caption(f"Pire drawdown du portefeuille : **{dd_pf.min():.1f}%**")

            else:
                st.info("💡 Ajuste les pourcentages pour que le total soit exactement 100%.")

        # ════════════════════════════════════════════════════
        #  TAB DCA
        # ════════════════════════════════════════════════════
        with tab_dca:
            st.subheader("Simulation DCA — Investissement régulier")
            st.caption(
                "Le DCA (Dollar-Cost Averaging) consiste à investir un montant fixe chaque mois, "
                "quel que soit le prix. Tu achètes plus de parts quand les prix baissent, "
                "moins quand ils montent — ce qui lisse ton prix de revient dans le temps."
            )

            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                dca_ticker = st.selectbox(
                    "Actif à simuler",
                    actifs_dispo,
                    help="Le DCA s'applique sur un seul actif à la fois.",
                    key="dca_ticker"
                )
            with col_d2:
                dca_mensuel = st.number_input(
                    "Versement mensuel (€)", min_value=10, max_value=100_000,
                    value=200, step=10, format="%d", key="dca_mensuel"
                )
            with col_d3:
                dca_initial = st.number_input(
                    "Apport initial (€)", min_value=0, max_value=1_000_000,
                    value=0, step=100, format="%d", key="dca_initial",
                    help="Montant investi en une seule fois au départ, en plus des versements mensuels."
                )

            # Calcul DCA
            serie_dca = df[dca_ticker].dropna()
            # Rééchantillonner au premier jour ouvré de chaque mois
            prix_mensuels = serie_dca.resample("MS").first().dropna()

            if len(prix_mensuels) < 2:
                st.warning("Pas assez de données pour simuler le DCA sur cette période.")
            else:
                parts_totales   = 0.0
                capital_investi = 0.0
                historique      = []

                for i, (dt, prix) in enumerate(prix_mensuels.items()):
                    if i == 0 and dca_initial > 0:
                        parts_totales   += dca_initial / prix
                        capital_investi += dca_initial
                    parts_totales   += dca_mensuel / prix
                    capital_investi += dca_mensuel
                    valeur_portefeuille = parts_totales * prix
                    historique.append({
                        "date":     dt,
                        "investi":  capital_investi,
                        "valeur":   valeur_portefeuille,
                        "parts":    parts_totales,
                        "prix":     prix,
                    })

                hist_df      = pd.DataFrame(historique).set_index("date")
                valeur_finale = hist_df["valeur"].iloc[-1]
                total_investi = hist_df["investi"].iloc[-1]
                gain_dca      = valeur_finale - total_investi
                perf_dca      = gain_dca / total_investi * 100
                prix_revient  = total_investi / hist_df["parts"].iloc[-1]
                prix_actuel   = hist_df["prix"].iloc[-1]
                nb_mois       = len(hist_df)

                # Métriques
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total investi",   f"{total_investi:,.0f} €",
                          help=f"{nb_mois} versements de {dca_mensuel} €"
                               + (f" + {dca_initial} € d'apport initial" if dca_initial else ""))
                m2.metric("Valeur actuelle", f"{valeur_finale:,.0f} €", f"{perf_dca:+.1f}%")
                m3.metric("Gain / Perte",    f"{gain_dca:+,.0f} €")
                m4.metric("Prix de revient", f"{prix_revient:.2f} €",
                          delta=f"vs prix actuel {prix_actuel:.2f} €",
                          delta_color="normal" if prix_actuel >= prix_revient else "inverse",
                          help="Prix moyen d'achat de tes parts, pondéré par les quantités achetées chaque mois.\n\n"
                               "Si le prix actuel est au-dessus → tu es en bénéfice.")

                st.divider()

                # Graphique évolution DCA
                fig_dca = go.Figure()
                fig_dca.add_trace(go.Scatter(
                    x=hist_df.index, y=hist_df["valeur"],
                    name="💼 Valeur du portefeuille DCA",
                    mode="lines", line=dict(width=2.5, color="#00D4AA"),
                    fill="tozeroy", fillcolor="rgba(0,212,170,0.06)",
                ))
                fig_dca.add_trace(go.Scatter(
                    x=hist_df.index, y=hist_df["investi"],
                    name="💸 Capital investi (cumul)",
                    mode="lines", line=dict(width=2, color="#FFD700", dash="dash"),
                ))
                # Zone gain/perte
                fig_dca.add_trace(go.Scatter(
                    x=list(hist_df.index) + list(hist_df.index[::-1]),
                    y=list(hist_df["valeur"]) + list(hist_df["investi"][::-1]),
                    fill="toself",
                    fillcolor="rgba(0,212,170,0.08)",
                    line=dict(color="rgba(0,0,0,0)"),
                    showlegend=False, hoverinfo="skip",
                ))
                fig_dca.add_hline(y=prix_revient,
                                  line_dash="dot", line_color="rgba(255,200,0,0.4)",
                                  annotation_text=f"Prix de revient : {prix_revient:.2f} €",
                                  annotation_font_color="rgba(255,200,0,0.7)",
                                  annotation_position="bottom right")
                fig_dca.update_layout(
                    height=460, margin=dict(l=10, r=10, t=30, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
                    hovermode="x unified",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#FAFAFA"),
                    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)",
                               tickformat="%Y", dtick="M12", ticklabelmode="period"),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)",
                               tickformat=",.0f", ticksuffix=" €"),
                )
                st.plotly_chart(fig_dca, width="stretch")

                # Comparaison DCA vs investissement unique
                st.divider()
                st.subheader("DCA vs Investissement unique")
                st.caption("Que se serait-il passé si tu avais tout investi en une seule fois au départ ?")

                prix_depart    = serie_dca.iloc[0]
                montant_lump   = total_investi
                valeur_lump    = (prix_actuel / prix_depart) * montant_lump
                gain_lump      = valeur_lump - montant_lump
                perf_lump      = gain_lump / montant_lump * 100

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**📅 DCA mensuel**")
                    st.markdown(f"Valeur finale : **{valeur_finale:,.0f} €**")
                    st.markdown(f"Gain : **:{('green' if gain_dca >= 0 else 'red')}[{gain_dca:+,.0f} €  ({perf_dca:+.1f}%)]**")
                with c2:
                    st.markdown("**💰 Investissement unique (Lump Sum)**")
                    st.markdown(f"Valeur finale : **{valeur_lump:,.0f} €**")
                    st.markdown(f"Gain : **:{('green' if gain_lump >= 0 else 'red')}[{gain_lump:+,.0f} €  ({perf_lump:+.1f}%)]**")

                diff = valeur_finale - valeur_lump
                if abs(diff) > 1:
                    gagnant = "DCA" if diff > 0 else "Lump Sum"
                    perdant = "Lump Sum" if diff > 0 else "DCA"
                    # Les deux perdent de l'argent
                    if gain_dca < 0 and gain_lump < 0:
                        st.warning(f"Les deux stratégies sont en perte. Le **{gagnant}** a limité les dégâts avec **{abs(diff):,.0f} €** de perte en moins que le {perdant}.")
                    # Le gagnant gagne, le perdant perd
                    elif (diff > 0 and gain_lump < 0) or (diff < 0 and gain_dca < 0):
                        st.info(f"Le **{gagnant}** termine en gain, tandis que le **{perdant}** est en perte. Écart de **{abs(diff):,.0f} €**.")
                    # Les deux gagnent
                    else:
                        st.success(f"Sur cette période, le **{gagnant}** aurait généré **{abs(diff):,.0f} €** de plus que le {perdant}.")

                # Courbe prix de revient DCA dans le temps
                st.divider()
                st.subheader("Évolution du prix de revient")
                st.caption("Le prix de revient DCA converge progressivement vers une moyenne lissée du marché.")
                prix_revient_ts = hist_df["investi"] / hist_df["parts"]
                fig_pr = go.Figure()
                fig_pr.add_trace(go.Scatter(
                    x=serie_dca.index, y=serie_dca.values,
                    name=f"Prix {dca_ticker}", mode="lines",
                    line=dict(width=1.5, color="#8888FF"), opacity=0.7,
                ))
                fig_pr.add_trace(go.Scatter(
                    x=prix_revient_ts.index, y=prix_revient_ts.values,
                    name="Prix de revient DCA", mode="lines",
                    line=dict(width=2, color="#FFD700", dash="dash"),
                ))
                fig_pr.update_layout(
                    height=340, margin=dict(l=10, r=10, t=20, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
                    hovermode="x unified",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#FAFAFA"),
                    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)",
                               tickformat="%Y", dtick="M12", ticklabelmode="period"),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)", tickformat=".2f"),
                )
                st.plotly_chart(fig_pr, width="stretch")

        # ════════════════════════════════════════════════════
        #  TAB COMPARATEUR DE STRATÉGIES
        # ════════════════════════════════════════════════════
        with tab_cmp:
            st.subheader("Comparateur de stratégies")
            st.caption(
                "Construis jusqu'à 4 portefeuilles hypothétiques et compare leurs performances "
                "sur la même période avec les mêmes métriques. "
                "Chaque stratégie est un mélange de tickers pondérés, rééquilibré mensuellement."
            )

            # ── Période ──────────────────────────────────────
            cp1, cp2 = st.columns(2)
            cmp_debut = cp1.date_input("Date de début", value=datetime(2016, 1, 1),
                                       min_value=datetime(2000, 1, 1), max_value=date.today(),
                                       key="cmp_debut")
            cmp_fin   = cp2.date_input("Date de fin", value=date.today(),
                                       min_value=datetime(2000, 1, 1), max_value=date.today(),
                                       key="cmp_fin")

            st.divider()

            # ── Stratégies prédéfinies ────────────────────────
            PRESETS = {
                "100% S&P 500":         {"^GSPC": 100},
                "60/40 Actions/Oblig.": {"^GSPC": 60,  "AGG": 40},
                "Portefeuille Monde":   {"^GSPC": 50,  "^FCHI": 25, "^N225": 25},
                "Croissance Tech":      {"AAPL": 20,   "MSFT": 20, "NVDA": 20, "GOOGL": 20, "META": 20},
                "Crypto + Tech":        {"BTC-USD": 30,"ETH-USD": 20,"NVDA": 25,"AAPL": 25},
                "Personnalisé":         {},
            }

            # ── Nombre de stratégies ──────────────────────────
            nb_strats = st.slider("Nombre de stratégies à comparer", 2, 4, 3, key="cmp_nb")

            COULEURS_STRAT = ["#00D4AA", "#FF6B6B", "#FFD700", "#74B9FF"]
            strats_config = []  # liste de {"nom": str, "poids": {ticker: poids}}

            cols_strat = st.columns(nb_strats)
            for i, col in enumerate(cols_strat):
                with col:
                    st.markdown(
                        f"<div style='border-left:3px solid {COULEURS_STRAT[i]};"
                        f"padding-left:10px; margin-bottom:8px;'>"
                        f"<b style='color:{COULEURS_STRAT[i]};'>Stratégie {i+1}</b></div>",
                        unsafe_allow_html=True
                    )
                    preset_choices = list(PRESETS.keys())
                    # Défauts variés selon l'indice
                    default_idx = [0, 1, 3, 4][i] if i < 4 else 0
                    preset_sel = st.selectbox(
                        "Modèle", preset_choices,
                        index=default_idx, key=f"cmp_preset_{i}"
                    )
                    nom_strat = st.text_input(
                        "Nom", value=preset_sel if preset_sel != "Personnalisé" else f"Stratégie {i+1}",
                        key=f"cmp_nom_{i}"
                    )

                    poids_strat = {}
                    if preset_sel != "Personnalisé":
                        poids_base = PRESETS[preset_sel]
                        st.caption("Composition :")
                        for tk, w in poids_base.items():
                            new_w = st.number_input(
                                f"{tk} (%)", min_value=0, max_value=100,
                                value=w, step=5, key=f"cmp_{i}_{tk}"
                            )
                            poids_strat[tk] = new_w
                    else:
                        # Mode personnalisé : jusqu'à 6 tickers
                        nb_lignes = st.number_input("Nb d'actifs", 1, 6, 3, key=f"cmp_nb_actifs_{i}")
                        nb_l = int(nb_lignes)
                        poids_egaux = round(100 / nb_l) if nb_l > 0 else 33
                        for j in range(nb_l):
                            tk_c1, tk_c2 = st.columns([2, 1])
                            tk_sym = tk_c1.text_input(
                                "Ticker", value=["AAPL","MSFT","NVDA","TSLA","BTC-USD","^GSPC"][j],
                                key=f"cmp_{i}_custom_tk_{j}"
                            ).strip().upper()
                            tk_w = tk_c2.number_input(
                                "%", min_value=0, max_value=100, value=poids_egaux,
                                step=5, key=f"cmp_{i}_custom_w_{j}"
                            )
                            if tk_sym:
                                poids_strat[tk_sym] = tk_w

                    total_w = sum(poids_strat.values())
                    if total_w > 0 and total_w != 100:
                        st.caption(f"⚠️ Total : {total_w}% (sera normalisé à 100%)")
                    elif total_w == 100:
                        st.caption(f"✅ Total : 100%")

                    strats_config.append({"nom": nom_strat, "poids": poids_strat})

            st.divider()

            # ── Bouton lancer ─────────────────────────────────
            if st.button("🚀 Comparer les stratégies", type="primary", key="cmp_run"):
                debut_s = cmp_debut.strftime("%Y-%m-%d")
                fin_s   = cmp_fin.strftime("%Y-%m-%d")

                # Collecte tous les tickers nécessaires
                tous_tickers = set()
                for s in strats_config:
                    tous_tickers.update(s["poids"].keys())
                tous_tickers.discard("")

                with st.spinner("⏳ Chargement des données…"):
                    try:
                        df_raw, _ = get_data_and_volume(tuple(sorted(tous_tickers)), debut_s, fin_s)
                    except Exception as e:
                        st.error(f"Erreur de chargement : {e}")
                        df_raw = pd.DataFrame()

                if df_raw.empty:
                    st.error("Impossible de charger les données. Vérifie les tickers.")
                else:
                    # ── Construction des séries de portefeuilles ──
                    series_pf = {}
                    erreurs   = []

                    for s in strats_config:
                        nom   = s["nom"]
                        poids = {tk: w for tk, w in s["poids"].items() if w > 0}
                        if not poids:
                            continue
                        total = sum(poids.values())
                        poids_n = {tk: w / total for tk, w in poids.items()}  # normalise à 1

                        # Tickers disponibles dans df_raw
                        tickers_ok = [tk for tk in poids_n if tk in df_raw.columns]
                        manquants  = [tk for tk in poids_n if tk not in df_raw.columns]
                        if manquants:
                            erreurs.append(f"**{nom}** : tickers introuvables → {', '.join(manquants)}")
                        if not tickers_ok:
                            continue

                        # Ré-normalise sur les tickers disponibles
                        poids_f = {tk: poids_n[tk] for tk in tickers_ok}
                        total_f = sum(poids_f.values())
                        poids_f = {tk: w / total_f for tk, w in poids_f.items()}

                        # Série du portefeuille = somme pondérée des rendements
                        df_sub = df_raw[tickers_ok].dropna(how="all").ffill()
                        rendements = df_sub.pct_change().fillna(0)
                        rend_pf    = sum(rendements[tk] * poids_f[tk] for tk in tickers_ok)
                        serie_pf   = (1 + rend_pf).cumprod() * 100
                        serie_pf.name = nom
                        series_pf[nom] = serie_pf

                    if erreurs:
                        for e in erreurs:
                            st.warning(e)

                    if not series_pf:
                        st.error("Aucune stratégie valide à afficher.")
                    else:
                        df_strats = pd.DataFrame(series_pf).dropna(how="all")

                        # ── Graphique base 100 ────────────────────
                        st.subheader("Évolution — Base 100")
                        fig_cmp = go.Figure()
                        for j, nom in enumerate(df_strats.columns):
                            c = COULEURS_STRAT[j % len(COULEURS_STRAT)]
                            fig_cmp.add_trace(go.Scatter(
                                x=df_strats.index, y=df_strats[nom],
                                name=nom, mode="lines",
                                line=dict(color=c, width=2.5),
                                hovertemplate=f"<b>{nom}</b><br>%{{x|%d/%m/%Y}}<br>Base 100 : %{{y:.1f}}<extra></extra>",
                            ))
                        fig_cmp.update_layout(
                            height=380, margin=dict(l=10, r=10, t=20, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                            hovermode="x unified",
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#FAFAFA"),
                            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)"),
                            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)"),
                        )
                        st.plotly_chart(fig_cmp, width="stretch")

                        # ── Drawdown ──────────────────────────────
                        # Convertit #RRGGBB → rgba(r,g,b,0.12) proprement
                        def hex_to_rgba(hex_color, alpha=0.12):
                            h = hex_color.lstrip("#")
                            r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
                            return f"rgba({r},{g},{b},{alpha})"

                        st.subheader("Drawdown comparé")
                        fig_dd = go.Figure()
                        for j, nom in enumerate(df_strats.columns):
                            s    = df_strats[nom].dropna()
                            dd_s = (s - s.cummax()) / s.cummax() * 100
                            c    = COULEURS_STRAT[j % len(COULEURS_STRAT)]
                            fig_dd.add_trace(go.Scatter(
                                x=dd_s.index, y=dd_s,
                                name=nom, mode="lines", fill="tozeroy",
                                line=dict(color=c, width=1.5),
                                fillcolor=hex_to_rgba(c),
                                hovertemplate=f"<b>{nom}</b><br>%{{x|%d/%m/%Y}}<br>Drawdown : %{{y:.1f}}%<extra></extra>",
                            ))
                        fig_dd.update_layout(
                            height=280, margin=dict(l=10, r=10, t=20, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                            hovermode="x unified",
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#FAFAFA"),
                            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)"),
                            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)",
                                       ticksuffix="%"),
                        )
                        st.plotly_chart(fig_dd, width="stretch")

                        # ── Tableau des métriques ─────────────────
                        st.subheader("Métriques comparées")
                        lignes = []
                        for j, nom in enumerate(df_strats.columns):
                            s  = df_strats[nom].dropna()
                            r  = s.pct_change().dropna()
                            if len(r) < 20:
                                continue
                            perf_tot  = (s.iloc[-1] / s.iloc[0] - 1) * 100
                            n_annees  = len(s) / 252
                            cagr      = ((s.iloc[-1] / s.iloc[0]) ** (1 / max(n_annees, 0.1)) - 1) * 100
                            vol       = r.std() * np.sqrt(252) * 100
                            sharpe    = ((r.mean() - 0.03/252) / r.std() * np.sqrt(252)) if r.std() > 0 else 0
                            dd_max    = ((s - s.cummax()) / s.cummax() * 100).min()
                            calmar    = cagr / abs(dd_max) if dd_max != 0 else 0
                            # Meilleure/pire année
                            ann = s.resample("YE").last().pct_change().dropna() * 100
                            best_yr  = ann.max() if len(ann) else 0
                            worst_yr = ann.min() if len(ann) else 0
                            # Nb mois positifs
                            mois = s.resample("ME").last().pct_change().dropna()
                            pct_pos = (mois > 0).mean() * 100 if len(mois) else 0

                            lignes.append({
                                "Stratégie":      nom,
                                "Perf. totale":   f"{perf_tot:+.1f}%",
                                "CAGR":           f"{cagr:+.1f}%",
                                "Volatilité":     f"{vol:.1f}%",
                                "Sharpe":         f"{sharpe:.2f}",
                                "Drawdown max":   f"{dd_max:.1f}%",
                                "Calmar":         f"{calmar:.2f}",
                                "Meilleure année":f"{best_yr:+.1f}%",
                                "Pire année":     f"{worst_yr:+.1f}%",
                                "% mois positifs":f"{pct_pos:.0f}%",
                            })

                        df_metrics = pd.DataFrame(lignes).set_index("Stratégie")

                        # Mise en forme colorée
                        def color_metric(val):
                            try:
                                v = float(str(val).replace("%","").replace("+",""))
                                if v > 0:  return "color: #00D4AA"
                                if v < 0:  return "color: #FF6B6B"
                            except Exception: pass
                            return ""

                        st.dataframe(
                            df_metrics.style.map(
                                color_metric,
                                subset=["Perf. totale","CAGR","Drawdown max","Meilleure année","Pire année"]
                            ),
                            width="stretch"
                        )

                        # ── Rendements annuels côte à côte ────────
                        st.subheader("Rendements annuels")
                        ann_data = {}
                        for nom in df_strats.columns:
                            s   = df_strats[nom].dropna()
                            ann = s.resample("YE").last().pct_change().dropna() * 100
                            ann.index = ann.index.year
                            ann_data[nom] = ann
                        df_ann = pd.DataFrame(ann_data).dropna(how="all")

                        fig_ann = go.Figure()
                        for j, nom in enumerate(df_ann.columns):
                            c = COULEURS_STRAT[j % len(COULEURS_STRAT)]
                            fig_ann.add_trace(go.Bar(
                                x=df_ann.index.astype(str), y=df_ann[nom],
                                name=nom, marker_color=c,
                                hovertemplate=f"<b>{nom}</b><br>Année : %{{x}}<br>Rendement : %{{y:+.1f}}%<extra></extra>",
                            ))
                        fig_ann.update_layout(
                            barmode="group",
                            height=320, margin=dict(l=10, r=10, t=20, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#FAFAFA"),
                            xaxis=dict(showgrid=False, gridcolor="rgba(255,255,255,0.07)"),
                            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)",
                                       ticksuffix="%"),
                        )
                        st.plotly_chart(fig_ann, width="stretch")

                        # ── Corrélation entre stratégies ──────────
                        if len(df_strats.columns) > 1:
                            st.subheader("Corrélation entre stratégies")
                            corr = df_strats.pct_change().dropna().corr().round(2)
                            fig_corr = go.Figure(go.Heatmap(
                                z=corr.values, x=corr.columns, y=corr.index,
                                colorscale="RdYlGn", zmid=0, zmin=-1, zmax=1,
                                text=corr.values.round(2), texttemplate="%{text}",
                                hovertemplate="%{x} / %{y}<br>Corrélation : %{z:.2f}<extra></extra>",
                            ))
                            fig_corr.update_layout(
                                height=260, margin=dict(l=10, r=10, t=20, b=10),
                                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                font=dict(color="#FAFAFA"),
                            )
                            st.plotly_chart(fig_corr, width="stretch")
                            st.caption(
                                "1.0 = parfaitement corrélées · 0 = indépendantes · -1 = opposées. "
                                "Une faible corrélation entre stratégies indique une bonne diversification."
                            )
# ════════════════════════════════════════════════════════════
with onglet2:
    st.title("Comparer deux périodes")
    if not selection:
        st.info("👈 Sélectionne des actifs.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Période A")
            debut_a = st.date_input("Début A", value=datetime(2018,1,1), key="da")
            fin_a   = st.date_input("Fin A",   value=datetime(2020,3,1), key="fa")
        with col2:
            st.subheader("Période B")
            debut_b = st.date_input("Début B", value=datetime(2020,3,1), key="db")
            fin_b   = st.date_input("Fin B",   value=datetime(2022,1,1), key="fb")
        if st.button("🔄 Comparer"):
            with st.spinner("Chargement..."):
                df_a, _ = get_data_and_volume(tuple(sorted(selection)), debut_a.strftime("%Y-%m-%d"), fin_a.strftime("%Y-%m-%d"))
                df_b, _ = get_data_and_volume(tuple(sorted(selection)), debut_b.strftime("%Y-%m-%d"), fin_b.strftime("%Y-%m-%d"))
            if df_a.empty or df_b.empty:
                st.error("Données insuffisantes.")
            else:
                b_a, b_b = base100(df_a), base100(df_b)
                def tracer_simple(aff):
                    fig = go.Figure()
                    for col in aff.columns:
                        fig.add_trace(go.Scatter(x=aff.index, y=aff[col], name=col, mode="lines"))
                    fig.update_layout(height=350, margin=dict(l=5,r=5,t=5,b=5),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#FAFAFA"), hovermode="x unified",
                        xaxis=dict(tickformat="%Y", dtick="M12", gridcolor="rgba(255,255,255,0.08)"),
                        yaxis=dict(tickformat=".0f", gridcolor="rgba(255,255,255,0.08)"))
                    return fig
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Période A** : {debut_a} → {fin_a}")
                    st.plotly_chart(tracer_simple(b_a), width="stretch")
                with col2:
                    st.markdown(f"**Période B** : {debut_b} → {fin_b}")
                    st.plotly_chart(tracer_simple(b_b), width="stretch")
                perf_a = {t: round(b_a[t].dropna().iloc[-1]-100,2) for t in b_a.columns}
                perf_b = {t: round(b_b[t].dropna().iloc[-1]-100,2) for t in b_b.columns}
                communs = [t for t in perf_a if t in perf_b]
                st.dataframe(pd.DataFrame({"Ticker": communs,
                    "Perf A %": [perf_a[t] for t in communs],
                    "Perf B %": [perf_b[t] for t in communs]}).set_index("Ticker"), width="stretch")


# ════════════════════════════════════════════════════════════
#  ONGLET 3 — CORRÉLATIONS
# ════════════════════════════════════════════════════════════
with onglet3:
    st.title("Corrélations entre actifs")
    st.caption("1.0 = évoluent ensemble. -1.0 = sens inverse. Pour diversifier, cherche des actifs peu corrélés.")
    if df.empty or len(df.columns) < 2:
        st.info("👈 Sélectionne au moins 2 actifs.")
    else:
        corr = df.pct_change().dropna().corr().round(2)
        def colorier(val):
            if val >= 0.7:    return "background-color: #1a6b3c; color: white"
            elif val >= 0.3:  return "background-color: #2d9e5f; color: white"
            elif val >= -0.3: return "background-color: #555555; color: white"
            elif val >= -0.7: return "background-color: #9e2d2d; color: white"
            else:             return "background-color: #6b1a1a; color: white"
        st.dataframe(corr.style.map(colorier).format("{:.2f}"), width="stretch")
        paires = [(c1,c2,corr.loc[c1,c2]) for i,c1 in enumerate(corr.columns) for c2 in corr.columns[i+1:]]
        paires_df = pd.DataFrame(paires, columns=["Actif 1","Actif 2","Corrélation"]).sort_values("Corrélation", ascending=False)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Plus corrélés")
            st.dataframe(paires_df.head(5).reset_index(drop=True), width="stretch")
        with col2:
            st.subheader("Moins corrélés")
            st.dataframe(paires_df.tail(5).reset_index(drop=True), width="stretch")


# ════════════════════════════════════════════════════════════
#  ONGLET 4 — DRAWDOWN
# ════════════════════════════════════════════════════════════
with onglet4:
    st.title("Drawdown Maximum")
    st.caption("Le drawdown max, c'est la pire chute qu'un actif a subie depuis son dernier sommet. "
        "Par exemple, -80% signifie qu'à un moment donné, l'actif avait perdu 80% de sa valeur maximale. "
        "C'est une mesure du risque réel que tu aurais vécu en le détenant.")
    if df.empty:
        st.info("👈 Sélectionne des actifs.")
    else:
        drawdowns = calcul_drawdown_max(df)
        cols = st.columns(min(len(drawdowns), 4))
        for i, t in enumerate(drawdowns.index):
            with cols[i % len(cols)]:
                niv = "🟢" if drawdowns[t] > -20 else ("🟡" if drawdowns[t] > -50 else "🔴")
                st.metric(t, f"{drawdowns[t]:.1f}%", niv,
                          help=f"Au pire moment, {t} avait perdu {abs(drawdowns[t]):.1f}% depuis son sommet.\n\n"
                               "• 🟢 > -20% : chute limitée\n• 🟡 -20 à -50% : correction sévère\n• 🔴 < -50% : effondrement")
        st.divider()
        ticker_dd = st.selectbox("Courbe de drawdown pour :", df.columns.tolist())
        serie = df[ticker_dd].dropna()
        courbe_dd = (serie - serie.cummax()) / serie.cummax() * 100
        fig_dd = go.Figure(go.Scatter(x=courbe_dd.index, y=courbe_dd.values, fill="tozeroy",
            line=dict(color="#e05252"), fillcolor="rgba(224,82,82,0.3)"))
        fig_dd.update_layout(height=400, margin=dict(l=10,r=10,t=10,b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#FAFAFA"),
            xaxis=dict(tickformat="%Y", dtick="M12", gridcolor="rgba(255,255,255,0.08)"),
            yaxis=dict(tickformat=".0f", gridcolor="rgba(255,255,255,0.08)"))
        st.plotly_chart(fig_dd, width="stretch")
        st.caption(f"Drawdown max : **{courbe_dd.min():.1f}%**")
        df_dd_tab = pd.DataFrame({"Ticker": drawdowns.index, "Drawdown Max (%)": drawdowns.values})
        df_dd_tab["Drawdown Max (%)"] = df_dd_tab["Drawdown Max (%)"].map(lambda x: f"{x:.2f}")
        st.dataframe(df_dd_tab.sort_values("Drawdown Max (%)").set_index("Ticker"), width="stretch")


# ════════════════════════════════════════════════════════════
#  ONGLET 5 — ANALYSES
# ════════════════════════════════════════════════════════════
with onglet5:
    st.title("Analyses approfondies")
    if df.empty:
        st.info("👈 Sélectionne des actifs.")
    else:
        # ════════════════════════════════════════════════════
        #  SCORE GLOBAL
        # ════════════════════════════════════════════════════
        st.subheader("Score global par actif")
        st.caption(
            "Note sur 20 combinant 4 critères financiers pondérés : "
            "**Sharpe 40%** · **Volatilité 25%** · **Drawdown 25%** · **Tendance 10%**"
        )

        # Explication de la méthode — mini annotation pédagogique
        with st.expander("📖 Comment est construite cette note ? (exemple concret)", expanded=False):
            st.markdown("""
**Exemple : AAPL sur 5 ans**

| Critère | Valeur mesurée | Note /5 | Poids | Contribution |
|---------|---------------|---------|-------|-------------|
| Sharpe ratio | 1.42 → bon rendement/risque | **4/5** | 40% | 1.60 |
| Volatilité annuelle | 28% → modérée | **3/5** | 25% | 0.75 |
| Drawdown maximum | -31% → correction sévère | **3/5** | 25% | 0.75 |
| Tendance 6m/12m moy. | +18% → haussière | **3/5** | 10% | 0.30 |
| **Score final** | | **3.4/5** | | **3.40 × 4 = 13.6/20** |

**Barèmes utilisés :**
- 🟢 **Sharpe** : < 0 → 0/5 · 0–0.5 → 1/5 · 0.5–1 → 2/5 · 1–1.5 → 3/5 · 1.5–2 → 4/5 · > 2 → 5/5
- 🟢 **Volatilité** (moins = mieux) : > 80% → 0/5 · 55–80% → 1/5 · 35–55% → 2/5 · 20–35% → 3/5 · 10–20% → 4/5 · < 10% → 5/5
- 🟢 **Drawdown** (moins = mieux) : < -70% → 0/5 · -70 à -50% → 1/5 · -50 à -35% → 2/5 · -35 à -20% → 3/5 · -20 à -10% → 4/5 · > -10% → 5/5
- 🟢 **Tendance** (moy. perf 6m+12m) : < -20% → 0/5 · -20 à -5% → 1/5 · -5 à 5% → 2/5 · 5 à 20% → 3/5 · 20 à 40% → 4/5 · > 40% → 5/5

> ⚠️ Ce score est un outil d'aide à l'analyse, pas un conseil d'investissement.
> Il se base sur l'historique de la période sélectionnée — les performances passées ne préjugent pas des performances futures.
""")

        scores, details = calcul_score_global(df)

        if scores:
            # Tri par score décroissant
            tri = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            # Affichage en grille
            nb_cols_sc = min(len(tri), 4)
            rows_sc = [tri[i:i+nb_cols_sc] for i in range(0, len(tri), nb_cols_sc)]
            for row_sc in rows_sc:
                cols_sc = st.columns(nb_cols_sc)
                for j, (t, score) in enumerate(row_sc):
                    d = details[t]
                    with cols_sc[j]:
                        # Couleur et médaille selon score
                        if   score >= 16: medal = "🥇"; color = "#FFD700"
                        elif score >= 12: medal = "🥈"; color = "#2d9e5f"
                        elif score >= 8:  medal = "🥉"; color = "#FF8C00"
                        else:             medal = "⚠️"; color = "#e05252"

                        st.markdown(
                            f"<div style='border:1px solid {color}33; border-radius:8px; padding:10px; margin-bottom:4px;'>"
                            f"<div style='font-size:1.1rem; font-weight:600;'>{medal} {t}</div>"
                            f"<div style='font-size:2rem; font-weight:700; color:{color};'>{score}/20</div>"
                            f"</div>", unsafe_allow_html=True
                        )

                        # Détail des 4 sous-critères
                        def barre(val, mx=5):
                            filled = int(round(val))
                            return "█" * filled + "░" * (mx - filled)

                        st.markdown(
                            f"<small>"
                            f"Sharpe {d['sharpe']:+.2f} &nbsp;`{barre(d['s_sharpe'])}` {d['s_sharpe']:.0f}/5<br>"
                            f"Vol {d['vol']:.0f}% &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`{barre(d['s_vol'])}` {d['s_vol']:.0f}/5<br>"
                            f"DD {d['dd']:.0f}% &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`{barre(d['s_dd'])}` {d['s_dd']:.0f}/5<br>"
                            f"Tendance {d['tendance']:+.0f}% `{barre(d['s_tend'])}` {d['s_tend']:.0f}/5"
                            f"</small>",
                            unsafe_allow_html=True
                        )
                # colonnes vides si row incomplète
                for k in range(len(row_sc), nb_cols_sc):
                    cols_sc[k].empty()

            # Tableau récapitulatif téléchargeable
            st.divider()
            df_scores = pd.DataFrame([
                {
                    "Actif":          t,
                    "Score /20":      d["score"],
                    "Sharpe":         d["sharpe"],
                    "Volatilité %":   d["vol"],
                    "Drawdown max %": d["dd"],
                    "Tendance moy %": d["tendance"],
                }
                for t, d in details.items()
            ]).sort_values("Score /20", ascending=False).set_index("Actif")
            st.dataframe(df_scores, width="stretch")

        st.divider()

        # ════════════════════════════════════════════════════
        #  SHARPE
        # ════════════════════════════════════════════════════
        st.subheader("Ratio de Sharpe")
        st.caption("Mesure si la performance est 'méritée' par rapport au risque pris.\n\n"
                   "• < 0.5 : mauvais\n• 0.5–1 : correct\n• 1–2 : bon\n• > 2 : excellent")
        sharpe = calcul_sharpe(df)
        cols_sh = st.columns(min(len(sharpe), 4))
        for i, t in enumerate(sharpe.index):
            with cols_sh[i % len(cols_sh)]:
                val = sharpe[t]
                niv = "🔴 Faible" if val < 0.5 else ("🟡 Correct" if val < 1 else ("🟢 Bon" if val < 2 else "🏆 Excellent"))
                st.metric(t, f"{val:.2f}", niv)
        st.divider()

        st.subheader("Rendements annuels (%)")
        ra = calcul_rendements_annuels(df)
        if not ra.empty:
            def cp(val):
                if pd.isna(val): return ""
                return ("background-color: #1a6b3c; color: white" if val > 20 else
                        "background-color: #2d9e5f; color: white" if val > 0 else
                        "background-color: #9e2d2d; color: white" if val > -20 else
                        "background-color: #6b1a1a; color: white")
            st.dataframe(ra.style.map(cp).format("{:+.1f}%"), width="stretch")
        st.divider()

        st.subheader("Meilleur & Pire mois")
        mp = calcul_meilleur_pire_mois(df)
        if mp:
            cols_mp = st.columns(min(len(mp), 3))
            for i, (t, data) in enumerate(mp.items()):
                with cols_mp[i % len(cols_mp)]:
                    st.markdown(f"**{t}**")
                    st.success(f"🟢 {data['meilleur_val']:+.1f}% ({data['meilleur_date']})")
                    st.error(f"🔴 {data['pire_val']:+.1f}% ({data['pire_date']})")


# ════════════════════════════════════════════════════════════
#  ONGLET SCREENER
# ════════════════════════════════════════════════════════════
with onglet_screener:
    st.title("Screener d'actifs")
    st.caption(
        "Filtre tes actifs sélectionnés selon des critères combinés. "
        "Seuls les actifs qui passent **tous** les filtres activés sont affichés."
    )

    if df.empty or len(df.columns) < 1:
        st.info("👈 Sélectionne au moins un actif dans le panneau latéral.")
    else:
        # ── Calcul des métriques de tous les actifs ───────────
        with st.spinner("Calcul des métriques…"):
            r_all      = df.pct_change().dropna()
            sharpes_sc = ((r_all - 0.03/252).mean() / r_all.std() * np.sqrt(252))
            vols_sc    = (r_all.std() * np.sqrt(252) * 100)
            scores_sc, details_sc = calcul_score_global(df)

            lignes_sc = []
            for t in df.columns:
                s = df[t].dropna()
                if len(s) < 14: continue
                rsi_val  = float(calcul_rsi(s).dropna().iloc[-1]) if len(s) >= 14 else None
                macd_v, sig_v, _ = calcul_macd(s)
                macd_cur = float(macd_v.dropna().iloc[-1]) if not macd_v.dropna().empty else None
                sig_cur  = float(sig_v.dropna().iloc[-1])  if not sig_v.dropna().empty  else None
                dd_val   = float(((s - s.cummax()) / s.cummax() * 100).min())
                perf1m   = float((s.iloc[-1] / s.iloc[max(-21,-len(s))] - 1) * 100)
                perf3m   = float((s.iloc[-1] / s.iloc[max(-63,-len(s))] - 1) * 100)
                perf1a   = float((s.iloc[-1] / s.iloc[max(-252,-len(s))] - 1) * 100)
                lignes_sc.append({
                    "Ticker":      t,
                    "Score /20":   scores_sc.get(t, 0),
                    "Sharpe":      round(float(sharpes_sc.get(t, 0)), 2),
                    "Vol %":       round(float(vols_sc.get(t, 0)), 1),
                    "Drawdown %":  round(dd_val, 1),
                    "RSI":         round(rsi_val, 1) if rsi_val else None,
                    "MACD > Sig":  (macd_cur > sig_cur) if (macd_cur and sig_cur) else None,
                    "Perf 1M %":   round(perf1m, 1),
                    "Perf 3M %":   round(perf3m, 1),
                    "Perf 1A %":   round(perf1a, 1),
                })
        df_sc = pd.DataFrame(lignes_sc)

        st.divider()
        st.subheader("Filtres")

        with st.expander("🎛️ Configurer les filtres", expanded=True):
            fc1, fc2, fc3 = st.columns(3)

            with fc1:
                st.markdown("**📊 Score global**")
                f_score_on  = st.toggle("Activer", key="f_score_on")
                f_score_min = st.slider("Score minimum /20", 0.0, 20.0, 10.0, 0.5,
                                        key="f_score_min", disabled=not f_score_on)

                st.markdown("**⚡ Sharpe**")
                f_sharpe_on  = st.toggle("Activer", key="f_sharpe_on")
                f_sharpe_min = st.slider("Sharpe minimum", -2.0, 5.0, 0.5, 0.1,
                                         key="f_sharpe_min", disabled=not f_sharpe_on)

            with fc2:
                st.markdown("**📉 Volatilité %**")
                f_vol_on  = st.toggle("Activer", key="f_vol_on")
                f_vol_max = st.slider("Volatilité max %", 5.0, 150.0, 50.0, 1.0,
                                      key="f_vol_max", disabled=not f_vol_on)

                st.markdown("**📉 Drawdown max %**")
                f_dd_on  = st.toggle("Activer", key="f_dd_on")
                f_dd_min = st.slider("Drawdown max (ex: -40 = max -40%)", -100.0, 0.0, -40.0, 1.0,
                                     key="f_dd_min", disabled=not f_dd_on)

            with fc3:
                st.markdown("**📡 RSI (14)**")
                f_rsi_on  = st.toggle("Activer", key="f_rsi_on")
                f_rsi_lo, f_rsi_hi = st.slider("Plage RSI", 0, 100, (0, 100),
                                                 key="f_rsi_rng", disabled=not f_rsi_on)

                st.markdown("**📈 Performance 1 mois %**")
                f_perf_on  = st.toggle("Activer", key="f_perf_on")
                f_perf_min = st.slider("Perf 1M minimum %", -50.0, 50.0, 0.0, 0.5,
                                       key="f_perf_min", disabled=not f_perf_on)

                st.markdown("**🔀 MACD > Signal**")
                f_macd_on   = st.toggle("Activer (signal haussier)", key="f_macd_on")

        # ── Application des filtres ───────────────────────────
        mask = pd.Series([True] * len(df_sc), index=df_sc.index)
        if f_score_on:  mask &= df_sc["Score /20"] >= f_score_min
        if f_sharpe_on: mask &= df_sc["Sharpe"]    >= f_sharpe_min
        if f_vol_on:    mask &= df_sc["Vol %"]      <= f_vol_max
        if f_dd_on:     mask &= df_sc["Drawdown %"] >= f_dd_min
        if f_rsi_on:    mask &= df_sc["RSI"].between(f_rsi_lo, f_rsi_hi)
        if f_perf_on:   mask &= df_sc["Perf 1M %"] >= f_perf_min
        if f_macd_on:   mask &= df_sc["MACD > Sig"] == True

        df_filtre = df_sc[mask].sort_values("Score /20", ascending=False)

        st.divider()
        nb_pass = len(df_filtre)
        nb_tot  = len(df_sc)

        if nb_pass == 0:
            st.warning(f"Aucun actif ne passe tous les filtres ({nb_tot} analysés). Assouplit les critères.")
        else:
            st.success(f"✅ **{nb_pass} / {nb_tot}** actif(s) passent les filtres")

            # Cartes résumé des actifs retenus
            nb_c = min(nb_pass, 4)
            rows_f = [df_filtre.iloc[i:i+nb_c] for i in range(0, nb_pass, nb_c)]
            for row_f in rows_f:
                cols_f = st.columns(nb_c)
                for j, (_, row) in enumerate(row_f.iterrows()):
                    t = row["Ticker"]
                    sc = row["Score /20"]
                    if   sc >= 16: medal, col = "🥇", "#FFD700"
                    elif sc >= 12: medal, col = "🥈", "#2d9e5f"
                    elif sc >= 8:  medal, col = "🟠", "#FF8C00"
                    else:          medal, col = "🔴", "#e05252"
                    with cols_f[j]:
                        rsi_str = f"{row['RSI']:.0f}" if row['RSI'] else "—"
                        st.markdown(
                            f"<div style='border:1px solid {col}44;border-radius:8px;padding:10px;'>"
                            f"<div style='font-weight:700;font-size:1.05rem;'>{medal} {t}</div>"
                            f"<div style='color:{col};font-size:1.4rem;font-weight:700;'>{sc}/20</div>"
                            f"<small>Sharpe {row['Sharpe']:+.2f} · Vol {row['Vol %']:.0f}%<br>"
                            f"RSI {rsi_str} · 1M {row['Perf 1M %']:+.1f}%</small>"
                            f"</div>", unsafe_allow_html=True
                        )

            st.divider()
            # Tableau complet
            st.subheader("Tableau détaillé")
            def color_score(val):
                if pd.isna(val): return ""
                if val >= 16: return "background-color:#7a6000;color:white"
                if val >= 12: return "background-color:#1a6b3c;color:white"
                if val >= 8:  return "background-color:#7a4500;color:white"
                return "background-color:#6b1a1a;color:white"
            def color_perf(val):
                if pd.isna(val): return ""
                return "color:#2d9e5f" if val > 0 else "color:#e05252"

            df_show = df_filtre.set_index("Ticker").drop(columns=["MACD > Sig"])
            st.dataframe(
                df_show.style
                    .map(color_score, subset=["Score /20"])
                    .map(color_perf,  subset=["Perf 1M %","Perf 3M %","Perf 1A %"])
                    .format({
                        "Score /20":  "{:.1f}",
                        "Sharpe":     "{:+.2f}",
                        "Vol %":      "{:.1f}%",
                        "Drawdown %": "{:.1f}%",
                        "RSI":        lambda x: f"{x:.0f}" if x else "—",
                        "Perf 1M %":  "{:+.1f}%",
                        "Perf 3M %":  "{:+.1f}%",
                        "Perf 1A %":  "{:+.1f}%",
                    }),
                width="stretch"
            )


# ════════════════════════════════════════════════════════════
#  ONGLET BACKTESTING
# ════════════════════════════════════════════════════════════
with onglet_bt:
    st.title("Backtesting de stratégie")
    st.caption(
        "Teste une règle d'entrée/sortie sur l'historique et compare la performance "
        "à un simple Buy & Hold. Les frais ne sont pas simulés."
    )

    if df.empty:
        st.info("👈 Sélectionne des actifs.")
    else:
        bt_ticker = st.selectbox("Actif à backtester", df.columns.tolist(), key="bt_ticker")
        serie_bt  = df[bt_ticker].dropna()

        st.divider()
        st.subheader("Règles de la stratégie")

        # ── Choix de la stratégie ─────────────────────────────
        strategie = st.selectbox("Stratégie", [
            "RSI — Survente/Surachat",
            "Croisement MA50 / MA200 (Golden/Death Cross)",
            "MACD — Croisement Signal",
            "Bollinger — Rebond sur bandes",
        ], key="bt_strat")

        col_p1, col_p2 = st.columns(2)

        if strategie == "RSI — Survente/Surachat":
            with col_p1:
                rsi_buy  = st.slider("RSI — Seuil achat (survente)", 10, 50, 30, key="bt_rsi_buy",
                                     help="Achète quand RSI descend sous ce seuil")
            with col_p2:
                rsi_sell = st.slider("RSI — Seuil vente (surachat)", 50, 90, 70, key="bt_rsi_sell",
                                     help="Vend quand RSI monte au-dessus de ce seuil")

        elif strategie == "Croisement MA50 / MA200 (Golden/Death Cross)":
            col_p1.caption("Achat : MA50 croise **au-dessus** de MA200 (Golden Cross)")
            col_p2.caption("Vente : MA50 croise **en-dessous** de MA200 (Death Cross)")

        elif strategie == "MACD — Croisement Signal":
            col_p1.caption("Achat : MACD croise **au-dessus** de la ligne Signal")
            col_p2.caption("Vente : MACD croise **en-dessous** de la ligne Signal")

        elif strategie == "Bollinger — Rebond sur bandes":
            with col_p1:
                bb_win = st.slider("Fenêtre Bollinger (jours)", 10, 50, 20, key="bt_bb_win")
            col_p2.caption("Achat : prix touche bande basse · Vente : prix touche bande haute")

        st.divider()

        # ── Exécution du backtest ─────────────────────────────
        if st.button("▶️ Lancer le backtest", key="btn_bt"):
            with st.spinner("Calcul en cours…"):
                prix_bt = serie_bt.copy()

                # Génération des signaux (1 = long, 0 = hors marché)
                signal = pd.Series(0, index=prix_bt.index)

                if strategie == "RSI — Survente/Surachat":
                    rsi_bt = calcul_rsi(prix_bt)
                    position = 0
                    for i in range(len(prix_bt)):
                        r = rsi_bt.iloc[i]
                        if pd.isna(r): continue
                        if position == 0 and r < rsi_buy:
                            position = 1
                        elif position == 1 and r > rsi_sell:
                            position = 0
                        signal.iloc[i] = position

                elif strategie == "Croisement MA50 / MA200 (Golden/Death Cross)":
                    ma50  = prix_bt.rolling(50).mean()
                    ma200 = prix_bt.rolling(200).mean()
                    for i in range(1, len(prix_bt)):
                        if pd.isna(ma50.iloc[i]) or pd.isna(ma200.iloc[i]): continue
                        if ma50.iloc[i] > ma200.iloc[i]:
                            signal.iloc[i] = 1
                        else:
                            signal.iloc[i] = 0

                elif strategie == "MACD — Croisement Signal":
                    macd_bt, sig_bt, _ = calcul_macd(prix_bt)
                    for i in range(1, len(prix_bt)):
                        if pd.isna(macd_bt.iloc[i]) or pd.isna(sig_bt.iloc[i]): continue
                        signal.iloc[i] = 1 if macd_bt.iloc[i] > sig_bt.iloc[i] else 0

                elif strategie == "Bollinger — Rebond sur bandes":
                    _, bb_h, bb_l = calcul_bollinger(prix_bt, fenetre=bb_win)
                    position = 0
                    for i in range(len(prix_bt)):
                        if pd.isna(bb_h.iloc[i]): continue
                        if position == 0 and prix_bt.iloc[i] <= bb_l.iloc[i]:
                            position = 1
                        elif position == 1 and prix_bt.iloc[i] >= bb_h.iloc[i]:
                            position = 0
                        signal.iloc[i] = position

                # Rendements
                rendements     = prix_bt.pct_change().fillna(0)
                rdt_strategie  = rendements * signal.shift(1).fillna(0)
                rdt_bah        = rendements

                # Courbes de valeur (base 100)
                val_strat = (1 + rdt_strategie).cumprod() * 100
                val_bah   = (1 + rdt_bah).cumprod() * 100

                # Métriques finales
                perf_strat = float(val_strat.iloc[-1] - 100)
                perf_bah   = float(val_bah.iloc[-1]   - 100)

                def sharpe_serie(r):
                    std = r.std()
                    if std == 0: return 0
                    return float((r.mean() - 0.03/252) / std * np.sqrt(252))

                sh_strat = sharpe_serie(rdt_strategie)
                sh_bah   = sharpe_serie(rdt_bah)

                def max_dd(v):
                    return float(((v - v.cummax()) / v.cummax() * 100).min())

                dd_strat = max_dd(val_strat)
                dd_bah   = max_dd(val_bah)

                # Nb de trades
                nb_trades = int(signal.diff().abs().sum() / 2)
                taux_investi = float(signal.mean() * 100)

            # ── Résultats ─────────────────────────────────────
            diff_perf = perf_strat - perf_bah
            winner    = "Stratégie" if diff_perf >= 0 else "Buy & Hold"
            col_w = "#2d9e5f" if diff_perf >= 0 else "#e05252"

            st.markdown(
                f"<div style='border:2px solid {col_w};border-radius:10px;"
                f"padding:12px 18px;margin:8px 0;'>"
                f"<b style='font-size:1.1rem;color:{col_w};'>"
                f"{'✅' if diff_perf >= 0 else '❌'} {winner} gagne de {abs(diff_perf):.1f} pts</b>"
                f"</div>",
                unsafe_allow_html=True
            )

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Perf Stratégie",  f"{perf_strat:+.1f}%",
                      f"{diff_perf:+.1f}% vs B&H",
                      delta_color="normal" if diff_perf >= 0 else "inverse")
            m2.metric("Perf Buy & Hold", f"{perf_bah:+.1f}%")
            m3.metric("Sharpe Stratégie", f"{sh_strat:.2f}",
                      f"{sh_strat-sh_bah:+.2f} vs B&H",
                      delta_color="normal" if sh_strat >= sh_bah else "inverse")
            m4.metric("Drawdown Stratégie", f"{dd_strat:.1f}%",
                      f"{dd_strat-dd_bah:+.1f}% vs B&H",
                      delta_color="inverse" if dd_strat > dd_bah else "normal")

            st.caption(f"Nombre de trades : **{nb_trades}** · Temps investi : **{taux_investi:.0f}%**")

            # Graphique comparatif
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(
                x=val_strat.index, y=val_strat,
                name=f"⚗️ {strategie}", mode="lines",
                line=dict(width=2.5, color="#00D4AA"),
            ))
            fig_bt.add_trace(go.Scatter(
                x=val_bah.index, y=val_bah,
                name="📦 Buy & Hold", mode="lines",
                line=dict(width=2, color="#8888FF", dash="dash"),
            ))
            # Zones d'investissement (signal = 1)
            in_trade = False
            start_trade = None
            for i, (idx, s) in enumerate(signal.items()):
                if s == 1 and not in_trade:
                    in_trade = True; start_trade = idx
                elif s == 0 and in_trade:
                    in_trade = False
                    fig_bt.add_vrect(
                        x0=start_trade, x1=idx,
                        fillcolor="rgba(0,212,170,0.06)",
                        line_width=0, layer="below"
                    )
            if in_trade and start_trade:
                fig_bt.add_vrect(
                    x0=start_trade, x1=val_strat.index[-1],
                    fillcolor="rgba(0,212,170,0.06)", line_width=0, layer="below"
                )

            fig_bt.add_hline(y=100, line_dash="dot",
                             line_color="rgba(255,255,255,0.2)")
            fig_bt.update_layout(
                height=480, margin=dict(l=10,r=10,t=30,b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
                hovermode="x unified",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#FAFAFA"),
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)",
                           tickformat="%Y", dtick="M12", ticklabelmode="period"),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)",
                           tickformat=".0f"),
            )
            st.plotly_chart(fig_bt, width="stretch", key="fig_backtest")
            st.caption(
                "Les zones vertes indiquent les périodes où la stratégie est investie. "
                "⚠️ Backtest sans frais de transaction ni slippage — les performances passées ne garantissent pas les résultats futurs."
            )
        else:
            st.info("Configure les paramètres ci-dessus puis clique sur **▶️ Lancer le backtest**.")


# ════════════════════════════════════════════════════════════
#  ONGLET 6 — FICHES ACTIFS
# ════════════════════════════════════════════════════════════
with onglet6:
    st.title("Fiches actifs")
    if not selection:
        st.info("👈 Sélectionne des actifs.")
    else:
        ticker_fiche = st.selectbox("Choisir un actif :", selection)
        with st.spinner(f"Chargement {ticker_fiche}..."):
            fiche = get_fiche(ticker_fiche)
        if not fiche:
            st.error("Impossible de récupérer les données.")
        else:
            tab_fiche, tab_dcf = st.tabs(["📋 Fiche fondamentale", "🔬 Valorisation DCF"])

            with tab_fiche:
                st.subheader(fiche.get("Nom", ticker_fiche))

                # ── Ligne 1 : prix / capi / dividende ────────────
                c1, c2, c3 = st.columns(3)
                prix = fiche.get("Prix actuel"); var = fiche.get("Variation jour")
                c1.metric("Prix actuel",
                          f"{prix:.2f} {fiche.get('Devise','')}" if prix else "—",
                          f"{var:+.2f}%" if var else None)
                c2.metric("Capitalisation", fmt_cap(fiche.get("Capitalisation")))
                div = fiche.get("Dividende %")
                if div:
                    div_pct = div * 100 if div < 1 else div
                    c3.metric("Dividende", f"{div_pct:.2f}%",
                              help="Rendement annuel du dividende versé aux actionnaires.")
                else:
                    c3.metric("Dividende", "Aucun",
                              help="Cet actif ne verse pas de dividende (ou donnée indisponible).")
                st.divider()

                # ── Ligne 2 : P/E / 52w ──────────────────────────
                c4, c5, c6 = st.columns(3)
                pe = fiche.get("P/E ratio"); pef = fiche.get("P/E forward")
                c4.metric("P/E ratio", f"{pe:.1f}x" if pe else "—",
                          help="Combien tu paies pour 1€ de bénéfice.\n< 15 : sous-évalué · 15–25 : normal · > 25 : cher")
                c5.metric("P/E forward", f"{pef:.1f}x" if pef else "—",
                          help="P/E basé sur les bénéfices anticipés l'an prochain.")
                h52 = fiche.get("52w Haut"); l52 = fiche.get("52w Bas")
                c6.metric("52 semaines", f"{l52:.2f} — {h52:.2f}" if h52 and l52 else "—")
                if h52 and l52 and prix and h52 > l52:
                    pos = (prix - l52) / (h52 - l52)
                    st.caption(f"Position dans la fourchette 52 sem. : **{pos*100:.0f}%** du range (0% = bas · 100% = haut)")
                    st.progress(float(pos))
                st.divider()

                # ── Consensus analystes ───────────────────────────
                st.subheader("Consensus analystes")
                reco   = fiche.get("Reco label", "—")
                color  = fiche.get("Reco color", "#888")
                nb_ana = fiche.get("Nb analystes")
                obj_m  = fiche.get("Objectif moyen")
                obj_b  = fiche.get("Objectif bas")
                obj_h  = fiche.get("Objectif haut")
                ca1, ca2, ca3, ca4 = st.columns(4)
                ca1.markdown(
                    f"<div style='border:1px solid {color}55; border-radius:8px; padding:10px; text-align:center;'>"
                    f"<div style='font-size:0.75rem; color:#aaa;'>Recommandation</div>"
                    f"<div style='font-size:1.2rem; font-weight:700; color:{color};'>{reco}</div>"
                    f"<div style='font-size:0.75rem; color:#aaa;'>{f'{nb_ana} analystes' if nb_ana else ''}</div>"
                    f"</div>", unsafe_allow_html=True)
                if obj_m and prix:
                    upside = (obj_m - prix) / prix * 100
                    ca2.metric("Objectif moyen", f"{obj_m:.2f}", f"{upside:+.1f}% vs prix actuel",
                               delta_color="normal" if upside >= 0 else "inverse",
                               help="Prix cible moyen des analystes.")
                else:
                    ca2.metric("Objectif moyen", "—")
                ca3.metric("Objectif bas",  f"{obj_b:.2f}" if obj_b else "—",
                           help="Cible la plus pessimiste des analystes.")
                ca4.metric("Objectif haut", f"{obj_h:.2f}" if obj_h else "—",
                           help="Cible la plus optimiste des analystes.")
                if obj_b and obj_h and prix and obj_h > obj_b:
                    pos_obj = max(0.0, min(1.0, (prix - obj_b) / (obj_h - obj_b)))
                    st.caption(f"Prix actuel dans la fourchette analystes : **{obj_b:.2f}** (bas) — **{prix:.2f}** (actuel) — **{obj_h:.2f}** (haut)")
                    st.progress(float(pos_obj))
                st.divider()

                # ── Dates importantes ─────────────────────────────
                st.subheader("Prochaines dates importantes")
                cd1, cd2, cd3 = st.columns(3)
                ex_div = fiche.get("Ex-dividende")
                if ex_div:
                    jours_div = (ex_div - date.today()).days
                    label_div = f"Dans {jours_div}j" if jours_div > 0 else ("🔔 Aujourd'hui !" if jours_div == 0 else f"Il y a {-jours_div}j")
                    cd1.metric("📆 Ex-dividende", str(ex_div), label_div,
                               help="Date à laquelle tu dois détenir l'action pour recevoir le prochain dividende.")
                else:
                    cd1.metric("📆 Ex-dividende", "—")
                earn = fiche.get("Résultats")
                if earn:
                    jours_earn = (earn - date.today()).days
                    label_earn = f"Dans {jours_earn}j" if jours_earn > 0 else ("🔔 Aujourd'hui !" if jours_earn == 0 else f"Il y a {-jours_earn}j")
                    cd2.metric("📊 Résultats", str(earn), label_earn,
                               help="Prochaine publication des résultats trimestriels.")
                else:
                    cd2.metric("📊 Résultats", "—")
                cd3.metric("🌍 Pays / Devise", f"{fiche.get('Pays','—')} · {fiche.get('Devise','—')}")
                st.divider()
                st.markdown(f"**Secteur :** {fiche.get('Secteur','—')}  |  **Industrie :** {fiche.get('Industrie','—')}")

            # ════════════════════════════════════════════════
            #  SOUS-ONGLET DCF
            # ════════════════════════════════════════════════
            with tab_dcf:
                st.subheader(f"Valorisation DCF — {fiche.get('Nom', ticker_fiche)}")
                st.caption(
                    "Estimation de la **valeur intrinsèque** par actualisation des flux de trésorerie (DCF simplifié). "
                    "Les hypothèses sont paramétrables. Ce modèle est indicatif — il ne remplace pas une analyse professionnelle."
                )

                prix_dcf = fiche.get("Prix actuel")
                fcf      = fiche.get("FCF")
                shares   = fiche.get("Shares")
                eps      = fiche.get("EPS")
                beta     = fiche.get("Beta")
                cr_bpa   = fiche.get("Croissance_BPA")
                dette    = fiche.get("Total_debt") or 0
                cash     = fiche.get("Cash") or 0

                # ── Sélection méthode ─────────────────────────────
                methode = st.radio(
                    "Méthode de valorisation",
                    ["DCF — Free Cash Flow", "DCF — BPA (Graham adapté)", "Valeur de Graham"],
                    horizontal=True,
                    help="• FCF : actualise les flux de trésorerie disponibles\n"
                         "• BPA : actualise les bénéfices par action\n"
                         "• Graham : formule simplifiée de Benjamin Graham"
                )
                st.divider()

                # ── Paramètres ajustables ─────────────────────────
                p1, p2, p3 = st.columns(3)

                # Taux de croissance
                if cr_bpa and cr_bpa > 0:
                    g_default = min(round(cr_bpa * 100, 1), 30.0)
                else:
                    g_default = 8.0
                g_court = p1.slider(
                    "Croissance court terme (5 ans, %/an)", 0.0, 40.0, float(g_default), 0.5,
                    help="Taux de croissance annuel appliqué sur les 5 premières années.")
                g_long  = p2.slider(
                    "Croissance long terme (5→10 ans, %/an)", 0.0, 20.0, min(float(g_default)*0.6, 12.0), 0.5,
                    help="Taux de croissance plus conservateur pour les années 6 à 10.")
                g_perp  = p3.slider(
                    "Taux perpétuel (%/an)", 0.5, 5.0, 2.5, 0.1,
                    help="Taux de croissance à l'infini (≈ croissance du PIB mondial). Standard : 2–3%.")

                p4, p5, p6 = st.columns(3)
                # Taux d'actualisation (WACC simplifié)
                if beta and 0.3 < beta < 4:
                    wacc_default = round(5.0 + beta * 4.0, 1)  # rf=5% + prime risque
                else:
                    wacc_default = 10.0
                taux_actu = p4.slider(
                    "Taux d'actualisation / WACC (%)", 5.0, 20.0, float(min(wacc_default, 15.0)), 0.5,
                    help=f"Coût du capital. Calculé à partir du beta ({beta:.2f}) : rf 5% + prime risque.\n"
                         f"Élevé = plus sévère. Standard : 8–12%." if beta else
                    "Coût du capital. Beta indisponible, valeur par défaut utilisée (10%).\n"
                    "Élevé = plus sévère. Standard : 8–12%.")
                marge_secu = p5.slider(
                    "Marge de sécurité (%)", 0, 50, 25, 5,
                    help="Décote appliquée à la valeur intrinsèque calculée. "
                         "Buffett recommande 25–50% pour compenser les erreurs du modèle.")
                horizon = p6.selectbox("Horizon de projection", [10, 8, 5], index=0,
                    help="Nombre d'années de flux projetés avant la valeur terminale.")

                st.divider()

                # ── Calcul DCF ────────────────────────────────────
                valeur_intrinsec = None
                flux_base        = None
                flux_annuels     = []
                label_flux       = ""

                if methode == "DCF — Free Cash Flow":
                    if fcf and shares and shares > 0:
                        flux_base  = fcf / shares
                        label_flux = f"FCF/action : {flux_base:.2f} {fiche.get('Devise','')}"
                    elif eps:
                        flux_base  = eps * 0.7   # approximation FCF ≈ 70% du BPA
                        label_flux = f"BPA × 0.7 (proxy FCF) : {flux_base:.2f} {fiche.get('Devise','')}"

                elif methode == "DCF — BPA (Graham adapté)":
                    if eps:
                        flux_base  = eps
                        label_flux = f"BPA (EPS) : {flux_base:.2f} {fiche.get('Devise','')}"

                elif methode == "Valeur de Graham":
                    # V = EPS × (8.5 + 2g) × 4.4 / Y (Y = taux oblig. AAA, proxy = taux_actu)
                    if eps and eps > 0:
                        g_graham = min(g_court, 25)
                        v_graham = eps * (8.5 + 2 * g_graham) * 4.4 / taux_actu
                        valeur_intrinsec = v_graham
                        label_flux = f"BPA : {eps:.2f} · g court terme : {g_graham:.1f}%"

                # Projection DCF classique
                if flux_base and methode != "Valeur de Graham":
                    wacc = taux_actu / 100
                    gC   = g_court / 100
                    gL   = g_long  / 100
                    gP   = g_perp  / 100

                    pv_total = 0.0
                    flux_annuels = []
                    f_courant = flux_base
                    for annee in range(1, int(horizon) + 1):
                        g_an = gC if annee <= 5 else gL
                        f_courant *= (1 + g_an)
                        pv = f_courant / (1 + wacc) ** annee
                        pv_total += pv
                        flux_annuels.append({"Année": f"A+{annee}", "Flux projeté": round(f_courant, 2), "VA": round(pv, 2)})

                    # Valeur terminale (Gordon)
                    flux_terminal  = f_courant * (1 + gP)
                    valeur_term    = flux_terminal / (wacc - gP) if wacc > gP else 0
                    pv_terminale   = valeur_term / (1 + wacc) ** int(horizon)
                    pv_total      += pv_terminale
                    valeur_intrinsec = pv_total

                # Ajout dette nette / action
                if valeur_intrinsec and shares and shares > 0:
                    dette_nette_par_action = (dette - cash) / shares
                    valeur_intrinsec -= dette_nette_par_action

                # Valeur avec marge de sécurité
                valeur_avec_marge = valeur_intrinsec * (1 - marge_secu / 100) if valeur_intrinsec else None

                # ── Affichage résultat ────────────────────────────
                if valeur_intrinsec is None or valeur_intrinsec <= 0:
                    st.warning(
                        "⚠️ Données insuffisantes pour calculer une valeur intrinsèque. "
                        "Yahoo Finance ne retourne pas de FCF/BPA pour cet actif "
                        "(fréquent sur les ETFs, indices, crypto et certaines small caps)."
                    )
                else:
                    # ── Verdict ───────────────────────────────────
                    if prix_dcf:
                        ratio = prix_dcf / valeur_intrinsec
                        ratio_marge = prix_dcf / valeur_avec_marge if valeur_avec_marge else None

                        if   ratio < 0.7:   verdict, vcolor, emoji = "🟢 Fortement sous-évalué",  "#2d9e5f", "📉"
                        elif ratio < 0.9:   verdict, vcolor, emoji = "🟢 Sous-évalué",             "#2d9e5f", "📉"
                        elif ratio < 1.1:   verdict, vcolor, emoji = "🟡 Correctement valorisé",  "#FFD700", "⚖️"
                        elif ratio < 1.4:   verdict, vcolor, emoji = "🟠 Légèrement surévalué",   "#FF8C00", "📈"
                        else:               verdict, vcolor, emoji = "🔴 Fortement surévalué",    "#e05252", "🚨"

                        # Bloc verdict principal
                        st.markdown(f"""
<div style="border:2px solid {vcolor}55; background:{vcolor}12; border-radius:12px;
            padding:20px 24px; margin:10px 0 18px 0;">
  <div style="font-size:1.5rem; font-weight:800; color:{vcolor};">{emoji} {verdict}</div>
  <div style="margin-top:10px; display:flex; gap:40px; flex-wrap:wrap;">
    <div>
      <div style="font-size:0.75rem; color:#aaa;">Prix actuel</div>
      <div style="font-size:1.3rem; font-weight:700;">{prix_dcf:.2f} {fiche.get('Devise','')}</div>
    </div>
    <div>
      <div style="font-size:0.75rem; color:#aaa;">Valeur intrinsèque</div>
      <div style="font-size:1.3rem; font-weight:700; color:{vcolor};">{valeur_intrinsec:.2f} {fiche.get('Devise','')}</div>
    </div>
    <div>
      <div style="font-size:0.75rem; color:#aaa;">Avec marge de sécurité ({marge_secu}%)</div>
      <div style="font-size:1.3rem; font-weight:700; color:{vcolor}55;">{valeur_avec_marge:.2f} {fiche.get('Devise','')}</div>
    </div>
    <div>
      <div style="font-size:0.75rem; color:#aaa;">Ratio Prix / Valeur</div>
      <div style="font-size:1.3rem; font-weight:700; color:{vcolor};">{ratio:.2f}x</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

                        # Jauge visuelle
                        st.caption(f"Base de calcul → {label_flux}")
                        bornes  = [0.5, 0.7, 0.9, 1.1, 1.4, 2.5]
                        labels_ = ["< 0.7×", "0.7–0.9×", "0.9–1.1×", "1.1–1.4×", "> 1.4×"]
                        colors_ = ["#2d9e5f","#5cb85c","#FFD700","#FF8C00","#e05252"]
                        fig_gauge = go.Figure(go.Indicator(
                            mode="gauge+number",
                            value=min(ratio, 2.4),
                            number={"suffix": "×", "font": {"size": 28}},
                            gauge={
                                "axis": {"range": [0, 2.5], "tickvals": bornes,
                                         "ticktext": [f"{b}×" for b in bornes]},
                                "bar": {"color": vcolor, "thickness": 0.25},
                                "steps": [
                                    {"range": [0,    0.7],  "color": "rgba(45,158,95,0.13)"},
                                    {"range": [0.7,  0.9],  "color": "rgba(92,184,92,0.13)"},
                                    {"range": [0.9,  1.1],  "color": "rgba(255,215,0,0.13)"},
                                    {"range": [1.1,  1.4],  "color": "rgba(255,140,0,0.13)"},
                                    {"range": [1.4,  2.5],  "color": "rgba(224,82,82,0.13)"},
                                ],
                                "threshold": {
                                    "line": {"color": "#fff", "width": 3},
                                    "thickness": 0.8, "value": 1.0
                                },
                            },
                            title={"text": "Ratio Prix / Valeur intrinsèque", "font": {"size": 14}},
                        ))
                        fig_gauge.update_layout(
                            height=240, margin=dict(l=30, r=30, t=40, b=10),
                            paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#FAFAFA")
                        )
                        st.plotly_chart(fig_gauge, width="stretch")

                    # ── Tableau flux projetés ──────────────────────
                    if methode != "Valeur de Graham" and flux_annuels:
                        with st.expander("📋 Détail des flux projetés"):
                            df_flux = pd.DataFrame(flux_annuels)
                            df_flux["Flux projeté"] = df_flux["Flux projeté"].map(lambda x: f"{x:.2f}")
                            df_flux["VA"]            = df_flux["VA"].map(lambda x: f"{x:.2f}")
                            df_flux.loc[len(df_flux)] = {
                                "Année": "Valeur terminale",
                                "Flux projeté": f"{flux_terminal:.2f}",
                                "VA": f"{pv_terminale:.2f}"
                            }
                            st.dataframe(df_flux, width="stretch", hide_index=True)
                            st.caption(
                                f"Dette nette/action déduite : {dette_nette_par_action:.2f} {fiche.get('Devise','')}"
                                if shares and shares > 0 else ""
                            )

                    # ── Données brutes utilisées ───────────────────
                    with st.expander("📊 Données fondamentales utilisées"):
                        fond_data = {
                            "Indicateur": ["FCF annuel","FCF/action","BPA (EPS)","Beta","Croissance BPA",
                                           "Dette totale","Trésorerie","Marge nette","ROE","P/B ratio","P/S ratio"],
                            "Valeur": [
                                fmt_cap(fiche.get("FCF")),
                                f"{fiche.get('FCF_per_share'):.2f}" if fiche.get("FCF_per_share") else "—",
                                f"{fiche.get('EPS'):.2f}"          if fiche.get("EPS")            else "—",
                                f"{fiche.get('Beta'):.2f}"         if fiche.get("Beta")           else "—",
                                f"{fiche.get('Croissance_BPA')*100:.1f}%" if fiche.get("Croissance_BPA") else "—",
                                fmt_cap(fiche.get("Total_debt")),
                                fmt_cap(fiche.get("Cash")),
                                f"{fiche.get('Marge_nette')*100:.1f}%" if fiche.get("Marge_nette") else "—",
                                f"{fiche.get('ROE')*100:.1f}%"         if fiche.get("ROE")         else "—",
                                f"{fiche.get('PB_ratio'):.2f}x"        if fiche.get("PB_ratio")    else "—",
                                f"{fiche.get('PS_ratio'):.2f}x"        if fiche.get("PS_ratio")    else "—",
                            ]
                        }
                        st.dataframe(pd.DataFrame(fond_data), width="stretch", hide_index=True)

                    st.info(
                        "⚠️ **Avertissement** : Ce DCF est une estimation simplifiée basée sur des données Yahoo Finance. "
                        "Les projections de croissance sont incertaines. Utilisez ce modèle comme point de départ, "
                        "pas comme seule base de décision d'investissement."
                    )


# ════════════════════════════════════════════════════════════
#  ONGLET MACRO
# ════════════════════════════════════════════════════════════
with onglet_macro:
    st.title("Tableau de Bord Macro")
    st.caption(
        "Vue d'ensemble des grands indicateurs macroéconomiques : sentiment de marché, indices actions, "
        "devises, matières premières, taux et obligations. Données rafraîchies toutes les 15 min."
    )

    if st.button("🔄 Rafraîchir les données macro", help="Vide le cache et recharge tous les indicateurs."):
        get_macro_quote.clear()
        st.rerun()

    # ── Sélection des catégories à afficher ──────────────────
    toutes_cats = list(MACRO_CATALOGUE.keys())
    cats_choisies = st.multiselect(
        "Catégories à afficher",
        toutes_cats,
        default=toutes_cats,
        label_visibility="collapsed",
    )
    st.divider()

    # ── Helpers d'affichage ───────────────────────────────────
    def couleur_var(v, inverse=False):
        if v is None: return "⬜"
        if inverse:
            return "🟢" if v < 0 else ("🔴" if v > 0 else "⬜")
        return "🟢" if v > 0 else ("🔴" if v < 0 else "⬜")

    def fmt_prix(v, unite):
        if v is None: return "—"
        if unite == "%": return f"{v:.2f}%"
        if v > 1000:     return f"{v:,.0f} {unite}".strip()
        if v > 10:       return f"{v:.2f} {unite}".strip()
        return f"{v:.4f} {unite}".strip()

    def mini_sparkline(serie: pd.Series, couleur: str) -> go.Figure:
        fig = go.Figure(go.Scatter(
            x=serie.index, y=serie.values, mode="lines",
            line=dict(width=1.5, color=couleur), fill="tozeroy",
            fillcolor=couleur.replace(")", ",0.08)").replace("rgb", "rgba") if "rgb" in couleur
                     else f"rgba(0,212,170,0.08)",
        ))
        fig.update_layout(
            height=60, margin=dict(l=0,r=0,t=0,b=0),
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        return fig

    # ── Rendu par catégorie ───────────────────────────────────
    for cat in cats_choisies:
        instruments = MACRO_CATALOGUE[cat]
        st.subheader(cat)

        # Chargement de tous les instruments en parallèle (cache)
        donnees = {}
        with st.spinner(f"Chargement {cat}…"):
            for inst in instruments:
                donnees[inst["ticker"]] = get_macro_quote(inst["ticker"])

        # Grille de cartes : 3 par ligne
        nb_cols = 3
        rows = [instruments[i:i+nb_cols] for i in range(0, len(instruments), nb_cols)]

        for row_idx, row in enumerate(rows):
            cols = st.columns(nb_cols)
            for j, inst in enumerate(row):
                d = donnees[inst["ticker"]]
                prix    = d["prix"]
                var_pct = d["var_pct"]
                var_52  = d["var_52"]
                hist    = d["hist"]
                emoji   = couleur_var(var_pct, inst["inverse"])
                # Clé globalement unique : catégorie + position dans la grille
                spark_key = f"spark_{cat}_{row_idx}_{j}"

                with cols[j]:
                    # En-tête de carte
                    st.markdown(f"**{inst['label']}**")
                    st.caption(f"`{inst['ticker']}`")

                    # Prix + variation jour
                    prix_str = fmt_prix(prix, inst["unite"])
                    delta_str = f"{var_pct:+.2f}%" if var_pct is not None else "—"
                    st.metric(
                        label="",
                        value=prix_str,
                        delta=delta_str,
                        delta_color="inverse" if inst["inverse"] else "normal",
                        help=inst["info"],
                    )

                    # Variation 1 an
                    if var_52 is not None:
                        signe = "+" if var_52 >= 0 else ""
                        couleur_52 = "#2d9e5f" if (var_52 >= 0) != inst["inverse"] else "#e05252"
                        st.markdown(
                            f"<span style='font-size:0.75rem;color:{couleur_52}'>"
                            f"52 sem : {signe}{var_52:.1f}%</span>",
                            unsafe_allow_html=True,
                        )

                    # Sparkline 1 an
                    if not hist.empty and len(hist) > 5:
                        c_spark = "#2d9e5f" if (var_52 or 0) >= 0 else "#e05252"
                        if inst["inverse"]:
                            c_spark = "#e05252" if (var_52 or 0) >= 0 else "#2d9e5f"
                        st.plotly_chart(mini_sparkline(hist, c_spark),
                                        width="stretch", config={"staticPlot": True},
                                        key=spark_key)

            # Colonnes vides si row incomplète
            for k in range(len(row), nb_cols):
                cols[k].empty()

        st.divider()

    # ── Section analyse : courbe de taux US (yield curve) ────
    if "🏦 Taux & Obligations" in cats_choisies:
        st.subheader("Courbe des taux US (Yield Curve)")
        st.caption(
            "Quand les taux courts dépassent les taux longs (courbe inversée), "
            "c'est historiquement un signal précurseur de récession (avec 12–18 mois de délai)."
        )
        taux_reels = {
            "3 mois": "^IRX",
            "10 ans": "^TNX",
            "30 ans": "^TYX",
        }
        vals_courbe = {}
        for label, tk in taux_reels.items():
            d = get_macro_quote(tk)
            if d["prix"]: vals_courbe[label] = d["prix"]

        if vals_courbe:
            fig_yc = go.Figure(go.Scatter(
                x=list(vals_courbe.keys()),
                y=list(vals_courbe.values()),
                mode="lines+markers",
                line=dict(width=2.5, color="#00D4AA"),
                marker=dict(size=8, color="#00D4AA"),
                fill="tozeroy", fillcolor="rgba(0,212,170,0.07)",
            ))
            fig_yc.update_layout(
                height=280, margin=dict(l=10,r=10,t=10,b=10),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#FAFAFA"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)", ticksuffix="%"),
                hovermode="x unified",
            )
            st.plotly_chart(fig_yc, width="stretch")

            # Signal d'inversion
            t3m = vals_courbe.get("3 mois")
            t10 = vals_courbe.get("10 ans")
            if t3m and t10:
                spread = t10 - t3m
                if spread < 0:
                    st.error(f"⚠️ **Courbe inversée** — Spread 10 ans – 3 mois : {spread:+.2f}% → Signal historique de récession à venir.")
                elif spread < 0.5:
                    st.warning(f"🟡 **Courbe plate** — Spread 10 ans – 3 mois : {spread:+.2f}% → Prudence, l'économie ralentit.")
                else:
                    st.success(f"🟢 **Courbe normale** — Spread 10 ans – 3 mois : {spread:+.2f}%")
        st.divider()

    # ── Tableau récapitulatif téléchargeable ──────────────────
    st.subheader("Tableau récapitulatif")
    lignes = []
    for cat in cats_choisies:
        for inst in MACRO_CATALOGUE[cat]:
            d = get_macro_quote(inst["ticker"])
            lignes.append({
                "Catégorie":   cat,
                "Instrument":  inst["label"],
                "Ticker":      inst["ticker"],
                "Prix":        fmt_prix(d["prix"], inst["unite"]),
                "Var. jour":   f"{d['var_pct']:+.2f}%" if d["var_pct"] is not None else "—",
                "Var. 52 sem": f"{d['var_52']:+.1f}%" if d["var_52"] is not None else "—",
            })
    if lignes:
        df_recap = pd.DataFrame(lignes)
        st.dataframe(df_recap, width="stretch", hide_index=True)
        csv_macro = df_recap.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exporter CSV", data=csv_macro,
                           file_name="macro_snapshot.csv", mime="text/csv")


# ════════════════════════════════════════════════════════════
#  ONGLET NEWS — ACTUALITÉS
# ════════════════════════════════════════════════════════════
with onglet_news:
    st.title("Actualités financières")
    st.caption("Dernières nouvelles issues de Yahoo Finance pour chaque actif sélectionné.")

    if not selection:
        st.info("👈 Sélectionne des actifs dans le panneau latéral.")
    else:
        col_sel, col_nb, col_btn = st.columns([2, 2, 1])
        with col_sel:
            ticker_news = st.selectbox("Actif", selection,
                help="Choisis un actif pour voir ses actualités récentes.")
        with col_nb:
            nb_articles = st.slider("Nombre d'articles", 3, 15, 8)
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 Rafraîchir", help="Vide le cache et recharge les news."):
                get_news.clear()
                st.rerun()

        with st.spinner(f"Chargement des actualités pour {ticker_news}…"):
            articles = get_news(ticker_news)

        if not articles:
            st.warning("Aucune actualité disponible pour ce ticker.")
        else:
            arts = articles[:nb_articles]
            st.caption(f"**{len(arts)} article(s)** trouvé(s) pour `{ticker_news}`")
            st.divider()

            for art in arts:
                has_thumb = bool(art["thumb"])
                if has_thumb:
                    img_col, txt_col = st.columns([1, 4])
                else:
                    img_col, txt_col = None, st.container()

                if has_thumb and img_col:
                    with img_col:
                        st.image(art["thumb"], width="stretch")

                with txt_col:
                    title_md = f"[{art['title']}]({art['url']})" if art["url"] else art["title"]
                    st.markdown(f"### {title_md}")

                    meta_parts = []
                    if art["source"]:
                        meta_parts.append(f"📡 **{art['source']}**")
                    if art["date"]:
                        try:
                            delta = datetime.utcnow() - art["date"].replace(tzinfo=None)
                            if delta.days == 0:
                                h = delta.seconds // 3600
                                meta_parts.append(f"🕐 il y a {h}h" if h else "🕐 à l'instant")
                            else:
                                meta_parts.append(f"📅 {art['date'].strftime('%d %b %Y')}")
                        except Exception:
                            pass
                    if meta_parts:
                        st.caption("  ·  ".join(meta_parts))

                    if art["summary"]:
                        st.markdown(
                            f"<small>{art['summary'][:300]}{'…' if len(art['summary']) > 300 else ''}</small>",
                            unsafe_allow_html=True)

                    if art["url"]:
                        st.markdown(f"[🔗 Lire l'article]({art['url']})", unsafe_allow_html=False)

                st.divider()


# ════════════════════════════════════════════════════════════
#  ONGLET ALERTES
# ════════════════════════════════════════════════════════════
with onglet_alertes:
    st.title("Alertes de prix")
    st.caption(
        "Configure des seuils de prix pour tes actifs. "
        "À chaque chargement de l'app, les alertes déclenchées s'affichent en haut de cet onglet."
    )

    if not selection and not st.session_state.alertes:
        st.info("👈 Sélectionne des actifs pour configurer des alertes.")
    else:
        # ── Vérification des alertes au chargement ─────────────
        alertes_declenchees = []
        tous_tickers_alertes = list(st.session_state.alertes.keys())

        if tous_tickers_alertes:
            with st.spinner("🔍 Vérification des alertes…"):
                for tk_a in tous_tickers_alertes:
                    cfg = st.session_state.alertes[tk_a]
                    try:
                        fi = yf.Ticker(tk_a).fast_info
                        prix_actuel = fi.get("lastPrice") if fi else None
                        if prix_actuel is None:
                            prix_actuel = yf.Ticker(tk_a).info.get("regularMarketPrice")
                        if prix_actuel is None:
                            continue
                        seuil_haut = cfg.get("above")
                        seuil_bas  = cfg.get("below")
                        if seuil_haut and prix_actuel >= seuil_haut:
                            alertes_declenchees.append({
                                "ticker": tk_a, "prix": prix_actuel,
                                "type": "above", "seuil": seuil_haut,
                                "msg": f"📈 **{tk_a}** a dépassé le seuil HAUT : {prix_actuel:.2f} ≥ {seuil_haut:.2f}",
                                "color": "#2d9e5f",
                            })
                        if seuil_bas and prix_actuel <= seuil_bas:
                            alertes_declenchees.append({
                                "ticker": tk_a, "prix": prix_actuel,
                                "type": "below", "seuil": seuil_bas,
                                "msg": f"📉 **{tk_a}** a franchi le seuil BAS : {prix_actuel:.2f} ≤ {seuil_bas:.2f}",
                                "color": "#e05252",
                            })
                    except Exception:
                        st.warning(f"⚠️ Impossible de vérifier le prix de {tk_a}.")

        # ── Affichage des alertes déclenchées ──────────────────
        if alertes_declenchees:
            st.subheader(f"{len(alertes_declenchees)} alerte(s) déclenchée(s) !")
            for al in alertes_declenchees:
                st.markdown(
                    f"<div style='border-left: 4px solid {al['color']}; "
                    f"background:{al['color']}18; border-radius:6px; "
                    f"padding:12px 16px; margin:6px 0;'>"
                    f"{al['msg']}"
                    f"</div>",
                    unsafe_allow_html=True
                )
            st.divider()
        elif tous_tickers_alertes:
            st.success("✅ Aucune alerte déclenchée pour le moment.")
            st.divider()

        # ── Configuration des alertes ──────────────────────────
        st.subheader("Configurer les seuils")

        # Actifs disponibles : sélection + tickers déjà en alerte
        tickers_disponibles = sorted(set(selection) | set(st.session_state.alertes.keys()))

        if not tickers_disponibles:
            st.info("👈 Sélectionne des actifs dans le panneau latéral.")
        else:
            ticker_alerte = st.selectbox(
                "Actif à surveiller", tickers_disponibles, key="sel_alerte"
            )

            cfg_existant = st.session_state.alertes.get(ticker_alerte, {})

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**📈 Alerte HAUSSE**")
                st.caption("Déclenche si le prix passe AU-DESSUS de ce seuil")
                val_above = cfg_existant.get("above", None)
                above_actif = st.toggle(
                    "Activer seuil haut", value=val_above is not None,
                    key=f"tog_above_{ticker_alerte}"
                )
                seuil_above = None
                if above_actif:
                    seuil_above = st.number_input(
                        "Seuil haut (prix)",
                        min_value=0.0, value=float(val_above) if val_above else 0.0,
                        step=0.5, format="%.2f",
                        key=f"inp_above_{ticker_alerte}",
                        help="L'alerte se déclenche quand le prix actuel ≥ ce seuil"
                    )

            with col_b:
                st.markdown("**📉 Alerte BAISSE**")
                st.caption("Déclenche si le prix passe EN-DESSOUS de ce seuil")
                val_below = cfg_existant.get("below", None)
                below_actif = st.toggle(
                    "Activer seuil bas", value=val_below is not None,
                    key=f"tog_below_{ticker_alerte}"
                )
                seuil_below = None
                if below_actif:
                    seuil_below = st.number_input(
                        "Seuil bas (prix)",
                        min_value=0.0, value=float(val_below) if val_below else 0.0,
                        step=0.5, format="%.2f",
                        key=f"inp_below_{ticker_alerte}",
                        help="L'alerte se déclenche quand le prix actuel ≤ ce seuil"
                    )

            col_save, col_del = st.columns([2, 1])
            with col_save:
                if st.button("💾 Enregistrer les seuils", key="btn_save_alerte"):
                    nouvelle_cfg = {}
                    if above_actif and seuil_above and seuil_above > 0:
                        nouvelle_cfg["above"] = seuil_above
                    if below_actif and seuil_below and seuil_below > 0:
                        nouvelle_cfg["below"] = seuil_below
                    if nouvelle_cfg:
                        st.session_state.alertes[ticker_alerte] = nouvelle_cfg
                        sauvegarder_alertes_json(st.session_state.alertes)
                        st.success(f"✅ Alertes enregistrées pour {ticker_alerte} !")
                    else:
                        if ticker_alerte in st.session_state.alertes:
                            del st.session_state.alertes[ticker_alerte]
                            sauvegarder_alertes_json(st.session_state.alertes)
                        st.info(f"Aucun seuil actif pour {ticker_alerte}.")

            with col_del:
                if ticker_alerte in st.session_state.alertes:
                    if st.button("🗑️ Supprimer", key="btn_del_alerte"):
                        del st.session_state.alertes[ticker_alerte]
                        sauvegarder_alertes_json(st.session_state.alertes)
                        st.rerun()

            st.divider()

        # ── Récapitulatif de toutes les alertes ────────────────
        if st.session_state.alertes:
            st.subheader("Toutes les alertes actives")
            lignes_al = []
            for tk_a, cfg in st.session_state.alertes.items():
                lignes_al.append({
                    "Ticker":       tk_a,
                    "Seuil haut":   f"{cfg['above']:.2f}" if cfg.get("above") else "—",
                    "Seuil bas":    f"{cfg['below']:.2f}" if cfg.get("below") else "—",
                    "État":         "🚨 Déclenchée" if any(
                        al["ticker"] == tk_a for al in alertes_declenchees
                    ) else "✅ En veille",
                })
            st.dataframe(pd.DataFrame(lignes_al).set_index("Ticker"), width="stretch")
            st.caption(
                "💾 Les alertes sont sauvegardées localement (alertes.json) et persistent entre les sessions. "
                "Recharge la page pour re-vérifier les prix."
            )
        else:
            st.info("Aucune alerte configurée pour l'instant.")


# ════════════════════════════════════════════════════════════
#  ONGLET CALENDRIER ÉCONOMIQUE
# ════════════════════════════════════════════════════════════
with onglet_cal:
    st.title("Calendrier Économique")
    st.caption("Événements macro générés automatiquement (FOMC, BCE, CPI, NFP, PCE, PPI, PIB) + résultats d'entreprises via Yahoo Finance.")

    # ── Génération dynamique du calendrier ──────────────────────
    CALENDRIER = generer_calendrier_macro(horizon_mois=6)
    # Ajouter les dates de résultats des tickers sélectionnés + tickers prédéfinis
    _tickers_earnings = tuple(sorted(set(
        list(TICKERS_APP.get("Actions", [])) + list(selection if selection else [])
    )))
    CALENDRIER += get_earnings_calendar(_tickers_earnings)
    # Dédupliquer par (date, evenement)
    _seen = set()
    _cal_dedup = []
    for e in CALENDRIER:
        key = (e["date"], e["evenement"])
        if key not in _seen:
            _seen.add(key)
            _cal_dedup.append(e)
    CALENDRIER = _cal_dedup
    CALENDRIER.sort(key=lambda x: x["date"])

    # ── Filtres ───────────────────────────────────────────────
    today = date.today()
    categories = ["Tout"] + sorted(set(e["categorie"] for e in CALENDRIER))
    impacts    = ["Tout", "🔴 Élevé", "🟠 Moyen", "🟡 Faible"]
    zones      = ["Tout", "🇺🇸", "🇪🇺"]

    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 2])
    with col_f1:
        filtre_cat = st.selectbox("Catégorie", categories)
    with col_f2:
        filtre_imp = st.selectbox("Impact", impacts)
    with col_f3:
        filtre_zone = st.selectbox("Zone", zones)
    with col_f4:
        filtre_periode = st.selectbox("Période", ["À venir (90j)", "Tout afficher", "Passé (30j)"])

    # Appliquer filtres
    evts = CALENDRIER.copy()
    if filtre_cat != "Tout":
        evts = [e for e in evts if e["categorie"] == filtre_cat]
    if filtre_imp != "Tout":
        evts = [e for e in evts if e["impact"] == filtre_imp]
    if filtre_zone != "Tout":
        evts = [e for e in evts if e["zone"] == filtre_zone]
    if filtre_periode == "À venir (90j)":
        evts = [e for e in evts if datetime.strptime(e["date"], "%Y-%m-%d").date() >= today]
    elif filtre_periode == "Passé (30j)":
        evts = [e for e in evts if datetime.strptime(e["date"], "%Y-%m-%d").date() < today]

    st.caption(f"**{len(evts)} événement(s)** affiché(s)")

    # ── Légende impact ────────────────────────────────────────
    st.markdown(
        "<div style='display:flex; gap:18px; flex-wrap:wrap; margin:4px 0 8px 0; font-size:0.8rem;'>"
        "<span><b style='color:#FF4444;'>🔴 Élevé</b> — Fort potentiel de mouvement de marché (&gt;1%) : "
        "Fed, BCE, CPI, NFP, résultats Mag7. Période à surveiller de près.</span>"
        "<span><b style='color:#FF8C00;'>🟠 Moyen</b> — Réaction modérée attendue (0,3–1%) : "
        "PIB, PPI, révisions. Influence sectorielle ou indicielle.</span>"
        "<span><b style='color:#FFD700;'>🟡 Faible</b> — Impact limité sauf surprise majeure : "
        "statistiques hebdomadaires, confirmations de données flash.</span>"
        "</div>",
        unsafe_allow_html=True
    )
    st.divider()

    if not evts:
        st.info("Aucun événement ne correspond aux filtres sélectionnés.")
    else:
        # ── Couleurs par impact ───────────────────────────────
        IMPACT_COLOR = {
            "🔴 Élevé":  ("#FF4444", "rgba(255,68,68,0.08)"),
            "🟠 Moyen":  ("#FF8C00", "rgba(255,140,0,0.08)"),
            "🟡 Faible": ("#FFD700", "rgba(255,215,0,0.08)"),
        }
        CAT_ICON = {
            "Banque centrale": "🏦",
            "Inflation":       "📊",
            "Emploi":          "👷",
            "Croissance":      "📈",
            "Résultats":       "🏢",
            "Géopolitique":    "🌐",
        }

        mois_courant = None
        for evt in evts:
            dt = datetime.strptime(evt["date"], "%Y-%m-%d")
            mois = dt.strftime("%B %Y").capitalize()

            # ── Séparateur mensuel ────────────────────────────
            if mois != mois_courant:
                mois_courant = mois
                st.markdown(
                    f"<h3 style='color:rgba(255,255,255,0.4);font-size:0.9rem;"
                    f"font-weight:600;text-transform:uppercase;letter-spacing:2px;"
                    f"margin:20px 0 8px 0;'>{mois}</h3>",
                    unsafe_allow_html=True
                )

            # ── Passé ou futur ────────────────────────────────
            est_passe = dt.date() < today
            couleur_bord, couleur_fond = IMPACT_COLOR.get(evt["impact"], ("#888", "rgba(128,128,128,0.05)"))
            if est_passe:
                couleur_bord = "rgba(255,255,255,0.15)"
                couleur_fond = "rgba(255,255,255,0.02)"

            icone_cat = CAT_ICON.get(evt["categorie"], "📌")
            jours_restants = (dt.date() - today).days
            if jours_restants == 0:
                badge_date = "🔔 <b>Aujourd'hui</b>"
            elif jours_restants == 1:
                badge_date = "⏰ <b>Demain</b>"
            elif jours_restants > 0:
                badge_date = f"dans <b>{jours_restants}j</b>"
            else:
                badge_date = f"il y a <b>{abs(jours_restants)}j</b>"

            actifs_str = " · ".join([f"<code>{a}</code>" for a in evt.get("actifs_cles", [])])

            st.markdown(f"""
<div style="border-left: 4px solid {couleur_bord}; background: {couleur_fond};
            border-radius: 8px; padding: 14px 18px; margin: 6px 0;
            opacity: {'0.55' if est_passe else '1'};">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:6px;">
    <div>
      <span style="font-size:1rem; font-weight:700;">{icone_cat} {evt['evenement']}</span>
      <span style="margin-left:10px; font-size:0.78rem; color:{couleur_bord};
                   background:{couleur_bord}22; border-radius:10px;
                   padding:2px 8px;">{evt['impact']}</span>
      <span style="margin-left:6px; font-size:0.78rem; color:rgba(255,255,255,0.4);
                   background:rgba(255,255,255,0.06); border-radius:10px;
                   padding:2px 8px;">{evt['categorie']}</span>
    </div>
    <div style="text-align:right; font-size:0.82rem; color:rgba(255,255,255,0.55);">
      {evt['zone']} &nbsp;
      <b style="color:rgba(255,255,255,0.8);">{dt.strftime('%d/%m/%Y')}</b>
      &nbsp;·&nbsp; {evt['heure']}
      &nbsp;&nbsp; <span style="color:{couleur_bord};">{badge_date}</span>
    </div>
  </div>
  <div style="margin-top:8px; font-size:0.84rem; color:rgba(255,255,255,0.75);">
    {evt['description']}
  </div>
  <div style="margin-top:6px; font-size:0.8rem; color:rgba(255,255,255,0.45);
              border-top:1px solid rgba(255,255,255,0.06); padding-top:6px;">
    📉 <i>Impact historique :</i> {evt['historique']}
  </div>
  <div style="margin-top:5px; font-size:0.78rem; color:rgba(255,255,255,0.35);">
    Actifs clés : {actifs_str}
  </div>
</div>
""", unsafe_allow_html=True)



# ════════════════════════════════════════════════════════════
#  ONGLET HEATMAP SECTORIELLE
# ════════════════════════════════════════════════════════════
with onglet_heat:
    st.title("Carte Thermique Sectorielle")
    st.caption(
        "Performance des secteurs S&P 500 sur la période choisie. "
        "Vert = hausse · Rouge = baisse · Taille des cases = capitalisation boursière relative."
    )

    # ── ETFs sectoriels SPDR (proxy secteurs S&P 500) ─────────
    SECTEURS = {
        "XLK":  {"nom": "Technologie",          "icone": "💻", "sous": ["AAPL","MSFT","NVDA","AVGO","ORCL"]},
        "XLV":  {"nom": "Santé",                "icone": "🏥", "sous": ["JNJ","LLY","UNH","ABBV","MRK"]},
        "XLF":  {"nom": "Finance",              "icone": "🏦", "sous": ["BRK-B","JPM","V","MA","BAC"]},
        "XLY":  {"nom": "Conso. Discr.",        "icone": "🛍️", "sous": ["AMZN","TSLA","HD","MCD","NKE"]},
        "XLP":  {"nom": "Conso. Courante",      "icone": "🛒", "sous": ["PG","KO","PEP","COST","WMT"]},
        "XLE":  {"nom": "Énergie",              "icone": "⚡", "sous": ["XOM","CVX","COP","SLB","EOG"]},
        "XLI":  {"nom": "Industrie",            "icone": "🏭", "sous": ["GE","CAT","UNP","RTX","HON"]},
        "XLB":  {"nom": "Matériaux",            "icone": "⛏️", "sous": ["LIN","APD","SHW","FCX","NEM"]},
        "XLRE": {"nom": "Immobilier",           "icone": "🏠", "sous": ["AMT","PLD","CCI","EQIX","PSA"]},
        "XLU":  {"nom": "Services Publics",     "icone": "💡", "sous": ["NEE","DUK","SO","D","AEP"]},
        "XLC":  {"nom": "Comm. & Médias",       "icone": "📡", "sous": ["META","GOOGL","NFLX","DIS","CMCSA"]},
    }

    # Capitalisation relative (pour taille des cases — fixe, ordre de grandeur réel)
    CAP_RELATIVE = {
        "XLK": 32, "XLV": 12, "XLF": 13, "XLY": 11, "XLP": 7,
        "XLE": 5,  "XLI": 9,  "XLB": 3,  "XLRE": 3, "XLU": 3, "XLC": 9,
    }

    # ── Contrôles ─────────────────────────────────────────────
    hc1, hc2, hc3 = st.columns([2, 2, 2])
    with hc1:
        heat_debut = st.date_input("Depuis", value=datetime(2024, 1, 1),
                                   min_value=datetime(2010, 1, 1), max_value=date.today(),
                                   key="heat_debut")
    with hc2:
        heat_fin = st.date_input("Jusqu'au", value=date.today(),
                                 min_value=datetime(2010, 1, 1), max_value=date.today(),
                                 key="heat_fin")
    with hc3:
        vue_mode = st.selectbox("Vue", ["Secteurs ETF", "Top actions par secteur"])

    # ── Chargement données ─────────────────────────────────────
    tickers_heat = list(SECTEURS.keys())
    debut_h = heat_debut.strftime("%Y-%m-%d")
    fin_h   = heat_fin.strftime("%Y-%m-%d")

    with st.spinner("⏳ Chargement des données sectorielles…"):
        try:
            df_heat, _ = get_data_and_volume(tuple(sorted(tickers_heat)), debut_h, fin_h)
        except Exception:
            df_heat = pd.DataFrame()

    if df_heat.empty:
        st.warning("Impossible de charger les données. Réessaie dans quelques secondes.")
    else:
        # ── Calcul des performances ───────────────────────────
        perfs = {}
        for tk in tickers_heat:
            if tk not in df_heat.columns:
                continue
            s = df_heat[tk].dropna()
            if len(s) < 2:
                continue
            perf = (s.iloc[-1] / s.iloc[0] - 1) * 100
            perfs[tk] = round(perf, 2)

        if not perfs:
            st.warning("Données insuffisantes pour la période sélectionnée.")
        else:
            nb_jours = (heat_fin - heat_debut).days

            # ── Heatmap principale (treemap style Bloomberg) ───
            if vue_mode == "Secteurs ETF":
                labels, values, parents, colors_map, texts, customs = [], [], [], [], [], []

                # Racine invisible
                labels.append("S&P 500")
                values.append(0)
                parents.append("")
                colors_map.append(0)
                texts.append("")
                customs.append("")

                max_abs = max(abs(v) for v in perfs.values()) or 1

                for tk, perf in perfs.items():
                    info_s = SECTEURS[tk]
                    nom    = f"{info_s['icone']} {info_s['nom']}"
                    cap    = CAP_RELATIVE.get(tk, 5)
                    signe  = "+" if perf >= 0 else ""

                    labels.append(nom)
                    values.append(cap)
                    parents.append("S&P 500")
                    colors_map.append(perf)
                    texts.append(f"{nom}<br><b>{signe}{perf:.1f}%</b>")
                    customs.append(f"{tk} · {nb_jours}j · Cap. rel. {cap}%")

                fig_tree = go.Figure(go.Treemap(
                    labels=labels,
                    values=values,
                    parents=parents,
                    text=texts,
                    customdata=customs,
                    textinfo="text",
                    hovertemplate="<b>%{label}</b><br>%{customdata}<extra></extra>",
                    marker=dict(
                        colors=colors_map,
                        colorscale=[
                            [0.0,  "#8B1A1A"],
                            [0.2,  "#C0392B"],
                            [0.4,  "#E74C3C"],
                            [0.48, "#2C2C2C"],
                            [0.52, "#2C2C2C"],
                            [0.6,  "#27AE60"],
                            [0.8,  "#1E8449"],
                            [1.0,  "#145A32"],
                        ],
                        cmid=0,
                        cmin=-max_abs,
                        cmax=max_abs,
                        colorbar=dict(
                            title="Perf. (%)",
                            ticksuffix="%",
                            thickness=14,
                            len=0.8,
                        ),
                        line=dict(width=2, color="#111"),
                    ),
                    textfont=dict(size=14, color="#FFFFFF"),
                    tiling=dict(packing="squarify", pad=4),
                ))
                fig_tree.update_layout(
                    height=520,
                    margin=dict(l=0, r=0, t=10, b=0),
                    paper_bgcolor="#111",
                    font=dict(color="#FAFAFA"),
                )
                st.plotly_chart(fig_tree, width="stretch")

                # ── Barre de performance triée ─────────────────
                st.subheader("Classement des secteurs")
                perfs_tri = sorted(perfs.items(), key=lambda x: x[1], reverse=True)
                noms_tri  = [f"{SECTEURS[tk]['icone']} {SECTEURS[tk]['nom']}" for tk, _ in perfs_tri]
                vals_tri  = [v for _, v in perfs_tri]
                cols_bar  = ["#27AE60" if v >= 0 else "#C0392B" for v in vals_tri]

                fig_bar = go.Figure(go.Bar(
                    x=noms_tri, y=vals_tri,
                    marker_color=cols_bar,
                    text=[f"{'+' if v>=0 else ''}{v:.1f}%" for v in vals_tri],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Performance : %{y:+.2f}%<extra></extra>",
                ))
                fig_bar.update_layout(
                    height=320,
                    margin=dict(l=10, r=10, t=30, b=60),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#FAFAFA"),
                    yaxis=dict(
                        showgrid=True, gridcolor="rgba(255,255,255,0.07)",
                        ticksuffix="%", zeroline=True, zerolinecolor="rgba(255,255,255,0.25)",
                    ),
                    xaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig_bar, width="stretch")

                # ── Tableau récap ──────────────────────────────
                st.subheader("Tableau récapitulatif")
                rows = []
                for tk, perf in perfs_tri:
                    s    = df_heat[tk].dropna()
                    r    = s.pct_change().dropna()
                    vol  = r.std() * np.sqrt(252) * 100 if len(r) > 5 else None
                    dd   = ((s - s.cummax()) / s.cummax() * 100).min() if len(s) > 1 else None
                    rows.append({
                        "Secteur":      f"{SECTEURS[tk]['icone']} {SECTEURS[tk]['nom']}",
                        "ETF":          tk,
                        "Performance":  f"{'+' if perf>=0 else ''}{perf:.1f}%",
                        "Volatilité":   f"{vol:.1f}%" if vol else "—",
                        "Drawdown max": f"{dd:.1f}%"  if dd  else "—",
                        "Cap. rel.":    f"{CAP_RELATIVE.get(tk,0)}%",
                    })
                df_recap = pd.DataFrame(rows)

                def color_perf(val):
                    try:
                        v = float(str(val).replace("%","").replace("+",""))
                        if v > 0:  return "color: #27AE60; font-weight:600"
                        if v < 0:  return "color: #C0392B; font-weight:600"
                    except Exception: pass
                    return ""

                st.dataframe(
                    df_recap.style.map(color_perf, subset=["Performance","Drawdown max"]),
                    width="stretch", hide_index=True
                )

            else:
                # ── Vue : Top actions par secteur ─────────────
                st.markdown("**Performances des principales actions par secteur** sur la période sélectionnée.")

                # Collecte tous les sous-tickers
                tous_sous = []
                for s_info in SECTEURS.values():
                    tous_sous.extend(s_info["sous"])
                tous_sous = list(set(tous_sous))

                with st.spinner("Chargement des actions individuelles…"):
                    try:
                        df_sous, _ = get_data_and_volume(tuple(sorted(tous_sous)), debut_h, fin_h)
                    except Exception:
                        df_sous = pd.DataFrame()

                if df_sous.empty:
                    st.warning("Impossible de charger les données des actions.")
                else:
                    for tk_sec, s_info in SECTEURS.items():
                        perf_sec = perfs.get(tk_sec, 0)
                        col_sec  = "#27AE60" if perf_sec >= 0 else "#C0392B"

                        st.markdown(
                            f"<div style='border-left:4px solid {col_sec}; padding:6px 14px; "
                            f"margin:14px 0 8px 0; background:{col_sec}11; border-radius:0 6px 6px 0;'>"
                            f"<b>{s_info['icone']} {s_info['nom']}</b>  "
                            f"<span style='color:{col_sec}; font-size:1.1rem; font-weight:700;'>"
                            f"{'+' if perf_sec>=0 else ''}{perf_sec:.1f}%</span>"
                            f"<span style='color:rgba(255,255,255,0.4); font-size:0.8rem;'> · ETF {tk_sec}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        # Actions du secteur
                        perfs_sous = {}
                        for tk_s in s_info["sous"]:
                            if tk_s not in df_sous.columns:
                                continue
                            s = df_sous[tk_s].dropna()
                            if len(s) < 2:
                                continue
                            perfs_sous[tk_s] = round((s.iloc[-1] / s.iloc[0] - 1) * 100, 2)

                        if not perfs_sous:
                            st.caption("Données insuffisantes.")
                            continue

                        cols_act = st.columns(len(perfs_sous))
                        for ci, (tk_s, p) in enumerate(perfs_sous.items()):
                            col_a   = "#27AE60" if p >= 0 else "#C0392B"
                            signe_a = "+" if p >= 0 else ""
                            cols_act[ci].markdown(
                                f"<div style='background:{col_a}22; border:1px solid {col_a}55; "
                                f"border-radius:8px; padding:10px 8px; text-align:center;'>"
                                f"<div style='font-size:0.85rem; font-weight:700; color:#fff;'>{tk_s}</div>"
                                f"<div style='font-size:1.1rem; font-weight:800; color:{col_a};'>{signe_a}{p:.1f}%</div>"
                                f"</div>",
                                unsafe_allow_html=True
                            )

            # ── Rotation sectorielle (sparklines) ─────────────────
            st.divider()
            st.subheader("Évolution mensuelle des secteurs")
            st.caption("Rendements mensuels par secteur — identifie les rotations et cycles sectoriels.")

            df_mens = df_heat[list(perfs.keys())].resample("ME").last().pct_change().dropna() * 100
            if not df_mens.empty and len(df_mens) >= 2:
                # Heatmap mensuelle : lignes = secteurs, colonnes = mois
                df_mens.columns = [f"{SECTEURS[c]['icone']} {SECTEURS[c]['nom']}" for c in df_mens.columns]
                df_mens.index   = df_mens.index.strftime("%b %Y")

                fig_mheat = go.Figure(go.Heatmap(
                    z=df_mens.values.T,
                    x=df_mens.index,
                    y=df_mens.columns,
                    colorscale=[
                        [0.0, "#8B1A1A"], [0.35, "#C0392B"], [0.48, "#1C1C1C"],
                        [0.52, "#1C1C1C"], [0.65, "#27AE60"], [1.0, "#145A32"],
                    ],
                    zmid=0,
                    text=df_mens.values.T.round(1),
                    texttemplate="%{text:.1f}%",
                    hovertemplate="<b>%{y}</b><br>%{x}<br><b>%{z:+.2f}%</b><extra></extra>",
                    colorbar=dict(title="Rend. %", ticksuffix="%", thickness=12, len=0.7),
                ))
                fig_mheat.update_layout(
                    height=max(340, len(df_mens.columns) * 34),
                    margin=dict(l=10, r=10, t=10, b=40),
                    paper_bgcolor="#111",
                    plot_bgcolor="#111",
                    font=dict(color="#FAFAFA", size=11),
                    xaxis=dict(side="bottom", tickangle=-45),
                )
                st.plotly_chart(fig_mheat, width="stretch")
            else:
                st.info("Période trop courte pour afficher les rendements mensuels (minimum 2 mois).")


# ════════════════════════════════════════════════════════════
#  ONGLET 7 — GLOSSAIRE
# ════════════════════════════════════════════════════════════
with onglet7:
    st.title("Recherche d'actifs")
    st.caption("Recherche par nom, symbole ou mot-clé — les résultats affichent un aperçu en temps réel.")
    recherche = st.text_input("Rechercher", placeholder="Ex : Take Two, IBM, bitcoin, CAC 40, gold...",
                              label_visibility="collapsed").strip()
    if recherche:
        with st.spinner("Recherche..."):
            resultats = rechercher_tickers(recherche)
        if not resultats:
            st.warning("Aucun résultat.")
        else:
            st.caption(f"{len(resultats)} résultat(s)")
            for r in resultats:
                sym = r["symbol"]
                type_label = TYPE_LABELS.get(r['type'], r['type'])
                already = sym in st.session_state.custom_tickers or sym in selection

                # Aperçu rapide du prix
                try:
                    tk_info = yf.Ticker(sym).fast_info
                    prix = tk_info.get("last_price") or tk_info.get("regularMarketPrice")
                    prev = tk_info.get("previous_close") or tk_info.get("regularMarketPreviousClose")
                    var = ((prix - prev) / prev * 100) if prix and prev else None
                except Exception:
                    prix, var = None, None

                c1, c2, c3, c4 = st.columns([1.5, 3.5, 2, 1.5])
                c1.markdown(f"**`{sym}`**")
                c2.markdown(f"{r['name']}")
                c2.caption(f"{type_label} · {r['exchange']}")

                if prix:
                    var_color = "#2d9e5f" if var and var >= 0 else "#e05252"
                    var_str = f"{var:+.2f}%" if var else ""
                    c3.markdown(f"**{prix:.2f}** <span style='color:{var_color};font-size:0.85rem'>{var_str}</span>",
                                unsafe_allow_html=True)
                else:
                    c3.caption("—")

                if already:
                    c4.success("Ajouté", icon="✓")
                else:
                    if c4.button("Ajouter", key=f"add_{sym}"):
                        st.session_state.custom_tickers.append(sym)
                        sauvegarder_tickers_json(st.session_state.custom_tickers)
                        st.rerun()
                st.divider()
    else:
        # Catégories de recherche rapide — tableau structuré
        _cats = [
            ("Tech US", [
                ("Apple","AAPL"),("Microsoft","MSFT"),("Alphabet","GOOGL"),("Nvidia","NVDA"),("Meta","META"),
                ("Amazon","AMZN"),("Tesla","TSLA"),("Netflix","NFLX"),("Salesforce","CRM"),("AMD","AMD"),
            ]),
            ("Finance", [
                ("JPMorgan","JPM"),("Goldman Sachs","GS"),("BlackRock","BLK"),("Morgan Stanley","MS"),
                ("Bank of America","BAC"),("Visa","V"),("Mastercard","MA"),("Am. Express","AXP"),("Schwab","SCHW"),("Blackstone","BX"),
            ]),
            ("Europe", [
                ("LVMH","MC.PA"),("SAP","SAP.DE"),("ASML","ASML.AS"),("Sanofi","SAN.PA"),("L'Oréal","OR.PA"),
                ("TotalEnergies","TTE.PA"),("Siemens","SIE.DE"),("AB InBev","ABI.BR"),("Novo Nordisk","NOVO-B.CO"),("Shell","SHEL.AS"),
            ]),
            ("Crypto", [
                ("Bitcoin","BTC-USD"),("Ethereum","ETH-USD"),("Solana","SOL-USD"),("BNB","BNB-USD"),("XRP","XRP-USD"),
                ("Cardano","ADA-USD"),("Avalanche","AVAX-USD"),("Dogecoin","DOGE-USD"),("Polkadot","DOT-USD"),("Chainlink","LINK-USD"),
            ]),
            ("Indices", [
                ("S&P 500","^GSPC"),("Nasdaq","^IXIC"),("Dow Jones","^DJI"),("CAC 40","^FCHI"),("DAX 40","^GDAXI"),
                ("Nikkei 225","^N225"),("Hang Seng","^HSI"),("KOSPI","^KS11"),("Euro Stoxx 50","^STOXX50E"),("FTSE 100","^FTSE"),
            ]),
            ("Matières premières", [
                ("Or","GC=F"),("Argent","SI=F"),("Pétrole WTI","CL=F"),("Gaz naturel","NG=F"),("Cuivre","HG=F"),
                ("Platine","PL=F"),("Blé","ZW=F"),("Maïs","ZC=F"),("Café","KC=F"),("Coton","CT=F"),
            ]),
        ]

        # CSS pour la grille
        st.markdown("""
        <style>
        .rp-nm{font-size:.66rem;color:#7cb3f0;text-align:center;
               padding:2px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
        .rp-cat-label{font-weight:700;font-size:.95rem;color:rgba(255,255,255,0.9);
                      padding:18px 0 8px;border-bottom:1px solid rgba(255,255,255,0.08);margin-bottom:8px;}
        </style>
        """, unsafe_allow_html=True)

        # Collecter les tickers déjà actifs
        _added = set(st.session_state.custom_tickers) | set(selection)

        for cat_name, items in _cats:
            st.markdown(f'<div class="rp-cat-label">{cat_name}</div>', unsafe_allow_html=True)
            cols = st.columns(len(items))
            for col, (name, tk) in zip(cols, items):
                with col:
                    st.markdown(f'<div class="rp-nm">{name}</div>', unsafe_allow_html=True)
                    if tk in _added:
                        if st.button(f"{tk} ✓", key=f"qk_{tk}", use_container_width=True):
                            # Désélectionner via le set (appliqué au prochain rerun)
                            if tk in _all_predefined:
                                st.session_state.deactivated_tickers.add(tk)
                            else:
                                if tk in st.session_state.custom_tickers:
                                    st.session_state.custom_tickers.remove(tk)
                                    sauvegarder_tickers_json(st.session_state.custom_tickers)
                            st.rerun()
                    else:
                        if st.button(tk, key=f"qk_{tk}", use_container_width=True):
                            if tk in _all_predefined:
                                st.session_state.activated_tickers.add(tk)
                            else:
                                st.session_state.custom_tickers.append(tk)
                                sauvegarder_tickers_json(st.session_state.custom_tickers)
                            st.rerun()
                            
# ── CSS global ────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Layout général ──────────────────────────────────────── */
.block-container { padding-top: 1rem !important; margin-top: 2rem !important }
hr { border-color: rgba(255,255,255,0.07) !important; margin: 0.6rem 0 !important; }

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] { min-width: 300px; max-width: 320px; }
[data-testid="stSidebar"] .stMarkdown p { font-size: 0.82rem; }
/* Toggles sur une seule ligne avec icône ⓘ bien alignée */
[data-testid="stSidebar"] [data-testid="stToggle"] {
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    flex-wrap: nowrap !important;
}
[data-testid="stSidebar"] [data-testid="stToggle"] > label {
    font-size: 0.84rem !important;
    white-space: nowrap !important;
    flex: 1 !important;
}

/* ── Tabs navigation ─────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 2px !important;
    flex-wrap: wrap !important;
    background: rgba(255,255,255,0.03) !important;
    border-radius: 10px !important;
    padding: 4px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 7px !important;
    padding: 6px 14px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: rgba(255,255,255,0.55) !important;
    background: transparent !important;
    border: none !important;
    white-space: nowrap !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    background: rgba(255,255,255,0.07) !important;
    color: rgba(255,255,255,0.9) !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: rgba(0,212,170,0.15) !important;
    color: #00D4AA !important;
    font-weight: 700 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    display: none !important;
}
[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.2rem !important;
}
/* Graphiques toujours pleine largeur */
[data-testid="stPlotlyChart"], [data-testid="stPlotlyChart"] > div {
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)
