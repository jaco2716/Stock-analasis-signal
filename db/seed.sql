-- seed.sql
-- Minimal seed for local dev and first deploy.
-- One default profile, one owned holding, one watchlist entry.

insert into profiles (name, slug, is_active)
values ('Default', 'default', true)
on conflict (slug) do nothing;

insert into portfolio_holdings (profile_id, ticker, name, position_dkk, kind)
select p.id, 'NOVO-B.CO', 'Novo Nordisk B', 50000.00, 'owned'
from profiles p
where p.slug = 'default'
on conflict (profile_id, ticker, kind) do nothing;

insert into portfolio_holdings (profile_id, ticker, name, position_dkk, kind)
select p.id, 'MAERSK-B.CO', 'A.P. Moller - Maersk B', null, 'watchlist'
from profiles p
where p.slug = 'default'
on conflict (profile_id, ticker, kind) do nothing;
