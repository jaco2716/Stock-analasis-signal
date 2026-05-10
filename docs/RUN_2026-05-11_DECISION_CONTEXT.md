# Decision Context — Run 2026-05-11

Run ID `0be7fa1b-0a32-4427-a06c-a3e6ca7a51c4`. Profile: Default. 5 holdings (4 owned USD, 1 watchlist DKK). Sister doc to `RUN_2026-05-10_DECISION_CONTEXT.md`. Compares the brief that was actually delivered to the agent in this run against the gaps that document called out, then enumerates what's *still* missing.

Portfolio totals (per profile, from the brief): `USD` → cost_basis $5,920 / value $5,978.03 / 4 holdings. `DKK` → cost_basis 0 / value 0 / 1 holding (watchlist only). FX rate snapshot: `DKK_USD = 0.15743`.

## How the context delivered to the agent changed vs. 2026-05-10

The previous doc enumerated 17 gaps across three tiers. Walking the list against this run's brief:

| # | Gap from 2026-05-10 doc | State in this run |
|---|---|---|
| Tier 1 | | |
| 1 | SMA200 populated | ✅ Present for every holding (`sma_200`: MAERSK 13,999.76 / NFLX 103.34 / ADBE 311.36 / TSM 308.51 / MSTR 223.46). `golden_cross` / `death_cross` flags now actually fire (MAERSK & TSM golden, NFLX/ADBE/MSTR death). |
| 2 | 52w high/low + distance | ✅ `high_52w`, `low_52w`, `pct_below_52w_high`, `pct_above_52w_low` on every holding. |
| 3 | ATR(14) + volatility regime | ✅ `atr_14` + `atr_pct_of_price` on every holding (MSTR flagged at 5.24% — clearly highest-vol of the basket, vs ADBE 3.64%, MAERSK 3.61%, TSM 3.43%, NFLX 2.94%). |
| 4 | Volume context | ✅ `volume_last`, `volume_20d_avg`, `volume_vs_avg_x`. TSM 1.27× confirmed conviction; ADBE 0.68× caveated the BUY. |
| 5 | Days since latest earnings | ✅ `last_earnings_date`, `days_since_earnings`, `next_earnings_date`, `days_until_earnings` all populated. |
| 6 | Prior-run signal history | ✅ `signal_history` (last 3) on every holding. Surfaced the NFLX whipsaw (SELL → HOLD → HOLD) and the ADBE BUY-HOLD-BUY pattern. |
| Tier 2 | | |
| 7 | Real-time / pre-market price | ⚠️ Partially. `intraday_price`, `intraday_change_pct`, `market_state` populated; `pre_market_price` / `pre_market_change_pct` were null for every holding (market state `CLOSED` or `PREPRE`). The block is wired — it just had nothing to show this run. |
| 8 | Forward calendar | ✅ Captured via `days_until_earnings`. (No ex-div / corporate-action fields yet.) |
| 9 | Sector / index relative strength | ✅ `baseline_index`, `baseline_pct_change_30d`, `relative_strength_30d_pct`. MAERSK −20.7% vs ^OMXC25, NFLX −20.5% vs ^GSPC, TSM +12% vs ^GSPC, MSTR +26.9% vs ^GSPC, ADBE −9.2% vs ^GSPC. |
| 10 | News sentiment scoring | ❌ Still not in the brief — the agent skims WebSearch snippets directly. |
| 11 | Analyst consensus + revisions | ✅ `analyst_target_mean`, `_distance_pct`, `_high`, `_low`, `_recommendation_key`, `_count`. (No revision-history field yet.) |
| Tier 3 | | |
| 12 | Fundamentals snapshot | ✅ Full block: trailing/forward PE, PEG, P/B, EV/EBITDA, div yield, market cap, debt/equity, profit margin, ROE, FCF yield. Drove the ADBE BUY (PE 14.7, FCF yield 9.1%) and qualified the MSTR HOLD (FCF yield −13.2%). |
| 13 | Insider transactions (last 90d) | ⚠️ Schema in place (`insider.net_dollars_90d`, `buy_count_90d`, `sell_count_90d`, `net_share_pct`) but **null for every holding** in this run — yfinance didn't return data for any of these tickers. The NFLX exec sales (Peters $2.4M, Neumann $823k) came from WebSearch, not from this field. |
| 14 | Options-implied earnings move | ⚠️ Schema in place (`earnings_implied_move.implied_move_pct`, expiration, atm_call_iv, atm_put_iv) but **null** because no holding had earnings within 14 days (closest: ADBE 32d out). Will only matter on a run where someone is pre-earnings. |
| 15 | Position-as-% of profile | ✅ `position_weight_pct` per holding (NFLX 21.3%, ADBE 24.3%, TSM 22.4%, **MSTR 32.0%** — flagged as concentrated). Directly drove confidence-tempering on ADBE BUY and the "don't add" call on MSTR/TSM. |
| 16 | Cross-run signal P&L scoring | ❌ The schema mentions `signal_history[].outcome_t5_pct` / `outcome_t30_pct` (agent prompt §"Signal outcomes") but the brief's `signal_history` entries only contain `generated_at`, `signal_type`, `confidence` — no outcomes. Calibration loop still open. |
| 17 | FX rates snapshot | ✅ `fx_rates: {"DKK_USD": 0.15743}` at profile level. `portfolio_totals` bucketed per currency. |
| Non-context | | |
| — | News snippet caching | ❌ Still re-searches every run. |
| — | `recent_closes` lookback | Still 10 closes (unchanged). |
| — | Brief size budget | Brief is now ~6 KB per holding (the budget mentioned in the prior doc). No trimming applied yet. |

