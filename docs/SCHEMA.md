# Schema reference

Authoritative source: `db/migrations/*.sql`. This page summarizes the shape and documents the discipline for keeping the TypeScript and Python mirrors in sync.

## Tables

### `profiles`

A logical portfolio. The system supports many; the seed creates one called `Default`.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | `gen_random_uuid()` |
| `name` | `text` | Display name, e.g. `Default`, `Aggressive` |
| `slug` | `text` UNIQUE | URL- and code-safe id, e.g. `default` |
| `discord_webhook_url` | `text` nullable | If set, signals route here. If null, fall back to `DEFAULT_DISCORD_WEBHOOK_URL` and prefix the embed title with `[<name>]`. |
| `is_active` | `bool` | The routine iterates `is_active = true` only |
| `created_at` / `updated_at` | `timestamptz` | `updated_at` maintained by trigger |

### `portfolio_holdings`

Tickers attached to a profile, either owned (with a DKK position size) or a watchlist entry.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `profile_id` | `uuid` FK -> `profiles.id` | `on delete cascade` |
| `ticker` | `text` | Copenhagen-suffixed, e.g. `NOVO-B.CO` |
| `name` | `text` nullable | Human-readable |
| `position_dkk` | `numeric(14,2)` nullable | Required when `kind = 'owned'` (CHECK constraint) |
| `kind` | `holding_kind` enum | `owned` \| `watchlist` |
| `added_at` / `updated_at` | `timestamptz` | |

Unique `(profile_id, ticker, kind)` so the same ticker can appear once owned and once on the watchlist of the same profile (rare, but valid).

### `analysis_runs`

One row per routine invocation. Used for observability and debugging.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `started_at` / `completed_at` | `timestamptz` | `completed_at` null while in flight |
| `profile_count` | `int` | How many active profiles processed |
| `signal_count` | `int` | How many signals produced this run |
| `status` | `run_status` enum | `running` \| `success` \| `partial` \| `failed` |
| `error_message` | `text` nullable | Populated on `partial` / `failed` |

### `signals`

The unit of output. One row per (profile, ticker) per run.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `profile_id` | `uuid` FK -> `profiles.id` | cascade |
| `ticker` | `text` | |
| `signal_type` | `signal_type` enum | `BUY` \| `SELL` \| `HOLD` |
| `reasoning` | `text` | Model's explanation; rendered verbatim in Discord |
| `confidence` | `numeric(3,2)` | `0.00 .. 1.00`, CHECK enforced |
| `generated_at` | `timestamptz` | |
| `run_id` | `uuid` FK -> `analysis_runs.id` | `on delete set null` so old signals survive run cleanup |

## Enums

- `signal_type`: `BUY`, `SELL`, `HOLD`
- `holding_kind`: `owned`, `watchlist`
- `run_status`: `running`, `success`, `partial`, `failed`

## RLS

See `db/migrations/0002_rls_policies.sql`. Today: anon can SELECT all four tables; writes go through `service_role`. The migration file contains a SQL comment block describing the future per-user migration (add `profiles.user_id`, replace anon SELECT with `auth.uid() = user_id`, join through profile for the rest).

## Indexes

See `db/migrations/0003_indexes.sql`:

- `idx_holdings_profile_id` on `portfolio_holdings(profile_id)`
- `idx_signals_profile_generated` on `signals(profile_id, generated_at desc)`
- `idx_runs_started` on `analysis_runs(started_at desc)`

---

## Sync discipline

The schema is mirrored in two places. Both must be updated whenever a migration lands. **Treat a migration as incomplete until both mirrors are regenerated/updated and committed in the same PR.**

### TypeScript: `frontend/lib/database.types.ts`

Generated from the live linked Supabase project. Do **not** edit by hand.

```bash
cd frontend
supabase gen types typescript --linked > lib/database.types.ts
```

Then:

```bash
git diff frontend/lib/database.types.ts
git add frontend/lib/database.types.ts
```

If the diff is empty after a migration, the migration didn't actually apply to the linked project - run `supabase db push` and try again.

### Python: `routine/lib/models.py`

Hand-mirrored. Pydantic models (or `dataclasses` - whichever the routine settled on) that match the table columns, enum values, and nullability. There is no generator; review the migration and patch this file by inspection.

Checklist when a migration changes:

- New column -> add field with the right type and `Optional[...]` if nullable.
- Renamed column -> rename the field; grep the routine for old name and update.
- Removed column -> remove the field; grep for it and remove its uses.
- New enum value -> extend the corresponding `Literal[...]` / `Enum`.
- New table -> add a new model class.

### PR template clause

When opening a PR that adds a migration, the description should include:

```
- [ ] Migration file added under db/migrations/NNNN_*.sql
- [ ] frontend/lib/database.types.ts regenerated (supabase gen types typescript --linked)
- [ ] routine/lib/models.py updated by hand to match
```
