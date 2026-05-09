-- 0001_init.sql
-- Initial schema for the stock-analysis-signal system.
-- Tables: profiles, portfolio_holdings, analysis_runs, signals.

create extension if not exists "pgcrypto";

create type signal_type as enum ('BUY', 'SELL', 'HOLD');
create type holding_kind as enum ('owned', 'watchlist');
create type run_status as enum ('running', 'success', 'partial', 'failed');

create table profiles (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  discord_webhook_url text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table portfolio_holdings (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references profiles(id) on delete cascade,
  ticker text not null,
  name text,
  position_dkk numeric(14, 2),
  kind holding_kind not null,
  added_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (profile_id, ticker, kind),
  check (kind = 'watchlist' or position_dkk is not null)
);

create table analysis_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  profile_count int,
  signal_count int,
  status run_status not null default 'running',
  error_message text
);

create table signals (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references profiles(id) on delete cascade,
  ticker text not null,
  signal_type signal_type not null,
  reasoning text not null,
  confidence numeric(3, 2) check (confidence between 0 and 1),
  generated_at timestamptz not null default now(),
  run_id uuid references analysis_runs(id) on delete set null
);

-- updated_at trigger for profiles + holdings
create or replace function set_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;
create trigger trg_profiles_updated before update on profiles for each row execute function set_updated_at();
create trigger trg_holdings_updated before update on portfolio_holdings for each row execute function set_updated_at();