**Net**: Tier 1 fully implemented. Tier 2 ~80% (sentiment scoring missing, real-time block conditionally null). Tier 3 ~50% (fundamentals/weights/FX in; insider effectively unusable; outcomes still absent).

## Per-holding context delivered this run

For each ticker the agent reasoned on (1) the brief from `prepare`, (2) one WebSearch query for last-14-day news.

### 1. MAERSK-B.CO — Watchlist → HOLD (0.70)

**Brief (DKK):**
- Price 14,130; intraday +1.33% (`market_state=PREPRE`); pre-market null
- 30d change **−13.7%**; RSI(14) **35.0**; ATR 510 (3.61% of price)
- MACD **−337.8** vs signal **−277.5** (hist **−60.3**, bearish)
- SMA20 15,070.75 / **SMA50 15,778.70 / SMA200 13,999.76** → **golden cross intact** but price below all SMAs
- 52w: **−22.89% below high** / +34.44% above low; volume 0.988× avg
- Last earnings 2026-05-07 (**3 days ago**); next 2026-08-13 (95d)
- Analyst target **13,053 DKK (−7.62%)**, key `underperform`, 18 analysts
- Baseline ^OMXC25 30d +6.96% → **RS −20.66%** (sharp laggard)
- Fundamentals: trailing PE 20.5, fwd PE −57.4 (negative forward estimate), PEG 0.38, P/B 0.60, EV/EBITDA 39.5, debt/equity 31.7, margin 3.0%, ROE 3.2%, FCF yield 1.3%
- Insider: all-null; implied-move block: all-null; `position_weight_pct=null` (watchlist)
- Prior signals: HOLD 0.70 / HOLD 0.70 / HOLD 0.65

**News (last ~14d):**
- May 7 Q1 print: EBIT $340M, underlying EBITDA $1.75B (**−35% YoY, in-line**), full-year EBITDA-growth guide held at 4.5–7%. Stock **−7.5% post-print**.
- CEO Vincent Clerc (CNBC): Iran-war oil costs running **~$500M/month**, larger impact still ahead.
- Volumes positive: Ocean +9.3%, Logistics +8.7%, Terminals +4.3%.

### 2. NFLX — Owned → HOLD (0.60)

**Brief (USD):**
- 15 sh @ $84 avg → current $87.49; cost basis $1,260 → value $1,312.35; **P&L +$52.35 (+4.15%)**; **position weight 21.28%**
- 30d −6.25%; RSI **33.9** (near oversold); ATR 2.57 (2.94% of price); intraday −0.91% (`CLOSED`)
- MACD **−2.15** vs signal **−1.23** (hist −0.92, bearish); **death cross active** (SMA50 95.54 < SMA200 103.34); price below all SMAs
- 52w: **−34.76% below high**; volume 0.83× avg
- Last earnings 2026-04-16 (24d ago); next 2026-07-16 (67d)
- Analyst target **$114.56 (+30.93%)**, key `buy`, 44 analysts (target_high $151.4, target_low $80.0 — split bands)
- Baseline ^GSPC 30d +14.23% → **RS −20.48%**
- Fundamentals: trailing PE 28.2, fwd 22.8, PEG 1.28, EV/EBITDA 26.1, margin 28.5%, ROE 48.5%, FCF yield 7.06%
- Insider: all-null in brief
- Prior signals: HOLD 0.65 / HOLD 0.65 / SELL 0.60 (recent whipsaw)

