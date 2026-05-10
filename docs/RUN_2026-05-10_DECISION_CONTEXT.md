# Decision Context — Run 2026-05-10

Run ID `99099efd-9821-426d-84bd-72a678ce4e29`. Profile: Default. 5 holdings. This document captures the exact context that drove each call (brief data + news), the rules applied, and the gaps in context worth filling in future iterations.

## Per-holding context

For each ticker the inputs were: (1) the brief from `prepare` (yfinance prices + computed indicators + portfolio P&L) and (2) WebSearch results.

### 1. MAERSK-B.CO — Watchlist → HOLD (0.70)

**Brief (DKK):**
- Price 14,130; 30d change **−13.7%**
- RSI(14) **35.0** (approaching oversold)
- MACD **−337.76** vs signal **−277.46** (histogram **−60.3**, bearish)
- SMA20 15,070.75 / SMA50 15,778.70 / SMA200 n/a — price below both available SMAs
- No P&L (watchlist), no quantity / cost basis
- Recent closes: 14,755 → 15,415 → 13,945 → 14,130

**News (last ~14d):**
- May 7: Q1 2026 EBIT **$340m**, revenue **$13B** (beat $12.5B); EBIT **−35% YoY** (in line with consensus); maintained 2026 EBITDA-growth guidance (4.5–7%).
- May 7: CEO Vincent Clerc warned the **U.S./Iran war** impact on shipping "will have bigger impact in coming months."
- Maersk **suspended two Middle East shipping routes** to protect crew/vessels.
- Volumes positive: Ocean +9.3%, Logistics +8.7%, Terminals +4.3%.

### 2. NFLX — Owned → HOLD (0.65)

**Brief (USD):**
- Price 87.49, **+4.15% P&L** ($52 unrealized on $1,260 cost basis), 30d change **−6.25%**
- Quantity 15, avg buy 84.00, current value $1,312.35
- RSI(14) **33.9** (oversold)
- MACD **−2.15** vs signal **−1.23** (histogram **−0.92**, bearish)
- SMA20 94.63 / SMA50 95.54 — price below both
- Recent closes: 91.37 → 93.61 → 87.49 (downtrend)

**News (last ~14d):**
- Apr 16: Q1 2026 revenue **$12.25B beat** ($12.18B est, +16% YoY).
- Q2 guidance light: revenue $12.5B (vs $12.6B exp), **EPS $0.78 vs $0.84 exp** → stock **−5.7%** post-print.
- $25B share buyback announced.
- Reed Hastings stepping down from board in June.
- On track for $3B advertising revenue (doubling YoY).
- Pending NFL deal (Australia Week 1 + Thanksgiving Eve game).

### 3. ADBE — Owned → BUY (0.65)

**Brief (USD):**
- Price 253.04, **+5.43% P&L** ($78 unrealized on $1,440 cost basis), 30d change **+5.05%**
- Quantity 6, avg buy 240.00, current value $1,518.24
- RSI(14) **53.7** (neutral)
- MACD **1.60** vs signal **−0.01** (histogram **+1.62**, **bullish crossover**)
- SMA20 247.07 / SMA50 250.36 — price **above both**
- Recent closes: 239.31 → 256.51 → 253.04 (uptrend)

**News (last ~14d):**
- Q1 FY26 revenue **$6.4B beat** ($6.3B est, +12% YoY); subscription revenue $6.2B (+13% YoY).
- **AI ARR more than tripled YoY**; Firefly subscription/credit-pack ARR **+75% QoQ**; gen-credit consumption **+45% QoQ**; video gen actions **+8x YoY**.
- April: launched **Firefly AI Assistant** (conversational interface across Photoshop / Premiere / Lightroom / Illustrator).
- Yellow flag: **CEO Shantanu Narayen stepping down** — leadership transition uncertainty.

### 4. TSM — Owned → HOLD (0.70)

**Brief (USD):**
- Price 411.68, **+24.37% P&L** ($322.72 unrealized on $1,324 cost basis — **just under the +25% trim threshold**), 30d change **+26.24%**
- Quantity 4, avg buy 331.00, current value $1,646.72
- RSI(14) **64.0** (rising, not yet overbought)
- MACD **14.51** vs signal **12.97** (histogram **+1.54**, bullish)
- SMA20 389.58 / SMA50 363.04 — price well above both
- Recent closes: 404.98 → 419.50 → 411.68

