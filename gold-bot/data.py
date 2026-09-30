"""Chargement des données OHLC de l'or (XAUUSD). Index = datetime UTC, colonnes open/high/low/close/volume."""
import pandas as pd


def load_csv(path: str) -> pd.DataFrame:
    """CSV exporté de TradingView (time en epoch ou ISO), MT5 (Date,Time,O,H,L,C,V) ou Dukascopy."""
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = [c.strip().lower().strip("<>") for c in df.columns]
    if "date" in df.columns and "time" in df.columns:
        ts = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str), utc=True)
    else:
        col = next(c for c in ("time", "datetime", "timestamp", "date", "gmt time") if c in df.columns)
        s = df[col]
        ts = pd.to_datetime(s, unit="s", utc=True) if pd.api.types.is_numeric_dtype(s) else pd.to_datetime(s, utc=True)
    df.index = ts
    df = df.rename(columns={"tick_volume": "volume", "vol": "volume"})
    if "volume" not in df.columns:
        df["volume"] = 0.0
    return df[["open", "high", "low", "close", "volume"]].sort_index().loc[lambda d: ~d.index.duplicated()]


def load_yfinance(interval: str = "1h", period: str = "1y", ticker: str = "GC=F") -> pd.DataFrame:
    """Yahoo: 1h dispo jusqu'à 730 j, 30m seulement 60 j -> pour 30m sur 1 an, utiliser un CSV."""
    import yfinance as yf
    d = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    d.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in d.columns]
    d.index = d.index.tz_convert("UTC")
    return d[["open", "high", "low", "close", "volume"]].dropna()


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """30min -> 1h : resample(df, '1h')."""
    o = df.resample(rule).agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return o.dropna(subset=["open"])
