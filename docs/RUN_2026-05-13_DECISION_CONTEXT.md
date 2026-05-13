# Decision Context — Run 2026-05-13

Run ID `4fb6b940-b44d-4235-96b1-e7517695997f`. Profile: Default. 19 holdings (8 owned USD, 11 watchlist — 10 USD + 1 DKK). Brief at `/tmp/stock-analysis-brief.json`. Sister doc to `RUN_2026-05-11_DECISION_CONTEXT.md`.

Portfolio totals (per profile, from the brief):
- `USD` → cost_basis $11,307 / value $12,175.91 / 18 holdings
- `DKK` → cost_basis 0 / value 0 / 1 holding (watchlist only)
- FX snapshot: `DKK_USD = 0.156706`

Signal mix this run: **1 BUY (ADBE), 2 SELL (AMD, PLTR), 16 HOLD**. Two BUY/SELL decisions stream into Discord as embeds; the 16 HOLDs roll up into a compact summary at `finish-run`.

## Brief schema observations (vs. RUN_2026-05-11)

This run's brief is materially fuller than the May-11 snapshot. Tier-by-tier:

| # | Field | State this run |
|---|---|---|
| Tier 1 | SMA200, 52w distance, ATR, volume, days since/until earnings, signal history | ✅ All populated for every holding. |
| Tier 2 | Real-time block | ✅ `intraday_*` populated everywhere; `pre_market_*` populated for **all 17 USD tickers** (`market_state="PRE"`), null for MAERSK-B.CO (`REGULAR` on CSE). |
| Tier 2 | Sector RS | ✅ Now present for 10/19 (`sector_benchmark` + `sector_pct_change_30d` + `sector_relative_strength_30d_pct`). Mapped: NFLX→XLC, ADBE→IGV, TSM/AMD/NVDA/AVGO→SMH, MSTR→IBIT, TSLA/AMZN→XLY, META→XLC, MSFT→XLK. Missing: MAERSK, PLTR, GOOG, IRON, IONQ, INTC, WMT, ASML (the search log printed `no suffix-mapped index for X; defaulting to ^GSPC` for the US tickers, confirming the sector-mapping table is still partial). |
| Tier 2 | Analyst consensus | ✅ Mean, distance, high/low, recommendation_key, count on all 19. |
| Tier 3 | Fundamentals | ✅ Full block on all 19 (IRON has null trailing_pe — pre-profit). |
| Tier 3 | Insider 90d | ✅ Now **populated for 17/19** (MAERSK + ASML the holdouts — both non-US). yfinance + SEC EDGAR Form 4 fallback (per the May-13 commit). |
| Tier 3 | Options-implied earnings move | ⚠️ Now populated for the **only two holdings with earnings ≤14d**: NVDA (May 20, implied 7.94%, ATM put IV 0.78, ATM call IV ~0) and WMT (May 21, implied 5.72%, ATM put IV 0.39, ATM call IV ~0). The asymmetric call-IV-near-zero on both is suspicious — likely a stale-quote or filter artifact in the option-chain pull worth a follow-up. |
| Tier 3 | Position weight | ✅ Per-currency `cost_basis × 100 / total_cost_basis_in_same_currency`. NFLX 11.14%, ADBE 12.74%, TSM 11.71%, **MSTR 16.77%**, **AMD 13.74%**, PLTR 10.29%, TSLA 12.15%, NVDA 11.45%. None breach the 25% concentration line. |
| Tier 3 | Outcomes | ❌ `signal_history[]` still carries only `generated_at`, `signal_type`, `confidence` — no `outcome_t5_pct` / `outcome_t30_pct`. Calibration loop still open. |
| — | News sentiment scoring | ❌ Agent skims WebSearch snippets directly; not pre-scored. |

**Net**: Tier 1+2 effectively complete. Tier 3 ~80%: insider gap closed via EDGAR fallback for US listings; sector-RS map ~50% covered; outcomes still missing.

## Per-holding context delivered this run

For each ticker the agent reasoned on (1) the brief, (2) one WebSearch query for last-14-day news.

### 1. MAERSK-B.CO — Watchlist → HOLD (0.60)

