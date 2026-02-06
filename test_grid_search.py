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
            # Compatibilité si l'index a été sauvegardé sans nom
            index_col = df.columns[0]
            df[index_col] = pd.to_datetime(df[index_col], utc=True)
            df.set_index(index_col, inplace=True)
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

    # Grille raisonnable (16 combinaisons)
    chop_trend_max_vals = [55, 60]
    chop_range_min_vals = [65, 70]
    ema_gap_min_vals = [0.0006, 0.0010]
    atr_pct_min_vals = [0.001, 0.002]
    rsi_pullback_long_vals = [48]
    rsi_pullback_short_vals = [52]

    max_combos = int(os.getenv('MAX_COMBOS', '16'))

    results = []

    combos = list(itertools.product(
        chop_trend_max_vals,
        chop_range_min_vals,
        ema_gap_min_vals,
        atr_pct_min_vals,
        rsi_pullback_long_vals,
        rsi_pullback_short_vals,
    ))[:max_combos]

    for idx, vals in enumerate(combos, 1):
        (chop_trend_max, chop_range_min, ema_gap_min, atr_pct_min, rsi_pullback_long, rsi_pullback_short) = vals

        os.environ['CHOP_TREND_MAX'] = str(chop_trend_max)
        os.environ['CHOP_RANGE_MIN'] = str(chop_range_min)
        os.environ['EMA_GAP_MIN'] = str(ema_gap_min)
        os.environ['ATR_PCT_MIN'] = str(atr_pct_min)
        os.environ['RSI_PULLBACK_LONG_MIN'] = str(rsi_pullback_long)
        os.environ['RSI_PULLBACK_SHORT_MAX'] = str(rsi_pullback_short)
        os.environ['USE_RANGE'] = 'false'

        trades, _ = compute_trades(df)
        stats = compute_stats(trades, "Depuis le début", initial_capital)

        results.append((stats['final_capital'], stats['total_return'], stats['trades'], vals))

        if idx % 4 == 0 or idx == len(combos):
            print(f"Progression: {idx}/{len(combos)} combinaisons")

    results.sort(reverse=True, key=lambda x: x[0])

    print("\nTop 10 configurations par capital final (Depuis le début):")
    for rank, (final_cap, total_return, trades, vals) in enumerate(results[:10], 1):
        chop_trend_max, chop_range_min, ema_gap_min, atr_pct_min, rsi_pullback_long, rsi_pullback_short = vals
        print(
            f"{rank:02d} | Capital: {final_cap:.2f} € | Retour: {total_return*100:.2f}% | Trades: {trades} | "
            f"CHOP_TREND_MAX={chop_trend_max} CHOP_RANGE_MIN={chop_range_min} EMA_GAP_MIN={ema_gap_min} "
            f"ATR_PCT_MIN={atr_pct_min} RSI_PULLBACK_LONG_MIN={rsi_pullback_long} RSI_PULLBACK_SHORT_MAX={rsi_pullback_short}"
        )


if __name__ == "__main__":
    main()
