"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import {
  deleteProfileById,
  getProfileById,
  insertProfile,
  updateProfileById,
} from "@/lib/api/profiles";
import { isValidSlug } from "@/lib/slug";
import type { ActionResult } from "@/lib/types";

const profileSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(120),
  slug: z
    .string()
    .trim()
    .min(1, "Slug is required")
    .max(64)
    .refine(isValidSlug, "Slug must be lowercase letters, numbers, and dashes"),
  discord_webhook_url: z
    .string()
    .trim()
    .url("Must be a valid URL")
    .optional()
    .or(z.literal("").transform(() => undefined)),
  is_active: z.boolean().default(true),
});

const toError = (e: unknown): string =>
  e instanceof Error ? e.message : "Unknown error";

export const createProfile = async (
  input: z.input<typeof profileSchema>,
): Promise<ActionResult> => {
  try {
    const parsed = profileSchema.parse(input);
    await insertProfile({
      name: parsed.name,
      slug: parsed.slug,
      discord_webhook_url: parsed.discord_webhook_url ?? null,
      is_active: parsed.is_active,
    });
    revalidatePath("/profiles");
    revalidatePath("/");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: toError(e) };
  }
};

export const updateProfile = async (
  id: string,
  input: z.input<typeof profileSchema>,
): Promise<ActionResult> => {
  try {
    const existing = await getProfileById(id);
    if (!existing) return { ok: false, error: "Profile not found" };
    const parsed = profileSchema.parse(input);
    await updateProfileById(id, {
      name: parsed.name,
      slug: parsed.slug,
      discord_webhook_url: parsed.discord_webhook_url ?? null,
      is_active: parsed.is_active,
    });
    revalidatePath("/profiles");
    revalidatePath("/");
    revalidatePath(`/p/${existing.slug}`, "page");
    if (existing.slug !== parsed.slug) {
      revalidatePath(`/p/${parsed.slug}`, "page");
    }
    return { ok: true };
  } catch (e) {
    return { ok: false, error: toError(e) };
  }
};

export const deleteProfile = async (id: string): Promise<ActionResult> => {
  try {
    const existing = await getProfileById(id);
    await deleteProfileById(id);
    revalidatePath("/profiles");
    revalidatePath("/");
    if (existing) revalidatePath(`/p/${existing.slug}`, "page");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: toError(e) };
  }
};