**Brief (DKK):**
- Price 14,720; intraday **+3.01%** (`market_state=REGULAR`)
- 30d change **−8.54%**; RSI 45.3; ATR 497 (3.38% of price)
- MACD −349.4 / signal −320.8 (hist **−28.6**, bearish)
- SMA20 14,859 / SMA50 15,742 / SMA200 14,020 — golden cross intact, between SMA20 and SMA200
- 52w: −19.67% below high / +37.45% above low; volume **0.31×** (low conviction)
- Earnings: last 2026-05-07 (6 days ago); next 2026-08-13 (92d)
- Analyst mean 13,188 DKK (**−10.41%**), key `underperform`, 19 analysts
- Baseline ^OMXC25 30d +8.39% → **RS −16.93%** (laggard)
- Fundamentals: trailing PE 21.5, fwd PE −54 (negative est), PEG 0.38, P/B 0.62, debt/eq 31.7, FCF yield 1.24%
- Insider: null; implied-move: null; position_weight_pct: null
- Prior: HOLD ×5 (0.60–0.65)

**News:** Q1 print May 7 — EBIT $340M, Ocean volumes +9.3%, Logistics revenue +8.7%, FY guide held at 2–4% market growth; ordered 8 18,600-TEU dual-fuel vessels; Suape (Brazil) and Lázaro Cárdenas (Mexico) terminal investments. Constructive but priced-in.

### 2. NFLX — Owned (15 sh @ $84) → HOLD (0.60)

**Brief (USD):**
- Price $87.66; intraday +2.59%; pre-market $86.98 (−0.78%, `PRE`)
- PnL **+$54.90 / +4.36%**, position 11.14%
- 30d −5.71%; RSI 37.9 (approaching oversold); ATR 2.64 (3.01% of price)
- MACD −2.44 / signal −1.66 (hist −0.78, bearish); **death cross**
- SMA20 92.81 / SMA50 95.13 / SMA200 103.02 — below all
- 52w: **−34.64% below high** / +16.86% above low; volume 0.98×
- Earnings: last 2026-04-16 (27d); next 2026-07-16 (64d)
- Analyst mean **$114.55 (+30.68%)**, key `buy`, 44 analysts
- Baseline ^GSPC +16.67% → **RS −22.38%**; sector XLC +7.32% → **sector RS −13.03%**
- Fundamentals: trailing PE 28.3, fwd PE 22.8, PEG 1.28, P/B 13.9, FCF yield 7.04%, margin 28.5%
- Insider: net **−$87M** (0 buys / **13 sells**); position 11.14%
- Prior: HOLD ×5 (0.60)

**News:** Texas AG sued NFLX May 11 for "addicting users" (data-collection allegations). Ad business reportedly scaling above Street expectations (+2.4% pop on the leak). Market response muted.

### 3. ADBE — Owned (6 sh @ $240) → **BUY (0.55)**

**Brief (USD):**
- Price $240.83; intraday −2.16%; pre-market $239.90 (−0.39%, `PRE`)
- PnL +$4.98 / +0.35%, position 12.74%
- 30d −0.12%; RSI 44.6; ATR 9.16 (3.81% of price)
- MACD **+0.41** / signal +0.26 (hist **+0.15**, fresh bullish twitch); death cross
- SMA20 247.63 / SMA50 249.63 / SMA200 310.09 — below all
- 52w: **−43.06% below high** / +7.45% above low; volume 0.64×
- Earnings: last 2026-03-12 (62d); next 2026-06-11 (29d) — just outside the 14d gate
- Analyst mean **$327.96 (+36.18%)**, key `buy`, 34 analysts
- Baseline ^GSPC → **RS −16.79%**; sector IGV +15.23% → **sector RS −15.35%**
- Fundamentals: **trailing PE 14.0**, fwd PE 9.13, PEG 0.68, P/B 8.55, EV/EBITDA 10.2, **FCF yield 9.58%**, margin 29.5%, ROE 58.8% (clean value setup)
- Insider: net −$18.8M (0 buys / 5 sells)
- Prior: BUY ×5 with declining confidence (0.62 → 0.58)

