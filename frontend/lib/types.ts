import type { Database, Enums } from "./database.types";

type Tables = Database["public"]["Tables"];

export type Profile = Tables["profiles"]["Row"];
export type NewProfile = Tables["profiles"]["Insert"];
export type ProfileUpdate = Tables["profiles"]["Update"];

export type Holding = Tables["portfolio_holdings"]["Row"];
export type NewHolding = Tables["portfolio_holdings"]["Insert"];
export type HoldingUpdate = Tables["portfolio_holdings"]["Update"];

export type Signal = Tables["signals"]["Row"];
export type NewSignal = Tables["signals"]["Insert"];

export type AnalysisRun = Tables["analysis_runs"]["Row"];

export type HoldingKind = Enums<"holding_kind">;
export type SignalType = Enums<"signal_type">;
export type AnalysisRunStatus = Enums<"run_status">;

export type ActionResult = { ok: true } | { ok: false; error: string };

export type SupportedCurrency = "DKK" | "USD" | "EUR";

export interface BacktestFilters {
  minConfidence: number;
  signalTypes: SignalType[];
  fromDate?: string;
  toDate?: string;
  tickers?: string[];
  window: 5 | 30;
  dedupWeekly: boolean;
  treatSellsAsShorts: boolean;
  notionalByCurrency: Record<SupportedCurrency, number>;
  kurtageByCurrency: Record<SupportedCurrency, number>;
}

export interface BacktestTickerRow {
  ticker: string;
  currency: string;
  trades: number;
  wins: number;
  avgOutcomePct: number;
  totalPnl: number;
}

export interface BacktestCurrencyTotal {
  currency: string;
  trades: number;
  wins: number;
  winRate: number;
  avgOutcomePct: number;
  totalPnl: number;
  bestTradePnl: number;
  worstTradePnl: number;
}

export interface BacktestResult {
  totals: BacktestCurrencyTotal[];
  byTicker: BacktestTickerRow[];
  excludedNoOutcome: number;
  dedupRemoved: number;
}
