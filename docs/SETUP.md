# Setup

End-to-end setup for the stock-analysis-signal system. Follow the sections in order on a fresh machine and a fresh Supabase project. Every external service the system depends on is covered here.

## What you will end up with

- A Supabase project with the schema applied and one default profile seeded.
- A Vercel deployment of the dashboard wired to that Supabase project.
- An Anthropic-managed scheduled agent that runs the routine three times each weekday and posts to Discord.
- Working local dev for both the frontend and the Python routine.

## Prerequisites

Install once, globally:

```bash
# Node 20+ and pnpm (or npm)
node -v          # >= 20
corepack enable
corepack prepare pnpm@latest --activate

# Python 3.12
python3.12 --version

# Supabase CLI
brew install supabase/tap/supabase

# Vercel CLI
pnpm add -g vercel

# GitHub CLI (for repo creation if you do not already have one)
brew install gh && gh auth login
```

Also have ready:

- A GitHub account and an empty repo named e.g. `stock-analysis-signal`.
- A Discord server where you can create webhooks.

> The analysis runs inside the scheduled-agent session and is billed against your Claude Code subscription. No separate Anthropic API key is required.

---

## 1. Supabase project

### 1.1 Create the project

1. Go to <https://supabase.com/dashboard> -> **New project**.
2. Name: `stock-analysis-signal`. Region: `eu-central-1` (Frankfurt) or `eu-west-1` (Ireland) for low latency from Copenhagen.
3. Set a strong database password and save it to your password manager.
4. Wait for the project to provision (~2 min).

### 1.2 Capture the keys

From **Project Settings -> API** copy:

