"""Backtest bougie par bougie : signal à la clôture, entrée à l'ouverture suivante, SL/TP en ATR,
coûts (spread + slippage), risque fixe par trade. Si SL et TP sont touchés dans la même bougie -> SL (prudent)."""
import numpy as np
import pandas as pd
from strategies import REGISTRY, atr

COST = dict(spread=0.35, slippage=0.10)  # USD par once, aller simple total ~ spread + slippage
RISK = 0.01  # 1 % du capital par trade


def run(df, long, short, sl_atr=1.5, tp_atr=3.0, max_bars=48, capital=10_000.0, cost=COST, risk=RISK):
    a = atr(df).values
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    L, S = long.values, short.values
    n = len(df)
    eq, trades = capital, []
    curve = np.full(n, capital, dtype=float)
    pos = 0
    entry = sl = tp = size = 0.0
    ebar = 0
    fee = cost["spread"] + cost["slippage"]
    for i in range(1, n):
        if pos:
            hit = None
            if pos == 1:
                if l[i] <= sl: hit = sl
                elif h[i] >= tp: hit = tp
            else:
                if h[i] >= sl: hit = sl
                elif l[i] <= tp: hit = tp
            if hit is None and i - ebar >= max_bars:
                hit = c[i]
            if hit is not None:
                pnl = (hit - entry) * pos * size - fee * size
                eq += pnl
                trades.append((df.index[ebar], df.index[i], pos, entry, hit, pnl, pnl / (abs(entry - sl) * size) if size else 0))
                pos = 0
        if not pos and (L[i - 1] or S[i - 1]) and a[i - 1] > 0:
            pos = 1 if L[i - 1] else -1
            entry, ebar = o[i], i
            dist = sl_atr * a[i - 1]
            sl, tp = entry - pos * dist, entry + pos * tp_atr * a[i - 1]
            size = eq * risk / dist
        curve[i] = eq
    t = pd.DataFrame(trades, columns=["open_t", "close_t", "side", "entry", "exit", "pnl", "R"])
    return t, pd.Series(curve, index=df.index)


def metrics(t, curve, bars_per_year):
    if t.empty:
        return dict(trades=0, ret_pct=0, pf=0, win=0, maxdd_pct=0, sharpe=0, exp_R=0)
    g, ls = t.pnl[t.pnl > 0].sum(), -t.pnl[t.pnl < 0].sum()
    r = curve.pct_change().fillna(0)
    return dict(trades=len(t), ret_pct=100 * (curve.iloc[-1] / curve.iloc[0] - 1), pf=g / ls if ls else np.inf,
                win=100 * (t.pnl > 0).mean(), maxdd_pct=100 * (curve / curve.cummax() - 1).min(),
                sharpe=r.mean() / r.std() * np.sqrt(bars_per_year) if r.std() > 0 else 0, exp_R=t.R.mean())


SL_TP = [(1.0, 2.0), (1.5, 3.0), (2.0, 4.0), (1.5, 2.25), (2.0, 2.0)]


def optimise(df, min_trades=25):
    """Grille sur `df` (in-sample). Retourne les résultats triés par profit factor."""
    bpy = 252 * 23 * (3600 * 24 / 86400) * (60 / max(1, int(df.index.to_series().diff().median().total_seconds() / 60)))
    rows = []
    for name, (fn, grid) in REGISTRY.items():
        for p in grid:
            lg, sh = fn(df, **p)
            for sl, tp in SL_TP:
                t, cv = run(df, lg, sh, sl, tp)
                m = metrics(t, cv, bpy)
                rows.append(dict(strategy=name, params=p, sl=sl, tp=tp, **m))
    r = pd.DataFrame(rows)
    return r[r.trades >= min_trades].sort_values("pf", ascending=False)


def walk_forward(df, split=0.5, top=3):
    """Optimise sur la 1re moitié, valide sur la 2e (jamais vue) : seul le hors-échantillon compte."""
    cut = df.index[int(len(df) * split)]
    is_, oos = df[df.index < cut], df[df.index >= cut]
    best = optimise(is_).head(top)
    bpy = 252 * 23 * (60 / max(1, int(df.index.to_series().diff().median().total_seconds() / 60)))
    out = []
    for _, b in best.iterrows():
        lg, sh = REGISTRY[b.strategy][0](oos, **b.params)
        t, cv = run(oos, lg, sh, b.sl, b.tp)
        m = metrics(t, cv, bpy)
        out.append(dict(strategy=b.strategy, params=b.params, sl=b.sl, tp=b.tp,
                        **{f"is_{k}": b[k] for k in ("trades", "pf", "ret_pct")},
                        **{f"oos_{k}": v for k, v in m.items()}))
    return pd.DataFrame(out)
