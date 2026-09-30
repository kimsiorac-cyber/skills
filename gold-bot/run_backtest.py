"""Usage: python run_backtest.py --csv xauusd_30m.csv [--synthetic]
Teste 30m et 1h (1h = rééchantillonnage du 30m), walk-forward 50/50, écrit results.md."""
import argparse
import numpy as np
import pandas as pd
from data import load_csv, resample
from backtest import walk_forward

ap = argparse.ArgumentParser()
ap.add_argument("--csv")
ap.add_argument("--synthetic", action="store_true", help="marche aléatoire : test de plomberie uniquement")
a = ap.parse_args()

if a.synthetic:
    idx = pd.date_range("2025-10-01", periods=12000, freq="30min", tz="UTC")
    idx = idx[idx.dayofweek < 5]
    c = 2000 + np.cumsum(np.random.default_rng(1).normal(0, 1.2, len(idx)))
    df30 = pd.DataFrame({"open": np.r_[c[0], c[:-1]], "close": c}, index=idx)
    df30["high"] = df30[["open", "close"]].max(axis=1) + 0.5
    df30["low"] = df30[["open", "close"]].min(axis=1) - 0.5
    df30["volume"] = 1.0
else:
    df30 = load_csv(a.csv)

pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 60)
res = {}
for tf, df in (("30m", df30), ("1h", resample(df30, "1h"))):
    print(f"\n=== {tf} : {len(df)} bougies {df.index[0]:%Y-%m-%d} -> {df.index[-1]:%Y-%m-%d}")
    res[tf] = walk_forward(df)
    print(res[tf].round(2).to_string())
with open("results.md", "w") as f:
    for tf, r in res.items():
        f.write(f"## {tf}\n\n```\n{r.round(2).to_string()}\n```\n\n")
