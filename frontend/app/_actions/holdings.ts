"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import {
  deleteHolding,
  insertHolding,
  updateHolding,
} from "@/lib/api/portfolio";
import { requireAuth } from "@/lib/auth-server";
import type { ActionResult } from "@/lib/types";

const tickerSchema = z
  .string()
  .trim()
  .min(1, "Ticker is required")
  .max(16)
  .transform((s) => s.toUpperCase());

const currencySchema = z
  .string()
  .trim()
  .toUpperCase()
  .regex(/^[A-Z]{3}$/, "Currency must be a 3-letter ISO code");

const ownedFieldsRefine = (
  v: { kind: "owned" | "watchlist"; quantity?: number; avg_buy_price?: number },
) => {
  if (v.kind !== "owned") return true;
  return (
    typeof v.quantity === "number" &&
    Number.isFinite(v.quantity) &&
    v.quantity > 0 &&
    typeof v.avg_buy_price === "number" &&
    Number.isFinite(v.avg_buy_price) &&
    v.avg_buy_price > 0
  );
};

const addHoldingSchema = z
  .object({
    profileId: z.string().uuid(),
    profileSlug: z.string().min(1),
    ticker: tickerSchema,
    name: z.string().trim().max(200).optional().or(z.literal("").transform(() => undefined)),
    kind: z.enum(["owned", "watchlist"]),
    quantity: z.number().optional(),
    avg_buy_price: z.number().optional(),
    currency: currencySchema.default("DKK"),
  })
  .refine(ownedFieldsRefine, {
    message: "Quantity and avg buy price are required for owned holdings",
    path: ["quantity"],
  });

const updateHoldingSchema = z.object({
  id: z.string().uuid(),
  profileSlug: z.string().min(1),
  quantity: z.number().positive("Quantity must be greater than zero"),
  avg_buy_price: z.number().positive("Avg buy price must be greater than zero"),
  currency: currencySchema,
});

const removeHoldingSchema = z.object({
  id: z.string().uuid(),
  profileSlug: z.string().min(1),
});

const lookupTickerSchema = z.object({
  ticker: tickerSchema,
});

const toError = (e: unknown): string =>
  e instanceof Error ? e.message : "Unknown error";

export const addHolding = async (
  input: z.input<typeof addHoldingSchema>,
): Promise<ActionResult> => {
  try {
    await requireAuth();
    const parsed = addHoldingSchema.parse(input);
    const isOwned = parsed.kind === "owned";
    await insertHolding({
      profile_id: parsed.profileId,
      ticker: parsed.ticker,
      name: parsed.name ?? parsed.ticker,
      kind: parsed.kind,
      quantity: isOwned && typeof parsed.quantity === "number" ? parsed.quantity : null,
      avg_buy_price:
        isOwned && typeof parsed.avg_buy_price === "number"
          ? parsed.avg_buy_price
          : null,
      currency: parsed.currency,
    });
    revalidatePath(`/p/${parsed.profileSlug}`, "page");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: toError(e) };
  }
};

export const updateHoldingAction = async (
  input: z.input<typeof updateHoldingSchema>,
): Promise<ActionResult> => {
  try {
    await requireAuth();
    const parsed = updateHoldingSchema.parse(input);
    await updateHolding(parsed.id, {
      quantity: parsed.quantity,
      avg_buy_price: parsed.avg_buy_price,
      currency: parsed.currency,
    });
    revalidatePath(`/p/${parsed.profileSlug}`, "page");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: toError(e) };
  }
};

export const removeHolding = async (
  input: z.input<typeof removeHoldingSchema>,
): Promise<ActionResult> => {
  try {
    await requireAuth();
    const parsed = removeHoldingSchema.parse(input);
    await deleteHolding(parsed.id);
    revalidatePath(`/p/${parsed.profileSlug}`, "page");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: toError(e) };
  }
};

// Yahoo's chart endpoint returns the security's native currency in
// `chart.result[0].meta.currency`. Same source yfinance uses, no auth required.
// On any failure we return null so the form falls back to its manual default.
export const lookupTickerCurrency = async (
  input: z.input<typeof lookupTickerSchema>,
): Promise<{ currency: string } | null> => {
  try {
    const { ticker } = lookupTickerSchema.parse(input);
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(
      ticker,
    )}?range=1d&interval=1d`;
    const res = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0" },
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as {
      chart?: { result?: Array<{ meta?: { currency?: string } }> };
    };
    const code = data.chart?.result?.[0]?.meta?.currency;
    if (typeof code !== "string" || !/^[A-Z]{3}$/i.test(code)) return null;
    return { currency: code.toUpperCase() };
  } catch {
    return null;
  }
};
