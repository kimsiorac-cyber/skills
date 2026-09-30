"""Stratégies candidates. Chaque fonction renvoie (long, short) : booléens évalués À LA CLÔTURE de la bougie
(l'ordre est exécuté à l'ouverture de la suivante -> pas de look-ahead)."""
import numpy as np
import pandas as pd


def atr(df, n=14):
    pc = df.close.shift()
    tr = pd.concat([df.high - df.low, (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def ema_pullback(df, fast=50, slow=200, rsi_lvl=40):
    """Tendance (EMA rapide > lente) + repli RSI qui repart -> entrée dans le sens de la tendance."""
    r = rsi(df.close)
    up = (ema(df.close, fast) > ema(df.close, slow)) & (df.close > ema(df.close, slow))
    dn = (ema(df.close, fast) < ema(df.close, slow)) & (df.close < ema(df.close, slow))
    long = up & (r.shift() < rsi_lvl) & (r >= rsi_lvl)
    short = dn & (r.shift() > 100 - rsi_lvl) & (r <= 100 - rsi_lvl)
    return long, short


def donchian(df, n=20, trend=200):
    """Cassure du plus haut/bas des n dernières bougies, filtrée par EMA de tendance."""
    hh, ll = df.high.rolling(n).max().shift(), df.low.rolling(n).min().shift()
    t = ema(df.close, trend)
    return (df.close > hh) & (df.close > t), (df.close < ll) & (df.close < t)


def supertrend(df, period=10, mult=3.0):
    a = atr(df, period).values
    hl2 = ((df.high + df.low) / 2).values
    c = df.close.values
    ub, lb = hl2 + mult * a, hl2 - mult * a
    n = len(c)
    fu, fl, d = ub.copy(), lb.copy(), np.ones(n, dtype=int)
    for i in range(1, n):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        d[i] = 1 if c[i] > fu[i - 1] else (-1 if c[i] < fl[i - 1] else d[i - 1])
    d = pd.Series(d, index=df.index)
    return (d == 1) & (d.shift() == -1), (d == -1) & (d.shift() == 1)


def bb_reversion(df, n=20, k=2.0, rsi_lo=30):
    """Retour à la moyenne : clôture hors bande de Bollinger + RSI extrême."""
    m, s = df.close.rolling(n).mean(), df.close.rolling(n).std()
    r = rsi(df.close)
    return (df.close < m - k * s) & (r < rsi_lo), (df.close > m + k * s) & (r > 100 - rsi_lo)


def session_breakout(df, asia_end=7, trade_end=16):
    """Cassure du range asiatique (00h-asia_end UTC) pendant Londres/NY, 1 signal max par jour et par sens."""
    h = df.index.hour
    day = df.index.normalize()
    asia = (h < asia_end)
    hi = df.high.where(asia).groupby(day).transform("max")
    lo = df.low.where(asia).groupby(day).transform("min")
    live = (h >= asia_end) & (h < trade_end)
    l = live & (df.close > hi)
    s = live & (df.close < lo)
    l &= ~l.groupby(day).transform(lambda x: x.shift(fill_value=False).cummax())
    s &= ~s.groupby(day).transform(lambda x: x.shift(fill_value=False).cummax())
    return l, s


# nom -> (fonction, grille de paramètres)
REGISTRY = {
    "ema_pullback": (ema_pullback, [dict(fast=f, slow=s, rsi_lvl=r) for f in (20, 50) for s in (100, 200) for r in (35, 40, 45)]),
    "donchian": (donchian, [dict(n=n, trend=t) for n in (10, 20, 40, 55) for t in (100, 200)]),
    "supertrend": (supertrend, [dict(period=p, mult=m) for p in (7, 10, 14) for m in (2.0, 3.0, 4.0)]),
    "bb_reversion": (bb_reversion, [dict(n=n, k=k, rsi_lo=r) for n in (20, 30) for k in (2.0, 2.5) for r in (25, 30)]),
    "session_breakout": (session_breakout, [dict(asia_end=a, trade_end=t) for a in (6, 7, 8) for t in (14, 16, 20)]),
}