**News (last ~14d):**
- −5.7% after cautious Q2 guidance + **$25B share buyback**.
- Insider selling **from WebSearch only**: Co-CEO Peters 27,312 sh (~$2.42M); CFO Neumann 9,253 sh (~$823k).
- Mobile-app "Clips" vertical-video redesign in development.
- DCF intrinsic ~$90 → roughly at fair value.

### 3. ADBE — Owned → BUY (0.65) ← only Discord-posted action this run

**Brief (USD):**
- 6 sh @ $240 → current $253.04; cost basis $1,440 → value $1,518.24; **P&L +$78.24 (+5.43%)**; **position weight 24.32%**
- 30d **+5.05%**; RSI **53.7**; ATR 9.21 (3.64% of price); intraday −1.35% (`CLOSED`)
- MACD **+1.60** vs signal **−0.02** (hist **+1.62, bullish crossover**); price reclaimed SMA20 (247.07) and SMA50 (250.36); SMA200 311.36 → **death cross still in place** (regime bear, action recovering)
- 52w: **−40.17% below high** (deep value zone); volume **0.68× avg** (low — caveat)
- Last earnings 2026-03-12 (59d); next **2026-06-11 (32d)** — just outside 30d gate
- Analyst target **$327.96 (+29.61%)**, key `buy`, 34 analysts
- Baseline ^GSPC → **RS −9.18%**
- Fundamentals (cleanest in basket): trailing PE **14.7**, fwd PE **9.6**, PEG **0.72**, P/B 8.99, EV/EBITDA 10.7, margin 29.5%, ROE 58.8%, **FCF yield 9.11%**
- Insider: all-null
- Prior signals: BUY 0.65 / HOLD 0.60 / BUY 0.70 (thesis consistent)

**News (last ~14d):**
- Late April: **$25B share-repurchase authorization**, new Acrobat productivity AI agent + PDF Spaces, Semrush acquisition, Alluvium healthcare partnership.
- YTD −26.7%.
- Counter-narrative ("Adobe = next Nokia"): gen-AI competitive risk to mass-market moat.

### 4. TSM — Owned → HOLD (0.75)

**Brief (USD):**
- 4 sh @ $331 → current $411.68; cost basis $1,324 → value $1,646.72; **P&L +$322.72 (+24.37%)** — **just under +25% trim threshold**; position weight 22.36%
- 30d **+26.24%**; RSI **64.0** (rising, not yet >70); ATR 14.11 (3.43% of price); intraday −0.60% (`CLOSED`)
- MACD **+14.51** vs signal **+12.98** (hist +1.54, bullish); price above all SMAs; **golden cross intact** (SMA50 363.04 > SMA200 308.51)
- 52w: **−1.98% below high** (right at the highs); volume **1.27× avg** (high-conviction tape)
- Last earnings 2026-04-16 (24d); next 2026-07-16 (67d)
- Analyst target **$463.45 (+12.58%)**, key `strong_buy`, 18 analysts
- Baseline ^GSPC → **RS +12.01%** (true alpha)
- Fundamentals: trailing PE 35.2, fwd 21.3, PEG 1.31, EV/EBITDA 2.9, margin **46.5%**, ROE 36.2%, FCF yield **33.79%**
- Prior signals: HOLD 0.70 / HOLD 0.80 / HOLD 0.65

**News (last ~14d):**
- Q1 EPS **+58.3% YoY**, net margin 50.5%.
- Q2 guide: revenue **$39–40.2B**, op margin 56.5–58.5%.
- Full-year 2026 target: **+30% revenue growth**; multi-year EPS CAGR consensus ~33%.
- YTD +30%; AI / HPC demand the through-line.

### 5. MSTR — Owned → HOLD (0.55)

**Brief (USD):**
- 8 sh @ $237 → current $187.59; cost basis $1,896 → value $1,500.72; **P&L −$395.28 (−20.85%)** — **past the −15% cut-loss threshold**; position weight **32.03%** (most concentrated holding)
- 30d **+41.12%**; RSI **66.3**; ATR 9.83 (**5.24% of price** — highest in basket); intraday **+4.31%** (`CLOSED`)
- MACD **+11.77** vs signal **+10.38** (hist +1.39, bullish); price above SMA20 (167.35) & SMA50 (147.41) but below SMA200 (223.46) → **death cross active**, long-term regime still bear
- 52w: **−58.97% below high** / +80.08% above low
- Last earnings 2026-05-05 (5d); next 2026-07-30 (81d)
- Analyst target **$380.43 (+102.80%)**, key `strong_buy`, 14 analysts (target_high $645, target_low $212 — heavy split)
- Baseline ^GSPC → **RS +26.89%**
- Fundamentals damaged: trailing PE null, fwd PE 5.16, PEG 2.85, P/B 1.33, EV/EBITDA **−5.8**, ROE −30.8%, **FCF yield −13.23%**, debt/equity 18.1
- Prior signals: HOLD 0.60 / HOLD 0.55 / HOLD 0.55