**News (last ~14d):**
- May 6: stock **+6%** to $418, **fresh 52-week high**, on AMD Q1 blowout sector tailwind.
- April revenue **NT$410.73B (~$13.08B), +17.5% YoY** on AI-chip demand.
- 2nm chip capacity to grow at **~70% CAGR through 2028** (5 fabs ramping).
- 2026 capex guided to **upper end of $52–56B**.
- Analyst price targets up to $480 (Barclays $470 OW, DA Davidson $450, Needham $480). Next earnings July 16.

### 5. MSTR — Owned → HOLD (0.60)

**Brief (USD):**
- Price 187.59, **−20.85% P&L** (−$395.28 unrealized on $1,896 cost basis — **past the −15% cut-loss threshold**), 30d change **+41.12%**
- Quantity 8, avg buy 237.00, current value $1,500.72
- RSI(14) **66.3**
- MACD **11.77** vs signal **10.38** (histogram **+1.39**, bullish)
- SMA20 167.35 / SMA50 147.41 — price well above both
- Recent closes: 169.20 → 158.19 → 187.59 (sharp recovery)

**News (last ~14d):**
- May 5: Q1 2026 GAAP **loss $12.54B / −$38.25 EPS**, but **better than analyst avg of −$18.98**. Revenue **$124.3M** (~in line with $125.07M est).
- Holds **818,334 BTC** at avg ~$75,500/coin (~3.9% of supply).
- **Major strategic pivot**: dropping "never sell" bitcoin policy → actively manage holdings to boost BTC-per-share.
- Q1 capital raises: $7.37B (ATM) + $2.07B (STRC preferred); STRC scaled to $8.5B in nine months.

## Rules applied (per `routine/agent_prompt.md`)

- **Watchlist default = HOLD**; BUY only on a clear bullish entry trigger.
  - MAERSK had RSI nearing oversold but bearish MACD + bearish news catalysts (Iran war) → no entry trigger → HOLD.
- **Owned default = HOLD**, with two override gates:
  - **SELL (lock gain)** when `pnl_pct > +25% AND technicals weakening` → TSM at +24.4% but technicals **strengthening** (MACD bullish, RSI rising, 52-week high) → no SELL.
  - **SELL (cut loss)** when `pnl_pct < −15% AND trend continues bearish` → MSTR at −20.8% but trend **bullish** (+41% in 30d, MACD positive, above SMAs) → no SELL.
  - **BUY (add)** when bullish technicals + supportive news + small-ish position → ADBE: MACD bullish crossover, above SMAs, AI/Firefly tailwind, $1,440 cost basis on the smaller end → BUY at moderate confidence (CEO transition cap).
  - NFLX in the ±10% noise band with mixed indicators (oversold RSI vs bearish MACD/guidance) → HOLD.

## What was missing — worth adding to the brief in future

These are gaps in the agent's context that were felt during this run. Roughly ordered by "highest signal value, lowest implementation cost" first.

### Tier 1 — cheap data already in or near the pipeline

1. **SMA200** — needs >200 trading days of history. Currently `prepare` requests `period="6mo"` (~125 trading days), which silently produces `null` for SMA200, making the **golden / death cross** flags always `false`. Bump `market_data.get_price_history(..., period="2y")` for the SMA call (or compute SMA200 separately on a longer window). Long-trend regime is the cheapest, highest-value indicator we're missing.
2. **52-week high / low + distance from each** — anchor for "breakout" vs "near support" reasoning. Trivially computed from existing closes if we extend the lookback.
3. **ATR(14) and recent volatility regime** — sizes how meaningful a given % move is. Without it, "+41% in 30d" on MSTR vs "+5% in 30d" on ADBE feel comparable but aren't.
4. **Volume context** — last-day volume vs 20d-avg volume. Low-volume moves are noise; high-volume moves on a catalyst are real. yfinance gives volume in the same dataframe, so this is a 5-line addition.
5. **Days since latest earnings** — pre-earnings vs post-earnings has very different decision logic. yfinance exposes `.calendar` / `.earnings_dates` per ticker.
6. **Prior-run signal history** — last N signals for the same ticker (already in the `signals` table). Lets the agent see "we said SELL last week and the position is still here" or "this is the third HOLD in a row." Cheap Supabase read in `prepare`.

### Tier 2 — adds a network call but high judgement value

