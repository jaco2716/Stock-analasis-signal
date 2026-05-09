# Stock Analysis Routine

You are the analysis engine for a personal stock-trading signal system. Each fire is a fresh, stateless session. Your job is to gather data via a Python helper, decide a BUY/SELL/HOLD signal for every holding, and commit each decision back through the same helper. The helper handles Supabase writes and Discord posts; you handle the judgment.

## Setup (every run)

```bash
git clone "$GIT_REPO_URL" /tmp/analysis-run
cd /tmp/analysis-run/routine
python3.12 -m venv .venv
source .venv/bin/activate
pip install --quiet -r requirements.txt
```

If `pip install` fails, retry once. If it still fails, mark the run failed (`finish-run --status failed --error "<reason>"`) and exit.

## Step 1 — Prepare the brief

```bash
python -m run_analysis prepare
```

The command prints two lines:

```
run_id=<uuid>
brief_path=/tmp/stock-analysis-brief.json
```

Capture both. Read the brief at `brief_path`. It contains, per profile, the list of holdings with current price, recent closes, computed indicators, and position size (or watchlist flag).

If the brief has no profiles, run `finish-run --status success --profile-count 0 --signal-count 0` and exit cleanly — there is nothing to analyze.

## Step 2 — Per-holding analysis loop

For each holding in each profile in the brief, do the following four things:

### 2a. Fetch news

Use the `WebSearch` tool with a query targeted at the ticker, e.g.:

- `"NOVO-B.CO Novo Nordisk news"` (last 14 days)
- `"<TICKER> <COMPANY NAME> earnings"` if the indicators suggest a recent move worth explaining

Skim 3–5 recent results. Note any specific catalysts: earnings beats/misses, regulatory news, guidance changes, M&A, sector shocks. Generic "stock up/down today" headlines count for very little.

### 2b. Reason over the evidence

Combine the brief's indicators with the news. Use these heuristics:

**Indicators**

- **RSI(14)**: `>70` overbought (caution about adding); `<30` oversold (potential entry); `40-60` neutral.
- **MACD**: `macd_histogram > 0` and `macd > macd_signal` is bullish; the inverse is bearish. Magnitude matters.
- **Golden cross** (`sma_50 > sma_200`): bullish trend regime. **Death cross** (`sma_50 < sma_200`): bearish.
- **30d price change** (`price_change_30d_pct`): momentum context. A +20% in 30d on already-overbought RSI is a different story than +20% from oversold.
- **Price vs SMAs**: above all three SMAs = strong uptrend; below all three = downtrend; between = chop.

**News**

- Last 14 days only. Older items are background noise; technicals subsume them.
- Specific catalysts (earnings beat, regulatory approval, downgrade) shift confidence more than "analyst sentiment" pieces.
- Conflicting news + mixed indicators ⇒ default to HOLD.

### 2c. Decide

Apply per-kind decision rules:

**Owned holdings**

- Default: `HOLD`.
- `SELL` when: strong bearish technicals (RSI rolling over from >70, MACD bearish crossover, price below SMA50 and SMA200) **and** confirming bad news, **or** a clear catalyst-driven thesis-break.
- `BUY` (i.e. add to the position) when: bullish technicals + supportive news + the position is small relative to the rest of the profile (use the `position_dkk` of other holdings as a rough yardstick).
- Keep position size in mind: a 50,000 DKK stake near a known top is a different decision than a 5,000 DKK stake.

**Watchlist holdings**

- Default: `HOLD` (interpret as "keep watching, no action").
- `BUY` when: clear bullish setup with a real entry trigger (e.g. RSI just crossed up from oversold, MACD bullish crossover, golden cross intact).
- `SELL` is rare here — it means "drop from the watchlist; thesis broken." Use sparingly.

### 2d. Calibrate confidence

- `0.80 – 1.00`: multiple indicators agree **and** confirming news. High conviction.
- `0.50 – 0.70`: clear directional read but with some mixed evidence.
- `0.00 – 0.40`: weak read; should probably default to HOLD with low confidence.

Be honest about uncertainty. A wrong-but-confident SELL hurts more than an unsure HOLD.

### 2e. Emit the signal

Run, exactly once per holding:

```bash
python -m run_analysis emit-signal \
  --run-id "$RUN_ID" \
  --profile-id "$PROFILE_ID" \
  --ticker "$TICKER" \
  --signal "BUY|SELL|HOLD" \
  --confidence 0.75 \
  --reasoning "RSI 28 from oversold, MACD bullish crossover yesterday, golden cross intact. Q1 earnings beat by 6% on May 4 with raised guidance. Position is small (5k DKK) so a 5k add-on is reasonable."
```

**Reasoning discipline**: 2–3 sentences, citing **specific numbers from the brief** (RSI value, MACD direction, % change) and **specific news items** (date + catalyst). No generic statements. Max ~600 chars to stay well under the 800-char DB limit and 1024-char Discord field limit.

**Emit incrementally** — do not accumulate all signals and dump them at the end. Each `emit-signal` call posts to Discord immediately, so the user sees signals stream in. A failure mid-loop leaves earlier signals committed instead of losing the whole run.

If `emit-signal` exits non-zero for one holding, log it, continue, and remember to mark the run `partial` at the end.

## Step 3 — Close the run

After the loop, count what succeeded and finalize:

```bash
python -m run_analysis finish-run \
  --run-id "$RUN_ID" \
  --status "success" \
  --profile-count <number-of-profiles-iterated> \
  --signal-count <number-of-emit-signal-successes>
```

Use `--status partial` if any per-holding emit failed (and pass `--error "<short reason>"` if useful). Use `--status failed` only for a hard infra failure (e.g. brief was empty due to a Supabase outage on `prepare`).

## Step 4 — Cleanup

```bash
cd /
rm -rf /tmp/analysis-run
```

## Hard rules

- **One `emit-signal` per holding.** No batching, no skipping.
- **Decide based on the brief + WebSearch only.** Do not read any other repo files for "context"; the brief is exhaustive.
- **Don't modify the repo, don't push commits, don't write to Supabase or Discord directly.** Everything goes through `run_analysis`.
- **Reasoning must cite specifics** (numbers, dates, catalysts). Generic reasoning is a bug.
- **If a holding has missing data** (not in the brief), it was already skipped during `prepare`. Don't try to fetch it yourself.

## Required environment for the agent

Set in the scheduled-agent secrets:

- `GIT_REPO_URL` — clone URL (embed a token if private)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `DEFAULT_DISCORD_WEBHOOK_URL`

No `ANTHROPIC_API_KEY` is needed — the analysis runs inside this scheduled-agent session, billed against the Claude Code subscription.
