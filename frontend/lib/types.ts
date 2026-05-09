import type { Database, HoldingKind, SignalType, AnalysisRunStatus } from "./database.types";

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

export type { HoldingKind, SignalType, AnalysisRunStatus };

export type ActionResult = { ok: true } | { ok: false; error: string };
