import "server-only";
import { createServerClient, createServiceClient } from "@/lib/supabase/server";
import type { Holding, HoldingKind, NewHolding } from "@/lib/types";

export const listHoldings = async (
  profileId: string,
  kind?: HoldingKind,
): Promise<Holding[]> => {
  const supabase = await createServerClient();
  let query = supabase
    .from("portfolio_holdings")
    .select("*")
    .eq("profile_id", profileId)
    .order("ticker", { ascending: true });
  if (kind) query = query.eq("kind", kind);
  const { data, error } = await query;
  if (error) throw error;
  return data ?? [];
};

export const insertHolding = async (input: NewHolding): Promise<Holding> => {
  const supabase = createServiceClient();
  const { data, error } = await supabase
    .from("portfolio_holdings")
    .insert(input)
    .select()
    .single();
  if (error) throw error;
  return data;
};

export const updateHolding = async (
  id: string,
  patch: {
    quantity: number | null;
    avg_buy_price: number | null;
    currency?: string;
  },
): Promise<Holding> => {
  const supabase = createServiceClient();
  const { data, error } = await supabase
    .from("portfolio_holdings")
    .update(patch)
    .eq("id", id)
    .select()
    .single();
  if (error) throw error;
  return data;
};

export const deleteHolding = async (id: string): Promise<void> => {
  const supabase = createServiceClient();
  const { error } = await supabase
    .from("portfolio_holdings")
    .delete()
    .eq("id", id);
  if (error) throw error;
};
