import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";

import { Toaster } from "@/components/ui/sonner";
import { ProfileSwitcher } from "@/components/profile-switcher";
import { LogoutButton } from "@/components/logout-button";
import { listProfiles } from "@/lib/api/profiles";
import { isAuthenticated } from "@/lib/auth-server";
import { ACTIVE_PROFILE_COOKIE } from "@/lib/constants";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stock signals",
  description: "Portfolio analysis and trading signals",
};

const RootLayout = async ({ children }: { children: React.ReactNode }) => {
  const authed = await isAuthenticated();
  const profiles = authed ? await listProfiles().catch(() => []) : [];
  const cookieStore = await cookies();
  const activeSlug = cookieStore.get(ACTIVE_PROFILE_COOKIE)?.value ?? null;

  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        {authed ? (
          <header className="border-b">
            <div className="container flex h-14 items-center justify-between gap-4">
              <Link href="/" className="font-semibold">
                Stock signals
              </Link>
              <div className="flex items-center gap-3">
                <ProfileSwitcher profiles={profiles} activeSlug={activeSlug} />
                <Link
                  href="/profiles"
                  className="text-sm text-muted-foreground hover:text-foreground"
                >
                  Manage profiles
                </Link>
                <LogoutButton />
              </div>
            </div>
          </header>
        ) : null}
        <main className="container py-6">{children}</main>
        <Toaster />
      </body>
    </html>
  );
};

export default RootLayout;
