"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getProfileBySlug } from "@/lib/api/profiles";
import { requireAuth } from "@/lib/auth-server";
import { ACTIVE_PROFILE_COOKIE } from "@/lib/constants";
import { isValidSlug } from "@/lib/slug";

export const setActiveProfileAction = async (slug: string): Promise<void> => {
  await requireAuth();
  if (!isValidSlug(slug)) {
    redirect("/profiles");
  }
  const profile = await getProfileBySlug(slug);
  if (!profile || !profile.is_active) {
    redirect("/profiles");
  }
  const cookieStore = await cookies();
  cookieStore.set(ACTIVE_PROFILE_COOKIE, slug, {
    httpOnly: false,
    sameSite: "lax",
    path: "/",
    // ~1 year — UI preference, not a security boundary.
    maxAge: 60 * 60 * 24 * 365,
  });
  redirect(`/p/${slug}`);
};