**News:** Apr 27 Mizuho downgrade Outperform→Neutral, PT cut $315→$270 ("no clear catalyst"). DA Davidson reiterated Buy at $300. Q1 FY26 print (Mar 12) was a beat: rev $6.40B +12% YoY, non-GAAP EPS $6.06 (+3.18% beat), record Q1 operating cash flow $2.96B. April Firefly AI Assistant + Anthropic partnership unmonetized. Q2 (early June) is the next binary.

### 4. TSM — Owned (4 sh @ $331) → HOLD (0.70)

**Brief (USD):**
- Price $397.28; intraday −1.79%; pre-market $400.78 (+0.88%, `PRE`)
- PnL **+$265.12 / +20.02%**, position 11.71%
- 30d **+25.52%**; RSI 55.5; ATR 14.4 (3.62% of price)
- MACD +12.53 / signal +13.02 (hist **−0.49**, slight rollover); **golden cross**; above all SMAs
- 52w: −5.41% below high / **+117.86% above low**; volume 1.20×
- Earnings: last 2026-04-16 (27d); next 2026-07-16 (64d)
- Analyst mean $463.45 (+16.66%), key `none`, 18 analysts
- Baseline ^GSPC → RS +8.86%; sector SMH +54.82% → **sector RS −29.29%** (TSM lagged the chip rally)
- Fundamentals: trailing PE 33.8, fwd PE 20.6, PEG 1.23, P/B 87.9, EV/EBITDA 2.79, **FCF yield 35.0%**, margin 46.5%
- Insider: **net +$168k (43 buys / 0 sells)** — only ticker in basket with net positive insider activity
- Prior: HOLD ×5 (0.70–0.72)

**News:** May 12 — board authorized up to **$20B capital increase for Arizona subsidiary**; FY26 capex guide raised to high end of $52–56B range (vs $40.9B FY25). Q1 strong: rev +35.1% YoY. 2nm fab capacity guided to +70% CAGR through 2028. Recent target raises: Barclays $470, Needham $480, DA Davidson $450.

### 5. MSTR — Owned (8 sh @ $237) → HOLD (0.55)

**Brief (USD):**
- Price $184.42; intraday **−5.88%**; pre-market $184.45 (+0.02%, `PRE`)
- PnL **−$420.64 / −22.19%**, position 16.77% (largest)
- 30d **+51.86%**; RSI 60.6; ATR 10.6 (**5.75% of price — highest-vol in basket**)
- MACD +12.03 / signal +11.05 (hist +0.98, bullish); death cross
- SMA20 172.88 / SMA50 149.67 / SMA200 221.26 — above 20/50, below 200
- 52w: **−59.66% below high** / +77.04% above low; volume 0.77×
- Earnings: last 2026-05-05 (8d); next 2026-07-30 (78d)
- Analyst mean **$380.43 (+106.28%)**, key `strong_buy`, 14 analysts
- Baseline ^GSPC → RS +35.20%; sector IBIT +21.55% → **sector RS +30.31%** (outperforming Bitcoin itself)
- Fundamentals: trailing PE null (loss), fwd PE 47.4, P/B 1.30, EV/EBITDA −5.69, FCF yield **−13.45%**
- Insider: net −$4.8M (1 buy / 46 sells)
- Prior: HOLD ×5 (0.50–0.55)

**News:** Q1 May 5 — net loss **$12.54B** (Bitcoin unrealized loss $14.46B). Strategic shift: CEO stated "we will sell bitcoin when advantageous" — break from Saylor's "never sell" doctrine. Bought 535 BTC for $43M on May 11 at avg $80,340 (cumulative 720k BTC at avg $75,540 cost basis). Debt-wall scrutiny piece on Investing.com.

### 6. AMD — Owned (6 sh @ $259) → **SELL (0.78)**

