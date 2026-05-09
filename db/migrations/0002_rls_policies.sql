-- 0002_rls_policies.sql
-- Row-Level Security policies.
--
-- Current model: single-user / shared-read.
--   - All four tables have RLS enabled.
--   - Anonymous (anon) role gets a permissive SELECT policy: read-only public access.
--   - Writes go through the service_role key from the routine and from Next.js
--     Server Actions. service_role bypasses RLS entirely; we never expose it
--     to the browser.
--
-- =============================================================================
-- FUTURE MULTI-USER MIGRATION (do not apply now; reference only)
-- =============================================================================
-- When migrating from single-shared-account to per-user accounts:
--
--   1. Add the owner column to profiles:
--        alter table profiles add column user_id uuid references auth.users(id);
--        update profiles set user_id = '<existing-user-uuid>';
--        alter table profiles alter column user_id set not null;
--
--   2. Replace the permissive anon SELECT policy on profiles with:
--        drop policy profiles_anon_select on profiles;
--        create policy profiles_owner_all on profiles
--          for all to authenticated
--          using (auth.uid() = user_id)
--          with check (auth.uid() = user_id);
--
--   3. Tighten holdings/signals/runs by joining through profiles. Example for
--      portfolio_holdings:
--        drop policy holdings_anon_select on portfolio_holdings;
--        create policy holdings_owner_all on portfolio_holdings
--          for all to authenticated
--          using (
--            exists (
--              select 1 from profiles p
--              where p.id = portfolio_holdings.profile_id
--                and p.user_id = auth.uid()
--            )
--          );
--      Repeat for signals (via profile_id) and analysis_runs (after adding a
--      profile_id column or a run-membership table).
--
--   4. Drop the service_role-only writes from frontend Server Actions and
--      switch them to user-session-scoped supabase clients.
-- =============================================================================

alter table profiles enable row level security;
alter table portfolio_holdings enable row level security;
alter table analysis_runs enable row level security;
alter table signals enable row level security;

create policy profiles_anon_select on profiles
  for select to anon using (true);

create policy holdings_anon_select on portfolio_holdings
  for select to anon using (true);

create policy runs_anon_select on analysis_runs
  for select to anon using (true);

create policy signals_anon_select on signals
  for select to anon using (true);
