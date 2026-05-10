import { redirect } from "next/navigation";

import { isAuthenticated } from "@/lib/auth-server";
import { LoginForm } from "./login-form";

interface LoginPageProps {
  searchParams: Promise<{ from?: string }>;
}

const LoginPage = async ({ searchParams }: LoginPageProps) => {
  if (await isAuthenticated()) redirect("/");
  const { from } = await searchParams;
  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <div className="w-full max-w-sm space-y-6 rounded-lg border bg-card p-6 shadow-sm">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">Sign in</h1>
          <p className="text-sm text-muted-foreground">
            Enter the shared password to access the dashboard.
          </p>
        </div>
        <LoginForm from={from ?? null} />
      </div>
    </div>
  );
};

export default LoginPage;
