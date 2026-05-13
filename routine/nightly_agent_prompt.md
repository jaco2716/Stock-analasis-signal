# Nightly backfill agent prompt

Register this as the prompt for the Anthropic scheduled agent that runs once
nightly (suggested cron: `0 22 * * 1-5 UTC`, i.e. weekday evenings after US
market close). It is independent of the per-tick analysis agent driven by
[`agent_prompt.md`](agent_prompt.md).

---

You are running the nightly backfill jobs for the stock-analysis routine. This
is a chained two-command job: no Discord, no commits, no PRs.

Setup and run:

```bash
cd routine
python3.12 -m venv .venv
source .venv/bin/activate
pip install --quiet -r requirements.txt
python -m run_analysis score-signals --window both \
  && python -m run_analysis backfill-signal-prices
```

If `pip install` fails, retry it once. If it still fails, report the error and
exit non-zero. If `score-signals` fails, `backfill-signal-prices` will not run
(intentional — the `&&` chain stops on first failure).

## What the commands do

**`score-signals --window both`** — for each row in the Supabase `signals` table
that is old enough to score (≥5 trading days for T+5, ≥30 trading days for
T+30) and doesn't yet have an outcome, pulls the close price at the anchor and
at T+N from yfinance, computes the realized % return, and writes it back to
`signals.outcome_t5_pct` / `outcome_t30_pct`. Idempotent — running again is
harmless. "No pending signals" is the normal state until enough signals have
aged.

**`backfill-signal-prices`** — for each row in `signals` where
`price_at_signal` is null, looks up the close price at `generated_at` from
yfinance and writes it to `signals.price_at_signal` + `signals.currency`. Also
idempotent. Catches up signals that were created before live `emit-signal`
began writing the price directly, and signals that were generated after the
last available yfinance close on a previous run.

## Required environment variables

Must be set as routine secrets:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

No other secrets are needed. `SEC_EDGAR_USER_AGENT` and
`DEFAULT_DISCORD_WEBHOOK_URL` are used by the main `prepare` / `emit-signal`
routines, not by this nightly job.

## Reporting

When finished, report the final summary lines from the logs of both commands,
for example:

```
score-signals: T+5 scored=3 skipped=12
score-signals: T+30 scored=1 skipped=14
score-signals done: scored=4 skipped=26
backfill-signal-prices done: written=2 skipped=0 reasons={}
```

Exit cleanly. Do not modify the repo or open PRs.
