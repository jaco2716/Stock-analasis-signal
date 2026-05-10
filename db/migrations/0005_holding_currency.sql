-- 0005_holding_currency.sql
-- Make portfolio_holdings currency-aware. Previously avg_buy_price_dkk hard-coded
-- DKK, but yfinance returns prices in the security's native currency (USD for US
-- listings, EUR/SEK/etc. for European). Comparing DKK cost basis to USD current
-- price was producing P&L numbers off by the FX rate.
--
-- Fix: each holding stores its own ISO currency code. P&L is computed in that
-- currency. Existing rows default to 'DKK' (the implicit assumption today).

alter table portfolio_holdings
  add column currency text not null default 'DKK'
  check (currency ~ '^[A-Z]{3}$');

alter table portfolio_holdings
  rename column avg_buy_price_dkk to avg_buy_price;
