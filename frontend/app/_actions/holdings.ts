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

const ownedFieldsRefine = (
  v: { kind: "owned" | "watchlist"; quantity?: number; avg_buy_price_dkk?: number },
) => {
  if (v.kind !== "owned") return true;
  return (
    typeof v.quantity === "number" &&
    Number.isFinite(v.quantity) &&
    v.quantity > 0 &&
    typeof v.avg_buy_price_dkk === "number" &&
    Number.isFinite(v.avg_buy_price_dkk) &&
    v.avg_buy_price_dkk > 0
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
    avg_buy_price_dkk: z.number().optional(),
  })
  .refine(ownedFieldsRefine, {
    message: "Quantity and avg buy price are required for owned holdings",
    path: ["quantity"],
  });

const updateHoldingSchema = z.object({
  id: z.string().uuid(),
  profileSlug: z.string().min(1),
  quantity: z.number().positive("Quantity must be greater than zero"),
  avg_buy_price_dkk: z.number().positive("Avg buy price must be greater than zero"),
});

const removeHoldingSchema = z.object({
  id: z.string().uuid(),
  profileSlug: z.string().min(1),
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
      avg_buy_price_dkk:
        isOwned && typeof parsed.avg_buy_price_dkk === "number"
          ? parsed.avg_buy_price_dkk
          : null,
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
      avg_buy_price_dkk: parsed.avg_buy_price_dkk,
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
