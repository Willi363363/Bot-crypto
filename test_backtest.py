"""
Backtest 1h sur BTC/USDT (ou autre symbole) avec la stratégie actuelle.
Récupère l'historique complet possible via une source dédiée et calcule des statistiques.
"""
import os
import time
from datetime import datetime, timedelta, timezone

import ccxt
import pandas as pd
from dotenv import load_dotenv

from src.indicators import TechnicalIndicators
from src.strategy import Strategy

load_dotenv()


def _timeframe_to_ms(timeframe: str) -> int:
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    if unit == 'm':
        return value * 60 * 1000
    if unit == 'h':
        return value * 60 * 60 * 1000
    if unit == 'd':
        return value * 24 * 60 * 60 * 1000
    raise ValueError(f"Timeframe non supporté: {timeframe}")


def fetch_all_ohlcv(exchange, symbol: str, timeframe: str = '1h', since_ms: int | None = None, limit: int = 720):
    """Récupère toutes les bougies disponibles (pagination via since)."""
    all_ohlcv = []
    timeframe_ms = _timeframe_to_ms(timeframe)

    last_seen_ts = None

    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
        if not ohlcv:
            break

        all_ohlcv.extend(ohlcv)
        last_ts = ohlcv[-1][0]
        if last_seen_ts is not None and last_ts == last_seen_ts:
            break
        last_seen_ts = last_ts
        next_since = last_ts + timeframe_ms

        if since_ms is not None and next_since <= since_ms:
            break

        since_ms = next_since
        time.sleep(exchange.rateLimit / 1000)

        if len(ohlcv) < limit:
            break

    # Déduplication par timestamp
    unique = {}
    for row in all_ohlcv:
        unique[row[0]] = row

    return [unique[k] for k in sorted(unique.keys())]


def build_dataframe(ohlcv):
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df.set_index('timestamp', inplace=True)
    return df


def compute_trades(df):
    """
    Calcule les trades en simulant la stratégie à chaque bougie.
    Entrée à l'ouverture de la bougie suivante, sortie sur signal opposé
    ou SL/TP. Les frais sont appliqués sur entrée et sortie.
    """
    results = []
    signal_counts = {"BUY": 0, "SELL": 0, "NEUTRAL": 0}

    fee_rate = float(os.getenv('FEE_RATE', '0.0004'))  # 0.04% par ordre
    sl_pct = float(os.getenv('SL_PCT', '0.01'))  # 1%
    tp_pct = float(os.getenv('TP_PCT', '0.02'))  # 2%
    use_atr = os.getenv('USE_ATR_STOPS', 'true').lower() == 'true'
    atr_mult_sl = float(os.getenv('ATR_MULT_SL', '1.5'))
    atr_mult_tp = float(os.getenv('ATR_MULT_TP', '2.5'))
    cooldown_bars = int(os.getenv('COOLDOWN_BARS', '3'))
    long_only = os.getenv('LONG_ONLY', 'true').lower() == 'false'

    position = None  # "BUY" ou "SELL"
    entry_price = None
    entry_time = None
    cooldown = 0

    for i in range(260, len(df) - 1):
        sub = df.iloc[:i + 1]
        signal = Strategy.generate_signal(sub).signal
        signal_counts[signal] = signal_counts.get(signal, 0) + 1

        next_bar = df.iloc[i + 1]

        if cooldown > 0:
            cooldown -= 1
            continue

        if position is None and signal in ("BUY", "SELL"):
            if long_only and signal == "SELL":
                continue
            position = signal
            entry_price = next_bar['open']
            entry_time = next_bar.name
            continue

        if position is None:
            continue

        direction = 1 if position == "BUY" else -1
        atr = df.iloc[i].get('atr')

        if use_atr and atr is not None:
            stop_distance = atr_mult_sl * atr
            take_distance = atr_mult_tp * atr
            stop_price = entry_price - stop_distance if position == "BUY" else entry_price + stop_distance
            take_price = entry_price + take_distance if position == "BUY" else entry_price - take_distance
        else:
            stop_price = entry_price * (1 - sl_pct) if position == "BUY" else entry_price * (1 + sl_pct)
            take_price = entry_price * (1 + tp_pct) if position == "BUY" else entry_price * (1 - tp_pct)

        hit_stop = next_bar['low'] <= stop_price if position == "BUY" else next_bar['high'] >= stop_price
        hit_take = next_bar['high'] >= take_price if position == "BUY" else next_bar['low'] <= take_price

        exit_price = None
        exit_reason = None

        if hit_stop:
            exit_price = stop_price
            exit_reason = "SL"
        elif hit_take:
            exit_price = take_price
            exit_reason = "TP"
        elif (position == "BUY" and signal == "SELL") or (position == "SELL" and signal == "BUY"):
            exit_price = next_bar['open']
            exit_reason = "REV"

        if exit_price is None:
            continue

        ret = direction * (exit_price - entry_price) / entry_price
        ret -= 2 * fee_rate

        results.append({
            "timestamp": next_bar.name,
            "signal": position,
            "entry": entry_price,
            "exit": exit_price,
            "return": ret,
            "prediction_correct": ret > 0,
            "exit_reason": exit_reason,
            "entry_time": entry_time
        })

        position = None
        entry_price = None
        entry_time = None
        cooldown = max(cooldown, cooldown_bars)

    return pd.DataFrame(results), signal_counts


