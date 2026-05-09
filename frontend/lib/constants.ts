import type { SignalType } from "./types";

export const ACTIVE_PROFILE_COOKIE = "active_profile_slug";

export const SIGNAL_COLORS: Record<
  SignalType,
  { bg: string; text: string; border: string }
> = {
  BUY: {
    bg: "bg-green-500/15",
    text: "text-green-700 dark:text-green-400",
    border: "border-green-500/30",
  },
  SELL: {
    bg: "bg-red-500/15",
    text: "text-red-700 dark:text-red-400",
    border: "border-red-500/30",
  },
  HOLD: {
    bg: "bg-zinc-500/15",
    text: "text-zinc-700 dark:text-zinc-400",
    border: "border-zinc-500/30",
  },
} as const;