- **Project URL** -> this is `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL`.
- **anon public** key -> `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- **service_role** key -> `SUPABASE_SERVICE_ROLE_KEY`. Treat as a password. Never commit, never expose to the browser.

From **Project Settings -> General** copy the **Reference ID** (a 20-char string). You'll need it to link the CLI.

### 1.3 Link the CLI and run migrations

From the repo root:

```bash
supabase login
supabase link --project-ref <your-ref-id>
# Apply each migration in order against the linked project.
# (Migrations live at db/migrations/, not the default supabase/migrations/,
# so `supabase db push` won't pick them up — apply them explicitly:)
for f in db/migrations/*.sql; do
  echo "Applying $f"
  supabase db query --linked -f "$f" || break
done
# Or, if you prefer manual control, paste each file from db/migrations/
# into the Supabase SQL editor in order: 0001 -> 0002 -> 0003 -> 0004.
```

### 1.4 Seed the default profile

```bash
supabase db query --linked -f db/seed.sql
# Or paste db/seed.sql into the SQL editor.
```

Verify in **Table Editor**: `profiles` should have one row (`Default` / `default`), `portfolio_holdings` should have NOVO-B.CO (owned) and MAERSK-B.CO (watchlist).

### 1.5 Generate the TypeScript types

The frontend imports `Database` from `frontend/lib/database.types.ts`. Regenerate it after every migration. Run from the **repo root** so the CLI uses the root-level `supabase/` link state (running it from `frontend/` creates a second `supabase/` link folder there — don't):

```bash
supabase gen types typescript --linked > frontend/lib/database.types.ts
```

See [`SCHEMA.md`](SCHEMA.md) for the full sync discipline (TS + Python).

---

## 2. Discord webhooks

You need at minimum one default webhook. Per-profile webhooks are optional.

### 2.1 Default webhook (required)

1. Discord -> pick a channel (e.g. `#signals`) -> **Edit Channel** -> **Integrations** -> **Webhooks** -> **New Webhook**.
2. Name it `Signal Bot (default)`. Copy the URL.
3. Save it as the env var `DEFAULT_DISCORD_WEBHOOK_URL` (used by the routine and by the scheduled-agent secrets).

### 2.2 Per-profile webhook (optional)

When you create a second profile and want its signals to land in a different channel:

1. Create a webhook in the target channel as above.
2. Update the profile row:

```sql
update profiles
   set discord_webhook_url = 'https://discord.com/api/webhooks/...'
 where slug = 'aggressive';
```

Routing rule: if `profiles.discord_webhook_url` is set, the routine posts there; if `null`, it posts to `DEFAULT_DISCORD_WEBHOOK_URL` and prefixes the embed title with `[<Profile Name>]`.

---

## 3. GitHub repo

The scheduled agent clones the repo on every run (it is stateless between runs), so the repo must be pushed before you register the schedule.

```bash
cd /Users/welin/Documents/Development/Bots/Stock-analasis-signal
git init
git add .
git commit -m "Initial commit"
gh repo create stock-analysis-signal --private --source=. --remote=origin --push
```

Capture the clone URL (HTTPS form) -> `GIT_REPO_URL`. If the repo is private, also create a fine-grained Personal Access Token with `Contents: Read` for that repo and embed it in the URL the agent uses: `https://<token>@github.com/<owner>/stock-analysis-signal.git`.

---

## 4. Vercel deployment (frontend)

### 4.1 Import the project

1. <https://vercel.com/new> -> **Import** the GitHub repo.
2. **Root Directory**: `frontend`.
3. **Framework Preset**: Next.js (auto-detected).
4. **Build Command**: leave default (`next build`).

### 4.2 Environment variables

In **Settings -> Environment Variables** add (Production + Preview + Development):

| Name | Value | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | from 1.2 | exposed to browser |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | from 1.2 | exposed to browser |
| `SUPABASE_SERVICE_ROLE_KEY` | from 1.2 | **server-only** - leave the "Available in browser" box unchecked |

Click **Deploy**.

### 4.3 Verify

Open the deployed URL. The dashboard should render the seeded `Default` profile with NOVO-B.CO and MAERSK-B.CO. If you see a blank state, check the Vercel build logs and the Supabase logs (Project -> Logs -> API).

---

## 5. Scheduled agent (the routine)

The routine runs as an Anthropic-managed scheduled agent. The agent is stateless: every fire-time it clones the repo, installs deps, prepares a data brief, decides each signal **inside its own Claude session** (using the brief + the `WebSearch` tool), commits each signal back through the script, and exits. Schedule it via Claude Code's `schedule` skill from this project.

### 5.1 Required environment for the agent

Configure these as agent-level secrets when the `schedule` skill prompts for them:

- `GIT_REPO_URL` — the clone URL the agent will use; embed a token if private
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `DEFAULT_DISCORD_WEBHOOK_URL`

No `ANTHROPIC_API_KEY`. The agent's own session is the LLM; analysis cost is metered against your Claude Code subscription.

### 5.2 Register the schedule

From a Claude Code session in this project, invoke the `schedule` skill and provide:

- **Cron**: `30 9,13,16 * * 1-5`
- **Timezone**: `Europe/Copenhagen` (DST is honored automatically; the cron is wall-clock local)
- **Prompt**: paste the full contents of `routine/agent_prompt.md`. That document is the canonical analysis prompt — methodology, decision rules, confidence calibration, and the three-step CLI flow (`prepare` → per-holding `emit-signal` → `finish-run`).

This produces three runs per weekday: 09:30, 13:30, 16:30 local time.

### 5.3 First manual run

From the `schedule` skill, trigger the routine once on demand to confirm the wiring. Then check:

- `analysis_runs` has a new row with `status = 'success'`.
- `signals` has one row per holding the agent decided on.
- The Discord channel received an embed per signal as it was emitted (not all at once at the end).

---

## 6. Local development

### 6.1 Frontend

```bash
cd frontend
cp .env.example .env.local
# Fill in NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY,
# SUPABASE_SERVICE_ROLE_KEY (same values as Vercel).
pnpm install
pnpm dev
# http://localhost:3000
```

### 6.2 Routine

```bash
cd routine
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DEFAULT_DISCORD_WEBHOOK_URL.

# 1. Smoke the data-gathering side without touching Supabase:
python -m run_analysis prepare --dry-run --profile default --verbose
cat /tmp/stock-analysis-brief.json | jq '.profiles[0].holdings[0]'

# 2. Smoke the commit side (no DB write, no Discord post):
python -m run_analysis emit-signal \
  --run-id 00000000-0000-0000-0000-000000000000 \
  --profile-id <id-from-brief> --ticker NOVO-B.CO \
  --signal HOLD --confidence 0.5 --reasoning "smoke test" \
  --dry-run --verbose
```

Locally you do not run the analysis loop yourself — that is the agent's job. If you want to exercise the full chain end-to-end, trigger the scheduled agent manually from the `schedule` skill.

---

## 7. Adding a new profile (operational recipe)

```sql
-- 1. Insert the profile (optionally with its own webhook)
insert into profiles (name, slug, discord_webhook_url, is_active)
values ('Aggressive', 'aggressive', 'https://discord.com/api/webhooks/...', true);

-- 2. Add holdings (quantity = shares held; avg_buy_price_dkk = per share)
insert into portfolio_holdings (profile_id, ticker, name, quantity, avg_buy_price_dkk, kind)
select id, 'ORSTED.CO', 'Orsted', 30, 250.00, 'owned'
from profiles where slug = 'aggressive';

-- Watchlist row: leave quantity and avg_buy_price_dkk null
insert into portfolio_holdings (profile_id, ticker, name, quantity, avg_buy_price_dkk, kind)
select id, 'CARLB.CO', 'Carlsberg B', null, null, 'watchlist'
from profiles where slug = 'aggressive';
```

The next scheduled run picks the new profile up automatically (it iterates active profiles).

---

## 8. Sanity checklist

- [ ] Supabase migrations applied; seed inserted; `select count(*) from profiles` returns `1`.
- [ ] `frontend/lib/database.types.ts` regenerated and committed.
- [ ] Vercel deploy is green; the dashboard lists the seeded holdings.
- [ ] Discord default webhook receives a test message from a manual routine run.
- [ ] Scheduled agent registered with the cron above and visible in `schedule` skill listings.
- [ ] First scheduled run lands a row in `analysis_runs` with `status = 'success'`.