def compute_stats(trades: pd.DataFrame, label: str, initial_capital: float):
    if trades.empty:
        return {
            "label": label,
            "trades": 0,
            "total_return": 0.0,
            "win_rate": 0.0,
            "accuracy": 0.0,
            "avg_return": 0.0,
            "median_return": 0.0,
            "max_drawdown": 0.0,
            "final_capital": initial_capital
        }

    equity = (1 + trades['return']).cumprod()
    peak = equity.cummax()
    drawdown = (equity - peak) / peak

    return {
        "label": label,
        "trades": int(len(trades)),
        "total_return": float(equity.iloc[-1] - 1),
        "win_rate": float((trades['return'] > 0).mean()),
        "accuracy": float(trades['prediction_correct'].mean()),
        "avg_return": float(trades['return'].mean()),
        "median_return": float(trades['return'].median()),
        "max_drawdown": float(drawdown.min()),
        "final_capital": float(initial_capital * equity.iloc[-1])
    }


def print_stats(stats, initial_capital: float):
    print(f"\n📌 {stats['label']}")
    print(f"- Trades: {stats['trades']}")
    print(f"- Rendement potentiel: {stats['total_return'] * 100:.2f}%")
    print(f"- Capital initial: {initial_capital:.2f} €")
    print(f"- Capital final: {stats['final_capital']:.2f} €")
    print(f"- Win rate (retour > 0): {stats['win_rate'] * 100:.2f}%")
    print(f"- % prévision correcte: {stats['accuracy'] * 100:.2f}%")
    print(f"- Rendement moyen par trade: {stats['avg_return'] * 100:.3f}%")
    print(f"- Rendement médian par trade: {stats['median_return'] * 100:.3f}%")
    print(f"- Max drawdown: {stats['max_drawdown'] * 100:.2f}%")


def main():
    symbol = os.getenv('SYMBOL', 'BTC/USDT')
    timeframe = '1h'
    exchange_name = os.getenv('EXCHANGE', 'kraken')
    hist_exchange_name = os.getenv('HIST_EXCHANGE', 'binance')
    start_date = os.getenv('START_DATE', '2017-08-17')

    if os.getenv('TIMEFRAME', '1h') != '1h':
        print("⚠️ TIMEFRAME ignoré pour le backtest. Forcé à 1h.")

    exchange = getattr(ccxt, hist_exchange_name)({'enableRateLimit': True})

    limit = 720
    since_ms = int(pd.Timestamp(start_date, tz=timezone.utc).timestamp() * 1000)

    if exchange.id == 'kraken':
        print("ℹ️ Kraken limite l'historique OHLCV à ~720 bougies par requête.")
        print("   En 1h, cela représente ~30 jours maximum via l'API.")
        since_ms = None

    print(f"🚀 Récupération historique {symbol} en {timeframe} depuis {start_date} (source: {hist_exchange_name})...")
    ohlcv = fetch_all_ohlcv(exchange, symbol, timeframe=timeframe, since_ms=since_ms, limit=limit)

    if not ohlcv:
        print("❌ Aucune donnée récupérée.")
        return

    df = build_dataframe(ohlcv)
    df = TechnicalIndicators.add_all_indicators(df)

    print(f"✅ {len(df)} bougies récupérées.")

    if not df.empty:
        first_ts = df.index[0]
        last_ts = df.index[-1]
        print(f"🗓️  Couverture: {first_ts.strftime('%Y-%m-%d')} → {last_ts.strftime('%Y-%m-%d')}")

        requested_since = pd.Timestamp(start_date, tz=timezone.utc)
        if first_ts > requested_since + timedelta(days=7):
            print(f"⚠️ {exchange.id} ne renvoie pas l'historique complet demandé pour ce timeframe.")
            print("   Conseil: ajuste START_DATE ou utilise une source historique dédiée.")

    trades, signal_counts = compute_trades(df)

    print(f"📊 Signaux générés: BUY={signal_counts.get('BUY', 0)}, SELL={signal_counts.get('SELL', 0)}, NEUTRAL={signal_counts.get('NEUTRAL', 0)}")

    if trades.empty:
        print("⚠️ Aucun trade généré sur la période.")
        return

    now = datetime.now(timezone.utc)
    last_year = now - timedelta(days=365)
    last_month = now - timedelta(days=30)
    last_week = now - timedelta(days=7)

    initial_capital = float(os.getenv('INITIAL_CAPITAL', '10'))

    stats_all = compute_stats(trades, "Depuis le début", initial_capital)
    stats_year = compute_stats(trades[trades['timestamp'] >= last_year], "Sur 1 an", initial_capital)
    stats_month = compute_stats(trades[trades['timestamp'] >= last_month], "Sur 1 mois", initial_capital)
    stats_week = compute_stats(trades[trades['timestamp'] >= last_week], "Sur 1 semaine", initial_capital)

    print_stats(stats_all, initial_capital)
    print_stats(stats_year, initial_capital)
    print_stats(stats_month, initial_capital)
    print_stats(stats_week, initial_capital)


if __name__ == "__main__":
    main()
