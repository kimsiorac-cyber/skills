"""Bot XAUUSD : à chaque clôture de bougie, calcule le signal de la stratégie choisie dans config.json
et envoie l'ordre avec SL/TP. MODE PAPER par défaut. Live = MetaTrader5 (Windows, terminal MT5 ouvert).
Usage: python bot.py            (paper)      |      python bot.py --live   (ordres réels, à vos risques)"""
import argparse, json, time
import pandas as pd
from strategies import REGISTRY, atr

cfg = json.load(open("config.json"))
ap = argparse.ArgumentParser(); ap.add_argument("--live", action="store_true"); a = ap.parse_args()
TF_MIN = cfg["timeframe_min"]


def fetch(mt5, n=600):
    tf = {30: mt5.TIMEFRAME_M30, 60: mt5.TIMEFRAME_H1}[TF_MIN]
    r = mt5.copy_rates_from_pos(cfg["symbol"], tf, 0, n)
    df = pd.DataFrame(r); df.index = pd.to_datetime(df.time, unit="s", utc=True)
    df = df.rename(columns={"tick_volume": "volume"})[["open", "high", "low", "close", "volume"]]
    return df.iloc[:-1]  # on retire la bougie en cours : signaux sur bougies CLÔTURÉES uniquement


def lots(mt5, equity, dist):
    info = mt5.symbol_info(cfg["symbol"])
    lot = equity * cfg["risk_per_trade"] / (dist * info.trade_contract_size)
    step = info.volume_step
    return max(info.volume_min, min(info.volume_max, round(lot / step) * step))


def main():
    import MetaTrader5 as mt5
    if not mt5.initialize(): raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    fn = REGISTRY[cfg["strategy"]][0]
    last = None
    while True:
        df = fetch(mt5)
        if df.index[-1] != last:
            last = df.index[-1]
            lg, sh = fn(df, **cfg["params"])
            side = 1 if lg.iloc[-1] else -1 if sh.iloc[-1] else 0
            open_pos = mt5.positions_get(symbol=cfg["symbol"], magic=cfg["magic"]) if hasattr(mt5, "positions_get") else ()
            print(f"{last} signal={side} positions={len(open_pos or [])}")
            if side and not open_pos:
                tick = mt5.symbol_info_tick(cfg["symbol"])
                px = tick.ask if side == 1 else tick.bid
                a_ = atr(df).iloc[-1]; sl_d, tp_d = cfg["sl_atr"] * a_, cfg["tp_atr"] * a_
                req = dict(action=mt5.TRADE_ACTION_DEAL, symbol=cfg["symbol"], magic=cfg["magic"],
                           volume=lots(mt5, mt5.account_info().equity, sl_d),
                           type=mt5.ORDER_TYPE_BUY if side == 1 else mt5.ORDER_TYPE_SELL, price=px,
                           sl=px - side * sl_d, tp=px + side * tp_d, deviation=20, comment="gold-bot",
                           type_filling=mt5.ORDER_FILLING_IOC)
                if a.live:
                    print(mt5.order_send(req))
                else:
                    print("[PAPER]", {k: req[k] for k in ("type", "volume", "price", "sl", "tp")})
        time.sleep(15)


if __name__ == "__main__":
    main()
