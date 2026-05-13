import "server-only";
import { createServerClient } from "@/lib/supabase/server";
import type {
  BacktestCurrencyTotal,
  BacktestFilters,
  BacktestResult,
  BacktestTickerRow,
  SupportedCurrency,
} from "@/lib/types";

interface SignalRow {
  id: string;
  ticker: string;
  signal_type: "BUY" | "SELL" | "HOLD";
  generated_at: string;
  confidence: number | null;
  currency: string | null;
  outcome_t5_pct: number | null;
  outcome_t30_pct: number | null;
}

// ISO-8601 week — Thursday in current week decides the year, week is counted
// from the first Thursday. Returns "YYYY-Www" so it groups stably as a string.
const isoWeekKey = (iso: string): string => {
  const d = new Date(iso);
  const utc = new Date(
    Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()),
  );
  const dayNum = utc.getUTCDay() || 7;
  utc.setUTCDate(utc.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(utc.getUTCFullYear(), 0, 1));
  const week = Math.ceil(
    ((utc.getTime() - yearStart.getTime()) / 86400000 + 1) / 7,
  );
  return `${utc.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
};

const SUPPORTED: SupportedCurrency[] = ["DKK", "USD", "EUR"];
const isSupportedCurrency = (c: string): c is SupportedCurrency =>
  (SUPPORTED as string[]).includes(c);

export const runBacktest = async (
  profileId: string,
  filters: BacktestFilters,
): Promise<BacktestResult> => {
  const supabase = await createServerClient();

  let query = supabase
    .from("signals")
    .select(
      "id, ticker, signal_type, generated_at, confidence, currency, outcome_t5_pct, outcome_t30_pct",
    )
    .eq("profile_id", profileId)
    .in("signal_type", filters.signalTypes)
    .gte("confidence", filters.minConfidence);

  if (filters.fromDate) query = query.gte("generated_at", filters.fromDate);
  if (filters.toDate) query = query.lte("generated_at", filters.toDate);
  if (filters.tickers && filters.tickers.length > 0) {
    query = query.in("ticker", filters.tickers);
  }

  query = query.order("generated_at", { ascending: true });

  const { data, error } = await query;
  if (error) throw error;
  const rows = (data ?? []) as SignalRow[];

  const outcomeKey: "outcome_t5_pct" | "outcome_t30_pct" =
    filters.window === 5 ? "outcome_t5_pct" : "outcome_t30_pct";

  let excludedNoOutcome = 0;
  const withOutcome = rows.filter((r) => {
    const v = r[outcomeKey];
    if (v == null) {
      excludedNoOutcome += 1;
      return false;
    }
    return true;
  });

  let dedupRemoved = 0;
  let surviving = withOutcome;
  if (filters.dedupWeekly) {
    const seen = new Map<string, SignalRow>();
    for (const r of withOutcome) {
      const key = `${r.ticker}::${r.signal_type}::${isoWeekKey(r.generated_at)}`;
      const existing = seen.get(key);
      if (!existing) {
        seen.set(key, r);
      } else {
        dedupRemoved += 1;
        // Keep the earliest signal per group — query is already ordered asc, so
        // the first one wins; nothing to swap.
      }
    }
    surviving = Array.from(seen.values());
  }

  interface Trade {
    ticker: string;
    currency: string;
    outcomePct: number;
    pnl: number;
  }
  const trades: Trade[] = [];

  for (const r of surviving) {
    if (r.signal_type === "HOLD") continue;
    if (r.signal_type === "SELL" && !filters.treatSellsAsShorts) continue;

    const rawCcy = (r.currency ?? "DKK").toUpperCase();
    const ccy: SupportedCurrency = isSupportedCurrency(rawCcy) ? rawCcy : "DKK";
    const notional = filters.notionalByCurrency[ccy];
    const kurtage = filters.kurtageByCurrency[ccy];
    if (
      notional == null ||
      kurtage == null ||
      !Number.isFinite(notional) ||
      !Number.isFinite(kurtage)
    ) {
      excludedNoOutcome += 1;
      continue;
    }

    const outcomePct = Number(r[outcomeKey]);
    const directional = r.signal_type === "BUY" ? 1 : -1;
    const pnl = (directional * notional * outcomePct) / 100 - 2 * kurtage;

    trades.push({
      ticker: r.ticker,
      currency: ccy,
      outcomePct,
      pnl,
    });
  }

  const byTickerMap = new Map<
    string,
    {
      ticker: string;
      currency: string;
      trades: number;
      wins: number;
      sumOutcome: number;
      totalPnl: number;
    }
  >();
  const byCurrencyMap = new Map<
    string,
    {
      currency: string;
      trades: number;
      wins: number;
      sumOutcome: number;
      totalPnl: number;
      best: number;
      worst: number;
    }
  >();

  for (const t of trades) {
    const tk = byTickerMap.get(t.ticker) ?? {
      ticker: t.ticker,
      currency: t.currency,
      trades: 0,
      wins: 0,
      sumOutcome: 0,
      totalPnl: 0,
    };
    tk.trades += 1;
    if (t.pnl > 0) tk.wins += 1;
    tk.sumOutcome += t.outcomePct;
    tk.totalPnl += t.pnl;
    byTickerMap.set(t.ticker, tk);

    const cc = byCurrencyMap.get(t.currency) ?? {
      currency: t.currency,
      trades: 0,
      wins: 0,
      sumOutcome: 0,
      totalPnl: 0,
      best: Number.NEGATIVE_INFINITY,
      worst: Number.POSITIVE_INFINITY,
    };
    cc.trades += 1;
    if (t.pnl > 0) cc.wins += 1;
    cc.sumOutcome += t.outcomePct;
    cc.totalPnl += t.pnl;
    if (t.pnl > cc.best) cc.best = t.pnl;
    if (t.pnl < cc.worst) cc.worst = t.pnl;
    byCurrencyMap.set(t.currency, cc);
  }

  const byTicker: BacktestTickerRow[] = Array.from(byTickerMap.values())
    .map((tk) => ({
      ticker: tk.ticker,
      currency: tk.currency,
      trades: tk.trades,
      wins: tk.wins,
      avgOutcomePct: tk.trades > 0 ? tk.sumOutcome / tk.trades : 0,
      totalPnl: tk.totalPnl,
    }))
    .sort((a, b) => b.totalPnl - a.totalPnl);

  const totals: BacktestCurrencyTotal[] = Array.from(byCurrencyMap.values())
    .map((cc) => ({
      currency: cc.currency,
      trades: cc.trades,
      wins: cc.wins,
      winRate: cc.trades > 0 ? cc.wins / cc.trades : 0,
      avgOutcomePct: cc.trades > 0 ? cc.sumOutcome / cc.trades : 0,
      totalPnl: cc.totalPnl,
      bestTradePnl: cc.trades > 0 ? cc.best : 0,
      worstTradePnl: cc.trades > 0 ? cc.worst : 0,
    }))
    .sort((a, b) => a.currency.localeCompare(b.currency));

  return {
    totals,
    byTicker,
    excludedNoOutcome,
    dedupRemoved,
  };
};
