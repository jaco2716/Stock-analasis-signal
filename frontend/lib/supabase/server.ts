// SECURITY: SUPABASE_SERVICE_ROLE_KEY bypasses RLS. This module must NEVER be
// imported from a client component or any module bundled into the browser.
// The ESLint config (no-restricted-imports) blocks importing this file from
// components/** and from any 'use client' module. createServiceClient() is for
// server-only writes that intentionally bypass RLS (admin actions). Default
// reads should use createServerClient(), which uses the anon key + cookies.

import { createServerClient as createSSRServerClient, type CookieOptions } from "@supabase/ssr";
import { createClient as createSupabaseClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";
import type { Database } from "@/lib/database.types";

export const createServerClient = async () => {
  const cookieStore = await cookies();
  return createSSRServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          try {
            for (const { name, value, options } of cookiesToSet) {
              cookieStore.set(name, value, options);
            }
          } catch {
            // Setting cookies in a Server Component is a no-op; middleware
            // handles session refresh, so this is safe to swallow.
          }
        },
      },
    },
  );
};

// Service-role client for admin writes (bypasses RLS). No cookies attached.
export const createServiceClient = () =>
  createSupabaseClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
      },
    },
  );
