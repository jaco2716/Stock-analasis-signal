"use client";

import { useTransition } from "react";

import { Button } from "@/components/ui/button";
import { logoutAction } from "@/app/_actions/auth";

export const LogoutButton = () => {
  const [pending, startTransition] = useTransition();
  return (
    <Button
      variant="ghost"
      size="sm"
      disabled={pending}
      onClick={() => startTransition(() => logoutAction())}
    >
      {pending ? "Signing out..." : "Sign out"}
    </Button>
  );
};
