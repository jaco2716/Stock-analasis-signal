// Placeholder generated-types stub. Regenerate with the live schema via:
//   supabase gen types typescript --linked > lib/database.types.ts
// Keep the shape `Database['public']['Tables']['<name>']['Row'|'Insert'|'Update']`
// so consumer code in lib/api/* and lib/types.ts continues to type-check after regen.

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export type HoldingKind = "owned" | "watchlist";
export type SignalType = "BUY" | "SELL" | "HOLD";
export type AnalysisRunStatus = "pending" | "running" | "completed" | "failed";

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string;
          name: string;
          slug: string;
          discord_webhook_url: string | null;
          is_active: boolean;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          name: string;
          slug: string;
          discord_webhook_url?: string | null;
          is_active?: boolean;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          name?: string;
          slug?: string;
          discord_webhook_url?: string | null;
          is_active?: boolean;
          created_at?: string;
          updated_at?: string;
        };
      };
      portfolio_holdings: {
        Row: {
          id: string;
          profile_id: string;
          ticker: string;
          name: string;
          quantity: number | null;
          avg_buy_price_dkk: number | null;
          kind: HoldingKind;
          added_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          profile_id: string;
          ticker: string;
          name: string;
          quantity?: number | null;
          avg_buy_price_dkk?: number | null;
          kind: HoldingKind;
          added_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          profile_id?: string;
          ticker?: string;
          name?: string;
          quantity?: number | null;
          avg_buy_price_dkk?: number | null;
          kind?: HoldingKind;
          added_at?: string;
          updated_at?: string;
        };
      };
      signals: {
        Row: {
          id: string;
          profile_id: string;
          ticker: string;
          signal_type: SignalType;
          reasoning: string;
          confidence: number;
          generated_at: string;
          run_id: string;
        };
        Insert: {
          id?: string;
          profile_id: string;
          ticker: string;
          signal_type: SignalType;
          reasoning: string;
          confidence: number;
          generated_at?: string;
          run_id: string;
        };
        Update: {
          id?: string;
          profile_id?: string;
          ticker?: string;
          signal_type?: SignalType;
          reasoning?: string;
          confidence?: number;
          generated_at?: string;
          run_id?: string;
        };
      };
      analysis_runs: {
        Row: {
          id: string;
          started_at: string;
          completed_at: string | null;
          profile_count: number;
          signal_count: number;
          status: AnalysisRunStatus;
          error_message: string | null;
        };
        Insert: {
          id?: string;
          started_at?: string;
          completed_at?: string | null;
          profile_count?: number;
          signal_count?: number;
          status?: AnalysisRunStatus;
          error_message?: string | null;
        };
        Update: {
          id?: string;
          started_at?: string;
          completed_at?: string | null;
          profile_count?: number;
          signal_count?: number;
          status?: AnalysisRunStatus;
          error_message?: string | null;
        };
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: {
      holding_kind: HoldingKind;
      signal_type: SignalType;
      analysis_run_status: AnalysisRunStatus;
    };
    CompositeTypes: Record<string, never>;
  };
}
