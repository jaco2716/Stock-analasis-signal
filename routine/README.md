# Stock Analysis Routine

Python analysis routine for the stock trading signal system. Iterates active profiles, fetches prices, computes technicals, gathers news via Claude `web_search`, and emits a single LLM-judged BUY/SELL/HOLD signal per holding to Supabase and Discord.

## Setup

```bash
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"   # pytest, pytest-mock, responses, ruff
cp .env.example .env                # fill in keys
```

## Run

```bash
python -m run_analysis                          # all active profiles
python -m run_analysis --profile alice          # single profile by slug
python -m run_analysis --ticker NOVO-B.CO       # single ticker
python -m run_analysis --dry-run --verbose      # no writes, debug logs
```

## Test

```bash
pytest
```

## Layout

- `run_analysis.py` — thin orchestrator
- `lib/` — config, models, DB, market data, technicals, news, analyzer, discord, logging
- `tests/` — unit tests (no network)
