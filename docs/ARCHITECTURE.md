# Architecture

## High-level diagram

```
                  +--------------------------------------------+
                  |  Anthropic scheduled agent (cron, stateless)|
                  |  30 9,13,16 * * 1-5  Europe/Copenhagen      |
                  |                                             |
                  |  Step 1: prepare --> brief.json             |
                  |  Step 2: per holding {                       |
                  |            WebSearch news (in-session)       |
                  |            reason over indicators + news     |
                  |            emit-signal --signal ... ...      |
                  |          }                                  |
                  |  Step 3: finish-run                          |
                  +-----------+----------------+----------------+
                              |                |
                       prepare/emit/finish      |
                              v                v
+---------------------+   +-----------------------------+
|  Yahoo Finance /    |<->|  routine/ (data plumbing)   |
|  market data source |   |  run_analysis.py prepare    |
+---------------------+   |     -> lib/market_data.py   |
                          |     -> lib/technicals.py    |
                          |     -> lib/brief.py         |
                          |  run_analysis.py emit-signal|
                          |     -> lib/supabase_client  |
                          |     -> lib/discord.py       |
                          |  run_analysis.py finish-run |
                          +------+-----------------+----+
                                 | service_role    |
                                 v                 v
                          +---------------+   +-------------+
                          |   Supabase    |   |  Discord    |
                          |   Postgres    |   |  webhooks   |
                          +-------+-------+   +-------------+
                                  ^
                                  | anon (read) / service_role (write)
                                  |
                          +-------+-------+
                          |  frontend/    |
                          |  Next.js 15   |
                          |  on Vercel    |
                          +-------+-------+
                                  ^
                                browser
```

## The LLM / deterministic-code split

A core design rule: **the agent's session does judgment; Python does everything else**. There is no Anthropic SDK call from the codebase — the LLM is the scheduled-agent runtime itself.

| Concern | Where it lives | Why |
|---|---|---|
| Fetching OHLCV bars | `routine/lib/market_data.py` | Deterministic, cheap, easily cached |
| RSI, SMAs, MACD, % change | `routine/lib/technicals.py` | Pure math; no tokens needed |
| Building the JSON brief | `routine/lib/brief.py` | Pure data transformation |
| Fetching news | The agent's `WebSearch` tool, in-session | No code, no extra API keys, billed via Code subscription |
| Per-ticker BUY/SELL/HOLD + reasoning | The agent itself, guided by `routine/agent_prompt.md` | Judgment job |
| Persisting signals + run row | `routine/lib/supabase_client.py` | Pure write |
| Discord embed shape + posting | `routine/lib/discord.py` | Pure formatting + HTTP |
| CLI surface (`prepare` / `emit-signal` / `finish-run`) | `routine/run_analysis.py` | Stable contract between agent and Python |

The methodology (RSI thresholds, MACD interpretation, decision rules per kind, confidence calibration) is encoded in `routine/agent_prompt.md`. To tune analysis behavior you edit that file; to tune what data is available to the agent you extend the brief in `lib/brief.py`.

## Data flow per run

1. Agent fires at the cron tick. It clones the repo and `pip install`s `routine/requirements.txt`.
2. `python -m run_analysis prepare`:
   - Inserts a row into `analysis_runs` with `status = 'running'`, returns the `run_id`.
   - Loads all `profiles` where `is_active = true`.
   - For each profile, loads `portfolio_holdings`. For each ticker, pulls 6mo bars (cached per run) and computes the indicator set.
   - Derives per owned holding (in the holding's `currency`): `cost_basis = quantity × avg_buy_price`, `current_value = quantity × current_price`, `pnl`, `pnl_pct`. Watchlist rows leave these `null`. No FX conversion is performed — yfinance returns `current_price` in the security's native currency, which must match the holding's stored currency.
   - Writes `/tmp/stock-analysis-brief.json` with the full input the agent will reason over.
   - Prints `run_id` + `brief_path` for the agent to capture.
3. The agent reads the brief. For each (profile, holding):
   - Uses `WebSearch` for last-14-days news on the ticker.
   - Reasons over the indicators + news + position context per the rules in `agent_prompt.md`.
   - Calls `python -m run_analysis emit-signal --run-id ... --profile-id ... --ticker ... --signal ... --confidence ... --reasoning "..."`.
4. Each `emit-signal` invocation:
   - Reads the brief to recover price/indicator/position context.
   - Inserts a row into `signals`.
   - Builds and posts a Discord embed. Routing rule:
     - `profile.discord_webhook_url` set -> post there.
     - `null` -> post to `DEFAULT_DISCORD_WEBHOOK_URL` and prefix the title with `[<profile.name>]`.
5. After the loop the agent calls `python -m run_analysis finish-run --run-id ... --status success|partial|failed --profile-count N --signal-count N`. The `analysis_runs` row updates with `completed_at`, counts, status, and (if non-success) an error message.

If any single `emit-signal` fails, the agent continues with the rest and marks the run `partial`. A hard infrastructure failure on `prepare` (DB unreachable) leaves no `analysis_runs` row to close — the agent should mark such a run `failed` only after a successful `prepare`.

## Multi-profile model

A profile is the unit of:

- A holdings list (owned + watchlist)
- A signal stream
- A Discord destination (optional override)

Profiles are independent: holdings, signals, and webhook settings don't cross between them. The frontend renders one tab/section per active profile. Adding a profile is a SQL insert (see `docs/SETUP.md` section 8); no code change is needed.

The schema is shaped so that a future migration to per-user accounts (one Supabase auth user can own many profiles, each user only sees theirs) is a localized RLS change, not a redesign. See the comment block at the top of `db/migrations/0002_rls_policies.sql`.

## Frontend boundaries

- **Reads** (lists, dashboards, signal history) -> Server Components using a Supabase client built with the **anon** key. RLS allows them.
- **Writes** (admin actions: add/remove holding, toggle profile active, edit webhook) -> Server Actions using a Supabase client built with the **service_role** key. The key never leaves the server.
- The browser bundle never sees `SUPABASE_SERVICE_ROLE_KEY`. Keep the env var unchecked for "Available in browser" in Vercel.

## Why a stateless scheduled agent (not a long-running worker)

- No infra to maintain (no VPS, no cron container, no log volume).
- Crash-safe: every tick starts from a clean checkout.
- Cheap: only billed for the seconds the routine actually runs.
- Auditable: every run leaves a row in `analysis_runs`.

Trade-off: cold start. Each tick pays for `git clone` + `pip install`. With three runs per weekday, the overhead is negligible; for high-frequency triggers we'd switch to a different model.