**Brief (USD):**
- Price $448.29; intraday −2.29%; pre-market $458.45 (+2.27%, `PRE`)
- PnL **+$1,135.74 / +73.08%**, position 13.74%
- 30d **+128.67%**; RSI **77.23 (deeply overbought)**; ATR 23.0 (5.14% of price)
- MACD +52.39 / signal +42.04 (hist +10.35, strongly bullish); **golden cross**, above all SMAs
- 52w: −4.46% below high / **+319.04% above low**; volume 0.80×
- Earnings: last 2026-05-05 (8d); next 2026-08-04 (83d)
- Analyst mean **$451.58 (+0.73% — essentially at target)**, key `strong_buy`, 48 analysts
- Baseline ^GSPC → RS +112%; sector SMH +54.82% → **sector RS +73.86%** (real alpha, not sector beta)
- Fundamentals: trailing PE 149.4, fwd PE 34.7, PEG 1.08, EV/EBITDA 97.2 (priced for perfection)
- Insider: net **−$85.7M (0 buys / 38 sells)** — conviction distribution
- Prior: **SELL ×4 with rising confidence (0.65 → 0.78), one HOLD before that**

**News:** May 5 Q1 blowout — rev $10.3B, GAAP EPS $0.84, non-GAAP $1.37 (vs $1.25 consensus, +9.6% beat). Data Center +57% YoY ($5.8B). Stock 320% / 12mo. Forward outlook strong but valuation now extreme.

### 7. PLTR — Owned (6 sh @ $194) → **SELL (0.73)**

**Brief (USD):**
- Price $136.00; intraday −0.65%; pre-market $135.14 (−0.63%, `PRE`)
- PnL **−$348.00 / −29.90%**, position 10.29%
- 30d −1.13%; RSI 43.9; ATR 6.29 (4.62% of price)
- MACD −2.16 / signal −1.75 (hist −0.41, bearish); **death cross**; below all SMAs
- 52w: **−34.46% below high** / +18.25% above low; volume 0.85×
- Earnings: last 2026-05-04 (9d); next 2026-08-03 (82d)
- Analyst mean $183.73 (+35.09%), key `buy`, 27 analysts
- Baseline ^GSPC → **RS −17.79%**; no sector benchmark mapped
- Fundamentals: trailing PE 154.5, fwd PE 65.9, PEG 2.02, P/B 44.0, EV/EBITDA 157.7
- Insider: net **−$432M (0 buys / 54 sells)** — massive distribution, largest in basket
- Prior: **SELL ×5 (0.72–0.75)**

**News:** May 4 Q1 — rev $1.63B vs $1.54B consensus, EPS $0.33 vs $0.28, **revenue +85% YoY (fastest since 2020)**. Raised FY26 guidance to $7.65–7.66B (+71%, above $7.27B LSEG). Initial reaction: −5.66% AH. Recovered +4% Thursday. May 7 Argus upgrade to Buy at $190 PT. Market unmoved by beat — bull thesis broken.

### 8. TSLA — Owned (3 sh @ $458) → HOLD (0.55)

**Brief (USD):**
- Price $433.45; intraday −2.61%; pre-market $438.30 (+1.12%, `PRE`)
- PnL −$73.65 / −5.36%, position 12.15%
- 30d **+22.00%**; RSI 67.1 (warm); ATR 16.9 (3.89% of price)
- MACD +12.86 / signal +6.19 (hist +6.67, strongly bullish); **death cross** still in place
- SMA20 394.85 / SMA50 384.64 / SMA200 405.67 — above 20/50, near 200
- 52w: −13.11% below high / +58.65% above low; volume 0.93×
- Earnings: last 2026-04-22 (21d); next 2026-07-22 (70d)
- Analyst mean **$412.25 (−4.89%)**, key `buy` (split panel: high $600 / low $123), 41 analysts
- Baseline ^GSPC → RS +5.34%; sector XLY +11.95% → **sector RS +10.05%**
- Fundamentals: trailing PE **405**, fwd PE 172, PEG 5.97 (extreme), debt/eq 18.7, margin 3.95%
- Insider: net −$30.9M (0 buys / 40 sells)
- Prior: HOLD ×5 (0.57–0.60)

**News:** May 12 −5% drop on Musk China trip (FSD approval), robotaxi operational glitches (Dallas/Houston long waits + cancellations), Panasonic battery production delays. Robotaxi launch **June 22** the key near-term binary. SpaceX IPO expected late June. Piper Sandler note: "Optimus is free at $445."

### 9. NVDA — Owned (7 sh @ $185) → HOLD (0.60)

