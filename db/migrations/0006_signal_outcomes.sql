-- 0006_signal_outcomes.sql
-- Realised T+5 / T+30 returns on each emitted signal, populated by the
-- `score-signals` subcommand once enough trading days have passed.

alter table signals
  add column if not exists outcome_t5_pct      numeric(8, 2),
  add column if not exists outcome_t30_pct     numeric(8, 2),
  add column if not exists outcome_computed_at timestamptz;

-- Partial index keeps the daily backfill scan cheap (tiny working set as the
-- table grows; rows graduate out of the index once both windows are scored).
create index if not exists idx_signals_outcome_pending
  on signals (generated_at)
  where outcome_t30_pct is null;