**News (last ~14d):**
- May 5 Q1: GAAP loss **$12.54B / −$38.25 EPS** driven by **$14.46B unrealized BTC mark-to-market loss**. Revenue $124.3M ~in-line.
- **Strategic pivot**: ending pure-stockpile model — willing to sell BTC to fund dividends or buy back debt if accretive to BTC-per-share (Saylor / Phong Le).
- Holds 818,334 BTC at avg $75,500; added 89,600 BTC in Q1 (~$5.5B).
- Q1 capital raises: ATM $7.37B + STRC preferred $2.07B (STRC now $8.5B, largest preferred-stock issuance in the world).

## Rules applied (per `routine/agent_prompt.md`)

- **Watchlist default = HOLD**, BUY only on clear entry trigger.
  - MAERSK RSI 35 wasn't oversold enough, MACD still bearish, RS −20.7%, Iran-war catalyst negative-asymmetric → HOLD.
- **Owned default = HOLD**, overrides:
  - **SELL (lock gain)** when `pnl_pct > +25% AND technicals weakening` → TSM at +24.4% but **technicals strengthening** (RSI rising not rolling, MACD widening, GC intact, fresh-near-high tape, volume 1.27×, RS +12%) → no SELL.
  - **SELL (cut loss)** when `pnl_pct < −15% AND trend continues bearish` → MSTR at −20.85% but **30d +41%** with bullish MACD and intraday +4.3% → trend is *not* continuing bearish → no SELL. Bear regime still flagged by death cross / −59% below 52w high, so no BUY either; HOLD at low confidence (0.55) reflects genuine two-sided uncertainty.
  - **BUY (add)** when bullish technicals + supportive news + smallish position → ADBE: fresh MACD bullish crossover, RSI 53 leaning up, price reclaimed SMA20/50, cheapest fundamentals in the basket, $25B buyback + AI product launches. Confidence held at 0.65 (not higher) because position is **already 24.3% of USD book** and earnings is **32 days out** (just clearing the 30d gate, but the prompt asks to size down at 7–14d; nothing for 30–35d, so I caveated rather than dropped a band).
  - NFLX P&L +4.15% inside the ±10% noise band with mixed indicators (oversold RSI vs death-cross + bearish MACD + insider sells) → HOLD.

## What's still missing — recommended next round of brief improvements

In rough order of "highest signal value, lowest implementation cost":

### Tier A — close out promises the schema already made

1. **`signal_history[].outcome_t5_pct` and `outcome_t30_pct`.** The agent prompt explicitly describes these and tells the agent to calibrate against them, but the brief delivers `signal_history` entries with only timestamp/type/confidence. Two ways to close it:
   - Backfill job: nightly, scan signals where `T+5`/`T+30` close exists; compute and store the realized return; join into the brief on `prepare`.
   - Compute on the fly during `prepare` from the same yfinance prices it already has.
2. **Insider data fallback.** Across all 5 holdings yfinance returned null for `insider.*`. yfinance's Yahoo-scraped insider feed is notoriously thin for non-US listings and uneven for US ones (it failed even on NFLX/ADBE/TSM/MSTR — all NYSE/NASDAQ). The NFLX exec sells were *in the public news feed*; we only missed them in the brief. Options: SEC EDGAR Form 4 ingestion (free, US-only); Finnhub `/stock/insider-transactions` (free tier, US + many intl).
3. **Pre-market freshness gate.** This run had `market_state=PREPRE` (MAERSK) and `CLOSED` (US tickers). The pre-market block was null for everything. Worth verifying the path: when `market_state` is `PRE`/`POST` the block should populate; if it never does, the wiring may be ignoring `bid`/`ask` deltas.

### Tier B — high judgement value, modest implementation cost