**Brief (USD):**
- Price $220.78; intraday +0.61%; pre-market $225.59 (+2.18%, `PRE`)
- PnL **+$250.46 / +19.34%**, position 11.45%
- 30d **+33.67%**; RSI 69.3; ATR 6.91 (3.13% of price)
- MACD +7.15 / signal +6.11 (hist +1.05, bullish); **golden cross**, above all SMAs
- 52w: **−1.33% below high** / +83.60% above low; volume 1.04×
- **Earnings: last 2026-02-25 (77d); next 2026-05-20 (7d)** — at the avoid-strong-directional gate
- **Implied earnings move: 7.94%** (exp 2026-05-22, ATM put IV 0.78, ATM call IV ~0 — likely data artifact)
- Analyst mean $269.95 (+22.27%), key `strong_buy`, 57 analysts
- Baseline ^GSPC → RS +17.00%; sector SMH +54.82% → **sector RS −21.15%** (NVDA lagged the rally — room left)
- Fundamentals: trailing PE 45.1, fwd PE 19.5, PEG 0.70, FCF yield 1.08%, margin 55.6%, ROE 101.5%
- Insider: net −$163.7M (0 buys / 38 sells)
- Prior: HOLD ×5 (0.55–0.65)

**News:** Q1 FY27 print May 20, guided $78B ± 2%, Street $78.8B / $1.77 EPS. Hyperscaler capex from MSFT/AMZN/GOOG/META totaling ~$725B 2026 (+77% YoY). Jensen: $1T Blackwell+Rubin opportunity through 2027. Fwd PE 25 below AI-era average — Morningstar sees "fair value."

### 10. AVGO — Watchlist → HOLD (0.50)

**Brief (USD):** Price $419.30, intraday −2.13%, pre-market $421.54 (+0.53%). RSI 59.8, MACD turning bearish (hist −2.07) despite **golden cross**. +42.91% 30d. −4.20% from 52w high. Volume 0.95×. Earnings 2026-06-03 (21d). Analyst mean $475.49 (+13.40%), `strong_buy`. RS vs ^GSPC +26.24%, sector SMH → sector RS −11.91%. Fundamentals: trailing PE 81.9, fwd PE 23.1, PEG 0.91, FCF yield 1.28%. **Insider net −$356M (0 buys / 95 sells — second-heaviest distribution in basket)**. No prior signals.

**News:** May 12 Citi PT raised $475→$500. Q1 AI revenue +106% YoY to $8.4B. Apollo/Blackstone in talks for $35B financing; OpenAI custom-chip deal hit $18B financing snag.

### 11. GOOG — Watchlist → HOLD (0.55)

**Brief (USD):** Price $383.82, intraday −0.76%. RSI 69.8, MACD bullish (hist +1.68), golden cross, above all SMAs. +40.52% 30d, **−3.65% from 52w high**. Earnings 2026-04-29 (14d ago — right at the boundary). Analyst mean $418.47 (+9.03%), `strong_buy`. RS vs ^GSPC +23.86%; no sector mapping. Fundamentals: trailing PE 29.2, fwd PE 26.5, FCF yield 0.59%, margin 37.9%. Insider net −$23.6M (0 buys / 40 sells). No prior signals.

**News:** Q1 +22% YoY, Cloud +63% YoY, operating margin 32.9%. Pentagon Gemini classified-environment contract; SpaceX 6.11% stake disclosed; SpaceX×GOOG orbital-data-center talks reported. May I/O event upcoming.

### 12. AMZN — Watchlist → HOLD (0.55)

**Brief (USD):** Price $265.82, intraday −1.18%. RSI 63.8, MACD slightly bearish (hist −1.06), golden cross, above all SMAs. +32.28% 30d, −4.57% from 52w high. Earnings 2026-04-29 (14d). Analyst mean $311.55 (+17.20%), `strong_buy`. RS vs ^GSPC +15.62%, sector XLY +11.95% → **sector RS +20.33%** (real alpha). Fundamentals: trailing PE 31.8, fwd PE 26.9, PEG 1.85, FCF yield 0.34%, margin 12.2%. Insider net −$46.5M (0 buys / 40 sells). No prior signals.

**News:** AWS +28% YoY to $37.6B (15-quarter fastest). Trainium/Graviton crossed $20B run-rate. New launches: Amazon Now 30-min delivery; **Amazon Supply Chain Solutions** competing in $750B logistics market (FDX/UPS −10% on the leak). Capex $131.8B TTM crushed FCF to $7.7B.

