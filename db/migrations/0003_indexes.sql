-- 0003_indexes.sql
-- Indexes for hot read paths.
--   - holdings lookup by profile (dashboard list view)
--   - signals scoped to a profile, newest first (dashboard + Discord paging)
--   - runs newest first (admin status page)

create index idx_holdings_profile_id
  on portfolio_holdings (profile_id);

create index idx_signals_profile_generated
  on signals (profile_id, generated_at desc);

create index idx_runs_started
  on analysis_runs (started_at desc);
