# Contributing

Thanks for your interest in improving this project.

## Development Setup

1. Fork and clone the repository.
2. Create a virtual environment.
3. Install dependencies.
4. Copy `.env.example` to `.env` and set your local values.

```bash
git clone https://github.com/Willi363363/Bot-crypto.git
cd Bot-crypto
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Branch and Commit Guidelines

- Create a feature branch from `dev`.
- Keep commits focused and readable.
- Use clear commit messages.

Recommended commit style:

- `feat: add ATR filter tuning`
- `fix: prevent duplicate heartbeat message`
- `docs: update setup instructions`

## Pull Requests

- Explain what changed and why.
- Include manual test steps.
- Include screenshots/log snippets if behavior changed.
- Keep PR scope small when possible.

## Local Validation

Run the scripts relevant to your changes:

```bash
python main.py
python test_connection.py
python test_new_strategy.py
python test_backtest.py
python test_grid_search.py
```

## Code Style

- Prefer small, explicit functions.
- Avoid hidden side effects.
- Keep environment variable names consistent with `.env.example`.
- Update documentation when behavior or configuration changes.

## Security

- Never commit real API keys or webhook URLs.
- Keep `.env`, cache files, and generated artifacts out of Git.
