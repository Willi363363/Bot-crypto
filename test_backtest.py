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
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc

from src.indicators import TechnicalIndicators
from src.strategy import ImprovedStrategy

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


def compute_trades(df, warmup_bars=220):
    """
    Calcule les trades en simulant la stratégie à chaque bougie.
    Entrée à l'ouverture de la bougie suivante, sortie sur signal opposé
    ou SL/TP. Les frais sont appliqués sur entrée et sortie. Gestion partielle :
    50% à TP1, stop remonté à BE, reste sort à TP2 ou stop. Stop temps si aucune
    sortie après N bougies.
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
    cooldown_bars_sl = int(os.getenv('COOLDOWN_BARS_SL', str(cooldown_bars)))
    long_only = os.getenv('LONG_ONLY', 'true').lower() == 'true'
    slippage_bps = float(os.getenv('SLIPPAGE_BPS', '0.0002'))
    time_stop_bars = int(os.getenv('TIME_STOP_BARS', '48'))

    position = None  # "BUY" ou "SELL"
    entry_price = None
    entry_time = None
    cooldown = 0
    stop_price = None
    take_price_1 = None
    take_price_2 = None
    took_tp1 = False
    bars_in_position = 0

    def apply_slippage(price, side, is_entry=True):
        if side == "BUY":
            return price * (1 + slippage_bps if is_entry else 1 - slippage_bps)
        return price * (1 - slippage_bps if is_entry else 1 + slippage_bps)

    warmup = warmup_bars
    for i in range(warmup, len(df) - 1):
        sub = df.iloc[:i + 1]
        signal_obj = ImprovedStrategy.generate_signal(sub)
        signal = signal_obj.signal
        signal_counts[signal] = signal_counts.get(signal, 0) + 1

        next_bar = df.iloc[i + 1]

        # Gestion position existante
        if position is not None:
            direction = 1 if position == "BUY" else -1
            bars_in_position += 1

            # Détection SL/TP
            hit_tp2 = next_bar['high'] >= take_price_2 if position == "BUY" else next_bar['low'] <= take_price_2
            hit_tp1 = next_bar['high'] >= take_price_1 if position == "BUY" else next_bar['low'] <= take_price_1
            hit_stop = next_bar['low'] <= stop_price if position == "BUY" else next_bar['high'] >= stop_price

            exit_price = None
            exit_reason = None
            size = 1.0

            if hit_tp2:
                exit_price = take_price_2
                exit_reason = "TP2" if took_tp1 else "TP2_full"
                size = 0.5 if took_tp1 else 1.0

            elif hit_tp1 and not took_tp1:
                exit_price = take_price_1
                exit_reason = "TP1"
                size = 0.5
                took_tp1 = True
                stop_price = entry_price  # BE après TP1

            elif hit_stop:
                exit_price = stop_price
                exit_reason = "SL"
                size = 0.5 if took_tp1 else 1.0

            elif bars_in_position >= time_stop_bars:
                exit_price = next_bar['open']
                exit_reason = "TIME"
                size = 0.5 if took_tp1 else 1.0

            elif (position == "BUY" and signal == "SELL") or (position == "SELL" and signal == "BUY"):
                exit_price = next_bar['open']
                exit_reason = "REV"
                size = 0.5 if took_tp1 else 1.0

            if exit_price is not None:
                exit_price_slip = apply_slippage(exit_price, "SELL" if position == "BUY" else "BUY", is_entry=False)
                ret = direction * (exit_price_slip - entry_price) / entry_price * size
                # Fees: entry fee already paid once; exit fee proportional to size
                ret -= fee_rate * (1 + size)

                results.append({
                    "timestamp": next_bar.name,
                    "signal": position,
                    "entry": entry_price,
                    "exit": exit_price_slip,
                    "return": ret,
                    "prediction_correct": ret > 0,
                    "exit_reason": exit_reason,
                    "entry_time": entry_time,
                    "stop": stop_price,
                    "tp1": take_price_1,
                    "tp2": take_price_2
                })

                if exit_reason == "TP1":
                    # conserver la moitié restante
                    continue

                position = None
                entry_price = None
                entry_time = None
                stop_price = None
                take_price_1 = None
                take_price_2 = None
                took_tp1 = False
                bars_in_position = 0
                if exit_reason == "SL":
                    cooldown = max(cooldown, cooldown_bars_sl)
                else:
                    cooldown = max(cooldown, cooldown_bars)

        # Cooldown pour nouvelles entrées
        if cooldown > 0:
            cooldown -= 1
            continue

        # Nouvelle entrée
        if position is None and signal in ("BUY", "SELL"):
            if long_only and signal == "SELL":
                continue

            direction = 1 if signal == "BUY" else -1
            raw_entry = next_bar['open']
            entry_price = apply_slippage(raw_entry, signal, is_entry=True)
            entry_time = next_bar.name

            atr = df.iloc[i]['atr'] if 'atr' in df.columns else None

            if signal_obj.stop_loss is not None:
                stop_price = signal_obj.stop_loss
            elif use_atr and atr is not None:
                stop_price = entry_price - atr_mult_sl * atr if signal == "BUY" else entry_price + atr_mult_sl * atr
            else:
                stop_price = entry_price * (1 - sl_pct) if signal == "BUY" else entry_price * (1 + sl_pct)

            if signal_obj.take_profit_1 is not None and signal_obj.take_profit_2 is not None:
                take_price_1 = signal_obj.take_profit_1
                take_price_2 = signal_obj.take_profit_2
            else:
                if use_atr and atr is not None:
                    take_price_1 = entry_price + atr_mult_tp * atr if signal == "BUY" else entry_price - atr_mult_tp * atr
                    take_price_2 = take_price_1
                else:
                    take_price_1 = entry_price * (1 + tp_pct) if signal == "BUY" else entry_price * (1 - tp_pct)
                    take_price_2 = take_price_1

            position = signal
            took_tp1 = False
            bars_in_position = 0

    # Si une position reste ouverte à la fin, on la clôture au dernier close
    if position is not None:
        last_bar = df.iloc[-1]
        exit_price_slip = apply_slippage(last_bar['close'], "SELL" if position == "BUY" else "BUY", is_entry=False)
        direction = 1 if position == "BUY" else -1
        size = 0.5 if took_tp1 else 1.0
        ret = direction * (exit_price_slip - entry_price) / entry_price * size
        ret -= fee_rate * (1 + size)

        results.append({
            "timestamp": last_bar.name,
            "signal": position,
            "entry": entry_price,
            "exit": exit_price_slip,
            "return": ret,
            "prediction_correct": ret > 0,
            "exit_reason": "EOD",
            "entry_time": entry_time,
            "stop": stop_price,
            "tp1": take_price_1,
            "tp2": take_price_2
        })

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


def plot_trades(df, trades, output_path="backtest_plot.png", max_bars=None, days_window=30):
    """
    Trace un graphique chandeliers avec les entrées/sorties et niveaux SL/TP.
    Amélioré pour plus de lisibilité (DPI élevé, marqueurs plus gros, lignes plus visibles).
    days_window: nombre de jours récents à afficher (ex: 30 pour 1 mois).
    """
    if df.empty or trades.empty:
        print("ℹ️ Rien à tracer (pas de données ou de trades).")
        return

    end_time = df.index.max()
    base_start = end_time - timedelta(days=days_window)
    start_date_env = os.getenv('PLOT_START_DATE')
    if start_date_env:
        env_start = pd.Timestamp(start_date_env, tz=timezone.utc)
        window_start = min(base_start, env_start)  # toujours au moins days_window de lookback
    else:
        window_start = base_start
    window_start_naive = pd.Timestamp(window_start).tz_convert(None)

    # garantir suffisamment de bougies pour couvrir days_window
    bars_needed = int(days_window * 24 * 1.1) + 1
    effective_max_bars = bars_needed if max_bars is None else max(max_bars, bars_needed)

    df_window = df[df.index >= window_start]
    if df_window.empty:
        df_window = df

    if len(df_window) > effective_max_bars:
        df_window = df_window.tail(effective_max_bars)

    df_plot = df_window[['open', 'high', 'low', 'close']].copy()
    df_plot.index = df_plot.index.tz_convert(None)

    df_plot['date_num'] = mdates.date2num(df_plot.index.to_pydatetime())
    ohlc = df_plot[['date_num', 'open', 'high', 'low', 'close']].values.tolist()
    if len(df_plot) > 1:
        spacing = df_plot['date_num'].diff().median()
        width = 0.6 * spacing
        jitter_unit = 0.18 * spacing
    else:
        width = 0.01
        jitter_unit = 0.0

    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor('#f8fafc')
    ax.set_facecolor('#fdfefe')

    candlestick_ohlc(
        ax,
        ohlc,
        width=width,
        colorup='#2ecc71',
        colordown='#e74c3c',
        alpha=0.8
    )

    t_min, t_max = window_start_naive, df_plot.index.max()
    trades = trades.copy()
    trades['entry_time'] = pd.to_datetime(trades['entry_time']).dt.tz_convert(None)
    trades['timestamp'] = pd.to_datetime(trades['timestamp']).dt.tz_convert(None)

    trades_all = trades.copy()
    trades = trades[(trades['entry_time'] <= t_max) & (trades['timestamp'] >= t_min)]
    label_trades = os.getenv('PLOT_LABEL_TRADES', 'false').lower() == 'true'
    jitter_cycle = 11  # phases pour limiter la superposition

    if os.getenv('PLOT_DEBUG', 'false').lower() == 'true':
        print()
        print(f"🔍 Debug plot window: t_min={t_min}, t_max={t_max}")
        print(f"🔍 Trades total={len(trades_all)}, in_window={len(trades)}")
        if len(trades) > 0:
            print(f"   windowed trades min={trades['timestamp'].min()}, max={trades['timestamp'].max()}")
            print(f"   windowed entries min={trades['entry_time'].min()}, max={trades['entry_time'].max()}")

    if trades.empty:
        print("ℹ️ Pas de trades dans la fenêtre de tracé.")
        return

    reason_color = {
        'TP1': 'lime',
        'TP2': 'green',
        'TP2_full': 'green',
        'SL': 'red',
        'REV': 'gray',
        'TIME': 'orange',
        'EOD': 'blue'
    }

    for idx, (_, tr) in enumerate(trades.iterrows()):
        entry_t = tr['entry_time'].to_pydatetime().replace(tzinfo=None)
        exit_t = tr['timestamp'].to_pydatetime().replace(tzinfo=None)
        # Jitter léger et clamp dans la fenêtre
        phase = (idx % jitter_cycle) - (jitter_cycle // 2)
        entry_num = mdates.date2num(entry_t) + phase * jitter_unit
        exit_num = mdates.date2num(exit_t) + phase * jitter_unit
        entry_num = min(max(entry_num, mdates.date2num(t_min)), mdates.date2num(t_max))
        exit_num = min(max(exit_num, mdates.date2num(t_min)), mdates.date2num(t_max))

        side = tr['signal']
        entry_color = '#1abc9c' if side == 'BUY' else '#c0392b'
        exit_color = reason_color.get(tr['exit_reason'], '#2c3e50')

        ax.scatter(
            entry_num,
            tr['entry'],
            marker='^' if side == 'BUY' else 'v',
            color=entry_color,
            edgecolors='black',
            linewidths=0.6,
            s=55,
            zorder=6,
        )
        ax.scatter(
            exit_num,
            tr['exit'],
            marker='D',
            color=exit_color,
            edgecolors='black',
            linewidths=0.6,
            s=55,
            zorder=6,
        )

        if label_trades:
            ax.text(
                exit_num,
                tr['exit'],
                str(idx + 1),
                fontsize=7,
                color='black',
                ha='center',
                va='bottom',
                zorder=7,
                bbox=dict(facecolor='white', edgecolor='none', alpha=0.6, boxstyle='round,pad=0.1')
            )

        # SL / TP niveaux
        if not pd.isna(tr.get('stop')):
            ax.plot([entry_num, exit_num], [tr['stop'], tr['stop']], linestyle='--', color='#e74c3c', alpha=0.8, linewidth=2.0)
        if not pd.isna(tr.get('tp1')):
            ax.plot([entry_num, exit_num], [tr['tp1'], tr['tp1']], linestyle=':', color='#2ecc71', alpha=0.8, linewidth=2.0)
        if not pd.isna(tr.get('tp2')):
            ax.plot([entry_num, exit_num], [tr['tp2'], tr['tp2']], linestyle='-.', color='#1abc9c', alpha=0.85, linewidth=2.0)

    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    ax.set_title('Backtest - Bougies + Trades', fontsize=14, fontweight='bold')
    ax.set_ylabel('Prix')
    ax.grid(True, alpha=0.25, linewidth=0.6)

    # Légende simple avec symboles et traits
    buy_patch = plt.Line2D([0], [0], marker='^', color='w', label='Entrée BUY', markerfacecolor='#1abc9c', markeredgecolor='black', markersize=9)
    sell_patch = plt.Line2D([0], [0], marker='v', color='w', label='Entrée SELL', markerfacecolor='#c0392b', markeredgecolor='black', markersize=9)
    tp_line = plt.Line2D([0, 1], [0, 0], color='#2ecc71', linestyle=':', linewidth=2, label='TP1/TP2')
    sl_line = plt.Line2D([0, 1], [0, 0], color='#e74c3c', linestyle='--', linewidth=2, label='SL')
    ax.legend(handles=[buy_patch, sell_patch, tp_line, sl_line], loc='upper left', frameon=True, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"📈 Graphique sauvegardé : {output_path}")


def main():
    symbol = os.getenv('SYMBOL', 'BTC/USDT')
    timeframe = os.getenv('TIMEFRAME', '1h')
    exchange_name = os.getenv('EXCHANGE', 'kraken')
    hist_exchange_name = os.getenv('HIST_EXCHANGE', 'binance')
    start_date = os.getenv('START_DATE', '2017-08-17')

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

    warmup_bars = int(os.getenv('WARMUP_BARS', '220'))
    trades, signal_counts = compute_trades(df, warmup_bars=warmup_bars)

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

    if os.getenv('PLOT_TRADES', 'true').lower() == 'true':
        out_path = os.getenv('PLOT_PATH', 'backtest_plot.png')
        plot_days = int(os.getenv('PLOT_DAYS', '35'))
        max_bars_env = os.getenv('PLOT_MAX_BARS')
        max_bars = int(max_bars_env) if max_bars_env else None
        plot_trades(df, trades, output_path=out_path, max_bars=max_bars, days_window=plot_days)


if __name__ == "__main__":
    main()
