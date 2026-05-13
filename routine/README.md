# Stock Analysis Routine

Python data-plumbing for the stock trading signal system. Fetches prices, computes technicals, writes a JSON brief, then commits per-holding signals to Supabase + Discord. The scheduled-agent session itself does the BUY/SELL/HOLD judgment using the brief + WebSearch — there is no Anthropic SDK call from this codebase.

## Setup

```bash
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"   # pytest, pytest-mock, responses, ruff
cp .env.example .env                # fill in Supabase + Discord
```

No `ANTHROPIC_API_KEY` is required.

## CLI

Three subcommands. The scheduled agent runs them in this order; locally you can do the same to smoke-test.

```bash
# 1. Gather data, write brief to /tmp/stock-analysis-brief.json, start an analysis_runs row.
python -m run_analysis prepare [--profile SLUG] [--ticker SYMBOL] [--dry-run] [--verbose]
#    -> prints: run_id=<uuid>
#               brief_path=/tmp/stock-analysis-brief.json

# 2. Commit one decided signal: insert row + post Discord embed.
python -m run_analysis emit-signal \
  --run-id <uuid> --profile-id <uuid> --ticker NOVO-B.CO \
  --signal BUY|SELL|HOLD --confidence 0.75 --reasoning "..." \
  [--brief-path PATH] [--dry-run] [--verbose]

# 3. Close the run.
python -m run_analysis finish-run \
  --run-id <uuid> --status success|partial|failed \
  [--profile-count N] [--signal-count N] [--error "..."] [--dry-run]

# 4. (Separate cron task) Backfill realised T+5 / T+30 returns onto past signals.
python -m run_analysis score-signals [--window 5|30|both] [--batch 200] [--dry-run]
```

Run `score-signals` daily after market close (suggested cron: 22:00 UTC) on its own
schedule — it does not depend on `prepare`. The job updates the `outcome_t5_pct` /
`outcome_t30_pct` columns added in migration `db/migrations/0006_signal_outcomes.sql`,
and those values are then surfaced to the agent through `signal_history` in the next
brief.

`--dry-run` skips Supabase writes and Discord posts everywhere; `prepare` still writes the brief file (the agent and downstream subcommands need it).

## Local smoke test

```bash
python -m run_analysis prepare --dry-run --profile default --verbose
cat /tmp/stock-analysis-brief.json | jq '.profiles[0].holdings[0]'

python -m run_analysis emit-signal \
  --run-id 00000000-0000-0000-0000-000000000000 \
  --profile-id <profile-id-from-brief> \
  --ticker NOVO-B.CO --signal HOLD --confidence 0.5 \
  --reasoning "smoke test" --dry-run --verbose
```

## Test

```bash
pytest
```

## Layout

- `run_analysis.py` — argparse subcommand dispatcher
- `agent_prompt.md` — the prompt registered with the Anthropic scheduled agent
- `lib/`
  - `config.py` — pydantic Settings, env loading
  - `models.py` — dataclasses mirroring the Supabase schema
  - `supabase_client.py` — typed read/write wrappers
  - `market_data.py` — yfinance + per-run cache + retries
  - `technicals.py` — pure indicator math (RSI, SMAs, MACD, %30d)
  - `brief.py` — assembles the JSON brief consumed by the agent
  - `discord.py` — embed + 429-aware POST, per-profile webhook fallback
  - `logging.py` — logger setup
- `tests/` — pytest unit tests (no network)


## Run locally

Paste this prompt in CLaude code, to run in local session:
```
You are the stock-analysis signal agent. The repo is already cloned into your session — your initial cwd is the repo root.

Read `routine/agent_prompt.md` and follow its instructions exactly. Do not read any other repo files for context; the agent_prompt + the brief from `prepare` are exhaustive.  
```