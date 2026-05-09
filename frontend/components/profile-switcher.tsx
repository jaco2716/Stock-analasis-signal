"use client";

import { useTransition } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { setActiveProfileAction } from "@/app/_actions/set-active-profile";
import type { Profile } from "@/lib/types";

interface ProfileSwitcherProps {
  profiles: Profile[];
  activeSlug: string | null;
}

export const ProfileSwitcher = ({
  profiles,
  activeSlug,
}: ProfileSwitcherProps) => {
  const [pending, startTransition] = useTransition();

  if (profiles.length === 0) {
    return null;
  }

  return (
    <Select
      value={activeSlug ?? undefined}
      onValueChange={(slug) => {
        startTransition(() => {
          void setActiveProfileAction(slug);
        });
      }}
      disabled={pending}
    >
      <SelectTrigger className="w-[220px]">
        <SelectValue placeholder="Select profile" />
      </SelectTrigger>
      <SelectContent>
        {profiles.map((p) => (
          <SelectItem key={p.id} value={p.slug}>
            {p.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
};
