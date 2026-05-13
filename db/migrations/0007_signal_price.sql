-- 0007_signal_price.sql
-- Persist the entry price + currency on each signal so backtests and the UI
-- can compare against the live quote without re-fetching market data. Until
-- now the price was only present in the transient brief; once the brief was
-- thrown away the signal row had no anchor for outcome / P&L math.
--
-- Currency is stored on the signal itself (not joined from portfolio_holdings)
-- so historical signals stay stable even if a watchlist row is deleted or
-- its currency changes later.

alter table signals
  add column if not exists price_at_signal numeric(18, 6),
  add column if not exists currency        text;

-- Partial index keeps the one-shot backfill scan cheap; rows graduate out of
-- the index once price_at_signal is populated.
create index if not exists idx_signals_price_missing
  on signals (generated_at)
  where price_at_signal is null;