### 13. IRON (IREN) — Watchlist → HOLD (0.50)

**Brief (USD):** Price $68.53, intraday −1.01%, pre-market $67.50 (−1.50%). RSI 53.8, MACD just turned bearish (hist −0.07), **death cross**, between SMAs. +12.75% 30d, **−31.13% from 52w high**. Volume **1.72×** (high). Earnings 2026-05-05 (8d). Analyst mean $100.17 (+46.16%), `strong_buy`. RS vs ^GSPC −3.92%; no sector mapping. Fundamentals: trailing PE null (loss), fwd PE −9.15, EV/EBITDA −7.26, FCF yield −4.64%. Insider net −$3.8M (0 buys / 15 sells, **net_share_pct −15.55%** very heavy). No prior signals.

**News:** Q3 May 7 — rev $144.8M (from $184.7M Q2), wider net loss; bitcoin-mining revenue under pressure. **NVIDIA 5-yr right to purchase up to 30M shares at $70 strike (~$2.1B value)**. ARR under contract $3.1B (Microsoft $1.9B + NVIDIA $0.7B annualized). Strategic pivot to AI Cloud from BTC mining on 5GW power portfolio.

### 14. IONQ — Watchlist → HOLD (0.45)

**Brief (USD):** Price $55.87, intraday −1.79%, pre-market $56.82 (+1.72%). RSI 68.8, MACD bullish (hist +0.83), **death cross**, above SMA20/50/200. **+110.12% 30d** (extreme). ATR **7.69% of price** (largest in basket). Volume 1.26×. −33.99% from 52w high. Earnings 2026-05-06 (7d). Analyst mean $66.38 (+18.81%), `strong_buy`, 14 analysts. RS vs ^GSPC **+93.45%**; no sector mapping. Fundamentals: trailing PE 143.3, fwd PE −53.6, **profit margin 174.9% (likely accounting-driven from warrant gains)**, FCF yield −0.44%. **Cash and investments $3.1B**. Insider net −$501k (1 buy / 5 sells).

**News:** May 6 Q1 — **record $64.7M revenue +755% YoY**, beat consensus $50.7M, gross profit $15.4M (+374% YoY), EPS −$0.34 vs −$0.52. Raised FY guide to $260–270M. Remaining performance obligations $470M (+554% YoY). 256-qubit sale to U. Cambridge; quantum-networking projects Poland/Florida; DARPA + Space Development Agency contracts.

### 15. INTC — Watchlist → HOLD (0.55)

**Brief (USD):** Price $120.61, intraday **−6.82%**, pre-market $125.06 (+3.69%). **RSI 75.14** (deeply overbought). MACD strongly bullish (hist +3.14), **golden cross**, above all SMAs. **+192.81% 30d (parabolic)**. ATR 6.16% of price. −9.15% from 52w high / +535.79% above 52w low. Volume 1.11×. Earnings 2026-04-23 (20d). Analyst mean **$84.43 = −29.99% BELOW current**, key `hold`. RS vs ^GSPC **+176.15%**; no sector mapping. Fundamentals: trailing PE null (loss), fwd PE 78.6, **margin −5.9%, ROE −2.9%, FCF yield −1.37%**. Insider net −$4M (0 buys / 1 sell — only sparse activity).

**News:** Apr 23 Q1 — rev $13.58B (+9.22% beat, +7.18% YoY), non-GAAP EPS $0.29, Data Center/AI +22% to $5.05B, Foundry +16%. **Apple-foundry-partnership reports** (Apple considering INTC 18A process) drove the rip to record high $132. May 12 inflation print triggered pullback.

### 16. META — Watchlist → HOLD (0.50)

**Brief (USD):** Price $603.00, intraday +0.69%, pre-market $599.53 (−0.58%). RSI 40.92 (neutral-low). MACD bearish (hist −6.63), **death cross**, below all SMAs. +12.42% 30d, **−24.09% from 52w high**. Volume 0.71× (low). Earnings 2026-04-29 (14d). Analyst mean $826.69 (+37.10%), `strong_buy`, 58 analysts. RS vs ^GSPC −4.25%, sector XLC +7.32% → **sector RS +5.10%**. Fundamentals: trailing PE 21.9, fwd PE 16.7, PEG 0.88, FCF yield 1.67%, margin 32.8%. Insider net −$105.7M (0 buys / 90 sells). No prior signals.

