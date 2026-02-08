"""
Grid search des paramètres de stratégie sans refetcher les données.
"""
import os
from pathlib import Path
from datetime import timezone
import itertools

import ccxt
import pandas as pd

from src.indicators import TechnicalIndicators
from test_backtest import fetch_all_ohlcv, build_dataframe, compute_trades, compute_stats


def main():
    symbol = os.getenv('SYMBOL', 'BTC/USDT')
    timeframe = '1h'
    hist_exchange_name = os.getenv('HIST_EXCHANGE', 'binance')
    start_date = os.getenv('START_DATE', '2017-08-17')
    initial_capital = float(os.getenv('INITIAL_CAPITAL', '10'))

    exchange = getattr(ccxt, hist_exchange_name)({'enableRateLimit': True})
    since_ms = int(pd.Timestamp(start_date, tz=timezone.utc).timestamp() * 1000)

    cache_dir = Path("/home/willi363/projet/perso/Bot-crypto/data")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"ohlcv_{hist_exchange_name}_{symbol.replace('/', '-')}_{timeframe}.csv"

    if cache_file.exists():
        print(f"✅ Chargement du cache: {cache_file.name}")
        df = pd.read_csv(cache_file)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df.set_index('timestamp', inplace=True)
        else:
            # Compatibilité : première colonne considérée comme timestamp si pas de nom
            first_col = df.columns[0]
            df[first_col] = pd.to_datetime(df[first_col], utc=True)
            df.set_index(first_col, inplace=True)
            df.index.name = 'timestamp'
    else:
        print(f"🚀 Récupération historique {symbol} en {timeframe} depuis {start_date} (source: {hist_exchange_name})...")
        ohlcv = fetch_all_ohlcv(exchange, symbol, timeframe=timeframe, since_ms=since_ms, limit=720)

        if not ohlcv:
            print("❌ Aucune donnée récupérée.")
            return

        df = build_dataframe(ohlcv)
        df.reset_index().to_csv(cache_file, index=False)
        df.set_index('timestamp', inplace=True)

    df = TechnicalIndicators.add_all_indicators(df)

    print(f"✅ {len(df)} bougies prêtes pour la grille.")

    # Grille étendue (tous les paramètres clés du .env). Ajuste les listes selon ton besoin.
    param_grid = {
        "VOLUME_RATIO_MIN": [0.70, 0.80, 0.90],
        "VOLUME_SPIKE_MIN": [1.25, 1.40, 1.55],
        "CHOP_NO_TRADE_MAX": [52, 55, 58, 60],
        "ATR_PCT_MIN": [0.0035, 0.0045, 0.0055],
        "ATR_EXTREME_MULT": [2.5, 3.0, 3.5],
        "RSI_MIN": [36, 38, 40, 42],
        "RSI_MAX": [58, 60, 62, 64],
        "ATR_STOP_MULT": [1.8, 2.0, 2.2],
        "TP1_MULT": [1.6, 1.85, 2.0],
        "TP2_MULT": [3.0, 3.3, 3.6],
        "COOLDOWN_BARS": [10, 14, 16, 18],
        "COOLDOWN_BARS_SL": [16, 20, 22, 24],
        "TIME_STOP_BARS": [24, 28, 32, 36],
        "RISK_PER_TRADE": [0.0025, 0.004, 0.006, 0.008],
        "REQUIRE_VOLUME_SPIKE": ["true", "false"],
    }

    max_combos_env = os.getenv('MAX_COMBOS')
    max_combos = int(max_combos_env) if max_combos_env else None

    key_list = list(param_grid.keys())
    value_lists = [param_grid[k] for k in key_list]
    combos = list(itertools.product(*value_lists))
    total = len(combos)
    if max_combos:
        combos = combos[:max_combos]
        total = len(combos)
    print(f"🔍 Exploration de {total} combinaisons (MAX_COMBOS={'∞' if not max_combos_env else max_combos}).")

    results = []
    for idx, vals in enumerate(combos, 1):
        for k, v in zip(key_list, vals):
            os.environ[k] = str(v)
        trades, _ = compute_trades(df)
        stats = compute_stats(trades, "Depuis le début", initial_capital)
        results.append((stats['final_capital'], stats['total_return'], stats['trades'], dict(zip(key_list, vals))))
        if idx % 25 == 0 or idx == total:
            print(f"Progression: {idx}/{total} combinaisons ({idx/total*100:.1f}%)")

    results.sort(reverse=True, key=lambda x: x[0])

    print("\nTop 20 configurations par capital final (Depuis le début):")
    for rank, (final_cap, total_return, trades, param_set) in enumerate(results[:20], 1):
        params_str = " ".join(f"{k}={v}" for k, v in param_set.items())
        print(f"{rank:02d} | Capital: {final_cap:.2f} € | Retour: {total_return*100:.2f}% | Trades: {trades} | {params_str}")


if __name__ == "__main__":
    main()
