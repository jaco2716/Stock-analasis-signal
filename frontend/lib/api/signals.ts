import "server-only";
import { createServerClient } from "@/lib/supabase/server";
import type { Signal, SignalType } from "@/lib/types";

export interface SignalFilters {
  signalType?: SignalType;
  ticker?: string;
  fromDate?: string;
  toDate?: string;
}

export const listRecentSignals = async (
  profileId: string,
  limit = 10,
): Promise<Signal[]> => {
  const supabase = await createServerClient();
  const { data, error } = await supabase
    .from("signals")
    .select("*")
    .eq("profile_id", profileId)
    .order("generated_at", { ascending: false })
    .limit(limit);
  if (error) throw error;
  return data ?? [];
};

export interface PagedSignals {
  rows: Signal[];
  total: number;
}

export const listSignals = async (
  profileId: string,
  filters: SignalFilters,
  page = 1,
  pageSize = 25,
): Promise<PagedSignals> => {
  const supabase = await createServerClient();
  const from = (page - 1) * pageSize;
  const to = from + pageSize - 1;

  let query = supabase
    .from("signals")
    .select("*", { count: "exact" })
    .eq("profile_id", profileId)
    .order("generated_at", { ascending: false });

  if (filters.signalType) query = query.eq("signal_type", filters.signalType);
  if (filters.ticker) query = query.ilike("ticker", `%${filters.ticker}%`);
  if (filters.fromDate) query = query.gte("generated_at", filters.fromDate);
  if (filters.toDate) query = query.lte("generated_at", filters.toDate);

  const { data, error, count } = await query.range(from, to);
  if (error) throw error;
  return { rows: data ?? [], total: count ?? 0 };
};