**News:** Apr 29 Q1 — rev $56.31B (+33% YoY) and EPS $10.44 vs $8.15 consensus, both beats. **Stock fell 6% post-earnings on raised FY26 capex guide $125–145B** (~2× FY25). User-count weakness blamed partly on **"internet disruptions in Iran"** (Hormuz conflict).

### 17. MSFT — Watchlist → HOLD (0.50)

**Brief (USD):** Price $407.77, intraday −1.19%, pre-market $405.65 (−0.52%). RSI 49 (neutral). MACD bearish (hist −1.87), **death cross**, below SMA20/200. +13.60% 30d, **−26.16% from 52w high**. Volume 1.07×. Earnings 2026-04-29 (14d). Analyst mean $561.56 (+37.71%), `strong_buy`. RS vs ^GSPC −3.07%, sector XLK +37.41% → **sector RS −23.81%** (badly lagged tech rally). Fundamentals: trailing PE 24.3, fwd PE 21.1, PEG 1.26, FCF yield 1.22%, margin 39.3%, ROE 34.0%. Insider net −$3.1M (1 buy / 1 sell — neutral).

**News:** Q3 — rev $82.9B +18%, op income $38.4B +20%, **AI run-rate $37B +123% YoY**, commercial backlog $627B +99% YoY, Azure +40%. Capex jumped 84% YoY to $30.88B; calendar 2026 capex ~$190B. Dividend ex-date **May 21** ($0.91). OpenAI investment targeting $92B return.

### 18. WMT — Watchlist → HOLD (0.45)

**Brief (USD):** Price $130.35, intraday +2.16%, pre-market $129.33 (−0.78%). RSI 55.8, MACD slightly bearish (hist −0.16), **golden cross**, above all SMAs. +5.75% 30d, **−2.84% from 52w high**. Volume 1.08×. **Earnings 2026-05-21 (8d)** — implied move 5.72% (ATM put IV 0.39, ATM call IV ~0). Analyst mean $137.37 (+5.38%), `strong_buy`. RS vs ^GSPC −10.92%; no sector mapping. Fundamentals: trailing PE 47.9, **fwd PE 39.6, PEG 4.86 (expensive)**, FCF yield 1.02%, margin 3.07%. Insider net −$411.9M (0 buys / 12 sells). No prior signals.

**News:** Earnings May 21. Morgan Stanley May 10 reiterated Overweight $140 PT. Tailwinds: food inflation ~2.3%, higher-income trade-down to WMT, MXN +16% (Walmart de México is 13% of consolidated AOI). **Headwinds: pharmacy ~100bps comp drag (Maximum Fair Pricing + generic GLP-1), ~$1B annual diesel/freight cost (~$100M Q1 before mitigation).**

### 19. ASML — Watchlist → HOLD (0.50)

**Brief (USD):** Price $1,520.94, intraday −2.87%, pre-market $1,532.55 (+0.76%). RSI 56.3, MACD strongly bullish (hist +11.30), **golden cross**, above all SMAs. +21.56% 30d, −4.66% from 52w high. ATR 4.10% of price. Volume 0.98×. Earnings 2026-04-15 (28d). Analyst mean $1,672.28 (+9.95%), `strong_buy`, 15 analysts. RS vs ^GSPC +4.89%; no sector mapping. Fundamentals: trailing PE 50.0, fwd PE 31.6, PEG 2.26, EV/EBITDA 45.7, FCF yield 1.41%, margin 29.7%, ROE 52.2%. Insider: null. No prior signals.

**News:** Raised FY26 guidance to **€36–40B** on AI demand (SK Hynix, Samsung orders). Risks: **TSMC delayed High-NA EUV deployment to ≥2029**; proposed US "MATCH Act" could tighten DUV-to-China export controls. May 8 institutional Buy→Hold downgrade triggered May 12 −3.54%.

## Decision summary table

