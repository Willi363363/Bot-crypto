# Crypto Trading Bot

[![Scheduled Analysis](https://github.com/Willi363363/Bot-crypto/actions/workflows/trading-bot.yml/badge.svg?branch=dev)](https://github.com/Willi363363/Bot-crypto/actions/workflows/trading-bot.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Python trading-signal bot for BTC/USDT with Discord notifications, backtesting, and parameter optimization.

This project is focused on learning and experimentation: strategy design, indicator engineering, and reproducible evaluation.

## Features

- Real-time market data using CCXT (default exchange: Kraken).
- Technical indicator pipeline (EMA, RSI, ATR, MACD, VWAP, Bollinger squeeze, market structure).
- Rule-based strategy that returns BUY, SELL, or NEUTRAL signals.
- Discord notifications for signals and heartbeat status.
- Stateful signal deduplication via `state.json`.
- Backtest engine with fees, slippage, ATR-based stop/take-profit, partial TP, and cooldown logic.
- Optuna grid search for strategy parameter tuning.
- GitHub Actions workflow for scheduled runs.

## Project Structure

| Path | Purpose |
| --- | --- |
| `main.py` | Main entry point: fetch data, compute indicators, generate signal, send notifications. |
| `src/data_fetcher.py` | OHLCV/ticker retrieval via CCXT. |
| `src/indicators.py` | Indicator calculations and feature engineering. |
| `src/strategy.py` | Main strategy logic (`ImprovedStrategy`). |
| `src/notifier.py` | Discord webhook messaging (signal + heartbeat + test mode). |
| `src/state_manager.py` | Persistent state to avoid duplicate alerts. |
| `test_connection.py` | Manual connectivity and Discord test script. |
| `test_new_strategy.py` | Manual strategy sanity-check script. |
| `test_simulation.py` | Loop runner for local test mode. |
| `test_backtest.py` | Historical backtesting and chart output. |
| `test_grid_search.py` | Optuna optimization script. |
| `.github/workflows/trading-bot.yml` | Scheduled GitHub Actions execution. |

## Requirements

- Python 3.11+ recommended.
- A Discord webhook URL.
- Internet connection for exchange data.

## Quick Start

1. Clone the repository.

```bash
git clone https://github.com/Willi363363/Bot-crypto.git
cd Bot-crypto
```

2. Create and activate a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies.

```bash
pip install -r requirements.txt
```

4. Create your environment file.

```bash
cp .env.example .env
```

5. Fill at least these keys in `.env`:

- `DISCORD_WEBHOOK_URL`
- `DISCORD_HEARTBEAT_WEBHOOK_URL` (optional, falls back to signal webhook)

6. Run the bot.

```bash
python main.py
```

## Main Commands

- Run live analysis once: `python main.py`
- Test exchange + webhook flow: `python test_connection.py`
- Run local loop in test mode: `python test_simulation.py`
- Backtest strategy: `python test_backtest.py`
- Run Optuna search: `python test_grid_search.py`

Example with custom trials:

```bash
GRID_TRIALS=100 python test_grid_search.py
```

## Configuration

All runtime settings are environment variables. See `.env.example` for the complete list.

Important groups:

- Market/runtime: `SYMBOL`, `TIMEFRAME`, `EXCHANGE`, `DATA_LIMIT`, `SEND_HEARTBEAT`
- Discord: `DISCORD_WEBHOOK_URL`, `DISCORD_HEARTBEAT_WEBHOOK_URL`, `DISCORD_TEST_WEBHOOK_URL`, `TEST_MODE`
- Strategy filters: `VOLUME_RATIO_MIN`, `VOLUME_SPIKE_MIN`, `CHOP_NO_TRADE_MAX`, `ATR_PCT_MIN`, `ATR_EXTREME_MULT`, `RSI_MIN`, `RSI_MAX`
- Risk management: `ATR_STOP_MULT`, `TP1_MULT`, `TP2_MULT`, `COOLDOWN_BARS`, `COOLDOWN_BARS_SL`, `TIME_STOP_BARS`
- Backtest: `INITIAL_CAPITAL`, `FEE_RATE`, `SLIPPAGE_BPS`, `HIST_EXCHANGE`, `START_DATE`, `WARMUP_BARS`, `LONG_ONLY`
- Plotting: `PLOT_TRADES`, `PLOT_PATH`, `PLOT_DAYS`, `PLOT_MAX_BARS`, `PLOT_LABEL_TRADES`, `PLOT_DEBUG`, `PLOT_START_DATE`

## GitHub Actions

The workflow in `.github/workflows/trading-bot.yml` runs on a schedule and can also be triggered manually.

Required GitHub repository secrets:

- `DISCORD_WEBHOOK_URL`
- `DISCORD_HEARTBEAT_WEBHOOK_URL`

## Notes

- `state.json` is intentionally local and ignored in Git.
- `data/` is ignored and used as a cache for historical OHLCV CSV files.
- This repository uses executable Python scripts for validation/backtesting rather than a full `pytest` suite.

## Portfolio and Skills

This repository is part of my software engineering learning journey as a first-year Epitech Montpellier student.

What this project demonstrates:

- Python application architecture with modular components.
- Market data ingestion and feature engineering for time-series analysis.
- Strategy implementation and rule-based decision systems.
- Backtesting methodology with realistic constraints (fees, slippage, risk controls).
- Practical DevOps basics with scheduled GitHub Actions workflows.
- Documentation discipline and reproducible local setup.

Current focus areas:

- Writing cleaner tests and improving reliability.
- Improving strategy robustness across market regimes.
- Strengthening code quality standards for team collaboration.

## Disclaimer

This software is for educational purposes only. It is not financial advice. Use at your own risk.

## Contributing

See `CONTRIBUTING.md`.

## License

MIT License. See `LICENSE`.
