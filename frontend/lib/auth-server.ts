// Server-only auth helpers that read/write the session cookie via next/headers.
// Keep these out of `lib/auth.ts` so middleware (Edge runtime) can import the
// pure crypto helpers without dragging in next/headers.

import { cookies } from "next/headers";

import {
  SESSION_COOKIE,
  SESSION_TTL_MS,
  buildSessionToken,
  verifySessionToken,
} from "./auth";

export const isAuthenticated = async (): Promise<boolean> => {
  const cookieStore = await cookies();
  return verifySessionToken(cookieStore.get(SESSION_COOKIE)?.value);
};

export const requireAuth = async (): Promise<void> => {
  if (!(await isAuthenticated())) throw new Error("Unauthorized");
};

export const setSessionCookie = async (): Promise<void> => {
  const { token } = await buildSessionToken();
  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: Math.floor(SESSION_TTL_MS / 1000),
  });
};

export const clearSessionCookie = async (): Promise<void> => {
  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
};