| # | Ticker | Kind | Signal | Confidence | Why (one-liner) |
|---|---|---|---|---|---|
| 1 | MAERSK-B.CO | watchlist | HOLD | 0.60 | Q1 in-line, but RS −16.9% vs OMXC25 and analyst `underperform` cap upside |
| 2 | NFLX | owned | HOLD | 0.60 | Small +4.36% P&L; death cross + Texas suit vs scaling ads — neutral |
| 3 | ADBE | owned | **BUY** | 0.55 | PE 14 / FCF yield 9.6%, MACD fresh bullish, −43% from high — value-add |
| 4 | TSM | owned | HOLD | 0.70 | +20% P&L holding; insiders net buyers, Arizona $20B confirms thesis |
| 5 | MSTR | owned | HOLD | 0.55 | −22% but +51.9% 30d recovery + strategic shift — don't cut into reversal |
| 6 | AMD | owned | **SELL** | 0.78 | +73% P&L, RSI 77, at analyst target, 38 insider sells — lock in |
| 7 | PLTR | owned | **SELL** | 0.73 | −29.9%, post-earnings dud, $432M insider sells — thesis broken |
| 8 | TSLA | owned | HOLD | 0.55 | −5.4% range; robotaxi binary + China FSD pending |
| 9 | NVDA | owned | HOLD | 0.60 | Earnings May 20 (7d), implied 7.94% — don't bet binary |
| 10 | AVGO | watchlist | HOLD | 0.50 | +42.9% extension, MACD weakening, 95 insider sells |
| 11 | GOOG | watchlist | HOLD | 0.55 | Strong fundamentals but RSI 69.8, near 52w high — wait pullback |
| 12 | AMZN | watchlist | HOLD | 0.55 | AWS +28% but extended, MACD slightly bearish, no entry trigger |
| 13 | IRON | watchlist | HOLD | 0.50 | NVIDIA deal vs miss revenue + MACD bearish — wait for setup |
| 14 | IONQ | watchlist | HOLD | 0.45 | +110% 30d parabolic on Q1 beat; chasing here = poor R/R |
| 15 | INTC | watchlist | HOLD | 0.55 | +193% 30d, RSI 75, analyst PT −30% below current — do not chase |
| 16 | META | watchlist | HOLD | 0.50 | Capex spook unresolved; bull thesis stalled below SMAs |
| 17 | MSFT | watchlist | HOLD | 0.50 | Strong AI run-rate but sector RS −24% vs XLK — wait |
| 18 | WMT | watchlist | HOLD | 0.45 | Earnings May 21 (8d), size down per rules |
| 19 | ASML | watchlist | HOLD | 0.50 | Regulatory overhang (MATCH Act) into +21.6% extension |

## Open data gaps / artifacts worth flagging

- **`atm_call_iv` near zero** on both NVDA (0.001) and WMT (0.001) while ATM put IV is plausible (0.78 and 0.39). Either the option-chain pull is missing the call side or the strike-matching logic is degenerate. Worth a code-side check before next earnings cycle.
- **Sector benchmark mapping** still missing for MAERSK-B.CO, PLTR, GOOG, IRON, IONQ, INTC, WMT, ASML. The `prepare` step logs `no suffix-mapped index for X; defaulting to ^GSPC` for these — the broad-RS reading is delivered but separating sector-beta from ticker-alpha isn't possible.
- **Insider data** still null for the two non-US listings (MAERSK, ASML). yfinance + SEC EDGAR Form 4 covers US tickers; foreign issuers need a different source.
- **`signal_history` outcomes** (`outcome_t5_pct`, `outcome_t30_pct`) still absent from the brief. Without these the agent can't actually calibrate against its own track record.
- **`profit_margin_pct=174.9%`** on IONQ in the fundamentals block is clearly an accounting artifact (warrant fair-value gains inflating net income vs. revenue). Either filter or annotate at brief generation.
- **`dividend_yield_pct=336.0`** on MAERSK-B.CO — likely a special-dividend / units bug (should be ~3.36%, not 336%). Same pattern on TSM (96%), AVGO (62%), GOOG (23%), MSFT (89%), WMT (76%), ASML (58%). The field is scaled wrong by a factor of 100 across the board.
