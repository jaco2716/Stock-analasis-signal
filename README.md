# Stock Analysis Signal

Automated trading-signal pipeline for a Copenhagen-listed equity portfolio. Three times each weekday, a scheduled Anthropic agent fetches market data, asks Claude for a BUY/SELL/HOLD judgment per ticker, writes the result to Supabase, and posts a notification to Discord. A small Next.js dashboard renders the current state.

## The three pieces

- **`frontend/`** - Next.js 15 (App Router) on Vercel. Tailwind + shadcn/ui. Server Components read from Supabase with the anon key; Server Actions write through the service-role key. Renders profiles, holdings, the latest signals, and recent run status.
- **`routine/`** - Python 3.12 analysis script. Pulls prices, computes technical indicators deterministically in helpers, then calls Claude from `analyzer.py` for the per-ticker judgment only. Writes signals + a row in `analysis_runs`, then posts to each profile's Discord webhook (or the default).
- **`db/`** - Supabase Postgres. Migrations under `db/migrations/` define profiles, portfolio_holdings, analysis_runs, signals, plus RLS policies and indexes. `db/seed.sql` populates one default profile.

## Get started

Full setup (Supabase project, Vercel import, Discord webhooks, Anthropic key, scheduled-agent registration, local dev): see [`docs/SETUP.md`](docs/SETUP.md).

Architecture and design notes: see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

Operations and debugging: see [`docs/RUNBOOK.md`](docs/RUNBOOK.md).
