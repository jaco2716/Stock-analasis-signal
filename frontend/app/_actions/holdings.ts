"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import {
  deleteHolding,
  insertHolding,
  updateHoldingPosition,
} from "@/lib/api/portfolio";
import type { ActionResult } from "@/lib/types";

const tickerSchema = z
  .string()
  .trim()
  .min(1, "Ticker is required")
  .max(16)
  .transform((s) => s.toUpperCase());

const addHoldingSchema = z
  .object({
    profileId: z.string().uuid(),
    profileSlug: z.string().min(1),
    ticker: tickerSchema,
    name: z.string().trim().max(200).optional().or(z.literal("").transform(() => undefined)),
    kind: z.enum(["owned", "watchlist"]),
    position_dkk: z.number().optional(),
  })
  .refine(
    (v) =>
      v.kind !== "owned" ||
      (typeof v.position_dkk === "number" &&
        !Number.isNaN(v.position_dkk) &&
        v.position_dkk > 0),
    {
      message: "Position (DKK) is required for owned holdings",
      path: ["position_dkk"],
    },
  );

const updatePositionSchema = z.object({
  id: z.string().uuid(),
  profileSlug: z.string().min(1),
  position_dkk: z.number().positive("Position must be greater than zero"),
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
    const parsed = addHoldingSchema.parse(input);
    await insertHolding({
      profile_id: parsed.profileId,
      ticker: parsed.ticker,
      name: parsed.name ?? parsed.ticker,
      kind: parsed.kind,
      position_dkk:
        parsed.kind === "owned" && typeof parsed.position_dkk === "number"
          ? parsed.position_dkk
          : null,
    });
    revalidatePath(`/p/${parsed.profileSlug}`, "page");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: toError(e) };
  }
};

export const updatePosition = async (
  input: z.input<typeof updatePositionSchema>,
): Promise<ActionResult> => {
  try {
    const parsed = updatePositionSchema.parse(input);
    await updateHoldingPosition(parsed.id, parsed.position_dkk);
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
    const parsed = removeHoldingSchema.parse(input);
    await deleteHolding(parsed.id);
    revalidatePath(`/p/${parsed.profileSlug}`, "page");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: toError(e) };
  }
};
