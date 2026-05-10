"use server";

import type { Route } from "next";
import { redirect } from "next/navigation";

import { verifyPassword } from "@/lib/auth";
import { clearSessionCookie, setSessionCookie } from "@/lib/auth-server";
import type { ActionResult } from "@/lib/types";

const isSafeRedirect = (target: string): boolean =>
  target.startsWith("/") && !target.startsWith("//") && !target.startsWith("/\\");

export const loginAction = async (
  password: string,
  from: string | null,
): Promise<ActionResult> => {
  if (typeof password !== "string" || password.length === 0) {
    return { ok: false, error: "Password is required" };
  }
  if (!verifyPassword(password)) {
    return { ok: false, error: "Incorrect password" };
  }
  await setSessionCookie();
  const target = from && isSafeRedirect(from) ? from : "/";
  redirect(target as Route);
};

export const logoutAction = async (): Promise<void> => {
  await clearSessionCookie();
  redirect("/login" as Route);
};
