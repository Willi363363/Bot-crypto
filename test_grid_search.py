import os
from pathlib import Path
from datetime import timezone

import ccxt
import optuna
import pandas as pd
from dotenv import load_dotenv

from src.indicators import TechnicalIndicators
from test_backtest import build_dataframe, compute_stats, compute_trades, fetch_all_ohlcv

load_dotenv()

# Cache global pour éviter de recharger les données à chaque essai
_df_cache = None


def load_dataset():
    global _df_cache
    if _df_cache is not None:
        return _df_cache

    symbol = os.getenv("SYMBOL", "BTC/USDT")
    timeframe = os.getenv("TIMEFRAME", "1h")
    hist_exchange_name = os.getenv("HIST_EXCHANGE", "binance")
    start_date = os.getenv("START_DATE", "2017-08-17")

    exchange = getattr(ccxt, hist_exchange_name)({"enableRateLimit": True})
    since_ms = int(pd.Timestamp(start_date, tz=timezone.utc).timestamp() * 1000)

    cache_dir = Path("data")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"ohlcv_{hist_exchange_name}_{symbol.replace('/', '-')}_{timeframe}.csv"

    if cache_file.exists():
        df = pd.read_csv(cache_file, parse_dates=["timestamp"], index_col="timestamp")
    else:
        ohlcv = fetch_all_ohlcv(exchange, symbol, timeframe, since_ms, limit=720)
        df = build_dataframe(ohlcv)
        df.reset_index().to_csv(cache_file, index=False)
        df.set_index("timestamp", inplace=True)

    df = TechnicalIndicators.add_all_indicators(df)
    _df_cache = df
    return df


def apply_params_to_env(params: dict):
    for key, value in params.items():
        os.environ[key] = str(value)


# Espace de recherche (bornes raisonnables autour des valeurs actuelles)


def objective(trial):
    df = load_dataset()

    params = {
        "VOLUME_RATIO_MIN": trial.suggest_float("VOLUME_RATIO_MIN", 0.50, 1.00),
        "VOLUME_SPIKE_MIN": trial.suggest_float("VOLUME_SPIKE_MIN", 1.05, 1.80),
        "CHOP_NO_TRADE_MAX": trial.suggest_float("CHOP_NO_TRADE_MAX", 45.0, 75.0),
        "ATR_PCT_MIN": trial.suggest_float("ATR_PCT_MIN", 0.0020, 0.0090),
        "ATR_EXTREME_MULT": trial.suggest_float("ATR_EXTREME_MULT", 2.0, 4.0),
        "RSI_MIN": trial.suggest_int("RSI_MIN", 30, 48),
        "RSI_MAX": trial.suggest_int("RSI_MAX", 55, 72),
        "ATR_STOP_MULT": trial.suggest_float("ATR_STOP_MULT", 1.2, 2.8),
        "TP1_MULT": trial.suggest_float("TP1_MULT", 1.2, 2.4),
        "TP2_MULT": trial.suggest_float("TP2_MULT", 2.2, 4.2),
        "COOLDOWN_BARS": trial.suggest_int("COOLDOWN_BARS", 6, 26),
        "COOLDOWN_BARS_SL": trial.suggest_int("COOLDOWN_BARS_SL", 8, 32),
        "TIME_STOP_BARS": trial.suggest_int("TIME_STOP_BARS", 16, 48),
    }

    # Contraintes simples pour garder des combinaisons réalistes
    if params["RSI_MAX"] <= params["RSI_MIN"] + 3:
        raise optuna.TrialPruned()
    if params["COOLDOWN_BARS_SL"] < params["COOLDOWN_BARS"]:
        params["COOLDOWN_BARS_SL"] = params["COOLDOWN_BARS"] + 2

    apply_params_to_env(params)

    initial_capital = float(os.getenv("INITIAL_CAPITAL", "100"))
    warmup_bars = int(os.getenv("WARMUP_BARS", "220"))

    trades, _ = compute_trades(df, warmup_bars=warmup_bars)
    stats = compute_stats(trades, "trial", initial_capital)

    # Écarter les configurations trop peu actives
    if stats["trades"] < 6:
        raise optuna.TrialPruned()

    return stats["final_capital"]


def main():
    n_trials = int(os.getenv("GRID_TRIALS", "500"))
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, n_jobs=1, show_progress_bar=True)

    best_params = study.best_params
    apply_params_to_env(best_params)

    df = load_dataset()
    initial_capital = float(os.getenv("INITIAL_CAPITAL", "100"))
    warmup_bars = int(os.getenv("WARMUP_BARS", "220"))
    trades, _ = compute_trades(df, warmup_bars=warmup_bars)
    stats = compute_stats(trades, "best", initial_capital)

    print("\nMeilleure configuration :")
    for k, v in best_params.items():
        print(f"- {k} = {v}")

    print("\nPerformances avec les meilleurs paramètres :")
    print(f"Trades: {stats['trades']}")
    print(f"Capital final: {stats['final_capital']:.2f} €")
    print(f"Rendement: {stats['total_return'] * 100:.2f}%")
    print(f"Win rate: {stats['win_rate'] * 100:.2f}%")


if __name__ == "__main__":
    main()
