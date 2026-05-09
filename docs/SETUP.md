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
- An Anthropic API key (console.anthropic.com -> API Keys).
- A Discord server where you can create webhooks.

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
# Apply each migration in order:
supabase db push
# Or, if you prefer manual control, paste each file from db/migrations/
# into the Supabase SQL editor in order: 0001 -> 0002 -> 0003.
```

### 1.4 Seed the default profile

```bash
supabase db execute --file db/seed.sql
# Or paste db/seed.sql into the SQL editor.
```

Verify in **Table Editor**: `profiles` should have one row (`Default` / `default`), `portfolio_holdings` should have NOVO-B.CO (owned) and MAERSK-B.CO (watchlist).

### 1.5 Generate the TypeScript types

The frontend imports `Database` from `frontend/lib/database.types.ts`. Regenerate it after every migration:

```bash
cd frontend
supabase gen types typescript --linked > lib/database.types.ts
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

## 3. Anthropic API key

1. <https://console.anthropic.com> -> **API Keys** -> **Create Key**. Name it `stock-analysis-signal-routine`.
2. Save as `ANTHROPIC_API_KEY`. The routine uses it; the scheduled-agent harness uses its own credentials separately.

---

## 4. GitHub repo

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

## 5. Vercel deployment (frontend)

### 5.1 Import the project

1. <https://vercel.com/new> -> **Import** the GitHub repo.
2. **Root Directory**: `frontend`.
3. **Framework Preset**: Next.js (auto-detected).
4. **Build Command**: leave default (`next build`).

### 5.2 Environment variables

In **Settings -> Environment Variables** add (Production + Preview + Development):

| Name | Value | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | from 1.2 | exposed to browser |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | from 1.2 | exposed to browser |
| `SUPABASE_SERVICE_ROLE_KEY` | from 1.2 | **server-only** - leave the "Available in browser" box unchecked |

Click **Deploy**.

### 5.3 Verify

Open the deployed URL. The dashboard should render the seeded `Default` profile with NOVO-B.CO and MAERSK-B.CO. If you see a blank state, check the Vercel build logs and the Supabase logs (Project -> Logs -> API).

---

## 6. Scheduled agent (the routine)

The routine runs as an Anthropic-managed scheduled agent. The agent is stateless: every fire-time it clones the repo, installs deps, runs the script, and exits. Schedule it via Claude Code's `schedule` skill from this project.

### 6.1 Required environment for the agent

Configure these as agent-level secrets when the `schedule` skill prompts for them:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `DEFAULT_DISCORD_WEBHOOK_URL`
- `ANTHROPIC_API_KEY`
- `GIT_REPO_URL` (the form the clone command will use; embed a token if private)

### 6.2 Register the schedule

From a Claude Code session in this project, invoke the `schedule` skill and provide:

- **Cron**: `30 9,13,16 * * 1-5`
- **Timezone**: `Europe/Copenhagen` (DST is honored automatically; the cron is wall-clock local)
- **Prompt** (the agent runs this each tick):

```
You are a scheduled runner. Execute the routine, do not modify the repo.

git clone "$GIT_REPO_URL" repo
cd repo/routine
python3.12 -m venv .venv && source .venv/bin/activate
pip install --quiet -r requirements.txt
python -m run_analysis

Exit non-zero on any failure so the harness records it.
```

This produces three runs per weekday: 09:30, 13:30, 16:30 local time.

### 6.3 First manual run

From the `schedule` skill, trigger the routine once on demand to confirm the wiring. Then check:

- `analysis_runs` has a new row with `status = 'success'`.
- `signals` has rows for each holding (or for everything in the watchlist + owned set).
- The Discord channel received an embed.

---

## 7. Local development

### 7.1 Frontend

```bash
cd frontend
cp .env.example .env.local
# Fill in NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY,
# SUPABASE_SERVICE_ROLE_KEY (same values as Vercel).
pnpm install
pnpm dev
# http://localhost:3000
```

### 7.2 Routine

```bash
cd routine
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
# DEFAULT_DISCORD_WEBHOOK_URL, ANTHROPIC_API_KEY.

# One-shot run against your real Supabase + Discord:
python -m run_analysis

# Dry run (no DB writes, no Discord post) - prints what it would do:
python -m run_analysis --dry-run
```

---

## 8. Adding a new profile (operational recipe)

```sql
-- 1. Insert the profile (optionally with its own webhook)
insert into profiles (name, slug, discord_webhook_url, is_active)
values ('Aggressive', 'aggressive', 'https://discord.com/api/webhooks/...', true);

-- 2. Add holdings
insert into portfolio_holdings (profile_id, ticker, name, position_dkk, kind)
select id, 'ORSTED.CO', 'Orsted', 25000.00, 'owned'
from profiles where slug = 'aggressive';
```

The next scheduled run picks the new profile up automatically (it iterates active profiles).

---

## 9. Sanity checklist

- [ ] Supabase migrations applied; seed inserted; `select count(*) from profiles` returns `1`.
- [ ] `frontend/lib/database.types.ts` regenerated and committed.
- [ ] Vercel deploy is green; the dashboard lists the seeded holdings.
- [ ] Discord default webhook receives a test message from a manual routine run.
- [ ] Scheduled agent registered with the cron above and visible in `schedule` skill listings.
- [ ] First scheduled run lands a row in `analysis_runs` with `status = 'success'`.