7. **Real-time / pre-market price + intraday change** — yfinance close is yesterday's. A pre-market move on news materially changes a "lock the gain" or "cut the loss" call. yfinance has `info["preMarketPrice"]` and `info["regularMarketChangePercent"]`; needs a freshness check.
8. **Forward calendar (earnings date, ex-div, key events) within next 14d** — "earnings in 3 days" should bias toward HOLD even on a strong technical setup.
9. **Sector / index relative strength** — was the move ticker-specific or sector-wide? `^GSPC`, `^NDX`, sector ETF (`XLK`, `XLF` …) close vs ticker close over 5d/30d. Helps discriminate alpha from beta.
10. **News sentiment scoring per article** — rather than rely on the agent skimming snippets, attach a numeric sentiment + catalyst type (earnings/regulatory/M&A/macro) per article. Could be done in a small LLM pass or a service like Finnhub.
11. **Analyst consensus + recent target changes** — current avg PT, # buys/holds/sells, recent revisions. Several free APIs (Finnhub, Yahoo) expose this.

### Tier 3 — bigger lift, situationally valuable

12. **Fundamentals snapshot** — PE, PEG, EV/EBITDA, FCF yield, dividend yield, debt/EBITDA. Currently the agent has zero valuation context, so a "buy the dip" call ignores whether the dip put it back to expensive or cheap.
13. **Insider transactions (last 90d)** — net insider buy/sell on dollar terms. Free via SEC EDGAR.
14. **Options-implied moves around earnings / IV percentile** — flags how much move is already priced in. Useful for sizing.
15. **Per-currency portfolio totals + position-as-% of profile** — the prompt asks the agent to weigh "small position relative to rest of profile" but only `cost_basis` per holding is exposed; the agent has to do the math itself. Pre-compute weights in the brief.
16. **Cross-run signal P&L scoring** — track how prior BUY signals played out (close T+5 vs close T+0). Closes the calibration loop. Probably belongs in a separate scheduled job, not in `prepare`.
17. **FX rates snapshot** — current DKK/USD, EUR/USD, etc. Doesn't change per-holding decisions (the prompt forbids cross-currency P&L) but would let us produce a portfolio-level summary in the user's home currency without the agent having to fetch FX.

### Non-context improvements (related but separate)

- **News snippet caching across runs** — the agent currently re-searches the same ticker the next day. A small Supabase table keyed `(ticker, day, query_hash)` would dedupe.
- **`recent_closes` is currently the last 10 closes** — fine for visual sanity but the agent never reasons over it directly. Either drop it from the brief to save tokens, or extend it to 30 closes if we want the agent to do its own mini-trend read.
- **Brief size budget** — every Tier 1/2 addition costs prompt tokens. Probably worth defining a target brief size (e.g. ≤ 6KB per holding) and trimming `recent_closes` / verbose indicator names if it grows.

## Sources cited during this run

- [Maersk Q1 2026 results — Maersk newsroom](https://www.maersk.com/news/articles/2026/05/07/maersk-delivered-volume-growth-across-all-businesses-in-q1)
- [Maersk CEO warns on Iran war impact — CNBC](https://www.cnbc.com/2026/05/07/maersk-ceo-warns-iran-war-will-have-bigger-impact-in-coming-months.html)
- [Netflix Q1 2026 earnings — CNBC](https://www.cnbc.com/2026/04/16/netflix-nflx-earnings-q1-2026.html)
- [Netflix stock fell after Q1 2026 — Motley Fool](https://www.fool.com/investing/2026/04/21/netflix-stock-fell-after-q1-2026-earnings-heres-wh/)
- [Adobe Q1 FY2026 earnings — Futurum](https://futurumgroup.com/insights/adobe-q1-fy-2026-earnings-show-ai-monetization-progress-amid-ceo-transition/)
- [Adobe Firefly AI Assistant launch — Adobe Newsroom](https://news.adobe.com/news/2026/04/adobe-new-creative-agent)
- [TSMC stock surges on AMD Q1 read-through — Investing.com](https://www.investing.com/news/company-news/why-is-taiwan-semiconductor-manufacturing-stock-surging-today-93CH-4664204)
- [TSMC 2nm capacity outlook — Motley Fool](https://www.fool.com/investing/2026/05/05/prediction-tsmc-stock-will-jump-3x-by-2030/)
- [MicroStrategy Q1 2026 results — TheStreet](https://www.thestreet.com/crypto/markets/michael-saylors-strategy-reports-12-54b-net-loss-in-q1)
- [MicroStrategy ditches 'never sell' bitcoin policy — CNBC](https://www.cnbc.com/2026/05/05/strategy-breaks-from-never-sell-bitcoin-approach.html)
