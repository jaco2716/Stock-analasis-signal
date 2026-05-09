# Runbook

Operational playbook for the stock-analysis-signal system. If something is broken or needs to change, start here.

## Quick triage: did the last run succeed?

```sql
select id, started_at, completed_at, status, profile_count, signal_count, error_message
  from analysis_runs
 order by started_at desc
 limit 10;
```

- `status = 'success'` and a recent `completed_at` -> system healthy.
- `status = 'running'` but `started_at` is more than ~10 minutes ago -> the agent crashed mid-run. Treat as failed.
- `status = 'partial'` -> read `error_message`; some profiles produced no signals. Cross-check against `signals` for the run id below.
- `status = 'failed'` -> `error_message` has the reason. The most common cause is a missing env var on the agent or a Supabase outage.

To see the signals from a specific run:

```sql
select profile_id, ticker, signal_type, confidence, generated_at
  from signals
 where run_id = '<run-id>'
 order by ticker;
```

## Manual rerun

When the scheduled run failed and you want to re-execute on demand:

### Triggering the scheduled agent on demand (preferred)

From a Claude Code session in this project, call the `schedule` skill and ask it to run the registered routine immediately. The full chain runs end-to-end: `prepare` → per-holding `emit-signal` → `finish-run`. This is the only way to reproduce the actual analysis the agent performs.

### From your laptop (data plumbing only)

You cannot reproduce the agent's judgment locally — the analysis happens inside the scheduled-agent session. But you can smoke-test the data plumbing:

```bash
cd routine
source .venv/bin/activate
# .env needs SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DEFAULT_DISCORD_WEBHOOK_URL.

# Gather data; writes /tmp/stock-analysis-brief.json. --dry-run skips the analysis_runs insert.
python -m run_analysis prepare --dry-run --verbose
cat /tmp/stock-analysis-brief.json | jq '.profiles[0].holdings[0]'

# Commit a manual signal (e.g. to test webhook routing) without a real DB write:
python -m run_analysis emit-signal \
  --run-id 00000000-0000-0000-0000-000000000000 \
  --profile-id <id-from-brief> --ticker NOVO-B.CO \
  --signal HOLD --confidence 0.5 --reasoning "manual webhook smoke" \
  --dry-run --verbose
```

To actually re-run analysis, trigger the scheduled agent (above).

## Discord webhooks

### Rotating a webhook

If a webhook is leaked or you want to move signals to a different channel:

1. Discord -> channel -> **Edit Channel** -> **Integrations** -> **Webhooks** -> delete the compromised webhook (this immediately stops it from posting).
2. Create a new webhook in the new channel; copy the URL.
3. Update where it lives:
   - **Default** webhook: change `DEFAULT_DISCORD_WEBHOOK_URL` in (a) the Anthropic scheduled-agent secrets, (b) `routine/.env` for local dev. There is no Vercel-side copy; the frontend doesn't post to Discord.
   - **Per-profile** webhook:
     ```sql
     update profiles set discord_webhook_url = '<new-url>' where slug = '<slug>';
     -- Or to drop back to the default:
     update profiles set discord_webhook_url = null where slug = '<slug>';
     ```
4. Trigger a manual rerun to confirm it posts to the new place.

### "Webhook is invalid" or 404 from Discord

The webhook was deleted on the Discord side. Recreate (steps above). The routine will mark the run `partial` (signals saved, post failed) rather than `failed`.

## Supabase

### Project paused after 7 days idle

Free-tier Supabase projects pause after a week without traffic. Symptoms: every routine run fails on the first DB call with a connection error; the dashboard returns 503.

To unpause:

1. <https://supabase.com/dashboard> -> open the project.
2. Click **Restore project** (the banner at the top). It takes ~1 minute.
3. Trigger a manual rerun to confirm.

To prevent future pauses, either:

- Upgrade the project to a paid plan (no auto-pause), or
- Add a tiny keepalive: a daily cron (e.g. via the existing scheduled agent or a GitHub Action) that runs `select 1`. The three weekday runs already keep it warm Mon-Fri; only weekends + holidays risk pausing. A Saturday `select 1` is enough.

### Re-applying migrations after a wipe

If you ever need to reset:

```bash
supabase db reset --linked        # destructive; drops everything
supabase db push                  # reapplies db/migrations/*
supabase db execute --file db/seed.sql
cd frontend && supabase gen types typescript --linked > lib/database.types.ts
```

## Swapping the LLM model

There is no model id in the codebase. Analysis runs inside the scheduled-agent's own Claude session, so the model is whatever the scheduled-agent runtime is currently set to. Change it in the `schedule` skill (or whatever the platform exposes for the agent's model setting), not in the repo.

To tune **how** the model analyzes (methodology, decision rules, confidence calibration, indicator interpretation), edit `routine/agent_prompt.md`. Re-register the schedule with the updated prompt. Trigger a manual run and compare a few signals' reasoning before relying on it in cron.

To extend **what data** the model sees, add fields to the brief in `routine/lib/brief.py` and update the indicator-interpretation section of `agent_prompt.md` to reference them. No other file should need to change.

## Adding / removing tickers

Pure SQL; no code or redeploy needed.

```sql
-- Add an owned holding to the default profile
insert into portfolio_holdings (profile_id, ticker, name, position_dkk, kind)
select id, 'ORSTED.CO', 'Orsted', 30000.00, 'owned'
from profiles where slug = 'default';

-- Promote watchlist -> owned (delete the watchlist row, add owned)
delete from portfolio_holdings
 where ticker = 'MAERSK-B.CO' and kind = 'watchlist';
insert into portfolio_holdings (profile_id, ticker, name, position_dkk, kind)
select id, 'MAERSK-B.CO', 'A.P. Moller - Maersk B', 25000.00, 'owned'
from profiles where slug = 'default';

-- Remove
delete from portfolio_holdings where ticker = 'XYZ.CO' and profile_id = '<id>';
```

## Common errors and where to look

| Symptom | First place to check |
|---|---|
| No Discord post but signals in DB | Routine logs from the agent; webhook URL validity |
| Discord post but no signals in DB | Race / partial run; `analysis_runs.status = 'partial'` and `error_message` |
| Frontend shows blank dashboard | Vercel build logs; Supabase **Logs -> API** for 401/403 (check anon key + RLS) |
| Frontend write action 500s | Vercel function logs; service_role key correct; RLS not blocking (writes should bypass RLS) |
| Routine errors `auth.users does not exist` | A future-migration RLS policy was applied prematurely; revert and re-run |
| Same ticker generates two signals same run | Duplicate row in `portfolio_holdings`; check the `(profile_id, ticker, kind)` unique constraint hasn't been bypassed |

## Escalation paths

- Anthropic / Claude Code outage -> <https://status.anthropic.com>. The scheduled agent fails to fire; nothing in `analysis_runs`. Resumes automatically once the platform recovers.
- Supabase outage -> <https://status.supabase.com>. `prepare` errors out before inserting the run row; agent should `finish-run --status failed` if a run row exists, otherwise log and exit.
- Vercel outage -> <https://www.vercel-status.com>. Frontend down; routine unaffected.