4. **Analyst-target *revisions* (last 14d).** Current consensus level is in the brief; what's missing is *direction*: upgrades, downgrades, target-bumps. A "Barclays raised to $470" two days ago is a different signal from "Barclays at $470 for six months." Finnhub `/stock/upgrade-downgrade` exposes this.
5. **News sentiment + catalyst-type tagging.** Right now the agent has to read snippets and judge tone. A small LLM pass over the WebSearch hits per ticker that returns `{sentiment: -1..+1, catalyst_type: earnings|regulatory|M&A|guidance|macro}` would (a) make reasoning more comparable across tickers, (b) make `confidence` calibration more reproducible.
6. **Pre-/post-news anchoring.** When the brief says "intraday +4.31% on MSTR", the agent doesn't currently know *why*. Joining the news catalyst date to the price move ("MSTR +4.3% intraday, 5 days after Q1 print + bitcoin strategy pivot") would let the agent attribute the move rather than just cite it.
7. **Forward calendar beyond earnings.** Ex-div dates, dividend declarations, scheduled investor days, FDA / regulatory PDUFA dates. Often known well in advance; cheap to ingest from Finnhub `/calendar/earnings|ipo|economic`.
8. **Sector ETF benchmark** in addition to broad index. Tracking TSM vs SMH (or ADBE vs IGV) would discriminate "sector strength carrying it" from "company-specific alpha." Currently the brief gives ^GSPC only for US tickers.

### Tier C — situationally valuable, bigger lift

9. **Options-flow / unusual-activity feed.** `earnings_implied_move` only populates ≤14d before earnings. For the 90% of runs that are *not* pre-earnings, options markets still carry information (large call sweeps, put/call skew shifts). Not free.
10. **Cross-run agreement metric.** "Last 3 signals from this routine matched the realized 5d direction." Lets the agent (and the user) see whether the model is calibrated, miscalibrated bullish, or miscalibrated bearish, *per ticker*. Builds on Tier A #1.
11. **News snippet cache (still open).** Same WebSearch query for the same ticker, same day, multiple runs → wasted external calls. A `(ticker, day, query_hash) → results` table keyed on Supabase would dedupe.
12. **Per-currency portfolio commentary in the Discord summary.** `portfolio_totals` and `fx_rates` are now in the brief; the next iteration could surface "USD book +1.0% on $5,920 cost basis" in the HOLD-summary message so the user sees portfolio drift, not just per-ticker calls. Pure surfacing change; data is already there.
13. **Decision-rule unit tests on synthetic briefs.** The decision matrix is now complex (P&L bands × trend × news × position-weight × earnings-window). A few golden synthetic briefs run on every prompt change would catch regressions in interpretation. (Not a *brief* improvement — a routine improvement.)

### Non-context follow-ups (carried over from 2026-05-10 doc, still relevant)

- `recent_closes` is still last-10 only — either drop (agent doesn't reason over it) or extend to 30 if we want the agent to do its own mini-trend read.
- No explicit brief-size budget enforced; ~6 KB/holding is fine for 5 holdings but will scale with `position_weight_pct` computation and any added blocks.

## Sources cited during this run

- [Maersk Q1 2026 release — Maersk Newsroom](https://www.maersk.com/news/articles/2026/05/07/maersk-delivered-volume-growth-across-all-businesses-in-q1)
- [Maersk CEO warns on Iran war impact — CNBC](https://www.cnbc.com/2026/05/07/maersk-ceo-warns-iran-war-will-have-bigger-impact-in-coming-months.html)
- [Netflix streaming-stock positioning + buyback — Yahoo Finance](https://finance.yahoo.com/markets/stocks/articles/streaming-stock-looks-positioned-next-190010722.html)
- [Netflix insider sales (Peters/Neumann) — TipRanks](https://www.tipranks.com/news/insider-trading/top-netflix-executives-make-major-move-with-their-stock-holdings-insider-trading-news)
- [Adobe $25B buyback + AI productivity agent — Yahoo Finance](https://finance.yahoo.com/markets/stocks/articles/adobes-adbe-us-25-billion-070936407.html)
- [TSMC 2026 Q1 quarterly results — TSMC IR](https://investor.tsmc.com/english/quarterly-results/2026/q1)
- [Strategy ditches "never sell" BTC approach — CNBC](https://www.cnbc.com/2026/05/05/strategy-breaks-from-never-sell-bitcoin-approach.html)
- [Strategy may sell BTC to fund dividends — CoinDesk](https://www.coindesk.com/business/2026/05/05/michael-saylor-s-strategy-signals-potential-bitcoin-sale-to-fund-dividends-obligations)
