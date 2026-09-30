# gold-bot — XAUUSD 30m / 1h

1. Exporter ~1 an de bougies **30 min** XAUUSD en CSV (MT5 : Outils > Centre d'historique ; TradingView : Export chart data ; ou Dukascopy).
2. `python run_backtest.py --csv xauusd_30m.csv` → compare 5 stratégies (EMA pullback, Donchian, Supertrend, Bollinger, cassure de session) en 30m et 1h.
3. **Walk-forward** : paramètres optimisés sur les 6 premiers mois, jugés sur les 6 derniers. Ne retenir que ce qui est rentable hors échantillon (PF > 1.3, > 30 trades, DD acceptable).
4. Reporter le gagnant dans `config.json`, tester en démo : `python bot.py` (paper), puis `--live` sur compte démo MT5.

Hypothèses : signal à la clôture, entrée à l'ouverture suivante, SL/TP en ATR, coûts 0,45 $/oz, risque 1 %/trade (backtest), SL prioritaire si SL et TP touchés dans la même bougie.
Un backtest ne garantit rien : 1 an = un seul régime de marché. Pas de conseil financier ; démo d'abord.
