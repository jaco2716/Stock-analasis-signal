# Architecture

## High-level diagram

```
                                     +--------------------------+
                                     |  Anthropic scheduled     |
                                     |  agent (cron, stateless) |
                                     |  30 9,13,16 * * 1-5      |
                                     |  Europe/Copenhagen       |
                                     +-----------+--------------+
                                                 |
                                  git clone + pip install + run
                                                 v
+---------------------+        +--------------------------------------+
|  Yahoo Finance /    |<------>|             routine/                 |
|  market data source |        |  run_analysis.py (orchestrator)      |
+---------------------+        |    -> lib/data.py    (fetch prices)  |
                               |    -> lib/indicators.py (RSI, MA...) |
                               |    -> lib/analyzer.py (Claude call)  |
                               |    -> lib/discord.py  (post embed)   |
                               +-------+------------------------+-----+
                                       | service_role           |
                                       v                        v
                               +-------------------+   +-------------------+
                               |   Supabase        |   |   Discord         |
                               |   Postgres        |   |   webhooks        |
                               |  - profiles       |   |  - per-profile    |
                               |  - holdings       |   |    or default     |
                               |  - analysis_runs  |   +-------------------+
                               |  - signals        |
                               +---------+---------+
                                         ^
                                         | anon (read) / service_role (write)
                                         |
                               +---------+---------+
                               |  frontend/        |
                               |  Next.js 15 on    |
                               |  Vercel           |
                               |  - RSC reads      |
                               |  - Server Actions |
                               |    write          |
                               +-------------------+
                                         ^
                                         |
                                       browser
```

## The LLM / deterministic-code split

A core design rule: **the model only does judgment**. Anything that can be written as code, is.

| Concern | Where it lives | Why |
|---|---|---|
| Fetching OHLCV bars | `routine/lib/data.py` | Deterministic, cheap, easily cached |
| RSI, moving averages, volatility, % change | `routine/lib/indicators.py` | Pure math; no reason to spend tokens on it |
| Per-ticker BUY/SELL/HOLD + reasoning | `routine/lib/analyzer.py` | The only place that calls Claude |
| Persisting signals + run row | `routine/lib/db.py` | Pure write |
| Discord embed shape + posting | `routine/lib/discord.py` | Pure formatting + HTTP |
| Orchestration / loop | `routine/run_analysis.py` | Pure control flow |

`analyzer.py` receives a structured payload (ticker, position size, current indicator values, recent price action) and returns `{signal_type, confidence, reasoning}`. That structured input keeps the prompt short and lets us swap the model without rewriting the rest.

## Data flow per run

1. Agent fires at the cron tick. It clones the repo, installs deps, runs `python -m run_analysis`.
2. `run_analysis.py` inserts a row into `analysis_runs` with `status = 'running'`.
3. It loads all `profiles` where `is_active = true`.
4. For each profile, it loads `portfolio_holdings` (both `owned` and `watchlist`).
5. For each unique ticker in scope, `data.py` pulls bars; `indicators.py` computes the feature set. (Cached per run so two profiles holding the same ticker only fetch once.)
6. For each (profile, ticker) pair, `analyzer.py` calls Claude with the indicator features + the holding context (owned vs watchlist, position size). It returns a signal.
7. Signals are inserted into `signals` with the run id.
8. Per profile, `discord.py` builds an embed and posts it. Routing rule:
   - `profile.discord_webhook_url` set -> post there.
   - `null` -> post to `DEFAULT_DISCORD_WEBHOOK_URL` and prefix the title with `[<profile.name>]`.
9. The `analysis_runs` row is updated: `completed_at = now()`, `signal_count`, `profile_count`, `status = 'success'` (or `'partial'` / `'failed'` with `error_message`).

If any single profile fails, the run is marked `partial` and the rest still complete. A hard infrastructure failure (DB unreachable on the run insert) is the only thing that produces `failed`.

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
