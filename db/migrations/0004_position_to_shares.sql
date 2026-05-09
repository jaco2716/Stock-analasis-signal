-- 0004_position_to_shares.sql
-- Replace the single-number position_dkk snapshot with the canonical
-- brokerage-style decomposition: shares held + average buy price.
-- Cost basis = quantity * avg_buy_price_dkk; current value and unrealized
-- P&L are derived per run from live prices in routine/lib/brief.py.

-- The original CHECK constraint referencing position_dkk was inline and
-- thus auto-named by Postgres. Find it by definition and drop by name.
do $$
declare
  conname text;
begin
  select c.conname into conname
  from pg_constraint c
  join pg_class t on t.oid = c.conrelid
  where t.relname = 'portfolio_holdings'
    and c.contype = 'c'
    and pg_get_constraintdef(c.oid) like '%position_dkk%';
  if conname is not null then
    execute format('alter table portfolio_holdings drop constraint %I', conname);
  end if;
end $$;

alter table portfolio_holdings drop column position_dkk;

-- Fractional shares for ETFs / future-proofing; six decimals is plenty.
alter table portfolio_holdings add column quantity numeric(18, 6);

-- Per-share cost in DKK. Four decimals supports sub-DKK precision
-- (e.g. low-priced shares, fractional currency rounding).
alter table portfolio_holdings add column avg_buy_price_dkk numeric(14, 4);

alter table portfolio_holdings
  add constraint portfolio_holdings_owned_fields_check
  check (kind = 'watchlist' or (quantity is not null and avg_buy_price_dkk is not null));
